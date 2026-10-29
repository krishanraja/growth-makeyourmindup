"""The scheduled measure job (`growth.py run measure auto`), against fakes only.

Every post, metric, channel and GA4 row here is synthetic. No test reaches
Buffer, Control Center or GitHub.
"""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from engine import cc_loop
from engine.core import instant, read_json, write_json
from engine.control_center import validate_report
from engine.run import measure, measure_auto
from engine.run.measure_auto import NEW_CHANNEL, verdicts
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.run.release import BUFFER_NAME
from test_control_center import StandIn, TOKEN

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'ga4'
NOW = '2026-11-05T13:00:00Z'
LINK = ('https://home.makeyourmindup.ai/p/synthetic-piece?utm_source={src}&utm_medium=organic'
        '&utm_campaign=growth&utm_content={content}')
SERVICES = {'substack-notes': 'substack', 'threads': 'threads', 'x': 'twitter', 'instagram': 'instagram',
            'facebook': 'facebook', 'tiktok': 'tiktok', 'youtube': 'youtube', 'linkedin': 'linkedin'}


def channel_id(n):
    return '{:024x}'.format(0xabc000 + n)


# The pinned Buffer channelIds (engine/buffer_channels.py): main's channel lock refuses any other.
CHANNEL_IDS = dict(BUFFER_CHANNEL_ID)


def post(n, cid, days_ago, impressions=None, text='TEST FIXTURE ONLY. A synthetic post.', via='api', with_metrics=True,
         channel=None):
    sent = instant(NOW) - dt.timedelta(days=days_ago)
    item = {'id': '{:024x}'.format(0xf00000 + n), 'status': 'sent', 'via': via, 'text': text,
            'sentAt': sent.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'channelId': CHANNEL_IDS.get(cid, channel_id(99)), 'channelService': SERVICES.get(cid, 'threads'),
            'channel': channel or {'id': CHANNEL_IDS[cid], 'name': BUFFER_NAME[cid], 'service': SERVICES[cid],
                                   'isDisconnected': False, 'isLocked': False}}
    if with_metrics:
        item['metrics'] = [] if impressions is None else [
            {'type': 'impressions', 'value': float(impressions), 'unit': 'count'},
            {'type': 'engagementRate', 'value': 3.5, 'unit': 'percentage'}]
    return item


class FakeBuffer:
    """list_posts and get_post, the whole interface the measure job needs."""

    def __init__(self, posts, details=None):
        self.posts, self.details = posts, details or {}
        self.calls = []

    def list_posts(self, status, since):
        self.calls.append(('list_posts', status, since))
        return {'edges': [{'node': p} for p in self.posts]}

    def get_post(self, post_id):
        self.calls.append(('get_post', post_id))
        return self.details[post_id]


def x_history(values, start=20):
    """Settled X posts, one a day, oldest first, more than 14 days into the channel."""
    return [post(100 + i, 'x', start - i, v) for i, v in enumerate(values)]


class VerdictRuleTests(unittest.TestCase):
    def setUp(self):
        self.now = instant(NOW)

    def read(self, posts):
        from engine.run.buffer_reads import sent_posts
        return sent_posts(FakeBuffer(posts), self.now - dt.timedelta(days=56), self.now)['posts']

    def by_id(self, posts):
        results, channels = verdicts(self.read(posts), NOW)
        return {r['post_id']: r for r in results}, channels

    def test_works_neutral_and_fails_against_the_channels_own_median(self):
        history = x_history([100, 100, 100, 100, 100, 100])
        results, channels = self.by_id(history + [post(1, 'x', 3, 200), post(2, 'x', 4, 100), post(3, 'x', 5, 40)])
        self.assertEqual(results[post(1, 'x', 3)['id']]['verdict'], 'works')
        self.assertEqual(results[post(2, 'x', 4)['id']]['verdict'], 'neutral')
        self.assertEqual(results[post(3, 'x', 5)['id']]['verdict'], 'fails')
        self.assertEqual(results[post(1, 'x', 3)['id']]['reason'], 'association, not cause')
        self.assertEqual(channels['x']['indicator'], 'impressions')

    def test_window_not_elapsed_and_thin_history_are_insufficient(self):
        young = post(1, 'x', 1, 500)  # X is judged at 48 hours
        results, _ = self.by_id(x_history([100] * 6) + [young])
        self.assertEqual(results[young['id']]['verdict'], 'insufficient')
        self.assertIn('window', results[young['id']]['reason'])
        results, _ = self.by_id(x_history([100] * 4) + [post(2, 'x', 3, 500)])
        self.assertEqual(results[post(2, 'x', 3)['id']]['verdict'], 'insufficient')
        self.assertIn('fewer than', results[post(2, 'x', 3)['id']]['reason'])

    def test_a_new_channel_stays_insufficient_for_fourteen_days(self):
        threads = [post(200 + i, 'threads', 13 - i, 100 if i else 900) for i in range(10)]
        results, channels = self.by_id(threads)
        self.assertTrue(channels['threads']['new'])
        self.assertEqual({r['verdict'] for r in results.values()}, {'insufficient'})
        self.assertEqual({r['reason'] for r in results.values()}, {NEW_CHANNEL})
        # Day 15 of the same channel: verdicts are given.
        later = [post(200 + i, 'threads', 15 - i, 100 if i else 900) for i in range(10)]
        results, channels = self.by_id(later)
        self.assertFalse(channels['threads']['new'])
        self.assertEqual(results[later[0]['id']]['verdict'], 'works')

    def test_a_zero_median_gives_no_verdict(self):
        results, _ = self.by_id(x_history([0] * 6) + [post(1, 'x', 3, 5)])
        self.assertEqual(results[post(1, 'x', 3)['id']]['verdict'], 'insufficient')

    def test_only_this_engines_pinned_channels_and_no_imported_posts(self):
        other = {'id': channel_id(77), 'name': 'another-venture', 'service': 'twitter',
                 'isDisconnected': False, 'isLocked': False}
        posts = [post(1, 'x', 3, 10), post(2, 'x', 3, 10, channel=other), post(3, 'x', 3, 10, via='network')]
        from engine.run.buffer_reads import sent_posts
        read = sent_posts(FakeBuffer(posts), self.now - dt.timedelta(days=56), self.now)
        self.assertEqual([p['post_id'] for p in read['posts']], [posts[0]['id']])
        self.assertEqual(read['imported'], 1)
        self.assertIn('threads', [m['channel'] for m in read['missing']])

    def test_metrics_come_from_get_post_only_when_the_list_has_none(self):
        bare = post(1, 'threads', 3, with_metrics=False)
        detail = dict(bare, metrics=[{'type': 'views', 'value': 7.0, 'unit': 'count'}])
        fake = FakeBuffer([bare, post(2, 'threads', 4, 9)], {bare['id']: detail})
        from engine.run.buffer_reads import sent_posts
        read = sent_posts(fake, self.now - dt.timedelta(days=56), self.now)
        self.assertEqual([c for c in fake.calls if c[0] == 'get_post'], [('get_post', bare['id'])])
        self.assertEqual(read['posts'][0]['metrics'], {'views': 7})
        # Percentages are never read as counts.
        self.assertNotIn('engagementRate', read['posts'][1]['metrics'])


class MeasureJobTests(unittest.TestCase):
    def workspace(self, folder, block=True, verified=True):
        (Path(folder) / 'invariants').mkdir()
        shutil.copy((FIX / 'config-verified.json') if verified else (ROOT / 'invariants' / 'ga4.json'),
                    Path(folder) / 'invariants' / 'ga4.json')
        if block:
            write_json(Path(folder) / '.scratch/cc/web-analytics.json', read_json(FIX / 'directive-block.json'))

    def posts(self):
        threads = [post(300 + i, 'threads', 20 - i, 100) for i in range(7)]
        tracked = post(1, 'threads', 3, 400, text='TEST FIXTURE ONLY. ' + LINK.format(
            src='threads', content='placement_bdc6f7e80a42d61ec2b6'))
        note = post(2, 'substack-notes', 2, 50, text='TEST FIXTURE ONLY. ' + LINK.format(
            src='notes', content='placement_0a24e3f622234d0f452c'))
        return threads + [tracked, note]

    def run_main(self, argv, folder, buffer, make_client=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = measure_auto.main(argv, make_client=make_client, buffer=buffer, root=folder, out=print)
        return code, out.getvalue()

    def test_dry_run_reads_fakes_reports_locally_and_logs_only_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            fake = FakeBuffer(self.posts())
            code, text = self.run_main(['--now', NOW, '--mode', 'synthetic'], folder, (fake, None))
            self.assertEqual(code, 0, text)
            self.assertIn('measure: works=1 neutral=7 fails=0 insufficient=1', text)
            self.assertIn('no Control Center call', text)
            # Numbers stay in the report: no metric, session or sign-up figure reaches the log.
            for private in ('400', 'impressions', 'sessions', 'placement_'):
                self.assertNotIn(private, text)
            report = validate_report(read_json(Path(folder) / '.scratch/cc/report-measure.json'))
            lines = ' | '.join(a['line'] for a in report['activity'])
            self.assertIn('Read 9 sent posts from Buffer on 2 of 8 pinned channels', lines)
            self.assertIn('GA4 joined on utm_content: 2 of 9 posts carry a tracked own link; 12 sessions on them; '
                          'sign-ups 3; paid subscriptions 1; coverage incomplete', lines)
            self.assertIn('Cost before this report:', lines)
            self.assertIn('threads: 8 posts, judged on impressions at 48 hours, channel median 100 over 8 settled posts', lines)
            self.assertEqual(report['status'], 'ready')
            self.assertEqual(report['run_id'], 'makeyourmindup:2026-11-05:measure-1300Z')
            self.assertEqual([c[0] for c in fake.calls], ['list_posts'])

    def test_without_buffer_it_still_runs_the_ga4_part(self):
        with tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            code, text = self.run_main(['--now', NOW], folder, (None, 'Buffer not configured'))
            self.assertEqual(code, 0, text)
            self.assertIn('Buffer not configured', text)
            report = read_json(Path(folder) / '.scratch/cc/report-measure.json')
            self.assertIn('Buffer not configured', [h['reason'] for h in report['holds']])
            self.assertTrue(any(a['line'].startswith('GA4 per-post rows: 3 utm_content values') for a in report['activity']))

    def test_unverified_event_names_are_not_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            self.workspace(folder, verified=False)
            self.run_main(['--now', NOW], folder, (FakeBuffer(self.posts()), None))
            lines = ' | '.join(a['line'] for a in read_json(Path(folder) / '.scratch/cc/report-measure.json')['activity'])
            self.assertIn('sign-ups not counted (refused: the sign_up event name is not verified', lines)

    def test_a_buffer_failure_is_held_by_name_and_fails_the_run(self):
        class Broken(FakeBuffer):
            def list_posts(self, status, since):
                raise RuntimeError('synthetic body that must not be printed')

        with tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            code, text = self.run_main(['--now', NOW], folder, (Broken([]), None))
            self.assertEqual(code, 1)
            report = read_json(Path(folder) / '.scratch/cc/report-measure.json')
            self.assertEqual(report['status'], 'degraded')
            self.assertIn({'reason': 'Buffer could not be read', 'detail': 'RuntimeError'}, report['holds'])
            self.assertNotIn('synthetic body', json.dumps(report) + text)

    def test_deliver_reports_by_the_existing_path_with_a_readback(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder, block=False)
            stand.directive_extra = {'web_analytics': read_json(FIX / 'directive-block.json')}
            code, text = self.run_main(['--now', NOW, '--deliver', '--mode', 'synthetic'], folder,
                                       (FakeBuffer(self.posts()), None), make_client=lambda: stand.client())
            self.assertEqual(code, 0, text)
            self.assertIn('readback digest matches', text)
            self.assertIn('attempt succeeded', text)
            self.assertNotIn(TOKEN, text)
            attempts = [c['body'] for c in stand.posts('attempts')]
            self.assertEqual({a['command'] for a in attempts}, {'measure'})
            report = stand.posts('reports')[0]['body']
            self.assertIn('sign-ups 3', ' '.join(a['line'] for a in report['activity']))
            # The directive's block is kept for the next local step too.
            self.assertTrue((Path(folder) / '.scratch/cc/web-analytics.json').is_file())

    def test_existing_measure_commands_still_route(self):
        with patch.object(measure_auto, 'main', return_value=7) as auto:
            self.assertEqual(measure.main(['measure', 'auto', '--deliver']), 7)
            auto.assert_called_once_with(['--deliver'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(measure.main(['measure', 'sources', '/nonexistent.json']), 1)


class WebAnalyticsSummaryTests(unittest.TestCase):
    def block(self):
        return read_json(FIX / 'directive-block.json')

    def test_summary_line_is_shape_only(self):
        line = cc_loop.web_analytics_line(cc_loop.web_analytics_summary(self.block()))
        self.assertEqual(line, 'web_analytics: rows source_medium=1 landing_page=0 utm_content=7; '
                               'coverage=incomplete (Per-post rows on 2 of 28 days, from 2026-11-03.); '
                               'events=page_view,synthetic_sign_up(key),synthetic_paid_subscription')
        for value in ('threads / organic', 'placement_', 'count_28d'):
            self.assertNotIn(value, line)
        activity = cc_loop.web_analytics_activity(cc_loop.web_analytics_summary(self.block()))
        self.assertTrue(activity.startswith('web_analytics for property mymu through 2026-11-04 over 28 days: rows'))

    def test_absent_and_unread_parts_are_said(self):
        self.assertEqual(cc_loop.web_analytics_line(cc_loop.web_analytics_summary(None)),
                         "web_analytics: not in today's directive")
        unread = dict(self.block(), rows=None, events=None, coverage={'complete': True, 'reason': None})
        self.assertEqual(cc_loop.web_analytics_line(cc_loop.web_analytics_summary(unread)),
                         'web_analytics: rows not read; coverage=complete; events=not read')

    def test_block_is_found_beside_or_inside_the_directive(self):
        block = self.block()
        self.assertEqual(cc_loop.web_analytics_block({'ok': True, 'web_analytics': block}), block)
        self.assertEqual(cc_loop.web_analytics_block({'ok': True, 'directive': {'web_analytics': block}}), block)
        self.assertIsNone(cc_loop.web_analytics_block({'ok': True, 'directive': {}}))

    def test_runner_keeps_the_block_and_logs_its_shape(self):
        from test_control_center import CliTests, NOW as CC_NOW
        helper = CliTests()
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            helper.workspace(folder)
            stand.directive_extra = {'web_analytics': self.block()}
            code, text = helper.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', CC_NOW], stand, folder)
            self.assertEqual(code, 0, text)
            self.assertIn('web_analytics: rows source_medium=1 landing_page=0 utm_content=7; coverage=incomplete', text)
            self.assertIn('Cost in all:', text)
            self.assertNotIn('threads / organic', text)
            self.assertEqual(read_json(Path(folder) / '.scratch/cc/web-analytics.json'), self.block())
            report = stand.posts('reports')[0]['body']
            lines = [a['line'] for a in report['activity']]
            self.assertTrue(any(line.startswith('Kept for the measure job: web_analytics for property mymu') for line in lines))
            self.assertTrue(any(line.startswith('Cost before this report:') for line in lines))

    def test_backup_runner_reports_under_its_own_run_id(self):
        from test_control_center import CliTests, NOW as CC_NOW
        helper = CliTests()
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            helper.workspace(folder)
            code, text = helper.capture(['cc', 'runner', '--deliver', '--backup', '--mode', 'synthetic', '--now', CC_NOW],
                                        stand, folder)
            self.assertEqual(code, 0, text)
            self.assertIn("web_analytics: not in today's directive", text)
            self.assertEqual(stand.posts('reports')[0]['body']['run_id'], 'makeyourmindup:2026-10-17:runner-backup')


if __name__ == '__main__':
    unittest.main()
