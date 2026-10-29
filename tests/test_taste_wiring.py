"""Inspiration House wiring: whoever makes reads his taste, reports back, and nothing that judges reads it.

Krish, 27 Oct 2026: "Make sure you're wiring into the Inspiration House repository in a way that is incredibly
robust". The procedure lives in krishanraja/inspirationhouse; docs/TASTE.md says only how this engine uses it.
Any session or PC automation that makes or writes follows it: there are no Claude routines (Krish, 29 Oct 2026).
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = re.compile('[–—]')
TASTE_WORDS = re.compile(r'taste|get_approved_taste|get_production_examples|voice-rules|inspiration', re.I)
# Everything that judges, scores or ranks a post. Judges never read taste (inspirationhouse docs/TWO_WAY.md).
JUDGES = ('engine/run/measure.py', 'engine/run/measure_auto.py', 'engine/run/buffer_reads.py',
          'engine/operations.py', 'crew/what-works/card.md', 'crew/what-works/lens.md',
          'crew/attribution-ladder/card.md')


def text(path):
    return (ROOT / path).read_text(encoding='utf-8')


class TasteWiringTests(unittest.TestCase):
    def test_judges_never_read_taste(self):
        for path in JUDGES:
            if (ROOT / path).exists():
                self.assertIsNone(TASTE_WORDS.search(text(path)), path + ' must never read taste or examples')

    def test_taste_file_reads_both_tools_and_never_blocks(self):
        raw = (ROOT / 'docs' / 'TASTE.md').read_bytes().replace(b'\r\n', b'\n')
        self.assertLessEqual(len(raw), 6 * 1024)
        body = ' '.join(raw.decode('utf-8').split())
        self.assertFalse(EM_DASH.search(body))
        for needle in ('get_approved_taste', 'get_production_examples', 'report_to_taste_engine',
                       'taste_unavailable', 'Taste never blocks a slot', 'ids only',
                       'Never take a subject from them', 'never invent one', 'character for character',
                       'never answer a card or approve a rule', 'At most one a week', 'krishanraja/inspirationhouse',
                       'Any session or PC automation that makes or writes for this engine',
                       'Whoever plans the week', 'There are no Claude routines',
                       # The only Control Center write a maker may call is the taste report (Ruling, Krish, 26 Oct 2026).
                       'Call no Control Center write tool but `report_to_taste_engine`'):
            self.assertIn(needle, body)
        # No schedule of its own: no clock time, no cron and no routine file (Krish, 29 Oct 2026).
        self.assertIsNone(re.search(r'\b\d{1,2}:\d{2}\b|\bUTC\b|\bcron\b|routines/', body))

    def test_makers_are_pointed_at_the_taste_file(self):
        for path in ('docs/LANES.md', 'AGENTS.md'):
            self.assertIn('`docs/TASTE.md`', text(path), path)
        self.assertFalse((ROOT / 'routines').exists(), 'there are no Claude routines (Krish, 29 Oct 2026)')

    def test_briefs_carry_the_ruling(self):
        ruling = ('Ruling (Krish, 2026-10-27): a maker may read his production examples (his study_style cards and '
                  'his form signals) as context for making; never a rule, never to judge.')
        for path in ('docs/briefs/2026-10-28-control-center-production-examples.md',
                     'docs/briefs/2026-10-28-inspirationhouse-growth-reader.md'):
            self.assertIn(ruling, text(path), path)
        tool = text('docs/briefs/2026-10-28-control-center-production-examples.md')
        self.assertIn('Never include `subject` or `workflow`', tool)


if __name__ == '__main__':
    unittest.main()
