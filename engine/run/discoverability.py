"""`growth.py run discoverability [--deliver]`: the weekly discoverability reading for makeyourmindup.ai.

Krish, 2026-11-26: "make sure that this page is the most discoverable page by
search engines and AI engines and hand growth the job of improving that from
there over time." This job is how Growth sees whether that is working. It runs
on GitHub Actions every Monday (.github/workflows/discoverability.yml) and
records, once a week:

1. pages: the site's own sitemap.xml and news-sitemap.xml, read live (pages
   submitted, edition days among them); pages Google shows in search and pages
   Bing has indexed, from Control Center's search signals;
2. Google impressions and clicks by desk over the last 28 days, from the same
   signals (the six desks, the home page, the Creative 24, the editions, and
   the pieces on home.makeyourmindup.ai);
3. AI citations by engine, from AEO-Engine's newest research as the
   directive's `ai_answers` standing (protocol 1.22.0 and 1.26.0);
4. new subscribers last week from search, from AI assistants and from
   makeyourmindup.ai itself, by Substack's own source label, from the
   directive's `subscribers` block (1.32.0);
5. visits from AI assistants to the publication, from the GA4 source rows in
   `web_analytics` (1.10.0), as supporting evidence only.

Search signals are what Control Center already reads each day into
growth_search_signals (Search Console, Bing). Until it serves them to this
engine as `search_signals` (docs/briefs/2026-11-26-search-signals-for-growth.md),
parts 1 and 2 beyond the sitemap are unknown with that reason, never zero.

The numbers go only into the Control Center report (its objectives and
activity lines), never into this public repository or its log: the log says
which parts were read. Without --deliver it writes the report to the ignored
.scratch/cc/report-discoverability.json and calls nothing but the public site.
Nothing here posts, sends, publishes or spends.
"""
import argparse
import datetime as dt
from pathlib import Path
import re
from urllib.parse import urlsplit
import urllib.request

from .. import meter
from ..cc_loop import STATE_DIR, revision, run, subscribers_block, summary, web_analytics_block
from ..control_center import SLUG, build_report, objective
from ..core import instant, today, write_json
from . import outcome

ROOT = Path(__file__).resolve().parents[2]
COMMAND = 'discoverability'
SITE = 'https://www.makeyourmindup.ai'
SITE_HOSTS = ('www.makeyourmindup.ai', 'makeyourmindup.ai')
PIECES_HOST = 'home.makeyourmindup.ai'
SITEMAPS = ('/sitemap.xml', '/news-sitemap.xml')
DESKS = ('music', 'film-tv', 'gaming', 'sport', 'publishing-media', 'art-design')
GROUPS = DESKS + ('home', 'creative-24', 'editions', 'pieces', 'other')
WINDOW_DAYS = 28
FETCH_SECONDS = 20
SEARCH_FEATURE = 'search_signals'
# Substack's own source labels, lower-cased. Search engines by exact label; an AI assistant by a word in the label,
# since Substack shows a referring host (chatgpt.com, perplexity.ai) as its label.
SEARCH_LABELS = {'google', 'google search', 'bing', 'duckduckgo', 'search', 'yahoo', 'ecosia', 'brave', 'startpage',
                 'yandex', 'baidu', 'naver', 'qwant'}
AI_WORDS = ('chatgpt', 'openai', 'perplexity', 'claude', 'anthropic', 'gemini', 'copilot', 'meta.ai', 'grok',
            'mistral', 'deepseek', 'you.com', 'phind', 'kagi')
SITE_LABELS = set(SITE_HOSTS)
NOT_SERVED = ('Control Center does not serve search_signals to this engine yet '
              '(docs/briefs/2026-11-26-search-signals-for-growth.md)')
NOT_MEASURED = 'The discoverability job reads sources by label, not the North Star; the numbers job measures it'
LOC = re.compile(r'<loc>\s*([^<\s]+)\s*</loc>')
TALLY = ('impressions', 'clicks')


def run_id(now):
    return SLUG + ':' + today(now) + ':' + COMMAND


def read_url(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'makeyourmindup-growth/1.0', 'Accept': 'application/xml'})
    with urllib.request.urlopen(request, timeout=FETCH_SECONDS) as response:  # noqa: S310 (a fixed https URL)
        return response.read(2_000_000).decode('utf-8', 'replace')


def _path(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return None, None
    path = parts.path.rstrip('/') or '/'
    return (parts.hostname or '').lower(), path


def group_of(url):
    """The desk or group a page belongs to: a desk page, the home page, the index, an edition, or a piece."""
    host, path = _path(url)
    if host == PIECES_HOST:
        return 'pieces'
    if host not in SITE_HOSTS:
        return None
    if path == '/':
        return 'home'
    first = path.split('/')[1]
    if first in DESKS or first == 'creative-24':
        return first
    if first in ('edition', 'editions'):
        return 'editions'
    return 'other'


def sitemap_part(fetch):
    """The pages the site submits, read live, or the reason they could not be read."""
    pages, editions, errors = set(), 0, []
    for path in SITEMAPS:
        try:
            body = fetch(SITE + path)
        except (OSError, ValueError) as exc:
            errors.append(path + ' ' + type(exc).__name__)
            continue
        for url in LOC.findall(body):
            host, page = _path(url)
            if host in SITE_HOSTS and page:
                pages.add(page)
    editions = sum(1 for p in pages if p.startswith('/edition/'))
    if errors and not pages:
        return {'measured': False, 'reason': 'the sitemaps could not be read: ' + ', '.join(errors)}
    return {'measured': True, 'pages': sorted(pages), 'count': len(pages), 'editions': editions, 'errors': errors}


def search_block(directive):
    """Control Center's search signals for this product, served behind features.search_signals, or None."""
    body = directive.get('directive') if isinstance(directive, dict) and isinstance(directive.get('directive'), dict) \
        else directive if isinstance(directive, dict) else {}
    features = body.get('features') if isinstance(body.get('features'), dict) else {}
    block = body.get(SEARCH_FEATURE)
    if features.get(SEARCH_FEATURE) is not True or not isinstance(block, dict) or not isinstance(block.get('rows'), list):
        return None
    return block


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def search_part(block, sitemap):
    """Google impressions and clicks by group, the pages Google shows, and the pages Bing has indexed."""
    if block is None:
        return {'measured': False, 'reason': NOT_SERVED}
    by_group = {g: dict.fromkeys(TALLY, 0) for g in GROUPS}
    shown, indexed = set(), {}
    for row in block['rows']:
        if (isinstance(row, dict) and row.get('source') == 'bing' and row.get('kind') == 'url_info'
                and isinstance(row.get('page'), str) and isinstance(row.get('indexed'), bool)
                and group_of(row['page']) not in (None, 'pieces')):
            indexed[row['page']] = row['indexed']  # rows come oldest first, so the newest word stands
    # Page rows and query-page rows count the same impressions twice: totals come from the page rows, and from
    # the query-page rows only when no page row was served.
    pages = [r for r in block['rows'] if isinstance(r, dict) and r.get('source') == 'gsc'
             and r.get('kind') == 'page' and isinstance(r.get('page'), str)]
    if not pages:
        pages = [r for r in block['rows'] if isinstance(r, dict) and r.get('source') == 'gsc'
                 and r.get('kind') == 'query_page' and isinstance(r.get('page'), str)]
    for row in pages:
        group = group_of(row['page'])
        if group is None:
            continue
        for key in TALLY:
            value = _number(row.get(key))
            if value is not None:
                by_group[group][key] += value
        if (_number(row.get('impressions')) or 0) > 0 and group != 'pieces':
            shown.add(_path(row['page'])[1])
    reads = [r for r in block.get('reads') or [] if isinstance(r, dict)]
    gsc_ok = any(r.get('source') == 'gsc' and r.get('ok') is True and r.get('host') in SITE_HOSTS for r in reads)
    submitted = set(sitemap.get('pages') or [])
    return {'measured': True, 'gsc_read': gsc_ok or bool(pages), 'by_group': by_group,
            'pages_in_google': len(shown), 'sitemap_pages_in_google': len(shown & submitted),
            'bing_checked': len(indexed), 'bing_indexed': sum(1 for v in indexed.values() if v),
            'through': block.get('through')}


def answers_part(directive):
    """AI citations by engine from AEO's newest research, or why they are unknown."""
    body = directive.get('directive') if isinstance(directive, dict) and isinstance(directive.get('directive'), dict) \
        else directive if isinstance(directive, dict) else {}
    block = body.get('ai_answers')
    standing = block.get('standing') if isinstance(block, dict) else None
    if not isinstance(standing, dict):
        return {'measured': False, 'reason': 'no AI-answer standing in the directive (AEO has not reported on the '
                                             'publication, or Control Center could not read it)'}
    latest = standing.get('latest') if isinstance(standing.get('latest'), dict) else None
    engines = {}
    for q in standing.get('questions') or []:
        if not isinstance(q, dict):
            continue
        for e in q.get('engines') or []:
            if not isinstance(e, dict) or not isinstance(e.get('engine'), str):
                continue
            row = engines.setdefault(e['engine'], {'asked': 0, 'cited': 0, 'first': 0})
            row['asked'] += 1
            position = e.get('our_position')
            if isinstance(position, int) and not isinstance(position, bool) and position >= 1:
                row['cited'] += 1
                row['first'] += position == 1
    if latest is None and not engines:
        return {'measured': False, 'reason': 'AEO has asked no question for the publication yet'}
    return {'measured': True, 'as_of': latest.get('as_of') if latest else None,
            'asked': _number(latest.get('asked')) if latest else None,
            'cited_first': _number(latest.get('cited_first')) if latest else None,
            'cited_any': sum(1 for q in standing.get('questions') or [] if isinstance(q, dict) and any(
                isinstance(e, dict) and isinstance(e.get('our_position'), int) and e['our_position'] >= 1
                for e in q.get('engines') or [])) if engines else None,
            'engines': engines}


def bucket(label):
    text = str(label).strip().lower()
    if text in SITE_LABELS:
        return 'site'
    if text in SEARCH_LABELS:
        return 'search'
    if any(word in text for word in AI_WORDS):
        return 'ai'
    return None


def subscribers_part(directive):
    """Last New York week's new subscribers from search, AI assistants and the site, by Substack's label."""
    block = subscribers_block(directive)
    if block is None:
        return {'measured': False, 'reason': 'subscribers by source not served today (Control Center reads them from '
                                             "Substack's notices; absent when unread or older than 3 days)"}
    counts = {'search': 0, 'ai': 0, 'site': 0}
    labels = {'search': [], 'ai': [], 'site': []}
    for label, value in block['by_source'].items():
        kind = bucket(label)
        if kind and _number(value) is not None:
            counts[kind] += value
            labels[kind].append(str(label))
    return {'measured': True, 'week_of': block['week_of'], 'counts': counts, 'labels': labels,
            'total': block.get('total')}


def visits_part(directive):
    """Sessions from AI assistants over the GA4 window, by source, from the web_analytics source rows."""
    block = web_analytics_block(directive)
    rows = block.get('rows') if isinstance(block, dict) else None
    if not isinstance(rows, list):
        return {'measured': False, 'reason': 'GA4 source rows not served today'}
    by_source = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('dim_type') != 'source_medium':
            continue
        source = str(row.get('value') or '').split('/')[0].strip().lower()
        sessions = _number(row.get('sessions'))
        if sessions is not None and any(word in source for word in AI_WORDS):
            by_source[source] = by_source.get(source, 0) + sessions
    return {'measured': True, 'by_source': by_source, 'through': block.get('through')}


def reading(directive, fetch):
    sitemap = sitemap_part(fetch)
    return {'sitemap': sitemap, 'search': search_part(search_block(directive), sitemap),
            'answers': answers_part(directive), 'subscribers': subscribers_part(directive),
            'visits': visits_part(directive)}


def _measured(key, value, unit_window):
    start, end = unit_window
    if value is None:
        return objective(key, reason='not in the reading')
    return objective(key, value, 'measured', window_start=start, window_end=end)


def objectives(read, now):
    week = (now - dt.timedelta(days=7), now)
    window = (now - dt.timedelta(days=WINDOW_DAYS), now)
    out = [objective('new_subscribers', reason=NOT_MEASURED)]
    s = read['sitemap']
    out.append(_measured('sitemap_pages', s['count'], (now, now)) if s['measured']
               else objective('sitemap_pages', reason=s['reason']))
    g = read['search']
    if g['measured']:
        out += [_measured('pages_in_google', g['pages_in_google'], window),
                _measured('pages_indexed_bing', g['bing_indexed'] if g['bing_checked'] else None, window),
                _measured('search_impressions', sum(v['impressions'] for k, v in g['by_group'].items() if k != 'pieces'),
                          window),
                _measured('search_clicks', sum(v['clicks'] for k, v in g['by_group'].items() if k != 'pieces'), window)]
    else:
        out += [objective(k, reason=g['reason']) for k in
                ('pages_in_google', 'pages_indexed_bing', 'search_impressions', 'search_clicks')]
    a = read['answers']
    if a['measured']:
        out += [_measured('ai_questions_asked', a['asked'], week), _measured('ai_cited_first', a['cited_first'], week),
                _measured('ai_cited_any', a['cited_any'], week)]
    else:
        out += [objective(k, reason=a['reason']) for k in ('ai_questions_asked', 'ai_cited_first', 'ai_cited_any')]
    n = read['subscribers']
    for key in ('search', 'ai', 'site'):
        name = 'subscribers_from_' + key
        out.append(_measured(name, n['counts'][key], week) if n['measured'] else objective(name, reason=n['reason']))
    v = read['visits']
    out.append(_measured('ai_visits', sum(v['by_source'].values()), window) if v['measured']
               else objective('ai_visits', reason=v['reason']))
    return out


def activity(read):
    """The detail, for Control Center only: this repository is public, so none of it reaches the log."""
    lines = []
    s = read['sitemap']
    lines.append('Sitemaps: ' + (str(s['count']) + ' pages submitted, ' + str(s['editions']) + ' edition days'
                                 + ('; unread: ' + ', '.join(s['errors']) if s['errors'] else '')
                                 if s['measured'] else 'unknown, ' + s['reason']))
    g = read['search']
    if g['measured']:
        lines.append('Google, last ' + str(WINDOW_DAYS) + ' days through ' + str(g['through']) + ', impressions/clicks: '
                     + ', '.join(k + ' ' + str(v['impressions']) + '/' + str(v['clicks'])
                                 for k, v in g['by_group'].items() if v['impressions'] or v['clicks'])
                     + '; pages shown ' + str(g['pages_in_google']) + ' (' + str(g['sitemap_pages_in_google'])
                     + ' of the sitemap)')
        lines.append('Bing: ' + str(g['bing_indexed']) + ' of ' + str(g['bing_checked']) + ' checked pages indexed')
    else:
        lines.append('Search impressions, clicks and indexing: unknown, ' + g['reason'])
    a = read['answers']
    if a['measured']:
        lines.append('AI answers (AEO, research of ' + str(a['as_of']) + '): ' + str(a['asked']) + ' asked, '
                     + str(a['cited_first']) + ' cited first; by engine asked/cited/first: '
                     + (', '.join(e + ' ' + '/'.join(str(r[k]) for k in ('asked', 'cited', 'first'))
                                  for e, r in sorted(a['engines'].items())) or 'no per-engine detail served'))
    else:
        lines.append('AI answers: unknown, ' + a['reason'])
    n = read['subscribers']
    if n['measured']:
        lines.append('New subscribers, week of ' + n['week_of'] + ': search ' + str(n['counts']['search']) + ', AI '
                     + str(n['counts']['ai']) + ', makeyourmindup.ai ' + str(n['counts']['site']) + ' of '
                     + str(n['total']) + ' (labels: ' + '; '.join(k + ' ' + ', '.join(v) for k, v in n['labels'].items()
                                                              if v) + ')')
    else:
        lines.append('New subscribers by source: unknown, ' + n['reason'])
    v = read['visits']
    lines.append('AI assistant visits (GA4, supporting): ' + (', '.join(k + ' ' + str(c) for k, c in
                                                                         sorted(v['by_source'].items())) or 'none seen')
                 if v['measured'] else 'AI assistant visits: unknown, ' + v['reason'])
    return [{'line': line} for line in lines]


def log_lines(read):
    """What the public log may say: which parts were read, never a number."""
    return ['discoverability ' + name + ': ' + ('read' if part['measured'] else 'unknown')
            for name, part in read.items()]


def build(directive, fetch, now, root, mode):
    read = reading(directive, fetch)
    lines = activity(read)
    measured = [k for k, part in read.items() if part['measured']]
    error = None if read['sitemap']['measured'] else 'sitemap_unread'
    status = 'held' if not measured else ('degraded' if error else 'ready')
    row = (outcome.row('blocked', 'the sitemaps could not be read', 'lookup filed: the next weekly run reads them '
                       'again; check www.makeyourmindup.ai/sitemap.xml by hand if it fails twice') if error
           else outcome.row('advanced', str(len(measured)) + ' of ' + str(len(read)) + ' parts measured'))
    lines.append({'line': outcome.line(row)})
    lines.append({'line': 'Posted, sent, published and spent nothing'})
    holds = [] if measured else [{'reason': 'Nothing to measure this run', 'detail': None}]
    report = build_report(run_id(now), mode, now, revision(root), now, status, objectives(read, now), lines, [], [],
                          holds)
    return report, error, read


def main(argv=None, make_client=None, fetch=read_url, out=print, root=ROOT):
    parser = argparse.ArgumentParser(prog='growth.py run discoverability', description=__doc__.split('\n')[0])
    parser.add_argument('command', nargs='?')
    parser.add_argument('--deliver', action='store_true')
    parser.add_argument('--mode', choices=('live', 'synthetic'), default='live')
    parser.add_argument('--now')
    args = parser.parse_args(argv)
    root = Path(root)
    clock = (lambda: instant(args.now)) if args.now else (lambda: instant())
    now = clock()
    seen = {}

    def work(directive):
        report, error, read = build(directive, fetch, clock(), root, args.mode)
        seen['read'] = read
        return report, error

    if not args.deliver:
        report, error = work(None)
        write_json(root / STATE_DIR / 'report-discoverability.json', report)
        for line in log_lines(seen['read']):
            out(line)
        out('Dry run: report ' + report['status'] + ', payload_sha256 ' + report['payload_sha256'] + '; written to '
            + str(STATE_DIR / 'report-discoverability.json') + '; no Control Center call')
        return int(bool(error))
    if make_client is None:
        import growth
        make_client = growth.engine_client
    cc = make_client()
    result = run(cc, COMMAND, run_id(now), work, now - dt.timedelta(days=7), clock)
    if result.get('report'):
        write_json(root / STATE_DIR / 'report-discoverability.json', result['report'])
    for line in log_lines(seen['read']) if 'read' in seen else []:
        out(line)
    for line in summary(result, public=True):
        out(line)
    out(meter.cost_line('in all'))
    return int(result['status'] != 'succeeded')
