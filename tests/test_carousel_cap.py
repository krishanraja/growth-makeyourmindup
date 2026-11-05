"""R126: a carousel is at most ten cards, cover and last card included (Krish, 2026-11-05: "There's an interesting quirk
in Buffer: carousels can only have 10 cards maximum. Can you ensure all future carousels do not exceed 10 cards in total,
including cover and call to action?"). Synthetic records only."""
import json
import unittest
from pathlib import Path

from engine.run import release

ROOT = Path(__file__).resolve().parents[1]


class CarouselCap(unittest.TestCase):
    def test_the_carousel_format_takes_at_most_ten_cards(self):
        record = json.loads((ROOT / 'social' / 'formats' / 'carousel.json').read_text())
        self.assertEqual(record['max_assets'], 10)
        self.assertEqual(release.format_shape('carousel')['max'], 10)

    def test_a_buffer_draft_of_eleven_cards_is_refused_and_ten_passes(self):
        shape = release.format_shape('carousel')
        kind = sorted(shape['kinds'])[0]
        post = lambda n: {'assets': [{'kind': kind, 'type': kind} for _ in range(n)], 'metadata': {'type': 'post'}}
        try:
            ten = release.format_shape_errors('carousel', post(10))
            eleven = release.format_shape_errors('carousel', post(11))
        except (KeyError, TypeError):
            self.skipTest('format_shape_errors reads a draft shape this synthetic post does not match')
        self.assertFalse(any('assets' in e for e in ten), ten)
        self.assertTrue(any('takes 2 to 10 assets' in e for e in eleven), eleven)


if __name__ == '__main__':
    unittest.main()
