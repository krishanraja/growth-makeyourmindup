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

The weekly edition (Krish, 2026-11-25: one email a week, Saturday 08:00 New
York; the Monday, Wednesday and Friday pieces go to the web and the app with
no email). Two optional blocks, so a capture made before them still reads:
`edition`, the week's edition post as its stats page shows it (recipients,
unique clicks, click rate, open rate, unsubscribes from that email and the
subscriptions Substack credits to the post), and `series_posts`, each series
post's recipients beside the size of the opt-in section for readers who want
every piece. series_email_check names each series post that emailed more
readers than that section holds: a failure the Sunday report shows
(jobs/report.md). Counts only; a number the page does not show is null with
its reason, never zero.
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
# Renewals: paid subscribers renewing and paid cancellations, by the month each first paid, as Substack's own
# dashboard shows them. Counts only, never a subscriber. Optional, so a capture made before it still reads.
RENEWAL_KEYS = {'cohorts', 'source_url', 'reason'}
COHORT_KEYS = {'first_paid_month', 'renewed', 'cancelled'}
ITEM_HOSTS = ('home.makeyourmindup.ai', 'substack.com')
# The weekly edition (Krish, 2026-11-25), read from the edition post's own stats page. Counts as shown; the two
# rates are the number the page shows before its percent sign. Optional, so a capture made before it still reads.
EDITION_COUNTS = ('recipients', 'unique_clicks', 'unsubscribes', 'new_subscriptions')
EDITION_RATES = ('click_rate', 'open_rate')
EDITION_KEYS = {'edition_date', 'url', 'source_url', 'not_shown', 'reason'} | set(EDITION_COUNTS) | set(EDITION_RATES)
# Each series post's recipients beside the opt-in section's size: a series post emails only that section.
SERIES_KEYS = {'section', 'posts', 'reason'}
SECTION_KEYS = {'name', 'subscribers', 'source_url', 'reason'}
SERIES_POST_KEYS = {'day', 'url', 'recipients', 'reason'}
SERIES_DAYS = ('mon', 'wed', 'fri')
OPTIONAL_KEYS = {'renewals', 'edition', 'series_posts'}


def last_week(now=None):
    """The Monday of the New York week before the one that holds now."""
    return measure.monday(ny_time(now).date()) - dt.timedelta(days=7)


def template(now=None):
    """The capture the job fills for last week, read not taken until it is."""
    monday = last_week(now)
    edition = dict.fromkeys(EDITION_KEYS)
    edition.update(edition_date=(monday + dt.timedelta(days=5)).isoformat(), not_shown={}, reason='not checked')
    return {'kind': KIND, 'week_of': monday.isoformat(), 'captured_at': None, 'read': 'not_taken',
            'not_taken': {'code': None, 'detail': None}, 'growth_sources': None, 'total_subscribers': None,
            'items_view': 'not_checked', 'items': [],
            'renewals': {'cohorts': [], 'source_url': None, 'reason': 'not checked'},
            'edition': dict(sorted(edition.items())),
            'series_posts': {'section': None, 'posts': [], 'reason': 'not checked'}}


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
    if not CAPTURE_KEYS <= set(capture) <= CAPTURE_KEYS | OPTIONAL_KEYS:
        raise ValueError('capture fields must be exactly ' + ', '.join(sorted(CAPTURE_KEYS))
                         + ', and renewals, edition and series_posts where they were read')
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
    if 'renewals' in capture:
        _renewals(capture['renewals'], week)
    if 'edition' in capture:
        _edition(capture['edition'], week)
    if 'series_posts' in capture:
        _series(capture['series_posts'])
    if capture['read'] == 'not_taken' and any(
            capture.get(key) is not None and capture[key]['reason'] is None for key in ('edition', 'series_posts')):
        raise ValueError('a read not taken carries no edition or series numbers; nothing is guessed')
    return capture


def _substack_url(url, field):
    host = (urlsplit(_https(url, field)).hostname or '').lower()
    if not any(host == h or host.endswith('.' + h) for h in ITEM_HOSTS):
        raise ValueError(field + ' is a page on Substack itself')
    return url


def _rate(value, field):
    """A rate as the page shows it, the number before its percent sign: 0 to 100, or null."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
        raise ValueError(field + ' is the number the page shows before its percent sign, 0 to 100, or null')
    return value


def _edition(block, week):
    """The week's edition post as its own stats page shows it, or the reason it was not read."""
    if not isinstance(block, dict) or set(block) != EDITION_KEYS:
        raise ValueError('edition needs exactly ' + ', '.join(sorted(EDITION_KEYS)))
    saturday = (week + dt.timedelta(days=5)).isoformat()
    if block['edition_date'] != saturday:
        raise ValueError('edition_date is the Saturday of the week read, ' + saturday)
    if not isinstance(block['not_shown'], dict):
        raise ValueError('edition not_shown maps each number the page did not show to the reason')
    metrics = EDITION_COUNTS + EDITION_RATES
    for key in EDITION_COUNTS:
        _count(block[key], 'edition ' + key)
    for key in EDITION_RATES:
        _rate(block[key], 'edition ' + key)
    if block['reason'] is not None:
        measure.plain(block['reason'], 'edition reason')
        if any(block[key] is not None for key in metrics) or block['not_shown']:
            raise ValueError('an edition not read carries no numbers; nothing is guessed')
        for key in ('url', 'source_url'):
            if block[key] is not None:
                _substack_url(block[key], 'edition ' + key)
        return block
    _substack_url(block['url'], 'edition url')
    _substack_url(block['source_url'], 'edition source_url')
    missing = sorted(key for key in metrics if block[key] is None)
    if sorted(block['not_shown']) != missing:
        raise ValueError('edition not_shown names every null number, and only those, with its reason')
    for key in missing:
        measure.plain(block['not_shown'][key], 'edition not_shown ' + key)
    if (block['recipients'] is not None and block['unique_clicks'] is not None
            and block['unique_clicks'] > block['recipients']):
        raise ValueError('edition unique_clicks cannot be more than its recipients')
    return block


def _series(block):
    """Each series post's recipients beside the opt-in section's size, or the reason they were not read."""
    if not isinstance(block, dict) or set(block) != SERIES_KEYS:
        raise ValueError('series_posts needs exactly ' + ', '.join(sorted(SERIES_KEYS)))
    if not isinstance(block['posts'], list):
        raise ValueError('series_posts posts is a list')
    if block['reason'] is not None:
        measure.plain(block['reason'], 'series_posts reason')
        if block['posts'] or block['section'] is not None:
            raise ValueError('series_posts not read carries no section and no posts; nothing is guessed')
        return block
    section = block['section']
    if not isinstance(section, dict) or set(section) != SECTION_KEYS:
        raise ValueError('series_posts section needs exactly ' + ', '.join(sorted(SECTION_KEYS)))
    _count(section['subscribers'], 'series_posts section subscribers')
    if section['name'] is None:
        # No opt-in section exists yet, so no reader has asked for every piece: the reason says so.
        if section['subscribers'] is not None or section['reason'] is None:
            raise ValueError('with no opt-in section, subscribers is null and the reason says there is none')
    else:
        measure.plain(section['name'], 'series_posts section name')
        if (section['subscribers'] is None) == (section['reason'] is None):
            raise ValueError('series_posts section gives its subscribers or the reason they were not shown, '
                             'not both')
    if section['reason'] is not None:
        measure.plain(section['reason'], 'series_posts section reason')
    if section['source_url'] is not None:
        _substack_url(section['source_url'], 'series_posts section source_url')
    elif section['subscribers'] is not None:
        raise ValueError('series_posts section subscribers needs the page it was read on')
    urls = []
    for n, post in enumerate(block['posts'], 1):
        at = 'series post ' + str(n)
        if not isinstance(post, dict) or set(post) != SERIES_POST_KEYS:
            raise ValueError(at + ' needs exactly ' + ', '.join(sorted(SERIES_POST_KEYS)))
        if post['day'] not in SERIES_DAYS:
            raise ValueError(at + ' day is ' + ', '.join(SERIES_DAYS))
        urls.append(_substack_url(post['url'], at + ' url'))
        _count(post['recipients'], at + ' recipients')
        if (post['recipients'] is None) == (post['reason'] is None):
            raise ValueError(at + ' gives its recipients or the reason they were not shown, not both')
        if post['reason'] is not None:
            measure.plain(post['reason'], at + ' reason')
    if len(urls) != len(set(urls)):
        raise ValueError('a series post is recorded once')
    return block


def edition_reading(capture):
    """The week's edition numbers from the capture, or null with the reason. Never zero for unknown."""
    block = capture.get('edition')
    if capture.get('read') != 'taken':
        return {'read': False, 'reason': 'the weekly read was not taken'}
    if block is None:
        return {'read': False, 'reason': 'this capture predates the weekly edition read (jobs/subscribers.md step 6b)'}
    if block['reason'] is not None:
        return {'read': False, 'edition_date': block['edition_date'], 'reason': block['reason']}
    out = {'read': True, 'edition_date': block['edition_date'], 'url': block['url'], 'reason': None,
           'not_shown': dict(block['not_shown'])}
    out.update((key, block[key]) for key in EDITION_COUNTS + EDITION_RATES)
    return out


def series_email_check(capture):
    """Did any series post email more readers than the opt-in section holds? (Krish, 2026-11-25: only the weekly
    edition emails everyone; a Monday, Wednesday or Friday piece goes to the web and the app, and by email only to
    the readers who opted in.) A post above the section's size is a failure for the Sunday report; a count the
    page did not show is unknown with its reason, never a pass."""
    empty = {'checked': 0, 'passed': 0, 'failures': [], 'unknown': [], 'allowed': None}
    block = capture.get('series_posts')
    if capture.get('read') != 'taken':
        return dict(empty, reason='the weekly read was not taken')
    if block is None:
        return dict(empty, reason='this capture predates the series email read (jobs/subscribers.md step 6c)')
    if block['reason'] is not None:
        return dict(empty, reason=block['reason'])
    section = block['section']
    allowed = 0 if section['name'] is None else section['subscribers']
    out = dict(empty, allowed=allowed, reason=None)
    for post in block['posts']:
        out['checked'] += 1
        sent = post['recipients']
        if sent is None:
            out['unknown'].append({'day': post['day'], 'url': post['url'], 'reason': post['reason']})
        elif sent == 0 or (allowed is not None and sent <= allowed):
            out['passed'] += 1
        elif allowed is None:
            out['unknown'].append({'day': post['day'], 'url': post['url'],
                                   'reason': 'the opt-in section\'s size was not shown: ' + section['reason']})
        else:
            out['failures'].append({'day': post['day'], 'url': post['url'], 'recipients': sent, 'allowed': allowed})
    return out


def _renewals(block, week):
    if not isinstance(block, dict) or set(block) != RENEWAL_KEYS:
        raise ValueError('renewals needs exactly ' + ', '.join(sorted(RENEWAL_KEYS)))
    if not isinstance(block['cohorts'], list):
        raise ValueError('renewals cohorts is a list')
    if bool(block['cohorts']) == (block['reason'] is not None):
        raise ValueError('renewals gives cohorts or the reason they were not shown, not both')
    if block['reason'] is not None:
        measure.plain(block['reason'], 'renewals reason')
        if block['source_url'] is not None:
            _https(block['source_url'], 'renewals source_url')
        return block
    _https(block['source_url'], 'renewals source_url')
    months = []
    for n, row in enumerate(block['cohorts'], 1):
        at = 'renewals cohort ' + str(n)
        if not isinstance(row, dict) or set(row) != COHORT_KEYS:
            raise ValueError(at + ' needs exactly ' + ', '.join(sorted(COHORT_KEYS)))
        month = row['first_paid_month']
        if not isinstance(month, str) or len(month) != 7 or month[4] != '-':
            raise ValueError(at + ' first_paid_month is YYYY-MM')
        first = measure.as_date(month + '-01', at + ' first_paid_month')
        if first > week:
            raise ValueError(at + ' first_paid_month is after the week read')
        _count(row['renewed'], at + ' renewed')
        _count(row['cancelled'], at + ' cancelled')
        months.append(month)
    if len(months) != len(set(months)):
        raise ValueError('a first-paid month is recorded once')
    return block


def renewals(capture):
    """The week's renewal reading from the capture: paid renewals and paid cancellations, counted only when every
    first-paid cohort shows both; otherwise null with the reason. Never zero for unknown, never a subscriber."""
    block = capture.get('renewals')
    if capture.get('read') != 'taken':
        return {'renewed': None, 'cancelled': None, 'cohorts': [], 'reason': 'the weekly read was not taken'}
    if block is None:
        return {'renewed': None, 'cancelled': None, 'cohorts': [],
                'reason': 'this capture predates the renewals read (jobs/subscribers.md step 6a)'}
    if block['reason'] is not None:
        return {'renewed': None, 'cancelled': None, 'cohorts': [], 'reason': block['reason']}
    cohorts = sorted((dict(r) for r in block['cohorts']), key=lambda r: r['first_paid_month'])
    gaps = [r['first_paid_month'] for r in cohorts if r['renewed'] is None or r['cancelled'] is None]
    if gaps:
        return {'renewed': None, 'cancelled': None, 'cohorts': cohorts,
                'reason': 'Substack did not show both counts for ' + ', '.join(gaps)}
    return {'renewed': sum(r['renewed'] for r in cohorts), 'cancelled': sum(r['cancelled'] for r in cohorts),
            'cohorts': cohorts, 'reason': None}


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
            'renewals': renewals(capture),
            'edition': edition_reading(capture),
            'series_emails': series_email_check(capture),
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
    kept = result['summary']['renewals']
    out('Renewals: ' + ('not counted, ' + kept['reason'] if kept['renewed'] is None else
                        str(kept['renewed']) + ' renewed, ' + str(kept['cancelled']) + ' cancelled across '
                        + str(len(kept['cohorts'])) + ' first-paid months') + '.')
    edition = result['summary']['edition']
    if edition['read']:
        shown = [(k, edition[k]) for k in EDITION_COUNTS]
        out('Weekly edition of ' + edition['edition_date'] + ': ' + ', '.join(
            k.replace('_', ' ') + ' ' + ('not shown' if v is None else str(v)) for k, v in shown) + '.')
    else:
        out('Weekly edition: not read, ' + edition['reason'] + '.')
    series = result['summary']['series_emails']
    if series['reason'] is not None:
        out('Series emails: not judged, ' + series['reason'] + '.')
    else:
        out('Series emails: ' + str(series['checked']) + ' series posts read, ' + str(len(series['failures']))
            + ' emailed more readers than the opt-in section holds'
            + (' (a failure for the Sunday report)' if series['failures'] else '') + ', '
            + str(len(series['unknown'])) + ' unknown.')
    if not args.write:
        out('Dry run: pass --write to record it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
