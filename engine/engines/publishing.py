"""The publishing engine: approved editions, the reader-facing checks that close them and held routes.

Review sections 6 and 7 (docs/reviews/2026-11-05-growth-engine-review.md). Each destination closes against
what a reader can see and do: scheduled, public, grid cover, player cover, playable video, continuation link
and email delivery are separate checks on the same post ID, and an edition is done only when every check
that applies to its channel and format is closed. Saved settings never close a check; only a readback of the
public reader view does. A failed route is held with its failure, a date and an explicit recheck condition.
LinkedIn follows its human publication rule: Krish's click, never scheduled by this engine. Nothing here
posts, publishes, schedules, sends, spends or writes to Control Center.
"""
import re
from pathlib import Path

from engine import social

KINDS = ('edition', 'route_hold', 'check')
STATES = {'edition': ('approved', 'scheduled', 'public', 'repair'), 'route_hold': ('held',),
          'check': ('open', 'discrepancy')}
CLOSED_STATES = ('done', 'released', 'passed')
# The closing state each kind may take: an edition is done, a hold released, a check passed on a readback.
ALLOWED = {'edition': STATES['edition'] + ('done',), 'route_hold': STATES['route_hold'] + ('released',),
           'check': STATES['check'] + ('passed',)}
CHECKS = ('scheduled', 'public', 'grid_cover', 'player_cover', 'playable_video', 'continuation_link',
          'email_delivery')
# Checks beyond scheduled and public that a destination carries (review section 6).
EXTRA_CHECKS = {('facebook', 'short-video'): ('grid_cover', 'player_cover'),
                ('youtube', 'short-video'): ('continuation_link',),
                ('substack', 'article'): ('playable_video', 'email_delivery')}
ROUTES = ('buffer', 'native', 'krish_click')
HUMAN_ONLY = ('linkedin',)
SHA256 = re.compile(r'^[0-9a-f]{64}$')
DATE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')


def applicable_checks(channel, format_id):
    """The reader-facing checks one destination closes against. LinkedIn is Krish's click, so not scheduled."""
    base = ('public',) if channel in HUMAN_ONLY else ('scheduled', 'public')
    return base + EXTRA_CHECKS.get((channel, format_id), ())


def channel_ids():
    """The channel ids social/channels carries; a destination names one of them exactly."""
    return {p.stem for p in (Path(social.ROOT) / 'social' / 'channels').glob('*.json')}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _date(value):
    return isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value))


def recheck_by(record):
    """The date bounding a record's recheck, read from its revisit_when, or None."""
    found = DATE.search(record.get('revisit_when') or '')
    return found.group(1) if found else None


def validate_detail(record):
    kind, d, state = record['kind'], record['detail'], record['state']
    errors = []
    if state not in ALLOWED[kind]:
        return [kind + ' state must be one of ' + ', '.join(ALLOWED[kind])]
    if kind in ('edition', 'check') and d.get('channel') not in channel_ids():
        errors.append('detail.channel must be a channel id in social/channels')
    if kind == 'edition':
        for name in ('channel', 'format'):
            if not _text(d.get(name)):
                errors.append('detail.' + name + ' is required')
        if d.get('route') not in ROUTES:
            errors.append('detail.route must be one of ' + ', '.join(ROUTES))
        if d.get('channel') in HUMAN_ONLY and (d.get('route') != 'krish_click' or state == 'scheduled'):
            errors.append('LinkedIn follows its human publication rule: route krish_click, never scheduled here')
        if not (isinstance(d.get('payload_sha256'), str) and SHA256.match(d['payload_sha256'])):
            errors.append('detail.payload_sha256 must be the sha256 of the approved edition')
        if d.get('post_id') is not None and not _text(d['post_id']):
            errors.append('detail.post_id must be a string or null')
        if state in ('public', 'repair', 'done') and not _text(d.get('post_id')):
            errors.append('a ' + state + ' edition carries its provider post_id')
        if d.get('due_on') is not None and not _date(d['due_on']):
            errors.append('detail.due_on must be YYYY-MM-DD or null')
    elif kind == 'route_hold':
        for name in ('tool', 'channel', 'format', 'failure', 'recheck_when', 'alternative'):
            if not _text(d.get(name)):
                errors.append('detail.' + name + ' is required')
        if not _date(d.get('held_since')):
            errors.append('detail.held_since must be YYYY-MM-DD')
    elif kind == 'check':
        if d.get('check') not in CHECKS:
            errors.append('detail.check must be one of ' + ', '.join(CHECKS))
        for name in ('channel', 'format'):
            if not _text(d.get(name)):
                errors.append('detail.' + name + ' is required')
        if not errors and d['check'] not in applicable_checks(d['channel'], d['format']):
            errors.append(d['check'] + ' does not apply to ' + d['channel'] + ' ' + d['format'])
        if d.get('post_id') is not None and not _text(d['post_id']):
            errors.append('detail.post_id must be a string or null')
        if state == 'passed':
            if record['source'].get('kind') != 'live_readback':
                errors.append('only a readback of the public reader view closes a check; saved settings never do')
            if not _text(d.get('post_id')):
                errors.append('a passed check names the post ID it was read on')
        if state == 'discrepancy' and _text(d.get('post_id')) and not recheck_by(record):
            # A discrepancy with no known post ID cannot be read back; it is dated once the post ID is recovered.
            errors.append('a discrepancy keeps a bounded recheck: a YYYY-MM-DD date in revisit_when')
    return errors


# Domain rules -------------------------------------------------------------------------------------------


def belongs(check, edition):
    """A check counts for an edition only on the edition's own channel, format and post ID."""
    c, e = check['detail'], edition['detail']
    return (c.get('channel'), c.get('format'), c.get('post_id')) == (e.get('channel'), e.get('format'),
                                                                      e.get('post_id'))


def checks_of(edition, records):
    """{check name: current check record} linked to one edition on its own post. The latest updated_at
    wins, then file order."""
    linked = [r for r in records.values() if r['kind'] == 'check' and edition['id'] in (r.get('links') or [])
              and belongs(r, edition)]
    return {r['detail']['check']: r for r in sorted(linked, key=lambda r: r['updated_at'])}


def edition_status(edition, records):
    """Which of the edition's applicable checks are closed, open or not yet recorded."""
    d = edition['detail']
    found = checks_of(edition, records)
    status = {}
    for name in applicable_checks(d.get('channel'), d.get('format')):
        r = found.get(name)
        status[name] = 'missing' if r is None else r['state']
    remaining = sorted(n for n, s in status.items() if s != 'passed')
    return {'id': edition['id'], 'checks': status, 'remaining': remaining, 'done': not remaining}


def close_edition(edition, records, now):
    """The next line marking an edition done. Refused while any applicable check is open or unrecorded."""
    status = edition_status(edition, records)
    if status['remaining']:
        raise ValueError('edition ' + edition['id'] + ' still has open checks: ' + ', '.join(status['remaining']))
    return dict(edition, state='done', next_owner='measurement', next_action=None, revisit_when=None,
                updated_at=now)


def readback(check, ok, now, ref, post_id=None, recheck_on=None):
    """The next line for one check after reading the public reader view. ok closes only this check; a miss
    keeps it open as a discrepancy on the same post ID with a dated recheck. A readback on a different post
    ID is refused: the discrepancy belongs to the post it was found on."""
    known = check['detail'].get('post_id')
    post_id = post_id or known
    if known and post_id != known:
        raise ValueError('readback on post ' + str(post_id) + ' but the check is on post ' + known)
    source = {'kind': 'live_readback', 'ref': ref, 'observed_at': now}
    detail = dict(check['detail'], post_id=post_id)
    if ok:
        return dict(check, state='passed', source=source, detail=detail, next_owner='none', next_action=None,
                    revisit_when=None, updated_at=now)
    if not recheck_on:
        raise ValueError('a discrepancy needs a bounded recheck date')
    return dict(check, state='discrepancy', source=source, detail=detail, next_owner='publishing',
                next_action='recheck the public ' + check['detail']['check'].replace('_', ' ') + ' on the same post',
                revisit_when='recheck by ' + recheck_on + ' on post ' + str(post_id), updated_at=now)


def tool_holds(root=None):
    """Held capabilities in social/tools/*.json: {(tool, channel, format): capability}. Reads only."""
    tools = social.inventory(root or social.ROOT)['tool']
    return {(t, c['channel'], c['format']): c for t, obj in sorted(tools.items())
            for c in obj['capabilities'] if c['status'] == 'held'}


def route_holds(records, held=None):
    """Every held route, from the tool records and this engine's route_hold records, joined by route."""
    held = tool_holds() if held is None else held
    out = {}
    for (tool, channel, format_id), cap in held.items():
        out[(tool, channel, format_id)] = {'route': tool + ' ' + channel + ' ' + format_id, 'tool_record': 'held',
                                           'record': None, 'held_since': cap.get('held_since'),
                                           'recheck_when': cap.get('recheck_when'),
                                           'alternative': cap.get('alternative')}
    for r in records.values():
        if r['kind'] != 'route_hold' or r['state'] != 'held':
            continue
        d = r['detail']
        key = (d['tool'], d['channel'], d['format'])
        entry = out.setdefault(key, {'route': ' '.join(key), 'tool_record': 'not_held', 'held_since': d['held_since'],
                                     'recheck_when': d['recheck_when'], 'alternative': d['alternative']})
        entry['record'] = r['id']
    return [out[k] for k in sorted(out)]


def blocked_editions(records, held=None):
    """Open editions routed through a held route, with the alternative to put to Krish."""
    held = tool_holds() if held is None else held
    out = []
    for r in sorted(records.values(), key=lambda r: r['id']):
        d = r['detail']
        if r['kind'] == 'edition' and r['state'] not in CLOSED_STATES \
                and (d.get('route'), d.get('channel'), d.get('format')) in held:
            out.append({'id': r['id'], 'alternative': held[(d['route'], d['channel'], d['format'])].get('alternative')})
    return out


def check_records(records):
    """Errors across current records that no single line shows: a done edition with a check not passed on
    its post, and a check linked to an edition on another channel, format or post."""
    errors = []
    for r in sorted(records.values(), key=lambda r: r['id']):
        if r.get('kind') == 'edition' and r.get('state') == 'done':
            remaining = edition_status(r, records)['remaining']
            if remaining:
                errors.append(r['id'] + ': done edition with checks not passed on its post: ' + ', '.join(remaining))
        if r.get('kind') == 'check':
            for link in r.get('links') or []:
                e = records.get(link)
                c = r['detail']
                if e and e.get('kind') == 'edition' and ((c['channel'], c['format']) != (e['detail']['channel'],
                                                         e['detail']['format'])
                                                         or None not in (c.get('post_id'), e['detail'].get('post_id'))
                                                         and c['post_id'] != e['detail']['post_id']):
                    errors.append(r['id'] + ': linked to edition ' + link + ' on another channel, format or post')
    return errors


def _brief(r):
    return {k: r.get(k) for k in ('id', 'title', 'state', 'next_owner', 'next_action', 'revisit_when')}


def recover(records, all_records, now, held=None):
    """Run Publishing: due slots, approved editions, existing provider records, route holds and unresolved
    public checks. next_action is the most urgent: an overdue recheck, then a due slot, then an open check."""
    live = [r for r in sorted(records.values(), key=lambda r: r['id']) if r['state'] not in CLOSED_STATES]
    editions = [r for r in live if r['kind'] == 'edition']
    checks = [r for r in live if r['kind'] == 'check']
    blocked = blocked_editions(records, held)
    due = [r for r in editions if r['state'] in ('approved', 'scheduled') and r['detail'].get('due_on')
           and r['detail']['due_on'] <= now]
    held_due = [dict(_brief(r), next_owner='krish', next_action='held route ' + r['detail']['route'] + ': offer '
                     + str(b['alternative']) + ' to Krish') for r in due for b in blocked if b['id'] == r['id']]
    due = [r for r in due if r['id'] not in {b['id'] for b in blocked}]
    overdue = [r for r in checks if recheck_by(r) and recheck_by(r) <= now]
    holds = route_holds(records, held)
    first = ([_brief(r) for r in overdue + due] or held_due or [_brief(r) for r in checks] or [None])[0]
    return {
        'due_slots': [r['id'] for r in due],
        'approved_editions': [r['id'] for r in editions if r['state'] == 'approved'],
        'provider_records': {r['id']: r['detail'].get('post_id') for r in editions if r['detail'].get('post_id')},
        'route_holds': holds,
        'route_hold_mismatches': [h['route'] for h in holds if h['tool_record'] != 'held' or not h['record']],
        'blocked_editions': blocked,
        'unresolved_checks': [{'id': r['id'], 'check': r['detail']['check'], 'channel': r['detail']['channel'],
                               'post_id': r['detail'].get('post_id'), 'state': r['state'],
                               'recheck_by': recheck_by(r)} for r in checks],
        'overdue_rechecks': [r['id'] for r in overdue],
        'editions': [edition_status(r, records) for r in editions],
        'next_action': first,
    }
