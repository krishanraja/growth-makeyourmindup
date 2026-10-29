"""Lane L0, handoff: turn a maker's dispatch into one press for Krish.

`growth.py run handoff --event TYPE --payload FILE [--deliver]` runs in
GitHub Actions (.github/workflows/handoff.yml). A session or PC automation
that saved the drafts sends a `repository_dispatch` (or Krish runs it by hand
as a `workflow_dispatch`); a session never holds the Control Center token, so
this runner turns the handoff into a Control Center proposal. There are no
Claude routines (Krish, 29 Oct 2026). It never schedules, publishes, sends or spends: release is
engine.run.autorelease's, and only after Krish approves.

Four event types, each with a closed client_payload (unknown keys refused):

- `growth-go-live-manifest` (a day's or a piece's drafts; an express idea with
  "express": true): {"run_id", "slots": [{"slot", "channel",
  "buffer_draft_id", "payload_sha256", "per_item_review", "format", "due_at",
  "link_placement", "publish_mode"}], "express"?}. Ids, codes, times and
  hashes only, never words. For each slot the Buffer draft is read fresh
  (status must be draft, on this engine's own Buffer account, else
  `wrong_account`) and the slot digest is rebuilt from it exactly as
  autorelease rebuilds it (autorelease.draft_line, which covers the draft's
  Buffer channel id and its meta: everything the edit sends besides the
  words and the time). A slot whose rebuilt run-spec digest
  (autorelease.spec_digest, what the maker's spec signs) is not the dispatch's
  payload_sha256 is held (`handoff_digest_mismatch`); the manifest line it
  becomes is signed under the go-live domain (autorelease.line_digest). So is
  a slot whose signed format is not what the draft is
  (`format_differs_from_draft`), and any slot
  autorelease could not carry, a due_at that is no real date (`bad_due_at`)
  and one outside the run window its run_id names (`due_outside_run_window`).
  The why Krish reads names, in plain words, the day, and the alt text,
  first comment, titles, privacy, location, AI label and tagged accounts
  that go out with each post.
  LinkedIn always goes in as krish_click. The slots that pass become the
  `growth-golive-manifest/1` exact_payload autorelease reads, each go-live a
  `post` wall with target null under the newest open plan Krish approved,
  reported in its own report whose run_id is
  `<proposal_id>:<first 12 hex of payload_sha256>`, then read back. One
  go-live per New York day (R94: a yes authorises exactly that day's posts;
  `:<YYYY-MM-DD>` when a dispatch spans days), and a day over 8,000
  characters splits into go-lives that come forward one after another
  (`:p1`, `:p2`, ...). A slot marked per_item_review, or whose
  format is a new kind (carousel, meme, opinion, reactive, or the list in
  invariants/authority.json), is its own go-live (`:item-1`, ...), so he
  sees it alone.
  A slot made from a concept Krish approved in the week's mix plan names it
  in `concept_id` and carries its `review` (closed: slot_id, verdict, lens,
  payload_sha256, reader_answer, share, asset_names). It is never a go-live:
  its draft is rebuilt the same way, and its review is reported as its own
  record, `makeyourmindup:review:<payload_sha256[:12]>`, listed in that New
  York day's index (`makeyourmindup:derived:<day>:<n>`, engine/run/
  cc_records.py). autorelease reads both back by that exact sha and judges
  the review with engine/run/spec.py review_reason, never here.
- `growth-mix-plan` (the weekly ideas board, `growth.py mix plan`): the plan
  file's {"week_of", "targets", "weights", "moved", "slots", "concepts",
  "shortfalls"}, each concept {"concept_id", "lane", "idea", "claim",
  "source_url", "piece_id", "mock_sha256", "placements", "mock_links"?,
  "ready"?, "text_only"?, "concept_sha256"?}. The runner checks the closed
  shape against mix.json, recomputes every concept_sha256 and the plan's words
  and digest with engine/concepts.py and engine/mix.py, and asks it through
  cc_loop.plan_proposals: one plan proposal behind strategy, or, when a week
  passes 8,000 characters, parts in order (`makeyourmindup:mix:<week>`, then
  `:p2`, ...), one ask at a time, each part's concepts in its own report.
  A version record (`makeyourmindup:mixplan:<week>:<n>`) names the parts in
  force. Each mock's first view link rides as the ask's evidence. Beside the
  parts, never inside them, the runner records the week's slots
  (`makeyourmindup:mixslots:<week>:<plan key>:<i>`, which concept goes where
  and when) and, when the dispatch carries the optional "mock_files"
  {sha256: Drive file id}, the week's mock manifest
  (`makeyourmindup:mocks:<week>:<plan key>:<i>`), both keyed by the version's
  part digests (cc_records.plan_key), for the maker (engine/run/maker.py). A
  ready concept whose mock files are not all in mock_files is counted as
  `mock_file_missing`, and the maker holds it. The same plan sent again is
  already reported, part by part and version by version: only a slots or mock
  record not yet there is written, so a plan dispatched before these records
  existed gains them by being sent again, and his digests never move. With
  "records_only": true the runner writes those records and nothing else, and
  refuses (`records_only_plan_not_in_force`) unless every part and the version
  it rebuilds are already the plan in force in Control Center.
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

from engine import concepts as concept_rules, mix as mix_rules
from engine.cc_loop import NO_SPEND, decisions_paged, plan_proposals, revision
from engine.control_center import (SLUG, ProtocolError, _expiry_hold, _latest, _plan_open, _stops,
                                   build_report, canonical_json, objective, proposal, sha256_hex)
from engine.core import http_url, instant, ny_time, today, write_json
from engine.run import autorelease, buffer_api, cc_records
from engine.run.autorelease import (DUE_MARGIN, LINE_KEYS, MANIFEST_SCHEMA, MAX_REPORT_READS, _authority, draft_line,
                                    due_instant, line_digest, read_proposal, run_window, show_before_post_until,
                                    spec_digest, staged_report_run_id)
from engine.run.buffer_api import BufferAuthError, BufferError, CarryHold
from engine.run.release import ASSET_NAME, BUFFER_ID, CHANNELS, DUE_AT, HEX64, KRISH_CLICK_ONLY, account_hold
from engine.run.spec import RUN_ID as SPEC_RUN_ID
from engine.social import inventory

ROOT = Path(__file__).resolve().parents[2]
GO_LIVE, WEEK_PACKET, MAKE_PIECE = 'growth-go-live-manifest', 'growth-week-packet', 'growth-make-piece'
MIX_PLAN = 'growth-mix-plan'
EVENTS = (GO_LIVE, WEEK_PACKET, MAKE_PIECE, MIX_PLAN)
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
# A slot made from an approved concept: its concept and its review (never words of the post).
DERIVED_KEYS = frozenset({'concept_id', 'review'})
REVIEW_KEYS = frozenset({'slot_id', 'verdict', 'lens', 'payload_sha256', 'reader_answer', 'share', 'asset_names'})
CONCEPT_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
LENS = re.compile(r'^[a-z0-9][a-z0-9-]*$')
# growth-mix-plan: the plan file's own fields (a client_payload holds at most ten top-level keys).
MIX_KEYS = frozenset({'week_of', 'targets', 'weights', 'moved', 'slots', 'concepts', 'shortfalls'})
# Optional: each approved mock file's Drive file id, for the maker's downloads (never part of what he approves).
# records_only: write the week's slots and mock records and nothing else, for a plan already reported and in force.
MIX_OPTIONAL = frozenset({'mock_files', 'records_only'})
DRIVE_ID = re.compile(r'^[A-Za-z0-9_-]{10,128}$')
MAX_MOCK_FILES = 400
MIX_SLOT_KEYS = frozenset({'slot_id', 'channel', 'format', 'lane', 'day', 'due_at', 'concept_id'})
MIX_CONCEPT_KEYS = frozenset(concept_rules.DIGESTED)
MIX_CONCEPT_OPTIONAL = frozenset({'mock_links', 'ready', 'text_only', 'concept_sha256'})
MIX_MAX_SLOTS, MIX_MAX_CONCEPTS, MIX_MAX_LINKS, TEXT_MAX = 400, 200, 12, 2000
MAX_INDEX_PARTS = 24  # numbered day indexes and plan versions read before a lane holds loudly
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


def _slot_common(slot, keys, optional=frozenset()):
    _closed(slot, keys, optional, where='slot')
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
        _slot_common(slot, MANIFEST_SLOT_KEYS, DERIVED_KEYS)
        if set(slot) & DERIVED_KEYS:
            _derived(slot)
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


def _text(value, limit=TEXT_MAX):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _derived(slot):
    """A slot made from an approved concept: its concept_id and its closed review, both or neither."""
    if DERIVED_KEYS - set(slot):
        raise PayloadRejected('derived_needs_concept_and_review')
    if not isinstance(slot['concept_id'], str) or not CONCEPT_ID.match(slot['concept_id']):
        raise PayloadRejected('bad_concept_id')
    review = slot['review']
    _closed(review, REVIEW_KEYS, where='review')
    if not isinstance(review['slot_id'], str) or not SLOT_ID.match(review['slot_id']) \
            or not isinstance(review['verdict'], str) or not CONCEPT_ID.match(review['verdict']) \
            or not isinstance(review['lens'], str) or not LENS.match(review['lens']) \
            or not isinstance(review['payload_sha256'], str) or not HEX64.match(review['payload_sha256']):
        raise PayloadRejected('bad_review')
    for key in ('reader_answer', 'share'):
        if review[key] is not None and (not isinstance(review[key], dict) or len(canonical_json(review[key])) > 4000):
            raise PayloadRejected('bad_review')
    names = review['asset_names']
    if not isinstance(names, list) or len(names) > 20 or not all(isinstance(n, str) and ASSET_NAME.match(n)
                                                                  for n in names):
        raise PayloadRejected('bad_review')


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


def validate_mix_plan(value, root=None):
    """The mix plan's closed shape, checked against mix.json and the social records. Returns the
    plan as engine/mix.py builds it, with every concept's ready, text_only and concept_sha256
    recomputed (a value sent that differs is refused), and {concept_id: mock view links}."""
    _closed(value, MIX_KEYS, MIX_OPTIONAL)
    try:
        cfg = mix_rules.load(root or ROOT)
        week = mix_rules.week_days(value['week_of'])
        formats = inventory(root or ROOT)['format']
    except (ValueError, KeyError, TypeError, OSError):
        raise PayloadRejected('bad_week_of') from None
    channels, lanes = cfg['channels'], cfg['lanes']
    targets = value['targets']
    if not isinstance(targets, dict) or sorted(targets) != sorted(channels):
        raise PayloadRejected('bad_targets')
    for channel, row in targets.items():
        _closed(row, frozenset({'target', 'floor'}), where='targets')
        if not all(type(row[k]) is int for k in row) \
                or not 0 <= row['floor'] <= row['target'] <= mix_rules.max_daily_posts(channel) or row['target'] < 1:
            raise PayloadRejected('bad_targets')
    weights = value['weights']
    if not isinstance(weights, dict) or sorted(weights) != sorted(lanes) or any(
            type(w) is not int or not lanes[n]['min'] <= w <= lanes[n]['max'] for n, w in weights.items()):
        raise PayloadRejected('bad_weights')
    moved = value['moved']
    if not isinstance(moved, dict) or set(moved) - set(lanes):
        raise PayloadRejected('bad_moved')
    for row in moved.values():
        _closed(row, frozenset({'from', 'to', 'judged', 'score'}), where='moved')
        if not all(type(row[k]) is int for k in ('from', 'to', 'judged')) or type(row['score']) not in (int, float):
            raise PayloadRejected('bad_moved')
    slots = value['slots']
    if not isinstance(slots, list) or not slots or len(slots) > MIX_MAX_SLOTS:
        raise PayloadRejected('bad_slots')
    days = {mix_rules.DAYS[d.weekday()]: d for d in week}
    for slot in slots:
        _closed(slot, MIX_SLOT_KEYS, where='mix_slot')
        if slot['channel'] not in channels or slot['lane'] not in lanes or slot['day'] not in days \
                or slot['format'] != lanes[slot['lane']]['placements'][slot['channel']] \
                or not isinstance(slot['slot_id'], str) or not SLOT_ID.match(slot['slot_id']) \
                or not (slot['concept_id'] is None or (isinstance(slot['concept_id'], str)
                                                       and CONCEPT_ID.match(slot['concept_id']))) \
                or not isinstance(slot['due_at'], str) or not DUE_AT.match(slot['due_at']) \
                or due_instant(slot['due_at']) is None or ny_time(slot['due_at']).date() != days[slot['day']]:
            raise PayloadRejected('bad_mix_slot')
    _unique(slots, 'slot_id', 'duplicate_slot')
    concepts, links, placed = [], {}, {}
    for slot in slots:
        if slot['concept_id'] is not None:
            pair = {'channel': slot['channel'], 'format': slot['format']}
            row = placed.setdefault(slot['concept_id'], [])
            if pair not in row:
                row.append(pair)
    sent = value['concepts']
    if not isinstance(sent, list) or len(sent) > MIX_MAX_CONCEPTS:
        raise PayloadRejected('bad_concepts')
    for item in sent:
        _closed(item, MIX_CONCEPT_KEYS, MIX_CONCEPT_OPTIONAL, where='concept')
        concept = {key: item[key] for key in concept_rules.DIGESTED}
        ok = (isinstance(concept['concept_id'], str) and CONCEPT_ID.match(concept['concept_id'])
              and concept['lane'] in lanes and _text(concept['idea'])
              and (concept['claim'] is None or _text(concept['claim']))
              and (concept['source_url'] is None or (http_url(concept['source_url'])
                                                     and concept['source_url'].startswith('https://')))
              and (concept['piece_id'] is None or (isinstance(concept['piece_id'], str)
                                                   and PIECE_ID.match(concept['piece_id'])))
              and isinstance(concept['mock_sha256'], list) and len(concept['mock_sha256']) <= 20
              and all(isinstance(h, str) and HEX64.match(h) for h in concept['mock_sha256'])
              and isinstance(concept['placements'], list) and concept['placements']
              and all(isinstance(p, dict) and set(p) == {'channel', 'format'} and p['channel'] in channels
                      and p['format'] == lanes[concept['lane']]['placements'][p['channel']]
                      for p in concept['placements']))
        if not ok:
            raise PayloadRejected('bad_concept')
        if concept['placements'] != placed.get(concept['concept_id']):
            raise PayloadRejected('concept_placements_differ_from_slots')
        given = item.get('mock_links') or []
        if not isinstance(given, list) or len(given) > MIX_MAX_LINKS or not all(
                http_url(u) and u.startswith('https://') and len(u) <= 2000 for u in given):
            raise PayloadRejected('bad_mock_links')
        concept['text_only'] = all(formats[p['format']]['min_assets'] == 0 for p in concept['placements'])
        concept['ready'] = mix_rules.ready(concept)
        concept['concept_sha256'] = concept_rules.concept_sha256(concept) if concept['ready'] else None
        for key in ('ready', 'text_only', 'concept_sha256'):
            if key in item and item[key] != concept[key]:
                raise PayloadRejected('concept_' + key + '_differs')  # recomputed, never trusted
        if concept['ready'] and concept_rules.concept_errors(concept):
            raise PayloadRejected('bad_concept')
        if given:
            links[concept['concept_id']] = list(given)
        concepts.append(concept)
    _unique(concepts, 'concept_id', 'duplicate_concept')
    if set(placed) - {c['concept_id'] for c in concepts}:
        raise PayloadRejected('slot_names_unknown_concept')
    shortfalls = value['shortfalls']
    if not isinstance(shortfalls, list) or len(shortfalls) > MIX_MAX_SLOTS or not all(
            isinstance(f, dict) and set(f) == {'channel', 'day', 'lane', 'needs'}
            and all(_text(f[k], 200) for k in f) for f in shortfalls):
        raise PayloadRejected('bad_shortfalls')
    # GitHub delivers a client_payload with its keys reordered: every map is put back in mix.json's own
    # order, so the words he reads are the same whatever order the dispatch arrived in.
    targets = {c: {'target': targets[c]['target'], 'floor': targets[c]['floor']} for c in channels}
    weights = {n: weights[n] for n in lanes}
    moved = {n: {k: moved[n][k] for k in ('from', 'to', 'judged', 'score')} for n in lanes if n in moved}
    mix = {'week_of': week[0].isoformat(), 'targets': targets, 'weights': weights, 'moved': moved,
           'slots': slots, 'concepts': concepts, 'shortfalls': shortfalls}
    return mix, links, cfg


def validate_mock_files(value, mix):
    """(manifest, missing) for the optional mock_files {sha256: Drive file id}: None and 0 when it is absent.

    Every key is one of the plan's own mock hashes (`mock_file_not_in_plan` otherwise); missing counts the
    ready concepts with a mock file the manifest does not name (the maker holds each as mock_file_missing)."""
    if value is None:
        return None, 0
    if not isinstance(value, dict) or not value or len(value) > MAX_MOCK_FILES or not all(
            isinstance(k, str) and HEX64.match(k) and isinstance(v, str) and DRIVE_ID.match(v)
            for k, v in value.items()):
        raise PayloadRejected('bad_mock_files')
    known = {h for c in mix['concepts'] for h in c['mock_sha256']}
    if set(value) - known:
        raise PayloadRejected('mock_file_not_in_plan')
    missing = sum(1 for c in mix['concepts'] if c['ready'] and set(c['mock_sha256']) - set(value))
    return {k: value[k] for k in sorted(value)}, missing


VALIDATORS = {GO_LIVE: validate_manifest, WEEK_PACKET: validate_packet, MAKE_PIECE: validate_piece,
              MIX_PLAN: lambda value: value}


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
    # A week's mix plan (makeyourmindup:mix:...) authorises concepts, never a go-live: it is no go-live's plan.
    wanted = sorted(((d.get('decided_at') or '', pid) for pid, d in latest.items()
                     if d.get('stage') == 'plan' and d.get('decision') == 'approved'
                     and isinstance(d.get('payload_sha256'), str) and not pid.startswith(SLUG + ':mix:')),
                    reverse=True)
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
    except CarryHold as hold:
        return None, hold.code  # format_differs_from_draft: the label is not what the draft is
    except BufferAuthError:
        raise
    except BufferError as error:
        return None, error.code if error.code.startswith('asset_') else 'asset_download_failed'
    # The dispatch carries the maker's run-spec slot digest; the manifest line is signed
    # under the go-live domain (line_digest), so the two paths never share one (F105).
    if spec_digest(line) != slot['payload_sha256']:
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
    alts, tags, titles = [], [], []
    for asset in meta.get('assets') or []:
        inner = next(iter(asset.values())) if isinstance(asset, dict) and len(asset) == 1 else {}
        extra = (inner or {}).get('metadata') or {}
        if extra.get('altText'):
            alts.append(_quoted(extra['altText']))  # F110: alt text is public words, so he reads it
        tags += ['@' + str(t.get('handle')) for t in extra.get('userTags') or [] if isinstance(t, dict)]
        if extra.get('title'):
            titles.append(_quoted(extra['title']))
    if alts:
        bits.append('alt text ' + ', '.join(alts))
    if tags:
        bits.append('tags ' + ', '.join(tags))
    if titles:
        bits.append('video title ' + ', '.join(titles))
    if not bits:
        return None
    return NAMES.get(line['channel'], line['channel']) + ' post ' + line['slot_id'] + ': ' + '; '.join(bits) + '.'


def post_day(line):
    """The New York calendar day a line goes out on, or None when it has no time."""
    return ny_time(line['due_at']).date() if line.get('due_at') else None


def _day_words(day):
    return day.strftime('%A ') + str(day.day) + day.strftime(' %B')


def golive_words(lines, kind, part, parts, day, root, express, on=None):
    """The title and why: in plain words, what his yes does. on is the New York day its
    posts go out (R94: a yes authorises exactly that day's posts, nothing more)."""
    where = _channels(lines)
    when = ' on ' + _day_words(on) if on else ''
    if kind == 'item':
        line = lines[0]
        title = 'New kind of post, yours to check: ' + _a(line['format']) + ' on ' + where + (',' + when if on else '')
        why = 'This is ' + _a(line['format']) + ', a kind of post you see one at a time, so it comes to you on its own. '
    elif express:
        title = 'Your quick idea, ready to go' + when + ': ' + _posts(len(lines)) + ' on ' + where
        why = 'Built from the idea you added in Buffer Ideas. '
    else:
        title = 'Go live' + when + ': ' + _posts(len(lines)) + ' on ' + where
        why = ''
    if parts > 1:
        title += ' (part ' + str(part) + ' of ' + str(parts) + ')'
        why += ('This day is too long for one approval, so it comes in ' + str(parts) + ' parts, one after another. '
                if on else 'This batch is too long for one approval, so it comes in ' + str(parts)
                + ' parts, one after another. ')
    engine = [line for line in lines if line['publish_mode'] == 'engine']
    clicks = len(lines) - len(engine)
    if engine:
        why += ('Yes schedules ' + ('this exact post' if len(engine) == 1 else 'these ' + str(len(engine)) + ' exact posts')
                + ' in Buffer' + (when + ', New York time,' if on else ' for the time shown,') + ' once. '
                + ('Nothing on another day: each day comes to you as its own go-live. ' if on else '')
                + 'A yes schedules each post about an hour before it is due. Until then, No stops it. ')
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


def by_day(lines):
    """The batch lines grouped by the New York day they go out, in day order. A line
    with no time (a draft for his own click, which schedules nothing) rides with the
    first day, or alone when no line has a time."""
    days = {}
    for line in lines:
        days.setdefault(post_day(line), []).append(line)
    undated = days.pop(None, [])
    order = sorted(days)
    if not order:
        return [(None, undated)] if undated else []
    days[order[0]] = undated + days[order[0]]
    return [(on, days[on]) for on in order]


def golive_proposals(manifest, lines, formats, plan_id, now, root, slots):
    """The go-lives one dispatch becomes: one per New York day (R94, F106), each day
    split into parts of PAYLOAD_CAP characters when it must be, and each new kind of post
    on its own, so one press never authorises more than one day's posts."""
    run_id, express = manifest['run_id'], bool(manifest.get('express'))
    base = SLUG + ':golive:' + _rest(run_id)
    review = {line['slot_id'] for line, slot in lines if needs_own_review(slot, formats)}
    batch = [line for line, _ in lines if line['slot_id'] not in review]
    items = [line for line, _ in lines if line['slot_id'] in review]
    day = today(now)

    def fits(kind, on):
        # Worst-case numbering, so a group that fits here fits once it is numbered.
        return lambda group: len(' '.join(golive_words(group, kind, 99, 99, day, root, express, on)[1].split())) \
            <= WHY_CAP

    days = by_day(batch)
    groups = []
    for on, day_lines in days:
        parts = pack(run_id, day_lines, slots, fits('batch', on))
        prefix = base if len(days) == 1 else base + ':' + on.isoformat()
        groups += [('batch', on, prefix, len(parts), number, part) for number, part in enumerate(parts, 1)]
    for line in items:
        on = post_day(line)
        groups += [('item', on, base, 1, 1, part) for part in pack(run_id, [line], slots, fits('item', on))]
    out = []
    numbers = {'item': 0}
    for kind, on, prefix, parts, number, group in groups:
        if kind == 'batch':
            pid = prefix if parts == 1 else prefix + ':p' + str(number)
        else:
            numbers['item'] += 1
            pid = base + ':item-' + str(numbers['item'])
        title, why = golive_words(group, kind, number, parts, day, root, express, on)
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


# Posts made from an approved concept ---------------------------------------------------------

def review_record(slot, line):
    """The record autorelease reads back by this slot's exact payload_sha256 (cc_records.REVIEW).

    The post's words are never in it: autorelease rebuilds them from the Buffer draft,
    and the digest binds them. Its review is judged there, by spec.review_reason."""
    review = slot['review']
    body = {key: review[key] for key in ('slot_id', 'verdict', 'lens', 'payload_sha256')}
    if review['reader_answer'] is not None:
        body['send_test'] = {'reader_answer': review['reader_answer']}
    return {'schema': cc_records.REVIEW, 'payload_sha256': slot['payload_sha256'],
            'slot': {'slot_id': slot['slot'], 'channel': line['channel'], 'format': slot['format'],
                     'due_at': slot['due_at'], 'link_placement': slot['link_placement'],
                     'publish_mode': slot['publish_mode'], 'buffer_draft_id': slot['buffer_draft_id'],
                     'concept_id': slot['concept_id'], 'share': review['share'],
                     'asset_names': review['asset_names']},
            'review': body}


def derived_record(buffer, slot, fetch, now, window=None):
    """(review record, None) for a slot made from a concept, or (None, hold code). Never a go-live."""
    if slot['channel'] not in concept_rules.CONCEPT_CHANNELS or slot['publish_mode'] != 'engine' \
            or slot['due_at'] is None:
        return None, 'derived_not_a_concept_post'
    review = slot['review']
    if review['payload_sha256'] != slot['payload_sha256'] or review['slot_id'] != slot['slot']:
        return None, 'review_for_another_payload'
    line, code = rebuild(buffer, slot, fetch, now, window)
    if code:
        return None, code
    if len(review['asset_names']) != len(line['assets']):
        return None, 'asset_count_differs'
    record = review_record(slot, line)
    if not cc_records.fits(cc_records.REVIEW, record):
        return None, 'review_too_large'
    return record, None


def derived_reports(records, now, root):
    """One review report per derived slot, at review:<payload_sha256[:12]>, and each New York day's entries."""
    rev, reports, days = revision(root), [], {}
    for record in records:
        reports.append(cc_records.record_report(
            cc_records.review_run_id(record['payload_sha256']), cc_records.REVIEW, record,
            ['Review of a post made from concept ' + record['slot']['concept_id'] + ', for the release that'
             ' schedules it once its concept is approved', 'Posted, sent, published and spent nothing'], now, rev))
        day = ny_time(record['slot']['due_at']).date().isoformat()
        days.setdefault(day, []).append({'payload_sha256': record['payload_sha256'],
                                         'due_at': record['slot']['due_at'], 'channel': record['slot']['channel'],
                                         'concept_id': record['slot']['concept_id'],
                                         'buffer_draft_id': record['slot']['buffer_draft_id']})
    return reports, {day: sorted(entries, key=lambda e: (instant(e['due_at']), e['payload_sha256']))
                     for day, entries in sorted(days.items())}


def index_report(day, number, entries, now, root):
    record = {'schema': cc_records.INDEX, 'day': day, 'entries': entries}
    return cc_records.record_report(cc_records.index_run_id(day, number), cc_records.INDEX, record,
                                    [_posts(len(entries)) + ' made from approved concepts, due ' + day + ' (New York)',
                                     'Posted, sent, published and spent nothing'], now, revision(root))


def deliver_records(cc, reports, schema, summary):
    """Post each record report once. A conflict is read back: the same record already stored
    counts as reported (a later run differs only in its time); anything else is loud."""
    for report in reports:
        posted = cc.post_report(report)
        if posted['accepted']:
            summary['reports']['posted'] += 1
            summary['reports']['readback_matches'] += int(bool(posted['readback_matches']))
        elif cc_records.read_record(cc, report['run_id'], schema) == cc_records.record_of(report, schema):
            summary['reports']['already_reported'] += 1
        else:
            summary['loud'].append('report_conflict')


def deliver_index(cc, day, entries, now, root, summary):
    """Index the day's entries not yet indexed, as the next numbered index (one runs at a time:
    handoff.yml's concurrency group). Every entry already indexed: nothing new is posted."""
    found = cc_records.probe(cc, lambda n: cc_records.index_run_id(day, n), cc_records.INDEX, MAX_INDEX_PARTS)
    if found is None:
        summary['loud'].append('derived_index_full')
        return
    known = {e.get('payload_sha256') for record in found for e in record.get('entries') or [] if isinstance(e, dict)}
    fresh = [e for e in entries if e['payload_sha256'] not in known]
    if not fresh:
        summary['reports']['already_reported'] += 1
        return
    deliver_records(cc, [index_report(day, len(found) + 1, fresh, now, root)], cc_records.INDEX, summary)


# The weekly ideas board (growth-mix-plan) --------------------------------------------------------

def check_mock_links(mix, links, fetch):
    """Every mock link he opens from the ask is one of the files he approves (review 3, S7).

    Each link is downloaded fresh and must hash to one of its concept's mock_sha256,
    so the picture shown and the hash bound are the same file. A link that cannot be
    read, or reads as another file, refuses the whole plan: nothing is half shown."""
    by_id = {c['concept_id']: c for c in mix['concepts']}
    for cid, urls in sorted(links.items()):
        mocks = set(by_id[cid]['mock_sha256'])
        for url in urls:
            try:
                got = fetch(url)
            except (BufferError, CarryHold):
                raise PayloadRejected('mock_link_unreadable') from None
            if (got[0] if isinstance(got, tuple) else got) not in mocks:
                raise PayloadRejected('mock_link_differs_from_mock')


def part_record(mix, number, parts, group):
    """What a plan part's report carries beside its proposal: its concepts, whole, and the week's targets."""
    return {'schema': cc_records.PART, 'week_of': mix['week_of'], 'part': number, 'parts': parts,
            'targets': mix['targets'],
            'concepts': [dict({key: c[key] for key in concept_rules.DIGESTED}, ready=c['ready'],
                              text_only=c['text_only'], concept_sha256=c['concept_sha256']) for c in group]}


def week_label(week_of):
    return mix_rules.proposal_id(week_of).rsplit(':', 1)[1]


def mix_reports(mix, links, cfg, now, root):
    """(part reports, version record) for the week's plan. Each part is a plan proposal behind strategy in its
    own report (`<proposal_id>:<payload_sha256[:12]>`, so autorelease reads it back by the digest he decided
    on), carrying its concepts; the version record names the parts in force. ValueError when a part cannot
    be built (a concept that fits no part on its own)."""
    fits = lambda group: cc_records.fits(cc_records.PART, part_record(mix, 99, 99, group))
    built, groups = mix_rules.part_proposals(mix, cfg, fits, links)
    items, hold = plan_proposals(dict(mix, parts=built))
    if hold:
        raise ValueError(hold['reason'])
    rev, reports = revision(root), []
    for number, (item, group) in enumerate(zip(items, groups), 1):
        ready = sum(1 for c in group if c['ready'])
        words = ['Mix plan for the week of ' + mix['week_of'] + ('' if len(items) == 1 else ', part ' + str(number)
                                                                 + ' of ' + str(len(items)))
                 + ': ' + str(ready) + ' ideas and their mocks for Krish to approve',
                 'Posted, sent, published and spent nothing']
        reports.append(cc_records.record_report(staged_report_run_id(item['proposal_id'], item['payload_sha256']),
                                                cc_records.PART, part_record(mix, number, len(items), group), words,
                                                now, rev, [item]))
    version = {'schema': cc_records.VERSION, 'week_of': mix['week_of'],
               'parts': [{'proposal_id': i['proposal_id'], 'payload_sha256': i['payload_sha256']} for i in items]}
    return reports, version


def week_records(mix, version, files, now, root):
    """The week's slots and, with files, its mock manifest: record reports at the version's plan key, in
    numbered chunks. They sit beside the plan parts and never change a part's words or digest."""
    parts, label = version['parts'], week_label(mix['week_of'])
    key, rev = cc_records.plan_key(parts), revision(root)

    def slots(group, number, total):
        return {'schema': cc_records.SLOTS, 'week_of': mix['week_of'], 'plan': parts, 'chunk': number,
                'chunks': total, 'weights': mix['weights'], 'moved': mix['moved'],
                'shortfalls': len(mix['shortfalls']), 'slots': group}

    def mocks(group, number, total):
        return {'schema': cc_records.MOCKS, 'week_of': mix['week_of'], 'plan': parts, 'chunk': number,
                'chunks': total, 'files': dict(group)}

    out = []
    for record in cc_records.chunked(cc_records.SLOTS, slots, mix['slots']):
        out.append((cc_records.SLOTS, cc_records.record_report(
            cc_records.slots_run_id(label, key, record['chunk']), cc_records.SLOTS, record,
            ['The slots of the mix plan for the week of ' + mix['week_of'] + ', chunk ' + str(record['chunk'])
             + ' of ' + str(record['chunks']) + ', for the maker', 'Posted, sent, published and spent nothing'],
            now, rev)))
    if files:
        for record in cc_records.chunked(cc_records.MOCKS, mocks, sorted(files.items())):
            out.append((cc_records.MOCKS, cc_records.record_report(
                cc_records.mocks_run_id(label, key, record['chunk']), cc_records.MOCKS, record,
                ['Where the approved mock files of the week of ' + mix['week_of'] + ' are kept, chunk '
                 + str(record['chunk']) + ' of ' + str(record['chunks']), 'Posted, sent, published and spent nothing'],
                now, rev)))
    return out


def in_force(cc, week_of, version):
    """True when this version's parts are the plan in force (the highest numbered version) and each part's
    own report is there, read back by the digest he decides on: nothing of his would move."""
    label = week_label(week_of)
    found = cc_records.probe(cc, lambda n: cc_records.version_run_id(label, n), cc_records.VERSION, MAX_INDEX_PARTS)
    if not found or found[-1].get('parts') != version['parts']:
        return False
    return all(read_proposal(cc, p['proposal_id'], p['payload_sha256'])[0] is not None for p in version['parts'])


def version_report(week_of, number, version, now, root):
    return cc_records.record_report(cc_records.version_run_id(week_label(week_of), number), cc_records.VERSION,
                                    version, ['The mix plan in force for the week of ' + week_of + ': '
                                              + str(len(version['parts'])) + ' part(s)',
                                              'Posted, sent, published and spent nothing'], now, revision(root))


def deliver_version(cc, week_of, version, now, root, summary):
    """The plan in force is the highest numbered version: post this one unless it already is."""
    label = week_label(week_of)
    found = cc_records.probe(cc, lambda n: cc_records.version_run_id(label, n), cc_records.VERSION, MAX_INDEX_PARTS)
    if found is None:
        summary['loud'].append('mix_versions_full')
        return
    if found and found[-1].get('parts') == version['parts']:
        summary['reports']['already_reported'] += 1
        return
    deliver_records(cc, [version_report(week_of, len(found) + 1, version, now, root)], cc_records.VERSION, summary)


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
        if event == MIX_PLAN:
            mix, links, cfg = validate_mix_plan(payload, root)
            files, missing = validate_mock_files(payload.get('mock_files'), mix)
            records_only = payload.get('records_only', False)
            if not isinstance(records_only, bool):
                raise PayloadRejected('bad_records_only')
            check_mock_links(mix, links, fetch or (lambda url: buffer_api.download_sha256(url)))
            try:
                reports, version = mix_reports(mix, links, cfg, now, root)
            except ValueError:
                reports, version = [held_report(event, mix_rules.proposal_id(mix['week_of']), slots, now, root,
                                                'mix_plan_part_over_cap')], None
                summary['holds']['mix_plan_part_over_cap'] = 1
            records = week_records(mix, version, files, now, root) if version else []
            if version and missing:
                summary['holds']['mock_file_missing'] = missing
            summary['proposals'] = {'plan': len(reports)} if version else {}
            summary['reports']['built'] = len(reports) + (1 if version else 0) + len(records)
            write_json(path, {'event': event, 'deliver': bool(deliver), 'reports': reports, 'version': version,
                              'records': [report for _, report in records]})
            if records_only and (version is None or (cc is not None and not in_force(cc, mix['week_of'], version))):
                raise PayloadRejected('records_only_plan_not_in_force')
            if deliver:
                if not records_only:
                    deliver_reports(cc, reports, summary)
                    if version:
                        deliver_version(cc, mix['week_of'], version, now, root, summary)
                for schema, report in records:
                    deliver_records(cc, [report], schema, summary)
            return _finish(summary, slots)
        VALIDATORS[event](payload)
        if event == MAKE_PIECE:
            # The maker that sent it does the making; the runner only records that it was asked.
            summary['recorded'] = 1
            write_json(path, {'event': event, 'deliver': bool(deliver), 'recorded': 1, 'reports': []})
            return _finish(summary, slots)
        # Every page of his decisions (F100): a No past the first 100 still stops the plan.
        decisions = decisions_paged(cc, now - autorelease.LOOKBACK)
        if decisions is None:
            raise autorelease.Unpaged()
        plan, reason = open_plan(cc, decisions, now)
        records, days = [], {}
        if event == GO_LIVE:
            fetch = fetch or (lambda url: buffer_api.download_sha256(url))
            window = run_window(payload['run_id'])
            lines = []
            for slot in payload['slots']:
                if 'concept_id' in slot:
                    # Made from a concept he approved in the mix plan: its review, never a go-live.
                    record, code = derived_record(buffer, slot, fetch, now, window)
                    if code:
                        slots.hold(code)
                    else:
                        slots.count('derived_recorded')
                        records.append(record)
                elif plan is not None:
                    line, code = rebuild(buffer, slot, fetch, now, window)
                    if code:
                        slots.hold(code)
                    else:
                        if slot['channel'] in KRISH_CLICK_ONLY and slot['publish_mode'] != 'krish_click':
                            slots.count('linkedin_to_krish_click')
                        lines.append((line, slot))
                else:
                    slots.hold(reason)
            items = golive_proposals(payload, lines, new_formats(root), plan and plan['proposal_id'], now, root,
                                     slots) if lines else []
            activity = [{'line': 'Rebuilt ' + _posts(len(lines)) + " from their Buffer drafts; each matched the dispatch's digest"},
                        {'line': 'Posted, sent, published and spent nothing'}]
            reports = reports_for(items, slots, now, root, activity) if items else \
                ([held_report(event, payload['run_id'], slots, now, root)] if slots.holds or not records else [])
            derived, days = derived_reports(records, now, root) if records else ([], {})
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
            derived = []
        summary['reports']['built'] = len(reports) + len(derived) + len(days)
        write_json(path, {'event': event, 'deliver': bool(deliver), 'reports': reports, 'derived': derived,
                          'days': days})
        if deliver:
            # Reviews first, then the day's index that points at them, then the go-lives.
            deliver_records(cc, derived, cc_records.REVIEW, summary)
            for day, entries in days.items():
                deliver_index(cc, day, entries, now, root, summary)
            deliver_reports(cc, reports, summary)
    except PayloadRejected as error:
        summary['error'] = 'payload_rejected_' + error.code
    except BufferAuthError as error:
        summary['error'] = error.code
    except BufferError as error:
        summary['error'] = error.code
    except ProtocolError as error:
        summary['error'] = 'control_center_' + error.code
    except autorelease.Unpaged:
        summary['error'] = 'decisions_unpaged'
    except ValueError as error:
        summary['error'] = 'record_' + (str(error) if re.match(r'^[a-z_]{1,40}$', str(error)) else 'unreadable')
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
    records_only = args.event == MIX_PLAN and isinstance(payload, dict) and payload.get('records_only') is True
    if args.event in (GO_LIVE, WEEK_PACKET) or (args.event == MIX_PLAN and (args.deliver or records_only)):
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
