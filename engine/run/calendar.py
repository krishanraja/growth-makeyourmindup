"""The posting calendar (calendar/v1.json): schema, a resolved steady-state week, and its lint.

Offline only. Nothing here posts, schedules, sends or spends. Every row's lane
is derived from invariants/authority.json (Krish, 27 Oct 2026, rules R92 to
R94); the lint proves it, and proves the floors and caps hold on the week the
rows resolve to.
"""
import argparse
import json
from pathlib import Path

from ..core import TIMEZONE, read_json
from ..social import inventory, validate
from .invariants import RULE_SOURCES, class_of, collapse, load_authority, posting_lane

ROOT = Path(__file__).resolve().parents[2]
CALENDAR = ROOT / 'calendar' / 'v1.json'
SCHEMA = ROOT / 'specs' / 'schema' / 'calendar.schema.json'
WEEKDAYS = ('MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')
# Stories expire in a day and are not feed posts, so no daily post cap counts them;
# the stories floor checks them instead.
STORY_FORMATS = ('story', 'story-frame')
PRODUCERS = {'content-engine': 'content-engine', 'growth-canva': 'canva-lane'}
CAP_SOURCES = ('knowledge/', 'social/', 'docs/')


def finding(code, at, message):
    return {'code': code, 'at': at, 'message': message}


def timezone_errors(name):
    """The calendar's day boundaries are the engine's: a valid IANA name, and New York."""
    if name != TIMEZONE:
        return ['tz must be ' + TIMEZONE + ', the engine timezone']
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:
        return []
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return []  # No IANA database (often Windows); core.ny_time has a tested fallback for this zone.
    except ValueError:
        return ['tz is not a valid IANA timezone']
    return []


def rows(calendar):
    """Every row, wave then weekly, each with its own JSON path."""
    for kind in ('wave', 'weekly'):
        for i, row in enumerate(calendar[kind]):
            yield '$.%s[%d]' % (kind, i), kind, row


def candidates(calendar):
    """Each row instance in a steady-state week: wave rows once per piece, weekly rows once."""
    out = []
    for p, piece in enumerate(calendar['pieces']):
        start = WEEKDAYS.index(piece['weekday'])
        for order, row in enumerate(calendar['wave']):
            for day in range(row['days'][0], row['days'][1] + 1):
                out.append({'row': row, 'piece': piece['series'], 'day': day, 'weekday': (start + day) % 7,
                            'key': (row['priority'], day, order, p)})
    for order, row in enumerate(calendar['weekly']):
        out.append({'row': row, 'piece': None, 'day': None, 'weekday': WEEKDAYS.index(row['weekday']),
                    'key': (row['priority'], 0, len(calendar['wave']) + order, 0)})
    return out


def daily_caps(calendar, channels):
    """Per channel: the smallest of its record's daily_posts_target, a quoted corpus cap and its floor max."""
    caps = {}
    for name, record in channels.items():
        target = record.get('daily_posts_target')
        if isinstance(target, int) and not isinstance(target, bool):
            caps[name] = target
    for cap in calendar['caps']:
        if cap['per'] == 'day':
            caps[cap['channel']] = min(caps.get(cap['channel'], cap['max']), cap['max'])
    for floor in calendar['floors']:
        caps[floor['channel']] = min(caps.get(floor['channel'], floor['max']), floor['max'])
    return caps


def resolve(calendar, channels):
    """(kept, bumped): the week the rows resolve to under each channel's daily cap.

    Per weekday and channel the lowest priority number wins, then the newer
    piece. A row whose `requires` row (same piece) did not run is dropped, and
    that can free room for another; repeat until nothing changes.
    """
    caps = daily_caps(calendar, channels)
    every = candidates(calendar)
    dropped = set()
    while True:
        kept, bumped = [], []
        slots = {}
        for index, item in sorted(enumerate(every), key=lambda pair: pair[1]['key']):
            if index in dropped:
                continue
            row = item['row']
            if row['format'] in STORY_FORMATS or row['channel'] not in caps:
                kept.append(index)
                continue
            used = slots.setdefault((item['weekday'], row['channel']), 0)
            if used < caps[row['channel']]:
                slots[(item['weekday'], row['channel'])] = used + 1
                kept.append(index)
            else:
                bumped.append(index)
        ran = {(every[i]['piece'], every[i]['row']['id']) for i in kept}
        orphans = {i for i in kept if every[i]['row']['requires']
                   and (every[i]['piece'], every[i]['row']['requires']) not in ran}
        if not orphans - dropped:
            break
        dropped |= orphans
    label = lambda i, why: dict(id=every[i]['row']['id'], piece=every[i]['piece'], day=every[i]['day'],
                                weekday=WEEKDAYS[every[i]['weekday']], channel=every[i]['row']['channel'],
                                priority=every[i]['row']['priority'], why=why)
    return ([every[i] for i in sorted(kept, key=lambda i: every[i]['key'])],
            [label(i, 'cap') for i in sorted(bumped)] + [label(i, 'requires') for i in sorted(dropped)])


def week_counts(kept):
    counts = {}
    for item in kept:
        day = counts.setdefault(WEEKDAYS[item['weekday']], {})
        day[item['row']['channel']] = day.get(item['row']['channel'], 0) + 1
    return counts


def _row_errors(at, row, authority, records, calendar, kit):
    errors = []
    channel, fmt = records['channel'].get(row['channel']), records['format'].get(row['format'])
    kind, _ = class_of(authority, row['class'])
    if channel is None:
        errors.append(finding('unknown_channel', at + '.channel', 'unknown channel ' + row['channel']))
    if fmt is None and kind != 'new':
        errors.append(finding('unknown_format', at + '.format', row['format'] + ' is in neither social/formats nor a'
                              ' new-format class of invariants/authority.json'))
    if channel and fmt and (row['format'] not in channel['formats'] or row['channel'] not in fmt['channels']):
        errors.append(finding('format_not_allowed', at + '.format', row['format'] + ' is not a format of ' + row['channel']))
    lane = posting_lane(authority, row['class'], row['channel'], row['format'])
    if row['lane'] != lane:
        errors.append(finding('lane', at + '.lane', row['id'] + ' is ' + lane + ' under invariants/authority.json, not '
                              + row['lane']))
    if row['channel'] == 'linkedin' and row['lane'] != 'L3_hands':
        errors.append(finding('linkedin_not_l3', at + '.lane', 'LinkedIn rows are his hands (L3_hands)'))
    if kind == 'new' and row['lane'] not in ('L2_eyes', 'L3_hands'):
        errors.append(finding('new_format_not_eyes', at + '.lane', row['class'] + ' is a new format: L2_eyes'))
    if (row['at'] == 'draft') != (row['lane'] == 'L3_hands'):
        errors.append(finding('draft_timing', at + '.at', 'only his hands take an unscheduled draft, and they take only that'))
    if fmt:
        owner = PRODUCERS[fmt['production_owner']]
        words_ok = row['template'] is None and fmt['min_assets'] == 0
        if row['producer'] != owner and not (row['producer'] == 'words' and words_ok):
            errors.append(finding('producer', at + '.producer', row['format'] + ' is made by ' + owner
                                  + (' or by words alone' if words_ok else '')))
    if (row['producer'] == 'canva-lane') != (row['template'] is not None):
        errors.append(finding('template', at + '.template', 'a canva-lane row names its template; no other row does'))
    if row['template'] is not None:
        size = calendar['templates'].get(row['template'])
        dims = kit['dimensions'].get(size) if isinstance(size, str) else None
        if dims is None:
            errors.append(finding('template', at + '.template', row['template'] + ' maps to no brand-kit size'))
        elif row['channel'] not in dims['channels']:
            errors.append(finding('template_size', at + '.template', size + ' is not a size for ' + row['channel']))
    return errors


def lint(calendar, root=ROOT):
    """{'valid', 'errors', 'warnings', 'held', 'bumped', 'week'} for one calendar. Errors block it."""
    root = Path(root)
    try:
        validate(calendar, read_json(root / 'specs' / 'schema' / 'calendar.schema.json'))
    except ValueError as exc:
        return {'valid': False, 'errors': [finding('schema', '$', str(exc))], 'warnings': [], 'held': [],
                'bumped': [], 'week': {}}
    authority = load_authority(root)
    records = inventory(root)
    kit = read_json(root / calendar['kit'])
    errors, warnings, held = [], [], []
    errors += [finding('timezone', '$.tz', e) for e in timezone_errors(calendar['tz'])]
    if calendar['preview_until'] != authority['show_before_post_until']:
        errors.append(finding('preview_until', '$.preview_until', 'must equal show_before_post_until in '
                              'invariants/authority.json: ' + authority['show_before_post_until']))
    ids = [row['id'] for _, _, row in rows(calendar)]
    errors += [finding('duplicate_row', '$', 'row id used twice: ' + i) for i in sorted({i for i in ids if ids.count(i) > 1})]
    wave_ids = {row['id'] for row in calendar['wave']}
    for at, kind, row in rows(calendar):
        errors += _row_errors(at, row, authority, records, calendar, kit)
        if kind == 'wave' and row['days'][0] > row['days'][1]:
            errors.append(finding('days', at + '.days', 'days run from the first to the last, in order'))
        if row['requires'] is not None and (kind != 'wave' or row['requires'] not in wave_ids):
            errors.append(finding('requires', at + '.requires', 'requires names another wave row'))
    for name, size in sorted(calendar['templates'].items()):
        if size not in kit['dimensions']:
            errors.append(finding('template', '$.templates.' + name, size + ' is not a size in ' + calendar['kit']))
    for i, cap in enumerate(calendar['caps']):
        at = '$.caps[%d]' % i
        path = root / cap['source_file']
        if not (cap['source_file'].startswith(CAP_SOURCES) or cap['source_file'] in RULE_SOURCES) or not path.is_file():
            errors.append(finding('cap_source', at + '.source_file', 'a cap cites a file in knowledge/, social/ or docs/'))
        elif collapse(cap['quote']) not in collapse(path.read_text(encoding='utf-8-sig')):
            errors.append(finding('cap_quote', at + '.quote', 'the quote is not in ' + cap['source_file']))
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings, 'held': held, 'bumped': [], 'week': {}}
    channels = records['channel']
    caps = daily_caps(calendar, channels)
    kept, bumped = resolve(calendar, channels)
    week = week_counts(kept)
    for item in bumped:
        if item['priority'] == 1:
            errors.append(finding('day0_bumped', '$', item['id'] + ' (' + str(item['piece']) + ') is cut on '
                                  + item['weekday'] + ': a priority 1 row must run'))
    for floor in calendar['floors']:
        name = floor['channel']
        if name in caps and caps[name] < floor['max']:
            held.append(name + ': the calendar allows ' + str(floor['max']) + ' a day, but the cap is ' + str(caps[name])
                        + '; more waits for Krish to raise it in social/channels/' + name + '.json')
        if name in caps and caps[name] < floor['min']:
            errors.append(finding('floor_over_cap', '$.floors', name + ' floor of ' + str(floor['min'])
                                  + ' a day is above its cap of ' + str(caps[name])))
        for day in WEEKDAYS:
            count = week.get(day, {}).get(name, 0)
            if count < floor['min']:
                errors.append(finding('floor', '$.floors', name + ' has ' + str(count) + ' on ' + day
                                      + ', below its floor of ' + str(floor['min'])))
    for (day, name), count in sorted(((d, c), n) for d, per in week.items() for c, n in per.items()):
        capped = [i for i in kept if WEEKDAYS[i['weekday']] == day and i['row']['channel'] == name
                  and i['row']['format'] not in STORY_FORMATS]
        if name in caps and len(capped) > caps[name]:
            errors.append(finding('cap', '$', name + ' has ' + str(len(capped)) + ' on ' + day + ', above its cap of '
                                  + str(caps[name])))
    for cap in calendar['caps']:
        if cap['per'] == 'week':
            total = sum(1 for i in kept if i['row']['channel'] == cap['channel'])
            if total > cap['max']:
                errors.append(finding('cap', '$.caps', cap['channel'] + ' has ' + str(total) + ' a week, above '
                                      + str(cap['max']) + ' (' + cap['source_file'] + ')'))
    stories = calendar['stories']
    for piece in calendar['pieces']:
        day = WEEKDAYS.index(piece['weekday'])
        for name in stories['channels']:
            made = {i['row']['template'] for i in kept if i['weekday'] == day and i['row']['channel'] == name
                    and i['row']['format'] in STORY_FORMATS}
            missing = [t for t in stories['templates'] if t not in made]
            if missing:
                errors.append(finding('stories', '$.stories', name + ' has no ' + ', '.join(missing) + ' frame on '
                                      + piece['weekday'] + ' (' + piece['series'] + ')'))
    memes = calendar['memes']
    for name in memes['channels']:
        total = sum(1 for i in kept if i['row']['channel'] == name and i['row']['class'] == 'meme')
        if not memes['min'] <= total <= memes['max']:
            errors.append(finding('memes', '$.memes', name + ' has ' + str(total) + ' memes a week, not '
                                  + str(memes['min']) + ' to ' + str(memes['max'])))
    for item in bumped:
        warnings.append(finding('bumped', '$', item['id'] + ' (' + str(item['piece']) + ', day ' + str(item['day'])
                                + ') does not run on ' + item['weekday'] + ': ' + ('the ' + item['channel'] + ' cap'
                                if item['why'] == 'cap' else 'the row it follows did not run')))
    return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'held': held, 'bumped': bumped, 'week': week}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run calendar')
    parser.add_argument('command', choices=['calendar'])
    parser.add_argument('action', choices=['lint'])
    parser.add_argument('file', nargs='?', default=str(CALENDAR))
    args = parser.parse_args(argv)
    try:
        calendar = read_json(Path(args.file))
    except (OSError, ValueError) as exc:
        print(json.dumps({'valid': False, 'errors': [finding('read', '$', str(exc))]}, indent=1))
        return 1
    result = lint(calendar)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['valid'] else 1
