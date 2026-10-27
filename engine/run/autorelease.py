"""Lane L0, release: schedule in Buffer exactly what Krish signed, once.

`growth.py run autorelease [--deliver]` runs in GitHub Actions with no model,
no session and no PC. Without --deliver it is a dry run: it reads Control
Center and Buffer and prints the plan as counts, and sends no mutation.

1. Signed go-lives. Krish's decisions are read from Control Center
   (engine.control_center.Client). Each approved go-live, its plan and any
   declined check-in are read back from the report that proposed them, and
   engine.cc_loop.claim_golives decides which go-lives may act (approved on
   the exact digest, plan open and not stopped, in date; an amended yes acts
   in his words, by amended_sha256).
2. Each signed slot. Its Buffer draft is read fresh and the slot digest
   (engine.run.release.slot_digest) is rebuilt from the draft: its text, its
   channel, the signed format, link placement, due time and publish mode, and
   the sha256 of each asset's bytes downloaded now (capped at 50 MB; any
   failure holds). It must equal the payload_sha256 the engine signed.
3. Match, still a draft, due more than five minutes ahead: one editPost to
   customScheduled at the signed due_at, carrying the whole draft forward,
   then a fresh readback that must say scheduled at that time, in those words.
4. Anything else holds with a reason code. Nothing is retried blindly and
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
buffer_draft_id, words, assets: [sha256, ...], payload_sha256}, where
payload_sha256 is release.slot_digest of the line. Krish may amend a line's
words or due_at, or drop a line, or turn a line to krish_click; any other
amendment holds. engine.run.handoff is the builder: it turns a routine's
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

from engine.cc_loop import claim_golives, decisions_since
from engine.control_center import (APPROVED_ORIGIN, RUN_ID, Client, ProtocolError, _latest, report_digest)
from engine.core import instant, read_json, today
from engine.run import buffer_api
from engine.run.buffer_api import Buffer, BufferAuthError, BufferError, CarryHold
from engine.run.release import BUFFER_ID, CHANNELS, DUE_AT, HEX64, KRISH_CLICK_ONLY, slot_digest

ROOT = Path(__file__).resolve().parents[2]
BUFFER_KEY_ENV = 'BUFFER_API_KEY'
MANIFEST_SCHEMA = 'growth-golive-manifest/1'
LINE_KEYS = frozenset({'slot_id', 'channel', 'format', 'due_at', 'link_placement', 'publish_mode',
                       'buffer_draft_id', 'words', 'assets', 'payload_sha256'})
# Fields Krish may change in his amended manifest; any other change holds.
AMENDABLE = frozenset({'words', 'due_at', 'publish_mode', 'payload_sha256'})
LOOKBACK = dt.timedelta(days=70)  # a standing plan is approved once for eight weeks
DUE_MARGIN = dt.timedelta(minutes=5)
MAX_REPORT_READS = 24
SERVICE_CHANNEL = {service: channel for channel, (service, _) in CHANNELS.items()}
AUTHORITY_FILE = Path('invariants') / 'authority.json'
SHOW_BEFORE_POST_DEFAULT = '2026-11-29'
# Where authority.json lists derivative format classes. Another work item
# writes that file; these are the shapes read. Verify against the file.
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


def derivative_formats(root=None):
    auth = _authority(root)
    for key in DERIVATIVE_KEYS:
        if isinstance(auth.get(key), list):
            return {f for f in auth[key] if isinstance(f, str)}
    classes = auth.get('format_classes')
    if isinstance(classes, dict) and isinstance(classes.get('derivative'), list):
        return {f for f in classes['derivative'] if isinstance(f, str)}
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
    return slot_digest({**line, 'assets': [{'sha256': h} for h in line['assets']]})


def draft_line(post, fields, fetch):
    """The manifest line one Buffer draft makes, rebuilt from the draft itself.

    Its channel comes from the draft's service, its words from the draft's
    text and each asset hash from the bytes downloaded now (fetch(url) returns
    (sha256, size) or raises BufferError). Every other digest field (format,
    due_at, link_placement, publish_mode) comes from fields, and
    payload_sha256 is the rebuilt line's own digest. Shared by the release
    (autorelease) and the handoff that proposes the go-live (engine.run.handoff),
    so both rebuild a slot exactly the same way."""
    hashes = []
    for asset in post.get('assets') or []:
        source = asset.get('source') if isinstance(asset, dict) else None
        digest, _ = fetch(source)
        hashes.append(digest)
    line = {**fields, 'channel': SERVICE_CHANNEL.get(post.get('channelService')), 'words': post.get('text'),
            'assets': hashes}
    line['payload_sha256'] = line_digest(line)
    return line


def parse_manifest(text, engine=True):
    """The manifest's lines by slot_id. The engine's own lines must each
    recompute to their payload_sha256; Krish's amended lines are recomputed."""
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
              and isinstance(line['words'], str) and line['words'].strip()
              and isinstance(line['assets'], list)
              and all(isinstance(h, str) and HEX64.match(h) for h in line['assets']))
        if not ok:
            raise ValueError('manifest_line_malformed')
        if line['slot_id'] in lines:
            raise ValueError('manifest_duplicate_slot')
        if engine and line['payload_sha256'] != line_digest(line):
            raise ValueError('manifest_line_digest_mismatch')
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


def signed_golives(cc, decisions, holds):
    """The staged proposals the go-live review needs, read back by digest."""
    latest, _ = _latest(decisions)
    wanted = [(pid, d['payload_sha256']) for pid, d in sorted(latest.items())
              if d.get('stage') == 'go_live' and d.get('decision') == 'approved']
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

    for pid, sha in wanted:
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
    for d in decisions or []:
        if isinstance(d, dict) and d.get('decision') == 'declined' and d.get('stage') == 'check_in' \
                and d.get('proposal_id') not in found and isinstance(d.get('payload_sha256'), str):
            item = fetch(d['proposal_id'], d['payload_sha256'], 'check_in_')
            if item is not None:
                found[d['proposal_id']] = item
    return list(found.values())


# One slot ------------------------------------------------------------------------

class Run:
    def __init__(self, buffer, now, deliver, fetch, root=None):
        self.buffer = buffer
        self.now = instant(now)
        self.deliver = deliver
        self.fetch = fetch
        self.root = root
        self.slots = {}
        self.holds = {}
        self.loud = []

    def count(self, outcome):
        self.slots[outcome] = self.slots.get(outcome, 0) + 1

    def hold(self, code):
        self.count('held')
        self.holds[code] = self.holds.get(code, 0) + 1

    def _rebuilt_digest(self, post, engine_line):
        rebuilt = draft_line(post, engine_line, self.fetch)
        if len(rebuilt['assets']) != len(engine_line['assets']):
            raise CarryHold('asset_count_differs')
        return rebuilt['payload_sha256']

    def _matches(self, post, signed):
        if post.get('text') != signed['words']:
            return False
        if post.get('status') == 'scheduled':
            try:
                return bool(post.get('dueAt')) and instant(post['dueAt']) == instant(signed['due_at'])
            except (ValueError, TypeError):
                return False
        return True

    def slot(self, signed, engine_line, golive_decision):
        """Release one signed line, or count why not."""
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
        try:
            post = self.buffer.get_post(signed['buffer_draft_id'])
        except BufferAuthError:
            raise
        except BufferError as error:
            return self.hold(error.code)
        service = CHANNELS[signed['channel']][0]
        if post.get('via') == 'network':
            return self.hold('imported_post')
        if post.get('channelService') != service:
            return self.hold('draft_on_another_service')
        status = post.get('status')
        if status in ('scheduled', 'sent'):
            if self._matches(post, signed):
                return self.count('already_' + status)
            return self.hold('live_post_differs_from_signed')
        if status != 'draft':
            return self.hold({'sending': 'still_sending', 'error': 'buffer_post_error',
                              'needs_approval': 'needs_approval'}.get(status, 'unknown_status'))
        try:
            if self._rebuilt_digest(post, engine_line) != engine_line['payload_sha256']:
                return self.hold('draft_differs_from_signed')
            buffer_api.edit_input(post, signed['due_at'], signed['words'])
        except CarryHold as hold:
            return self.hold(hold.code)
        except BufferAuthError:
            raise
        except BufferError as error:
            return self.hold(error.code if error.code.startswith('asset_') else 'asset_download_failed')
        if instant(signed['due_at']) - self.now <= DUE_MARGIN:
            return self.hold('due_time_passed')
        if not self.deliver:
            return self.count('would_schedule')
        try:
            self.buffer.schedule_draft(post, signed['due_at'], signed['words'])
        except BufferAuthError:
            raise
        except (BufferError, CarryHold) as error:
            # Read back once: an uncertain edit may have landed. Never resend.
            code = getattr(error, 'code', 'edit_failed')
            try:
                again = self.buffer.get_post(post['id'])
            except BufferError:
                self.loud.append('uncertain_edit')
                return self.hold('uncertain_edit')
            if again.get('status') == 'scheduled' and self._matches(again, signed):
                return self.count('scheduled')
            if again.get('status') != 'draft':
                self.loud.append('uncertain_edit')
                return self.hold('uncertain_edit')
            return self.hold(code)
        try:
            back = self.buffer.get_post(post['id'])
        except BufferError:
            self.loud.append('readback_failed')
            return self.hold('readback_failed')
        if back.get('status') != 'scheduled' or not self._matches(back, signed) \
                or back.get('channelId') != post.get('channelId') \
                or len(back.get('assets') or []) != len(post.get('assets') or []):
            self.loud.append('readback_mismatch')
            return self.hold('readback_mismatch')
        return self.count('scheduled')

    def golive(self, action, proposal):
        """Every line of one approved go-live. Lines he dropped are never touched."""
        try:
            engine_lines = parse_manifest(proposal.get('exact_payload'), engine=True)
            signed_lines = parse_manifest(action['exact_payload'], engine=False) if action['amended'] else engine_lines
        except ValueError as error:
            return self.hold(str(error))
        decision = {'decision': 'approved', 'stage': 'go_live'}
        for sid in sorted(engine_lines):
            if sid not in signed_lines:
                self.count('unsigned')
        for sid in sorted(signed_lines):
            self.slot(signed_lines[sid], engine_lines.get(sid), decision)


# The run ----------------------------------------------------------------------------

def autorelease(cc, buffer, now=None, deliver=False, fetch=None, state_root=None, root=None):
    """Returns (summary, exit_code). summary holds counts and codes only."""
    now = instant(now)
    fetch = fetch or (lambda url: buffer_api.download_sha256(url))
    summary = {'lane': 'L0', 'command': 'autorelease', 'deliver': bool(deliver), 'decisions_read': 0,
               'golives': {'releasable': 0, 'held': {}}, 'slots': {}, 'holds': {}, 'mutations': 0,
               'loud': [], 'error': None}
    run = Run(buffer, now, deliver, fetch, root)
    folder = None
    try:
        buffer.account_check()
        if state_root is None:
            folder = tempfile.TemporaryDirectory()
            state_root = folder.name
        since = min(decisions_since(state_root, now), now - LOOKBACK)
        decisions = cc.decisions(since)
        summary['decisions_read'] = len(decisions)
        held = summary['golives']['held']
        proposals = signed_golives(cc, decisions, held)
        review = claim_golives(state_root, proposals, decisions, now)
        for item in review['holds']:
            held[item['reason']] = held.get(item['reason'], 0) + 1
        by_id = {p['proposal_id']: p for p in proposals}
        summary['golives']['releasable'] = len(review['actions'])
        for action in review['actions']:
            run.golive(action, by_id[action['proposal_id']])
    except BufferAuthError as error:
        summary['error'] = error.code
    except BufferError as error:
        summary['error'] = error.code
    except ProtocolError as error:
        summary['error'] = 'control_center_' + error.code
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
    parser.add_argument('--state', help='a folder for the claim ledger; default a throwaway one (Buffer is the ledger)')
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
