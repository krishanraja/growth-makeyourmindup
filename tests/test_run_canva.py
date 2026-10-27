"""The Canva brand lint (engine/run/canva.py) against social/brand/kit.json. Synthetic designs only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from engine.run import cli
from engine.run.canva import colour, lint, lint_design, load_kit
from engine.run.invariants import ROOT, guard_exists

PIECE = ('TEST FIXTURE ONLY. A synthetic piece about who gets paid.\n'
         'The model host keeps most of the money, and the tool on top keeps less.\n'
         "Ask who owns the model before you sign.")


def kit_with_template():
    kit = copy.deepcopy(load_kit())
    kit['templates'] = {'receipt-card-x': 'SYNTHETIC-TEMPLATE-ID'}
    return kit


def design(**changes):
    base = {'channel': 'x', 'width': 1600, 'height': 900, 'size': 'x-card', 'template': 'receipt-card-x',
            'colours': ['#0C1512', '#f4efe4', '7EF0C0'], 'fonts': ['Anton', 'Archivo Regular', 'IBM Plex Mono'],
            'texts': ['“The model host keeps most of the money, and the tool on top keeps less.”',
                      'Read it free']}
    base.update(changes)
    return base


def codes(found):
    return sorted({f['code'] for f in found})


class CanvaLintTests(unittest.TestCase):
    def test_kit_holds_the_makeyourmindup_brand(self):
        kit = load_kit()
        self.assertEqual((kit['kit_id'], kit['name']), ('kAHZOJ-K6I8', 'Make Your Mind Up'))
        self.assertEqual({p['name']: p['hex'] for p in kit['palette']},
                         {'Ink': '#0C1512', 'Ink deep': '#070D0B', 'Cream': '#F4EFE4', 'Deep green': '#2F6B5C',
                          'Mint': '#7EF0C0', 'Butter': '#FFD84D', 'Coral': '#FF6A4D', 'Lilac': '#B7A6FF'})
        self.assertEqual(kit['fonts'], {'heading': 'Anton', 'subheading': 'Fraunces', 'body': 'Archivo',
                                        'labels': 'IBM Plex Mono'})
        self.assertEqual({k: (v['width'], v['height']) for k, v in kit['dimensions'].items()},
                         {'note-image': (1456, 1048), 'square': (1080, 1080), 'portrait': (1080, 1350),
                          'story': (1080, 1920), 'x-card': (1600, 900)})
        self.assertTrue(kit['templates'])  # built in Canva on 27 Oct 2026
        for key, entry in kit['templates'].items():
            self.assertRegex(entry['design_id'], r'^DA[A-Za-z0-9_-]{9}$', key)
            self.assertIn((entry['width'], entry['height']), {(v['width'], v['height']) for v in kit['dimensions'].values()}, key)
        self.assertTrue(guard_exists('engine/run/canva.py:lint'))  # crew/registry.json canva-studio lint

    def test_an_on_kit_design_passes(self):
        kit = kit_with_template()
        self.assertEqual(lint_design(design(), PIECE, kit), [])
        note = design(channel='substack-notes', width=1456, height=1048, size=None, texts=['Who gets paid?'])
        self.assertEqual(lint_design(note, None, kit), [])
        self.assertEqual(colour('#0c1'), '#00CC11')
        self.assertIsNone(colour('teal'))

    def test_off_kit_colour_font_and_size_are_refused(self):
        kit = kit_with_template()
        self.assertEqual(codes(lint_design(design(colours=['#0C1512', '#FF0000', 'teal']), PIECE, kit)),
                         ['off_kit_colour'])
        self.assertEqual(codes(lint_design(design(fonts=['Anton', 'Comic Sans MS', 'Antonio']), PIECE, kit)),
                         ['off_kit_font'])
        self.assertEqual(codes(lint_design(design(width=1080, height=1920, size=None), PIECE, kit)),
                         ['wrong_dimensions'])  # a Story frame is not an X size in the kit
        self.assertEqual(codes(lint_design(design(size='portrait'), PIECE, kit)), ['wrong_dimensions'])
        self.assertEqual(codes(lint_design(design(channel='youtube', size=None), PIECE, kit)), ['wrong_dimensions'])
        self.assertEqual(codes(lint_design(design(channel='myspace', size=None), PIECE, kit)), ['unknown_channel'])
        self.assertEqual(codes(lint_design(design(width='wide'), PIECE, kit)), ['bad_dataset'])
        self.assertEqual(codes(lint_design('not a design', PIECE, kit)), ['bad_dataset'])

    def test_a_quote_must_be_a_literal_match_to_the_piece(self):
        kit = kit_with_template()
        straight = design(texts=['"The model host keeps most of the money,  and the tool on top keeps less."'])
        self.assertEqual(lint_design(straight, PIECE, kit), [], 'quote marks and whitespace are normalised')
        curly = design(quotes=['Ask who owns the model before you sign.'], texts=[])
        self.assertEqual(lint_design(curly, PIECE.replace("'", '’'), kit), [])
        paraphrase = design(texts=['“The host keeps nearly all the money.”'])
        self.assertEqual(codes(lint_design(paraphrase, PIECE, kit)), ['quote_not_in_piece'])
        self.assertEqual(codes(lint_design(design(), None, kit)), ['no_piece_text'])
        self.assertEqual(codes(lint_design(design(quotes=['the model host keeps most']), PIECE, kit)),
                         ['quote_not_in_piece'], 'case is part of a literal match')

    def test_boilerplate_and_unapproved_templates_are_refused(self):
        kit = kit_with_template()
        found = lint_design(design(texts=['Illustration generated with AI']), PIECE, kit)
        self.assertEqual(codes(found), ['boilerplate'])
        self.assertEqual(codes(lint_design(design(template='freehand'), PIECE, kit)), ['template_not_approved'])
        self.assertEqual(codes(lint_design(design(template=None), PIECE, kit)), ['template_not_approved'])
        # The checked-in kit carries the templates built in Canva; anything else holds.
        self.assertEqual(codes(lint(design(), PIECE)), [])
        self.assertEqual(codes(lint(design(template='freehand'), PIECE)), ['template_not_approved'])

    def test_canva_lint_is_a_run_route(self):
        self.assertEqual(cli.ROUTES['canva'], 'canva')
        with tempfile.TemporaryDirectory() as folder:
            path, piece = Path(folder) / 'design.json', Path(folder) / 'piece.txt'
            path.write_text(json.dumps(design(colours=['#123456'])), encoding='utf-8')
            piece.write_text(PIECE, encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(['canva', 'lint', str(path), '--piece', str(piece)]), 1)
            self.assertEqual(json.loads(out.getvalue())['codes'], ['off_kit_colour'])


if __name__ == '__main__':
    unittest.main()
