"""The weekly Substack subscriber read: one capture a week, one North Star reading.

Ruling (Krish, 2026-11-12): the engine reads subscribers every week and judges
posts by subscribers, not engagement.

Substack has no public API, so the reading is taken in Krish's signed-in
browser on his PC by the automation "Growth: subscribers" (automations.json,
Mondays 06:15 New York), which follows jobs/subscribers.md exactly. That job
saves one capture for the week just finished under .scratch/substack/ and
then records it here:

    python growth.py run subscribers template [--now TIME] [--out FILE]
    python growth.py run subscribers ingest FILE [--write] [--now TIME]

`template` writes the empty capture for last week (Monday to Sunday, New York)
for the job to fill. `ingest` validates the capture and, through the North
Star code in engine/run/measure.py (the same path as `growth.py run
northstar`), builds the week's state line: the organic count against that
week's rung, or null with the reason (classification not approved, a window
that misses the week, a read that could not be taken). With --write it
replaces NOW.md's state line when that loses nothing (measure.keeps) and
appends the reading to lists/northstar-history.jsonl in either case, once.
The total, the sources and the per-post and per-Note rows stay in the ignored
.scratch/substack/weekly.jsonl: only the North Star line and its ledger are
committed, as they already are.

A read that could not be taken is recorded as unknown with its reason code,
never a guess and never zero. Nothing here opens a network connection, reads
a cookie or a password, or changes a Substack setting.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from ..core import http_url, instant, ny_time, read_json, write_json
from . import measure

ROOT = Path(__file__).resolve().parents[2]
KIND = 'substack_subscribers_weekly'
SCRATCH = Path('.scratch') / 'substack'
HISTORY = SCRATCH / 'weekly.jsonl'
CAPTURE_KEYS = {'kind', 'week_of', 'captured_at', 'read', 'not_taken', 'growth_sources', 'total_subscribers',
                'items_view', 'items'}
NOT_TAKEN = {
    'signed_out': 'the browser was not signed in to Substack as Krish',
    'browser_unavailable': 'no signed-in browser was available to the automation',
    'page_changed': 'the dashboard did not show the subscriber growth by source view the job names',
    'not_settled': 'the window label and its values never agreed (F54), so nothing was read',
    'window_unavailable': 'the dashboard offered no window the job could read',
    'substack_unreachable': 'the Substack dashboard did not load',
}
ITEMS_VIEWS = ('per_item', 'category_only', 'not_checked')
ITEM_KINDS = ('post', 'note')
ITEM_KEYS = {'kind', 'url', 'window_label', 'new_free', 'new_paid'}
TOTAL_KEYS = {'value', 'free', 'paid', 'source_url', 'reason'}
ITEM_HOSTS = ('home.makeyourmindup.ai', 'substack.com')


def last_week(now=None):
    """The Monday of the New York week before the one that holds now."""
    return measure.monday(ny_time(now).date()) - dt.timedelta(days=7)


def template(now=None):
    """The capture the job fills for last week, read not taken until it is."""
    monday = last_week(now)
    return {'kind': KIND, 'week_of': monday.isoformat(), 'captured_at': None, 'read': 'not_taken',
            'not_taken': {'code': None, 'detail': None}, 'growth_sources': None, 'total_subscribers': None,
            'items_view': 'not_checked', 'items': []}


def _count(value, field):
    return measure.count(value, field)


def _https(url, field):
    if not http_url(url) or urlsplit(url).scheme != 'https':
        raise ValueError(field + ' must be an https URL without credentials')
    return url


def _item(item, at):
    if not isinstance(item, dict) or set(item) != ITEM_KEYS:
        raise ValueError(at + ' needs exactly ' + ', '.join(sorted(ITEM_KEYS)))
    if item['kind'] not in ITEM_KINDS:
        raise ValueError(at + ' kind is post or note')
    host = (urlsplit(_https(item['url'], at + ' url')).hostname or '').lower()
    if not any(host == h or host.endswith('.' + h) for h in ITEM_HOSTS):
        raise ValueError(at + ' url is the post or Note on Substack itself')
    measure.plain(item['window_label'], at + ' window_label')
    _count(item['new_free'], at + ' new_free')
    _count(item['new_paid'], at + ' new_paid')
    return item


def validate(capture, now=None):
    """The weekly capture in its closed shape; the Growth-sources part by measure.validate_capture (F54)."""
    if not isinstance(capture, dict) or capture.get('kind') != KIND:
        raise ValueError('capture must be a ' + KIND + ' object')
    if set(capture) != CAPTURE_KEYS:
        raise ValueError('capture fields must be exactly ' + ', '.join(sorted(CAPTURE_KEYS)))
    week = measure.as_date(capture['week_of'], 'week_of')
    if week.weekday() != 0:
        raise ValueError('week_of is the Monday of the week read')
    if not isinstance(capture['captured_at'], str):
        raise ValueError('captured_at must be a timestamp with an offset')
    captured = instant(capture['captured_at'])
    if captured > instant(now):
        raise ValueError('captured_at is in the future')
    if ny_time(captured).date() <= week:
        raise ValueError('the week is read after its Monday')
    if capture['read'] == 'not_taken':
        missing = capture['not_taken']
        if not isinstance(missing, dict) or set(missing) != {'code', 'detail'} or missing['code'] not in NOT_TAKEN:
            raise ValueError('a read not taken names its code: ' + ', '.join(sorted(NOT_TAKEN)))
        if missing['detail'] is not None:
            measure.plain(missing['detail'], 'not_taken detail')
        if capture['growth_sources'] is not None or capture['items']:
            raise ValueError('a read not taken carries no growth_sources or items; nothing is guessed')
    elif capture['read'] == 'taken':
        if capture['not_taken'] is not None:
            raise ValueError('a read taken has not_taken null')
        measure.validate_capture(capture['growth_sources'], now)
        if instant(capture['growth_sources']['captured_at']) > captured:
            raise ValueError('the Growth-sources read is later than the capture')
    else:
        raise ValueError('read is taken or not_taken')
    total = capture['total_subscribers']
    if total is not None:
        if not isinstance(total, dict) or set(total) != TOTAL_KEYS:
            raise ValueError('total_subscribers needs exactly ' + ', '.join(sorted(TOTAL_KEYS)))
        for key in ('value', 'free', 'paid'):
            _count(total[key], 'total_subscribers ' + key)
        _https(total['source_url'], 'total_subscribers source_url')
        if (total['value'] is None) == (total['reason'] is None):
            raise ValueError('total_subscribers gives a value or the reason it was not shown, not both')
        if total['reason'] is not None:
            measure.plain(total['reason'], 'total_subscribers reason')
    if capture['items_view'] not in ITEMS_VIEWS:
        raise ValueError('items_view is ' + ', '.join(ITEMS_VIEWS))
    if not isinstance(capture['items'], list):
        raise ValueError('items is a list')
    if capture['items'] and capture['items_view'] != 'per_item':
        raise ValueError('items are recorded only when Substack shows subscribers per post or per Note')
    urls = [_item(item, 'item ' + str(n))['url'] for n, item in enumerate(capture['items'], 1)]
    if len(urls) != len(set(urls)):
        raise ValueError('an item is recorded once')
    return capture


def _target(metric, week):
    ladder = metric['ladder']
    if isinstance(ladder, list) and ladder and week > ladder[-1][0]:
        return ladder[-1][1]  # after the last rung the final target stands; the deadline rule applies
    return measure.week_target(week, metric)


def not_taken_line(capture, root=ROOT, history=()):
    """The state line for a week whose read could not be taken: unknown with its reason, never zero."""
    week = measure.as_date(capture['week_of'])
    metric = measure.north_star(Path(root) / 'docs' / 'NORTH_STAR.md')
    if metric.get('status') == 'paused':
        raise ValueError('the North Star is paused, so it carries no urgency until Krish revives it')
    target = _target(metric, week)
    read_on = ny_time(capture['captured_at']).date()
    day = min(read_on, week + dt.timedelta(days=6))
    code = capture['not_taken']['code']
    source = ('Substack Growth sources for the week of {} not read on {}: {} ({})').format(
        week.isoformat(), read_on.isoformat(), code, NOT_TAKEN[code])
    level = measure.urgency(None, target, None, day, list(history), metric.get('deadline'))
    return {'line': measure.state_line(week, target, None, None, source, level['urgency'], level['urgency_reason']),
            'urgency': level, 'week_of': week.isoformat(), 'week_target': target,
            'not_counted_because': 'the read was not taken: ' + code}


def reading_day(capture):
    """The day the North Star code reads the capture as of: the window's last day, so a whole week read on the
    Monday after counts for that week, and a window that misses it says so."""
    return capture['growth_sources']['window']['end']


def item_verdicts(items):
    """Substack's own per-post and per-Note numbers, where it shows them, judged by subscribers
    (measure.judge_subscribers, Ruling, Krish, 2026-11-12): a new subscriber works; a zero with no visit count
    beside it is too little to call a fail; not shown is insufficient. Counts by verdict."""
    out = dict.fromkeys(('works', 'neutral', 'fails', 'insufficient'), 0)
    for item in items:
        shown = item['new_free'] is not None or item['new_paid'] is not None
        gained = (item['new_free'] or 0) + (item['new_paid'] or 0) if shown else None
        result = measure.judge_subscribers(gained, None, measure.SUBSCRIBER_WINDOW_HOURS,
                                           reason='Substack did not show a count for it')
        out[result['verdict']] += 1
    return out


def summary(capture, result):
    """The private weekly record kept in .scratch/substack/weekly.jsonl, never committed."""
    items = capture['items']

    def gained(item):
        return None if item['new_free'] is None and item['new_paid'] is None \
            else (item['new_free'] or 0) + (item['new_paid'] or 0)
    shown = [gained(i) for i in items if gained(i) is not None]
    sources = capture['growth_sources']
    return {'schema': 'growth-subscribers-week/1', 'week_of': capture['week_of'],
            'captured_at': capture['captured_at'], 'read': capture['read'],
            'not_taken': (capture['not_taken'] or {}).get('code'),
            'window': sources['window'] if sources else None,
            'all_source_new': result.get('classification', {}).get('all_source') if sources else None,
            'organic_new': result.get('classification', {}).get('organic') if sources else None,
            'paid_new': result.get('paid_subscribers'),
            'sources': [dict(r) for r in sources['rows']] if sources else [],
            'total_subscribers': capture['total_subscribers'],
            'items_view': capture['items_view'],
            'items': {'recorded': len(items), 'with_a_new_subscriber': len([g for g in shown if g >= 1]),
                      'with_none': len([g for g in shown if g == 0]), 'not_shown': len(items) - len(shown)},
            'items_by_subscribers': item_verdicts(items),
            'north_star': {'week_of': result['week_of'], 'week_target': result['week_target'],
                           'urgency': result['urgency']['urgency'],
                           'not_counted_because': result['not_counted_because']}}


def in_ledger(root, state):
    """True when this exact state is already a ledger line, so a re-run records it once."""
    wanted = dict((k, state.get(k)) for k in measure.STATE_KEYS)
    return any(dict((k, e.get(k)) for k in measure.STATE_KEYS) == wanted for e in measure.read_ledger(root))


def ingest(capture, root=ROOT, write=False, now=None, sources='invariants/sources.json'):
    """Validate, build the week's state line and, with write, record it. Returns what happened."""
    validate(capture, now)
    root = Path(root)
    existing = measure.current_state(root)
    history = measure.read_ledger(root) + [existing]
    if capture['read'] == 'taken':
        result = measure.northstar(capture['growth_sources'], reading_day(capture), root, sources, history, now)
    else:
        result = not_taken_line(capture, root, history)
    state = measure.state_of(result['line'])
    try:
        measure.keeps(existing, state, result['not_counted_because'])
        now_kept, why_kept = True, None
    except ValueError as exc:
        now_kept, why_kept = False, str(exc)  # NOW.md keeps its newer or measured line; the ledger still records
    diff = measure.write_now(root, result['line'], write) if now_kept else ''
    recorded = False
    if write and not in_ledger(root, state):
        measure.append_ledger(root, state)
        recorded = True
    if write:
        path = root / HISTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(summary(capture, result), sort_keys=True) + '\n')
    return {'state': state, 'diff': diff, 'now_md': 'replaced' if diff and write else
            ('would replace' if diff else ('kept: ' + why_kept if why_kept else 'already current')),
            'ledger': 'appended' if recorded else ('already recorded' if write else 'not written'),
            'urgency': result['urgency'], 'not_counted_because': result['not_counted_because'],
            'summary': summary(capture, result)}


def _private_out(path, root):
    """The capture holds private figures: inside this repository it is written only under .scratch/."""
    path = Path(path)
    path = path if path.is_absolute() else Path.cwd() / path
    base = Path(root).resolve()
    resolved = path.resolve()
    if (resolved == base or base in resolved.parents) and (base / '.scratch').resolve() not in resolved.parents:
        raise ValueError('the capture stays out of the public repository; write it under .scratch/')
    return path


def main(argv=None, out=print, root=ROOT):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog='growth.py run subscribers', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('template', help="the empty capture for last week's read")
    t.add_argument('--now'); t.add_argument('--out')
    i = sub.add_parser('ingest', help='validate a capture and record the North Star reading')
    i.add_argument('file'); i.add_argument('--write', action='store_true'); i.add_argument('--now')
    i.add_argument('--sources', default='invariants/sources.json')
    for command in (t, i):
        command.add_argument('--root', default=str(root))
    args = parser.parse_args(argv[1:] if argv and argv[0] == 'subscribers' else argv)
    try:
        if args.cmd == 'template':
            value = template(args.now)
            path = _private_out(args.out or Path(args.root) / SCRATCH / ('week-' + value['week_of'] + '.json'),
                                args.root)
            if path.exists():
                raise ValueError(str(path) + ' exists; a capture is never overwritten')
            write_json(path, value)
            out('written ' + str(path) + ': fill it from the dashboard as jobs/subscribers.md says')
            return 0
        result = ingest(read_json(args.file), args.root, args.write, args.now, args.sources)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        out(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    state = result['state']
    out(result['diff'] or 'NOW.md state line unchanged')
    out('Week of ' + state['week_of'] + ': ' + ('not counted, ' + str(result['not_counted_because'])
                                               if state['current'] is None else
                                               '{:,} of {:,}'.format(state['current'], state['week_target']))
        + '. Urgency U' + str(state['urgency']) + ', ' + result['urgency']['label'] + '.')
    out('NOW.md: ' + result['now_md'] + '. ' + measure.LEDGER.as_posix() + ': ' + result['ledger'] + '.')
    items = result['summary']['items']
    judged = result['summary']['items_by_subscribers']
    out('Per post and per Note (' + result['summary']['items_view'] + '): ' + str(items['recorded'])
        + ' recorded, ' + str(items['with_a_new_subscriber']) + ' with a new subscriber, '
        + str(items['with_none']) + ' with none, ' + str(items['not_shown']) + ' not shown; by subscribers '
        + ', '.join(k + ' ' + str(v) for k, v in judged.items()) + '.')
    if not args.write:
        out('Dry run: pass --write to record it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
