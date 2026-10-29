"""The day's engagement taps as one copy and open ask (protocol 1.14.0). Synthetic fixtures only."""
import json
from pathlib import Path
import unittest

from engine.cc_loop import Loop, workspace_report
from engine.control_center import (ENGAGE_VERSION, ProtocolError, action_errors, copy_open, engage_action, proposal,
                                   validate_report)

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-29T15:00:00Z'
GAP = {'week_of': '2026-10-26', 'week_target': 25, 'current': 0, 'as_of': '2026-10-27', 'urgency': 4,
       'reason': 'under two fifths'}
CALM = dict(GAP, current=30, urgency=1, reason="at or above this week's target")


def radar(n, url='https://www.linkedin.com/feed/update/urn:li:activity:{}/'):
    items, meta = [], []
    for i in range(n):
        items.append({'platform': 'linkedin', 'text': 'TEST FIXTURE ONLY. A useful reply number ' + str(i) + '.',
                      'target_url': url.format(i), 'target_name': 'Synthetic author ' + str(i)})
        meta.append({'item_id': 'radar-' + str(i), 'placement': 'comment', 'minutes': 1, 'priority': 1,
                     'evidence_ids': ['ev'], 'expires_at': '2026-10-30T0' + str(i % 10) + ':00:00Z',
                     'why_now': 'Fixture only.', 'success_check': 'Fixture.'})
    envelope = {'pack': {'kind': 'radar', 'items': items}, 'metadata': meta,
                'evidence': [{'evidence_id': 'ev', 'kind': 'source_thread', 'url': 'https://www.linkedin.com/feed/'}]}
    queue = {'items': [{'item_id': m['item_id']} for m in meta], 'deferred': [], 'budget_minutes': 20}
    return envelope, queue


def report(n, gap=GAP, **kw):
    envelope, queue = radar(n, **kw)
    return workspace_report('radar', 'makeyourmindup:2026-10-29:radar', NOW, [envelope], queue, rev='fixture',
                            root=ROOT, gap=gap)[0]


class EngagementTask(unittest.TestCase):
    def test_taps_go_as_one_copy_open_ask(self):
        result = report(4)
        self.assertEqual(len(result['proposals']), 1, 'one ask, however many taps')
        task = result['proposals'][0]
        action = copy_open(task)
        self.assertEqual((task['wall'], task['kind'], task['channel']), ('post', 'prepared', 'engage'))
        self.assertNotIn('stage', task)
        self.assertEqual(result['schema_version'], ENGAGE_VERSION)
        self.assertEqual(set(action), {'version', 'channel', 'kind', 'body', 'taps'})
        self.assertEqual((action['version'], action['kind']), (2, 'copy_open'))
        self.assertEqual(len(action['taps']), 4)
        self.assertEqual(set(action['taps'][0]), {'label', 'text', 'url'})
        self.assertTrue(action['taps'][0]['url'].startswith('https://www.linkedin.com/'))
        self.assertEqual(task['expires_at'], '2026-10-30T00:00:00Z', 'the ask expires with its first tap')
        self.assertEqual(task['close_condition']['event'], 'tapped')

    def test_as_many_as_clear_the_bar_up_to_the_urgency_cap(self):
        self.assertEqual(len(copy_open(report(18)['proposals'][0])['taps']), 15, 'U4 takes 15')
        calm = report(18, CALM)
        self.assertEqual(len(copy_open(calm['proposals'][0])['taps']), 5, 'U1 keeps five')
        over = [h for h in calm['holds'] if h['reason'].startswith("Over today's engagement cap")]
        self.assertEqual(len(over), 13, 'every tap past the cap is held by name, never dropped')

    def test_a_tap_without_a_public_page_or_with_contact_details_is_held(self):
        result = report(2, url='http://example.invalid/{}')
        self.assertEqual(result['proposals'], [])
        self.assertTrue(all(h['reason'] == 'Engagement draft cannot be a tap' for h in result['holds']))
        with self.assertRaises(ValueError):
            engage_action('body', [{'label': 'x', 'text': 'Write to me at someone@example.org', 'url': 'https://a.b/'}])
        with self.assertRaises(ValueError):
            engage_action('body', [{'label': 'x', 'text': 'Call 415 555 0100', 'url': 'https://a.b/'}])
        with self.assertRaises(ValueError):
            engage_action('body', [])

    def test_taps_follow_control_centers_own_rule(self):
        def errors(text='Fixture.', url='https://a.b/c'):
            return action_errors({'body': 'x', 'taps': [{'label': 'x', 'text': text, 'url': url}]})
        # src/lib/growthEngines.ts: any run of ten digits however spaced, and a page of 2000 characters at most.
        self.assertTrue(errors('Seen in 2024 2025 2026 and since.'))
        self.assertTrue(errors('Ring 4155550100.'))
        self.assertTrue(errors('Write to SOMEONE@EXAMPLE.ORG'))
        self.assertEqual(errors('Up 40 percent since 2024.'), [], 'a year or a figure is not a number to ring')
        self.assertTrue(errors(url='https://a.b/' + 'c' * 2000))
        self.assertTrue(errors(url='https://wa.me/14155550100'), 'a private chat is not a public page')
        self.assertTrue(errors(url='https://a.b/share?to=someone'), 'a contact key is refused')
        self.assertTrue(errors(url='https://a.b/p/someone%40example.org'), 'an encoded address is refused')
        self.assertEqual(errors(url='https://x.com/someone/status/1849000000000000000'), [], 'a post id is not a number')
        self.assertEqual(errors(url='https://www.linkedin.com/feed/update/urn:li:activity:7254000000000000000/'), [])

    def test_one_bad_tap_is_held_alone(self):
        envelope, queue = radar(3)
        envelope['pack']['items'][1]['text'] = 'TEST FIXTURE ONLY. We ran it in 2024 2025 2026.'
        result = workspace_report('radar', 'makeyourmindup:2026-10-29:radar', NOW, [envelope], queue, rev='fixture',
                                  root=ROOT, gap=GAP)[0]
        self.assertEqual(len(copy_open(result['proposals'][0])['taps']), 2, 'the other taps still go')
        held = [h for h in result['holds'] if h['reason'] == 'Engagement draft cannot be a tap']
        self.assertEqual([h['detail'].split(':')[0] for h in held], ['radar-1'])

    def test_report_refuses_a_task_off_the_post_wall(self):
        payload = json.dumps(engage_action('body', [{'label': 'x', 'text': 'Fixture.', 'url': 'https://a.b/c'}]))
        bad = proposal('makeyourmindup:engage:x', 'Fixture', 'Fixture', 'advice', 'strategy', 'tapped',
                       channel='engage', exact_payload=payload)
        good = report(1)
        good['proposals'] = [bad]
        from engine.control_center import report_digest
        good['payload_sha256'] = report_digest(good)
        with self.assertRaisesRegex(ValueError, 'sits behind post'):
            validate_report(good)

    def test_plain_fallback_carries_the_same_taps_at_the_old_version(self):
        envelope, queue = radar(3)
        plain = workspace_report('radar', 'r1', NOW, [envelope], queue, rev='fixture', root=ROOT, gap=GAP,
                                 plain_taps=True)[0]
        task = plain['proposals'][0]
        self.assertIsNone(copy_open(task))
        self.assertEqual(plain['schema_version'], '1.0.0')
        self.assertEqual((task['kind'], task['wall'], task['proposal_id']),
                         ('advice', 'post', report(3)['proposals'][0]['proposal_id']))
        self.assertEqual(task['exact_payload'].count('\nOpen: https://'), 3)

    def test_loop_degrades_once_when_control_center_cannot_take_the_task(self):
        class Client:
            def __init__(self, refuse):
                self.refuse, self.posted = refuse, []

            def attempt(self, record):
                return {'ok': True}

            def directive(self):
                return {'ok': True, 'directive': {}}

            def post_report(self, value):
                self.posted.append(value)
                if copy_open(value['proposals'][0]) and self.refuse:
                    raise ProtocolError(self.refuse)
                return {'conflict': False, 'replayed': False, 'readback_matches': True}

            def decisions(self, since):
                return []
        envelope, queue = radar(2)

        def build(directive, plain_taps=False):
            return workspace_report('radar', 'r1', NOW, [envelope], queue, rev='fixture', root=ROOT, gap=GAP,
                                    plain_taps=plain_taps)
        for code in ('schema_version_unsupported', 'copy_open_unsupported', 'bad_request'):
            client = Client(code)
            loop = Loop(client, 'radar', 'r1', lambda: NOW)
            loop.start()
            outcome = loop.finish(build, NOW, degrade=lambda d: build(d, True))
            self.assertEqual((outcome['status'], outcome['degraded'], len(client.posted)), ('succeeded', code, 2))
            self.assertIsNone(copy_open(outcome['report']['proposals'][0]))
        client = Client('rate_limited')
        loop = Loop(client, 'radar', 'r1', lambda: NOW)
        loop.start()
        outcome = loop.finish(build, NOW, degrade=lambda d: build(d, True))
        self.assertEqual((outcome['status'], len(client.posted)), ('failed', 1), 'other failures are never resent')
        accepted = Client(None)
        loop = Loop(accepted, 'radar', 'r1', lambda: NOW)
        loop.start()
        self.assertNotIn('degraded', loop.finish(build, NOW, degrade=lambda d: build(d, True)))

    def test_client_sends_the_task_only_where_copy_open_is_served(self):
        from engine.control_center import Client
        client = Client('gen1_' + 'x' * 43, 'http://127.0.0.1:9', loopback_for_tests=True)
        client.capabilities = lambda: {'schema_versions': ['1.0.0', ENGAGE_VERSION], 'features': {'copy_open': False}}
        with self.assertRaisesRegex(ProtocolError, 'copy_open_unsupported'):
            client.confirm_version(ENGAGE_VERSION, 'copy_open')
        client.capabilities = lambda: {'schema_versions': ['1.0.0', '1.13.0'], 'features': {'copy_open': True}}
        with self.assertRaisesRegex(ProtocolError, 'schema_version_unsupported'):
            client.confirm_version(ENGAGE_VERSION, 'copy_open')
        client.capabilities = lambda: {'schema_versions': [ENGAGE_VERSION], 'features': {'copy_open': True}}
        self.assertEqual(client.confirm_version(ENGAGE_VERSION, 'copy_open'), ENGAGE_VERSION)


if __name__ == '__main__':
    unittest.main()


class ExactTargets(unittest.TestCase):
    """W2.8: each tap opens exactly the post or profile to engage with (Krish, 2026-10-28)."""

    def test_each_queue_platform_opens_its_exact_post_or_profile(self):
        from engine.engage import target_kind
        good = {('x', 'https://x.com/synthetic_one/status/1850000000000000001'): 'post',
                ('x', 'https://twitter.com/synthetic_one'): 'profile',
                ('tiktok', 'https://www.tiktok.com/@synthetic.one/video/7430000000000000001'): 'post',
                ('tiktok', 'https://www.tiktok.com/@synthetic.one'): 'profile',
                ('instagram', 'https://www.instagram.com/reel/SYNTHabc12/'): 'post',
                ('instagram', 'https://www.instagram.com/synthetic.one/'): 'profile',
                ('linkedin', 'https://www.linkedin.com/feed/update/urn:li:activity:7250000000000000001/'): 'post',
                ('linkedin', 'https://www.linkedin.com/posts/synthetic-one_ai-activity-7250000000000000001-AbCd'): 'post',
                ('linkedin', 'https://www.linkedin.com/in/synthetic-one/'): 'profile',
                ('youtube', 'https://www.youtube.com/watch?v=synthetic'): 'page'}
        for (platform, url), kind in good.items():
            self.assertEqual(target_kind(platform, url), kind, url)
        bad = [('x', 'https://x.com/home'), ('x', 'https://x.com/search?q=ai'), ('x', 'https://t.co/abc123'),
               ('x', 'http://x.com/synthetic_one/status/1850000000000000001'),
               ('tiktok', 'https://www.tiktok.com/foryou'), ('tiktok', 'https://vm.tiktok.com/ZMabc/'),
               ('instagram', 'https://www.instagram.com/explore/'), ('instagram', 'https://www.instagram.com/'),
               ('linkedin', 'https://www.linkedin.com/feed/'), ('linkedin', 'https://lnkd.in/abc'),
               ('linkedin', 'https://www.linkedin.com/search/results/content/?keywords=ai'),
               ('x', 'https://x.com.evil.example/synthetic_one/status/1850000000000000001')]
        for platform, url in bad:
            self.assertIsNone(target_kind(platform, url), url)

    def test_a_tap_that_does_not_open_its_exact_target_is_held_by_name(self):
        result = report(3, url='https://www.linkedin.com/feed/?n={}')
        self.assertEqual(result['proposals'], [])
        details = ' '.join(h['detail'] for h in result['holds'])
        self.assertIn('exact post or profile', details)

    def test_a_linkedin_reply_with_a_link_is_held(self):
        from engine.engage import tap_errors
        self.assertEqual(tap_errors('linkedin', 'https://www.linkedin.com/in/synthetic-one/', 'Read www.example.com'),
                         ['a LinkedIn reply carries no link'])
        self.assertEqual(tap_errors('x', 'https://x.com/synthetic_one', 'See https://example.com'), [])
