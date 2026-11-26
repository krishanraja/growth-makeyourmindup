"""The production boundary (Ruling, Krish, 2026-11-26): content-engine makes every asset; Growth grows the channel.

His words: "I believe that growth should move all asset production to Content Engine. I see no point in having a
separate repository produce specific assets." invariants/boundary.json assigns every asset kind to content-engine, and
engine/run/invariants.py:check_production_boundary fails the build if a renderer, template, font, image tool or caption
writer comes back. Every file written here is synthetic and lives in a temporary folder.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.run.invariants import ROOT, check_production_boundary, collapse, load_boundary
from engine.social import inventory

# Every asset kind the old split gave Growth (the 26 Oct split, the 27 Oct Canva lane, the 28 Oct derived posts, the
# 13 Nov kit route and the 19 Nov captions), each now content-engine's.
ONCE_GROWTH = ('carousel', 'meme', 'note-image', 'note-text', 'caption', 'title', 'cover', 'thumbnail', 'quote-card',
               'receipt-card', 'scorecard', 'poll-result', 'profile-art', 'highlight-art', 'platform-resize',
               'weekly-edition')


class BoundaryTests(unittest.TestCase):
    def test_every_asset_kind_is_made_by_content_engine(self):
        data = load_boundary()
        self.assertEqual(data['source_file'], 'CHANGES.md')
        self.assertIn(collapse(data['quote']), collapse((ROOT / 'CHANGES.md').read_text(encoding='utf-8')))
        self.assertIn('I believe that growth should move all asset production to Content Engine', data['quote'])
        self.assertEqual(set(data['owners'].values()), {'content-engine'})
        for kind in ONCE_GROWTH:
            self.assertEqual(data['owners'][kind], 'content-engine', kind)
        self.assertIn('posting', data['growth'])
        self.assertIn('edition-placement', data['growth'], 'the weekly edition Substack step stays Growth (PR 144)')
        for name, fmt in inventory()['format'].items():
            self.assertEqual(fmt['production_owner'], 'content-engine', name)

    def test_this_repository_produces_nothing(self):
        self.assertEqual(check_production_boundary(), [])

    def test_the_old_producers_are_gone(self):
        for rel in ('render', 'scripts/render_mocks.mjs', 'engine/run/kits.py', 'engine/run/tall_meme.py',
                    'engine/run/video_cover.py', 'engine/run/canva.py', 'engine/run/plain.py',
                    'engine/run/voice_profile.py', 'crew/canva-studio', 'social/guides/canva.md',
                    'social/brand/kit.json', 'codex/results', 'calendar/mock-briefs'):
            self.assertFalse((ROOT / rel).exists(), rel)
        maker = (ROOT / 'engine' / 'run' / 'maker.py').read_text(encoding='utf-8')
        for gone in ('WRITER_SYSTEM', 'WRITE_SCHEMA', 'def write_words', 'STANDING_SYSTEM', 'voice_profile'):
            self.assertNotIn(gone, maker)

    def test_the_release_gate_for_a_video_cover_stays(self):
        from engine.run import cover_gate
        self.assertTrue(cover_gate.offset_ok(61500))
        self.assertFalse(cover_gate.offset_ok(None))


class RefusalTests(unittest.TestCase):
    """Each kind of production coming back is refused; the dated plan records are not."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / 'invariants').mkdir()
        shutil.copy(ROOT / 'invariants' / 'boundary.json', self.root / 'invariants' / 'boundary.json')

    def write(self, rel, text='synthetic\n'):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def problems(self):
        return check_production_boundary(self.root)

    def test_an_empty_repository_is_clean(self):
        self.assertEqual(self.problems(), [])

    def test_a_renderer_or_kit_coming_back_is_refused(self):
        self.write('render/templates.json', '{}')
        self.write('engine/run/kits.py', 'def kit_errors():\n    return []\n')
        self.write('scripts/render_mocks.mjs', '// synthetic\n')
        found = ' '.join(self.problems())
        for rel in ('render/templates.json', 'engine/run/kits.py', 'scripts/render_mocks.mjs'):
            self.assertIn(rel, found)

    def test_a_template_font_or_design_file_is_refused(self):
        for rel in ('engine/templates/cover.html', 'assets/kit.css', 'fonts/Anton-Regular.ttf', 'fonts/body.woff2',
                    'art/cover.psd'):
            self.write(rel)
        self.assertEqual(len(self.problems()), 5, self.problems())

    def test_a_renderer_import_or_an_image_tool_call_is_refused(self):
        self.write('engine/run/cards_new.py', 'from playwright.sync_api import sync_playwright\n')
        self.write('engine/run/pictures.py', 'import PIL.Image\n')
        self.write('scripts/shot.mjs', "import { chromium } from 'playwright';\n")
        self.write('engine/run/cut.py', "import subprocess\nsubprocess.run(['ffmpeg', '-i', 'a.mp4'])\n")
        found = ' '.join(self.problems())
        for rel in ('cards_new.py', 'pictures.py', 'shot.mjs', 'cut.py'):
            self.assertIn(rel, found)

    def test_a_caption_writer_coming_back_is_refused(self):
        self.write('engine/run/words.py', "WRITER_SYSTEM = 'You write the words of one social post'\n")
        self.assertTrue(any('engine/run/words.py' in p for p in self.problems()))

    def test_the_dated_plan_records_and_the_tests_are_exempt(self):
        self.write('docs/plans/2026-11-25-weekly-edition/dry-run/render_edition.py', 'import PIL\n')
        self.write('docs/plans/2026-11-25-weekly-edition/dry-run/edition.preview.html', '<p>synthetic</p>\n')
        self.write('docs/history/old.html', '<p>synthetic</p>\n')
        self.write('tests/test_synthetic.py', "MARKER = 'WRITER_SYSTEM'\n")
        self.assertEqual(self.problems(), [])

    def test_a_boundary_naming_another_producer_is_refused(self):
        data = json.loads((self.root / 'invariants' / 'boundary.json').read_text(encoding='utf-8'))
        for owner in ('growth-canva', 'growth-copy', 'growth'):
            data['owners']['meme'] = owner
            (self.root / 'invariants' / 'boundary.json').write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'content-engine'):
                load_boundary(self.root)


if __name__ == '__main__':
    unittest.main()
