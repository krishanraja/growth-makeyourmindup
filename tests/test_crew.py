"""The crew registry and its cards: size limits, house rules, W45 and live citations."""
import json
from pathlib import Path
import tempfile
import unittest

from engine.run.invariants import (CARD_BYTES, LENS_BYTES, ROOT, W45, check_cards, collapse, house_errors,
                                   load_failures, load_registry, load_rules)

CARD = ('# Card: Synthetic\n\n| If | Then | Cite |\n|---|---|---|\n'
        '| A | B | P1, R01 |\n| C | D | P8 |\n| E | F | R01 |\n')
LENS = '# Lens\n\n**Question:** Is this synthetic?\n'


def crew_root(folder, card=CARD, lens=LENS):
    root = Path(folder)
    entries = []
    for cid in sorted(W45):
        (root / 'crew' / cid).mkdir(parents=True)
        (root / 'crew' / cid / 'card.md').write_text(card, encoding='utf-8')
        (root / 'crew' / cid / 'lens.md').write_text(lens, encoding='utf-8')
        entries.append({'id': cid, 'name': cid, 'owns': ['x'], 'channels': ['x'], 'formats': ['x'],
                        'lint': 'engine/run/spec.py:lint', 'check': 'engine/run/measure.py:check',
                        'card': 'crew/' + cid + '/card.md', 'lens': 'crew/' + cid + '/lens.md', 'w45': True})
    (root / 'crew' / 'registry.json').write_text(json.dumps({'crew': entries}), encoding='utf-8')
    return root


class CrewTests(unittest.TestCase):
    def setUp(self):
        self.crew = load_registry()

    def test_registry_lists_the_specialists_and_the_release_gate(self):
        # Twelve from plan section 3, then row 13, the blind Send-Test Reader (Krish, 2026-10-28).
        self.assertEqual(len(self.crew), 14)
        self.assertEqual(sorted(e['row'] for e in self.crew if e['row'] is not None), list(range(1, 14)))
        self.assertEqual([e['id'] for e in self.crew if e['row'] is None], ['release-gate'])
        self.assertEqual(next(e for e in self.crew if e['row'] == 13)['id'], 'send-test')

    def test_send_test_reader_is_blind_and_cites_the_ruling(self):
        entry = next(e for e in self.crew if e['id'] == 'send-test')
        self.assertEqual((entry['lint'], entry['check']),
                         ('engine/share.py:share_errors', 'engine/share.py:compare_send_test'))
        self.assertFalse(entry['w45'])
        self.assertEqual(set(entry['formats']), {'meme', 'carousel', 'single-image', 'short-video', 'story', 'note'})
        card = collapse((ROOT / entry['card']).read_text(encoding='utf-8'))
        for phrase in ('never the share block', 'Back for revision with the reader\'s answer',
                       'growth.py social send-test', 'R99'):
            self.assertIn(phrase, card)

    def test_what_works_card_makes_share_rates_the_snackable_measure(self):
        text = collapse((ROOT / 'crew' / 'what-works' / 'card.md').read_text(encoding='utf-8'))
        for phrase in ('sends (native shares) per reach and saves per reach', 'share_rates',
                       "a house hypothesis until MYMU's own dated data confirms it", 'never zero'):
            self.assertIn(phrase, text)

    def test_every_entry_has_card_and_lens_within_size(self):
        for entry in self.crew:
            card, lens = ROOT / entry['card'], ROOT / entry['lens']
            self.assertTrue(card.is_file() and lens.is_file(), entry['id'])
            self.assertLessEqual(len(card.read_bytes()), CARD_BYTES, entry['id'])
            self.assertLessEqual(len(lens.read_bytes()), LENS_BYTES, entry['id'])

    def test_cards_and_lenses_have_no_em_dash_or_percent(self):
        for entry in self.crew:
            for field in ('card', 'lens'):
                self.assertEqual(house_errors((ROOT / entry[field]).read_text(encoding='utf-8')), [], entry[field])
        registry = (ROOT / 'crew' / 'registry.json').read_text(encoding='utf-8')
        self.assertEqual(house_errors(registry), [])

    def test_w45_crew_is_exactly_the_planned_five(self):
        self.assertEqual({e['id'] for e in self.crew if e['w45']},
                         {'substack', 'threads', 'attribution-ladder', 'what-works', 'release-gate'})

    def test_cards_are_decision_tables_citing_plays_and_rules(self):
        rules = [r['id'] for r in load_rules()]
        failures = [f['id'] for f in load_failures()]
        self.assertEqual(check_cards(self.crew, rule_ids=rules, failure_ids=failures), [])

    def test_what_works_card_carries_its_verdict_rules(self):
        entry = next(e for e in self.crew if e['id'] == 'what-works')
        text = collapse((ROOT / entry['card']).read_text(encoding='utf-8')).lower()
        for phrase in ('every post gets a verdict at its judge window against its own channel and format median',
                       'engine.operations.experiment_decision', 'at least 6 observations', '"association, not cause"',
                       'two weeks as baseline with no verdicts', 'the ledger goes to krish in the sunday check-in'):
            self.assertIn(phrase, text)
        self.assertEqual(entry['check'], 'engine/operations.py:experiment_decision')

    def test_substack_card_gives_notes_identity_and_cadence(self):
        # 27 Oct correction: Notes post from Krish's profile, at most two a day (PUBLISHING-AUTHORITY.md).
        text = (ROOT / 'crew' / 'substack' / 'card.md').read_text(encoding='utf-8')
        self.assertNotIn('two to three', text)
        rows = [line for line in text.splitlines() if line.startswith('| A Note slot is due')]
        self.assertEqual(len(rows), 1)
        self.assertIn('Notes per day as signed, at most two a day', rows[0])
        identity = [line for line in text.splitlines() if '@mindmakerlive' in line]
        self.assertEqual(len(identity), 1)
        for phrase in ("Krish's personal voice", 'Buffer channel Krish', 'held for Krish', 'R59', 'R54'):
            self.assertIn(phrase, identity[0])
        self.assertTrue(any(line.startswith('| Buffer has no Substack channel connected') for line in text.splitlines()),
                        'the not-connected fallback stays')

    def test_measurement_specialist_card_carries_ga4(self):
        entry = next(e for e in self.crew if e['id'] == 'attribution-ladder')
        self.assertEqual(entry['name'], 'Measurement Specialist')
        self.assertIn('GA4', entry['owns'])
        self.assertTrue(entry['w45'])
        card = collapse((ROOT / entry['card']).read_text(encoding='utf-8'))
        for phrase in ('# Card: Measurement Specialist', 'Substack Growth sources stay the North Star source',
                       'G-VC5V9LDE17', 'sessions, free sign-ups and paid subscriptions per post',
                       'joined to slots on `utm_content`', 'the more conservative reading wins and the gap is logged',
                       'never guess an event name', 'What-Works Analyst', 'R83'):
            self.assertIn(phrase, card)
        lens = (ROOT / entry['lens']).read_text(encoding='utf-8')
        self.assertIn('do GA4 and Substack agree?', lens)

    def test_oversized_card_or_free_text_list_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder)
            self.assertEqual(check_cards(load_registry(root), root, ['R01']), [])
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder, card=CARD + '| G | ' + 'x' * CARD_BYTES + ' | P1 |\n')
            self.assertTrue(any('over 3072 bytes' in e for e in check_cards(load_registry(root), root)))
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder, card=CARD + '\n- Do not post links.\n')
            self.assertTrue(any('free-text list' in e for e in check_cards(load_registry(root), root)))
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder, card=CARD.replace('R01', 'R99'), lens=LENS + 'And another?\n')
            errors = check_cards(load_registry(root), root, ['R01'])
            self.assertTrue(any('unknown rule R99' in e for e in errors))
            self.assertTrue(any('exactly one question' in e for e in errors))

    def test_numbered_list_and_bad_row_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder, card=CARD + '\n1. Do not post links.\n')
            self.assertTrue(any('free-text list' in e for e in check_cards(load_registry(root), root)))
            data = json.loads((root / 'crew' / 'registry.json').read_text(encoding='utf-8'))
            data['crew'][0]['row'] = 'one'
            (root / 'crew' / 'registry.json').write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'row'):
                load_registry(root)

    def test_every_experiment_needs_at_least_six_observations(self):
        # The What-Works card promises the floor; engine.operations.experiment_decision takes any positive one.
        experiments = json.loads((ROOT / 'experiments.json').read_text(encoding='utf-8'))['experiments']
        self.assertTrue(experiments)
        for experiment in experiments:
            self.assertGreaterEqual(experiment['minimum_observations'], 6, experiment.get('id'))

    def test_missing_lens_and_wrong_w45_set_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = crew_root(folder)
            (root / 'crew' / 'threads' / 'lens.md').unlink()
            data = json.loads((root / 'crew' / 'registry.json').read_text(encoding='utf-8'))
            data['crew'][0]['w45'] = False
            (root / 'crew' / 'registry.json').write_text(json.dumps(data), encoding='utf-8')
            errors = check_cards(load_registry(root), root)
            self.assertIn('threads: missing crew/threads/lens.md', errors)
            self.assertTrue(any(e.startswith('W45 crew must be exactly') for e in errors))


if __name__ == '__main__':
    unittest.main()
