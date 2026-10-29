"""The mock templates in render/: present, in the kit's colours and fonts only, no em dashes, plain placeholders.

Static and stdlib only: nothing here starts a browser. scripts/render_mocks.mjs is the one
non-stdlib piece (Node and Playwright's Chromium), and neither the engine nor this test imports it.
"""
import importlib.util
import json
from pathlib import Path
import re
import unittest

from engine.copy_lint import copy_lint_errors
from engine.packs import prose_errors

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'render'
MANIFEST = RENDER / 'templates.json'
KIT_COLOURS = {'#0C1512', '#070D0B', '#F4EFE4', '#2F6B5C', '#7EF0C0', '#FFD84D', '#FF6A4D', '#B7A6FF'}
KIT_FONTS = {'Anton', 'Fraunces', 'Archivo', 'IBM Plex Mono'}
GENERIC_FONTS = {'serif', 'sans-serif', 'monospace'}
FONT_FILES = {'Anton': ['Anton-Regular.ttf'], 'Fraunces': ['Fraunces-Variable.ttf'], 'Archivo': ['Archivo-Variable.ttf'],
              'IBM Plex Mono': ['IBMPlexMono-Regular.ttf', 'IBMPlexMono-Medium.ttf']}
LICENCES = {'Anton': 'Anton-OFL.txt', 'Fraunces': 'Fraunces-OFL.txt', 'Archivo': 'Archivo-OFL.txt',
            'IBM Plex Mono': 'IBMPlexMono-OFL.txt'}
# The ten kit templates; the carousel is three pages and the poll two.
TEN = {'quote-card': (1080, 1350), 'receipt-card': (1600, 900), 'scorecard': (1080, 1350),
       'poll-question': (1080, 1350), 'poll-result': (1080, 1350), 'carousel-cover': (1080, 1350),
       'carousel-body': (1080, 1350), 'carousel-close': (1080, 1350), 'story-frame': (1080, 1920),
       'meme-square': (1080, 1080), 'meme-vertical': (1080, 1920), 'profile-art': (1080, 1080)}
PLACEHOLDER = re.compile(r'\{\{(?:(rows|options):)?([a-z0-9_]+)\}\}')
HEX = re.compile(r'#[0-9A-Fa-f]{3,8}\b')


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def template_text(spec):
    return (RENDER / spec['file']).read_text(encoding='utf-8')


def style_sources():
    """Every file that can style a mock: the kit stylesheet, the fit script and each template."""
    files = [RENDER / 'kit.css', RENDER / 'fit.js'] + sorted((RENDER / 'templates').glob('*.html'))
    return {f: f.read_text(encoding='utf-8') for f in files}


def example_strings(value):
    if isinstance(value, list):
        return [s for item in value for s in example_strings(item)]
    return [str(value)]


def plain_lint():
    """engine/run/plain.py's plain-English check when that module exists, else None."""
    if importlib.util.find_spec('engine.run.plain') is None:
        return None
    from engine.run import plain
    for name in ('plain_errors', 'errors', 'lint'):
        if callable(getattr(plain, name, None)):
            return getattr(plain, name)
    raise AssertionError('engine/run/plain.py exists but names no plain_errors, errors or lint; update this test')


class TemplatesExist(unittest.TestCase):
    def test_the_ten_kit_templates_at_their_sizes(self):
        templates = manifest()['templates']
        self.assertEqual(set(templates), set(TEN))
        for tid, (w, h) in TEN.items():
            spec = templates[tid]
            self.assertEqual((spec['width'], spec['height']), (w, h), tid)
            text = template_text(spec)
            self.assertIn('--w: %dpx' % w, text, tid)
            self.assertIn('--h: %dpx' % h, text, tid)
            self.assertIn('href="../kit.css"', text, tid)
            self.assertIn('src="../fit.js"', text, tid)

    def test_vertical_frames_keep_the_safe_zones_clear(self):
        for tid in ('story-frame', 'meme-vertical'):
            spec = manifest()['templates'][tid]
            self.assertEqual(spec['safe'], {'top': 250, 'bottom': 340})
            text = template_text(spec)
            self.assertIn('--top: 250px', text)
            self.assertIn('--bottom: 340px', text)

    def test_every_page_carries_the_footer_and_the_rule_except_profile_art(self):
        for tid, spec in manifest()['templates'].items():
            text = template_text(spec)
            if tid != 'profile-art':
                self.assertIn('makeyourmindup.ai', text, tid)
                self.assertIn('class="label"', text, tid)
            self.assertIn('rule', text, tid)

    def test_placeholders_match_the_declared_fields(self):
        for tid, spec in manifest()['templates'].items():
            used = {}
            for kind, name in PLACEHOLDER.findall(template_text(spec)):
                used[name] = kind or 'text'
            self.assertEqual(used, spec['fields'], tid)
            self.assertTrue(set(spec['required']) <= set(spec['fields']), tid)
            self.assertTrue(set(spec['required']) <= set(spec['example']), tid)
            self.assertTrue(set(spec['example']) <= set(spec['fields']), tid)


class KitOnly(unittest.TestCase):
    def test_only_kit_colours(self):
        declared = {v.upper() for v in manifest()['kit']['colours'].values()}
        self.assertEqual(declared, KIT_COLOURS)
        for path, text in style_sources().items():
            for colour in HEX.findall(text):
                self.assertIn(colour.upper(), KIT_COLOURS, str(path))
            self.assertIsNone(re.search(r'\b(?:rgba?|hsla?)\(', text), str(path) + ' uses a colour function')
            for word in re.findall(r'(?:color|background(?:-color)?|border(?:-[a-z]+)?)\s*:\s*([^;]+);', text):
                for token in re.findall(r'\b[a-z]+\b', re.sub(r'var\([^)]*\)', '', word)):
                    self.assertNotIn(token, {'white', 'black', 'red', 'blue', 'green', 'grey', 'gray', 'yellow',
                                             'orange', 'purple', 'pink'}, str(path) + ': named colour ' + token)

    def test_only_kit_fonts_and_they_are_vendored_with_licences(self):
        css = (RENDER / 'kit.css').read_text(encoding='utf-8')
        faces = re.findall(r"@font-face\s*\{[^}]*font-family:\s*'([^']+)'[^}]*src:\s*url\('([^']+)'\)", css)
        self.assertEqual({f for f, _ in faces}, KIT_FONTS)
        for family, src in faces:
            self.assertTrue((RENDER / src).is_file(), src)
            self.assertIn(Path(src).name, FONT_FILES[family])
        for family, files in FONT_FILES.items():
            for name in files:
                self.assertTrue((RENDER / 'fonts' / name).is_file(), name)
            licence = (RENDER / 'fonts' / LICENCES[family]).read_text(encoding='utf-8')
            self.assertIn('SIL OPEN FONT LICENSE', licence.upper(), family)
        for path, text in style_sources().items():
            for decl in re.findall(r'font-family\s*:\s*([^;]+);', text):
                for name in [n.strip().strip("'\"") for n in decl.split(',')]:
                    if name.startswith('var('):
                        continue
                    self.assertIn(name, KIT_FONTS | GENERIC_FONTS, str(path))
        self.assertIsNone(re.search(r'fonts\.googleapis|fonts\.gstatic|https?://', css), 'fonts load offline only')

    def test_no_em_dashes(self):
        files = list(style_sources()) + [MANIFEST, ROOT / 'scripts' / 'render_mocks.mjs']
        for path in files:
            self.assertNotIn('\u2014', path.read_text(encoding='utf-8'), str(path))

    def test_words_never_run_together(self):
        css = (RENDER / 'kit.css').read_text(encoding='utf-8')
        self.assertIn('word-spacing: normal', css)
        self.assertIn('hyphens: none', css)
        self.assertIsNone(re.search(r'word-spacing:\s*-|letter-spacing:\s*-|word-break:\s*break-all', css))


class Placeholders(unittest.TestCase):
    """Every carousel and caption placeholder is plain: copy lint, the prose rules and, if present, plain.py."""

    def test_placeholders_pass_the_lints(self):
        plain = plain_lint()
        for tid, spec in manifest()['templates'].items():
            for field, value in spec['example'].items():
                for text in example_strings(value):
                    where = tid + '.' + field + ': ' + text
                    self.assertEqual(copy_lint_errors(text, 'carousel_text'), [], where)
                    self.assertEqual(copy_lint_errors(text, 'channel_copy'), [], where)
                    self.assertEqual(prose_errors(text), [], where)
                    self.assertNotIn('\u2014', text, where)
                    if plain is not None:
                        self.assertFalse(plain(text), where)

    def test_placeholders_hold_no_real_words(self):
        # A placeholder describes its slot; real ideas, claims and mocks stay out of this public repository.
        for tid, spec in manifest()['templates'].items():
            for text in example_strings(spec['example'].get('quote', '')) + example_strings(spec['example'].get('body', '')):
                self.assertNotRegex(text, r'\d{4}', tid)


class OutsideTheEngine(unittest.TestCase):
    def test_the_engine_never_imports_the_renderer(self):
        for path in list((ROOT / 'engine').rglob('*.py')) + [ROOT / 'growth.py']:
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('render_mocks', text, str(path))
            self.assertNotIn('playwright', text.lower(), str(path))


if __name__ == '__main__':
    unittest.main()
