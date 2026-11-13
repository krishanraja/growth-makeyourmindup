"""One subscribe route, checked one way: the gate, GA4 and the go-live path agree. Synthetic data only."""
import unittest
from unittest.mock import patch

from engine import intensity, route, subscribe_gate
from engine.buffer_channels import BUFFER_CHANNEL_ID, DENIED_CHANNELS
from engine.run import ga4

PAGE = 'https://home.makeyourmindup.ai/subscribe'


def line(channel, words, first_comment=None, publish_mode='engine'):
    meta = {'metadata': {}}
    if first_comment is not None:
        meta['metadata'][subscribe_gate.SERVICE.get(channel, channel)] = {'firstComment': first_comment}
    return {'slot_id': 'test-slot', 'channel': channel, 'buffer_channel_id': BUFFER_CHANNEL_ID[channel],
            'words': words, 'meta': meta, 'publish_mode': publish_mode}


class RouteTests(unittest.TestCase):
    def test_the_route_carries_all_four_tags_and_passes_the_gate(self):
        url = route.subscribe_url('threads', 'w46-threads-0830')
        self.assertTrue(url.startswith(PAGE + '?'))
        for tag in route.UTMS:
            self.assertIn(tag + '=', url)
        self.assertIn('utm_medium=social', url)
        self.assertEqual(intensity.subscribe_errors({'url': url, 'placement': 'in_post'}, 'threads', 'Read it ' + url,
                                                    None, 5), [])

    def test_a_gate_passing_url_is_tracked_by_ga4(self):
        for channel in ('substack-notes', 'threads', 'x', 'facebook'):
            url = route.subscribe_url(channel, 'slot-' + channel)
            found = ga4.own_links('Subscribe: ' + url)
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0]['tracked'], url)
            self.assertEqual(found[0]['utm_content'], 'slot-' + channel)

    def test_a_link_ga4_cannot_credit_passes_no_gate(self):
        two_tags = PAGE + '?utm_source=threads&utm_content=slot'
        problems = intensity.subscribe_errors({'url': two_tags, 'placement': 'in_post'}, 'threads', two_tags, None, 5)
        self.assertTrue(problems and 'source tags' in problems[0])
        self.assertFalse(ga4.own_links(two_tags)[0]['tracked'])

    def test_unique_content_and_only_this_engines_channels(self):
        self.assertNotEqual(route.subscribe_url('x', 'a'), route.subscribe_url('x', 'b'))
        for bad in ('', 'Has Space', 'x' * 65, 'a/b'):
            with self.assertRaises(ValueError):
                route.subscribe_url('x', bad)
        with self.assertRaises(ValueError):
            route.subscribe_url('heartside-instagram', 'slot')
        for other in DENIED_CHANNELS.values() if isinstance(DENIED_CHANNELS, dict) else DENIED_CHANNELS:
            self.assertNotIn(other, subscribe_gate.CHANNEL_BY_ID)

    def test_a_go_live_line_without_a_route_holds_at_u4_and_u5(self):
        for urgency in (4, 5):
            self.assertTrue(route.line_errors(line('threads', 'TEST FIXTURE ONLY. No route.'), urgency))
        self.assertEqual(route.line_errors(line('threads', 'TEST FIXTURE ONLY. No route.'), 3), [])

    def test_a_routed_line_passes_in_its_words_or_first_comment(self):
        url = route.subscribe_url('threads', 'slot-1')
        self.assertEqual(route.line_errors(line('threads', 'TEST FIXTURE ONLY. ' + url), 5), [])
        self.assertEqual(route.line_errors(line('threads', 'TEST FIXTURE ONLY.', first_comment=url), 5), [])
        self.assertEqual(route.line_errors(line('instagram', 'TEST FIXTURE ONLY. Subscribe: link in bio.'), 5), [])

    def test_another_ventures_channel_is_never_this_engines(self):
        other = dict(line('threads', 'TEST FIXTURE ONLY.'), buffer_channel_id='f' * 24)
        self.assertEqual(route.line_errors(other, 5), [])
        self.assertTrue(route.line_errors('not a line', 5))


class GoLivePathTests(unittest.TestCase):
    """The engine's own release path holds a line with no route, as the Buffer hook holds a hand-made call."""

    def test_autorelease_slot_holds_a_routeless_line(self):
        from engine.run import autorelease
        run = autorelease.Run(buffer=None, now='2026-11-16T12:00:00Z', deliver=False, fetch=None)
        run.urgency = 5
        signed = line('threads', 'TEST FIXTURE ONLY. No route.')
        signed.update(format='text', due_at='2026-11-16T13:00:00Z', link_placement='in_post',
                      buffer_draft_id='a' * 24, assets=[], payload_sha256='0' * 64)
        with patch.object(autorelease, 'may_release', return_value=True), \
                patch.object(autorelease, 'route_holds', return_value=(False, None, None)), \
                patch.object(autorelease, 'share_ask_errors', return_value=[]):
            self.assertEqual(run.slot(signed, dict(signed), {'decision': 'approved', 'stage': 'go_live'}), 'held')
        self.assertEqual(run.holds, {'subscribe_route_missing': 1})
        self.assertIn('subscribe_route_missing', run.loud)


if __name__ == '__main__':
    unittest.main()
