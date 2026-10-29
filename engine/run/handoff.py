"""Lane L0, handoff: turn a maker's dispatch into one press for Krish.

`growth.py run handoff --event TYPE --payload FILE [--deliver]` runs in
GitHub Actions (.github/workflows/handoff.yml). A session or PC automation
that saved the drafts sends a `repository_dispatch` (or Krish runs it by hand
as a `workflow_dispatch`); a session never holds the Control Center token, so
this runner turns the handoff into a Control Center proposal. There are no
Claude routines (Krish, 29 Oct 2026). It never schedules, publishes, sends or spends: release is
engine.run.autorelease's, and only after Krish approves.

Three event types, each with a closed client_payload (unknown keys refused):

- `growth-go-live-manifest` (a day's or a piece's drafts; an express idea with
  "express": true): {"run_id", "slots": [{"slot", "channel",
  "buffer_draft_id", "payload_sha256", "per_item_review", "format", "due_at",
  "link_placement", "publish_mode"}], "express"?}. Ids, codes, times and
  hashes only, never words. For each slot the Buffer draft is read fresh
  (status must be draft, on this engine's own Buffer account, else
  `wrong_account`) and the slot digest is rebuilt from it exactly as
  autorelease rebuilds it (autorelease.draft_line, which covers the draft's
  Buffer channel id and its meta: everything the edit sends besides the
  words and the time). A slot whose rebuilt digest is not the dispatch's
  payload_sha256 is held (`handoff_digest_mismatch`), as is any slot
  autorelease could not carry, a due_at that is no real date (`bad_due_at`)
  and one outside the run window its run_id names (`due_outside_run_window`).
  The why Krish reads names, in plain words, the first comment, titles,
  privacy, location, AI label and tagged accounts that go out with each post.
  LinkedIn always goes in as krish_click. The slots that pass become the
  `growth-golive-manifest/1` exact_payload autorelease reads, each go-live a
  `post` wall with target null under the newest open plan Krish approved,
  reported in its own report whose run_id is
  `<proposal_id>:<first 12 hex of payload_sha256>`, then read back. A
  manifest over 8,000 characters splits into go-lives that come forward one
  after another (`:p1`, `:p2`, ...). A slot marked per_item_review, or whose
  format is a new kind (carousel, meme, opinion, reactive, or the list in
  invariants/authority.json), is its own go-live (`:item-1`, ...), so he
  sees it alone.
- `growth-week-packet` (whoever plans the week): {"run_id", "week",
  "spec_sha256", "slots": [{"slot", "channel", "payload_sha256"}]}. Proposed
  as a `check_in` on the open plan ("On track?"), or as a `plan` when no
  plan is open. One proposal per packet: one ask at a time.
- `growth-make-piece` (a publish board Krish approved): {"piece_id"}. Nothing
  to propose: it is recorded and counted.

Without --deliver it is a dry run: it reads Control Center and Buffer, sends
no report, and writes the would-be reports to .scratch/cc/handoff-<type>.json.
Output is one JSON line of counts and reason codes: never words, URLs, ids
or keys.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys

from engine.cc_loop import NO_SPEND, revision
from engine.control_center import (SLUG, ProtocolError, _expiry_hold, _latest, _plan_open, _stops,
                                   build_report, canonical_json, objective, proposal, sha256_hex)
from engine.core import instant, today, write_json
from engine.run import autorelease, buffer_api
from engine.run.autorelease import (DUE_MARGIN, LINE_KEYS, MANIFEST_SCHEMA, MAX_REPORT_READS, _authority, draft_line,
                                    due_instant, line_digest, read_proposal, run_window, show_before_post_until,
                                    staged_report_run_id)
from engine.run.buffer_api import BufferAuthError, BufferError, CarryHold
from engine.run.release import BUFFER_ID, CHANNELS, DUE_AT, HEX64, KRISH_CLICK_ONLY, account_hold
from engine.run.spec import RUN_ID as SPEC_RUN_ID

ROOT = Path(__file__).resolve().parents[2]
GO_LIVE, WEEK_PACKET, MAKE_PIECE = 'growth-go-live-manifest', 'growth-week-packet', 'growth-make-piece'
EVENTS = (GO_LIVE, WEEK_PACKET, MAKE_PIECE)
MAX_PAYLOAD_BYTES = 65536
MAX_SLOTS = 60
PAYLOAD_CAP = 8000
WHY_CAP = 1000  # control_center.proposal clips why here; a why that would be cut is never sent
SLOT_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
FORMAT = re.compile(r'^[a-z0-9][a-z0-9_-]{0,47}$')
PLACEMENT = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
WEEK = re.compile(r'^W(0[1-9]|[1-4][0-9]|5[0-3])$')
PIECE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:._-]{0,119}$')
MANIFEST_KEYS, MANIFEST_OPTIONAL = frozenset({'run_id', 'slots'}), frozenset({'express'})
MANIFEST_SLOT_KEYS = frozenset({'slot', 'channel', 'buffer_draft_id', 'payload_sha256', 'per_item_review',
                                'format', 'due_at', 'link_placement', 'publish_mode'})
PACKET_KEYS, PACKET_SLOT_KEYS = (frozenset({'run_id', 'week', 'spec_sha256', 'slots'}),
                                 frozenset({'slot', 'channel', 'payload_sha256'}))
PIECE_KEYS = frozenset({'piece_id'})
# New kinds of post Krish sees one by one (docs/LANES.md, L2). invariants/authority.json
# may list its own; these are read when it does not.
NEW_FORMATS_DEFAULT = ('carousel', 'meme', 'opinion', 'reactive')
NAMES = {'substack-notes': 'Substack Notes', 'threads': 'Threads', 'x': 'X', 'instagram': 'Instagram',
         'facebook': 'Facebook', 'tiktok': 'TikTok', 'youtube': 'YouTube', 'linkedin': 'LinkedIn'}
STATE_DIR = Path('.scratch') / 'cc'


class PayloadRejected(ValueError):
    """The client_payload is not the closed shape. Carries a code only."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


# The closed payload shapes ----------------------------------------------------

def _closed(value, required, optional=frozenset(), where='payload'):
    if not isinstance(value, dict):
        raise PayloadRejected(where + '_not_object')
    if set(value) - required - optional:
        raise PayloadRejected(where + '_unknown_key')
    if required - set(value):
        raise PayloadRejected(where + '_missing_key')


def _run_id(value):
    if not isinstance(value, str) or not SPEC_RUN_ID.match(value) or not value.startswith(SLUG + ':'):
        raise PayloadRejected('bad_run_id')
    return value


def _slots(value):
    if not isinstance(value, list) or not value:
        raise PayloadRejected('no_slots')
    if len(value) > MAX_SLOTS:
        raise PayloadRejected('too_many_slots')
    return value


def _unique(slots, key, code):
    seen = [slot[key] for slot in slots]
    if len(seen) != len(set(seen)):
        raise PayloadRejected(code)


def _slot_common(slot, keys):
    _closed(slot, keys, where='slot')
    if not isinstance(slot['slot'], str) or not SLOT_ID.match(slot['slot']):
        raise PayloadRejected('bad_slot_id')
    if slot['channel'] not in CHANNELS:
        raise PayloadRejected('unknown_channel')
    if not isinstance(slot['payload_sha256'], str) or not HEX64.match(slot['payload_sha256']):
        raise PayloadRejected('bad_payload_sha256')


def validate_manifest(value):
    _closed(value, MANIFEST_KEYS, MANIFEST_OPTIONAL)
    _run_id(value['run_id'])
    if 'express' in value and not isinstance(value['express'], bool):
        raise PayloadRejected('bad_express')
    for slot in _slots(value['slots']):
        _slot_common(slot, MANIFEST_SLOT_KEYS)
        if not isinstance(slot['buffer_draft_id'], str) or not BUFFER_ID.match(slot['buffer_draft_id']):
            raise PayloadRejected('bad_buffer_draft_id')
        if not isinstance(slot['per_item_review'], bool):
            raise PayloadRejected('bad_per_item_review')
        if not isinstance(slot['format'], str) or not FORMAT.match(slot['format']):
            raise PayloadRejected('bad_format')
        if slot['due_at'] is not None and not (isinstance(slot['due_at'], str) and DUE_AT.match(slot['due_at'])):
            raise PayloadRejected('bad_due_at')
        if slot['link_placement'] is not None and not (isinstance(slot['link_placement'], str)
                                                       and PLACEMENT.match(slot['link_placement'])):
            raise PayloadRejected('bad_link_placement')
        if slot['publish_mode'] not in ('engine', 'krish_click'):
            raise PayloadRejected('bad_publish_mode')
    _unique(value['slots'], 'slot', 'duplicate_slot')
    _unique(value['slots'], 'buffer_draft_id', 'duplicate_draft')
    return value


def validate_packet(value):
    _closed(value, PACKET_KEYS)
    _run_id(value['run_id'])
    if not isinstance(value['week'], str) or not WEEK.match(value['week']):
        raise PayloadRejected('bad_week')
    if not isinstance(value['spec_sha256'], str) or not HEX64.match(value['spec_sha256']):
        raise PayloadRejected('bad_spec_sha256')
    for slot in _slots(value['slots']):
        _slot_common(slot, PACKET_SLOT_KEYS)
    _unique(value['slots'], 'slot', 'duplicate_slot')
    return value


def validate_piece(value):
    _closed(value, PIECE_KEYS)
    if not isinstance(value['piece_id'], str) or not PIECE_ID.match(value['piece_id']):
        raise PayloadRejected('bad_piece_id')
    return value


VALIDATORS = {GO_LIVE: validate_manifest, WEEK_PACKET: validate_packet, MAKE_PIECE: validate_piece}


def load_payload(path):
    try:
        with open(path, 'rb') as handle:
            raw = handle.read(MAX_PAYLOAD_BYTES + 1)
    except OSError:
        raise PayloadRejected('payload_unreadable') from None
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise PayloadRejected('payload_too_large')
    try:
        return json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise PayloadRejected('payload_unreadable') from None


# Authority ------------------------------------------------------------------------

def new_formats(root=None):
    """Formats that are not derivatives of an approved piece: each needs his eyes alone.

    invariants/authority.json lists the derivative classes; any other class
    needs eyes (any_other_class). Without the file, the default kinds hold.
    """
    derivatives = autorelease.derivative_formats(root)
    if not derivatives:
        return set(NEW_FORMATS_DEFAULT)
    return NotDerivative(derivatives)


class NotDerivative:
    """A 'set' of every format that is not a derivative."""

    def __init__(self, derivatives):
        self.derivatives = frozenset(derivatives)

    def __contains__(self, fmt):
        return fmt not in self.derivatives


def needs_own_review(slot, formats):
    """per_item_review from the dispatch, or a format of a new kind: his eyes on this one alone."""
    fmt = slot['format']
    if isinstance(formats, NotDerivative):
        return bool(slot['per_item_review']) or fmt in formats
    return bool(slot['per_item_review']) or fmt in formats or any(p in formats for p in re.split(r'[-_]', fmt))


# The plan a proposal names ---------------------------------------------------------

def open_plan(cc, decisions, now):
    """(plan, None) for the newest plan Krish approved that is still open, or (None, code).

    Each plan is read back from its own report by the digest he decided on. A
    declined check-in is read back too, to learn which plan it stopped; while
    one cannot be read, nothing is proposed (`stop_unresolved`)."""
    latest, undated = _latest(decisions)
    found, reads = [], 0
    for item in decisions or []:
        if isinstance(item, dict) and item.get('decision') == 'declined' and item.get('stage') == 'check_in' \
                and isinstance(item.get('proposal_id'), str) and isinstance(item.get('payload_sha256'), str) \
                and reads < MAX_REPORT_READS:
            reads += 1
            got, _ = read_proposal(cc, item['proposal_id'], item['payload_sha256'])
            if got is not None:
                found.append(got)
    wanted = sorted(((d.get('decided_at') or '', pid) for pid, d in latest.items()
                     if d.get('stage') == 'plan' and d.get('decision') == 'approved'
                     and isinstance(d.get('payload_sha256'), str)), reverse=True)
    plans = []
    for _, pid in wanted:
        if reads >= MAX_REPORT_READS:
            break
        reads += 1
        got, _ = read_proposal(cc, pid, latest[pid]['payload_sha256'])
        if got is not None and got.get('stage') == 'plan':
            plans.append(got)
            found.append(got)
    stopped, unresolved = _stops(found, decisions)
    if unresolved:
        return None, 'stop_unresolved'
    for plan in plans:
        pid = plan['proposal_id']
        if pid in undated or pid in stopped or not _plan_open(plan, latest.get(pid)) or _expiry_hold(plan, now):
            continue
        return plan, None
    return None, 'no_open_plan'


# The go-live manifest ---------------------------------------------------------------

class Slots:
    def __init__(self):
        self.counts, self.holds = {}, {}

    def count(self, outcome):
        self.counts[outcome] = self.counts.get(outcome, 0) + 1

    def hold(self, code):
        self.count('held')
        self.holds[code] = self.holds.get(code, 0) + 1


def rebuild(buffer, slot, fetch, now, window=None):
    """(manifest line, None) for one slot whose draft matches, or (None, hold code).
    window is the (start, end) of the run the run_id names, when it names one."""
    due = None
    if slot['due_at'] is not None:
        due = due_instant(slot['due_at'])
        if due is None:
            return None, 'bad_due_at'
    try:
        post = buffer.get_post(slot['buffer_draft_id'])
    except BufferAuthError:
        raise
    except BufferError:
        return None, 'draft_unreadable'
    if post.get('via') == 'network':
        return None, 'imported_post'
    if post.get('channelService') != CHANNELS[slot['channel']][0]:
        return None, 'draft_on_another_service'
    if account_hold(slot['channel'], post):
        return None, 'wrong_account'
    if post.get('status') != 'draft':
        return None, 'not_a_draft'
    fields = {'slot_id': slot['slot'], 'format': slot['format'], 'due_at': slot['due_at'],
              'link_placement': slot['link_placement'], 'publish_mode': slot['publish_mode'],
              'buffer_draft_id': slot['buffer_draft_id']}
    try:
        line = draft_line(post, fields, fetch)
    except BufferAuthError:
        raise
    except BufferError as error:
        return None, error.code if error.code.startswith('asset_') else 'asset_download_failed'
    if line['payload_sha256'] != slot['payload_sha256']:
        return None, 'handoff_digest_mismatch'
    if not isinstance(line['words'], str) or not line['words'].strip():
        return None, 'no_words'
    if slot['channel'] in KRISH_CLICK_ONLY and line['publish_mode'] != 'krish_click':
        # LinkedIn is always his own click: the line goes in as krish_click, with its own digest.
        line['publish_mode'] = 'krish_click'
        line['payload_sha256'] = line_digest(line)
    if line['publish_mode'] == 'engine':
        if line['due_at'] is None:
            return None, 'no_due_at'
        try:
            buffer_api.edit_input(post, line['due_at'], line['words'])  # what autorelease would carry
        except CarryHold as hold:
            return None, hold.code
        if due - instant(now) <= DUE_MARGIN:
            return None, 'due_time_passed'
        if window is not None and not window[0] <= due < window[1]:
            return None, 'due_outside_run_window'
    if set(line) != LINE_KEYS:
        return None, 'line_malformed'
    return line, None


def manifest_text(run_id, lines):
    return canonical_json({'schema': MANIFEST_SCHEMA, 'run_id': run_id, 'slots': lines})


def pack(run_id, lines, slots, fits=None):
    """Lines in order, packed into manifests of PAYLOAD_CAP characters or less,
    each group also passing fits (its why must be shown whole)."""
    fits = fits or (lambda group: True)
    parts, current = [], []
    for line in lines:
        if len(manifest_text(run_id, [line])) > PAYLOAD_CAP:
            slots.hold('slot_over_payload_cap')
            continue
        if not fits([line]):
            slots.hold('details_too_long')
            continue
        if current and (len(manifest_text(run_id, current + [line])) > PAYLOAD_CAP or not fits(current + [line])):
            parts.append(current)
            current = []
        current.append(line)
    if current:
        parts.append(current)
    return parts


def _rest(run_id):
    return run_id[len(SLUG) + 1:]


def _channels(lines):
    seen = []
    for line in lines:
        name = NAMES.get(line['channel'], line['channel'])
        if name not in seen:
            seen.append(name)
    return seen[0] if len(seen) == 1 else ', '.join(seen[:-1]) + ' and ' + seen[-1]


def _posts(number):
    return str(number) + (' post' if number == 1 else ' posts')


def _quoted(text):
    return '"' + ' '.join(str(text).split()) + '"'


def meta_words(line):
    """In plain words, what goes out with a post besides its words, or None."""
    meta = line.get('meta') or {}
    bits = []
    for service, fields in sorted((meta.get('metadata') or {}).items()):
        fields = fields if isinstance(fields, dict) else {}
        if fields.get('firstComment'):
            bits.append('first comment ' + _quoted(fields['firstComment']))
        if fields.get('title'):
            bits.append(('YouTube' if service == 'youtube' else 'TikTok' if service == 'tiktok' else 'post')
                        + ' title ' + _quoted(fields['title']))
        if fields.get('privacy'):
            bits.append('privacy ' + str(fields['privacy']))
        if fields.get('categoryId'):
            bits.append('YouTube category ' + str(fields['categoryId']))
        if fields.get('madeForKids') is True:
            bits.append('marked made for kids')
        if fields.get('notifySubscribers') is False:
            bits.append('subscribers not notified')
        if fields.get('license'):
            bits.append('licence ' + str(fields['license']))
        if fields.get('topic'):
            bits.append('topic ' + _quoted(fields['topic']))
        place = fields.get('locationName') or (fields.get('geolocation') or {}).get('text')
        if place:
            bits.append('location ' + _quoted(place))
        if fields.get('isAiGenerated') is True:
            bits.append('labelled as made with AI')
        if service == 'instagram' and fields.get('shouldShareToFeed') is False and fields.get('type') != 'story':
            bits.append('not shared to the feed')
    tags, titles = [], []
    for asset in meta.get('assets') or []:
        inner = next(iter(asset.values())) if isinstance(asset, dict) and len(asset) == 1 else {}
        extra = (inner or {}).get('metadata') or {}
        tags += ['@' + str(t.get('handle')) for t in extra.get('userTags') or [] if isinstance(t, dict)]
        if extra.get('title'):
            titles.append(_quoted(extra['title']))
    if tags:
        bits.append('tags ' + ', '.join(tags))
    if titles:
        bits.append('video title ' + ', '.join(titles))
    if not bits:
        return None
    return NAMES.get(line['channel'], line['channel']) + ' post ' + line['slot_id'] + ': ' + '; '.join(bits) + '.'


def golive_words(lines, kind, part, parts, day, root, express):
    """The title and why: in plain words, what his yes does."""
    where = _channels(lines)
    if kind == 'item':
        line = lines[0]
        title = 'New kind of post, yours to check: ' + _a(line['format']) + ' on ' + where
        why = 'This is ' + _a(line['format']) + ', a kind of post you see one at a time, so it comes to you on its own. '
    elif express:
        title = 'Your quick idea, ready to go: ' + _posts(len(lines)) + ' on ' + where
        why = 'Built from the idea you added in Buffer Ideas. '
    else:
        title = 'Go live: ' + _posts(len(lines)) + ' on ' + where
        why = ''
    if parts > 1:
        title += ' (part ' + str(part) + ' of ' + str(parts) + ')'
        why += 'This batch is too long for one approval, so it comes in ' + str(parts) + ' parts, one after another. '
    engine = [line for line in lines if line['publish_mode'] == 'engine']
    clicks = len(lines) - len(engine)
    if engine:
        why += ('Yes schedules ' + ('this exact post' if len(engine) == 1 else 'these ' + str(len(engine)) + ' exact posts')
                + ' in Buffer for the time shown, once. A yes schedules each post about an hour before it is due. '
                'Until then, No stops it. ')
    if clicks:
        why += (_posts(clicks) + (' stays' if clicks == 1 else ' stay') + ' a draft in Buffer for you to publish yourself'
                + (', as LinkedIn always does. ' if any(line['channel'] in KRISH_CLICK_ONLY for line in lines) else '. '))
    if day <= show_before_post_until(root):
        why += 'Until ' + _long_date(show_before_post_until(root)) + ' you see every batch before it goes out. '
    details = [text for text in (meta_words(line) for line in lines) if text]
    if details:
        why += 'Also going out with the words: ' + ' '.join(details) + ' '
    why += 'You can change the words or a time, or take a post out, before you say yes.'
    if not engine:
        why += ' No stops it: nothing in it goes out.'
    return title, why


def _a(noun):
    return ('an ' if noun[:1] in 'aeiou' else 'a ') + noun


def _long_date(value):
    day = dt.date.fromisoformat(value)
    return str(day.day) + ' ' + day.strftime('%B %Y')


def golive_proposals(manifest, lines, formats, plan_id, now, root, slots):
    run_id, express = manifest['run_id'], bool(manifest.get('express'))
    base = SLUG + ':golive:' + _rest(run_id)
    review = {line['slot_id'] for line, slot in lines if needs_own_review(slot, formats)}
    batch = [line for line, _ in lines if line['slot_id'] not in review]
    items = [line for line, _ in lines if line['slot_id'] in review]
    day = today(now)

    def fits(kind):
        # Worst-case numbering, so a group that fits here fits once it is numbered.
        return lambda group: len(' '.join(golive_words(group, kind, 99, 99, day, root, express)[1].split())) <= WHY_CAP

    groups = [('batch', part) for part in pack(run_id, batch, slots, fits('batch'))]
    groups += [('item', part) for line in items for part in pack(run_id, [line], slots, fits('item'))]
    out = []
    batches = sum(kind == 'batch' for kind, _ in groups)
    numbers = {'batch': 0, 'item': 0}
    for kind, group in groups:
        numbers[kind] += 1
        if kind == 'batch':
            pid = base if batches == 1 else base + ':p' + str(numbers['batch'])
        else:
            pid = base + ':item-' + str(numbers['item'])
        title, why = golive_words(group, kind, numbers[kind], batches if kind == 'batch' else 1, day, root, express)
        dues = [instant(line['due_at']) for line in group if line['publish_mode'] == 'engine' and line['due_at']]
        item = proposal(pid, title, why, 'prepared', 'post', 'published', channel='buffer',
                        exact_payload=manifest_text(run_id, group), target=None,
                        expires_at=max(dues) if dues else None, stage='go_live', parent_proposal_id=plan_id)
        if staged_report_run_id(pid, item['payload_sha256']) is None:
            for _ in group:
                slots.hold('run_id_too_long')
            continue
        for line in group:
            slots.count('proposed')
            if kind == 'item':
                slots.count('own_review')
        out.append(item)
    return out


# The week packet -----------------------------------------------------------------------

def packet_proposal(packet, plan):
    week, slots = packet['week'], packet['slots']
    tally = {}
    for slot in slots:
        name = NAMES.get(slot['channel'], slot['channel'])
        tally[name] = tally.get(name, 0) + 1
    spread = ', '.join(name + ' ' + str(n) for name, n in tally.items())
    lines = ['Week ' + week + ' (' + packet['run_id'] + '), the packet built for next week.',
             _posts(len(slots)) + ' planned: ' + spread + '.',
             'Spec digest: ' + packet['spec_sha256'][:12] + '.',
             'Every post still comes to you as a go-live before anything goes out.']
    if plan is not None:
        ask = 'Yes keeps the plan going into this week. Change these words to redirect it. No stops the plan for good.'
    else:
        ask = 'Yes opens this plan for the week. Change these words to redirect it. No: nothing is made from it.'
    lines += [ask, 'Posts:']
    lines += ['- ' + slot['slot'] + ' on ' + NAMES.get(slot['channel'], slot['channel']) + ', digest '
              + slot['payload_sha256'][:12] for slot in slots]
    words = '\n'.join(lines)
    if len(words) > PAYLOAD_CAP:
        return None
    rest = _rest(packet['run_id'])
    if plan is not None:
        return proposal(SLUG + ':checkin:' + rest, 'On track? Next week, ' + week + ': ' + _posts(len(slots)) + ' planned',
                        'The Sunday sign-off for ' + week + '. ' + ask, 'advice', 'strategy',
                        'reviewed', exact_payload=words, stage='check_in', parent_proposal_id=plan['proposal_id'])
    return proposal(SLUG + ':plan:' + rest, 'Plan for ' + week + ': ' + _posts(len(slots)),
                    'The Sunday sign-off for ' + week + '. No plan is open, so this one asks first. '
                    + ask, 'advice', 'strategy', 'reviewed', exact_payload=words, stage='plan')


# Reports ------------------------------------------------------------------------------------

def _objectives():
    return [objective('new_subscribers', reason='Measured by the measure job; this handoff only proposes'),
            objective('paid_boosts_usd', reason='Measured by the measure job; ' + NO_SPEND)]


def _holds(slots):
    return [{'reason': code, 'detail': _posts(n) + ' held by the handoff'} for code, n in sorted(slots.holds.items())]


def reports_for(items, slots, now, root, activity):
    """One report per proposal, addressed by the run_id convention; the holds ride on the first."""
    rev, out = revision(root), []
    for index, item in enumerate(items):
        holds = _holds(slots) if index == 0 else []
        out.append(build_report(staged_report_run_id(item['proposal_id'], item['payload_sha256']), 'live', now, rev,
                                now, 'ready', _objectives(), activity, [item], [], holds))
    return out


def held_report(event, key_value, slots, now, root, reason=None):
    holds = _holds(slots) + ([{'reason': reason, 'detail': None}] if reason else [])
    tag = sha256_hex({'event': event, 'key': key_value, 'holds': holds})[:12]
    run_id = SLUG + ':handoff:' + _rest(key_value)[:80] + ':held:' + tag
    return build_report(run_id, 'live', now, revision(root), now, 'held', _objectives(),
                        [{'line': 'Proposed nothing: every part of the handoff was held'},
                         {'line': 'Posted, sent, published and spent nothing'}], [], [], holds)


def deliver_reports(cc, reports, summary):
    """Post each report once and read it back. A conflict is read back, never resent:
    when the stored report already holds this exact proposal, it counts as reported."""
    for report in reports:
        posted = cc.post_report(report)  # raises unless an accepted report reads back the same
        if posted['accepted']:
            summary['reports']['posted'] += 1
            summary['reports']['readback_matches'] += int(bool(posted['readback_matches']))
            continue
        # The run_id already holds a report. Its address carries the proposal's digest (or,
        # for a held report, the holds' digest), so the same proposal is already reported.
        if all(read_proposal(cc, item['proposal_id'], item['payload_sha256'])[0] is not None
               for item in report['proposals']):
            summary['reports']['already_reported'] += 1
        else:
            summary['loud'].append('report_conflict')


# The run ------------------------------------------------------------------------------------

def handoff(event, payload, cc=None, buffer=None, now=None, deliver=False, fetch=None, root=None, out_path=None):
    """Returns (summary, exit_code). summary holds counts and codes only."""
    now = instant(now)
    root = Path(root or ROOT)
    summary = {'lane': 'L0', 'command': 'handoff', 'event': event if event in EVENTS else 'unknown',
               'deliver': bool(deliver), 'slots': {}, 'holds': {}, 'proposals': {},
               'reports': {'built': 0, 'posted': 0, 'already_reported': 0, 'readback_matches': 0},
               'recorded': 0, 'loud': [], 'error': None}
    path = Path(out_path) if out_path else root / STATE_DIR / ('handoff-' + summary['event'] + '.json')
    slots = Slots()
    reports = []
    try:
        if event not in EVENTS:
            raise PayloadRejected('unknown_event')
        VALIDATORS[event](payload)
        if event == MAKE_PIECE:
            # The maker that sent it does the making; the runner only records that it was asked.
            summary['recorded'] = 1
            write_json(path, {'event': event, 'deliver': bool(deliver), 'recorded': 1, 'reports': []})
            return _finish(summary, slots)
        decisions = cc.decisions(now - autorelease.LOOKBACK)
        plan, reason = open_plan(cc, decisions, now)
        if event == GO_LIVE:
            fetch = fetch or (lambda url: buffer_api.download_sha256(url))
            lines = []
            if plan is not None:
                window = run_window(payload['run_id'])
                for slot in payload['slots']:
                    line, code = rebuild(buffer, slot, fetch, now, window)
                    if code:
                        slots.hold(code)
                    else:
                        if slot['channel'] in KRISH_CLICK_ONLY and slot['publish_mode'] != 'krish_click':
                            slots.count('linkedin_to_krish_click')
                        lines.append((line, slot))
            else:
                for _ in payload['slots']:
                    slots.hold(reason)
            items = golive_proposals(payload, lines, new_formats(root), plan and plan['proposal_id'], now, root,
                                     slots) if lines else []
            activity = [{'line': 'Rebuilt ' + _posts(len(lines)) + " from their Buffer drafts; each matched the dispatch's digest"},
                        {'line': 'Posted, sent, published and spent nothing'}]
            reports = reports_for(items, slots, now, root, activity) if items else \
                [held_report(event, payload['run_id'], slots, now, root)]
            summary['proposals'] = {'go_live': len(items)} if items else {}
        else:
            item = packet_proposal(payload, plan) if reason in (None, 'no_open_plan') else None
            if item is None:
                reports = [held_report(event, payload['run_id'], slots, now, root,
                                       reason if reason == 'stop_unresolved' else 'packet_over_payload_cap')]
                summary['holds'][reason if reason == 'stop_unresolved' else 'packet_over_payload_cap'] = 1
            else:
                activity = [{'line': 'Turned the week packet into one ask'},
                            {'line': 'Posted, sent, published and spent nothing'}]
                reports = reports_for([item], slots, now, root, activity)
                summary['proposals'] = {item['stage']: 1}
        summary['reports']['built'] = len(reports)
        write_json(path, {'event': event, 'deliver': bool(deliver), 'reports': reports})
        if deliver:
            deliver_reports(cc, reports, summary)
    except PayloadRejected as error:
        summary['error'] = 'payload_rejected_' + error.code
    except BufferAuthError as error:
        summary['error'] = error.code
    except BufferError as error:
        summary['error'] = error.code
    except ProtocolError as error:
        summary['error'] = 'control_center_' + error.code
    return _finish(summary, slots)


def _finish(summary, slots):
    summary['slots'] = dict(sorted(slots.counts.items()))
    summary['holds'] = dict(sorted({**summary['holds'], **slots.holds}.items()))
    summary['loud'] = sorted(set(summary['loud']))
    code = 1 if summary['error'] or summary['loud'] else 0
    summary['exit'] = code
    return summary, code


def main(argv=None, make_cc=None, make_buffer=None, fetch=None, out=print, root=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['handoff']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run handoff', description=__doc__.split('\n')[0])
    parser.add_argument('--event', required=True, help='one of ' + ', '.join(EVENTS))
    parser.add_argument('--payload', required=True, help='a file holding the client_payload JSON')
    parser.add_argument('--deliver', action='store_true', help='report to Control Center; without it, a dry run')
    parser.add_argument('--now', help='a fixed clock, for tests')
    parser.add_argument('--out', help='where the would-be reports go; default .scratch/cc/handoff-<type>.json')
    args = parser.parse_args(argv)
    summary = {'lane': 'L0', 'command': 'handoff', 'event': args.event if args.event in EVENTS else 'unknown',
               'deliver': args.deliver}
    try:
        payload = load_payload(args.payload)
    except PayloadRejected as error:
        summary.update(error='payload_rejected_' + error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    cc = buffer = None
    if args.event in (GO_LIVE, WEEK_PACKET):
        try:
            if args.event == GO_LIVE:
                buffer = (make_buffer or autorelease._buffer_client)()
            cc = (make_cc or autorelease._cc_client)()
        except BufferError as error:
            summary.update(error=error.code, exit=1)
            out(json.dumps(summary, sort_keys=True))
            return 1
        except ProtocolError as error:
            summary.update(error='control_center_' + error.code, exit=1)
            out(json.dumps(summary, sort_keys=True))
            return 1
    result, code = handoff(args.event, payload, cc, buffer, args.now, args.deliver, fetch, root, args.out)
    out(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
