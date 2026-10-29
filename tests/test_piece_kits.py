"""Piece kits (render/pieces/<piece_id>/): one visual idea per piece, held to the house kit (Krish, 29 Oct 2026).

Every kit renders the same bytes twice, paints only kit colours and fonts, carries no picture of anyone,
reaches nothing remote (fonts only from render/fonts) and has no em dash. Each check is shown to fail on a
planted kit: an off-kit colour, a remote font and an <img>. Then engine/run/artdirect.py: Codex through a
stub runner, the spend cap, the token count, and the fall back to the house kit (piece_kit_refused).

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

from engine.run import artdirect
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
            self.assertEqual(artdirect.kit_errors(kit), [], kit.name)

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

    def test_the_route_and_the_prompt(self):
        self.assertEqual(ROUTES['artdirect'], 'artdirect')
        prompt = artdirect.PROMPT.read_text(encoding='utf-8')
        for needle in ('{{piece_id}}', '{{title}}', '{{claims}}', '{{lane}}', 'passport', 'no person', 'plain English',
                       'var(--ink)', 'piece_kit', 'house kit'):
            self.assertIn(needle.lower(), prompt.lower(), needle)
        self.assertNotIn('—', prompt)
        self.assertNotIn('krish', prompt.lower(), 'the prompt never names him')
        filled = artdirect.build_prompt({'piece_id': 'synthetic-a', 'title': 'A synthetic title', 'claims': ['One'],
                                         'lane': 'meme'})
        self.assertNotRegex(filled, r'\{\{(?:piece_id|title|claims|lane)\}\}')
        self.assertIn('{{rows:name}}', filled, 'only the four piece placeholders are filled')


class StaticChecksCanFail(unittest.TestCase):
    """Each static check, proved able to find something."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def errors(self, kind):
        return artdirect.kit_errors(plant(copy_kit(self.tmp.name), kind))

    def test_the_copy_passes_before_anything_is_planted(self):
        self.assertEqual(artdirect.kit_errors(copy_kit(self.tmp.name)), [])

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
            self.assertTrue(any(needle in e for e in artdirect.kit_errors(kit)), decl)

    def test_the_wordmark_a_person_a_secret_and_a_stray_file(self):
        kit = copy_kit(self.tmp.name, 'synthetic-wordmark')
        css = kit / 'piece.css'
        css.write_text(css.read_text(encoding='utf-8') + '\n.wordmark .up { color: var(--coral); }\n', encoding='utf-8')
        self.assertTrue(any('restyles the wordmark' in e for e in artdirect.kit_errors(kit)))
        kit = copy_kit(self.tmp.name, 'synthetic-named')
        (kit / 'idea.md').write_text('A picture of Krish holding a passport, drawn on a till receipt.\n',
                                     encoding='utf-8')
        found = artdirect.kit_errors(kit)
        self.assertTrue(any('passports idea' in e for e in found) and any('never names anyone' in e for e in found))
        kit = copy_kit(self.tmp.name, 'synthetic-key')
        (kit / 'idea.md').write_text((kit / 'idea.md').read_text(encoding='utf-8').strip() + ' synthetic0key0value\n',
                                     encoding='utf-8')
        self.assertTrue(any('shaped like a key' in e for e in artdirect.kit_errors(kit, secrets=('synthetic0key0value',))))
        kit = copy_kit(self.tmp.name, 'synthetic-stray')
        (kit / 'face.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        self.assertTrue(any('face.png: a file a kit does not have' in e for e in artdirect.kit_errors(kit)))

    def test_a_kit_is_never_a_copy(self):
        twin = copy_kit(self.tmp.name, 'synthetic-twin')
        copy_kit(self.tmp.name, 'synthetic-original')
        self.assertTrue(any('another piece kit' in e for e in artdirect.kit_errors(twin)))
        house = copy_kit(self.tmp.name + '/house', 'synthetic-house')
        shutil.copy(str(RENDER / 'templates' / 'story-frame.html'), str(house / 'templates' / 'tape-cover.html'))
        self.assertTrue(any('a copy of a house template' in e for e in artdirect.kit_errors(house)))

    def test_the_piece_words_stay_out_of_the_kit(self):
        kit = copy_kit(self.tmp.name)
        piece = {'piece_id': kit.name, 'title': 'For one made-up answer', 'claims': [], 'lane': 'x'}
        self.assertEqual(artdirect.words_errors(kit, piece), ['the piece\'s title is in the kit; examples are '
                                                              'placeholders'])


class RendersTheSameAndInTheKit(unittest.TestCase):
    """Every committed kit, rendered in two separate runs (each --verify renders twice): same bytes, kit only."""

    @classmethod
    def setUpClass(cls):
        if not renderer_available():
            raise unittest.SkipTest('Node is not installed here')
        cls.tmp = tempfile.TemporaryDirectory()
        jobs = [dict(job, out=kit.name + '/' + job['out']) for kit in kits() for job in artdirect.render_jobs(kit)]
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
            self.assertEqual(artdirect.painted_errors(kit, results), [], kit.name)
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
        return kit, render(artdirect.render_jobs(kit), Path(self.tmp.name) / ('out-' + kind), self.pieces,
                           verify=False)

    def test_an_off_kit_colour_is_painted_and_refused(self):
        kit, (code, results, err) = self.render_planted('colour')
        self.assertEqual(code, 0, err)
        self.assertTrue(any(OFF_KIT in r['colours'] for r in results))
        self.assertTrue(any('outside the kit' in e and OFF_KIT in e for e in artdirect.painted_errors(kit, results)))

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
        code, results, err = render(artdirect.render_jobs(kit), Path(self.tmp.name) / 'clean', self.pieces,
                                    verify=False)
        self.assertEqual(code, 0, err)
        self.assertEqual(artdirect.painted_errors(kit, results), [])


def events(*usages, failed=False):
    lines = [json.dumps({'type': 'thread.started', 'thread_id': 'synthetic'})]
    for u in usages:
        lines.append(json.dumps({'type': 'turn.completed', 'usage': u}))
    if failed:
        lines.append(json.dumps({'type': 'turn.failed', 'error': {'message': 'synthetic'}}))
    return '\n'.join(lines) + '\n'


USAGE = {'input_tokens': 1000, 'cached_input_tokens': 200, 'output_tokens': 300, 'reasoning_output_tokens': 50}


class StubCodex:
    """Stands in for codex exec: writes a kit into the folder it is given (a clean copy, or one with a defect)."""

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = []

    def __call__(self, cmd, prompt, cwd, env):
        self.calls.append({'cmd': cmd, 'prompt': prompt, 'env': env})
        kit = Path(cmd[cmd.index('-C') + 1])
        behaviour = self.behaviours.pop(0)
        if behaviour == 'exit':
            (kit / 'idea.md').write_text('half done', encoding='utf-8')
            return 1, events(USAGE)
        for item in EXAMPLE.rglob('*'):
            target = kit / item.relative_to(EXAMPLE)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(item), str(target))
        data = json.loads((kit / 'templates.json').read_text(encoding='utf-8'))
        data['piece_id'] = kit.name
        (kit / 'templates.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
        # Make each kit its own (the reuse check refuses a byte-for-byte twin of another kit).
        for path in [kit / 'idea.md', kit / 'piece.css'] + sorted((kit / 'templates').glob('*.html')):
            marker = ('\n<!-- ' + kit.name + ' -->\n') if path.suffix == '.html' else (
                '\n/* ' + kit.name + ' */\n' if path.suffix == '.css' else '')
            if marker:
                path.write_text(path.read_text(encoding='utf-8') + marker, encoding='utf-8')
            else:
                path.write_text(path.read_text(encoding='utf-8').strip() + ' It is made for ' + kit.name.replace('-', ' ')
                                + '.\n', encoding='utf-8')
        if behaviour != 'clean':
            plant(kit, behaviour)
        return 0, events(USAGE)


def pieces(n):
    return [{'piece_id': 'synthetic-piece-%d' % i, 'title': 'A synthetic piece number %d' % i,
             'claims': ['A synthetic claim that is never copied into a kit'], 'lane': 'repurposed_carousel'}
            for i in range(1, n + 1)]


class ArtDirectRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pieces = Path(self.tmp.name) / 'pieces'
        self.pieces.mkdir()
        self.out = Path(self.tmp.name) / 'out'

    def make(self, stub, items, **kw):
        return artdirect.make(items, '2026-11-02', self.out, runner=stub, pieces_dir=self.pieces, changes=None,
                              environ={'OPENAI_API_KEY': 'synthetic-not-a-key', 'GITHUB_TOKEN': 'synthetic'}, **kw)

    def test_cap_codes_tokens_and_fall_back(self):
        stub = StubCodex(['clean', 'colour', 'exit'])
        summary = self.make(stub, pieces(5))
        self.assertEqual(len(stub.calls), 3, 'the spend cap stops after --max-pieces')
        rows = {r['piece_id']: r for r in summary['pieces']}
        self.assertEqual(rows['synthetic-piece-1']['kit'], 'awaiting_render')
        self.assertEqual((rows['synthetic-piece-2']['kit'], rows['synthetic-piece-2']['code']), ('house', 'piece_kit_refused'))
        self.assertEqual((rows['synthetic-piece-3']['kit'], rows['synthetic-piece-3']['code']), ('house', 'codex_failed'))
        self.assertEqual([rows['synthetic-piece-%d' % i]['code'] for i in (4, 5)], ['not_attempted_cap'] * 2)
        self.assertTrue((self.pieces / 'synthetic-piece-1').is_dir())
        self.assertFalse((self.pieces / 'synthetic-piece-2').exists(), 'a refused kit is removed')
        self.assertFalse((self.pieces / 'synthetic-piece-3').exists())
        self.assertEqual(summary['codex_tokens'], {k: v * 3 for k, v in USAGE.items()})
        jobs = json.loads((self.out / 'jobs' / 'synthetic-piece-1.json').read_text(encoding='utf-8'))
        self.assertEqual({j['template'].split('/')[0] for j in jobs}, {'piece:synthetic-piece-1'})

    def test_the_codex_command_has_no_network_and_no_inherited_secret(self):
        stub = StubCodex(['clean'])
        self.make(stub, pieces(1))
        call = stub.calls[0]
        cmd = call['cmd']
        self.assertEqual(cmd[:6], ['codex', 'exec', '--json', '--skip-git-repo-check', '-s', 'workspace-write'])
        self.assertEqual(cmd[cmd.index('-C') + 1], str(self.pieces / 'synthetic-piece-1'))
        self.assertEqual(cmd[-1], '-')
        self.assertIn('sandbox_workspace_write.network_access=false', cmd)
        self.assertEqual(set(call['env']), {'OPENAI_API_KEY'})
        self.assertIn('A synthetic piece number 1', call['prompt'])
        self.assertIn('A synthetic claim', call['prompt'])

    def test_a_kit_holding_the_key_or_the_claim_is_refused(self):
        class Leaky(StubCodex):
            def __call__(self, cmd, prompt, cwd, env):
                code, out = super().__call__(cmd, prompt, cwd, env)
                kit = Path(cmd[cmd.index('-C') + 1])
                (kit / 'idea.md').write_text((kit / 'idea.md').read_text(encoding='utf-8').strip() + ' '
                                             + self.extra + '\n', encoding='utf-8')
                return code, out
        stub = Leaky(['clean'])
        stub.extra = 'synthetic-not-a-key'
        row = self.make(stub, pieces(1))['pieces'][0]
        self.assertEqual(row['code'], 'piece_kit_refused')
        self.assertTrue(any('shaped like a key' in r for r in row['reasons']))
        stub = Leaky(['clean'])
        stub.extra = 'A synthetic claim that is never copied into a kit.'
        row = self.make(stub, pieces(2)[1:])['pieces'][0]
        self.assertEqual(row['code'], 'piece_kit_refused')
        self.assertIn("the piece's claim is in the kit; examples are placeholders", row['reasons'])

    def test_an_existing_kit_is_kept_and_not_counted(self):
        copy_kit(self.pieces, 'synthetic-piece-1')
        stub = StubCodex(['clean'])
        summary = self.make(stub, pieces(2), max_pieces=1)
        self.assertEqual([r['code'] for r in summary['pieces']], ['kit_exists', None])
        self.assertEqual(len(stub.calls), 1)

    def test_codex_writing_outside_its_folder_is_refused(self):
        seen = iter([set(), {'engine/core.py'}])
        summary = artdirect.make(pieces(1), '2026-11-02', self.out, runner=StubCodex(['clean']),
                                 pieces_dir=self.pieces, changes=lambda root: next(seen), environ={})
        row = summary['pieces'][0]
        self.assertEqual(row['code'], 'piece_kit_refused')
        self.assertIn('wrote outside its folder', row['reasons'])

    def test_the_gate_holds_the_render_report_and_prints_counts_only(self):
        summary = self.make(StubCodex(['clean', 'clean']), pieces(2))
        self.assertEqual([r['kit'] for r in summary['pieces']], ['awaiting_render'] * 2)
        (self.out / 'rendered').mkdir()
        good = []
        for job in json.loads((self.out / 'jobs' / 'synthetic-piece-1.json').read_text(encoding='utf-8')):
            spec = json.loads((self.pieces / 'synthetic-piece-1' / 'templates.json').read_text(encoding='utf-8'))
            tid = job['template'].split('/')[1]
            good.append({'template': job['template'], 'width': spec['templates'][tid]['width'],
                         'height': spec['templates'][tid]['height'], 'colours': ['#0C1512', '#F4EFE4'],
                         'fonts': ['Anton']})
        (self.out / 'rendered' / 'synthetic-piece-1.json').write_text(json.dumps(good), encoding='utf-8')
        # synthetic-piece-2 has no render report: the renderer refused it.
        gated = artdirect.gate(self.out, self.pieces)
        self.assertEqual([(r['kit'], r['code']) for r in gated['pieces']],
                         [('piece', None), ('house', 'piece_kit_refused')])
        self.assertFalse((self.pieces / 'synthetic-piece-2').exists())
        self.assertEqual((self.out / 'passed.txt').read_text(encoding='utf-8'), 'synthetic-piece-1\n')
        text = '\n'.join(artdirect.summary_lines(gated))
        self.assertNotIn('synthetic-piece', text)
        self.assertNotIn('A synthetic', text)
        self.assertIn('piece_kit_refused 1', text)
        self.assertIn('Codex tokens: 2000 input (400 cached), 600 output (100 reasoning), 2600 in all', text)

    def test_painted_errors_catch_a_colour_a_font_and_a_size(self):
        kit = copy_kit(self.pieces)
        results = [dict(j, width=1080, height=1350, colours=['#0C1512'], fonts=['Anton']) for j in
                   artdirect.render_jobs(kit)]
        results[0]['colours'].append(OFF_KIT)
        results[1]['fonts'].append('Remote Sans')
        results[2]['height'] = 1350
        found = artdirect.painted_errors(kit, results)
        self.assertTrue(any(OFF_KIT in e for e in found))
        self.assertTrue(any('Remote Sans' in e for e in found))
        self.assertTrue(any('another size' in e for e in found))


class TheWeekAndTheCommand(unittest.TestCase):
    def test_pieces_from_the_mix_in_the_order_they_are_due(self):
        mix = {'slots': [{'concept_id': 'carousel-b', 'due_at': '2026-11-02T09:00:00-05:00'},
                         {'concept_id': 'meme-a', 'due_at': '2026-11-03T09:00:00-05:00'},
                         {'concept_id': 'carousel-b', 'due_at': '2026-11-05T09:00:00-05:00'},
                         {'concept_id': None, 'due_at': '2026-11-01T09:00:00-05:00'}],
               'concepts': [{'concept_id': 'meme-a', 'lane': 'meme', 'idea': 'A synthetic meme idea', 'claim': 'X',
                             'piece_id': None},
                            {'concept_id': 'carousel-b', 'lane': 'repurposed_carousel', 'idea': 'A carousel of "T"',
                             'claim': None, 'piece_id': 'piece_b'}]}
        inventory = {'pieces': [{'piece_id': 'piece_b', 'title': 'A synthetic title'}]}
        self.assertEqual(artdirect.pieces_from_mix(mix, inventory),
                         [{'piece_id': 'carousel-b', 'title': 'A synthetic title', 'claims': [],
                           'lane': 'repurposed_carousel'},
                          {'piece_id': 'meme-a', 'title': 'A synthetic meme idea', 'claims': ['X'], 'lane': 'meme'}])

    def test_the_coming_week_from_the_backlog_fixture(self):
        inventory = json.loads((ROOT / 'backlog' / 'fixture.json').read_text(encoding='utf-8'))
        found = artdirect.week_pieces('2026-11-02', inventory)
        self.assertTrue(found)
        for piece in found:
            self.assertIsNone(artdirect.piece_errors(piece), piece)
        self.assertEqual(artdirect.coming_monday('2026-10-31T12:00:00+00:00').isoformat(), '2026-11-02')
        self.assertEqual(artdirect.coming_monday('2026-11-02T15:00:00+00:00').isoformat(), '2026-11-09')
        self.assertEqual(artdirect.week_label('2026-11-02'), '2026-W45')

    def test_check_command(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = artdirect.main(['artdirect', 'check', str(EXAMPLE)])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn('passes the static checks', out.getvalue())


class TheWorkflow(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / '.github' / 'workflows' / 'artdirect.yml').read_text(encoding='utf-8')

    def test_schedule_secret_pin_and_pull_request(self):
        for needle in ("cron: '0 7 * * 6'", 'workflow_dispatch', 'contents: write', 'pull-requests: write',
                       '@openai/codex@0.165.0', 'OPENAI_API_KEY: ${{ secrets.OPEN_AI_API_KEY }}',
                       'python growth.py run artdirect make', 'python growth.py run artdirect gate',
                       'Piece kits for week', '--verify', 'persist-credentials: false'):
            self.assertIn(needle, self.text, needle)
        self.assertEqual(set(re.findall(r'secrets\.([A-Za-z0-9_]+)', self.text)), {'OPEN_AI_API_KEY'})
        self.assertEqual(self.text.count('secrets.OPEN_AI_API_KEY'), 1, 'the key reaches one step only')
        self.assertNotIn('upload-artifact', self.text)
        self.assertNotRegex(self.text, r'gh pr merge|--auto|merge_pull_request')
        self.assertNotIn('—', self.text)


if __name__ == '__main__':
    unittest.main()
