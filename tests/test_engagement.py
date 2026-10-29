"""The day's engagement taps as one copy and open ask (protocol 1.14.0). Synthetic fixtures only."""
import json
from pathlib import Path
import unittest

from engine.cc_loop import Loop, workspace_report
from engine.control_center import (ENGAGE_VERSION, ProtocolError, copy_open, engage_action, proposal,
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
