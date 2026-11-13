"""All vertical content goes to Instagram, Threads, Facebook, TikTok and X.

Ruling (Krish, 2026-11-13): "saturdays post should be instagram, threads, facebook, tiktok, X - all vertical content
should be all those platforms". Every vertical format reaches the five, the inventory refuses one that does not, and
the run spec warns on a vertical post that misses any. Synthetic only.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.run.spec import vertical_warnings
from engine.social import ROOT, VERTICAL_CHANNELS, VERTICAL_FORMATS, inventory, vertical_missing

COVER = '1' * 64
CLIP = '2' * 64


def slot(slot_id, channel, fmt, sha):
    return {'slot_id': slot_id, 'channel': channel, 'format': fmt, 'assets': [{'name': 'card-1.png', 'sha256': sha}]}


class VerticalChannelTests(unittest.TestCase):
    def test_the_five_and_the_vertical_formats(self):
        self.assertEqual(VERTICAL_CHANNELS, ('instagram', 'threads', 'facebook', 'tiktok', 'x'))
        self.assertEqual(set(VERTICAL_FORMATS), {'carousel', 'short-video', 'meme'})

    def test_every_vertical_format_reaches_all_five_both_ways(self):
        records = inventory()
        for fmt in VERTICAL_FORMATS:
            self.assertEqual(vertical_missing(fmt, records['format'][fmt]['channels']), [], fmt)
            for channel in VERTICAL_CHANNELS:
                self.assertIn(fmt, records['channel'][channel]['formats'], channel + ' takes ' + fmt)

    def test_inventory_refuses_a_vertical_format_that_misses_a_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
            (root / 'docs').mkdir()
            for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
                shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
            inventory(root)
            for path, key, drop in (('formats/carousel.json', 'channels', 'threads'),
                                    ('channels/threads.json', 'formats', 'carousel')):
                record_path = root / 'social' / path
                record = json.loads(record_path.read_text(encoding='utf-8'))
                record[key].remove(drop)
                record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'vertical format goes to Instagram, Threads, Facebook, TikTok and X'
                                                    r'.*carousel misses threads'):
                inventory(root)

    def test_other_formats_are_not_held_to_the_five(self):
        self.assertEqual(vertical_missing('text', ['threads']), [])
        self.assertEqual(vertical_missing('single-image', ['x']), [])
        self.assertEqual(vertical_missing('carousel', ['instagram', 'facebook']), ['threads', 'tiktok', 'x'])

    def test_spec_warns_on_a_vertical_post_that_misses_a_channel(self):
        partial = [slot('sat-ig', 'instagram', 'carousel', COVER), slot('sat-fb', 'facebook', 'carousel', COVER)]
        warnings = vertical_warnings(partial)
        self.assertEqual([(w['code'], w['slot_id']) for w in warnings], [('vertical_channels_missing', 'sat-ig')])
        self.assertIn('misses threads, tiktok, x', warnings[0]['message'])
        # X's four-card cut is a single-image slot of the same post, and counts as its X post.
        full = partial + [slot('sat-th', 'threads', 'carousel', COVER), slot('sat-tt', 'tiktok', 'carousel', COVER),
                          slot('sat-x', 'x', 'single-image', COVER), slot('sat-yt', 'youtube', 'short-video', CLIP)]
        self.assertEqual([w['slot_id'] for w in vertical_warnings(full)], ['sat-yt'], 'the clip is its own post')
        clip = [slot('clip-' + c, c, 'short-video', CLIP) for c in VERTICAL_CHANNELS + ('youtube',)]
        self.assertEqual(vertical_warnings(full[:-1] + clip), [])
        # A text post or a slot with no asset is never held to the five.
        self.assertEqual(vertical_warnings([slot('t', 'threads', 'text', COVER),
                                            {'slot_id': 'n', 'channel': 'threads', 'format': 'text', 'assets': []}]), [])


if __name__ == '__main__':
    unittest.main()
