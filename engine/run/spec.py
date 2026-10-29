"""The run spec Krish signs: schema, lint, computed fields and computed readiness.

Offline only. Nothing here posts, schedules, sends or spends. Readiness is
derived from evidence files under .scratch/runs/<run>/; no session writes a stage.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re

from ..control_center import sha256_hex
from ..copy_lint import copy_lint_errors
from ..core import TIMEZONE, UTC, calendar_date, http_url, instant, ny_time, read_json, write_json
from ..packs import prose_errors
from ..share import (compare_send_test, cta_applies, cta_errors, share_errors, share_line,
                     slot_send_test_request)
from ..social import inventory, validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / 'specs' / 'schema' / 'run-spec.schema.json'
RUNS = Path('.scratch') / 'runs'
STAGES = ('drafted', 'linted', 'reviewed', 'signed', 'queued', 'live', 'measured', 'verdict')
DIGESTED = ('channel', 'format', 'words', 'assets', 'link_placement', 'due_at', 'publish_mode')
SHA = re.compile(r'^[0-9a-f]{64}$')
RUN_ID = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9:.-]{0,118}[A-Za-z0-9])?$')
LENS = re.compile(r'^[a-z0-9][a-z0-9-]*$')
WINDOW = re.compile(r'^[1-9][0-9]*[hd]$')
RUNG = re.compile(r'^\s*-\s*\[(\d{4}-\d{2}-\d{2}),\s*(\d+)\]\s*$')
KRISH_MIN = {'weekday': 20, 'sunday': 30}
VERDICTS = ('works', 'neutral', 'fails', 'insufficient')
LENGTH = {'week': 7, 'piece': 8, 'express': 1}


# Computed fields ------------------------------------------------------------

def payload(slot):
    """Exactly what Krish signs for one slot; no other field moves the digest."""
    return {'channel': slot['channel'], 'format': slot['format'], 'words': slot['words'],
            'assets': [asset['sha256'] for asset in slot['assets']],
            'link_placement': slot['link_placement'], 'due_at': slot['due_at'],
            'publish_mode': slot['publish_mode']}


def payload_sha256(slot):
    return sha256_hex(payload(slot))


def ladder(root=ROOT):
    """The weekly ladder from docs/NORTH_STAR.md, keyed by its Monday."""
    text = (Path(root) / 'docs' / 'NORTH_STAR.md').read_text(encoding='utf-8-sig')
    if '```yaml north-star-metric' not in text:
        raise ValueError('docs/NORTH_STAR.md has no north-star-metric block')
    lines = text.split('```yaml north-star-metric', 1)[1].split('```', 1)[0].splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == 'ladder:']
    rungs = {}
    for line in lines[starts[0] + 1:] if starts else []:
        match = RUNG.match(line)
        if not match:
            break
        rungs[calendar_date(match.group(1))] = int(match.group(2))
    if not rungs:
        raise ValueError('docs/NORTH_STAR.md has no ladder')
    return rungs


def monday(value):
    day = ny_time(value).date()
    return day - dt.timedelta(days=day.weekday())


def week_target(start, root=ROOT):
    week = monday(start)
    rungs = ladder(root)
    if week not in rungs:
        raise ValueError('no North Star ladder rung for the week of ' + week.isoformat())
    return rungs[week]


def ny_midnight(day):
    """Local midnight in New York, offset included. DST changes at 02:00, so 05:00 UTC shares it."""
    offset = ny_time(dt.datetime(day.year, day.month, day.day, 5, tzinfo=UTC)).utcoffset()
    return dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone(offset))


def computed(spec, root=ROOT):
    """A copy with week_target and every payload_sha256 filled from their sources.

    A week with no ladder rung keeps its week_target; lint reports it.
    """
    spec = json.loads(json.dumps(spec))
    try:
        spec['north_star'] = {'week_target': week_target(spec['window']['start'], root)}
    except ValueError:
        pass
    for slot in spec['slots']:
        slot['payload_sha256'] = payload_sha256(slot)
        derived = forward_line(slot)
        if derived is not None:
            slot['forward_line'] = derived
    return spec


def forward_line(slot):
    """The forward_line a slot's share block computes (engine/share.py:share_line), or None without a valid one."""
    share = slot.get('share') if isinstance(slot, dict) else None
    if not isinstance(share, dict):
        return None
    try:
        return share_line(share)
    except ValueError:
        return None


def snackable(record):
    """A format record marked snackable: its slots are built to be sent (Krish, 2026-10-28)."""
    return isinstance(record, dict) and record.get('snackable') is True


def skeleton(start, kind='week', run_id=None, root=ROOT):
    if kind not in LENGTH:
        raise ValueError('kind must be week, piece or express')
    day = calendar_date(start)
    if kind == 'week':
        day -= dt.timedelta(days=day.weekday())
    if run_id is None:
        year, week = day.isocalendar()[:2]
        run_id = ('makeyourmindup:%d-W%02d:week' % (year, week) if kind == 'week'
                  else 'makeyourmindup:' + day.isoformat() + ':' + kind)
    window = {'start': ny_midnight(day).isoformat(),
              'end': ny_midnight(day + dt.timedelta(days=LENGTH[kind])).isoformat(), 'tz': TIMEZONE}
    return computed({'schema': 'growth-run-spec/1', 'run_id': run_id, 'kind': kind, 'parent_run_id': None,
                     'window': window, 'north_star': {'week_target': 0}, 'secondary_targets': [],
                     'inputs': [], 'slots': [], 'experiments': [],
                     'budgets': {'krish_min': dict(KRISH_MIN), 'spend_usd': 0}, 'signature': None}, root)


# Lint -----------------------------------------------------------------------

def lint_digest(spec):
    """What lint.json is bound to: the spec less its signature and Buffer draft ids.

    Signing and queueing add those two fields later; neither changes what was linted.
    """
    spec = json.loads(json.dumps(spec))
    spec.pop('signature', None)
    for slot in spec.get('slots') or []:
        if isinstance(slot, dict):
            slot.pop('buffer_draft_id', None)
    return sha256_hex(spec)


def window_errors(spec):
    """The window must match its kind: New York midnights, 7, 8 or 1 days, a week from Monday."""
    start, end = ny_time(spec['window']['start']), instant(spec['window']['end'])
    if end <= start:
        return ['the window must end after it starts']
    errors = []
    if start.time() != dt.time(0, 0):
        errors.append('window.start must be midnight in New York')
    if spec['kind'] == 'week' and start.weekday() != 0:
        errors.append('a week starts on a Monday in New York')
    if end != ny_midnight(start.date() + dt.timedelta(days=LENGTH[spec['kind']])):
        errors.append('a ' + spec['kind'] + ' window is ' + str(LENGTH[spec['kind']])
                      + ' New York days, ending at midnight')
    return errors


def finding(code, at, message, slot_id=None):
    return {'code': code, 'at': at, 'slot_id': slot_id, 'message': message}


def social_records(root=ROOT):
    found = inventory(root)
    return {'channel': found['channel'], 'format': found['format']}


def daily_cap(record):
    """Scheduled posts a channel takes per New York day, from its record; None means no engine cap.

    A human-only channel (LinkedIn) records null: its slots are unscheduled drafts.
    """
    cap = record.get('daily_posts_target') if isinstance(record, dict) else None
    return cap if isinstance(cap, int) and not isinstance(cap, bool) else None


def _slot(slot, at, channels, formats, tests, manifest, window):
    errors, warnings = [], []
    sid = slot['slot_id']
    channel, fmt = channels.get(slot['channel']), formats.get(slot['format'])
    if channel is None:
        errors.append(finding('unknown_channel', at + '.channel', 'unknown channel ' + slot['channel'], sid))
    if fmt is None:
        errors.append(finding('unknown_format', at + '.format', 'unknown format ' + slot['format'], sid))
    if channel and fmt and (slot['format'] not in channel['formats'] or slot['channel'] not in fmt['channels']):
        errors.append(finding('format_not_allowed', at + '.format',
                              slot['format'] + ' is not a format of ' + slot['channel'], sid))
    if channel:
        expected = 'krish_click' if channel['publication_mode'] == 'human_publish_only' else 'engine'
        if slot['publish_mode'] != expected:
            errors.append(finding('publish_mode', at + '.publish_mode',
                                  slot['channel'] + ' slots are ' + expected + ' (docs/PUBLISHING-AUTHORITY.md)', sid))
    if slot['publish_mode'] == 'krish_click' and slot['due_at'] is not None:
        errors.append(finding('krish_click_due_at', at + '.due_at',
                              'a krish_click slot stays an unscheduled draft: due_at must be null', sid))
    errors += [finding('prose', at + '.words', 'words ' + e, sid) for e in prose_errors(slot['words'])]
    try:
        lint = copy_lint_errors(slot['words'], 'channel_copy')
    except ValueError as exc:
        lint = ['copy lint could not run: ' + str(exc)]
    errors += [finding('copy_lint', at + '.words', 'words: ' + e, sid) for e in lint]
    # Built to be sent (Krish, 2026-10-28): a snackable slot says why one person sends it to another, its
    # forward_line is computed from that, and the share comes from the content, never a request.
    snack = snackable(fmt)
    share = slot.get('share')
    if snack and share is None:
        errors.append(finding('share_required', at + '.share', 'a snackable slot needs a share block: who sends it'
                              ' to whom, for which job, in what words (social/share.json)', sid))
    elif share is not None:
        found = share_errors(share, snack)
        errors += [finding('share', at + '.share', 'share ' + e, sid) for e in found]
        derived = forward_line(slot)
        if not found and derived is not None and slot['forward_line'] != derived:
            errors.append(finding('forward_line', at + '.forward_line', 'forward_line is computed from share:'
                                  ' run new --from', sid))
    if cta_applies(snack):
        errors += [finding('share_cta', at + '.words', 'words ask for the share (' + e + '); the share must come'
                           ' from the content (social/share.json)', sid) for e in cta_errors(slot['words'])]
    warnings += [finding('forward_line_prose', at + '.forward_line', 'forward_line ' + e, sid)
                 for e in prose_errors(slot['forward_line'])]
    listed, approved = manifest
    for j, asset in enumerate(slot['assets']):
        if not SHA.match(asset['sha256']):
            errors.append(finding('asset_sha256', at + '.assets[%d].sha256' % j,
                                  'asset sha256 must be 64 lowercase hex characters', sid))
        elif slot['publish_mode'] == 'engine' and asset['sha256'] not in approved:
            errors.append(finding('creative_not_approved', at + '.assets[%d]' % j,
                                  'an engine slot uses only approved creative: this asset is in no manifest'
                                  ' of an input with a creative_approval_ref (docs/PUBLISHING-AUTHORITY.md)', sid))
        elif asset['sha256'] not in listed:
            warnings.append(finding('asset_not_in_manifest', at + '.assets[%d]' % j,
                                    'asset is not listed in any input manifest', sid))
    if fmt and (len(slot['assets']) < fmt['min_assets']
                or (fmt['max_assets'] is not None and len(slot['assets']) > fmt['max_assets'])):
        warnings.append(finding('asset_count', at + '.assets', 'asset count is outside the ' + slot['format'] + ' bounds', sid))
    arm = slot['experiment_arm']
    if arm is not None and (slot['channel'] not in tests or arm not in tests[slot['channel']]['arms']):
        errors.append(finding('experiment_arm', at + '.experiment_arm',
                              'experiment_arm ' + arm + ' is not a registered arm on ' + slot['channel'], sid))
    if slot['payload_sha256'] != payload_sha256(slot):
        errors.append(finding('payload_sha256', at + '.payload_sha256',
                              'payload_sha256 is computed; it does not match this slot (run new --from)', sid))
    if slot['due_at'] is not None and not window[0] <= instant(slot['due_at']) < window[1]:
        warnings.append(finding('due_outside_window', at + '.due_at', 'due_at falls outside the run window', sid))
    if slot['publish_mode'] == 'engine' and slot['due_at'] is None:
        cap = daily_cap(channel)
        warnings.append(finding('engine_unscheduled', at + '.due_at',
                                'an engine slot needs a due_at to release'
                                + ('' if cap is None else ', and only scheduled slots count towards the '
                                   + slot['channel'] + ' cap of ' + str(cap) + ' a day'), sid))
    return errors, warnings


def lint(spec, records=None, root=ROOT):
    """Errors block the run; warnings are soft guidance only."""
    try:
        validate(spec, read_json(SCHEMA))
    except ValueError as exc:
        return {'errors': [finding('schema', '$', str(exc))], 'warnings': []}
    records = records or social_records(root)
    channels, formats = records['channel'], records['format']
    errors, warnings = [], []
    window = (instant(spec['window']['start']), instant(spec['window']['end']))
    errors += [finding('window', '$.window', message) for message in window_errors(spec)]
    try:
        target = week_target(spec['window']['start'], root)
        if spec['north_star']['week_target'] != target:
            errors.append(finding('week_target', '$.north_star.week_target',
                                  'week_target is computed: the ladder rung for the week of '
                                  + monday(spec['window']['start']).isoformat() + ' is ' + str(target)))
    except ValueError as exc:
        errors.append(finding('week_target', '$.north_star.week_target', str(exc)))
    if spec['budgets']['spend_usd'] != 0:
        errors.append(finding('spend', '$.budgets.spend_usd', 'zero paid: spend_usd must be 0'))
    for key, limit in sorted(KRISH_MIN.items()):
        if spec['budgets']['krish_min'][key] > limit:
            warnings.append(finding('krish_minutes', '$.budgets.krish_min.' + key,
                                    'above the plan budget of ' + str(limit) + ' minutes'))
    tests = {}
    for i, test in enumerate(spec['experiments']):
        at = '$.experiments[%d]' % i
        if test['channel'] not in channels:
            errors.append(finding('unknown_channel', at + '.channel', 'unknown channel ' + test['channel']))
        if test['channel'] in tests:
            errors.append(finding('experiment_per_channel', at, 'at most one experiment per channel: ' + test['channel']))
        else:
            tests[test['channel']] = test
    listed, approved = set(), set()
    for i, item in enumerate(spec['inputs']):
        for j, entry in enumerate((item['manifest'] or {}).get('files', [])):
            if not SHA.match(entry['sha256']):
                errors.append(finding('asset_sha256', '$.inputs[%d].manifest.files[%d].sha256' % (i, j),
                                      'manifest sha256 must be 64 lowercase hex characters'))
            listed.add(entry['sha256'])
            if item['creative_approval_ref'] is not None:
                approved.add(entry['sha256'])
    seen, per_day = set(), {}
    for i, slot in enumerate(spec['slots']):
        at = '$.slots[%d]' % i
        if slot['slot_id'] in seen:
            errors.append(finding('duplicate_slot_id', at + '.slot_id', 'slot_id must be unique', slot['slot_id']))
        seen.add(slot['slot_id'])
        more, soft = _slot(slot, at, channels, formats, tests, (listed, approved), window)
        errors += more
        warnings += soft
        if slot['due_at'] is not None:
            key = (slot['channel'], ny_time(slot['due_at']).date().isoformat())
            per_day.setdefault(key, []).append(slot['slot_id'])
    for (channel, day), ids in sorted(per_day.items()):
        cap = daily_cap(channels.get(channel))
        if cap is not None and len(ids) > cap:
            errors.append(finding('posts_per_day', '$.slots', str(len(ids)) + ' scheduled ' + channel + ' slots on '
                                  + day + ' (New York); its record allows at most ' + str(cap) + ' a day'))
    for channel, test in sorted(tests.items()):
        if not any(s['channel'] == channel and s['experiment_arm'] for s in spec['slots']):
            warnings.append(finding('experiment_unused', '$.experiments', 'experiment ' + test['id'] + ' has no slot on an arm'))
    return {'errors': errors, 'warnings': warnings}


def lint_report(spec, records=None, root=ROOT):
    result = lint(spec, records, root)
    try:
        digest = lint_digest(spec)
    except (ValueError, AttributeError):
        digest = None
    return {'run_id': spec.get('run_id') if isinstance(spec, dict) else None, 'valid': not result['errors'],
            'spec_sha256': digest, 'errors': result['errors'], 'warnings': result['warnings']}


# Computed readiness ---------------------------------------------------------

def run_dir(spec, runs=None, root=ROOT):
    run_id = spec.get('run_id') if isinstance(spec, dict) else None
    if not isinstance(run_id, str) or not RUN_ID.match(run_id):
        raise ValueError('run_id cannot name a run folder')
    return (Path(runs) if runs else Path(root) / RUNS) / run_id.replace(':', '_')


def _evidence(path, label):
    """(object, None) for a readable JSON object, else (None, reason)."""
    if not path.is_file():
        return None, 'no ' + label
    try:
        value = read_json(path)
    except (ValueError, OSError):
        return None, label + ' is not readable JSON'
    if not isinstance(value, dict):
        return None, label + ' is not a JSON object'
    return value, None


def _same(value, key, expected):
    """An optional binding: absent is allowed, present must match."""
    return key not in value or value[key] == expected


def amended_errors(slot, amended, window=None):
    if not isinstance(amended, dict) or set(amended) != set(DIGESTED):
        return 'an amended payload carries exactly ' + ', '.join(DIGESTED)
    if any(amended[key] != slot[key] for key in ('channel', 'format', 'publish_mode')):
        return 'an amendment cannot change channel, format or publish_mode'
    if not isinstance(amended['words'], str) or not amended['words'].strip():
        return 'amended words are empty'
    if not isinstance(amended['assets'], list) or not all(isinstance(x, str) and SHA.match(x) for x in amended['assets']):
        return 'amended assets must be sha256 strings'
    if amended['link_placement'] is not None and not isinstance(amended['link_placement'], str):
        return 'amended link_placement must be text or null'
    if amended['due_at'] is not None:
        if slot['publish_mode'] == 'krish_click':
            return 'a krish_click amendment stays unscheduled'
        try:
            due = instant(amended['due_at'])
        except (ValueError, TypeError):
            return 'amended due_at needs an offset'
        if window and not window[0] <= due < window[1]:
            return 'amended due_at falls outside the run window'
    return None


def decision_errors(spec, decision):
    """Why decision.json is not Krish's approved go-live for this signed spec, or None.

    Shape (shared with engine/run/release.py): {"run_id", "proposal_id",
    "decision": "approved", "decided_at", "slots": {slot_id: 64-hex digest},
    "amended": {slot_id: amended payload}}; "amended" is optional. The spec's
    signature names the proposal and holds decision_digest, the sha256 of the
    canonical JSON of the slots map.
    """
    if decision.get('run_id') != spec['run_id']:
        return 'decision.json is for another run'
    if decision.get('decision') != 'approved':
        return 'decision.json is not an approved go-live decision'
    if not isinstance(decision.get('slots'), dict):
        return 'decision.json slots must map each slot_id to its signed digest'
    if decision.get('amended') is not None and not isinstance(decision['amended'], dict):
        return 'decision.json amended must map slot_id to an amended payload'
    signature = spec.get('signature')
    if not signature:
        return 'the spec has no signature naming this decision'
    if signature['go_live_proposal_id'] != decision.get('proposal_id'):
        return 'decision.json is for another go-live proposal'
    try:
        digest = sha256_hex(decision['slots'])
    except ValueError:
        return 'decision.json slots are not canonical JSON'
    if signature['decision_digest'] != digest:
        return 'decision.json slots do not match the signed decision_digest; a mismatch is never signed'
    return None


def signed_digest(slot, decision, window=None):
    """(digest Krish signed for this slot, None) or (None, reason). The amended version wins."""
    digest = decision['slots'].get(slot['slot_id'])
    if digest is None:
        return None, 'decision.json has no entry for this slot'
    if not isinstance(digest, str) or not SHA.match(digest):
        return None, 'decision.json holds no 64-hex digest for this slot'
    if digest == slot['payload_sha256']:
        return digest, None
    amended = (decision.get('amended') or {}).get(slot['slot_id'])
    if amended is None:
        return None, 'decision digest does not match payload_sha256; a mismatch is never signed'
    reason = amended_errors(slot, amended, window)
    if reason:
        return None, reason
    if sha256_hex(amended) != digest:
        return None, 'decision digest does not recompute from the amended payload; never signed'
    return digest, None


def _measured(folder, slot):
    windows = []
    for path in sorted((folder / 'measured').glob(slot['slot_id'] + '-*.json')):
        window = path.name[len(slot['slot_id']) + 1:-len('.json')]
        value, reason = _evidence(path, 'measured/' + path.name)
        if (not WINDOW.match(window) or reason or not _same(value, 'slot_id', slot['slot_id'])
                or not isinstance(value.get('captured_at'), str)):
            continue
        try:
            instant(value['captured_at'])  # instant(None) would mean now: never a capture time.
        except (ValueError, TypeError):
            continue
        windows.append(window)
    return windows


def row(slot, stage, reason=None):
    index = STAGES.index(stage)
    return {'slot_id': slot['slot_id'], 'channel': slot['channel'], 'stage': stage,
            'next': STAGES[index + 1] if index + 1 < len(STAGES) else None, 'reason': reason}


def slot_status(slot, folder, lint_reason, decision, decision_reason, window=None, snack=False):
    """snack: the slot's format is snackable, so its review is the blind send test (crew/send-test/)."""
    sid = slot['slot_id']
    if lint_reason:
        return row(slot, 'drafted', lint_reason)
    label = 'review/' + sid + '.json'
    review, reason = _evidence(folder / 'review' / (sid + '.json'), label)
    if review is not None and (review.get('verdict') != 'pass' or not isinstance(review.get('lens'), str)
                               or not LENS.match(review['lens'])):
        reason = label + ' needs verdict pass and a lens id'
    elif review is not None and review.get('payload_sha256') != slot['payload_sha256']:
        reason = label + " must carry this slot's payload_sha256; a review of another payload never counts"
    elif review is not None and not _same(review, 'slot_id', sid):
        reason = label + ' reviewed another slot'
    elif review is not None and snack and review.get('lens') != 'send-test':
        reason = label + ' of a snackable slot is the blind send test: lens send-test (run send-test)'
    if reason:
        return row(slot, 'linted', reason)
    if decision_reason:
        return row(slot, 'reviewed', decision_reason)
    digest, reason = signed_digest(slot, decision, window)
    if reason:
        return row(slot, 'reviewed', reason)
    label = 'queued/' + sid + '.json'
    queued, reason = _evidence(folder / 'queued' / (sid + '.json'), label)
    if queued is not None:
        if queued.get('status') not in ('scheduled', 'draft'):
            reason = label + ' status must be scheduled or draft'
        elif slot['publish_mode'] == 'krish_click' and queued['status'] != 'draft':
            reason = 'a krish_click slot is only ever an unscheduled draft'
        elif queued.get('payload_sha256') != digest or not _same(queued, 'slot_id', sid):
            reason = label + ' does not match the signed digest'
    if reason and queued is None and digest != slot['payload_sha256']:
        reason += '; signed as amended: rewrite the slot with the amended payload (run new --from) to release it'
    if reason:
        return row(slot, 'signed', reason)
    label = 'live/' + sid + '.json'
    live, reason = _evidence(folder / 'live' / (sid + '.json'), label)
    if live is not None:
        url = live.get('native_url')
        if live.get('status') != 'sent':
            reason = 'live needs status sent read back; ' + json.dumps(live.get('status')) + ' is not live'
        elif not (http_url(url) and url.startswith('https://')):
            reason = 'live needs an https native_url read back from the platform'
        elif not (_same(live, 'payload_sha256', digest) and _same(live, 'slot_id', sid)):
            reason = label + ' does not match the signed digest'
    if reason:
        return row(slot, 'queued', reason)
    if not _measured(folder, slot):
        return row(slot, 'live', 'no valid measured/' + sid + '-<window>.json with captured_at')
    label = 'verdict/' + sid + '.json'
    verdict, reason = _evidence(folder / 'verdict' / (sid + '.json'), label)
    if verdict is not None and (verdict.get('verdict') not in VERDICTS or not _same(verdict, 'slot_id', sid)):
        reason = label + ' verdict must be one of ' + ', '.join(VERDICTS)
    if reason:
        return row(slot, 'measured', reason)
    return row(slot, 'verdict')


def status(spec, runs=None, root=ROOT, records=None):
    """Each slot's furthest stage the evidence proves, and why it stops there."""
    validate(spec, read_json(SCHEMA))
    formats = (records or social_records(root))['format']
    folder = run_dir(spec, runs, root)
    lint_record, lint_reason = _evidence(folder / 'lint.json', 'lint.json (run lint --record)')
    if lint_record is not None:
        if lint_record.get('run_id') != spec['run_id'] or lint_record.get('spec_sha256') != lint_digest(spec):
            lint_reason = 'lint.json is for another version of this spec; run lint --record again'
        elif lint_record.get('errors') != []:
            lint_reason = 'lint.json records errors'
    decision, decision_reason = _evidence(folder / 'decision.json', 'decision.json')
    if decision is not None:
        decision_reason = decision_errors(spec, decision)
    window = (instant(spec['window']['start']), instant(spec['window']['end']))
    try:
        shown = folder.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        shown = folder.name
    return {'local_only': True, 'run_id': spec['run_id'], 'evidence': shown,
            'slots': [slot_status(slot, folder, lint_reason, decision, decision_reason, window,
                                  snackable(formats.get(slot['format'])))
                      for slot in spec['slots']]}


# The blind send test for a slot -------------------------------------------

def send_test_review(spec, slot_id, answer=None):
    """A slot's blind request, or with the reader's answer the review record run status reads.

    The record's lens is send-test and it carries the slot's payload_sha256, so a
    later edit to the words, assets or format leaves it reviewing another payload.
    """
    validate(spec, read_json(SCHEMA))
    slot = next((s for s in spec['slots'] if s['slot_id'] == slot_id), None)
    if slot is None:
        raise ValueError('no slot ' + str(slot_id) + ' in this spec')
    request = slot_send_test_request(slot)
    if answer is None:
        return request
    if slot.get('share') is None:
        raise ValueError(slot_id + ' declares no share block to compare against')
    if slot['payload_sha256'] != payload_sha256(slot):
        raise ValueError(slot_id + ': payload_sha256 does not recompute; run new --from first')
    result = compare_send_test(slot['share'], answer, request)
    return {'slot_id': slot_id, 'verdict': result['verdict'], 'lens': 'send-test',
            'payload_sha256': slot['payload_sha256'], 'send_test': result}


# Command line ---------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run', description='Run specs: new, lint and computed status. Offline.')
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('new', help='a spec skeleton, or a draft with its computed fields filled')
    p.add_argument('--start', help='YYYY-MM-DD in New York; a week starts on its Monday')
    p.add_argument('--kind', choices=sorted(LENGTH), default='week')
    p.add_argument('--run-id')
    p.add_argument('--from', dest='source',
                   help='a draft spec: fill week_target, every payload_sha256 and each forward_line with a share')
    p.add_argument('--out')
    for name in ('lint', 'status'):
        p = sub.add_parser(name)
        p.add_argument('spec')
        p.add_argument('--runs-dir', help='evidence root (default .scratch/runs)')
        if name == 'lint':
            p.add_argument('--record', action='store_true', help='write lint.json for run status')
    p = sub.add_parser('send-test', help="a slot's blind send test: the request, or with --answer its review record")
    p.add_argument('spec')
    p.add_argument('slot')
    p.add_argument('--answer', help="the fresh reader's JSON answer to this slot's request")
    p.add_argument('--record', action='store_true', help='write the review record to review/<slot>.json')
    p.add_argument('--runs-dir', help='evidence root (default .scratch/runs)')
    args = parser.parse_args(argv)
    try:
        if args.action == 'new':
            if bool(args.source) == bool(args.start):
                raise ValueError('give --start for a skeleton or --from for a draft')
            spec = computed(read_json(args.source)) if args.source else skeleton(args.start, args.kind, args.run_id)
            if not args.out:
                print(json.dumps(spec, indent=2))
                return 0
            if Path(args.out).exists() and not (args.source and Path(args.out).resolve() == Path(args.source).resolve()):
                raise ValueError('refusing to replace ' + args.out + '; only --from may rewrite its own file')
            write_json(args.out, spec)
            print('spec written locally: ' + args.out + '; no external write')
            return 0
        spec = read_json(args.spec)
        if args.action == 'send-test':
            if args.record and not args.answer:
                raise ValueError('--record needs --answer: only a compared answer is review evidence')
            result = send_test_review(spec, args.slot, read_json(args.answer) if args.answer else None)
            if args.record:
                write_json(run_dir(spec, args.runs_dir) / 'review' / (args.slot + '.json'),
                           dict(result, recorded_at=instant().isoformat()))
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return int(bool(args.answer) and result['verdict'] != 'pass')
        if args.action == 'status':
            print(json.dumps(status(spec, args.runs_dir), indent=2))
            return 0
        report = lint_report(spec)
        if args.record:
            write_json(run_dir(spec, args.runs_dir) / 'lint.json',
                       dict(report, recorded_at=instant().isoformat()))
        print(json.dumps(report, indent=2))
        return int(not report['valid'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
