"""Lane L0, release: schedule in Buffer exactly what Krish signed, once.

`growth.py run autorelease [--deliver]` runs in GitHub Actions with no model,
no session and no PC. Without --deliver it is a dry run: it reads Control
Center and Buffer and prints the plan as counts, and sends no mutation.

1. Signed go-lives. Krish's decisions are read from Control Center
   (engine.control_center.Client), every page of them (engine.cc_loop.
   decisions_paged: 100 a read, ties at a page edge kept; pages that never
   end fail the run as decisions_unpaged). Each approved go-live, its plan and any
   declined check-in are read back from the report that proposed them, and
   engine.cc_loop.claim_golives decides which go-lives may act (approved on
   the exact digest, plan open and not stopped, in date; an amended yes acts
   in his words, by amended_sha256).
2. Each signed slot, only once it is near: more than 90 minutes before its
   due time it is `not_yet_due` and nothing is read or edited, so a No, an
   amendment or a changed asset file before then stops it (the workflow runs
   every 30 minutes and GitHub cron can run late, so 90 minutes is the
   window). Then its Buffer draft is read fresh, it must be on this engine's
   own Buffer account (release.BUFFER_NAME, else `wrong_account`), and the
   line digest (line_digest, the go-live domain) is rebuilt from the draft:
   its text, its channel and Buffer channel id, the signed format, link
   placement, due time and publish mode, the sha256 of each asset's bytes
   downloaded now (capped at 50 MB; any failure holds), and `meta`: exactly
   what the edit will send besides the words and the time (first comment,
   titles, privacy, tags, alt text and the rest; buffer_api.signed_meta). It
   must equal the payload_sha256 the engine signed.
   The signed format must be what the draft is (asset count and kinds, and
   the Instagram or Facebook type), else `format_differs_from_draft`; a due_at
   outside its go-live's run window holds as `due_outside_run_window`.
   A route not verified and fresh in social/tools/buffer.json holds as
   `route_not_verified` (its one capability check goes through `run release`),
   and a snackable post that asks for the share as `share_ask_refused`.
   Every word the edit would schedule (the text, carried alt text, titles
   and first comments) runs content-engine's copy lint as `run release` does
   (buffer_api.edit_input, through release.copy_errors and
   release.media_copy_errors); a failing word holds as `copy_lint_refused`.
3. Match, still a draft, due more than five minutes ahead: one editPost to
   customScheduled at the signed due_at, carrying the whole draft forward,
   then a fresh readback that must say scheduled at that time, in those
   words, with that meta. A draft still unscheduled within five minutes of
   its time holds loudly (`due_time_passed`).
4. The alarm. A go-live whose latest decision is no longer an approval (or
   approves another version), or whose plan was stopped, may already have
   drafts scheduled from the earlier yes. Each such draft still scheduled,
   and not exactly the version he now approves, is reported loudly as
   `scheduled_after_decline`: the run exits non-zero so GitHub emails Krish.
   A stop that cannot be read (`stop_unresolved`), a capped read
   (`too_many_reads`) or an undated decision is loud too, and then every post
   scheduled on the pinned channels that no standing signed line matches is
   listed as `scheduled_after_decline`. It is never unscheduled here; that is
   his call.
5. Anything else holds with a reason code. Nothing is retried blindly and
   nothing without a signed decision is touched. LinkedIn and every
   krish_click slot stay drafts for Krish. A post already scheduled or sent in
   the signed words counts as done: Buffer is the ledger, so a second run is
   a no-op and no local state is needed (the claim ledger lives in a
   throwaway folder unless --state names one).

Output is one JSON summary of counts and reason codes: never words, URLs,
ids or keys.

Where the go-live comes from (the convention a go-live builder follows): a
staged proposal (plan, go_live, check_in) is reported in its own report whose
run_id is `<proposal_id>:<first 12 hex of its payload_sha256>`, so one GET
finds exactly the version Krish decided on. A go-live is a `post` wall with
target null; its exact_payload is the manifest, canonical JSON of
{"schema": "growth-golive-manifest/1", "run_id": ..., "slots": [line, ...]},
each line {slot_id, channel, format, due_at, link_placement, publish_mode,
buffer_draft_id, buffer_channel_id, words, assets: [sha256, ...], meta,
payload_sha256}, where payload_sha256 is line_digest of the line: the
release.slot_digest fields under the go-live domain, never equal to a run-spec
slot's digest, so a go-live yes is never a `run release` decision (F105).
Krish may amend a line's words or due_at, or drop a line, or turn a line to
krish_click; any other amendment holds. A line whose due_at is not a real
date holds alone (`bad_due_at`). engine.run.handoff is the builder: it turns a maker's
dispatch into such a go-live, rebuilding each line with draft_line below.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from engine.cc_loop import claim_golives, decisions_paged, decisions_since
from engine.control_center import (APPROVED_ORIGIN, RUN_ID, Client, ProtocolError, _decided_at, _latest,
                                   amendment_ok, report_digest)
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.core import calendar_date, instant, read_json, today
from engine.run import buffer_api
from engine.run.buffer_api import Buffer, BufferAuthError, BufferError, CarryHold
from engine.run.release import (BUFFER_ID, CHANNELS, DUE_AT, HEX64, KRISH_CLICK_ONLY, LINE_DOMAIN, account_hold,
                                format_shape_errors, route_holds, share_ask_errors, slot_digest)
from engine.run.spec import LENGTH, ny_midnight

ROOT = Path(__file__).resolve().parents[2]
BUFFER_KEY_ENV = 'BUFFER_API_KEY'
MANIFEST_SCHEMA = 'growth-golive-manifest/1'
LINE_KEYS = frozenset({'slot_id', 'channel', 'format', 'due_at', 'link_placement', 'publish_mode',
                       'buffer_draft_id', 'buffer_channel_id', 'words', 'assets', 'meta', 'payload_sha256'})
# Fields Krish may change in his amended manifest; any other change holds.
AMENDABLE = frozenset({'words', 'due_at', 'publish_mode', 'payload_sha256'})
LOOKBACK = dt.timedelta(days=70)  # a standing plan is approved once for eight weeks
DUE_MARGIN = dt.timedelta(minutes=5)
# A draft is scheduled only when DUE_MARGIN < due_at - now <= SCHEDULE_WINDOW. The
# workflow runs every 30 minutes and GitHub cron can run late, so 90 minutes.
SCHEDULE_WINDOW = dt.timedelta(minutes=90)
MAX_REPORT_READS = 24
MAX_ALARM_READS = 12
# Go-live holds that mean the run cannot tell whether a yes still stands (F103): each is
# loud (exit 1), as is every *too_many_reads, and each lists what is scheduled.
UNKNOWN_HOLDS = ('stop_unresolved', 'undated_decision')
# A go-live's id names its run (engine.run.handoff): the run window bounds every due_at in it.
GOLIVE_RUN = re.compile(r'^makeyourmindup:(?:golive:)?(\d{4}-W\d{2}|\d{4}-\d{2}-\d{2}):(week|piece|express)(?::|$)')
SERVICE_CHANNEL = {service: channel for channel, (service, _) in CHANNELS.items()}
AUTHORITY_FILE = Path('invariants') / 'authority.json'
SHOW_BEFORE_POST_DEFAULT = '2026-11-29'
# Where invariants/authority.json lists the derivative classes (each with its formats).
DERIVATIVE_KEYS = ('derivative_formats', 'derivatives')


# Show-before-post gate -------------------------------------------------------

def _authority(root=None):
    path = Path(root or ROOT) / AUTHORITY_FILE
    try:
        value = read_json(path)
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def show_before_post_until(root=None):
    value = _authority(root).get('show_before_post_until')
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return value
    return SHOW_BEFORE_POST_DEFAULT


def _format_names(entries):
    """Format names from a list of names, or of classes each listing its formats."""
    names = set()
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, str):
            names.add(entry)
        elif isinstance(entry, dict):
            names.update(f for f in entry.get('formats') or [] if isinstance(f, str))
    return names


def derivative_formats(root=None):
    """Formats invariants/authority.json lists as derivatives of an approved piece."""
    auth = _authority(root)
    for key in DERIVATIVE_KEYS:
        if isinstance(auth.get(key), list):
            return _format_names(auth[key])
    classes = auth.get('format_classes')
    if isinstance(classes, dict):
        return _format_names(classes.get('derivative'))
    return set()


def standing_derivative_allowed(slot, board_decision, today, root=None):
    """Whether a derivative may go out under a standing approval, with no go-live
    of its own. False until and including show_before_post_until (Krish sees
    every post first); after it, only a format class listed as a derivative in
    invariants/authority.json, and only when the piece's publish-board decision
    is approved."""
    day = today.isoformat() if isinstance(today, (dt.date, dt.datetime)) else str(today)
    if day <= show_before_post_until(root):
        return False
    fmt = slot.get('format') if isinstance(slot, dict) else None
    if fmt not in derivative_formats(root):
        return False
    verdict = board_decision.get('decision') if isinstance(board_decision, dict) else board_decision
    return verdict == 'approved'


def may_release(slot, golive_decision, board_decision, today, root=None):
    """A slot is released only under a go-live Krish approved; the standing
    derivative path stays shut until the show-before-post date has passed."""
    if isinstance(golive_decision, dict) and golive_decision.get('decision') == 'approved' \
            and golive_decision.get('stage') == 'go_live':
        return True
    return standing_derivative_allowed(slot, board_decision, today, root)


# The signed manifest ---------------------------------------------------------

def line_digest(line):
    """A go-live line's digest: the slot fields under the go-live domain (F105)."""
    return slot_digest({**line, 'assets': [{'sha256': h} for h in line['assets']]}, LINE_DOMAIN)


def spec_digest(line):
    """The run-spec slot digest of the same fields (release.slot_digest): what a maker's
    dispatch carries, from its spec, and what the handoff checks a rebuilt draft against.
    It never signs a go-live line."""
    return slot_digest({**line, 'assets': [{'sha256': h} for h in line['assets']]})


def run_window(run_id):
    """(start, end) of the run a run_id or go-live id names, or None when it names none."""
    match = GOLIVE_RUN.match(run_id) if isinstance(run_id, str) else None
    if not match:
        return None
    first, kind = match.groups()
    try:
        if '-W' in first:
            day = dt.date.fromisocalendar(int(first[:4]), int(first[6:]), 1)
        else:
            day = calendar_date(first)
        if kind == 'week':
            day -= dt.timedelta(days=day.weekday())
        return ny_midnight(day), ny_midnight(day + dt.timedelta(days=LENGTH[kind]))
    except (ValueError, OverflowError):
        return None


def asset_sources(post):
    return [a.get('source') if isinstance(a, dict) else None for a in post.get('assets') or []]


def draft_line(post, fields, fetch):
    """The manifest line one Buffer draft makes, rebuilt from the draft itself.

    Its channel comes from the draft's service, its Buffer channel id, words
    and meta (buffer_api.signed_meta: everything the edit sends besides the
    words and the time) from the draft, and each asset hash from the bytes
    downloaded now (fetch(url) returns (sha256, size) or raises BufferError).
    Every other digest field (format, due_at, link_placement, publish_mode)
    comes from fields, and payload_sha256 is the rebuilt line's own digest.
    The signed format must be what the draft is (release.format_shape_errors:
    its asset count and kinds and its Instagram or Facebook type), else
    CarryHold('format_differs_from_draft'), before any download (F101).
    Shared by the release (autorelease) and the handoff that proposes the
    go-live (engine.run.handoff), so both rebuild a slot exactly the same way."""
    if format_shape_errors(fields.get('format'), post):
        raise CarryHold('format_differs_from_draft')
    hashes = []
    for source in asset_sources(post):
        digest, _ = fetch(source)
        hashes.append(digest)
    channel_id = post.get('channelId')
    line = {**fields, 'channel': SERVICE_CHANNEL.get(post.get('channelService')), 'words': post.get('text'),
            'assets': hashes, 'meta': buffer_api.signed_meta(post, hashes),
            'buffer_channel_id': channel_id if isinstance(channel_id, str) and BUFFER_ID.match(channel_id) else None}
    line['payload_sha256'] = line_digest(line)
    return line


def due_instant(value):
    """The instant of a due_at, or None when it is not a real date (2026-02-30)."""
    try:
        return instant(value)
    except (ValueError, TypeError, OverflowError):
        return None


def parse_manifest(text, engine=True, bad=None):
    """The manifest's lines by slot_id. The engine's own lines must each
    recompute to their payload_sha256; Krish's amended lines are recomputed.

    A line whose due_at is shaped right but is no real date is that slot's
    problem alone: with a bad dict it is left out and recorded there as
    bad_due_at; without one it raises bad_due_at."""
    try:
        value = json.loads(text) if isinstance(text, str) else None
    except ValueError:
        value = None
    if not isinstance(value, dict) or value.get('schema') != MANIFEST_SCHEMA or not isinstance(value.get('slots'), list):
        raise ValueError('manifest_unreadable')
    lines = {}
    for line in value['slots']:
        if not isinstance(line, dict) or set(line) != LINE_KEYS:
            raise ValueError('manifest_line_malformed')
        ok = (isinstance(line['slot_id'], str) and line['slot_id'].strip() and line['channel'] in CHANNELS
              and isinstance(line['format'], str) and line['format'].strip()
              and (line['due_at'] is None or (isinstance(line['due_at'], str) and DUE_AT.match(line['due_at'])))
              and (line['link_placement'] is None or isinstance(line['link_placement'], str))
              and line['publish_mode'] in ('engine', 'krish_click')
              and isinstance(line['buffer_draft_id'], str) and BUFFER_ID.match(line['buffer_draft_id'])
              and isinstance(line['buffer_channel_id'], str) and BUFFER_ID.match(line['buffer_channel_id'])
              and (line['meta'] is None or isinstance(line['meta'], dict))
              and isinstance(line['words'], str) and line['words'].strip()
              and isinstance(line['assets'], list)
              and all(isinstance(h, str) and HEX64.match(h) for h in line['assets']))
        if not ok:
            raise ValueError('manifest_line_malformed')
        if line['slot_id'] in lines:
            raise ValueError('manifest_duplicate_slot')
        if engine and line['payload_sha256'] != line_digest(line):
            raise ValueError('manifest_line_digest_mismatch')
        if line['due_at'] is not None and due_instant(line['due_at']) is None:
            if bad is None:
                raise ValueError('bad_due_at')
            bad[line['slot_id']] = 'bad_due_at'
            continue
        lines[line['slot_id']] = line
    return lines


# Reading the go-lives back from Control Center --------------------------------

def staged_report_run_id(proposal_id, payload_sha256):
    if not isinstance(proposal_id, str) or not isinstance(payload_sha256, str) or not HEX64.match(payload_sha256):
        return None
    run_id = proposal_id + ':' + payload_sha256[:12]
    return run_id if RUN_ID.match(run_id) else None


def read_proposal(cc, proposal_id, payload_sha256):
    """(proposal, None) for exactly the version decided on, or (None, reason)."""
    run_id = staged_report_run_id(proposal_id, payload_sha256)
    if run_id is None:
        return None, 'golive_report_unaddressable'
    try:
        got = cc.read_report(run_id)
    except ProtocolError as error:
        if error.code == 'not_found':
            return None, 'golive_report_missing'
        raise
    report = got.get('report')
    if not isinstance(report, dict) or got.get('mode') != 'live' or report.get('mode') != 'live':
        return None, 'golive_report_not_live'
    try:
        sound = got.get('payload_sha256') == report.get('payload_sha256') == report_digest(report)
    except (ValueError, TypeError):
        sound = False
    if not sound:
        return None, 'golive_report_digest_mismatch'
    for item in report.get('proposals') or []:
        if isinstance(item, dict) and item.get('proposal_id') == proposal_id \
                and item.get('payload_sha256') == payload_sha256:
            return item, None
    return None, 'golive_not_in_report'


def golive_ended(pid, now):
    """True when the run a go-live id names has ended, so every due_at in it has passed
    and the go-live is expired: it is skipped before it costs a read."""
    window = run_window(pid)
    return now is not None and window is not None and window[1] <= instant(now)


def signed_golives(cc, decisions, holds, now=None):
    """The staged proposals the go-live review needs, read back by digest.

    Reads are capped at MAX_REPORT_READS, so their order matters: declined
    check-ins first (an unknown stop holds everything), then approved go-lives
    newest first by decision time, each with its plan. A go-live whose run has
    ended is skipped before it uses a read, so old ones never starve a new one."""
    latest, _ = _latest(decisions)
    approved = [(_decided_at(d), pid) for pid, d in latest.items()
                if d.get('stage') == 'go_live' and d.get('decision') == 'approved']
    wanted = [(pid, latest[pid]['payload_sha256']) for _, pid in sorted(approved, reverse=True)]
    found, reads = {}, 0

    def fetch(pid, sha, code_prefix):
        nonlocal reads
        if reads >= MAX_REPORT_READS:
            holds[code_prefix + 'too_many_reads'] = holds.get(code_prefix + 'too_many_reads', 0) + 1
            return None
        reads += 1
        item, reason = read_proposal(cc, pid, sha)
        if reason:
            code = reason if code_prefix == '' else code_prefix + reason.replace('golive_', '')
            holds[code] = holds.get(code, 0) + 1
        return item

    for d in decisions or []:
        if isinstance(d, dict) and d.get('decision') == 'declined' and d.get('stage') == 'check_in' \
                and d.get('proposal_id') not in found and isinstance(d.get('payload_sha256'), str):
            item = fetch(d['proposal_id'], d['payload_sha256'], 'check_in_')
            if item is not None:
                found[d['proposal_id']] = item
    for pid, sha in wanted:
        if golive_ended(pid, now):
            holds['golive_ended_unread'] = holds.get('golive_ended_unread', 0) + 1
            continue
        item = fetch(pid, sha, '')
        if item is None or item.get('stage') != 'go_live':
            continue
        found[pid] = item
        parent = item.get('parent_proposal_id')
        plan_decision = latest.get(parent) if isinstance(parent, str) else None
        if parent not in found and plan_decision and plan_decision.get('payload_sha256'):
            plan = fetch(parent, plan_decision['payload_sha256'], 'plan_')
            if plan is not None:
                found[parent] = plan
    return list(found.values())


def _version(decision):
    amended = decision.get('amended') is True
    return decision.get('payload_sha256'), decision.get('amended_sha256') if amended else None


def revoked_versions(decisions):
    """Earlier approvals of a go-live that no longer stand, newest first: the
    latest decision on it is not an approval, or approves another version."""
    by_pid = {}
    for index, d in enumerate(decisions or []):
        if not isinstance(d, dict) or d.get('stage') != 'go_live' or not isinstance(d.get('proposal_id'), str):
            continue
        at = _decided_at(d)
        if at is not None:
            by_pid.setdefault(d['proposal_id'], []).append(((at, index), d))
    out = []
    for pid, rows in by_pid.items():
        rows.sort(key=lambda row: row[0])
        latest = rows[-1][1]
        current = _version(latest) if latest.get('decision') == 'approved' else None
        seen = set()
        for key, d in rows[:-1]:
            version = _version(d)
            if d.get('decision') != 'approved' or version == current or version in seen \
                    or not isinstance(d.get('payload_sha256'), str):
                continue
            seen.add(version)
            out.append((key, pid, d))
    return [(pid, d) for _, pid, d in sorted(out, key=lambda row: row[0], reverse=True)]


# One slot ------------------------------------------------------------------------

class Run:
    def __init__(self, buffer, now, deliver, fetch, root=None, clock=None):
        self.buffer = buffer
        self.now = instant(now)
        # The clock is read again before each margin check: downloads take time.
        self.clock = clock or (lambda: self.now)
        self.deliver = deliver
        self.fetch = fetch
        self.root = root
        self.slots = {}
        self.holds = {}
        self.loud = []
        self.signed = {}  # buffer_draft_id -> the engine line a standing approval signs for it
        self.alarm_checked = set()

    def count(self, outcome):
        self.slots[outcome] = self.slots.get(outcome, 0) + 1

    def hold(self, code, loud=False):
        self.count('held')
        self.holds[code] = self.holds.get(code, 0) + 1
        if loud:
            self.loud.append(code)

    def _matches(self, post, signed):
        """The full rebuilt digest (words, channel, Buffer account, asset bytes and
        meta) and, when scheduled, the time: never words and time alone. A post that
        is not the signed format never matches."""
        try:
            rebuilt = draft_line(post, signed, self.fetch)
        except CarryHold:
            return False
        if rebuilt['payload_sha256'] != line_digest(signed):
            return False
        if post.get('status') == 'scheduled':
            due = due_instant(post.get('dueAt'))
            return due is not None and due == due_instant(signed['due_at'])
        return True

    def _rebuilt_digest(self, post, engine_line):
        """The line the draft makes now (its payload_sha256 is the rebuilt digest)."""
        rebuilt = draft_line(post, engine_line, self.fetch)
        if len(rebuilt['assets']) != len(engine_line['assets']):
            raise CarryHold('asset_count_differs')
        return rebuilt

    def _readback_ok(self, back, post, signed, rebuilt):
        """The readback after the edit: scheduled at the signed time, in the signed
        words, on the same channel, the same asset sources and the signed meta."""
        if back.get('status') != 'scheduled' or back.get('text') != signed['words']:
            return False
        due = due_instant(back.get('dueAt'))
        if due is None or due != due_instant(signed['due_at']) or back.get('channelId') != post.get('channelId'):
            return False
        if asset_sources(back) != asset_sources(post):
            return False
        return buffer_api.signed_meta(back, rebuilt['assets']) == rebuilt['meta']

    def _read(self, post_id):
        try:
            return self.buffer.get_post(post_id), None
        except BufferAuthError:
            raise
        except BufferError as error:
            return None, error.code

    def slot(self, signed, engine_line, golive_decision, window=None):
        """Release one signed line, or count why not. window is the (start, end) of the
        run its go-live names: a due_at outside it (his amended time too) holds."""
        if engine_line is None:
            return self.hold('amended_slot_unknown')
        changed = {k for k in LINE_KEYS if signed[k] != engine_line[k]} - AMENDABLE
        if changed:
            return self.hold('amendment_not_releasable')
        if engine_line['publish_mode'] == 'krish_click' and signed['publish_mode'] != 'krish_click':
            return self.hold('amendment_not_releasable')
        if not may_release(signed, golive_decision, None, today(self.now), self.root):
            return self.hold('not_signed')
        if signed['channel'] in KRISH_CLICK_ONLY or signed['publish_mode'] == 'krish_click':
            return self.count('krish_click')  # LinkedIn and every krish_click slot stay drafts; no call at all.
        if signed['due_at'] is None:
            return self.hold('no_due_at')
        due = due_instant(signed['due_at'])
        if due is None:
            return self.hold('bad_due_at')
        if window is not None and not window[0] <= due < window[1]:
            return self.hold('due_outside_run_window')  # F108: the handoff's check, on his amended time too
        self.signed[signed['buffer_draft_id']] = signed
        if due - self.clock() > SCHEDULE_WINDOW:
            # Further out it stays a draft with no read and no edit: a No, an
            # amendment or a changed file before then stops it.
            return self.count('not_yet_due')
        # Main's walls, as `run release` holds them (R95, R99): a route not yet
        # verified and fresh in social/tools/buffer.json releases only its one
        # capability check, which goes through `run release` on the Monday he
        # approves it; here it holds until the route is recorded as passed. A
        # snackable post never asks for the share.
        unverified, _, _ = route_holds(signed, instant(self.now).date().isoformat())
        if unverified:
            return self.hold('route_not_verified')
        if share_ask_errors(signed, signed['words']):
            return self.hold('share_ask_refused')
        post, code = self._read(signed['buffer_draft_id'])
        if code:
            return self.hold(code)
        service = CHANNELS[signed['channel']][0]
        if post.get('via') == 'network':
            return self.hold('imported_post')
        if post.get('channelService') != service:
            return self.hold('draft_on_another_service')
        if account_hold(signed['channel'], post) or post.get('channelId') != signed['buffer_channel_id']:
            return self.hold('wrong_account')
        status = post.get('status')
        if status in ('scheduled', 'sent'):
            try:
                same = self._matches(post, signed)
            except BufferAuthError:
                raise
            except BufferError as error:
                return self.hold(error.code if error.code.startswith('asset_') else 'asset_download_failed')
            if same:
                return self.count('already_' + status)
            return self.hold('live_post_differs_from_signed', loud=True)
        if status != 'draft':
            return self.hold({'sending': 'still_sending', 'error': 'buffer_post_error',
                              'needs_approval': 'needs_approval'}.get(status, 'unknown_status'))
        if due - self.clock() <= DUE_MARGIN:
            return self.hold('due_time_passed', loud=True)
        try:
            rebuilt = self._rebuilt_digest(post, engine_line)
            if rebuilt['payload_sha256'] != engine_line['payload_sha256']:
                return self.hold('draft_differs_from_signed')
            buffer_api.edit_input(post, signed['due_at'], signed['words'])
        except CarryHold as hold:
            return self.hold(hold.code)
        except BufferAuthError:
            raise
        except BufferError as error:
            return self.hold(error.code if error.code.startswith('asset_') else 'asset_download_failed')
        if due - self.clock() <= DUE_MARGIN:
            return self.hold('due_time_passed', loud=True)
        if not self.deliver:
            return self.count('would_schedule')
        try:
            self.buffer.schedule_draft(post, signed['due_at'], signed['words'])
        except BufferAuthError:
            raise
        except (BufferError, CarryHold) as error:
            # Read back once: an uncertain edit may have landed. Never resend.
            code = getattr(error, 'code', 'edit_failed')
            again, failed = self._read(post['id'])
            if failed:
                return self.hold('uncertain_edit', loud=True)
            if self._readback_ok(again, post, signed, rebuilt):
                return self.count('scheduled')
            if again.get('status') != 'draft':
                return self.hold('uncertain_edit', loud=True)
            return self.hold(code)
        back, failed = self._read(post['id'])
        if failed:
            return self.hold('readback_failed', loud=True)
        if not self._readback_ok(back, post, signed, rebuilt):
            return self.hold('readback_mismatch', loud=True)
        return self.count('scheduled')

    def golive(self, action, proposal):
        """Every line of one approved go-live. Lines he dropped are never touched."""
        bad = {}
        try:
            engine_lines = parse_manifest(proposal.get('exact_payload'), engine=True, bad=bad)
            signed_lines = (parse_manifest(action['exact_payload'], engine=False, bad=bad) if action['amended']
                            else engine_lines)
        except ValueError as error:
            return self.hold(str(error))
        decision = {'decision': 'approved', 'stage': 'go_live'}
        window = run_window(action['proposal_id'])
        for sid in sorted(bad):
            self.hold(bad[sid])
        for sid in sorted(engine_lines):
            if sid not in signed_lines and sid not in bad:
                self.count('unsigned')
        for sid in sorted(signed_lines):
            if sid not in bad:
                self.slot(signed_lines[sid], engine_lines.get(sid), decision, window)

    def check_scheduled(self, line):
        """The alarm for one line of a yes that no longer stands: its draft must
        not be scheduled unless exactly as the standing approval signs it."""
        draft = line['buffer_draft_id']
        if draft in self.alarm_checked:
            return
        self.alarm_checked.add(draft)
        post, code = self._read(draft)
        if code:
            self.holds['revoked_unreadable'] = self.holds.get('revoked_unreadable', 0) + 1
            self.loud.append('revoked_unreadable')
            return
        self.alarm(post)

    def sweep_scheduled(self, organizations):
        """While a stop or a read cannot be told (F103), every post scheduled on this
        engine's own channels (the pinned ids, LinkedIn aside: it is only ever his click)
        that no standing signed line of this run matches exactly is reported loudly as
        scheduled_after_decline. Lists only; never unschedules."""
        pinned = sorted(cid for channel, cid in BUFFER_CHANNEL_ID.items() if channel not in KRISH_CLICK_ONLY)
        posts = {}
        try:
            for organization in organizations:
                for post in self.buffer.list_posts(organization, ['scheduled', 'sending'], pinned):
                    if isinstance(post, dict) and post.get('channelId') in pinned and isinstance(post.get('id'), str):
                        posts[post['id']] = post
        except BufferAuthError:
            raise
        except BufferError:
            self.holds['scheduled_unlisted'] = self.holds.get('scheduled_unlisted', 0) + 1
            self.loud.append('scheduled_unlisted')
            return
        for post_id in sorted(posts):
            if post_id not in self.alarm_checked:
                self.alarm_checked.add(post_id)
                self.alarm(posts[post_id])

    def alarm(self, post):
        """Loud unless the post is not scheduled, or is exactly what a standing yes signs."""
        draft = post.get('id')
        if post.get('status') not in ('scheduled', 'sending'):
            return
        current = self.signed.get(draft)
        if current is not None and post.get('status') == 'scheduled':
            try:
                if self._matches(post, current):
                    return
            except BufferAuthError:
                raise
            except BufferError:
                pass
        self.holds['scheduled_after_decline'] = self.holds.get('scheduled_after_decline', 0) + 1
        self.loud.append('scheduled_after_decline')


def check_revoked(cc, run, decisions, stopped, now, held):
    """Every yes that no longer stands, and every go-live whose plan was stopped:
    report loudly each of their drafts that is still scheduled. Never unschedules."""
    reads = 0
    for pid, decision, item in [(pid, d, None) for pid, d in revoked_versions(decisions)] + list(stopped):
        if golive_ended(pid, now):
            continue
        if item is None:
            if reads >= MAX_ALARM_READS:
                held['revoked_too_many_reads'] = held.get('revoked_too_many_reads', 0) + 1
                run.loud.append('revoked_unchecked')
                continue
            reads += 1
            item, reason = read_proposal(cc, pid, decision['payload_sha256'])
            if item is None:
                code = 'revoked_' + reason.replace('golive_', '')
                held[code] = held.get(code, 0) + 1
                run.loud.append('revoked_unchecked')
                continue
        amended = decision.get('amended') is True
        if amended and not amendment_ok(decision):
            continue  # an amendment that never recomputed never acted
        try:
            lines = parse_manifest(decision.get('exact_payload') if amended else item.get('exact_payload'),
                                   engine=not amended, bad={})
        except ValueError:
            held['revoked_manifest_unreadable'] = held.get('revoked_manifest_unreadable', 0) + 1
            run.loud.append('revoked_unchecked')
            continue
        for line in lines.values():
            if line['publish_mode'] == 'engine' and line['channel'] not in KRISH_CLICK_ONLY:
                run.check_scheduled(line)


# The run ----------------------------------------------------------------------------

class Unpaged(Exception):
    """Krish's decisions did not page out within the cap: nothing is read as complete."""


def autorelease(cc, buffer, now=None, deliver=False, fetch=None, state_root=None, root=None, clock=None):
    """Returns (summary, exit_code). summary holds counts and codes only.

    now fixes the clock (tests, --now); without it the clock is read again
    before each slot's margin check."""
    if clock is None:
        clock = (lambda: instant(now)) if now is not None else (lambda: instant(None))
    now = clock()
    fetch = fetch or (lambda url: buffer_api.download_sha256(url))
    summary = {'lane': 'L0', 'command': 'autorelease', 'deliver': bool(deliver), 'decisions_read': 0,
               'golives': {'releasable': 0, 'held': {}}, 'slots': {}, 'holds': {}, 'mutations': 0,
               'loud': [], 'error': None}
    run = Run(buffer, now, deliver, fetch, root, clock)
    folder = None
    try:
        organizations = buffer.account_check().get('organization_ids') or []
        if state_root is None:
            folder = tempfile.TemporaryDirectory()
            state_root = folder.name
        since = min(decisions_since(state_root, now), now - LOOKBACK)
        # Control Center serves 100 decisions a read, the oldest first: every page, or nothing (F100).
        decisions = decisions_paged(cc, since)
        if decisions is None:
            raise Unpaged()
        summary['decisions_read'] = len(decisions)
        held = summary['golives']['held']
        proposals = signed_golives(cc, decisions, held, now)
        review = claim_golives(state_root, proposals, decisions, now)
        for item in review['holds']:
            held[item['reason']] = held.get(item['reason'], 0) + 1
        by_id = {p['proposal_id']: p for p in proposals}
        summary['golives']['releasable'] = len(review['actions'])
        for action in review['actions']:
            run.golive(action, by_id[action['proposal_id']])
        latest, _ = _latest(decisions)
        stopped = [(item['proposal_id'], latest[item['proposal_id']], by_id[item['proposal_id']])
                   for item in review['holds'] if item['reason'] == 'plan_stopped'
                   and item['proposal_id'] in by_id and item['proposal_id'] in latest]
        check_revoked(cc, run, decisions, stopped, now, held)
        # F103: a stop or a read that cannot be told is loud, and then every post scheduled
        # on this engine's channels that no standing signed line matches is listed loudly.
        if review['unresolved'] and 'stop_unresolved' not in held:
            held['stop_unresolved'] = 1
        unknown = sorted(code for code in held if code in UNKNOWN_HOLDS or code.endswith('too_many_reads'))
        run.loud += unknown
        if unknown or 'revoked_unchecked' in run.loud:
            run.sweep_scheduled(organizations)
    except BufferAuthError as error:
        summary['error'] = error.code
    except BufferError as error:
        summary['error'] = error.code
    except ProtocolError as error:
        summary['error'] = 'control_center_' + error.code
    except Unpaged:
        summary['error'] = 'decisions_unpaged'
    finally:
        if folder is not None:
            folder.cleanup()
    summary.update(slots=dict(sorted(run.slots.items())), holds=dict(sorted(run.holds.items())),
                   mutations=buffer.mutations, loud=sorted(set(run.loud)))
    summary['golives']['held'] = dict(sorted(summary['golives']['held'].items()))
    code = 1 if summary['error'] or summary['loud'] else 0
    summary['exit'] = code
    return summary, code


CC_TOKEN_ENV = 'CONTROL_CENTER_ENGINE_TOKEN'


def _cc_client():
    key = ''
    # Only the engine's own bearer. cc_loop.SECRET_ENV lists every secret name
    # for redaction (it includes BUFFER_API_KEY), so it must never pick the key.
    key = os.environ.get(CC_TOKEN_ENV, '').strip()
    if not key:
        raise ProtocolError('missing_token')
    return Client(key, os.environ.get('CONTROL_CENTER_URL', '').strip() or APPROVED_ORIGIN)


def _buffer_client():
    return Buffer(os.environ.get(BUFFER_KEY_ENV, '').strip())


def main(argv=None, make_cc=None, make_buffer=None, fetch=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['autorelease']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run autorelease', description=__doc__.split('\n')[0])
    parser.add_argument('--deliver', action='store_true', help='schedule in Buffer; without it, a dry run')
    parser.add_argument('--now', help='a fixed clock, for tests')
    parser.add_argument('--state', help='a folder for the claim ledger, for tests; default a throwaway one (Buffer is '
                        'the ledger). A kept ledger claims a go-live once, so a slot not yet due then never releases')
    args = parser.parse_args(argv)
    summary = {'lane': 'L0', 'command': 'autorelease', 'deliver': args.deliver}
    try:
        buffer = (make_buffer or _buffer_client)()
    except BufferError as error:
        summary.update(error=error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    try:
        cc = (make_cc or _cc_client)()
    except ProtocolError as error:
        summary.update(error='control_center_' + error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    result, code = autorelease(cc, buffer, args.now, args.deliver, fetch, args.state)
    out(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
