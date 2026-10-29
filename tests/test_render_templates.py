"""The mock templates in render/: present, in the kit's colours and fonts only, no em dashes, plain placeholders.

Most of this file is static and stdlib only. RendersInChromium is the one class that runs
scripts/render_mocks.mjs (Node and Playwright's Chromium) as a separate process, and it skips when
either is missing; neither the engine nor this test imports the renderer.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
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
# The ten kit templates (the carousel is three pages and the poll two), then the four drawn from the
# published artwork in render/KIT.md: versus, number and chapter cards in two sizes each, and the evidence card.
TEN = {'quote-card': (1080, 1350), 'receipt-card': (1600, 900), 'scorecard': (1080, 1350),
       'poll-question': (1080, 1350), 'poll-result': (1080, 1350), 'carousel-cover': (1080, 1350),
       'carousel-body': (1080, 1350), 'carousel-close': (1080, 1350), 'story-frame': (1080, 1920),
       'meme-square': (1080, 1080), 'meme-vertical': (1080, 1920), 'profile-art': (1080, 1080)}
FROM_THE_ARTWORK = {'versus-card': (1200, 675), 'versus-card-tall': (1080, 1350), 'number-card': (1314, 1080),
                    'number-card-tall': (1080, 1350), 'chapter-card': (1920, 1080),
                    'chapter-card-vertical': (1080, 1920), 'evidence-card': (1280, 820)}
TEMPLATES = {**TEN, **FROM_THE_ARTWORK}
# Every page that carries the wordmark, and the pages that keep the old label, rule and footer.
WORDMARK = {'carousel-cover', 'story-frame', 'quote-card', 'receipt-card', 'meme-square', 'meme-vertical',
            'versus-card', 'versus-card-tall', 'evidence-card'}
WITH_RULE = {'quote-card', 'receipt-card', 'carousel-body', 'carousel-close', 'meme-square', 'meme-vertical', 'profile-art'}
TONES = ['butter', 'mint', 'coral']
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
    for name in ('plain_errors', 'errors', 'lint', 'lint_text'):
        if callable(getattr(plain, name, None)):
            return getattr(plain, name)
    raise AssertionError('engine/run/plain.py exists but names no plain_errors, errors or lint; update this test')


class TemplatesExist(unittest.TestCase):
    def test_every_template_at_its_size(self):
        templates = manifest()['templates']
        self.assertEqual(set(templates), set(TEMPLATES))
        for tid, (w, h) in TEMPLATES.items():
            spec = templates[tid]
            self.assertEqual((spec['width'], spec['height']), (w, h), tid)
            self.assertEqual(spec['file'], 'templates/%s.html' % tid)
            text = template_text(spec)
            self.assertIn('--w: %dpx' % w, text, tid)
            self.assertIn('--h: %dpx' % h, text, tid)
            self.assertIn('href="../kit.css"', text, tid)
            self.assertIn('src="../fit.js"', text, tid)

    def test_vertical_frames_keep_the_safe_zones_clear(self):
        for tid in ('story-frame', 'meme-vertical', 'chapter-card-vertical'):
            spec = manifest()['templates'][tid]
            self.assertEqual(spec['safe'], {'top': 250, 'bottom': 340})
            text = template_text(spec)
            self.assertIn('--top: 250px', text)
            self.assertIn('--bottom: 340px', text)

    def test_the_older_pages_keep_the_footer_label_and_rule(self):
        for tid in TEN:
            text = template_text(manifest()['templates'][tid])
            if tid != 'profile-art':
                self.assertIn('makeyourmindup.ai', text, tid)
                self.assertIn('class="label"', text, tid)
            if tid in WITH_RULE:
                self.assertIn('class="rule"', text, tid)

    def test_the_wordmark_is_built_from_the_kit_on_every_cover(self):
        for tid, spec in manifest()['templates'].items():
            text = template_text(spec)
            has = '<span class="words">MAKE YOUR MIND/</span><span class="up">UP</span>' in text
            self.assertEqual(has, tid in WORDMARK, tid)
            if has:
                self.assertIn('<span class="mark"><i></i><i></i><i></i></span>', text, tid)

    def test_a_two_tone_headline_has_one_accent_line(self):
        for tid, spec in manifest()['templates'].items():
            text = template_text(spec)
            if 'class="headline"' in text:
                self.assertEqual(text.count('class="accent"'), 1, tid)
                self.assertIn('tone', spec['fields'], tid)

    def test_choices_name_declared_fields_and_the_three_tones(self):
        for tid, spec in manifest()['templates'].items():
            for name, allowed in spec.get('choices', {}).items():
                self.assertIn(name, spec['fields'], tid)
                self.assertEqual(allowed, TONES, tid)
                self.assertIn('tone-{{tone}}', template_text(spec), tid)
            if 'tone' in spec['fields']:
                self.assertIn('tone', spec.get('choices', {}), tid)

    def test_placeholders_match_the_declared_fields(self):
        for tid, spec in manifest()['templates'].items():
            used = {}
            for kind, name in PLACEHOLDER.findall(template_text(spec)):
                used[name] = kind or 'text'
            self.assertEqual(used, spec['fields'], tid)
            self.assertTrue(set(spec['required']) <= set(spec['fields']), tid)
            self.assertTrue(set(spec['required']) <= set(spec['example']), tid)
            self.assertTrue(set(spec['example']) <= set(spec['fields']), tid)


class NoPersonNoPassports(unittest.TestCase):
    """Growth posts speak as the publication: no photo of anyone, no name of his, and the passports stay untemplated."""

    def test_no_image_of_anyone(self):
        for path, text in style_sources().items():
            self.assertIsNone(re.search(r'<img\b|<picture\b|<image\b|<svg\b', text, re.I), str(path))
            for url in re.findall(r'url\(([^)]*)\)', text):
                self.assertRegex(url.strip("'\""), r'^fonts/[A-Za-z-]+\.ttf$', str(path))

    def test_no_passport_and_no_name_of_his(self):
        for path in list(style_sources()) + [MANIFEST]:
            text = path.read_text(encoding='utf-8').lower()
            self.assertNotIn('passport', text, str(path))
            self.assertNotIn('krish', text, str(path))


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
        files = list(style_sources()) + [MANIFEST, ROOT / 'scripts' / 'render_mocks.mjs', RENDER / 'KIT.md']
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


def png_size(path):
    data = path.read_bytes()[:24]
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise AssertionError(str(path) + ' is not a PNG')
    return struct.unpack('>II', data[16:24])


class RendersInChromium(unittest.TestCase):
    """Every registered template renders from its example at its declared size, the same bytes every time, and
    paints with the kit's colours and fonts only. Two separate runs, each with --verify (which renders twice)."""

    @classmethod
    def setUpClass(cls):
        if shutil.which('node') is None:
            raise unittest.SkipTest('Node is not installed here')
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        jobs = [{'template': tid, 'fields': spec['example'], 'out': tid + '.png'}
                for tid, spec in manifest()['templates'].items()]
        (base / 'jobs.json').write_text(json.dumps(jobs), encoding='utf-8')
        cls.runs = []
        for run in ('first', 'second'):
            proc = subprocess.run(['node', str(ROOT / 'scripts' / 'render_mocks.mjs'), str(base / 'jobs.json'),
                                   '--out-dir', str(base / run), '--verify'],
                                  capture_output=True, text=True, timeout=600, cwd=str(ROOT))
            if proc.returncode and re.search(r"Playwright is not available|Executable doesn't exist|browserType\.launch",
                                             proc.stderr):
                cls.tmp.cleanup()
                raise unittest.SkipTest('Playwright or its Chromium is not available here: ' + proc.stderr.strip()[:200])
            if proc.returncode:
                cls.tmp.cleanup()
                raise AssertionError('render_mocks failed: ' + proc.stderr.strip())
            cls.runs.append((base / run, {r['out']: r for r in json.loads(proc.stdout)}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_template_renders_at_its_declared_size(self):
        templates = manifest()['templates']
        folder, results = self.runs[0]
        self.assertEqual({r['template'] for r in results.values()}, set(templates))
        for tid, spec in templates.items():
            self.assertEqual(png_size(folder / (tid + '.png')), (spec['width'], spec['height']), tid)

    def test_two_runs_give_the_same_bytes(self):
        (first, a), (second, b) = self.runs
        for out in a:
            one, two = (first / out).read_bytes(), (second / out).read_bytes()
            self.assertEqual(hashlib.sha256(one).hexdigest(), a[out]['sha256'], out)
            self.assertEqual(one, two, out)

    def test_only_kit_colours_and_fonts_are_painted(self):
        for out, result in self.runs[0][1].items():
            self.assertTrue(result['colours'], out)
            self.assertLessEqual(set(result['colours']), KIT_COLOURS, out)
            self.assertTrue(result['fonts'], out)
            self.assertLessEqual(set(result['fonts']), KIT_FONTS, out)


class OutsideTheEngine(unittest.TestCase):
    def test_the_engine_never_imports_the_renderer(self):
        for path in list((ROOT / 'engine').rglob('*.py')) + [ROOT / 'growth.py']:
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('render_mocks', text, str(path))
            self.assertNotIn('playwright', text.lower(), str(path))


if __name__ == '__main__':
    unittest.main()
