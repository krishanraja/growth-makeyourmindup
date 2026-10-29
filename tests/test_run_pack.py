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
from engine.run.pack import MAX_BYTES, compile_pack, week_flag
from engine.run.pack import main as pack_main
from engine.run.spec import computed

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'specs' / 'fixtures'
NORTH_STAR = """```yaml north-star-metric
ladder:
  - [2026-11-02, 86]
```
"""
RECORDS = json.loads((FIXTURES / 'social-records.json').read_text(encoding='utf-8'))


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def card_bytes(**changes):
    card = fixture('task-card')
    card.update(changes)
    return json.dumps(card, indent=2).encode('utf-8')


class RunPackTests(unittest.TestCase):
    def setUp(self):
        # A synthetic root: the real RUN.md, a synthetic ladder and a crew of our own.
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir()
        shutil.copyfile(str(ROOT / 'docs' / 'RUN.md'), str(self.root / 'docs' / 'RUN.md'))
        (self.root / 'docs' / 'NORTH_STAR.md').write_text(NORTH_STAR, encoding='utf-8')
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

    def test_pack_follows_the_registry_week_flag(self):
        # The registry shape of crew/registry.json: a row per crew member and a flag per launch week.
        crew = self.root / 'crew'
        rows = [('substack', ['substack', 'substack-notes'], True), ('threads', ['threads'], True),
                ('canva-studio', ['threads', 'substack-notes', 'instagram'], False),
                ('engagement', ['threads', 'substack-notes'], False), ('attribution-ladder', ['substack'], True),
                ('what-works', ['substack-notes', 'threads', 'x'], True), ('meta', ['instagram'], False),
                ('release-gate', ['substack-notes', 'threads', 'x'], True)]
        for cid, channels, _ in rows:
            (crew / cid).mkdir(parents=True)
            (crew / cid / 'card.md').write_text('CARD ' + cid + '\n', encoding='utf-8')
        write_json(crew / 'registry.json', {'schema_version': 1, 'kind': 'crew', 'crew': [
            {'id': cid, 'channels': channels, 'card': 'crew/' + cid + '/card.md', 'w45': flag}
            for cid, channels, flag in rows]})
        spec = fixture('w45-week')
        self.assertEqual(week_flag(spec), 'w45')
        text = self.pack(spec)
        loaded = {cid for cid, _, _ in rows if 'CARD ' + cid + '\n' in text + '\n'}
        self.assertEqual(loaded, {'substack', 'threads', 'attribution-ladder', 'what-works', 'release-gate'},
                         'W45 loads rows 1, 6, 10, 11 and the Release Gate')
        narrowed = self.pack(spec, channel='threads')
        loaded = {cid for cid, _, _ in rows if 'CARD ' + cid + '\n' in narrowed + '\n'}
        self.assertEqual(loaded, {'threads', 'what-works', 'release-gate'})
        later = computed(dict(spec, window={'start': '2026-11-09T00:00:00-05:00', 'end': '2026-11-16T00:00:00-05:00',
                                            'tz': 'America/New_York'}))
        self.assertEqual(week_flag(later), 'w46')
        self.assertIn('CARD engagement', self.pack(later), 'without a flag for the week, channels decide')

    def test_pack_refuses_a_part_over_its_budget(self):
        spec = fixture('w45-week')
        for item in spec['slots']:
            item['words'] = 'TEST FIXTURE ONLY. A long synthetic line. ' * 55
        spec = computed(spec)
        with self.assertRaisesRegex(ValueError, 'the spec slice is [0-9]+ bytes; its budget is 10240'):
            self.pack(spec)
        self.assertIn('# Run sessions', self.pack(spec, day='2026-11-02', channel='threads'))

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
        # Measured with LF endings: a Windows checkout adds a CR per line (F49).
        raw = (ROOT / 'docs' / 'RUN.md').read_bytes().replace(b'\r\n', b'\n')
        self.assertLessEqual(len(raw), 8 * 1024)
        text = raw.decode('utf-8')
        self.assertFalse(EM_DASH.search(text))
        self.assertFalse(PERCENT.search(text))
        for command in ('run new', 'run lint', 'run status', 'run pack', 'run card lint', 'ASSET-STORAGE',
                        'invariants/rules.json', '4 Growth', 'ACCOUNT-VOICE', 'run release', 'Content Engine',
                        'automation'):
            self.assertIn(command, text)


class TaskCardTests(unittest.TestCase):
    def test_card_lint_refuses_unpinned_model_and_oversize(self):
        self.assertEqual(card_errors((FIXTURES / 'task-card.json').read_bytes()), [])
        for model in ('', '   ', 'latest', 'gpt-latest', 'default', 'auto', 'gpt latest', ' gpt-6.1-sol',
                      'gpt-6.1-sol ', 'gpt-latest-preview'):
            self.assertIn('model_unpinned', {e['code'] for e in card_errors(card_bytes(model=model))}, model)
        for effort in ('', 'auto', 'max', 'medium ', ' high'):
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


class PrivateOutreachSignOff(unittest.TestCase):
    """A pitch Krish sends from his own address may carry his signature; a public draft may not."""

    def test_pitch_may_be_signed_but_public_copy_may_not(self):
        from engine.packs import problems
        item = {'platform': 'email', 'target_url': 'https://example.org', 'target_name': 'A host', 'why': 'fit',
                'text': 'Would love to talk about the AI passports piece. Krish Raja, makeyourmindup.ai', 'status': 'draft'}
        self.assertFalse([e for e in problems(item, 'pitches') if 'no_name' in e])
        self.assertTrue([e for e in problems(item, 'daily') if 'no_name' in e])
