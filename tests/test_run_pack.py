"""Session packs, docs/RUN.md and Codex task cards, on synthetic fixtures only."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.core import write_json
from engine.packs import EM_DASH, PERCENT
from engine.run.cards import card_errors
from engine.run.cards import main as card_main
from engine.run.pack import MAX_BYTES, compile_pack
from engine.run.pack import main as pack_main
from engine.run.spec import computed

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'specs' / 'fixtures'
RECORDS = json.loads((FIXTURES / 'social-records.json').read_text(encoding='utf-8'))


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def card_bytes(**changes):
    card = fixture('task-card')
    card.update(changes)
    return json.dumps(card, indent=2).encode('utf-8')


class RunPackTests(unittest.TestCase):
    def setUp(self):
        # A synthetic root: the real RUN.md and ladder, and a crew of our own.
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('docs/RUN.md', 'docs/NORTH_STAR.md'):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / name), str(self.root / name))
        self.runs = str(self.root / 'runs')

    def tearDown(self):
        self.temp.cleanup()

    def pack(self, spec, day=None, channel=None):
        return compile_pack(spec, day, channel, self.runs, self.root, RECORDS)

    def test_pack_holds_doc_slice_findings_and_status(self):
        text = self.pack(fixture('w45-week'), day='2026-11-02', channel='substack-notes')
        self.assertLessEqual(len(text.encode('utf-8')), MAX_BYTES)
        self.assertIn('# Run sessions', text)
        self.assertIn('w45-mon-note-1', text)
        self.assertIn('w45-mon-note-2', text)
        self.assertNotIn('w45-tue-note-1', text, 'another day is not in the slice')
        self.assertNotIn('w45-mon-threads-1', text, 'another channel is not in the slice')
        self.assertIn('crew/registry.json is not built yet', text, 'a missing crew is a finding, not a failure')
        self.assertIn('"stage": "drafted"', text)

    def test_pack_loads_only_the_crew_in_play(self):
        crew = self.root / 'crew'
        for cid in ('substack', 'threads', 'release-gate'):
            (crew / cid).mkdir(parents=True)
            (crew / cid / 'card.md').write_text('CARD ' + cid + '\n', encoding='utf-8')
        write_json(crew / 'registry.json', {'crew': [
            {'id': 'substack', 'channels': ['substack-notes']},
            {'id': 'threads', 'channels': ['threads']},
            {'id': 'release-gate', 'always': True},
            {'id': 'meta', 'channels': ['instagram']}]})
        text = self.pack(fixture('w45-week'), channel='substack-notes')
        self.assertIn('CARD substack', text)
        self.assertIn('CARD release-gate', text)
        self.assertNotIn('CARD threads', text)
        whole = self.pack(fixture('w45-week'))
        self.assertIn('CARD threads', whole)
        # Meta has no card file: looking it up would add a finding. Out of play, it is never looked up.
        self.assertNotIn('card for meta', whole)
        (crew / 'threads' / 'card.md').write_text('x' * (3 * 1024 + 1), encoding='utf-8')
        self.assertIn('card for threads is over 3 KB; not loaded', self.pack(fixture('w45-week')))

    def test_pack_refuses_over_36kb(self):
        spec = fixture('w45-week')
        spec['slots'][0]['words'] = 'TEST FIXTURE ONLY. A long synthetic Note line. ' * 900
        spec = computed(spec)
        with self.assertRaisesRegex(ValueError, 'the limit is 36864'):
            self.pack(spec)
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as out:
            path = Path(folder) / 'spec.json'
            out_path = Path(folder) / 'pack.md'
            write_json(path, spec)
            self.assertEqual(pack_main(['pack', str(path), '--out', str(out_path)]), 1)
            self.assertFalse(out_path.exists(), 'nothing is written when the pack is refused')
        self.assertIn('the limit is 36864', out.getvalue())
        narrowed = self.pack(spec, channel='threads')
        self.assertLessEqual(len(narrowed.encode('utf-8')), MAX_BYTES, 'narrowing brings it back under')

    def test_run_doc_is_small_and_house_clean(self):
        raw = (ROOT / 'docs' / 'RUN.md').read_bytes()
        self.assertLessEqual(len(raw), 8 * 1024)
        text = raw.decode('utf-8')
        self.assertFalse(EM_DASH.search(text))
        self.assertFalse(PERCENT.search(text))
        for command in ('run new', 'run lint', 'run status', 'run pack', 'run card lint', 'ASSET-STORAGE',
                        'invariants/rules.json', '4 Growth'):
            self.assertIn(command, text)


class TaskCardTests(unittest.TestCase):
    def test_card_lint_refuses_unpinned_model_and_oversize(self):
        self.assertEqual(card_errors((FIXTURES / 'task-card.json').read_bytes()), [])
        for model in ('', '   ', 'latest', 'gpt-latest', 'default', 'auto'):
            self.assertIn('model_unpinned', {e['code'] for e in card_errors(card_bytes(model=model))}, model)
        for effort in ('', 'auto', 'max'):
            self.assertIn('effort_unpinned', {e['code'] for e in card_errors(card_bytes(effort=effort))}, effort)
        big = card_bytes(interface='def example(value): ' + 'x' * (6 * 1024))
        self.assertGreater(len(big), 6 * 1024)
        self.assertEqual({e['code'] for e in card_errors(big)}, {'oversize'})
        self.assertEqual({e['code'] for e in card_errors(card_bytes(read_files=['f%d.py' % i for i in range(6)]))},
                         {'read_files'})
        never = [x for x in fixture('task-card')['never'] if x != 'git']
        self.assertEqual({e['code'] for e in card_errors(card_bytes(never=never))}, {'never_list'})
        for allow in (['*'], ['**'], ['../other/*.py'], ['/etc/x'], ['C:\\x\\y.py']):
            self.assertEqual({e['code'] for e in card_errors(card_bytes(write_allow=allow))}, {'write_allow'}, allow)
        self.assertEqual({e['code'] for e in card_errors(card_bytes(write_allow=[]))}, {'schema'})
        self.assertEqual({e['code'] for e in card_errors(card_bytes(return_shape={}))}, {'return_shape'})
        self.assertEqual({e['code'] for e in card_errors(card_bytes(worktree={'path': '.', 'branch': 'main'}))}, {'worktree'})
        self.assertEqual({e['code'] for e in card_errors(card_bytes(extra='x'))}, {'schema'})
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            path = Path(folder) / 'card.json'
            path.write_bytes(card_bytes(model='latest'))
            self.assertEqual(card_main(['card', 'lint', str(path)]), 1)
            path.write_bytes(card_bytes())
            self.assertEqual(card_main(['card', 'lint', str(path)]), 0)


if __name__ == '__main__':
    unittest.main()
