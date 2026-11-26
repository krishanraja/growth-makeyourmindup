"""The revenue desk adapter (Ruling, Krish, 2026-11-24): config/revenue-desk.json parses and names real sources.

No network and no figures. It checks that every read the adapter names exists, that a measure-first step carries
its reading plan, that no band binds before Krish's yes, and that the desk has no spend authority.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / 'config' / 'revenue-desk.json'
STAGES = {'counted', 'measure_first'}


def load():
    return json.loads(ADAPTER.read_text(encoding='utf-8'))


def defines(path, name):
    text = (ROOT / path).read_text(encoding='utf-8')
    return re.search(r'^def ' + re.escape(name) + r'\(', text, re.M) is not None


class RevenueDeskAdapterTest(unittest.TestCase):
    def test_the_adapter_parses_and_names_the_method(self):
        cfg = load()
        self.assertEqual(cfg['schema'], 'revenue-desk-adapter/1')
        self.assertEqual(cfg['method']['name'], 'revenue-desk')
        self.assertEqual(cfg['venture'], 'makeyourmindup')
        self.assertEqual(cfg['spend_authority'], 'none')
        self.assertFalse(cfg['sheets']['committed'])
        self.assertTrue(cfg['sheets']['path'].startswith('.scratch/'))
        self.assertTrue((ROOT / cfg['north_star']['doc']).exists())

    def test_the_money_path_runs_post_to_renewal(self):
        steps = [s['step'] for s in load()['money_path']]
        self.assertEqual(steps, ['post', 'visit', 'free_subscriber', 'paid_subscriber', 'renewal'])

    def test_every_named_source_exists(self):
        cfg = load()
        reads = [r for s in cfg['money_path'] for r in s['read']]
        reads += [s['measure_first']['nearest_reading'] for s in cfg['money_path'] if 'measure_first' in s]
        reads += [r['read'] for r in cfg['rules'] if 'read' in r]
        self.assertTrue(reads)
        for read in reads:
            self.assertTrue((ROOT / read['path']).exists(), read['path'])
            if 'function' in read:
                self.assertTrue(defines(read['path'], read['function']), read['path'] + ' ' + read['function'])

    def test_a_step_with_no_counted_read_is_measure_first_with_a_plan(self):
        cfg = load()
        names = {s['step'] for s in cfg['money_path']}
        for step in cfg['money_path']:
            self.assertIn(step['stage'], STAGES)
            if not step['read']:
                self.assertEqual(step['stage'], 'measure_first', step['step'])
            if step['stage'] == 'measure_first':
                self.assertTrue(step['measure_first']['plan'])
        retention = {r['id']: r for r in cfg['rules']}['cohort_retention']
        self.assertEqual(retention['stage'], 'measure_first')
        for rule in cfg['rules']:
            self.assertTrue(set(rule.get('needs', [])) <= names, rule['id'])

    def test_bands_are_assumptions_that_bind_only_after_his_yes(self):
        bands = load()['bands']
        self.assertEqual(bands['status'], 'assumption')
        self.assertFalse(bands['binding'])
        self.assertIn('yes', bands['binding_after'])
        for band in bands['per_step'].values():
            self.assertIsNone(band['warning'])
            self.assertIsNone(band['breach'])

    def test_discount_is_the_last_lever_and_traded(self):
        terms = {t['id']: t for t in load()['offer_terms']}
        self.assertIn('traded for something', terms['discount_last_lever']['rule'])

    def test_no_em_dash_exclamation_or_figure(self):
        text = ADAPTER.read_text(encoding='utf-8')
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn('!', text)
        self.assertNotIn('$', text)

    def test_agents_md_points_to_the_adapter(self):
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('## Revenue desk', text)
        self.assertIn('config/revenue-desk.json', text)


if __name__ == '__main__':
    unittest.main()
