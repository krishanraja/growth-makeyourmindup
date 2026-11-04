"""R125: the publishing day decides an asset's colour, Monday to Saturday. Synthetic fixtures only."""
import unittest

from engine import day_colours
from engine.run import artdirect
from engine.run.canva import lint_design, load_kit

# Monday 9 November 2026 to Saturday 14 November 2026.
WEEK = {'Monday': '2026-11-09', 'Tuesday': '2026-11-10', 'Wednesday': '2026-11-11',
        'Thursday': '2026-11-12', 'Friday': '2026-11-13', 'Saturday': '2026-11-14'}
BUTTER, LILAC, CORAL, MINT, INK = '#FFD84D', '#B7A6FF', '#FF6A4D', '#7EF0C0', '#0C1512'


class DayColours(unittest.TestCase):
    def test_each_series_day_wears_its_subchannel_and_every_other_day_the_house_mint(self):
        expected = {'Monday': ('butter', BUTTER), 'Wednesday': ('lilac', LILAC), 'Friday': ('coral', CORAL)}
        for day, date in WEEK.items():
            look = day_colours.day_look(date)
            self.assertEqual(look['day'], day)
            self.assertEqual((look['tone'], look['colour']), expected.get(day, ('mint', MINT)), day)
            self.assertEqual(look['series_day'], day in expected)

    def test_the_kit_holds_the_same_colours(self):
        import json
        from pathlib import Path
        kit = json.loads((Path(__file__).resolve().parents[1] / 'render' / 'templates.json').read_text())['kit']['colours']
        self.assertEqual({kit['butter'], kit['lilac'], kit['coral']}, day_colours.SERIES_COLOURS)
        self.assertEqual(kit['mint'], day_colours.OFF_DAY[2])

    def test_an_off_day_paints_no_subchannel_colour(self):
        self.assertEqual(day_colours.colour_errors([INK, MINT], WEEK['Thursday']), [])
        for wrong in (BUTTER, LILAC, CORAL):
            found = day_colours.colour_errors([INK, wrong.lower()], WEEK['Thursday'])
            self.assertEqual(len(found), 1)
            self.assertIn('Thursday is an off day and wears no subchannel colour', found[0])
        self.assertTrue(day_colours.colour_errors([BUTTER], None), 'an undated asset is held as an off day')

    def test_a_series_day_paints_its_own_colour_only(self):
        self.assertEqual(day_colours.colour_errors([INK, LILAC, MINT], WEEK['Wednesday']), [])
        found = day_colours.colour_errors([LILAC, CORAL], WEEK['Wednesday'])
        self.assertEqual(len(found), 1)
        self.assertIn(CORAL, found[0])

    def test_art_direction_briefs_the_day_and_gates_the_render(self):
        piece = {'piece_id': 'synthetic-a', 'title': 'A synthetic title', 'claims': [], 'lane': 'meme',
                 'date': WEEK['Saturday']}
        prompt = artdirect.build_prompt(piece, '- Day: {{day}}')
        self.assertIn('Saturday: an off day', prompt)
        self.assertNotIn('{{day}}', artdirect.build_prompt({**piece, 'date': WEEK['Friday']}, '{{day}}'))
        self.assertIsNone(artdirect.piece_errors(piece))
        self.assertIsNotNone(artdirect.piece_errors({**piece, 'date': 'Saturday'}))
        renders = [{'template': 'piece:synthetic-a/cover', 'colours': [INK, BUTTER]}]
        self.assertTrue(artdirect.day_errors(renders, WEEK['Saturday']))
        self.assertEqual(artdirect.day_errors(renders, WEEK['Monday']), [])

    def test_a_dated_canva_design_is_held_to_its_day(self):
        base = {'channel': 'x', 'width': 1600, 'height': 900, 'size': 'x-card',
                'colours': [INK, '#F4EFE4', CORAL], 'fonts': ['Anton', 'Archivo Regular', 'IBM Plex Mono'],
                'texts': ['Read it free']}
        kit = load_kit()
        friday = [f['code'] for f in lint_design({**base, 'date': WEEK['Friday']}, None, kit, require_template=False)]
        tuesday = [f['code'] for f in lint_design({**base, 'date': WEEK['Tuesday']}, None, kit, require_template=False)]
        undated = [f['code'] for f in lint_design(base, None, kit, require_template=False)]
        self.assertNotIn('wrong_day_colour', friday)
        self.assertIn('wrong_day_colour', tuesday)
        self.assertNotIn('wrong_day_colour', undated)


if __name__ == '__main__':
    unittest.main()
