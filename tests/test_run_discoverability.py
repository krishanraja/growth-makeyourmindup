"""The weekly discoverability reading (`growth.py run discoverability`), against fakes only.

Every page, row, count and label here is synthetic. No test reaches the site, Control Center or GitHub.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.control_center import validate_report
from engine.run import discoverability as d

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-30T07:30:00Z'
SITEMAP = ('<urlset><url><loc>https://www.makeyourmindup.ai/</loc></url>'
           '<url><loc>https://www.makeyourmindup.ai/music</loc></url>'
           '<url><loc>https://www.makeyourmindup.ai/creative-24</loc></url>'
           '<url><loc>https://www.makeyourmindup.ai/edition/2026-11-27</loc></url>'
           '<url><loc>https://elsewhere.example/ignored</loc></url></urlset>')
NEWS = '<urlset><url><loc>https://www.makeyourmindup.ai/edition/2026-11-27</loc></url></urlset>'


def fetch(url):
    if url.endswith('/news-sitemap.xml'):
        return NEWS
    if url.endswith('/sitemap.xml'):
        return SITEMAP
    raise OSError('unexpected ' + url)


def broken(url):
    raise OSError('offline')


def gsc(page, impressions, clicks, kind='page'):
    return {'source': 'gsc', 'kind': kind, 'host': 'www.makeyourmindup.ai', 'page': page, 'query': None,
            'day': '2026-11-20', 'impressions': impressions, 'clicks': clicks}


def directive(search=True, answers=True, subscribers=True, visits=True):
    body = {'features': {'subscriber_sources': True, 'ai_answers': True, 'search_signals': search}}
    if search:
        body['search_signals'] = {'through': '2026-11-29', 'reads': [
            {'source': 'gsc', 'part': 'search_analytics', 'host': 'www.makeyourmindup.ai', 'ok': True}], 'rows': [
            gsc('https://www.makeyourmindup.ai/music', 120, 4),
            gsc('https://www.makeyourmindup.ai/music', 30, 1),
            gsc('https://www.makeyourmindup.ai/', 50, 6),
            gsc('https://www.makeyourmindup.ai/edition/2026-11-27', 10, 0),
            gsc('https://www.makeyourmindup.ai/gaming', 0, 0),
            gsc('https://www.makeyourmindup.ai/music', 999, 99, kind='query_page'),
            gsc('https://home.makeyourmindup.ai/p/a-piece', 70, 2),
            gsc('https://elsewhere.example/x', 500, 50),
            {'source': 'bing', 'kind': 'url_info', 'page': 'https://www.makeyourmindup.ai/music', 'indexed': False},
            {'source': 'bing', 'kind': 'url_info', 'page': 'https://www.makeyourmindup.ai/music', 'indexed': True},
            {'source': 'bing', 'kind': 'url_info', 'page': 'https://www.makeyourmindup.ai/sport', 'indexed': False}]}
    if answers:
        body['ai_answers'] = {'rule': 'r', 'standing': {
            'latest': {'as_of': '2026-11-22', 'asked': 2, 'cited_first': 1, 'share': 50},
            'questions': [
                {'question': 'Synthetic question one?', 'engines': [
                    {'engine': 'perplexity', 'our_position': 1}, {'engine': 'chatgpt', 'our_position': 3},
                    {'engine': 'claude', 'our_position': None}]},
                {'question': 'Synthetic question two?', 'engines': [
                    {'engine': 'perplexity', 'our_position': None}, {'engine': 'chatgpt', 'our_position': None}]}]}}
    if subscribers:
        body['subscribers'] = {'rule': 'r', 'week_of': '2026-11-23', 'total': 9, 'organic': 6, 'paid': 0,
                               'by_source': {'Google': 2, 'chatgpt.com': 1, 'perplexity.ai': 1,
                                             'www.makeyourmindup.ai': 3, 'Substack Notes': 2},
                               'unclassified': [], 'this_week_so_far': {'since': '2026-11-30', 'total': 0,
                                                                         'organic': 0, 'by_source': {}},
                               'read_on': '2026-11-30'}
    if visits:
        body['web_analytics'] = {'through': '2026-11-29', 'rows': [
            {'date': '2026-11-20', 'dim_type': 'source_medium', 'value': 'chatgpt.com / referral', 'sessions': 5},
            {'date': '2026-11-21', 'dim_type': 'source_medium', 'value': 'chatgpt.com / referral', 'sessions': 2},
            {'date': '2026-11-21', 'dim_type': 'source_medium', 'value': 'google / organic', 'sessions': 40},
            {'date': '2026-11-21', 'dim_type': 'landing_page', 'value': 'perplexity.ai', 'sessions': 9}]}
    return {'ok': True, 'directive': body}


def objectives(report):
    return {o['key']: (o['value'], o['availability']) for o in report['objectives']}


class FakeCC:
    def __init__(self, served):
        self.served, self.reports, self.attempts = served, [], []

    def attempt(self, record):
        self.attempts.append(record)
        return {'ok': True}

    def directive(self):
        return self.served

    def post_report(self, report):
        validate_report(report)
        self.reports.append(report)
        return {'accepted': True, 'conflict': False, 'replayed': False, 'readback_matches': True,
                'payload_sha256': report['payload_sha256']}

    def decisions(self, since):
        return []


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def build(self, served, fetcher=fetch):
        from engine.core import instant
        return d.build(served, fetcher, instant(NOW), ROOT, 'synthetic')

    def test_every_part_measured_counts_each_page_once_by_desk(self):
        report, error, read = self.build(directive())
        self.assertIsNone(error)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(read['sitemap']['count'], 4)
        self.assertEqual(read['sitemap']['editions'], 1)
        groups = read['search']['by_group']
        # Page rows only: the query-page row and the other host's row are left out, the piece is its own group.
        self.assertEqual(groups['music'], {'impressions': 150, 'clicks': 5})
        self.assertEqual(groups['home'], {'impressions': 50, 'clicks': 6})
        self.assertEqual(groups['editions'], {'impressions': 10, 'clicks': 0})
        self.assertEqual(groups['pieces'], {'impressions': 70, 'clicks': 2})
        self.assertEqual(read['search']['pages_in_google'], 3)
        self.assertEqual(read['search']['sitemap_pages_in_google'], 3)
        self.assertEqual((read['search']['bing_indexed'], read['search']['bing_checked']), (1, 2))
        got = objectives(report)
        self.assertEqual(got['sitemap_pages'], (4, 'measured'))
        self.assertEqual(got['search_impressions'], (210, 'measured'))
        self.assertEqual(got['search_clicks'], (11, 'measured'))
        self.assertEqual(got['pages_indexed_bing'], (1, 'measured'))
        self.assertEqual(got['ai_questions_asked'], (2, 'measured'))
        self.assertEqual(got['ai_cited_first'], (1, 'measured'))
        self.assertEqual(got['ai_cited_any'], (1, 'measured'))
        self.assertEqual(got['subscribers_from_search'], (2, 'measured'))
        self.assertEqual(got['subscribers_from_ai'], (2, 'measured'))
        self.assertEqual(got['subscribers_from_site'], (3, 'measured'))
        self.assertEqual(got['ai_visits'], (7, 'measured'))
        self.assertEqual(read['answers']['engines']['perplexity'], {'asked': 2, 'cited': 1, 'first': 1})
        self.assertEqual(read['answers']['engines']['chatgpt'], {'asked': 2, 'cited': 1, 'first': 0})
        self.assertEqual(read['answers']['engines']['claude'], {'asked': 1, 'cited': 0, 'first': 0})
        self.assertLessEqual(len(report['objectives']), 20)

    def test_an_unserved_part_is_unknown_with_its_reason_never_zero(self):
        report, error, read = self.build(directive(search=False, answers=False, subscribers=False, visits=False))
        self.assertIsNone(error)
        got = objectives(report)
        for key in ('pages_in_google', 'pages_indexed_bing', 'search_impressions', 'search_clicks',
                    'ai_questions_asked', 'subscribers_from_ai', 'ai_visits'):
            self.assertEqual(got[key], (None, 'missing'), key)
        reasons = {o['key']: o['reason'] for o in report['objectives']}
        self.assertIn('search_signals', reasons['search_impressions'])
        self.assertEqual(got['sitemap_pages'], (4, 'measured'))
        self.assertEqual(report['status'], 'ready')

    def test_the_search_flag_off_ignores_a_stray_block(self):
        served = directive()
        served['directive']['features']['search_signals'] = False
        _, _, read = self.build(served)
        self.assertFalse(read['search']['measured'])

    def test_an_unreadable_sitemap_degrades_the_report_and_names_the_way_out(self):
        report, error, _ = self.build(directive(), broken)
        self.assertEqual(error, 'sitemap_unread')
        self.assertEqual(report['status'], 'degraded')
        self.assertEqual(objectives(report)['sitemap_pages'], (None, 'missing'))
        self.assertTrue(any('way out' in a['line'] for a in report['activity']))

    def test_source_labels_are_bucketed_by_label_not_guessed(self):
        self.assertEqual(d.bucket('Google'), 'search')
        self.assertEqual(d.bucket('chatgpt.com'), 'ai')
        self.assertEqual(d.bucket('makeyourmindup.ai'), 'site')
        self.assertIsNone(d.bucket('Substack Notes'))
        self.assertIsNone(d.bucket('Direct'))

    def test_pages_are_grouped_by_desk_and_host(self):
        self.assertEqual(d.group_of('https://www.makeyourmindup.ai/film-tv'), 'film-tv')
        self.assertEqual(d.group_of('https://makeyourmindup.ai/edition/2026-11-27#story-3'), 'editions')
        self.assertEqual(d.group_of('https://www.makeyourmindup.ai/editions'), 'editions')
        self.assertEqual(d.group_of('https://www.makeyourmindup.ai/creative-24'), 'creative-24')
        self.assertEqual(d.group_of('https://home.makeyourmindup.ai/p/x'), 'pieces')
        self.assertEqual(d.group_of('https://www.makeyourmindup.ai/terms'), 'other')
        self.assertIsNone(d.group_of('https://elsewhere.example/music'))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_delivery_reports_once_and_the_log_carries_no_number(self):
        cc, lines = FakeCC(directive()), []
        code = d.main(['discoverability', '--deliver', '--mode', 'synthetic', '--now', NOW],
                      make_client=lambda: cc, fetch=fetch, out=lines.append, root=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(len(cc.reports), 1)
        self.assertEqual(cc.reports[0]['run_id'], 'makeyourmindup:2026-11-30:discoverability')
        self.assertEqual([a['status'] for a in cc.attempts], ['started', 'succeeded'])
        log = '\n'.join(lines)
        self.assertIn('discoverability search: read', log)
        # The run's own cost line (Actions seconds, HTTP calls) and the digest are the only numbers it may print.
        reading = '\n'.join(line for line in lines if not line.startswith('Cost '))
        reading = reading.replace(cc.reports[0]['payload_sha256'], '')
        for number in ('150', '210', '11', '7', '4'):
            self.assertNotRegex(reading, r'(?<![\d.:-])' + number + r'(?![\d.:-])', number)

    def test_a_dry_run_calls_no_one_but_the_site(self):
        lines = []
        code = d.main(['discoverability', '--now', NOW], make_client=lambda: self.fail('no client on a dry run'),
                      fetch=fetch, out=lines.append, root=self.root)
        self.assertEqual(code, 0)
        self.assertTrue((self.root / '.scratch' / 'cc' / 'report-discoverability.json').exists())
        self.assertTrue(any(line.startswith('Dry run: report') for line in lines))


if __name__ == '__main__':
    unittest.main()
