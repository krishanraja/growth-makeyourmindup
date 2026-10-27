"""Phase 0 cost meter: aggregates from synthetic agent session logs only."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.run.cost import baseline, in_repo, main, stamp

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'cost'


class CostBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.codex = root / 'codex' / 'sessions'
        self.claude = root / 'claude' / 'projects'

    def place(self, *names):
        for name in names:
            if name == 'claude-subagent.jsonl':  # beside its parent session, as Claude Code stores it
                folder = self.claude / 'fixture-project' / 'claude-session' / 'subagents'
                target = folder / 'agent-x.jsonl'
            elif name.startswith('codex'):
                folder = self.codex / '2026' / '10' / '20'
                target = folder / ('rollout-2026-10-20-' + name)
            else:
                folder = self.claude / 'fixture-project'
                target = folder / name
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FIXTURES / name, target)

    def run_baseline(self, **kwargs):
        return baseline(str(self.codex), str(self.claude), **kwargs)

    def test_codex_rollout_tokens_and_calls(self):
        self.place('codex-numbers.jsonl')
        result = self.run_baseline()
        self.assertEqual(result['sessions_counted'], 1)
        session = result['sessions'][0]
        self.assertEqual(session['job_kind'], 'numbers')
        self.assertEqual(session['model_calls'], 2)
        # The cumulative total is the authority, not the sum of per-call usage.
        self.assertEqual(session['tokens'], {'input': 3000, 'cached_input': 1700, 'output': 400,
                                             'reasoning_output': 150, 'total': 3400})
        self.assertEqual(session['mean_context'], 1500)
        self.assertEqual(session['models'], ['fixture-model'])
        self.assertEqual(session['tool_minutes'], 1.0)
        numbers = result['by_job_kind']['numbers']
        self.assertEqual((numbers['sessions'], numbers['model_calls'], numbers['mean_context']), (1, 2, 1500))
        self.assertEqual(result['lines'], {'lines': 13, 'unparseable': 0, 'unknown': 0})

    def test_wait_time_is_separate_from_engine_time(self):
        self.place('codex-numbers.jsonl', 'claude-session.jsonl')
        result = self.run_baseline()
        codex = [s for s in result['sessions'] if s['tool'] == 'codex'][0]
        self.assertEqual(codex['engine_minutes'], 8.0)   # 5 minutes plus 3 minutes of tasks
        self.assertEqual(codex['wait_for_human_minutes'], 10.0)
        claude = [s for s in result['sessions'] if s['tool'] == 'claude'][0]
        self.assertEqual(claude['engine_minutes'], 3.0)  # 12:00 to 12:02, then 12:12 to 12:13
        self.assertEqual(claude['wait_for_human_minutes'], 10.0)
        self.assertEqual(claude['tool_minutes'], 0.5)
        # One response split over two lines is one call; its last usage counts.
        self.assertEqual(claude['model_calls'], 3)
        self.assertEqual(claude['tokens'], {'input': 60, 'cache_creation_input': 1000,
                                            'cache_read_input': 18000, 'output': 170, 'total': 19230})
        self.assertEqual(claude['job_kind'], 'interactive')
        self.assertEqual(result['by_job_kind']['interactive']['wait_for_human_minutes'], 10.0)

    def test_unknown_lines_are_counted_not_guessed(self):
        self.place('codex-drift.jsonl')
        result = self.run_baseline()
        session = result['sessions'][0]
        self.assertEqual(session['unparseable_lines'], 2)
        self.assertEqual(session['unknown_lines'], 3)  # unknown type, untyped event, malformed usage
        self.assertEqual(session['model_calls'], 1)
        self.assertEqual(session['tokens']['input'], 500)
        self.assertEqual(result['lines']['unparseable'], 2)
        self.assertEqual(result['lines']['unknown'], 3)
        self.assertIsNone(stamp('2026-10-22T10:00:00'), 'a timestamp without an offset is never guessed')
        self.assertEqual(stamp('2026-10-22T10:00:00.000000000Z').isoformat(), '2026-10-22T10:00:00+00:00')
        self.assertEqual(stamp('2026-10-22T06:00:00-0400').isoformat(), '2026-10-22T10:00:00+00:00')

    def test_sessions_outside_repo_are_ignored(self):
        self.place('codex-numbers.jsonl', 'codex-outside.jsonl', 'codex-drift.jsonl')
        result = self.run_baseline()
        self.assertEqual(result['sessions_counted'], 2)  # a Windows path to the repo still counts
        self.assertEqual(result['sessions_outside_repo'], 1)
        self.assertNotIn('daily-growth', result['by_job_kind'])
        self.assertEqual(self.run_baseline(repo='other-repo')['sessions_counted'], 1)
        later = self.run_baseline(since='2026-10-21')
        self.assertEqual((later['sessions_counted'], later['sessions_before_since']), (1, 1))
        with self.assertRaises(ValueError):
            self.run_baseline(repo='../growth-makeyourmindup')
        # A whole path component must match, not a longer folder name.
        self.assertTrue(in_repo('C:\\Users\\fixture\\growth-makeyourmindup\\.claude\\worktrees\\x', 'growth-makeyourmindup'))
        self.assertFalse(in_repo('/home/fixture/growth-makeyourmindup-old', 'growth-makeyourmindup'))
        self.assertTrue(in_repo('https://github.com/fixture-owner/growth-makeyourmindup.git', 'growth-makeyourmindup'))

    def test_claude_subagents_fold_into_their_session(self):
        self.place('claude-session.jsonl', 'claude-subagent.jsonl')
        journal = self.claude / 'fixture-project' / 'claude-session' / 'subagents' / 'journal.jsonl'
        journal.write_text('{"type": "workflow-step", "note": "FIXTURE-SECRET-JOURNAL"}\n', encoding='utf-8')
        result = self.run_baseline()
        self.assertEqual(result['sessions_counted'], 1)  # one session, not one per subagent
        self.assertEqual(result['files_read']['claude_subagents'], 1)
        claude = result['sessions'][0]
        self.assertEqual(claude['job_kind'], 'interactive')  # the parent's prompt decides, not a subagent's
        self.assertEqual(claude['model_calls'], 5)
        self.assertEqual(claude['tokens'], {'input': 70, 'cache_creation_input': 1300, 'cache_read_input': 22300,
                                            'output': 220, 'total': 23890})
        self.assertEqual(claude['models'], ['fixture-claude-model', 'fixture-subagent-model'])
        self.assertEqual((claude['engine_minutes'], claude['wait_for_human_minutes']), (3.0, 10.0))
        self.assertEqual(claude['tool_minutes'], 1.0)  # 30 seconds in the parent, 30 in the subagent
        self.assertEqual(claude['unknown_lines'], 0)  # attachment lines are routine, not drift

    def test_codex_repeats_and_aborted_turns_are_not_misread(self):
        self.place('codex-aborted.jsonl')
        result = self.run_baseline()
        self.assertEqual(result['sessions_counted'], 1)  # a worktree elsewhere, matched by its git remote
        session = result['sessions'][0]
        self.assertEqual((session['model_calls'], session['mean_context']), (1, 800))  # a repeated total is one call
        self.assertEqual(session['tokens']['total'], 820)
        self.assertEqual((session['engine_minutes'], session['wait_for_human_minutes']), (2.0, 4.0))
        self.assertEqual(session['unknown_lines'], 1)  # an unrecognised event kind is drift, counted
        self.assertEqual(result['allowance']['primary_used_percent'], 12.0)
        self.assertIsNone(result['allowance']['primary_resets_at'])  # an impossible reset is left unknown

    def test_allowance_reading_from_rate_limits(self):
        self.place('codex-numbers.jsonl')
        reading = self.run_baseline()['allowance']
        self.assertEqual(reading['primary_used_percent'], 41.5)
        self.assertEqual(reading['read_at'], '2026-10-20T09:17:00+00:00')
        self.assertEqual(reading['primary_resets_at'], '2026-10-20T10:17:00+00:00')
        self.assertEqual(reading['primary_window_minutes'], 10080)
        # The allowance is account-wide: the newest reading wins, whatever the repository.
        self.place('codex-outside.jsonl')
        self.assertEqual(self.run_baseline()['allowance']['primary_used_percent'], 55.25)
        self.assertIsNone(baseline(str(self.codex / 'missing'), str(self.claude / 'missing'))['allowance'])

    def test_output_has_no_message_text(self):
        self.place('codex-numbers.jsonl', 'codex-outside.jsonl', 'codex-drift.jsonl', 'claude-session.jsonl',
                   'claude-subagent.jsonl', 'codex-aborted.jsonl')
        posts = Path(self.tmp.name) / 'verified.json'
        posts.write_text(json.dumps({'numbers': 2, 'carousel': 0}), encoding='utf-8')
        out = Path(self.tmp.name) / 'baseline.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['cost', 'baseline', '--codex-dir', str(self.codex), '--claude-dir', str(self.claude),
                                   '--verified-posts', str(posts), '--out', str(out)]), 0)
        text = out.read_text(encoding='utf-8')
        for secret in ('FIXTURE-SECRET', 'fixture-session', 'private-notes', '/home/', 'Users', 'please look',
                       self.tmp.name, 'call-1', 'tool-1', 'msg-1', 'fixture-owner', 'growth-wt', 'fixture-agent'):
            self.assertNotIn(secret, text)
        result = json.loads(text)
        self.assertEqual(result['repo'], 'growth-makeyourmindup')
        self.assertEqual(result['per_verified_post']['numbers'],
                         {'verified_posts': 2, 'tokens_per_post': 2110, 'engine_minutes_per_post': 5.0, 'reason': None})
        self.assertEqual(result['per_verified_post']['carousel']['reason'], 'no sessions of this job kind')


if __name__ == '__main__':
    unittest.main()
