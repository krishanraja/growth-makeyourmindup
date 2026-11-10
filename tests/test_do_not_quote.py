"""growth.py check refuses the unsourced statistics the external growth skills repeat (rule 6)."""
import json
from pathlib import Path
import tempfile
import unittest

import growth

ROOT = Path(__file__).resolve().parents[1]
DIGEST = ROOT / 'knowledge' / 'corpus' / 'external-growth-skills.md'


def pack(text, why=None):
    item = {'platform': 'x', 'text': text}
    if why:
        item['why'] = why
    return {'pack_date': '2026-11-10', 'kind': 'daily', 'headline': 'Test fixture only, do not publish',
            'items': [item]}


class DoNotQuoteTests(unittest.TestCase):
    def check(self, value):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pack.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            return growth.main(['check', str(path)])

    def test_each_listed_statistic_is_refused(self):
        for text in ('People now have an 8-second attention span, so lead fast.',
                     'Your attention span is shorter than a goldfish.',
                     'Keep it under 75 words and you get more replies.',
                     'Most decision-makers ignore irrelevant emails.',
                     'Success is mostly human engineering.',
                     'Readers have an 8-sec attention span now.',
                     'Notes of fewer than 75 words get more replies.',
                     '75-word emails get more replies.',
                     'Human engineering is most of outreach success.'):
            with self.subTest(text=text):
                self.assertTrue(growth.unsourced_stats(pack(text)))
                with self.assertRaisesRegex(ValueError, 'unsourced statistic'):
                    self.check(pack(text))

    def test_reviewer_fields_and_envelopes_are_read_too(self):
        value = {'schema_version': 2, 'pack': pack('One useful question.', why='Readers have an 8 second attention span.')}
        self.assertEqual(len(growth.unsourced_stats(value)), 1)
        with self.assertRaisesRegex(ValueError, 'draft 1 why'):
            self.check(value)

    def test_headline_target_name_and_number_notes_are_read(self):
        value = pack('One useful question.')
        value['headline'] = 'Cold emails under 75 words get more replies'
        value['items'][0]['target_name'] = 'Readers with an 8-second attention span'
        value['numbers'] = [{'metric': 'replies', 'value': 3, 'note': 'Most decision-makers ignore irrelevant emails'}]
        found = growth.unsourced_stats(value)
        self.assertEqual(len(found), 3)
        for where in ('headline', 'draft 1 target_name', 'number row 1 note'):
            self.assertTrue(any(line.startswith(where) for line in found), where)

    def test_near_misses_pass(self):
        for text in ('The first 8 seconds decide attention, so the hook leads (source in the note).',
                     'We ran a human engineering review of the onboarding flow.',
                     'Keep the note under 75 words.',
                     'Eight seconds in, the demo starts.'):
            with self.subTest(text=text):
                self.assertEqual(growth.unsourced_stats(pack(text)), [])

    def test_clean_copy_still_passes(self):
        self.assertEqual(growth.unsourced_stats(pack('We tested two agents on five everyday jobs.')), [])
        self.assertEqual(self.check(pack('We tested two agents on five everyday jobs.')), 0)

    def test_the_digest_lists_what_check_refuses(self):
        text = DIGEST.read_text(encoding='utf-8')
        for label, _ in growth.DO_NOT_QUOTE:
            self.assertIn(label, text)


if __name__ == '__main__':
    unittest.main()
