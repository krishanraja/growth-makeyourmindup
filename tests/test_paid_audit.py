"""growth.py run paid audit: paid reach is told apart from genuine interest, read only (engine/run/paid_audit.py).

Every post, number and reading here is synthetic. Checked: the four results of the audit contract borrowed from
Claude Ads (docs/reviews/2026-11-15-hyperframes-and-claude-ads.md), that a missing number is never zero, that a boost
reading holds its post out of the organic baseline, that subscribers from a boosted platform's boost week are not
taken as organic without a question, and that no recommendation can change an account.
"""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.run import cli
from engine.run import paid_audit as pa

NOW = '2026-11-15T21:00:00Z'
ROOT = Path(__file__).resolve().parents[1]


def post(channel, day, exposure, reactions=None, via='buffer', comments=None, shares=None, pid=None, text='A post'):
    """One Buffer list_posts Post with metrics, as includeMetrics returns them."""
    indicator = {'facebook': 'impressions', 'x': 'impressions', 'substack-notes': 'impressions'}.get(channel, 'views')
    metrics = []
    if exposure is not None:
        metrics.append({'type': indicator, 'value': exposure, 'unit': 'count'})
    for name, value in (('reactions', reactions), ('comments', comments), ('shares', shares)):
        if value is not None:
            metrics.append({'type': name, 'value': value, 'unit': 'count'})
    metrics.append({'type': 'engagementRate', 'value': 1.5, 'unit': 'percentage'})
    return {'id': pid or '{}-{}-{}'.format(channel, day, exposure), 'status': 'sent', 'via': via, 'text': text,
            'sentAt': '2026-11-{:02d}T15:00:00.000Z'.format(day), 'channelId': BUFFER_CHANNEL_ID[channel],
            'channelService': channel, 'metrics': metrics}


def ordinary(channel, exposure, reactions, days=range(1, 8)):
    return [post(channel, d, exposure + d, reactions) for d in days]


def boost(platform='tiktok', start='2026-11-11', end='2026-11-12', spend=2500, rid='msr-boost-1'):
    return {'id': rid, 'engine': 'measurement', 'kind': 'observation', 'state': 'recorded',
            'detail': {'metric': 'views', 'unit': 'views', 'data_source': 'TikTok Promote, read by Codex',
                       'read_at': '2026-11-15', 'value': 15000, 'window_start': start, 'window_end': end,
                       'paid_boost': {'platform': platform, 'window_start': start, 'window_end': end,
                                      'spend_cents': spend}}}


def capture(posts):
    return {'read_at': '2026-11-15T20:00:00Z', 'posts': posts}


def run(posts, records=(), **kw):
    return pa.audit(capture(posts), list(records), now=NOW, since='2026-10-01T00:00:00Z', **kw)


def row(report, pid):
    return next(r for r in report['posts'] if r['post_id'] == pid)


def result(report, check_id):
    return next(c for c in report['checks'] if c['id'] == check_id)['result']


class TellsPaidFromInterest(unittest.TestCase):

    def test_reach_without_interest_is_suspected_paid_and_asks_for_a_read(self):
        spike = post('tiktok', 11, 18000, 12, via='network', pid='spike')
        report = run(ordinary('tiktok', 280, 2) + [spike])
        self.assertEqual(row(report, 'spike')['class'], 'suspected_paid')
        self.assertIn('reach without interest', row(report, 'spike')['why'])
        self.assertEqual(result(report, 'boosts_recorded'), 'fail')
        self.assertEqual(result(report, 'zero_paid_line'), 'unknown')
        read = [r for r in report['recommendations'] if r['kind'] == 'read_boost']
        self.assertEqual(len(read), 1)
        self.assertIn('TikTok Promote', read[0]['what'])
        self.assertIn('read only', read[0]['owner'])

    def test_reach_a_page_never_reaches_organically_is_suspected_whatever_its_rate(self):
        spike = post('facebook', 13, 16000, 90, pid='page-spike')
        report = run(ordinary('facebook', 3, 0) + [spike])
        self.assertEqual(row(report, 'page-spike')['class'], 'suspected_paid')
        self.assertIn('not reached organically', row(report, 'page-spike')['why'])

    def test_a_spike_people_stayed_with_is_a_breakout_to_make_more_of(self):
        hit = post('instagram', 10, 900, 60, shares=6, pid='hit', text='Claude Duet messages you first')
        report = run(ordinary('instagram', 60, 2) + [hit])
        self.assertEqual(row(report, 'hit')['class'], 'organic_breakout')
        more = [r for r in report['recommendations'] if r['kind'] == 'make_more_like']
        self.assertEqual(len(more), 1)
        self.assertIn('Claude Duet messages you first', more[0]['what'])
        self.assertEqual(result(report, 'zero_paid_line'), 'pass')

    def test_one_reaction_is_never_a_breakout(self):
        lone = post('facebook', 10, 200, 1, pid='lone-like')
        report = run(ordinary('facebook', 3, 0) + [lone])
        self.assertEqual(row(report, 'lone-like')['class'], 'reach_outlier')
        self.assertFalse([r for r in report['recommendations'] if r['kind'] == 'make_more_like'])

    def test_a_small_spike_is_never_called_bought(self):
        small = post('youtube', 10, 500, 0, pid='small')
        report = run(ordinary('youtube', 10, 0) + [small])
        self.assertEqual(row(report, 'small')['class'], 'reach_outlier')
        self.assertIn('too small to call bought', row(report, 'small')['why'])
        self.assertEqual(report['suspected_paid'], [])

    def test_no_ads_platform_can_boost_a_note(self):
        note = post('substack-notes', 10, 5000, 0, pid='note')
        report = run(ordinary('substack-notes', 4, 1) + [note])
        self.assertEqual(row(report, 'note')['class'], 'reach_outlier')
        self.assertIn('no ads platform', row(report, 'note')['why'])

    def test_a_young_post_far_past_its_channel_is_judged_at_once(self):
        # Reach only grows, so a spike is evidence before the judge window ends; an ordinary young post waits.
        young = post('tiktok', 15, 20000, 5, pid='young')
        calm = post('tiktok', 15, 290, 2, pid='calm')
        report = run(ordinary('tiktok', 280, 2) + [young, calm])
        self.assertEqual(row(report, 'young')['class'], 'suspected_paid')
        self.assertEqual(row(report, 'calm')['class'], 'too_early')

    def test_too_few_posts_is_insufficient_never_a_verdict(self):
        report = run(ordinary('x', 16, 1, days=range(1, 4)) + [post('x', 10, 9000, 0, pid='lone')])
        self.assertEqual(row(report, 'lone')['class'], 'insufficient')


class BoostReadings(unittest.TestCase):

    def test_a_recorded_boost_holds_its_post_out_of_the_organic_baseline(self):
        spike = post('tiktok', 11, 18000, 12, via='network', pid='spike')
        report = run(ordinary('tiktok', 280, 2) + [spike], [boost()])
        self.assertEqual(row(report, 'spike')['class'], 'paid_window')
        self.assertEqual(row(report, 'spike')['boosts'], ['msr-boost-1'])
        self.assertEqual(result(report, 'boosts_recorded'), 'pass')
        self.assertEqual(result(report, 'spend_known'), 'pass')
        self.assertEqual(result(report, 'zero_paid_line'), 'fail')
        tiktok = next(b for b in report['baselines'] if b['channel'] == 'tiktok')
        self.assertEqual(tiktok['held_out'], 1)
        self.assertLess(tiktok['median_organic'], 300)
        self.assertTrue(any(r['kind'] == 'no_new_boosts' for r in report['recommendations']))

    def test_a_boost_with_no_spend_shown_leaves_spend_unknown_never_zero(self):
        report = run(ordinary('tiktok', 280, 2), [boost(spend=None)])
        self.assertEqual(result(report, 'spend_known'), 'unknown')

    def test_a_boost_reading_measurement_refuses_is_never_used(self):
        bad = boost(platform='instagram_app')
        report = run(ordinary('tiktok', 280, 2) + [post('tiktok', 11, 18000, 12, pid='spike')], [bad])
        self.assertEqual(report['boosts'], [])
        self.assertEqual(report['refused_boost_records'][0]['id'], 'msr-boost-1')
        self.assertEqual(row(report, 'spike')['class'], 'suspected_paid')

    def test_a_meta_boost_covers_facebook_instagram_and_threads_but_not_tiktok(self):
        posts = [post('instagram', 12, 70, 2, pid='ig'), post('tiktok', 12, 290, 2, pid='tt')]
        report = run(ordinary('tiktok', 280, 2) + ordinary('instagram', 60, 2) + posts,
                     [boost(platform='meta', start='2026-11-13', end='2026-11-14')])
        self.assertEqual(row(report, 'ig')['class'], 'paid_window')  # sent within LEAD_DAYS before the window
        self.assertNotEqual(row(report, 'tt')['class'], 'paid_window')


class NorthStarExposure(unittest.TestCase):

    def substack(self, rows, start='2026-11-09', end='2026-11-15'):
        return {'kind': 'substack_growth_sources', 'captured_at': '2026-11-15T15:00:00-05:00',
                'source_url': 'https://example.substack.com/publish/stats/growth-sources',
                'window': {'label': 'Custom', 'start': start, 'end': end, 'tz': 'America/New_York'},
                'settled': {'label_seen': 'Custom', 'values_seen_after_label': True}, 'metric': 'new_subscribers',
                'rows': rows, 'total_new_free': sum(r['new_free'] for r in rows)}

    def rows(self):
        return [{'source': 'Facebook', 'new_free': 3, 'new_paid': 0},
                {'source': 'Substack Notes', 'new_free': 2, 'new_paid': 0}]

    def test_subscribers_from_a_boosted_platform_in_its_window_are_not_provably_organic(self):
        report = run(ordinary('facebook', 3, 0), [boost(platform='meta', start='2026-11-13', end='2026-11-14')],
                     substack=self.substack(self.rows()))
        self.assertEqual(result(report, 'north_star_exposure'), 'fail')
        self.assertEqual(report['north_star_exposed'], [{'source': 'Facebook', 'new_free': 3, 'boost': 'msr-boost-1'}])
        hold = [r for r in report['recommendations'] if r['kind'] == 'hold_out']
        self.assertEqual(len(hold), 1)
        self.assertEqual(hold[0]['owner'], 'Krish')

    def test_no_capture_is_unknown_and_a_boost_outside_the_window_passes(self):
        records = [boost(platform='meta', start='2026-10-01', end='2026-10-02')]
        self.assertEqual(result(run(ordinary('facebook', 3, 0), records), 'north_star_exposure'), 'unknown')
        report = run(ordinary('facebook', 3, 0), records, substack=self.substack(self.rows()))
        self.assertEqual(result(report, 'north_star_exposure'), 'pass')

    def test_no_boost_at_all_is_not_applicable(self):
        report = run(ordinary('facebook', 3, 0), substack=self.substack(self.rows()))
        self.assertEqual(result(report, 'north_star_exposure'), 'not_applicable')


class ReadsHonestly(unittest.TestCase):

    def test_a_missing_number_is_not_shown_never_zero(self):
        bare = post('tiktok', 10, None, pid='bare')
        bare['metrics'] = None
        report = run(ordinary('tiktok', 280, 2) + [bare])
        self.assertEqual(row(report, 'bare')['class'], 'not_shown')
        self.assertIsNone(row(report, 'bare')['exposure'])
        self.assertIsNone(row(report, 'bare')['interactions'])
        self.assertEqual(pa.interactions({'views': 10}), (None, []))

    def test_native_posts_are_read_and_other_ventures_channels_are_not(self):
        native = post('tiktok', 10, 300, 2, via='network', pid='native')
        stranger = dict(post('tiktok', 10, 300, 2, pid='stranger'), channelId='0' * 24)
        report = run(ordinary('tiktok', 280, 2) + [native, stranger])
        self.assertEqual(row(report, 'native')['via'], 'network')
        self.assertNotIn('stranger', [r['post_id'] for r in report['posts']])
        self.assertEqual(report['source']['skipped'], {'a channel this engine does not read': 1})

    def test_likes_count_only_where_no_reactions_are_shown(self):
        self.assertEqual(pa.interactions({'reactions': 4, 'likes': 4, 'comments': 1}), (5, ['reactions', 'comments']))
        self.assertEqual(pa.interactions({'likes': 4}), (4, ['likes']))


class ChangesNoAccount(unittest.TestCase):

    def test_every_recommendation_is_a_draft_outside_the_north_star(self):
        posts = ordinary('tiktok', 280, 2) + [post('tiktok', 11, 18000, 12, pid='spike'),
                                              post('tiktok', 12, 3000, 400, pid='hit')]
        report = run(posts)
        self.assertTrue(report['recommendations'])
        for rec in report['recommendations']:
            self.assertIn(rec['kind'], pa.ACTIONS)
            self.assertEqual(rec['mutation'], 'none')
            self.assertIs(rec['counts_toward_north_star'], False)
            self.assertIn("Krish's Yes", rec['approval'])

    def test_no_recommendation_can_launch_buy_pause_or_change_a_budget(self):
        for kind in ('launch', 'boost', 'pause', 'budget', 'increase_spend', 'edit_campaign'):
            with self.assertRaises(ValueError):
                pa.recommend(kind, 'x', 'y', [], 'z')
        self.assertNotIn('--deliver', (ROOT / 'engine' / 'run' / 'paid_audit.py').read_text(encoding='utf-8')
                         .split('def main', 1)[1])

    def test_the_module_opens_no_network_connection(self):
        source = (ROOT / 'engine' / 'run' / 'paid_audit.py').read_text(encoding='utf-8')
        for name in ('urllib', 'http.client', 'socket', 'requests', 'buffer_api', 'control_center'):
            self.assertNotIn('import ' + name, source)
            self.assertNotIn('from ' + name, source)

    def test_a_check_ends_in_one_of_four_results(self):
        with self.assertRaises(ValueError):
            pa.check('x', 'probably', 'why')


class Command(unittest.TestCase):

    def test_the_route_is_registered(self):
        self.assertEqual(cli.ROUTES['paid'], 'paid_audit')

    def test_the_command_writes_its_report_locally(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'posts.json').write_text(json.dumps(capture(ordinary('tiktok', 280, 2)
                                                               + [post('tiktok', 11, 18000, 12, pid='spike')])))
            (tmp / 'records.jsonl').write_text(json.dumps(boost()) + '\n')
            out = tmp / 'out' / 'audit.json'
            code = pa.main(['paid', 'audit', '--posts', str(tmp / 'posts.json'), '--records', str(tmp / 'records.jsonl'),
                            '--now', NOW, '--since', '2026-10-01T00:00:00Z', '--out', str(out)])
            self.assertEqual(code, 0)
            report = json.loads(out.read_text())
            self.assertEqual(report['paid_window'], ['spike'])
            self.assertEqual(pa.main(['paid']), 2)

    def test_the_repository_records_are_read_without_error(self):
        records = pa.read_records(ROOT / pa.RECORDS)
        boosts, refused = pa.boost_readings(records)
        self.assertEqual(refused, [])
        self.assertTrue(all(isinstance(b['window_start'], dt.date) for b in boosts))


if __name__ == '__main__':
    unittest.main()
