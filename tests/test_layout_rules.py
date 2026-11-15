"""Carousel covers, centred cards, the tall clear box and judges that see the cards (Ruling, Krish, 2026-11-15).

His words: "the front cover card does not look like a front cover", the cards "aren't using the page space centrally
or correctly. They look too bland and too plain", and "The POV computer meme, it's not centralized on the screen."
Every box and asset here is synthetic.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from engine.run import judges, kits, tall_meme


class LayoutRuleTests(unittest.TestCase):
    def line(self, box, centred=False):
        return {'box': box, 'centred': centred}

    def test_a_carousel_card_keeps_words_and_mark_inside_the_feed_margin(self):
        ok = {'lines': [self.line([100, 200, 880, 60])], 'marks': [[780, 1240, 220, 26]], 'slots': []}
        self.assertEqual(kits.layout_errors(1080, 1350, ok), [])
        out = {'lines': [self.line([40, 200, 300, 60])], 'marks': [[780, 1290, 220, 40]], 'slots': []}
        self.assertEqual(len(kits.layout_errors(1080, 1350, out)), 2)

    def test_a_centred_line_sits_on_the_centre_line(self):
        self.assertEqual(kits.layout_errors(1080, 1350, {'lines': [self.line([240, 500, 600, 60], True)]}), [])
        found = kits.layout_errors(1080, 1350, {'lines': [self.line([98, 500, 600, 60], True)]})
        self.assertEqual(found, ['a centred line sits -142 px off the centre line'])

    def test_a_tall_frame_keeps_everything_in_the_clear_box(self):
        # The POV meme's measured group: headline x 122 to 867 from y 308, the credit to x 874 at y 1257.
        meme = {'lines': [self.line([122, 308, 745, 164]), self.line([256, 1235, 618, 22])],
                'marks': [[560, 1176, 319, 37]], 'slots': [[114, 571, 771, 564]]}
        found = kits.layout_errors(1080, 1920, meme)
        self.assertTrue(any('media slot' in e for e in found), found)
        self.assertTrue(any('clear box' in e or 'rail' in e for e in found), found)
        # The old 250/340 safe area put words at y 1500, under Instagram's caption.
        self.assertTrue(kits.layout_errors(1080, 1920, {'lines': [self.line([200, 1500, 680, 60])]}))
        centred = {'lines': [self.line([240, 400, 600, 120], True)], 'marks': [[420, 1256, 240, 28]],
                   'slots': [[200, 600, 680, 640]]}
        self.assertEqual(kits.layout_errors(1080, 1920, centred), [])

    def test_no_layout_is_an_error(self):
        self.assertEqual(kits.layout_errors(1080, 1350, None), ['no layout reported (render with the current renderer)'])

    def test_a_cover_drawn_like_its_body_cards_is_refused(self):
        manifest = {'templates': {'x-cover': {'width': 1080, 'height': 1350},
                                  'x-detail': {'width': 1080, 'height': 1350}}}
        same = '<style>.frame { gap: 1px; }</style>'
        self.assertTrue(kits.cover_errors(manifest, {'x-cover': same, 'x-detail': same}))
        self.assertEqual(kits.cover_errors(manifest, {'x-cover': '<style>.a{}</style>', 'x-detail': same}), [])
        no_cover = {'templates': {'x-one': {'width': 1080, 'height': 1350}}}
        self.assertTrue(kits.cover_errors(no_cover, {'x-one': same}))
        self.assertEqual(kits.cover_errors({'templates': {'t': {'width': 1080, 'height': 1920}}}, {}), [])


class JudgesSeeTheCards(unittest.TestCase):
    class Board:
        def __init__(self):
            self.bodies = []

        def judge(self, monday, body):
            self.bodies.append(body)
            return {'verdict': 'pass', 'artifact_sha256': judges.artifact_sha256(
                {'format': body['format'], 'channel': body['channel']}, body['words'], body['assets'])}

    def test_every_picture_goes_with_its_view_link_and_a_blind_ask_holds(self):
        slot = {'slot_id': 's1', 'format': 'carousel', 'channel': 'instagram'}
        assets = [{'name': 'mock-1.png', 'sha256': 'a' * 64, 'view_url': 'https://drive.example.invalid/1'}]
        board = self.Board()
        judges.judge(board, '2026-11-16', slot, {}, 'Synthetic words.', assets)
        self.assertEqual(board.bodies[0]['assets'][0]['view_url'], 'https://drive.example.invalid/1')
        with self.assertRaisesRegex(judges.JudgesHeld, 'judges_cannot_see'):
            judges.judge(board, '2026-11-16', slot, {}, 'Synthetic words.', [{'name': 'm.png', 'sha256': 'a' * 64}])
        self.assertEqual(len(board.bodies), 1, 'a blind ask is never sent')



class TallMemeTests(unittest.TestCase):
    def test_every_clip_shape_lands_centred_in_the_clear_box(self):
        for size in ((1920, 1080), (1080, 1920), (1080, 1080), (1280, 1024)):
            box = tall_meme.placement(*size)
            self.assertEqual(tall_meme.placement_errors(box), [], (size, box))
            self.assertEqual(box[0] + box[2] / 2, 540, size)
        # The hand-made POV meme's clip frame: 40 px left and 107 px high.
        self.assertEqual(tall_meme.placement_errors([114, 571, 771, 564]), ['clip_off_centre', 'clip_outside_clear_box'])

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg is not installed')
    def test_compose_puts_the_clip_in_the_window(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        frame, clip, out = tmp / 'frame.png', tmp / 'clip.mp4', tmp / 'out.mp4'
        run = lambda *a: subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + list(a), check=True)
        run('-f', 'lavfi', '-i', 'color=c=0x0C1512:s=1080x1920', '-frames:v', '1', str(frame))
        run('-f', 'lavfi', '-i', 'color=c=0xF0E6C8:s=640x360:rate=30', '-t', '1', '-pix_fmt', 'yuv420p', str(clip))
        result = tall_meme.compose(frame, clip, out)
        self.assertEqual(result['box'], [200, 729, 680, 382])
        raw = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(out), '-frames:v', '1',
                              '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
        at = lambda x, y: raw[y * 1080 + x]
        self.assertGreater(at(540, 920), 180, 'the clip fills the centre of the window')
        self.assertLess(at(540, 700), 60, 'the ground shows above the fitted clip')
        self.assertLess(at(150, 920), 60, 'nothing spills left of the window')


if __name__ == '__main__':
    unittest.main()
