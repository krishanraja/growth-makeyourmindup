"""Reconciliation and outcome rows. Synthetic data only."""
import unittest

from engine import route
from engine.run import outcome, reconcile

NOW = '2026-11-16T12:00:00Z'


def post(channel, words, sent='2026-11-15T12:00:00Z', pid='a' * 24):
    return {'post_id': pid, 'channel': channel, 'sent_at': sent, 'words': words}


class ReconcileTests(unittest.TestCase):
    def test_a_tracked_route_or_the_profile_link_passes(self):
        self.assertTrue(reconcile.routed(post('x', 'TEST FIXTURE ONLY. ' + route.subscribe_url('x', 'slot-1'))))
        self.assertTrue(reconcile.routed(post('instagram', 'TEST FIXTURE ONLY. Subscribe: link in bio.')))
        self.assertFalse(reconcile.routed(post('x', 'TEST FIXTURE ONLY. Subscribe: link in bio.')))
        two_tags = 'https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_content=slot'
        self.assertFalse(reconcile.routed(post('x', 'TEST FIXTURE ONLY. ' + two_tags)))
        self.assertFalse(reconcile.routed(post('threads', 'TEST FIXTURE ONLY. No link.')))

    def test_buffer_made_and_native_posts_are_both_counted(self):
        read = {'listed': 4,
                'posts': [post('x', 'TEST FIXTURE ONLY. No link.'),
                          post('x', 'TEST FIXTURE ONLY. ' + route.subscribe_url('x', 'slot-2'))],
                'native': [post('youtube', 'TEST FIXTURE ONLY. Native upload, no link.'),
                           post('threads', 'TEST FIXTURE ONLY. Old.', sent='2026-11-01T12:00:00Z')]}
        found = reconcile.check(read, NOW)
        self.assertEqual(found['checked'], 3)  # the 1 Nov post is outside seven days
        self.assertEqual(found['routeless'], {'buffer': 1, 'native': 1})
        self.assertEqual(found['alarm'], 2)
        self.assertIn('approval not reconciled yet', found['line'])
        self.assertNotIn('TEST FIXTURE', found['line'])

    def test_posts_before_the_check_landed_are_counted_never_alarmed(self):
        read = {'listed': 1, 'posts': [post('x', 'TEST FIXTURE ONLY. No link.', sent='2026-11-12T12:00:00Z')]}
        found = reconcile.check(read, '2026-11-14T12:00:00Z')
        self.assertEqual((found['routeless']['buffer'], found['alarm']), (1, 0))


class OutcomeTests(unittest.TestCase):
    def test_each_kind_and_its_line(self):
        self.assertEqual(outcome.line(outcome.row('advanced', '3 posts measured')), 'Outcome: advanced (3 posts measured)')
        blocked = outcome.row('blocked', 'buffer_read_failed', 'lookup filed: read again next run')
        self.assertIn('way out: lookup filed', outcome.line(blocked))
        self.assertTrue(outcome.failed(blocked))
        self.assertTrue(outcome.failed(None))
        self.assertFalse(outcome.failed(outcome.row('nothing_to_do', 'no posts')))

    def test_a_blocked_run_must_name_its_way_out(self):
        with self.assertRaises(ValueError):
            outcome.row('blocked', 'buffer_read_failed')
        with self.assertRaises(ValueError):
            outcome.row('stuck', 'anything')
        with self.assertRaises(ValueError):
            outcome.row('advanced', '  ')


if __name__ == '__main__':
    unittest.main()


class MeasureReportTests(unittest.TestCase):
    def test_the_measure_report_carries_the_outcome_and_alarms_a_routeless_post(self):
        from pathlib import Path
        from engine.core import instant
        from engine.run import measure_auto
        from engine.run.ga4 import load_config
        root = Path(__file__).resolve().parents[1]
        native = post('youtube', 'TEST FIXTURE ONLY. Native upload, no link.')
        native['sent_at'] = instant(native['sent_at'])
        read = {'listed': 1, 'posts': [], 'native': [native], 'missing': [], 'held': [], 'imported': 1,
                'get_post_reads': 0}
        report, error, _ = measure_auto.build(read, None, NOW, root, 'synthetic', load_config(root), False)
        lines = [a['line'] for a in report['activity']]
        self.assertIsNone(error)
        self.assertTrue(any(l.startswith('Outcome: nothing_to_do') for l in lines), lines)
        self.assertTrue(any(l.startswith('Reconciliation over the last 7 days: 1 sent posts') for l in lines))
        self.assertIn('Posts with no tracked subscribe route', [h['reason'] for h in report['holds']])
        broken = dict(read, error='RuntimeError')
        report, error, _ = measure_auto.build(broken, None, NOW, root, 'synthetic', load_config(root), False)
        self.assertEqual(error, 'buffer_read_failed')
        self.assertTrue(any('Outcome: blocked' in a['line'] and 'way out' in a['line'] for a in report['activity']))


class ReleaseOutcomeTests(unittest.TestCase):
    def test_every_release_run_ends_with_one_row(self):
        from engine.run.autorelease import release_outcome
        base = {'error': None, 'mutations': 0, 'holds': {}, 'decisions_read': 2}
        self.assertEqual(release_outcome(base)['outcome'], 'nothing_to_do')
        self.assertEqual(release_outcome(dict(base, mutations=2))['outcome'], 'advanced')
        held = release_outcome(dict(base, holds={'subscribe_route_missing': 2, 'not_signed': 1}))
        self.assertEqual((held['outcome'], held['what']), ('held_below_bar', 'subscribe_route_missing 2, not_signed 1'))
        blocked = release_outcome(dict(base, error='decisions_unpaged'))
        self.assertEqual(blocked['outcome'], 'blocked')
        self.assertTrue(blocked['way_out'])
