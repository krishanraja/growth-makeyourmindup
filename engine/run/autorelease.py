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
   the signed words counts as done, so a second run is a no-op.
6. The go-live ledger (F114). The claim ledger cc_loop.claim_golives reads
   lives in a throwaway folder unless --state names one, so it is seeded
   each run from Control Center (seed_claims): once every line a go-live
   signs is done, the run reports a claim (record_claim) and every later run
   only checks that go-live's posts, never schedules one again. A go-live he
   approved that names lines on more than one New York day holds as
   `golive_spans_days` (R94, F111).
7. Posts made from the week's mix (Ruling, Krish, 2026-10-30: "approve the
   week's mix once, let Growth fill it"; docs/CONCEPT-MANIFEST.md, On GitHub
   Actions). Each one the handoff indexed for today or the window is read
   back by its exact payload_sha256 (its review record), and its week's
   authority from Control Center and the board (week_state: the plan in
   force read by digest, his stops through engine/run/decision.py
   cc_readback, and mix_binding: his one press on content-engine's board,
   approved on the hash of the mix Growth proposes from that same plan).
   A post outside that mix (its day, its concept among that day's options,
   its channel:format in the option's format line) holds as
   outside_approved_mix, loud as scheduled_outside_mix when already live.
   Then Run.derived calls release's own checks and schedules it like a
   go-live line. No press holds quietly (mix_not_approved); a press on
   another hash holds loudly (mix_hash_mismatch) and the summary carries
   the mix to propose again. A concept_hold or an unresolved stop holds
   every such post loudly; a post from a plan he declined that is still
   scheduled is loud as scheduled_after_decline.

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

from engine import concepts as concept_rules, intensity, mix as mix_rules
from engine.cc_loop import (GOLIVE_LEDGER, claim_golives, decisions_paged, decisions_since, golive_ledger,
                            record_stops, revision, state_path)
from engine.control_center import (APPROVED_ORIGIN, RUN_ID, TIMEZONE, Client, ProtocolError, _decided_at, _latest,
                                   action_key, amendment_ok, golive_review, payload_digest, report_digest)
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.core import locked, write_json
from engine.core import calendar_date, instant, ny_time, read_json, today
from engine.run import buffer_api
from engine.run.buffer_api import Buffer, BufferAuthError, BufferError, CarryHold
from engine.run import cc_records, decision as decide, release
from engine.run.release import (BUFFER_ID, CHANNELS, DUE_AT, HEX64, KRISH_CLICK_ONLY, LINE_DOMAIN, account_hold,
                                format_shape_errors, route_holds, share_ask_errors, slot_digest)
from engine.run.spec import LENGTH, ny_midnight
from engine.social import inventory

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
# A line in one of these is done: its go-live is claimed once every line it signs is (cc_records.CLAIM).
DONE = ('scheduled', 'already_scheduled', 'already_sent', 'krish_click', 'unsigned')
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
    """The instant of a due_at, or None when it is not a real date (2026-02-30) or is missing (never now)."""
    if value is None:
        return None
    try:
        return instant(value)
    except (ValueError, TypeError, OverflowError):
        return None


def spans_days(*manifests):
    """The New York days the engine lines of these manifests go out on (lines with no time ride along)."""
    days = set()
    for lines in manifests:
        for line in lines.values():
            due = due_instant(line['due_at']) if line['publish_mode'] == 'engine' and line['due_at'] else None
            if due is not None:
                days.add(ny_time(due).date())
    return sorted(days)


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
        self.organizations = []
        self.caps = {}  # channel -> posts a New York day (release.concept_caps)
        self.per_day = {}  # (channel, New York day) -> posts scheduled on it, read from Buffer (F117)

    def count(self, outcome):
        self.slots[outcome] = self.slots.get(outcome, 0) + 1
        return outcome

    def hold(self, code, loud=False):
        self.count('held')
        self.holds[code] = self.holds.get(code, 0) + 1
        if loud:
            self.loud.append(code)
        return 'held'

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

    def stopped(self, draft_id, state):
        """A post of a week he said no to, read from Buffer by its draft id alone (no review needed): one still
        scheduled, or sent after his no, is loud (never unscheduled); one that cannot be read is loud too."""
        post, code = self._read(draft_id)
        if code:
            return self.hold(code, loud=True)
        status = post.get('status')
        if status in ('scheduled', 'sending'):
            return self.hold('scheduled_after_decline', loud=True)
        if status == 'sent':
            went = due_instant(post.get('sentAt')) or due_instant(post.get('dueAt'))
            at = state.get('stopped_at')
            if went is None or at is None or went >= at:
                return self.hold('sent_after_decline', loud=True)
        return self.hold(concept_rules.STOPPED)

    def _read(self, post_id):
        try:
            return self.buffer.get_post(post_id), None
        except BufferAuthError:
            raise
        except BufferError as error:
            return None, error.code

    def slot(self, signed, engine_line, golive_decision, window=None, acted=False):
        """Release one signed line, or count why not. window is the (start, end) of the
        run its go-live names: a due_at outside it (his amended time too) holds. acted: its
        go-live is claimed (it acted once), so the line is only checked, never scheduled again."""
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
        if acted:
            return self.hold('acted_once_now_a_draft')  # a go-live acts once: never scheduled a second time
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

    def golive(self, action, proposal, acted=False):
        """Every line of one approved go-live. Lines he dropped are never touched. Returns each line's
        outcome: when every one is done (scheduled, already scheduled or sent, his own click, or
        dropped) the go-live is claimed in Control Center and never acted on again (record_claim)."""
        bad = {}
        try:
            engine_lines = parse_manifest(proposal.get('exact_payload'), engine=True, bad=bad)
            signed_lines = (parse_manifest(action['exact_payload'], engine=False, bad=bad) if action['amended']
                            else engine_lines)
        except ValueError as error:
            return [self.hold(str(error))]
        if len(spans_days(signed_lines)) > 1:
            # R94 (F111): approving a day authorises exactly that day's posts. A go-live he approved that
            # names lines on more than one New York day (built before the handoff made one per day) never acts.
            return [self.hold('golive_spans_days') for _ in signed_lines]
        decision = {'decision': 'approved', 'stage': 'go_live'}
        window = run_window(action['proposal_id'])
        outcomes = []
        for sid in sorted(bad):
            outcomes.append(self.hold(bad[sid]))
        for sid in sorted(engine_lines):
            if sid not in signed_lines and sid not in bad:
                outcomes.append(self.count('unsigned'))
        for sid in sorted(signed_lines):
            if sid not in bad:
                outcomes.append(self.slot(signed_lines[sid], engine_lines.get(sid), decision, window, acted))
        return outcomes

    def day_count(self, channel, day):
        """Every post scheduled, sending or sent on this engine's own channel that New York day, read from
        Buffer once a run, plus each line a standing go-live signs for that day not yet scheduled, so a
        concept post never takes the place of a post he signed one by one (F117)."""
        key = (channel, day)
        if key not in self.per_day:
            pinned = BUFFER_CHANNEL_ID[channel]
            start = ny_midnight(calendar_date(day))
            seen = set()
            for organization in self.organizations:
                for post in self.buffer.list_posts(organization, ['scheduled', 'sending', 'sent'], [pinned],
                                                   start.isoformat()):
                    due = due_instant(post.get('dueAt')) if isinstance(post, dict) else None
                    if post.get('channelId') == pinned and due is not None and ny_time(due).date().isoformat() == day:
                        seen.add(post.get('id'))
            reserved = {draft for draft, line in self.signed.items() if line['channel'] == channel
                        and line['due_at'] and due_instant(line['due_at']) is not None
                        and ny_time(due_instant(line['due_at'])).date().isoformat() == day}
            self.per_day[key] = len(seen | reserved)
        return self.per_day

    def derived(self, fields, review, state):
        """Schedule one post made from a concept Krish approved in the week's mix plan, or count why not.

        fields and review are read back from Control Center by the post's exact payload_sha256
        (review_of); state is week_state's. In order: the week's holds (loud); then, from the
        draft read fresh, release's own concept checks (engine/concepts.py authority: placement,
        mock files, the claim word for word, not stopped; release.concept_post_hold: the review
        at this payload judged by spec.review_reason, the New York daily cap counted from
        Buffer; copy lint, share asks, the route, the channel lock), called, never copied; then
        the draft digest, meta, account, format shape and the 5 to 90 minute window."""
        if state.get('hold'):
            return self.hold(state['hold'], loud=state.get('loud', False))
        if state.get('stopped'):
            # His no on the mix plan, read before every other gate (S3).
            return self.stopped(fields['buffer_draft_id'], state)
        due = due_instant(fields['due_at'])
        if due is None:
            return self.hold('bad_due_at')
        if due - self.clock() > SCHEDULE_WINDOW:
            return self.count('not_yet_due')
        if fields['channel'] not in concept_rules.CONCEPT_CHANNELS or fields['publish_mode'] != 'engine':
            return self.hold(concept_rules.DEPARTS)
        unverified, _, _ = route_holds(fields, instant(self.now).date().isoformat())
        if unverified:
            return self.hold('route_not_verified')
        post, code = self._read(fields['buffer_draft_id'])
        if code:
            return self.hold(code)
        if post.get('via') == 'network':
            return self.hold('imported_post')
        if post.get('channelService') != CHANNELS[fields['channel']][0]:
            return self.hold('draft_on_another_service')
        if account_hold(fields['channel'], post):
            return self.hold('wrong_account')
        status = post.get('status')
        live = status in ('scheduled', 'sending', 'sent')
        if not live and status != 'draft':
            return self.hold({'error': 'buffer_post_error', 'needs_approval': 'needs_approval'}.get(status,
                                                                                                  'unknown_status'))
        if outside_mix(state, fields['concept_id'], fields['channel'], fields['format'], due):
            # Nothing outside the mix he approved on the board goes out (Ruling, Krish, 2026-10-30).
            return self.hold('scheduled_outside_mix' if live else 'outside_approved_mix', loud=live)
        line_fields = {key: fields[key] for key in ('slot_id', 'format', 'due_at', 'link_placement', 'publish_mode',
                                                    'buffer_draft_id')}
        try:
            line = draft_line(post, line_fields, self.fetch)
        except CarryHold as hold:
            return self.hold(hold.code)
        except BufferAuthError:
            raise
        except BufferError as error:
            return self.hold(error.code if error.code.startswith('asset_') else 'asset_download_failed')
        if len(fields['asset_names']) != len(line['assets']) or line['channel'] != fields['channel']:
            return self.hold('asset_count_differs')
        slot = {'slot_id': fields['slot_id'], 'channel': line['channel'], 'format': fields['format'],
                'due_at': fields['due_at'], 'words': line['words'], 'link_placement': fields['link_placement'],
                'publish_mode': fields['publish_mode'], 'concept_id': fields['concept_id'], 'share': fields['share'],
                'assets': [{'name': name, 'sha256': digest} for name, digest in zip(fields['asset_names'],
                                                                                   line['assets'])],
                'payload_sha256': spec_digest(line)}
        spec = dict(state['spec'], slots=[slot])
        formats = inventory(self.root or ROOT)['format']
        _, reasons = release.authorised_digests(spec, state['decision'], {}, state['stopped_proposals'], (), formats)
        snack = release.snackable_formats()
        day = ny_time(due).date().isoformat()
        why = reasons.get(slot['slot_id'])
        if why is None:
            # The cap counts this post's own day from Buffer; a post already out is counted in it.
            why = release.concept_post_hold(slot, state['decision'], review, {} if live else self.caps,
                                            {} if live else self.day_count(slot['channel'], day), snack)
            if live and why and why.startswith('concept_daily_cap_unknown'):
                why = None
        if live:
            if why or spec_digest(line) != fields['payload_sha256']:
                return self.hold('scheduled_after_decline' if why else 'live_post_differs_from_signed', loud=True)
            if status == 'scheduled' and due_instant(post.get('dueAt')) != due:
                return self.hold('live_post_differs_from_signed', loud=True)
            self.signed[fields['buffer_draft_id']] = line
            return self.count('already_' + ('scheduled' if status in ('scheduled', 'sending') else 'sent'))
        if why:
            return self.hold(why.split(':')[0])
        if release.copy_errors(slot['words']):
            return self.hold('copy_lint_refused')
        if share_ask_errors(slot, slot['words'], snack):
            return self.hold('share_ask_refused')
        if spec_digest(line) != fields['payload_sha256']:
            return self.hold('draft_differs_from_signed')
        try:
            buffer_api.edit_input(post, fields['due_at'], line['words'])
        except CarryHold as hold:
            return self.hold(hold.code)
        if due - self.clock() <= DUE_MARGIN:
            return self.hold('due_time_passed', loud=True)
        if not self.deliver:
            self.per_day[(slot['channel'], day)] += 1
            return self.count('would_schedule')
        signed = {'words': line['words'], 'due_at': fields['due_at']}
        try:
            self.buffer.schedule_draft(post, fields['due_at'], line['words'])
        except BufferAuthError:
            raise
        except (BufferError, CarryHold) as error:
            code = getattr(error, 'code', 'edit_failed')
            again, failed = self._read(post['id'])
            if failed:
                return self.hold('uncertain_edit', loud=True)
            if self._readback_ok(again, post, signed, line):
                self.per_day[(slot['channel'], day)] += 1
                self.signed[fields['buffer_draft_id']] = line
                return self.count('scheduled')
            if again.get('status') != 'draft':
                return self.hold('uncertain_edit', loud=True)
            return self.hold(code)
        back, failed = self._read(post['id'])
        if failed:
            return self.hold('readback_failed', loud=True)
        if not self._readback_ok(back, post, signed, line):
            return self.hold('readback_mismatch', loud=True)
        self.per_day[(slot['channel'], day)] += 1
        self.signed[fields['buffer_draft_id']] = line
        return self.count('scheduled')

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


# The go-live ledger, kept in Control Center -----------------------------------------------

def seed_claims(cc, state_root, proposals, decisions, now):
    """Read back, by their exact run_id, the go-lives this lane already finished acting on, into the
    local ledger engine.cc_loop.claim_golives reads, so each acts once across clean runners.

    Only a go-live that could act now is looked up (golive_review, pure), so old ones cost
    no read. The claim is kept per go-live (cc_records.claim_run_id), so one claimed under
    an earlier decision is found under any later one: each acts once, whatever is approved
    on it later (control_center.golive_review). A claim that cannot be read fails the run
    (Control Center errors propagate)."""
    review = golive_review(proposals, decisions, golive_ledger(state_root), now)
    found = {}
    for action in review['actions']:
        record = cc_records.read_record(cc, cc_records.claim_run_id(action['proposal_id']), cc_records.CLAIM)
        if record is None:
            continue
        key = record.get('action_key')
        if record.get('proposal_id') != action['proposal_id'] or not isinstance(key, str) \
                or not key.startswith(action['proposal_id'] + '#'):
            raise ValueError('claim_mismatch')
        found[key] = {k: record.get(k) for k in ('proposal_id', 'parent_proposal_id', 'action_sha256', 'amended',
                                                 'decided_at', 'claimed_at')}
    if found:
        path = state_path(state_root, GOLIVE_LEDGER)
        with locked(path):
            ledger = golive_ledger(state_root)
            ledger['acted'].update(found)
            write_json(path, {key: dict(sorted(ledger[key].items())) for key in ('acted', 'stopped', 'unresolved')})
    return len(found)


def acted_action(proposal, decision):
    """The version of a claimed go-live his latest decision stands on, as golive() reads an action, or None.

    A claimed go-live acts once: its lines are only checked each run (a scheduled post that drifts
    from what he signed is loud, and the alarm knows his posts), never scheduled again."""
    if not isinstance(decision, dict) or decision.get('decision') != 'approved':
        return None
    amended = decision.get('amended') is True
    if amended and not amendment_ok(decision):
        return None
    return {'proposal_id': proposal['proposal_id'], 'amended': amended,
            'exact_payload': decision.get('exact_payload') if amended else proposal.get('exact_payload')}


def record_claim(cc, action, now, root, outcomes):
    """Report that this lane finished one go-live (every line it signs done), at its claim run_id.

    A conflict reads back: the same claim already there counts. Codes only in the words."""
    key = action_key(action)
    record = {'schema': cc_records.CLAIM, 'action_key': key, 'proposal_id': action['proposal_id'],
              'parent_proposal_id': action['parent_proposal_id'], 'action_sha256': action['action_sha256'],
              'amended': action['amended'], 'decided_at': action['decided_at'], 'claimed_at': instant(now).isoformat(),
              'outcomes': dict(sorted(outcomes.items()))}
    report = cc_records.record_report(cc_records.claim_run_id(action['proposal_id']), cc_records.CLAIM, record,
                                      ['Go-live acted on once: every line it signs is scheduled, sent or his click',
                                       'Scheduled only what Krish approved; published, sent and spent nothing'],
                                      now, revision(root or ROOT))
    posted = cc.post_report(report)
    if posted['accepted']:
        return True
    stored = cc_records.read_record(cc, report['run_id'], cc_records.CLAIM)
    # Any claim already there for this go-live counts: it has acted, under whichever decision.
    return isinstance(stored, dict) and stored.get('proposal_id') == action['proposal_id']


# Posts made from an approved concept (the mix plan) -----------------------------------------

MAX_DERIVED = 40  # derived slots read in one run; past it the run is loud (derived_too_many_reads)
MAX_NUMBERED = 24  # day indexes and plan versions probed
# Week-level holds: each is loud (exit 1, GitHub emails him) and holds every derived slot of the week.
LOUD_CONCEPT = ('concept_hold', 'concept_stop_unresolved')
REVIEW_SLOT_KEYS = frozenset({'slot_id', 'channel', 'format', 'due_at', 'link_placement', 'publish_mode',
                              'buffer_draft_id', 'concept_id', 'share', 'asset_names'})


def week_of(due):
    day = ny_time(due).date()
    return (day - dt.timedelta(days=day.weekday())).isoformat()


def _week_label(monday):
    return mix_rules.proposal_id(monday).rsplit(':', 1)[1]


def _held(code, why, loud=True):
    return {'hold': code, 'why': why, 'loud': loud}


def read_part(cc, proposal_id, payload_sha256):
    """(proposal, record) for one plan part, read back from its own report by digest (as a go-live is)."""
    run_id = staged_report_run_id(proposal_id, payload_sha256)
    report = cc_records.read_report(cc, run_id) if run_id else None
    if report is None:
        return None, None
    for item in report.get('proposals') or []:
        if isinstance(item, dict) and item.get('proposal_id') == proposal_id \
                and item.get('payload_sha256') == payload_sha256:
            return item, cc_records.record_of(report, cc_records.PART)
    return None, None


def _why_code(why):
    """A reason code for why decision.judge recorded nothing: codes only ever reach the log."""
    head = str(why).split(':')[0]
    if re.match(r'^[a-z_]{1,40}$', head):
        return head
    for start, code in (('no decision on', 'no_decision'), ('the latest decision on', 'not_approved'),
                        ('a decision on', 'undated_decision')):
        if str(why).startswith(start):
            return code
    return 'not_applied'


def week_state(cc, monday, decisions, state_root, now, root, proposals=(), board=None):
    """What the week's mix authorises: the concept part of a decision (decision.concept_part, engine/run/
    decision.py's own rules), a synthetic spec carrying the approved concepts for release's checks, the
    stops and the mix binding; or a hold. Never a local file.

    The plan in force is its highest numbered version record. Every decision, stop and decline is read
    first: his no on any part stops the week before any part is trusted, and decision.cc_readback still
    reads his stops, amended-away concepts and changed terms. Since 30 October the approval itself is his
    one press on the board's mix (mix_binding), bound to the hash of the mix Growth proposes from this
    same plan; a Control Center yes on the plan approves nothing on its own."""
    pid = mix_rules.proposal_id(monday)
    label = _week_label(monday)
    versions = cc_records.probe(cc, lambda n: cc_records.version_run_id(label, n), cc_records.VERSION, MAX_NUMBERED)
    if versions is None:
        return _held('concept_hold', 'mix_versions_unbounded')
    if not versions:
        return _held('concept_hold', 'mix_plan_not_reported')
    version = versions[-1]
    parts = version.get('parts')
    if version.get('week_of') != monday or not isinstance(parts, list) or not parts or any(
            not isinstance(p, dict) or set(p) != {'proposal_id', 'payload_sha256'}
            or p['proposal_id'] != mix_rules.part_id(monday, n) or not isinstance(p['payload_sha256'], str)
            or not HEX64.match(p['payload_sha256']) for n, p in enumerate(parts, 1)):
        return _held('concept_hold', 'mix_version_malformed')
    stubs = [{'proposal_id': p['proposal_id'], 'stage': 'plan', 'payload_sha256': p['payload_sha256']} for p in parts]
    # Every part he ever decided on, in any version: a part a later version dropped still carries his no (R111).
    current = {p['proposal_id'] for p in parts}
    dropped = sorted({d['proposal_id'] for d in decisions if isinstance(d, dict)
                      and mix_rules.week_part(d.get('proposal_id'), monday)} - current)
    stubs += [{'proposal_id': i, 'stage': 'plan'} for i in dropped]
    ledger = record_stops(state_root, list(proposals) + stubs, decisions)
    stopped = tuple(sorted(ledger['stopped']))
    ids = sorted(current) + dropped
    if any(i in ledger['stopped'] or any(
            isinstance(d, dict) and d.get('proposal_id') == i and d.get('decision') == 'declined'
            for d in decisions) for i in ids):
        return {'hold': None, 'stopped': True, 'why': 'declined', 'stopped_at': _stopped_at(decisions, ledger, ids)}
    if ledger['unresolved']:
        return _held('concept_stop_unresolved', 'stop_unresolved')
    read = []
    for part in parts:
        try:
            item, record = read_part(cc, part['proposal_id'], part['payload_sha256'])
        except ValueError:
            return _held('concept_hold', 'mix_part_unreadable')
        if item is None:
            return _held('concept_hold', 'mix_part_missing')
        read.append((item, record))
    try:
        cfg = mix_rules.load(root or ROOT)
        record, why = decide.cc_readback(monday, read, cfg, decisions, ledger, now)
    except (ValueError, KeyError, TypeError):
        return _held('concept_hold', 'plan_untrusted')
    # Since 30 October his yes on the plan in Control Center no longer approves anything (the board's mix
    # press does, below); his no, a stop, an amended-away concept or his changed terms still stop or hold.
    if record is None:
        code = _why_code(why)
        if code not in ('no_decision', 'not_approved', 'stale_approval'):
            return _held('concept_hold', code)
    elif record['decision'] == 'declined':
        return {'hold': None, 'stopped': True, 'why': 'declined', 'stopped_at': _stopped_at(decisions, ledger, ids)}
    elif record['decision'] == 'held':
        return _held('concept_hold', str(record.get('hold') or decide.HOLD_TERMS).split(':')[0])
    try:
        gone = amended_away(cc, monday, decisions)
    except ValueError as error:
        return _held('concept_hold', str(error))
    binding, held = mix_binding(cc, board, monday, parts, read, cfg, root)
    if held:
        return held
    known = {c['concept_id']: c for _, part in read for c in part['concepts'] if c['ready']}
    stops = set((record or {}).get('stopped_concepts') or []) | gone
    approved = {cid: known[cid]['concept_sha256'] for cid in sorted(binding['concepts'])
                if cid in known and cid not in stops}
    plan_sha = read[0][0]['payload_sha256']
    pressed = {'decision': 'approved', 'decided_at': binding['at'], 'plan_payload_sha256': plan_sha,
               'amended': False, 'amended_sha256': None, 'read_at': instant(now).isoformat(), 'approved': approved,
               'stopped_concepts': sorted(stops), 'changed_concepts': (record or {}).get('changed_concepts') or []}
    ceilings = {c: mix_rules.ceiling({'targets': read[0][1]['targets']}, c) for c in cfg['channels']}
    try:
        part = decide.concept_part(pid, known, pressed, (), ceilings, plan_sha, None)
    except ValueError:
        return _held('concept_hold', 'not_applied')
    if part['concept_hold']:
        return _held('concept_hold', part['concept_hold'].split(':')[0])
    start = ny_midnight(calendar_date(monday))
    spec = {'concepts': part['concept_manifest'],
            'window': {'start': start.isoformat(), 'end': ny_midnight(calendar_date(monday) + dt.timedelta(days=7))
                       .isoformat(), 'tz': TIMEZONE},
            'signature': {'concept_proposal_id': pid, 'concepts_digest': concept_rules.concepts_digest(part['concepts'])}}
    problem = concept_rules.decision_errors(spec, part)
    if problem:
        return _held('concept_hold', 'not_applied')
    return {'hold': None, 'stopped': False, 'why': None, 'decision': part, 'spec': spec,
            'stopped_proposals': stopped, 'mix': binding}


# The week's mix, approved once on the board (Ruling, Krish, 2026-10-30) ----------------------

MIX_PENDING = ('mix_board_not_configured', 'mix_not_approved', 'mix_not_proposed')


def mix_binding(cc, board, monday, parts, read, cfg, root):
    """(binding, None) when Krish's one press on the board approves the mix Growth itself proposes for the
    week, else (None, a hold). Ruling (Krish, 2026-10-30): "approve the week's mix once, let Growth fill it".

    Growth's proposal is rebuilt from its own kept plan, read back from Control Center by digest: the plan in
    force (its parts, each concept recomputed to its concept_sha256) and its slots record (engine/run/maker.py
    week_slots, checked against the words of part 1). From them engine/offday.py options lays out the board's
    Off days and proposed_mix computes the days and the hash exactly as content-engine's week_mix does. The
    press must say approved on that hash and those days. The binding then names, per day key, each option's
    concept and its format line: a derived post goes out only as one of them (outside_mix). No press, or a
    press not yet approved, holds quietly; a press on another hash holds loudly and the proposal is re-sent
    in the summary (repropose)."""
    from engine import offday
    from engine.run import board_tick, maker
    try:
        slots = maker.week_slots(cc, monday, parts, read, cfg, root or ROOT)
    except maker.Held as hold:
        return None, _held('concept_hold', hold.code)
    doc = {'week_of': monday, 'slots': slots, 'concepts': [c for _, record in read for c in record['concepts']]}
    try:
        offdays = offday.options(doc, (), root or ROOT)
        days, sha = offday.proposed_mix(offdays, monday)
        kept = offday.board_options(offdays, monday)
    except (ValueError, KeyError, TypeError):
        return None, _held('concept_hold', 'mix_unproposable')
    if not days:
        return None, _held('mix_not_proposed', 'mix_not_proposed', loud=False)
    if board is None:
        return None, _held('mix_board_not_configured', 'mix_board_not_configured', loud=False)
    try:
        pressed, approved = board.approvals(monday) if hasattr(board, 'approvals') else (board.mix(monday), [])
    except board_tick.BoardError as error:
        return None, _held('mix_board_unreadable', error.code if error.code == 'board_token_refused'
                           else 'mix_board_unreadable')
    if approved:
        # Ruling (Krish, 2026-11-01): each off-day option is approved on its own, idea and direction. The binding is
        # exactly the options he approved that Growth itself proposed, each with its own format line; anything else
        # stays outside the mix (outside_mix fails closed).
        picked = {(row['day'], row['option_id']) for row in approved}
        options = {key: {o['concept_id']: offday.option_format(o) for o in opts
                         if o.get('kind') != 'recorded' and (key, o['concept_id']) in picked}
                   for key, opts in kept.items()}
        options = {key: row for key, row in options.items() if row}
        if not options:
            return None, _held('mix_not_approved', 'mix_not_approved', loud=False)
        chosen = {key: sorted(set(row.values())) for key, row in options.items()}
        return {'mix_sha256': offday.mix_sha256(chosen), 'days': chosen, 'at': max(str(r.get('approved_at') or '') for r in approved) or None,
                'options': options, 'concepts': sorted({cid for row in options.values() for cid in row}),
                'by': 'option'}, None
    if pressed is None or pressed['approved'] is not True:
        return None, _held('mix_not_approved', 'mix_not_approved', loud=False)
    if pressed['mix_sha256'] != sha or pressed['days'] != days or offday.mix_sha256(pressed['days']) != sha:
        return None, dict(_held('mix_hash_mismatch', 'mix_hash_mismatch'), repropose={'mix_sha256': sha, 'days': days})
    options = {key: {o['concept_id']: offday.option_format(o) for o in opts if o.get('kind') != 'recorded'}
               for key, opts in kept.items()}
    return {'mix_sha256': sha, 'days': days, 'at': pressed.get('at'), 'options': options,
            'concepts': sorted({cid for row in options.values() for cid in row})}, None


def outside_mix(state, concept_id, channel, fmt, due):
    """True unless this post is inside the mix he approved: its New York day is a day of the mix, its concept
    is one of that day's options, and channel:format is in that option's format line. Pure; fails closed."""
    binding = state.get('mix') if isinstance(state, dict) else None
    when = due_instant(due) if isinstance(due, str) else due
    if not isinstance(binding, dict) or when is None:
        return True
    from engine.offday import DAY_KEYS
    key = DAY_KEYS[ny_time(when).weekday()]
    line = (binding['options'].get(key) or {}).get(concept_id)
    return line is None or line not in binding['days'].get(key, []) \
        or str(channel) + ':' + str(fmt) not in line.split(', ')


def _stopped_at(decisions, ledger, ids):
    """The earliest time he stopped any of these parts (a decline, or the ledger's stop), or None if none reads."""
    times = [d.get('decided_at') for d in decisions if isinstance(d, dict) and d.get('proposal_id') in ids
             and d.get('decision') == 'declined']
    times += [(ledger['stopped'].get(i) or {}).get('decided_at') for i in ids if i in ledger['stopped']]
    read = [due_instant(t) for t in times if isinstance(t, str)]
    read = [t for t in read if t is not None]
    return min(read) if read else None


def amended_away(cc, monday, decisions):
    """Every concept id he deleted or edited in an amended yes on any part of the week, in any version.

    Read from the words each amended decision was made on (the part's own report, by
    the digest he decided on, recomputed here) against his text, so no record is
    trusted for it. Raises ValueError (a loud hold) when such a part cannot be read."""
    gone = set()
    for d in decisions:
        if not isinstance(d, dict) or not mix_rules.week_part(d.get('proposal_id'), monday) \
                or d.get('amended') is not True:
            continue
        if not isinstance(d.get('payload_sha256'), str) or not HEX64.match(d['payload_sha256']) \
                or not isinstance(d.get('exact_payload'), str):
            raise ValueError('amended_part_unreadable')
        item, _ = read_part(cc, d['proposal_id'], d['payload_sha256'])
        if item is None or not isinstance(item.get('exact_payload'), str):
            raise ValueError('amended_part_unreadable')
        try:
            own = payload_digest(item.get('wall'), item.get('channel'), item['exact_payload'], item.get('target'),
                                 item.get('amount_usd'))
        except (ValueError, TypeError):
            own = None
        if own != d['payload_sha256']:
            raise ValueError('amended_part_unreadable')
        kept = {mix_rules._line(line) for line in d['exact_payload'].split('\n')}
        for line in item['exact_payload'].split('\n'):
            if line.startswith('- ') and mix_rules._line(line) not in kept:
                gone.add(line[2:].split(' (', 1)[0])
    return gone


LATE = dt.timedelta(minutes=25)  # a draft this far past its time is no longer read: loud once, then quiet (S6)


def index_days(cc, days, holds):
    """Every well formed entry of each New York day's numbered indexes (cc_records.INDEX), by payload_sha256.
    None (loud) when a day's indexes never end."""
    found = {}
    for day in days:
        records = cc_records.probe(cc, lambda n: cc_records.index_run_id(day, n), cc_records.INDEX, MAX_NUMBERED)
        if records is None:
            return None
        for record in records:
            for entry in record.get('entries') or [] if record.get('day') == day else []:
                due = due_instant(entry.get('due_at')) if isinstance(entry, dict) else None
                if due is None or not isinstance(entry.get('payload_sha256'), str) \
                        or not HEX64.match(entry['payload_sha256']) or ny_time(due).date().isoformat() != day \
                        or not isinstance(entry.get('concept_id'), str) or not isinstance(entry.get('channel'), str) \
                        or not isinstance(entry.get('buffer_draft_id'), str) \
                        or not BUFFER_ID.match(entry['buffer_draft_id']):
                    holds['derived_index_malformed'] = holds.get('derived_index_malformed', 0) + 1
                    continue
                found.setdefault(entry['payload_sha256'], entry)
    return found


def _due_order(entries):
    return sorted(entries, key=lambda e: (due_instant(e['due_at']), e['payload_sha256']))


def derived_entries(cc, now, holds):
    """The derived slots due from LATE before now to the end of the release window, from each day's
    numbered index, in due order. None (loud) when a day's indexes never end."""
    days = sorted({ny_time(now - LATE).date().isoformat(), ny_time(now + SCHEDULE_WINDOW).date().isoformat()})
    found = index_days(cc, days, holds)
    if found is None:
        return None
    return _due_order(e for e in found.values() if now - LATE <= due_instant(e['due_at']) <= now + SCHEDULE_WINDOW)


def week_entries(cc, monday, holds):
    """Every derived slot indexed for the New York week starting monday, in due order, or None (loud)."""
    start = calendar_date(monday)
    found = index_days(cc, [(start + dt.timedelta(days=n)).isoformat() for n in range(7)], holds)
    return None if found is None else _due_order(found.values())


LIVE = ('scheduled', 'sending', 'sent')


def other_drafts(week, entry):
    """The other Buffer drafts indexed that week for entry's concept on entry's channel (S2): a piece or idea
    runs at most once per channel in a week (engine/mix.py). A draft reviewed again is the same post."""
    return sorted({e['buffer_draft_id'] for e in week if e['concept_id'] == entry['concept_id']
                   and e['channel'] == entry['channel']} - {entry['buffer_draft_id']})


def review_of(cc, entry):
    """(slot fields, review) for one indexed derived slot, read back by its exact payload_sha256, or (None, code)."""
    sha = entry['payload_sha256']
    record = cc_records.read_record(cc, cc_records.review_run_id(sha), cc_records.REVIEW)
    if record is None:
        return None, 'review_missing'
    slot, review = record.get('slot'), record.get('review')
    if record.get('payload_sha256') != sha or not isinstance(review, dict) or review.get('payload_sha256') != sha:
        return None, 'review_for_another_payload'  # F113: a review at another sha never counts
    if not isinstance(slot, dict) or set(slot) != REVIEW_SLOT_KEYS or slot['due_at'] != entry['due_at'] \
            or slot['channel'] != entry.get('channel') or not isinstance(slot['buffer_draft_id'], str) \
            or not BUFFER_ID.match(slot['buffer_draft_id']) or not isinstance(slot['asset_names'], list) \
            or not isinstance(slot['concept_id'], str) or slot['concept_id'] != entry.get('concept_id') \
            or slot['buffer_draft_id'] != entry.get('buffer_draft_id'):
        return None, 'review_malformed'
    return dict(slot, payload_sha256=sha), review


def derived_lane(cc, run, decisions, state_root, now, root, summary, proposals=(), board=None):
    """Every post made from an approved concept, indexed for today or the release window, through Run.derived.
    The week's authority is read once per week (week_state); reads are capped at MAX_DERIVED, past it loud."""
    try:
        entries = derived_entries(cc, now, run.holds)
    except ValueError:
        entries = None
    if entries is None:
        run.hold('derived_index_unreadable', loud=True)
        return
    if len(entries) > MAX_DERIVED:
        run.loud.append('derived_too_many_reads')
        run.holds['derived_too_many_reads'] = len(entries) - MAX_DERIVED
        entries = entries[:MAX_DERIVED]
    weeks, indexed, taken, statuses = {}, {}, {}, {}

    def state_of(monday):
        if monday not in weeks:
            try:
                weeks[monday] = week_state(cc, monday, decisions, state_root, now, root, proposals, board)
            except ValueError:
                weeks[monday] = _held('concept_hold', 'record_unreadable')
        return weeks[monday]

    def week_of_entries(monday):
        if monday not in indexed:
            try:
                indexed[monday] = week_entries(cc, monday, run.holds)
            except ValueError:
                indexed[monday] = None
        return indexed[monday]

    def status_of(draft_id):
        if draft_id not in statuses:
            post, code = run._read(draft_id)
            statuses[draft_id] = (None, code) if code else (post.get('status'), None)
        return statuses[draft_id]

    def one(entry, state):
        if state.get('stopped'):
            # His no is checked on the post itself, from its draft id: no review needs to read (S3).
            run.stopped(entry['buffer_draft_id'], state)
            return
        try:
            fields, review = review_of(cc, entry)
        except ValueError:
            fields, review = None, 'review_unreadable'
        if fields is None:
            run.hold(review, loud=review == 'review_unreadable')
            return
        key = (entry['concept_id'], entry['channel'], week_of(entry['due_at']))
        if not state.get('hold'):
            # S2: the concept's one post on this channel this week is whichever draft Buffer already holds
            # live, or else the first this run schedules; any other holds. Two live is loud.
            if taken.get(key, entry['buffer_draft_id']) != entry['buffer_draft_id']:
                run.hold('concept_once_per_channel_week')
                return
            week = week_of_entries(key[2])
            if week is None:
                run.hold('derived_index_unreadable', loud=True)
                return
            live = []
            for other in other_drafts(week, entry):
                status, code = status_of(other)
                if code:
                    run.hold(code, loud=True)
                    return
                if status in LIVE:
                    live.append(other)
            if live:
                status, code = status_of(entry['buffer_draft_id'])
                if code or status in LIVE:
                    run.hold(code or 'concept_twice_on_channel_week', loud=True)
                else:
                    run.hold('concept_once_per_channel_week')
                return
        outcome = run.derived(fields, review, state)
        if outcome in ('scheduled', 'would_schedule', 'already_scheduled', 'already_sent'):
            taken[key] = entry['buffer_draft_id']

    done = set()
    for entry in entries:
        done.add(entry['payload_sha256'])
        one(entry, state_of(week_of(entry['due_at'])))
    # S3: when he has said no to anything, this week's and next week's plans are read, and a stopped week's
    # every post still to come is checked now, not when it nears its time: one still scheduled is loud.
    this = week_of(now)
    near = (this, (calendar_date(this) + dt.timedelta(days=7)).isoformat())
    recent = now - dt.timedelta(days=14)
    # Only a no on this week's or next week's plan, or a check-in declined in the last fortnight (it may stop
    # either), starts the scan, so an old no costs nothing.
    if any(isinstance(d, dict) and d.get('decision') == 'declined'
           and (any(mix_rules.week_part(d.get('proposal_id'), m) for m in near)
                or (d.get('stage') == 'check_in' and (due_instant(d.get('decided_at')) or now) >= recent))
           for d in decisions):
        scanned = 0
        for monday in near:
            if monday in weeks:
                state = weeks[monday]
            else:
                try:
                    state = week_state(cc, monday, decisions, state_root, now, root, proposals, board)
                except ValueError:
                    state = _held('concept_hold', 'record_unreadable')
                if state.get('stopped'):
                    weeks[monday] = state
            if not state.get('stopped'):
                continue
            week = week_of_entries(monday)
            if week is None:
                run.hold('derived_index_unreadable', loud=True)
                continue
            for entry in week:
                if entry['payload_sha256'] not in done and due_instant(entry['due_at']) >= now - LATE:
                    if scanned >= MAX_DERIVED:
                        run.loud.append('derived_too_many_reads')
                        run.holds['derived_too_many_reads'] = run.holds.get('derived_too_many_reads', 0) + 1
                        break
                    scanned += 1
                    done.add(entry['payload_sha256'])
                    one(entry, state)
    summary['derived'] = {'read': len(done),
                          'weeks': {_week_label(m): (w.get('why') or 'approved') for m, w in sorted(weeks.items())}}
    # A press on another hash: the mix Growth proposes now, for the board to show again (codes and formats only).
    again = {_week_label(m): w['repropose'] for m, w in sorted(weeks.items()) if w.get('repropose')}
    if again:
        summary['derived']['repropose'] = again


# The run ----------------------------------------------------------------------------

class Unpaged(Exception):
    """Krish's decisions did not page out within the cap: nothing is read as complete."""


def autorelease(cc, buffer, now=None, deliver=False, fetch=None, state_root=None, root=None, clock=None,
                board=None):
    """Returns (summary, exit_code). summary holds counts and codes only.

    now fixes the clock (tests, --now); without it the clock is read again
    before each slot's margin check."""
    if clock is None:
        clock = (lambda: instant(now)) if now is not None else (lambda: instant(None))
    now = clock()
    fetch = fetch or (lambda url: buffer_api.download_sha256(url))
    summary = {'lane': 'L0', 'command': 'autorelease', 'deliver': bool(deliver), 'decisions_read': 0,
               'golives': {'releasable': 0, 'held': {}, 'claimed': 0}, 'derived': {'read': 0, 'weeks': {}},
               'slots': {}, 'holds': {}, 'mutations': 0, 'loud': [], 'error': None}
    run = Run(buffer, now, deliver, fetch, root, clock)
    folder = None
    try:
        organizations = buffer.account_check().get('organization_ids') or []
        run.organizations = organizations
        run.caps = release.concept_caps(intensity.state(root or ROOT, now)['urgency'], root or ROOT)
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
        # The go-live ledger is Control Center's (F114): the go-lives this lane already finished are read
        # back into the ledger claim_golives reads, so each acts once though every runner starts clean.
        seed_claims(cc, state_root, proposals, decisions, now)
        review = claim_golives(state_root, proposals, decisions, now)
        for item in review['holds']:
            held[item['reason']] = held.get(item['reason'], 0) + 1
        by_id = {p['proposal_id']: p for p in proposals}
        latest, _ = _latest(decisions)
        for item in review['holds']:
            if item['reason'] == 'already_acted' and item['proposal_id'] in by_id:
                acted = acted_action(by_id[item['proposal_id']], latest.get(item['proposal_id']))
                if acted:
                    run.golive(acted, by_id[item['proposal_id']], acted=True)
        summary['golives']['releasable'] = len(review['actions'])
        for action in review['actions']:
            outcomes = run.golive(action, by_id[action['proposal_id']])
            if deliver and outcomes and all(outcome in DONE for outcome in outcomes):
                tally = {}
                for outcome in outcomes:
                    tally[outcome] = tally.get(outcome, 0) + 1
                summary['golives']['claimed'] += int(record_claim(cc, action, now, root, tally))
        # Posts made from a concept he approved in the week's mix plan, read back from Control Center.
        derived_lane(cc, run, decisions, state_root, now, root, summary, proposals, board)
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
    except ValueError as error:
        # A record in Control Center that cannot be read whole: nothing is guessed (codes only).
        summary['error'] = str(error) if re.match(r'^[a-z_]{1,40}$', str(error)) else 'record_unreadable'
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


def main(argv=None, make_cc=None, make_buffer=None, fetch=None, out=print, make_board=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['autorelease']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run autorelease', description=__doc__.split('\n')[0])
    parser.add_argument('--deliver', action='store_true', help='schedule in Buffer; without it, a dry run')
    parser.add_argument('--now', help='a fixed clock, for tests')
    parser.add_argument('--state', help='a folder for the claim ledger, for tests; default a throwaway one, seeded '
                        'each run from the claims kept in Control Center')
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
    # The board's mix press (GROWTH_WRITEBACK_TOKEN, the secret board tick already uses); without it no
    # derived post is approved (mix_board_not_configured) and every other lane runs as before.
    from engine.run.board_tick import board_from_env
    board = (make_board or board_from_env)()
    result, code = autorelease(cc, buffer, args.now, args.deliver, fetch, args.state, board=board)
    out(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
