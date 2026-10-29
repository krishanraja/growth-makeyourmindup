"""Prepaid credits, protocol 1.16.0 (engine/credits.py). Synthetic pools only, against the local stand-in."""
import tempfile
import unittest

from engine.control_center import CREDITS_VERSION, SCHEMA_VERSION, ProtocolError, build_report, objective, validate_report
from engine.credits import CreditRefused, Guard, credits_block, credits_lines, spent_errors
from tests import test_control_center as cc

NOW, StandIn = cc.NOW, cc.StandIn


def setUpModule():
    cc.setUpModule()


def tearDownModule():
    cc.tearDownModule()

POOLS = {'rule': 'Spend within remaining_for_you.', 'pools': [
    {'pool': 'elevenlabs', 'tool': 'ElevenLabs', 'unit': 'characters', 'share': 'main', 'share_amount': 50000,
     'spent_this_cycle': 0, 'remaining_for_you': 1000, 'pool_balance': None, 'balance_as_of': None,
     'use_by': '2026-11-09', 'resets_on': '2026-11-10', 'days_left': 12, 'unit_costs': []},
    {'pool': 'apify', 'tool': 'Apify', 'unit': 'usd', 'share': 'main', 'share_amount': 5.8,
     'spent_this_cycle': 0, 'remaining_for_you': 5.8, 'pool_balance': None, 'balance_as_of': None,
     'use_by': '2026-11-20', 'resets_on': '2026-11-21', 'days_left': 23, 'unit_costs': []}]}


def report(credits_spent=None):
    return build_report('makeyourmindup:2026-10-17:credits', 'synthetic', NOW, 'fixture', NOW, 'held',
                        [objective('new_subscribers', reason='Fixture: not measured')],
                        [{'line': 'Fixture run'}], [], [], [{'reason': 'Fixture hold'}], credits_spent=credits_spent)


class CreditsTests(unittest.TestCase):
    def test_no_block_is_unknown_and_spends_nothing(self):
        self.assertIsNone(credits_block({'directive': {'schema_version': '1.16.0'}}))
        self.assertIn('unknown', credits_lines(None)[0])
        guard = Guard(None)
        with self.assertRaisesRegex(CreditRefused, 'unknown'):
            guard.reserve('elevenlabs', 1, 'a narration draft')
        self.assertEqual(guard.spent, [])
        self.assertEqual(report()['schema_version'], SCHEMA_VERSION, 'no spend, the version is unchanged')
        self.assertNotIn('credits_spent', report())

    def test_a_spend_past_the_share_is_refused(self):
        guard = Guard(credits_block({'directive': {'credits': POOLS}}))
        guard.reserve('apify', 5.0, 'subscriber-source research run')
        with self.assertRaisesRegex(CreditRefused, 'over the share'):
            guard.reserve('apify', 1.0, 'one more run')
        with self.assertRaisesRegex(CreditRefused, 'no share'):
            guard.reserve('higgsfield', 1, 'a still')
        self.assertEqual(len(guard.spent), 1)

    def test_lines_name_each_pool_and_its_last_day(self):
        lines = credits_lines(credits_block({'credits': POOLS}))
        self.assertEqual(len(lines), 2)
        self.assertIn('ElevenLabs 1,000 characters left', lines[0])
        self.assertIn('use by 2026-11-09', lines[0])
        self.assertIn('Apify $5.80 left', lines[1])

    def test_a_report_with_credits_spent_is_1_16_0_and_validates(self):
        guard = Guard(credits_block({'credits': POOLS}))
        guard.reserve('elevenlabs', 800, 'narration draft of an approved script, waiting for his yes')
        sent = report(guard.spent)
        self.assertEqual(sent['schema_version'], CREDITS_VERSION)
        validate_report(sent)
        self.assertEqual(spent_errors([{'pool': 'apify', 'amount': 1, 'asset': 'mailed a@b.co', 'objective_key': None}]),
                         ['credits_spent[0] says what was made in words, never an address'])
        with self.assertRaises(ValueError):
            report([{'pool': 'apify', 'amount': 0, 'asset': 'nothing', 'objective_key': None}])

    def test_the_stand_in_takes_it_only_where_credits_are_served(self):
        guard = Guard(credits_block({'credits': POOLS}))
        guard.reserve('apify', 2.5, 'audience research run')
        sent = report(guard.spent)
        with StandIn() as stand:
            stand.capabilities = {'schema_versions': ['1.0.0', CREDITS_VERSION], 'features': {'credits': False}}
            with self.assertRaisesRegex(ProtocolError, 'credits_unsupported'):
                stand.client().post_report(sent)
            self.assertEqual(stand.posts('reports'), [])
            stand.capabilities = {'schema_versions': ['1.0.0', CREDITS_VERSION], 'features': {'credits': True}}
            self.assertTrue(stand.client().post_report(sent)['readback_matches'])
            self.assertEqual(stand.posts('reports')[0]['body']['credits_spent'][0]['pool'], 'apify')


class RunnerCreditsTests(unittest.TestCase):
    capture = cc.CliTests.capture
    workspace = cc.CliTests.workspace

    def test_runner_reports_the_share_and_spends_none(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            stand.directive_extra = {'credits': POOLS}
            code, text = self.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            body = stand.posts('reports')[0]['body']
            self.assertEqual(body['schema_version'], SCHEMA_VERSION)
            self.assertNotIn('credits_spent', body)
            lines = [a['line'] for a in body['activity']]
            self.assertTrue(any(line.startswith('Prepaid credits: ElevenLabs') for line in lines), lines)
            self.assertNotIn('1,000 characters', text, 'the share stays off the public log')


if __name__ == '__main__':
    unittest.main()
