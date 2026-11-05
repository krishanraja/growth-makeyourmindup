"""R125: no Growth asset wears a series' colour or name, on any day; the Tuesday meme carries the house mark bottom
right; the Saturday carousel keeps the standard of the first one. Synthetic fixtures only."""
import json
import re
import unittest
from pathlib import Path

from engine import series_colours
from engine.run import artdirect
from engine.run.canva import lint_design, load_kit

ROOT = Path(__file__).resolve().parents[1]
BUTTER, LILAC, CORAL, MINT, INK, CREAM = '#FFD84D', '#B7A6FF', '#FF6A4D', '#7EF0C0', '#0C1512', '#F4EFE4'


def canva(**changes):
    base = {'channel': 'x', 'width': 1600, 'height': 900, 'size': 'x-card',
            'colours': [INK, CREAM, MINT], 'fonts': ['Anton', 'Archivo Regular', 'IBM Plex Mono'],
            'texts': ['Read it free']}
    base.update(changes)
    return [f['code'] for f in lint_design(base, None, load_kit(), require_template=False)]


class SeriesColours(unittest.TestCase):
    def test_the_series_and_the_kit_hold_the_same_colours(self):
        kit = json.loads((ROOT / 'render' / 'templates.json').read_text())['kit']['colours']
        self.assertEqual({kit['butter'], kit['lilac'], kit['coral']}, series_colours.SERIES_COLOURS)
        self.assertEqual(kit['mint'], series_colours.HOUSE_TONE[1])
        self.assertEqual(set(series_colours.SERIES), {'follow.the.money', 'under.the.hood', 'mind.the.gap'})

    def test_no_asset_wears_a_series_colour_on_any_day(self):
        self.assertEqual(series_colours.colour_errors([INK, MINT, CREAM]), [])
        for wrong in (BUTTER, LILAC, CORAL):
            found = series_colours.colour_errors([INK, wrong.lower()])
            self.assertEqual(len(found), 1)
            self.assertIn(wrong, found[0])

    def test_no_asset_names_a_series(self):
        self.assertEqual(series_colours.name_errors(['Mind the gaps in your notes', 'what is under the hood']), [])
        found = series_colours.name_errors(['From Follow.The.Money: who gets paid'])
        self.assertEqual(len(found), 1)
        self.assertIn('follow.the.money', found[0])

    def test_art_direction_briefs_the_rule_and_gates_every_render(self):
        piece = {'piece_id': 'synthetic-a', 'title': 'A synthetic title', 'claims': [], 'lane': 'meme'}
        prompt = artdirect.build_prompt(piece, '- Colour: {{colour_rule}}')
        self.assertIn('never butter, lilac or coral', prompt)
        self.assertNotIn('{{colour_rule}}', prompt)
        self.assertTrue(artdirect.series_errors([{'template': 'piece:synthetic-a/cover', 'colours': [INK, BUTTER]}]))
        self.assertEqual(artdirect.series_errors([{'template': 'piece:synthetic-a/cover', 'colours': [INK, MINT]}]), [])

    def test_a_canva_design_is_refused_a_series_colour_or_name_dated_or_not(self):
        self.assertNotIn('series_colour', canva())
        self.assertIn('series_colour', canva(colours=[INK, CREAM, CORAL]))
        self.assertIn('series_colour', canva(colours=[INK, LILAC], date='2026-11-11'))
        self.assertIn('series_name', canva(texts=['under.the.hood, part two']))


class TuesdayMeme(unittest.TestCase):
    # Krish, 2026-11-04: "The Tuesday meme is likely to be more random but needs to be lightly subtly skinned in the
    # bottom right corner."
    def test_the_house_meme_templates_carry_the_mark_bottom_right_and_nothing_else(self):
        templates = json.loads((ROOT / 'render' / 'templates.json').read_text())['templates']
        for tid in ('meme-square', 'meme-vertical'):
            text = (ROOT / 'render' / templates[tid]['file']).read_text()
            self.assertEqual(text.count('brandmark'), 2, tid)   # the corner mark and its one style rule
            self.assertIn('<div class="brandmark corner"></div>', text, tid)
            for gone in ('class="masthead"', 'class="label"', 'makeyourmindup.ai', '{{label}}'):
                self.assertNotIn(gone, text, tid)
            self.assertNotIn('label', templates[tid]['fields'], tid)
            self.assertEqual(templates[tid]['choices']['tone'], ['mint'], tid)

    def test_a_canva_meme_needs_its_mark_small_in_the_bottom_right(self):
        square = dict(channel='instagram', width=1080, height=1080, size='square', template='meme-square')
        self.assertIn('meme_mark_missing', canva(**square))
        self.assertNotIn('meme_mark_missing', canva(**square, mark={'box': [880, 1000, 1030, 1030]}))
        self.assertEqual([c for c in canva(**square, mark={'box': [880, 1000, 1030, 1030]}) if c.startswith('meme_')], [])
        self.assertIn('meme_mark_misplaced', canva(**square, mark={'box': [40, 40, 200, 70]}))
        self.assertIn('meme_mark_too_big', canva(**square, mark={'box': [560, 980, 1060, 1060]}))
        tall = dict(channel='instagram', width=1080, height=1920, size='story', template='meme-video')
        self.assertIn('meme_mark_misplaced', canva(**tall, mark={'box': [880, 1860, 1030, 1890]}))
        self.assertNotIn('meme_mark_misplaced', canva(**tall, mark={'box': [880, 1540, 1030, 1570]}))


class SaturdayCarousel(unittest.TestCase):
    # Krish, 2026-11-04: "Saturday's carousel should have the standards of the first one that's coming up this
    # Saturday." The first is the 7 November good news, render/pieces/off-sat-goodnews.
    KIT = ROOT / 'render' / 'pieces' / 'off-sat-goodnews'

    def test_the_first_saturday_carousel_is_the_reference_kit(self):
        kit = json.loads((self.KIT / 'templates.json').read_text())
        self.assertEqual(set(kit['templates']), {'cover', 'item', 'close'})
        for tid, spec in kit['templates'].items():
            self.assertEqual((spec['width'], spec['height']), (1080, 1350), tid)
            html = (self.KIT / spec['file']).read_text()
            self.assertIn('<div class="brandmark corner"></div>', html, tid)
        self.assertIn('five stories', kit['templates']['item']['note'])
        self.assertIn('photo', kit['templates']['cover']['fields'])
        self.assertIn('render/pieces/off-sat-goodnews', (ROOT / 'render' / 'KIT.md').read_text())

    def test_it_wears_no_series_colour_or_name(self):
        text = ''.join(f.read_text() for f in sorted(self.KIT.rglob('*')) if f.is_file() and f.suffix in ('.css', '.html', '.json'))
        self.assertFalse(re.search(r'var\(--(butter|lilac|coral)\)', text))
        self.assertEqual(series_colours.name_errors([text]), [])


if __name__ == '__main__':
    unittest.main()
