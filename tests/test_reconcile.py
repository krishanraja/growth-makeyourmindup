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
        self.assertTrue(reconcile.routed(post('x', 'TEST FIXTURE ONLY. ' + two_tags)), 'a route GA4 cannot credit')
        self.assertEqual(reconcile.route_of(post('x', 'TEST FIXTURE ONLY. ' + two_tags)), 'untracked')
        self.assertFalse(reconcile.routed(post('x', 'TEST FIXTURE ONLY. https://home.makeyourmindup.ai/subscribe'
                                                     '?utm_source=x&utm_medium=social')))
        self.assertFalse(reconcile.routed(post('x', 'TEST FIXTURE ONLY. https://evil.example/subscribe'
                                                     '?utm_source=x&utm_content=slot')))
        self.assertFalse(reconcile.routed(post('threads', 'TEST FIXTURE ONLY. No link.')))

    def test_a_route_in_the_first_comment_counts_and_an_article_link_does_not(self):
        from engine.run.buffer_reads import _words
        url = route.subscribe_url('instagram', 'slot-3')
        words = _words({'text': 'TEST FIXTURE ONLY.', 'metadata': {'firstComment': 'Subscribe: ' + url}})
        self.assertTrue(reconcile.routed(post('facebook', words)))
        article = ('https://home.makeyourmindup.ai/p/a-piece?utm_source=x&utm_medium=social&utm_campaign=growth'
                   '&utm_content=slot-4')
        self.assertFalse(reconcile.routed(post('x', 'TEST FIXTURE ONLY. ' + article)))

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

    def test_the_old_gates_two_tag_link_is_a_route_counted_untracked_by_ga4_never_alarmed(self):
        # Before the four-tag check merged, the gate passed utm_source and utm_content and its own hint said
        # utm_medium=organic with no utm_campaign; such a post sent on 13 November raised the alarm for 7 days
        # (adversarial review, 13 Nov 2026).
        hint = 'https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_medium=organic&utm_content=slot-old'
        read = {'listed': 2, 'posts': [post('x', 'TEST FIXTURE ONLY. ' + hint, sent='2026-11-13T10:00:00Z'),
                                       post('x', 'TEST FIXTURE ONLY. No link.', sent='2026-11-13T11:00:00Z')]}
        found = reconcile.check(read, '2026-11-15T12:00:00Z')
        self.assertEqual((found['untracked'], found['routeless']['buffer'], found['alarm']), (1, 1, 1))
        self.assertIn('untracked by GA4 1', found['line'])
        self.assertNotIn('slot-old', found['line'])

    def test_a_two_tag_link_sent_from_14_november_raises_the_alarm_as_a_missing_route(self):
        # The two-tag link is a route only before UNTRACKED_FROM (reverifier, 13 Nov 2026: one sent 25 November
        # gave no alarm, though GA4 can never credit it). Both sides of the cut-off.
        two = 'https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_content=slot-late'
        self.assertEqual(reconcile.UNTRACKED_FROM, '2026-11-14T00:00:00+00:00')
        before = {'listed': 1, 'posts': [post('x', 'TEST FIXTURE ONLY. ' + two, sent='2026-11-13T23:59:59Z')]}
        found = reconcile.check(before, '2026-11-15T12:00:00Z')
        self.assertEqual((found['untracked'], found['untracked_alarmed'], found['alarm']), (1, 0, 0))
        after = {'listed': 2, 'posts': [post('x', 'TEST FIXTURE ONLY. ' + two, sent='2026-11-14T00:00:00Z')],
                 'native': [post('youtube', 'TEST FIXTURE ONLY. ' + two.replace('=x', '=youtube'),
                                 sent='2026-11-19T12:00:00Z')]}
        found = reconcile.check(after, '2026-11-26T12:00:00Z')
        self.assertEqual(found['checked'], 1)  # the 14 November post is outside seven days of 26 November
        self.assertEqual((found['untracked'], found['untracked_alarmed'], found['alarm'], found['alarm_by']),
                         (1, 1, 1, {'buffer': 0, 'native': 1}))
        found = reconcile.check(after, '2026-11-20T12:00:00Z')
        self.assertEqual((found['untracked_alarmed'], found['alarm_by']), (2, {'buffer': 1, 'native': 1}))
        self.assertIn('untracked by GA4 2', found['line'])
        self.assertIn('2 sent from 14 November raise the alarm', found['line'])
        self.assertNotIn('slot-late', found['line'])
        # A four-tag link sent the same day is tracked and never alarmed.
        tracked = {'listed': 1, 'posts': [post('x', 'TEST FIXTURE ONLY. ' + route.subscribe_url('x', 'slot-late'),
                                               sent='2026-11-19T12:00:00Z')]}
        self.assertEqual(reconcile.check(tracked, '2026-11-20T12:00:00Z')['alarm'], 0)

    def test_the_measure_hold_says_untracked_by_ga4(self):
        from pathlib import Path
        from engine.core import instant
        from engine.run import measure_auto
        from engine.run.ga4 import load_config
        root = Path(__file__).resolve().parents[1]
        late = post('x', 'TEST FIXTURE ONLY. https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_content=s',
                    sent='2026-11-15T12:00:00Z')
        late['sent_at'] = instant(late['sent_at'])
        read = {'listed': 1, 'posts': [], 'native': [late], 'missing': [], 'held': [], 'imported': 1,
                'get_post_reads': 0}
        report, _, _ = measure_auto.build(read, None, NOW, root, 'synthetic', load_config(root), False)
        hold = next(h for h in report['holds'] if h['reason'] == 'Posts with no tracked subscribe route')
        self.assertIn('1 of them with a subscribe link GA4 cannot credit', hold['detail'])
        self.assertNotIn('utm_content=s', hold['detail'])

    def test_an_instagram_story_link_sticker_is_a_route(self):
        from engine.run.buffer_reads import _words
        url = route.subscribe_url('instagram', 'slot-story')
        words = _words({'text': 'TEST FIXTURE ONLY. A story.',
                        'metadata': {'__typename': 'InstagramPostMetadata', 'type': 'story', 'link': url}})
        self.assertEqual(reconcile.route_of(post('instagram', words)), 'tracked')

    def test_a_thread_whose_later_items_are_not_read_is_unverifiable_never_alarmed(self):
        # The sent listing selects threadCount, not the thread items, so a route in item two cannot be seen.
        from engine.run.buffer_reads import _thread_count
        listed = {'text': 'TEST FIXTURE ONLY. Part one.',
                  'metadata': {'__typename': 'TwitterPostMetadata', 'type': 'post', 'threadCount': 2}}
        self.assertEqual(_thread_count(listed), 2)
        self.assertEqual(_thread_count({'metadata': {'threadCount': True}}), 0)
        thread = dict(post('x', 'TEST FIXTURE ONLY. Part one.'), thread_count=2)
        single = post('x', 'TEST FIXTURE ONLY. No link.', pid='b' * 24)
        found = reconcile.check({'listed': 2, 'posts': [thread, single]}, NOW)
        self.assertEqual((found['unverified'], found['routeless']['buffer'], found['alarm']), (1, 1, 1))
        self.assertIn('not verifiable 1', found['line'])
        # The line and the module say plainly that a thread's later items are not read yet (reverifier, 13 Nov 2026:
        # a fully routeless thread raises no alarm, a detection gap kept on purpose until the items are read).
        self.assertIn("a thread's later items are not read yet", found['line'])
        self.assertIn("A thread's later items are not read yet.", reconcile.__doc__)
        # From 14 November a two-tag link is no route, so a thread whose first item carries only one is unverified.
        late = dict(post('x', 'TEST FIXTURE ONLY. https://home.makeyourmindup.ai/subscribe?utm_source=x'
                              '&utm_content=slot'), thread_count=1)
        found = reconcile.check({'listed': 1, 'posts': [late]}, NOW)
        self.assertEqual((found['unverified'], found['untracked'], found['alarm']), (1, 0, 0))

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
        # A checkout with no buffer_api module is a fix to the checkout, never Krish's key to add.
        from engine.run import buffer_reads
        for note, way in ((buffer_reads.NOT_INSTALLED, 'buffer_api.py is missing'),
                          (buffer_reads.NOT_CONFIGURED, 'BUFFER_API_KEY')):
            report, _, _ = measure_auto.build({'note': note}, None, NOW, root, 'synthetic', load_config(root), False)
            row = next(a['line'] for a in report['activity'] if a['line'].startswith('Outcome: blocked'))
            self.assertIn(way, row)
            detail = next(h['detail'] for h in report['holds'] if h['reason'] == note)
            self.assertIn('restore engine/run/buffer_api.py' if note == buffer_reads.NOT_INSTALLED
                          else 'set BUFFER_API_KEY', detail)
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



class RoundThreeTests(unittest.TestCase):
    """What the second reverification found (13 Nov 2026)."""

    def test_link_in_bio_on_instagram_is_a_route_whatever_else_the_words_carry(self):
        two_tags = 'https://home.makeyourmindup.ai/subscribe?utm_source=instagram&utm_content=x'
        found = reconcile.check({'listed': 1, 'posts': [post('instagram', 'TEST FIXTURE ONLY. Subscribe: link in bio. '
                                                              + two_tags, sent='2026-11-19T12:00:00Z')]}, '2026-11-20T12:00:00Z')
        self.assertEqual(found['alarm'], 0)

    def test_an_adopted_draft_is_measured_without_its_route_line(self):
        from engine.run import maker
        url = route.subscribe_url('x', 'slot-9')
        self.assertEqual(maker.without_route('Words.\nSubscribe: ' + url), 'Words.')
        self.assertEqual(maker.without_route('Words.\n' + maker.PROFILE_ROUTE), 'Words.')
        self.assertEqual(maker.without_route('Words with no route.'), 'Words with no route.')

    def test_an_edit_with_an_empty_channel_id_is_resolved_like_none(self):
        from engine import subscribe_gate
        call = {'postId': 'a' * 24, 'channelId': '', 'text': 'TEST FIXTURE ONLY. makeyourmindup, no route.'}
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', call, 5),
                         subscribe_gate.errors('mcp__Buffer__edit_post', dict(call, channelId=None), 5))


if __name__ == '__main__':
    unittest.main()


class PresendTests(unittest.TestCase):
    """Before it goes out (gmymu-1 and gmymu-2, audit of 14 Nov 2026): Buffer's scheduled posts, whoever scheduled
    them, checked with the subscribe gate's own rule. Synthetic posts only."""

    def scheduled(self, channel, text, metadata=None, due='2026-11-16T15:00:00Z', thread=0, pid='b' * 24):
        from engine.core import instant
        return {'post_id': pid, 'channel': channel, 'due_at': instant(due), 'text': text,
                'metadata': metadata or {}, 'thread_count': thread}

    def test_a_routeless_post_is_held_and_a_routed_one_passes(self):
        posts = [self.scheduled('x', 'TEST FIXTURE ONLY. No link.'),
                 self.scheduled('threads', 'TEST FIXTURE ONLY. ' + route.subscribe_url('threads', 'slot-1')),
                 self.scheduled('facebook', 'TEST FIXTURE ONLY. No link in words.',
                                {'firstComment': 'Subscribe: ' + route.subscribe_url('facebook', 'slot-2')}),
                 self.scheduled('instagram', 'TEST FIXTURE ONLY. Subscribe: link in bio.')]
        found = reconcile.presend(posts, 5)
        self.assertEqual([h['channel'] for h in found['held']], ['x'])
        self.assertEqual(found['checked'], 4)
        self.assertIn('1 with no tracked subscribe route', found['line'])
        holds = reconcile.presend_holds(found)
        self.assertEqual(len(holds), 1)
        self.assertIn('x post due Mon 16 Nov 10:00 New York (15:00 UTC)', holds[0]['detail'])
        self.assertNotIn('b' * 24, holds[0]['detail'])
        self.assertNotIn('TEST FIXTURE', holds[0]['detail'])

    def test_the_gates_rule_is_used_a_link_naming_another_channel_is_held(self):
        # The gate requires utm_source to name the channel; the sent check does not. Pre-send follows the gate.
        found = reconcile.presend([self.scheduled('x', 'TEST FIXTURE ONLY. ' + route.subscribe_url('threads', 's'))], 5)
        self.assertEqual(len(found['held']), 1)

    def test_below_the_conversion_urgency_nothing_is_held(self):
        found = reconcile.presend([self.scheduled('x', 'TEST FIXTURE ONLY. No link.')], 3)
        self.assertEqual(found['held'], [])

    def test_a_thread_whose_first_item_has_no_route_is_not_verifiable(self):
        found = reconcile.presend([self.scheduled('x', 'TEST FIXTURE ONLY. No link.', thread=2)], 5)
        self.assertEqual((found['held'], found['unverified']), ([], 1))

    def test_holds_are_capped_so_the_report_stays_valid(self):
        posts = [self.scheduled('x', 'TEST FIXTURE ONLY. No link.', pid='{:024x}'.format(i)) for i in range(30)]
        holds = reconcile.presend_holds(reconcile.presend(posts, 5))
        self.assertEqual(len(holds), reconcile.PRESEND_HOLDS_MAX + 1)
        self.assertIn('5 more', holds[-1]['detail'])

    def test_buffer_reads_lists_only_scheduled_posts_on_pinned_channels_within_two_days(self):
        from engine.buffer_channels import BUFFER_CHANNEL_ID, HANDED_OFF_CHANNELS
        from engine.run import buffer_reads
        from engine.run.release import BUFFER_NAME

        def node(n, cid, due, status='scheduled', service='twitter', name=None, channel_id=None):
            channel_id = channel_id or BUFFER_CHANNEL_ID[cid]
            return {'id': '{:024x}'.format(n), 'status': status, 'dueAt': due, 'text': 'TEST FIXTURE ONLY.',
                    'channelId': channel_id, 'metadata': {'threadCount': 0},
                    'channel': {'id': channel_id, 'name': name or BUFFER_NAME.get(cid), 'service': service,
                                'isDisconnected': False, 'isLocked': False}}
        linkedin = next(iter(HANDED_OFF_CHANNELS))

        class Fake:
            calls = []

            def list_posts(self, status, since):
                self.calls.append(status)
                return [node(1, 'x', '2026-11-16T15:00:00Z'),
                        node(2, 'x', '2026-11-20T15:00:00Z'),  # beyond two days
                        node(3, 'x', '2026-11-16T16:00:00Z', status='sent'),
                        node(4, 'x', '2026-11-16T17:00:00Z', service='linkedin', name='Krish',
                             channel_id=linkedin)]

        fake = Fake()
        got = buffer_reads.scheduled_posts(fake, '2026-11-16T12:00:00Z')
        self.assertEqual(fake.calls, ['scheduled'])
        self.assertEqual([(p['channel'], p['post_id']) for p in got], [('x', '{:024x}'.format(1))])
