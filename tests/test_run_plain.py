"""The plain-English lint (engine/run/plain.py) for carousels and captions. Synthetic copy only.

Krish, 27 Oct 2026, on the last carousel: "It wasn't plain English and human and humble enough."
"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine.run import cli
from engine.run import spec as spec_module
from engine.run.plain import codes, humble, lint_carousel, lint_text, sentences
from engine.run.spec import lint, payload_sha256, social_records

ROOT = Path(__file__).resolve().parents[1]
GOOD = ['TEST FIXTURE. Who gets paid when your team buys an AI tool?',
        'Most of the money goes to the company that hosts the model.',
        'The tool you see is often a thin layer on top.',
        'That layer can change its price with one email.',
        'So ask who owns the model before you sign.',
        'I think this matters more than the demo does.',
        'Thanks for reading. Tell me where I got it wrong.']


class PlainTextTests(unittest.TestCase):
    def test_good_synthetic_carousel_passes(self):
        self.assertEqual(lint_carousel(GOOD, 'A short guide to who gets paid. I learned this the slow way.'), [])
        self.assertEqual(lint_text('One clear sentence. Then another one, just as clear.'), [])

    def test_long_sentences_and_long_averages_are_refused(self):
        long_one = ' '.join(['word'] * 26) + '.'
        self.assertEqual(codes(lint_text(long_one)), ['average_too_long', 'sentence_too_long'])
        steady = ' '.join(' '.join(['word'] * 18) + '.' for _ in range(3))
        self.assertEqual(codes(lint_text(steady)), ['average_too_long'])
        self.assertEqual(lint_text(' '.join(['word'] * 25) + '. Short one here.'), [])
        self.assertEqual(len(sentences('One here. Two here!\nThree here? Four.')), 4)

    def test_jargon_and_em_dashes_are_refused(self):
        found = lint_text('We leverage a robust ecosystem to unlock value. It is a game-changer.')
        self.assertEqual([f['detail'] for f in found if f['code'] == 'jargon'],
                         ['leverage', 'unlock', 'game-changer', 'robust', 'ecosystem'])
        for text, name in (('This paradigm is new.', 'paradigm'), ('Real synergy here.', 'synergy'),
                           ('Let us delve into it.', 'delve'), ('The landscape moved.', 'landscape'),
                           ('A cutting-edge tool.', 'cutting-edge'), ("In today’s market, prices fell.", "in today's")):
            self.assertIn(name, [f['detail'] for f in lint_text(text)], text)
        self.assertEqual(codes(lint_text('A clear story — with real stakes.')), ['em_dash'])
        self.assertEqual(lint_text('Landscaped gardens and unlockable doors are fine words.'), [])

    def test_stacked_two_word_fragments_are_refused(self):
        self.assertEqual(codes(lint_text('Big news. Huge stakes. Read the whole piece today.')), ['stacked_fragments'])
        self.assertEqual(lint_text('Thanks. Read the whole piece today, it is short.'), [])

    def test_a_carousel_needs_a_humble_human_line_and_six_to_eight_cards(self):
        cold = GOOD[:5] + ['Ask who owns the model.', 'Read the full piece today.']
        self.assertEqual(codes(lint_carousel(cold)), ['no_humble_line'])
        self.assertEqual(codes(lint_carousel(GOOD[2:])), ['card_count'])
        self.assertEqual(codes(lint_carousel(GOOD + GOOD[:2])), ['card_count'])
        self.assertEqual(codes(lint_carousel('not a list')), ['bad_input'])
        for line in ('I think we missed this.', 'I was wrong about the price.', 'We learned it the hard way.',
                     'Thanks, I owe you one.', 'I am not sure this lasts.'):
            self.assertTrue(humble(line), line)
        for line in ('Thanks for reading.', 'The price was wrong.', 'I sell this tool.'):
            self.assertFalse(humble(line), line)

    def test_carousel_lint_is_a_run_route(self):
        self.assertEqual((cli.ROUTES['carousel'], cli.ROUTES['plain']), ('plain', 'plain'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'carousel.json'
            path.write_text(json.dumps({'cards': GOOD, 'caption': 'I hope this helps.'}), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(['carousel', 'lint', str(path)]), 0)
            self.assertTrue(json.loads(out.getvalue())['valid'])
            path.write_text(json.dumps({'cards': GOOD[4:], 'caption': 'We leverage it.'}), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(['carousel', 'lint', str(path)]), 1)
            self.assertEqual(json.loads(out.getvalue())['codes'], ['card_count', 'jargon'])


class SpecCaptionTests(unittest.TestCase):
    def test_run_lint_blocks_an_unplain_carousel_and_warns_on_other_captions(self):
        spec = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        carousel, other = spec['slots'][0], spec['slots'][1]
        carousel.update(channel='instagram', format='carousel', words='TEST FIXTURE. We leverage the model.')
        other['words'] = 'TEST FIXTURE. We leverage the model.'
        for slot in (carousel, other):
            slot['payload_sha256'] = payload_sha256(slot)
        target = spec['north_star']['week_target']
        with patch.object(spec_module, 'week_target', lambda start, root=None: target):
            result = lint(spec, social_records(ROOT))
        errors = {(e['code'], e['slot_id']) for e in result['errors']}
        warnings = {(w['code'], w['slot_id']) for w in result['warnings']}
        self.assertIn(('plain_jargon', carousel['slot_id']), errors)
        self.assertIn(('plain_jargon', other['slot_id']), warnings)
        self.assertNotIn(('plain_jargon', other['slot_id']), errors)


if __name__ == '__main__':
    unittest.main()
