"""Piece kits (render/pieces/<piece_id>/): one visual idea per piece, held to the house kit (Krish, 29 Oct 2026).

Every kit renders the same bytes twice, paints only kit colours and fonts, carries no picture of anyone,
reaches nothing remote (fonts only from render/fonts) and has no em dash. Each check is shown to fail on a
planted kit: an off-kit colour, a remote font and an <img>. Then the commands a Codex card's acceptance runs
(engine/run/kit_checks.py), and the route: a kit is built only in a Claude session, with the Codex plugin building it
(Ruling, Krish, 2026-11-13), so no workflow here runs Codex or the renderer, and the art-direction run is gone.

Static checks are stdlib only. The classes that render run scripts/render_mocks.mjs as a separate process
and skip when Node or Playwright's Chromium is missing; the engine never runs the renderer itself.
Synthetic fixtures only: this repository is public.
"""
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from engine.run import kits as kit_checks
from engine.run.cli import ROUTES

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'render'
PIECES = RENDER / 'pieces'
EXAMPLE = PIECES / 'synthetic-receipt-tape'
KIT_COLOURS = {'#0C1512', '#070D0B', '#F4EFE4', '#2F6B5C', '#7EF0C0', '#FFD84D', '#FF6A4D', '#B7A6FF'}
KIT_FONTS = {'Anton', 'Fraunces', 'Archivo', 'IBM Plex Mono'}
OFF_KIT = '#123456'
REMOTE_FONT = ("@font-face { font-family: 'Remote Sans'; src: url('https://fonts.example.invalid/remote.woff2'); }\n"
               ".tape .headline { font-family: 'Remote Sans'; }\n")
IMG = '<img class="face" src="person.png" alt="">'


def kits():
    return sorted(p for p in PIECES.iterdir() if p.is_dir()) if PIECES.is_dir() else []


def copy_kit(folder, name='synthetic-planted'):
    target = Path(folder) / name
    shutil.copytree(str(EXAMPLE), str(target))
    data = json.loads((target / 'templates.json').read_text(encoding='utf-8'))
    data['piece_id'] = name
    (target / 'templates.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    return target


def plant(kit, kind):
    """Put one defect into a copied kit, past the static checks, as a careless or hostile author would."""
    first = sorted((kit / 'templates').glob('*.html'))[0]
    if kind == 'colour':
        css = kit / 'piece.css'
        css.write_text(css.read_text(encoding='utf-8') + '\n.tape { color: ' + OFF_KIT + '; }\n', encoding='utf-8')
    elif kind == 'font':
        css = kit / 'piece.css'
        css.write_text(REMOTE_FONT + css.read_text(encoding='utf-8'), encoding='utf-8')
    elif kind == 'img':
        html = first.read_text(encoding='utf-8')
        first.write_text(html.replace('<div class="slot"></div>', '<div class="slot"></div>' + IMG, 1), encoding='utf-8')
    elif kind == 'em_dash':
        data = json.loads((kit / 'templates.json').read_text(encoding='utf-8'))
        spec = next(iter(data['templates'].values()))
        spec['example']['label'] = 'series — label'
        (kit / 'templates.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return kit


def renderer_available():
    return shutil.which('node') is not None


def render(jobs, folder, pieces_dir, verify=True):
    """(exit code, results, stderr) of one render_mocks run; raises SkipTest without Playwright's Chromium."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'jobs.json').write_text(json.dumps(jobs), encoding='utf-8')
    cmd = ['node', str(ROOT / 'scripts' / 'render_mocks.mjs'), str(folder / 'jobs.json'), '--out-dir', str(folder),
           '--pieces', str(pieces_dir)] + (['--verify'] if verify else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    if proc.returncode and re.search(r"Playwright is not available|Executable doesn't exist|browserType\.launch",
                                     proc.stderr):
        raise unittest.SkipTest('Playwright or its Chromium is not available here: ' + proc.stderr.strip()[:200])
    return proc.returncode, (json.loads(proc.stdout) if proc.returncode == 0 else []), proc.stderr


class TheExampleKit(unittest.TestCase):
    def test_there_is_one_synthetic_example_and_every_kit_passes_the_static_checks(self):
        self.assertTrue(EXAMPLE.is_dir())
        self.assertIn('synthetic', (EXAMPLE / 'idea.md').read_text(encoding='utf-8').lower())
        self.assertTrue(kits())
        for kit in kits():
            self.assertEqual(kit_checks.kit_errors(kit), [], kit.name)

    def test_the_contract_files(self):
        for kit in kits():
            names = sorted(p.relative_to(kit).as_posix() for p in kit.rglob('*') if p.is_file())
            self.assertEqual([n for n in names if not n.startswith('templates/')], ['idea.md', 'piece.css',
                                                                                    'templates.json'], kit.name)
            data = json.loads((kit / 'templates.json').read_text(encoding='utf-8'))
            self.assertEqual((data['schema_version'], data['kind'], data['piece_id']), (1, 'piece_kit', kit.name))
            self.assertEqual(sorted('templates/' + t + '.html' for t in data['templates']),
                             [n for n in names if n.startswith('templates/')])
            idea = (kit / 'idea.md').read_text(encoding='utf-8').strip()
            self.assertNotIn('\n\n', idea)

    def test_the_route_and_the_rules(self):
        self.assertEqual(ROUTES['kit'], 'kits')
        self.assertNotIn('artdirect', ROUTES)
        rules = kit_checks.RULES.read_text(encoding='utf-8')
        for needle in ('Claude session', 'Codex plugin', 've card', 'passport', 'no person', 'plain English',
                       'var(--ink)', 'piece_kit', "the card's acceptance", 'growth.py run kit check'):
            self.assertIn(needle.lower(), rules.lower(), needle)
        self.assertNotIn('—', rules)
        self.assertNotIn('krish', rules.lower(), 'the brief never names him')
        self.assertNotRegex(rules, r'\{\{(?:piece_id|title|claims|lane)\}\}', 'a card names the piece; the brief has no slots')


class StaticChecksCanFail(unittest.TestCase):
    """Each static check, proved able to find something."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def errors(self, kind):
        return kit_checks.kit_errors(plant(copy_kit(self.tmp.name), kind))

    def test_the_copy_passes_before_anything_is_planted(self):
        self.assertEqual(kit_checks.kit_errors(copy_kit(self.tmp.name)), [])

    def test_an_off_kit_colour(self):
        self.assertTrue(any('hex colour' in e for e in self.errors('colour')))

    def test_a_remote_font(self):
        found = self.errors('font')
        self.assertTrue(any('remote address' in e for e in found), found)
        self.assertTrue(any('at-rule' in e for e in found), found)
        self.assertTrue(any('Remote Sans is not a kit font' in e for e in found), found)

    def test_an_img(self):
        self.assertTrue(any('<img>' in e for e in self.errors('img')))

    def test_an_em_dash(self):
        self.assertTrue(any('em dash' in e for e in self.errors('em_dash')))

    def test_more_ways_off_the_kit(self):
        cases = {'color: rgb(1, 2, 3);': 'colour function', 'color: tomato;': 'named colour tomato',
                 'background: color-mix(in srgb, var(--mint) 50%, var(--coral));': 'colour function',
                 'filter: hue-rotate(40deg);': 'filter is not allowed', '--ink: var(--coral);': 'redefines',
                 'background-image: url(face.png);': 'remote address or url'}
        for decl, needle in cases.items():
            kit = copy_kit(self.tmp.name, 'synthetic-' + hashlib.sha256(decl.encode()).hexdigest()[:8])
            css = kit / 'piece.css'
            css.write_text(css.read_text(encoding='utf-8') + '\n.tape { ' + decl + ' }\n', encoding='utf-8')
            self.assertTrue(any(needle in e for e in kit_checks.kit_errors(kit)), decl)

    def test_the_wordmark_a_person_a_secret_and_a_stray_file(self):
        kit = copy_kit(self.tmp.name, 'synthetic-wordmark')
        css = kit / 'piece.css'
        css.write_text(css.read_text(encoding='utf-8') + '\n.brandmark { opacity: 0.5; }\n', encoding='utf-8')
        self.assertTrue(any('restyles the brand mark' in e for e in kit_checks.kit_errors(kit)))
        # Ruling (Krish, 2026-11-03): "You've fabricated my brand logo." A wordmark set as type is refused.
        kit = copy_kit(self.tmp.name, 'synthetic-drawn')
        page = next((kit / 'templates').glob('*.html'))
        page.write_text(page.read_text(encoding='utf-8').replace('<div class="frame', '<div class="wordmark">MAKE YOUR MIND/</div><div class="frame', 1),
                        encoding='utf-8')
        self.assertTrue(any('a wordmark set as type' in e for e in kit_checks.kit_errors(kit)))
        kit = copy_kit(self.tmp.name, 'synthetic-named')
        (kit / 'idea.md').write_text('A picture of Krish holding a passport, drawn on a till receipt.\n',
                                     encoding='utf-8')
        found = kit_checks.kit_errors(kit)
        self.assertTrue(any('passports idea' in e for e in found) and any('never names anyone' in e for e in found))
        kit = copy_kit(self.tmp.name, 'synthetic-key')
        (kit / 'idea.md').write_text((kit / 'idea.md').read_text(encoding='utf-8').strip() + ' synthetic0key0value\n',
                                     encoding='utf-8')
        self.assertTrue(any('shaped like a key' in e for e in kit_checks.kit_errors(kit, secrets=('synthetic0key0value',))))
        kit = copy_kit(self.tmp.name, 'synthetic-stray')
        (kit / 'face.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        self.assertTrue(any('face.png: a file a kit does not have' in e for e in kit_checks.kit_errors(kit)))

    def test_a_kit_is_never_a_copy(self):
        twin = copy_kit(self.tmp.name, 'synthetic-twin')
        copy_kit(self.tmp.name, 'synthetic-original')
        self.assertTrue(any('another piece kit' in e for e in kit_checks.kit_errors(twin)))
        house = copy_kit(self.tmp.name + '/house', 'synthetic-house')
        shutil.copy(str(RENDER / 'templates' / 'story-frame.html'), str(house / 'templates' / 'tape-cover.html'))
        self.assertTrue(any('a copy of a house template' in e for e in kit_checks.kit_errors(house)))

    def test_the_piece_words_stay_out_of_the_kit(self):
        kit = copy_kit(self.tmp.name)
        piece = {'piece_id': kit.name, 'title': 'For one made-up answer', 'claims': [], 'lane': 'x'}
        self.assertEqual(kit_checks.words_errors(kit, piece), ['the piece\'s title is in the kit; examples are '
                                                              'placeholders'])


class RendersTheSameAndInTheKit(unittest.TestCase):
    """Every committed kit, rendered in two separate runs (each --verify renders twice): same bytes, kit only."""

    @classmethod
    def setUpClass(cls):
        if not renderer_available():
            raise unittest.SkipTest('Node is not installed here')
        cls.tmp = tempfile.TemporaryDirectory()
        jobs = [dict(job, out=kit.name + '/' + job['out']) for kit in kits() for job in kit_checks.render_jobs(kit)]
        cls.runs = []
        for run in ('first', 'second'):
            code, results, err = render(jobs, Path(cls.tmp.name) / run, PIECES)
            if code:
                cls.tmp.cleanup()
                raise AssertionError('render_mocks failed: ' + err.strip())
            cls.runs.append((Path(cls.tmp.name) / run, results))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_byte_identical_twice(self):
        (first, a), (second, b) = self.runs
        self.assertEqual([r['sha256'] for r in a], [r['sha256'] for r in b])
        for r in a:
            self.assertEqual((first / r['out']).read_bytes(), (second / r['out']).read_bytes(), r['out'])

    def test_only_kit_colours_and_fonts_at_the_declared_sizes(self):
        results = self.runs[0][1]
        for kit in kits():
            self.assertEqual(kit_checks.painted_errors(kit, results), [], kit.name)
        for r in results:
            self.assertLessEqual(set(r['colours']), KIT_COLOURS, r['out'])
            self.assertLessEqual(set(r['fonts']), KIT_FONTS, r['out'])


class RenderChecksCanFail(unittest.TestCase):
    """The renderer's own checks, proved able to fail on planted kits the static checks never saw."""

    @classmethod
    def setUpClass(cls):
        if not renderer_available():
            raise unittest.SkipTest('Node is not installed here')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pieces = Path(self.tmp.name) / 'pieces'

    def render_planted(self, kind):
        kit = plant(copy_kit(self.pieces), kind)
        return kit, render(kit_checks.render_jobs(kit), Path(self.tmp.name) / ('out-' + kind), self.pieces,
                           verify=False)

    def test_an_off_kit_colour_is_painted_and_refused(self):
        kit, (code, results, err) = self.render_planted('colour')
        self.assertEqual(code, 0, err)
        self.assertTrue(any(OFF_KIT in r['colours'] for r in results))
        self.assertTrue(any('outside the kit' in e and OFF_KIT in e for e in kit_checks.painted_errors(kit, results)))

    def test_a_remote_font_is_refused(self):
        _, (code, _, err) = self.render_planted('font')
        self.assertNotEqual(code, 0)
        self.assertIn('the page asked for what the renderer refuses', err)

    def test_an_img_is_refused(self):
        _, (code, _, err) = self.render_planted('img')
        self.assertNotEqual(code, 0)
        self.assertIn('person.png', err)

    def test_an_em_dash_is_refused(self):
        _, (code, _, err) = self.render_planted('em_dash')
        self.assertNotEqual(code, 0)
        self.assertIn('em dash', err)

    def test_the_clean_copy_renders(self):
        kit = copy_kit(self.pieces)
        code, results, err = render(kit_checks.render_jobs(kit), Path(self.tmp.name) / 'clean', self.pieces,
                                    verify=False)
        self.assertEqual(code, 0, err)
        self.assertEqual(kit_checks.painted_errors(kit, results), [])


class TheCommands(unittest.TestCase):
    """What a Codex card's acceptance runs, and what the session that verifies it runs again."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pieces = Path(self.tmp.name) / 'pieces'

    def run_main(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kit_checks.main(argv)
        return code, out.getvalue()

    def test_check_command(self):
        code, out = self.run_main(['kit', 'check', str(EXAMPLE)])
        self.assertEqual(code, 0, out)
        self.assertIn('passes the static checks', out)

    def test_check_refuses_the_decks_own_words_in_the_kit(self):
        kit = copy_kit(self.pieces)
        deck = Path(self.tmp.name) / 'deck.json'
        deck.write_text(json.dumps({'schema': 'carousel-deck/1', 'title': 'A synthetic deck',
                                    'cards': [{'headline': 'For one made-up answer'}]}), encoding='utf-8')
        code, out = self.run_main(['kit', 'check', str(kit), '--words', str(deck)])
        self.assertEqual(code, 1, out)
        self.assertIn("the piece's claim is in the kit; examples are placeholders", out)

    def test_jobs_and_painted(self):
        kit = copy_kit(self.pieces)
        jobs = Path(self.tmp.name) / 'jobs.json'
        code, out = self.run_main(['kit', 'jobs', str(kit), '--out', str(jobs)])
        self.assertEqual(code, 0, out)
        written = json.loads(jobs.read_text(encoding='utf-8'))
        self.assertEqual(written, kit_checks.render_jobs(kit))
        spec = json.loads((kit / 'templates.json').read_text(encoding='utf-8'))['templates']
        good = [{'template': j['template'], 'width': spec[j['template'].split('/')[1]]['width'],
                 'height': spec[j['template'].split('/')[1]]['height'], 'colours': ['#0C1512'], 'fonts': ['Anton']}
                for j in written]
        report = Path(self.tmp.name) / 'report.json'
        report.write_text(json.dumps(good), encoding='utf-8')
        self.assertEqual(self.run_main(['kit', 'painted', str(kit), '--report', str(report)])[0], 0)
        good[0]['colours'].append(OFF_KIT)
        report.write_text(json.dumps(good), encoding='utf-8')
        code, out = self.run_main(['kit', 'painted', str(kit), '--report', str(report)])
        self.assertEqual(code, 1)
        self.assertIn(OFF_KIT, out)
        self.assertEqual(self.run_main(['kit', 'painted', str(kit), '--report', str(report) + '.missing'])[0], 1)

    def test_painted_errors_catch_a_colour_a_font_and_a_size(self):
        kit = copy_kit(self.pieces)
        results = [dict(j, width=1080, height=1350, colours=['#0C1512'], fonts=['Anton']) for j in
                   kit_checks.render_jobs(kit)]
        results[0]['colours'].append(OFF_KIT)
        results[1]['fonts'].append('Remote Sans')
        results[2]['height'] = 1350
        found = kit_checks.painted_errors(kit, results)
        self.assertTrue(any(OFF_KIT in e for e in found))
        self.assertTrue(any('Remote Sans' in e for e in found))
        self.assertTrue(any('another size' in e for e in found))


class OnlyInAClaudeSession(unittest.TestCase):
    """Ruling (Krish, 2026-11-13): "all the carousels should now be done in Claude, but using the Codex plug in as per
    the other usual workflows"; "memes and Notes images should go the same way". No workflow, cron or runner here makes
    a carousel, a meme or a Notes image: none runs Codex, the renderer or the kit checks, and the art-direction run, its
    Codex runner and its key are gone."""

    HEADLESS = re.compile(r'codex exec|@openai/codex|codex login|OPEN_AI_API_KEY|OPENAI_API_KEY|render_mocks|'
                          r'growth\.py run kit|\bartdirect\b', re.I)

    def test_no_workflow_makes_one(self):
        flows = sorted((ROOT / '.github' / 'workflows').glob('*.yml'))
        self.assertTrue(flows)
        self.assertFalse((ROOT / '.github' / 'workflows' / 'artdirect.yml').exists())
        for flow in flows:
            self.assertIsNone(self.HEADLESS.search(flow.read_text(encoding='utf-8')), flow.name)

    def test_no_runner_or_lane_runs_codex(self):
        source = (ROOT / 'engine' / 'run' / 'kits.py').read_text(encoding='utf-8')
        for gone in ('def make(', 'def run_codex(', 'def codex_command(', 'def gate(', 'subprocess'):
            self.assertNotIn(gone, source, gone)
        lanes = json.loads((ROOT / 'lanes.json').read_text(encoding='utf-8'))
        self.assertNotIn('artdirect', json.dumps(lanes))
        self.assertNotIn('OPEN_AI_API_KEY', json.dumps(lanes))

    def test_memes_and_notes_images_take_the_same_route(self):
        boundary = json.loads((ROOT / 'invariants' / 'boundary.json').read_text(encoding='utf-8'))['owners']
        for name in ('carousel', 'meme', 'note-image'):
            self.assertEqual(boundary[name], 'content-engine', name)
        for name in ('meme', 'note'):
            fmt = json.loads((ROOT / 'social' / 'formats' / (name + '.json')).read_text(encoding='utf-8'))
            self.assertEqual(fmt['production_owner'], 'content-engine', name)
            self.assertIn('CAROUSEL-STANDARD.md', fmt['production_reference'], name)
            checks = ' '.join(fmt['delivery_checks'])
            self.assertIn('Claude session', checks, name)
            self.assertIn('Codex plugin', checks, name)
            self.assertNotIn('Canva', checks, name)


if __name__ == '__main__':
    unittest.main()
