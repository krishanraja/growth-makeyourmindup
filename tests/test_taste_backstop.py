"""W3.3 the filtered chat backstop: only his flagged, scrubbed lines, kept locally. Synthetic transcripts only."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import taste_backstop as backstop  # noqa: E402


def record(content, kind='user', **extra):
    return dict({'type': kind, 'message': {'role': kind, 'content': content}}, **extra)


TRANSCRIPT = [
    record('Please build the off-day lane. No, not that layout, use the mix instead.'),
    record([{'type': 'text', 'text': "That's not on brand. My key is sk-ant-SYNTHETICsynthetic0123456789 by the way."}]),
    record([{'type': 'tool_result', 'content': 'No, wrong file, this is tool output'}]),
    record('<pasted_content id="1">No, never do this, pasted from elsewhere</pasted_content> Looks good.'),
    record('<system-reminder>Never do X</system-reminder>'),
    record('Never mention me. Write to synthetic.person@example.com for help.'),
    record('No, wrong again.', kind='assistant'),
    record('No, not that layout, use the mix instead.'),
    record("Don't add AI notes.", isMeta=True),
]


class Backstop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / 'transcript.jsonl'
        self.path.write_text('\n'.join(json.dumps(r) for r in TRANSCRIPT) + '\nnot json\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_his_flagged_lines_go_through_scrubbed(self):
        lines = backstop.flagged(self.path)
        self.assertEqual(lines, ['No, not that layout, use the mix instead.', "That's not on brand.",
                                 'Never mention me.'])
        self.assertNotIn('Please build the off-day lane.', lines)
        joined = ' '.join(lines)
        for leak in ('tool output', 'pasted from elsewhere', 'Never do X', 'wrong again', 'AI notes'):
            self.assertNotIn(leak, joined)

    def test_a_planted_secret_is_removed(self):
        for planted in ('No, use sk-ant-SYNTHETICsynthetic0123456789 here', 'Stop: token=abc123secretvalue',
                        "Don't share ghp_SYNTHETICsyntheticSYNTHETIC0123", 'No, mail synthetic.person@example.com',
                        'No, Bearer SYNTHETICtokenvalue012345'):
            clean = backstop.scrub(planted)
            self.assertNotRegex(clean, r'sk-ant|abc123secret|ghp_|example\.com|SYNTHETICtokenvalue')

    def test_the_hook_keeps_lines_locally_once_and_never_fails(self):
        hook = json.dumps({'transcript_path': str(self.path), 'session_id': 'synthetic-session'})
        printed = []
        self.assertEqual(backstop.main([], io.StringIO(hook), self.root, printed.append), 0)
        self.assertEqual(backstop.main([], io.StringIO(hook), self.root, printed.append), 0)
        rows = [json.loads(l) for l in (self.root / backstop.OUTBOX).read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(rows), 3, 'a line is kept once')
        self.assertEqual({r['venture'] for r in rows}, {'publication'})
        self.assertTrue(all(r['posted'] is False for r in rows))
        self.assertIn('nothing sent', printed[0])
        for junk in ('', 'not json', json.dumps({'transcript_path': 7}), json.dumps({'transcript_path': '/missing'})):
            self.assertEqual(backstop.main([], io.StringIO(junk), self.root, printed.append), 0)

    def test_the_hook_is_wired_as_session_end(self):
        settings = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        [entry] = settings['hooks']['SessionEnd']
        self.assertIn('scripts/taste_backstop.py', entry['hooks'][0]['command'])


if __name__ == '__main__':
    unittest.main()
