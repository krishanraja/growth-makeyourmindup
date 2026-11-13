"""The source clock keeps each post's own counts, Notes' free subscriptions among them. Synthetic data only."""
import json
import unittest

from engine.run import cc_records, source_clock

NOW = '2026-11-13T19:00:00Z'


def post(pid, channel, sent_at, **metrics):
    return {'post_id': pid, 'channel': channel, 'sent_at': sent_at, 'metrics': metrics}


class SourceClockTests(unittest.TestCase):
    def test_a_note_keeps_its_free_subscriptions(self):
        value = source_clock.record([post('a' * 24, 'substack-notes', '2026-11-04T15:00:00Z', impressions=225,
                                          freeSubscriptions=1, reposts=0, likes=4)], NOW)
        self.assertEqual(value['schema'], source_clock.SCHEMA)
        self.assertEqual(value['posts'][0]['counts'], {'freeSubscriptions': 1, 'reposts': 0, 'impressions': 225})
        self.assertEqual(value['totals']['substack-notes'], {'posts': 1, 'freeSubscriptions': 1, 'reposts': 0,
                                                             'impressions': 225})
        self.assertIn('1 free subscriptions', source_clock.line(value))

    def test_a_count_a_post_does_not_show_is_absent_never_zero(self):
        value = source_clock.record([post('b' * 24, 'x', '2026-11-05T15:00:00Z', impressions=40, clicks=2)], NOW)
        self.assertNotIn('freeSubscriptions', value['totals']['x'])
        self.assertIn('no Substack Note', source_clock.line(value))

    def test_counts_only_anything_else_is_left_out(self):
        posts = [post('reader@example.com', 'x', '2026-11-05T15:00:00Z', impressions=3),
                 post('c' * 24, 'x', '2026-11-05T15:00:00Z', impressions=2.5, clicks=-1, views=True),
                 post('d' * 24, 'x', 'not a time', impressions=3),
                 {'post_id': 'e' * 24, 'channel': 'x', 'sent_at': '2026-11-05T15:00:00Z', 'metrics': None},
                 post('f' * 24, 'x', '2026-11-05T15:00:00Z', impressions=7, note='words')]
        value = source_clock.record(posts, NOW)
        self.assertEqual([p['post_id'] for p in value['posts']], ['f' * 24])
        self.assertEqual(value['posts'][0]['counts'], {'impressions': 7})
        self.assertEqual(value['left_out'], 4)
        self.assertNotIn('@', json.dumps(value))

    def test_newest_first_and_it_always_fits_one_report(self):
        posts = [post('{:024x}'.format(n), 'instagram', '2026-10-{:02d}T12:00:00Z'.format(1 + n % 28),
                      **{k: 10 ** 9 + n for k in source_clock.COUNTS}) for n in range(120)]
        value = source_clock.record(posts, NOW)
        self.assertTrue(cc_records.fits(source_clock.SCHEMA, value))
        self.assertLessEqual(len(value['posts']), source_clock.MAX_POSTS)
        self.assertEqual(len(value['posts']) + value['dropped_oldest'], 120)
        times = [p['sent_at'] for p in value['posts']]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_a_note_that_brought_a_subscriber_is_kept_past_sixty_newer_posts(self):
        # The 4 November Note and its one free subscription dropped out once about 60 posts followed it, and the line
        # said no Note was in the lookback (adversarial review, 13 Nov 2026).
        note = post('a' * 24, 'substack-notes', '2026-11-04T15:00:00Z', impressions=225, freeSubscriptions=1)
        newer = [post('{:024x}'.format(n), 'x', '2026-11-{:02d}T{:02d}:00:00Z'.format(5 + n // 12, n % 12 + 1),
                      impressions=100 + n, clicks=2) for n in range(61)]
        value = source_clock.record([note] + newer, NOW)
        ids = [p['post_id'] for p in value['posts']]
        self.assertIn('a' * 24, ids)
        self.assertEqual((len(ids), value['dropped_oldest']), (source_clock.MAX_POSTS, 2))
        self.assertEqual(value['totals']['substack-notes']['freeSubscriptions'], 1)
        times = [p['sent_at'] for p in value['posts']]
        self.assertEqual(times, sorted(times, reverse=True), 'readers still see newest first')
        self.assertIn('1 free subscriptions', source_clock.line(value))
        self.assertIn('2 older posts in the lookback not recorded', source_clock.line(value))
        bare = source_clock.record(newer, NOW)
        self.assertIn('no Substack Note with counts in the posts kept', source_clock.line(bare))
        self.assertIn('1 older posts in the lookback not recorded', source_clock.line(bare))

    def test_a_post_with_no_sent_time_is_left_out_and_a_post_listed_twice_counts_once(self):
        value = source_clock.record([post('a' * 24, 'substack-notes', None, freeSubscriptions=1)], NOW)
        self.assertEqual((value['posts'], value['left_out']), ([], 1), 'never stamped with the run time')
        twice = post('b' * 24, 'substack-notes', '2026-11-04T15:00:00Z', freeSubscriptions=1)
        value = source_clock.record([twice, dict(twice)], NOW)
        self.assertEqual((len(value['posts']), value['left_out']), (1, 0))
        self.assertEqual(value['totals']['substack-notes']['freeSubscriptions'], 1)

    def test_the_report_reads_back_whole(self):
        report = source_clock.report([post('a' * 24, 'substack-notes', '2026-11-04T15:00:00Z', freeSubscriptions=1)],
                                     NOW, 'abc1234')
        self.assertEqual(report['run_id'], 'makeyourmindup:sourceclock:2026-11-13-1900Z')
        self.assertEqual(cc_records.record_of(report, source_clock.SCHEMA)['posts'][0]['counts'],
                         {'freeSubscriptions': 1})
        self.assertIsNone(source_clock.report([], NOW, 'abc1234'))


if __name__ == '__main__':
    unittest.main()
