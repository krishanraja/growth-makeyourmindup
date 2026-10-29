"""North Star attribution, secondary counts and What-Works verdicts.

Local only. It reads captures a browser session saved and the repository's
own files; it never opens a network connection. It builds, validates and
records: the only files it can change are NOW.md's state line and the
lists/northstar-history.jsonl ledger beside it, and only with an explicit
write flag.
"""
import argparse
import datetime as dt
import difflib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

from ..core import TIMEZONE, calendar_date, http_url, instant, ny_time, read_json, today as ny_today
from ..operations import METRICS, validate_observation
from ..packs import EM_DASH
from ..share import rules_or_default as share_rules_or_default

ROOT = Path(__file__).resolve().parents[2]
AWAITS = "classification awaits Krish's approval"
CATEGORIES = ('organic', 'unattributed', 'paid')
CAPTURE_KEYS = {'kind', 'captured_at', 'source_url', 'window', 'settled', 'metric', 'rows', 'total_new_free'}
WINDOW_KEYS = {'label', 'start', 'end', 'tz'}
ROW_KEYS = {'source', 'new_free', 'new_paid'}
LABELS = {1: 'on pace', 2: 'behind', 3: 'well behind', 4: 'far behind', 5: 'stalled'}
STALE_DAYS = 7
STALL_DAYS = 14
TWO_WEEKS = 'under two fifths two weeks running'
NO_MOVEMENT = 'no movement for 14 days'
HEADING = re.compile(r'^## Where it is right now\b')
STATE_PREFIX = '<!-- north-star-state'
LEDGER = Path('lists') / 'northstar-history.jsonl'
STATE_KEYS = ('week_of', 'week_target', 'current', 'current_as_of', 'current_source', 'urgency', 'urgency_reason')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December')
# Proposed defaults for Krish's approval at G-A. Ratios of the post's leading
# indicator to the median of its own channel and format history.
WORKS_AT_OR_ABOVE = 1.5
FAILS_AT_OR_BELOW = 0.5
MIN_HISTORY = 6


def count(value, field, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(field + ' must be a non-negative whole number' + (' or null' if nullable else ''))
    return value


def as_date(value, field='date'):
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    try:
        return calendar_date(value)
    except (TypeError, ValueError):
        raise ValueError(field + ' must be YYYY-MM-DD') from None


def human_date(value):
    value = as_date(value)
    return str(value.day) + ' ' + MONTHS[value.month - 1] + ' ' + str(value.year)


def monday(value):
    value = as_date(value)
    return value - dt.timedelta(days=value.weekday())


def plain(text, field):
    """Text a person reads: one line, no em dash, no percentages."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(field + ' must be a non-empty string')
    if '\n' in text or '\r' in text or '-->' in text:
        raise ValueError(field + ' must be one line without a comment terminator')
    if EM_DASH.search(text) or '%' in text or re.search(r'\bper ?cent\b', text, re.I):
        raise ValueError(field + ' must have no em dash or percentage')
    return text


# Growth-sources capture --------------------------------------------------

def validate_capture(capture, now=None):
    """A structured Substack Growth-sources read; F54 settle rule enforced."""
    if not isinstance(capture, dict) or capture.get('kind') != 'substack_growth_sources':
        raise ValueError('capture must be a substack_growth_sources object')
    if set(capture) != CAPTURE_KEYS:
        raise ValueError('capture fields must be exactly ' + ', '.join(sorted(CAPTURE_KEYS)))
    if not isinstance(capture['captured_at'], str):
        raise ValueError('captured_at must be a timestamp with an offset')
    captured = instant(capture['captured_at'])
    if captured > instant(now):
        raise ValueError('captured_at is in the future')
    url = capture['source_url']
    if not http_url(url) or urlsplit(url).scheme != 'https':
        raise ValueError('source_url must be an https URL without credentials')
    window = capture['window']
    if not isinstance(window, dict) or set(window) != WINDOW_KEYS:
        raise ValueError('window needs exactly label, start, end and tz')
    if not isinstance(window['label'], str) or not window['label'].strip():
        raise ValueError('window label must be the label the page showed')
    if window['tz'] != TIMEZONE:
        raise ValueError('window tz must be ' + TIMEZONE)
    start, end = as_date(window['start'], 'window start'), as_date(window['end'], 'window end')
    if end < start or ny_time(captured).date() < end:
        raise ValueError('window must end on or before the capture date and not before it starts')
    settled = capture['settled']
    if not isinstance(settled, dict) or set(settled) != {'label_seen', 'values_seen_after_label'}:
        raise ValueError('settled needs label_seen and values_seen_after_label')
    # F54 substack-filter-settle: the label changes before the old table goes.
    if settled['values_seen_after_label'] is not True or settled['label_seen'] != window['label']:
        raise ValueError('F54: the Growth-sources read has not settled; read again once the '
                         'selected window label and its values agree')
    if capture['metric'] != 'new_subscribers':
        raise ValueError('metric must be new_subscribers')
    rows = capture['rows']
    if not isinstance(rows, list):
        raise ValueError('rows must be a list')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise ValueError('each row needs exactly source, new_free and new_paid')
        if not isinstance(row['source'], str) or not row['source'].strip():
            raise ValueError('each row needs the source label the page showed')
        if label_key(row['source']) in seen:
            raise ValueError('duplicate source row: ' + row['source'])
        seen.add(label_key(row['source']))
        count(row['new_free'], 'new_free')
        count(row['new_paid'], 'new_paid')
    total = count(capture['total_new_free'], 'total_new_free')
    known = sum(r['new_free'] for r in rows if r['new_free'] is not None)
    if total is not None and known > total:
        raise ValueError('source rows exceed the total shown')
    if total is not None and all(r['new_free'] is not None for r in rows) and known != total:
        raise ValueError('source rows sum to ' + str(known) + ' but the total shows ' + str(total))
    return capture


def all_source(capture):
    if capture['total_new_free'] is not None:
        return {'value': capture['total_new_free'], 'reason': None}
    if any(r['new_free'] is None for r in capture['rows']):
        return {'value': None, 'reason': 'a source row shows no count and no total was shown'}
    return {'value': sum(r['new_free'] for r in capture['rows']), 'reason': None}


def label_key(label):
    """Source labels match whatever case or spacing the page shows ('Direct', 'direct ')."""
    return label.strip().casefold()


def load_sources(sources_path='invariants/sources.json', root=ROOT):
    """Return (label key -> category, approved, reason). The map counts only once approved.

    The same rules as engine/run/invariants.py load_sources: approved,
    approved_by, approved_at, note and a non-empty "categories" map keyed by
    lower-case labels; an unapproved file names no approver.
    """
    path = Path(sources_path)
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file():
        return None, None, AWAITS
    value = read_json(path)
    if not isinstance(value, dict) or not isinstance(value.get('approved'), bool) or not isinstance(value.get('categories'), dict):
        raise ValueError('sources file needs approved (true or false) and a categories map')
    for field in ('approved_by', 'approved_at', 'note'):
        if field not in value:
            raise ValueError('sources file needs ' + field)
    if not value['categories']:
        raise ValueError('sources file needs categories')
    if value['approved'] is not True and (value['approved_by'] is not None or value['approved_at'] is not None):
        raise ValueError('an unapproved classification names no approver')
    mapping = {}
    for label, category in value['categories'].items():
        if not isinstance(label, str) or not label.strip() or category not in CATEGORIES:
            raise ValueError('sources map labels to organic, unattributed or paid only')
        if label != label_key(label):
            raise ValueError('source ' + repr(label) + ' must be lower-case with no outer spaces')
        mapping[label] = category
    if value['approved'] is not True:
        return mapping, False, AWAITS
    return mapping, True, None


def classify(capture, sources_path='invariants/sources.json', root=ROOT):
    """All-source total always; organic, unattributed and paid only when approved."""
    mapping, approved, reason = load_sources(sources_path, root)
    labels = [r['source'] for r in capture['rows']]
    unknown = sorted(x for x in labels if mapping is None or label_key(x) not in mapping)
    result = {'all_source': all_source(capture), 'unknown_labels': unknown, 'approved': bool(approved)}
    if not approved:
        result.update({name: {'value': None, 'reason': reason} for name in CATEGORIES})
        return result
    blocking = [r['source'] for r in capture['rows'] if r['source'] in unknown and r['new_free'] != 0]
    for name in CATEGORIES:
        if blocking:
            result[name] = {'value': None, 'reason': 'unknown source labels need classification: ' + ', '.join(sorted(blocking))}
            continue
        rows = [r for r in capture['rows'] if mapping.get(label_key(r['source'])) == name]
        if any(r['new_free'] is None for r in rows):
            result[name] = {'value': None, 'reason': 'a ' + name + ' source shows no count'}
        else:
            result[name] = {'value': sum(r['new_free'] for r in rows), 'reason': None}
    return result


def paid_week(capture):
    """New paid subscribers in the capture window: summed only when every row shows it."""
    rows = capture['rows']
    out = {'window_start': capture['window']['start'], 'window_end': capture['window']['end']}
    if not rows and capture['total_new_free'] == 0:
        out.update(value=0, reason=None)  # an empty table under a zero total: nobody came in
    elif not rows:
        out.update(value=None, reason='no source rows were shown to read paid counts from')
    elif any(r['new_paid'] is None for r in rows):
        out.update(value=None, reason='the page did not show paid counts for every source')
    else:
        out.update(value=sum(r['new_paid'] for r in rows), reason=None)
    return out


# Followers per channel per day ------------------------------------------

def followers_daily(rows):
    """Daily follower snapshots per channel, via the shared metric registry."""
    if not isinstance(rows, list):
        raise ValueError('followers snapshots must be a JSON list')
    if 'followers' not in METRICS:
        raise ValueError('the followers metric is missing from the registry')
    latest = {}
    for row in rows:
        validate_observation(row)
        if row['metric'] != 'followers':
            raise ValueError('followers_daily reads followers snapshots only')
        key = (row['platform'], row['scope'], ny_time(row['end']).date().isoformat())
        old = latest.get(key)
        if old and instant(old['captured_at']) == instant(row['captured_at']) and old != row:
            raise ValueError('conflicting follower snapshots at the same capture time')
        if not old or instant(row['captured_at']) > instant(old['captured_at']):
            latest[key] = row
    channels = {}
    for (platform, scope, day) in sorted(latest):
        row = latest[(platform, scope, day)]
        days = channels.setdefault((platform, scope), [])
        previous = days[-1] if days else None
        adjacent = previous and as_date(day) - as_date(previous['date']) == dt.timedelta(days=1)
        value = row['value'] if row['availability'] == 'available' else None
        net = value - previous['value'] if adjacent and value is not None and previous['value'] is not None else None
        days.append({'date': day, 'value': value, 'net_change': net,
                     'reason': None if value is not None else row['reason']})
    return [{'channel': p, 'scope': s, 'days': d} for (p, s), d in sorted(channels.items())]


# North Star --------------------------------------------------------------

def _scalar(text):
    text = text.strip()
    if not text or text.startswith('#'):
        return None  # "key:   # a comment" carries no value
    if text.startswith('"'):
        end = text.find('"', 1)
        while end != -1 and text[end - 1] == '\\':
            end = text.find('"', end + 1)
        if end == -1:
            raise ValueError('unterminated quoted value in north-star-metric')
        rest = text[end + 1:].strip()
        if rest and not rest.startswith('#'):
            raise ValueError('unexpected text after a quoted value')
        return json.loads(text[:end + 1])
    text = text.split(' #', 1)[0].strip()
    return int(text) if re.fullmatch(r'\d+', text) else text


def north_star(path=None):
    """Parse the one fenced yaml north-star-metric block. Purpose-built, no PyYAML."""
    path = Path(path) if path else ROOT / 'docs' / 'NORTH_STAR.md'
    text = path.read_text(encoding='utf-8-sig')
    blocks = re.findall(r'^```yaml north-star-metric[ \t]*\r?\n(.*?)^```', text, re.M | re.S)
    if len(blocks) != 1:
        raise ValueError('the North Star file needs exactly one yaml north-star-metric block')
    metric, ladder = {}, None
    for line in blocks[0].splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        row = re.fullmatch(r'\s+-\s*\[\s*(\d{4}-\d{2}-\d{2})\s*,\s*(\d+)\s*\]\s*(?:#.*)?', line)
        if row:
            if not isinstance(ladder, list):
                raise ValueError('ladder row outside a ladder list')
            ladder.append((as_date(row.group(1), 'ladder date'), int(row.group(2))))
            continue
        pair = re.fullmatch(r'([a-z_]+):(.*)', line)
        if not pair:
            raise ValueError('unreadable north-star-metric line: ' + line.strip())
        key, value = pair.group(1), pair.group(2)
        if key in metric or (key == 'ladder' and ladder is not None):
            raise ValueError('duplicate north-star-metric key: ' + key)
        if key == 'ladder':
            value = _scalar(value)
            ladder = [] if value is None else value
            metric['ladder'] = ladder
        else:
            metric[key] = _scalar(value)
    if isinstance(ladder, list):
        dates = [d for d, _ in ladder]
        if not ladder or any(d.weekday() != 0 for d in dates) or dates != sorted(set(dates)):
            raise ValueError('ladder rows need ascending, unique Monday dates')
    for key in ('metric', 'target', 'deadline', 'ladder'):
        if key not in metric:
            raise ValueError('north-star-metric needs ' + key)
    return metric


def week_target(monday_date, metric=None):
    week = as_date(monday_date, 'week')
    if week.weekday() != 0:
        raise ValueError('a week target is looked up by its Monday')
    metric = metric or north_star()
    if not isinstance(metric['ladder'], list):
        raise ValueError('the ladder is pending a baseline; no week target yet')
    for day, value in metric['ladder']:
        if day == week:
            return value
    raise ValueError('no ladder row for the week of ' + week.isoformat())


def _reading(entry):
    if not isinstance(entry, dict):
        raise ValueError('history entries are north-star-state objects')
    current = count(entry.get('current'), 'history current')
    target = count(entry.get('week_target'), 'history week_target', nullable=False)
    as_of = as_date(entry['current_as_of'], 'history current_as_of') if entry.get('current_as_of') else None
    reason = entry.get('urgency_reason')
    return {'week_of': as_date(entry.get('week_of'), 'history week_of'), 'week_target': target,
            'current': current, 'as_of': as_of, 'urgency': entry.get('urgency'),
            'reason': reason if isinstance(reason, str) else ''}


def _under(current, target):
    return current * 5 < target * 2


def urgency(current, week_target, current_as_of, today, history=(), deadline=None):
    """Urgency U1 to U5, exactly per the harness north-star-metric contract."""
    today = as_date(today, 'today')
    target = count(week_target, 'week_target', nullable=False)
    if target == 0:
        raise ValueError('week_target must be positive')
    current = count(current, 'current')
    as_of = as_date(current_as_of, 'current_as_of') if current_as_of else None
    if current is not None and as_of is None:
        raise ValueError('a reading needs its date')
    if as_of and as_of > today:
        raise ValueError('current_as_of is in the future')
    readings = [_reading(x) for x in history]
    on_target = current is not None and current >= target
    shown = '' if current is None else '{:,} of {:,}; '.format(current, target)

    def level(n, why):
        return {'urgency': n, 'label': LABELS[n], 'urgency_reason': shown + why}
    if deadline is not None and today > as_date(deadline, 'deadline') + dt.timedelta(days=6) and not on_target:
        return level(5, 'past the deadline week of ' + human_date(deadline) + ' and off target')
    if current is None:
        return level(4, 'not measured yet')
    if (today - as_of).days > STALE_DAYS:
        return level(4, 'the reading of ' + human_date(as_of) + ' is more than 7 days old')
    if on_target:
        return level(1, "at or above this week's target")
    # A stall found earlier this week holds for the rest of it while it still applies.
    held = [r for r in readings if r['week_of'] == monday(today) and r['urgency'] == 5]
    if _under(current, target) and any(r['reason'].endswith(TWO_WEEKS) for r in held):
        return level(5, TWO_WEEKS)
    if any(r['reason'].endswith(NO_MOVEMENT) and r['current'] == current for r in held):
        return level(5, NO_MOVEMENT)
    previous = [r for r in readings if r['week_of'] == monday(today) - dt.timedelta(days=7)
                and r['current'] is not None and r['as_of']]
    if _under(current, target) and previous:
        last = max(previous, key=lambda r: r['as_of'])
        if _under(last['current'], last['week_target']):
            return level(5, TWO_WEEKS)
    dated = [r for r in readings if r['current'] is not None and r['as_of'] and r['as_of'] <= as_of]
    anchors = [r for r in dated if r['as_of'] <= today - dt.timedelta(days=STALL_DAYS)]
    if anchors:
        anchor = max(anchors, key=lambda r: r['as_of'])
        if all(r['current'] == current for r in dated if r['as_of'] >= anchor['as_of']):
            return level(5, NO_MOVEMENT)
    if current * 4 >= target * 3:
        return level(2, 'at least three quarters')
    if not _under(current, target):
        return level(3, 'from two fifths to three quarters')
    return level(4, 'under two fifths')


def state_line(week_of, week_target, current, current_as_of, current_source, urgency, urgency_reason, sentence=None):
    """The one NOW.md line: machine JSON in a comment, then one plain sentence."""
    if isinstance(urgency, bool) or urgency not in LABELS:
        raise ValueError('urgency must be 1 to 5')
    as_date(week_of, 'week_of')
    count(week_target, 'week_target', nullable=False)
    count(current, 'current')
    if current is not None and not current_as_of:
        raise ValueError('a reading needs its date')
    if current_as_of:
        as_date(current_as_of, 'current_as_of')
    if current_source is not None:
        plain(current_source, 'current_source')
    plain(urgency_reason, 'urgency_reason')
    if sentence is None:
        if current is None:
            sentence = ('New publication subscribers this week from organic posts and shares: not measured '
                        'yet, against {:,} this week, so measuring it comes first.').format(week_target)
        else:
            sentence = ('{:,} of {:,} new publication subscribers this week from organic posts and shares, '
                        'read on {}.').format(current, week_target, human_date(current_as_of))
    plain(sentence, 'sentence')
    state = dict(zip(STATE_KEYS, (as_date(week_of).isoformat(), week_target, current,
                                  as_date(current_as_of).isoformat() if current_as_of else None,
                                  current_source, urgency, urgency_reason)))
    return (STATE_PREFIX + ' ' + json.dumps(state) + ' --> **North Star number: U' + str(urgency)
            + ', ' + LABELS[urgency] + '.** ' + sentence)


def _state_index(lines):
    heads = [i for i, line in enumerate(lines) if HEADING.match(line)]
    states = [i for i, line in enumerate(lines) if line.startswith(STATE_PREFIX)]
    if len(heads) != 1 or len(states) != 1:
        raise ValueError('NOW.md needs exactly one "## Where it is right now" heading and one state line')
    if states[0] < heads[0] or any(line.strip() for line in lines[heads[0] + 1:states[0]]):
        raise ValueError('the state line must sit directly under "## Where it is right now"')
    return states[0]


def current_state(root=ROOT):
    """The state object NOW.md carries today, as history for the next reading."""
    with open(Path(root) / 'NOW.md', encoding='utf-8', newline='') as handle:
        lines = handle.read().splitlines(True)
    return state_of(lines[_state_index(lines)])


def state_of(line):
    """The JSON object inside one north-star-state line."""
    match = re.match(re.escape(STATE_PREFIX) + r' (\{.*?\}) -->', line)
    if not match:
        raise ValueError('the state line has no readable state')
    try:
        state = json.loads(match.group(1))
    except ValueError:
        raise ValueError('the state line has no readable state') from None
    if not isinstance(state, dict):
        raise ValueError('the state line has no readable state')
    return state


def read_ledger(root=ROOT):
    """Every state written before, oldest first; the history urgency needs."""
    path = Path(root) / LEDGER
    if not path.is_file():
        return []
    out = []
    with open(path, encoding='utf-8') as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                raise ValueError(str(LEDGER.as_posix()) + ' line ' + str(number) + ' is not readable') from None
            if not isinstance(entry, dict):
                raise ValueError(str(LEDGER.as_posix()) + ' line ' + str(number) + ' is not a state object')
            out.append(entry)
    return out


def append_ledger(root, state):
    """Record one written state, one JSON line, so later runs keep their history."""
    path = Path(root) / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(dict((k, state.get(k)) for k in STATE_KEYS)) + '\n')


def keeps(existing, state, why=None):
    """Lose nothing: a new state never replaces a newer or a measured reading."""
    if not isinstance(existing, dict) or not existing.get('week_of'):
        return
    old_week = as_date(existing['week_of'], 'existing week_of')
    if as_date(state['week_of']) < old_week:
        raise ValueError('this capture is for an earlier week than NOW.md holds; the reading for the week of '
                         + human_date(old_week) + ' stays')
    if as_date(state['week_of']) != old_week or existing.get('current') is None:
        return
    held = existing.get('current_as_of')
    held = human_date(held) if held else 'an earlier day'
    if state['current'] is None:
        raise ValueError('this capture does not count (' + (why or 'not measured') + '); the existing reading of '
                         + held + ' for this week stays')
    if existing.get('current_as_of') and as_date(state['current_as_of']) < as_date(existing['current_as_of']):
        raise ValueError('this capture is older than the reading of ' + held + ' for this week; that reading stays')


def write_now(root, line, write=False):
    """Replace only the state line; return the unified diff. Writes only when asked."""
    if not isinstance(line, str) or not line.startswith(STATE_PREFIX + ' ') or '\n' in line or '\r' in line:
        raise ValueError('the replacement must be one north-star-state line')
    path = Path(root) / 'NOW.md'
    with open(path, encoding='utf-8', newline='') as handle:
        lines = handle.read().splitlines(True)
    index = _state_index(lines)
    old = lines[index]
    new = lines[:index] + [line + old[len(old.rstrip('\r\n')):]] + lines[index + 1:]
    diff = ''.join(difflib.unified_diff(lines, new, 'a/NOW.md', 'b/NOW.md'))
    if write and new != lines:
        temp = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent, delete=False) as handle:
                temp = handle.name
                handle.write(''.join(new))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)
    return diff


def reading(capture, classified, week_of):
    """This week's organic count from one capture, or null with the reason."""
    start, end = as_date(capture['window']['start']), as_date(capture['window']['end'])
    week_of = as_date(week_of)
    organic, every = classified['organic']['value'], classified['all_source']['value']
    if not week_of <= end <= week_of + dt.timedelta(days=6):
        return None, 'the capture window ends outside the week of ' + human_date(week_of)
    if start > week_of:
        return None, 'the capture window starts after Monday and misses part of this week'
    if every == 0:
        return 0, None
    if start < week_of:
        if organic == 0:
            return 0, None
        return None, 'the capture window starts before Monday, so it only bounds this week'
    if organic is None:
        unknown = len([r for r in capture['rows'] if r['source'] in classified['unknown_labels'] and r['new_free'] != 0])
        if classified['approved'] and unknown:  # a count, never the labels: they are page text
            return None, '{} unknown source {} classification'.format(unknown, 'label needs' if unknown == 1 else 'labels need')
        return None, classified['organic']['reason']
    return organic, None


def northstar(capture, today=None, root=ROOT, sources_path='invariants/sources.json', history=None, now=None):
    validate_capture(capture, now)
    day = as_date(today) if today else as_date(ny_today())
    metric = north_star(Path(root) / 'docs' / 'NORTH_STAR.md')
    if metric.get('status') == 'paused':
        raise ValueError('the North Star is paused, so it carries no urgency until Krish revives it')
    week = monday(day)
    ladder = metric['ladder']
    if isinstance(ladder, list) and ladder and week > ladder[-1][0]:
        target = ladder[-1][1]  # after the last row the final target stands; the deadline rule applies
    else:
        target = week_target(week, metric)
    classified = classify(capture, sources_path, root)
    current, why = reading(capture, classified, week)
    read_on = ny_time(capture['captured_at']).date()
    as_of = min(read_on, as_date(capture['window']['end']))  # never fresher than the data it covers
    window = capture['window']
    every = classified['all_source']['value']
    source = ('Substack Growth sources, new subscribers, {} ({} to {}), read {}: all sources {}, organic {}').format(
        window['label'], window['start'], window['end'], read_on.isoformat(),
        'not shown' if every is None else every,
        'not classified' if classified['organic']['value'] is None else classified['organic']['value'])
    if current is None:
        source += '; not counted because ' + why
    level = urgency(current, target, as_of if current is not None else None, day,
                    history if history is not None else [], metric.get('deadline'))
    line = state_line(week, target, current, as_of if current is not None else None, source,
                      level['urgency'], level['urgency_reason'])
    return {'line': line, 'classification': classified, 'urgency': level, 'week_of': week.isoformat(),
            'week_target': target, 'paid_subscribers': paid_week(capture), 'not_counted_because': why}


# Built to be sent: the snackable lane's primary measure ---------------------

# Krish, 2026-10-28: snackable posts are built to be sent from one person to
# another. Sends (native shares) per reach and saves per reach are their primary
# measure, a house hypothesis until MYMU's own dated data confirms it; the
# What-Works Analyst judges them with judge() like any other indicator.
SNACKABLE_PRIMARY = ('sends_per_reach', 'saves_per_reach')


def share_fields(channel, rules=None):
    """Which Buffer metric counts as sends, saves and reach on a channel (read 28 Oct 2026; social/share.json)."""
    rules = share_rules_or_default(rules)
    fields = rules['measure']['buffer_fields']['channels'].get(channel)
    if fields is None:
        raise ValueError('no share measurement fields recorded for channel ' + str(channel))
    return fields


def share_rates(channel, metrics, rules=None):
    """Sends and saves per reach for one snackable post, from its exposed metrics.

    metrics maps a Buffer metric type to its value as read. A field the channel
    does not expose, or a post that does not show it, is None ("not shown"),
    never zero; a reach of zero gives no ratio.
    """
    rules = share_rules_or_default(rules)
    if not isinstance(metrics, dict):
        raise ValueError('metrics must map metric types to values')
    fields = share_fields(channel, rules)

    def value(name):
        if fields[name] is None:
            return None
        return count(metrics.get(fields[name]), fields[name])

    reach, sends, saves = value('reach'), value('sends'), value('saves')
    # A repost is public amplification, never a one-to-one send: kept apart, never in sends_per_reach.
    out = {'channel': channel, 'status': rules['measure']['status'], 'fields': fields,
           'reach': reach, 'sends': sends, 'saves': saves,
           'public_reposts': value('public_reposts') if fields.get('public_reposts') else None}
    for key, numerator in (('sends_per_reach', sends), ('saves_per_reach', saves)):
        out[key] = None if numerator is None or not reach else numerator / reach
        out[key.replace('per_reach', 'per_1000_reached')] = (None if out[key] is None
                                                             else round(out[key] * 1000, 1))
    out['not_shown'] = [k for k in ('reach', 'sends', 'saves') if out[k] is None]
    return out


# What-Works verdicts -----------------------------------------------------

def _indicator(row, field):
    if not isinstance(row, dict):
        raise ValueError(field + ' must be an object')
    for key in ('channel', 'format', 'indicator'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(field + ' needs ' + key)
    value = row.get('value')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(field + ' needs a finite non-negative value')
    return row


def judge(post, history, window_hours, elapsed_hours):
    """Verdict with its denominator: the median of the post's own channel and format."""
    _indicator(post, 'post')
    for name, value in (('window_hours', window_hours), ('elapsed_hours', elapsed_hours)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(name + ' must be a non-negative number')
    if window_hours <= 0:
        raise ValueError('window_hours must be positive')
    if not isinstance(history, (list, tuple)):
        raise ValueError('history must be a list')
    rows = [_indicator(r, 'history row') for r in history]
    same = [r['value'] for r in rows if all(r[k] == post[k] for k in ('channel', 'format', 'indicator'))]
    out = {'verdict': 'insufficient', 'observations': len(same), 'median': None, 'ratio': None,
           'bands': {'works_at_or_above': WORKS_AT_OR_ABOVE, 'fails_at_or_below': FAILS_AT_OR_BELOW,
                     'zero_median': 'insufficient',
                     'status': "proposed defaults for Krish's approval at G-A"}}
    if elapsed_hours < window_hours:
        out['reason'] = 'the judge window has not elapsed'
        return out
    if len(same) < MIN_HISTORY:
        out['reason'] = 'fewer than {} history points for this channel and format'.format(MIN_HISTORY)
        return out
    values = sorted(same)
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    out['median'] = median
    if median == 0:
        # Proposed default for Krish at G-A: no ratio exists, so no verdict is given.
        out['reason'] = 'the median is zero, so no ratio can be judged'
        return out
    ratio = post['value'] / median
    out['ratio'] = round(ratio, 4)
    out['verdict'] = 'works' if ratio >= WORKS_AT_OR_ABOVE else 'fails' if ratio <= FAILS_AT_OR_BELOW else 'neutral'
    out['reason'] = 'association, not cause'
    return out


def verdict(post, history, window_hours, elapsed_hours):
    return judge(post, history, window_hours, elapsed_hours)['verdict']


# Command line ------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure')
    m.add_argument('what', choices=('sources', 'followers'))
    m.add_argument('file'); m.add_argument('--sources', default='invariants/sources.json'); m.add_argument('--root', default=str(ROOT))
    m.add_argument('--now')
    n = sub.add_parser('northstar')
    n.add_argument('--capture', required=True); n.add_argument('--write', action='store_true'); n.add_argument('--today')
    n.add_argument('--history', help='JSON list of earlier north-star-state objects'); n.add_argument('--root', default=str(ROOT))
    n.add_argument('--sources', default='invariants/sources.json'); n.add_argument('--now')
    v = sub.add_parser('verdict'); v.add_argument('file')
    args = parser.parse_args(argv)
    try:
        if args.cmd == 'measure' and args.what == 'sources':
            capture = validate_capture(read_json(args.file), args.now)
            result = {'local_only': True, 'settled': True, 'window': capture['window'],
                      'classification': classify(capture, args.sources, args.root),
                      'paid_subscribers': paid_week(capture)}
        elif args.cmd == 'measure':
            result = {'local_only': True, 'followers': followers_daily(read_json(args.file))}
        elif args.cmd == 'northstar':
            history = read_json(args.history) if args.history else []
            if not isinstance(history, list):
                raise ValueError('history must be a JSON list')
            existing = current_state(args.root)
            history = history + read_ledger(args.root) + [existing]
            if args.today:
                as_date(args.today, '--today')
            result = northstar(read_json(args.capture), args.today, Path(args.root), args.sources, history, args.now)
            state = state_of(result['line'])
            keeps(existing, state, result['not_counted_because'])
            diff = write_now(args.root, result['line'], args.write)
            if args.write and diff:
                append_ledger(args.root, state)
            print(diff or 'NOW.md state line already current')
            print(('written: NOW.md state line and ' + LEDGER.as_posix() if args.write and diff
                   else 'not written; pass --write to apply')
                  + '. Urgency U' + str(result['urgency']['urgency']) + ', ' + result['urgency']['label'] + '.')
            return 0
        else:
            value = read_json(args.file)
            if not isinstance(value, dict):
                raise ValueError('verdict file must be an object')
            history = value.get('history')
            result = judge(value.get('post'), [] if history is None else history, value.get('window_hours'),
                           value.get('elapsed_hours'))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
