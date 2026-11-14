"""Own-pull-requests-only auto-merge (Ruling, Krish, 2026-11-14, decision 1.11).

Runs the real jq rule .github/workflows/auto-merge.yml runs: only a ready pull
request of ours, at the commit whose checks passed, merges itself.
"""
import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULE = ROOT / '.github' / 'scripts' / 'auto-merge-pick.jq'
WORKFLOW = ROOT / '.github' / 'workflows' / 'auto-merge.yml'
SHA = 'a' * 40
OWNER = 'krishanraja'
OURS = {'number': 7, 'headRefOid': SHA, 'isDraft': False, 'isCrossRepository': False,
        'author': {'login': 'krishanraja'}, 'headRepositoryOwner': {'login': OWNER}}


def pick(prs):
    out = subprocess.run(['jq', '-r', '--arg', 'sha', SHA, '--arg', 'owner', OWNER, '-f', str(RULE)],
                         input=json.dumps(prs), capture_output=True, text=True, check=True)
    return out.stdout.strip()


def but(**changes):
    return {**OURS, **changes}


class AutoMergeGuard(unittest.TestCase):
    def test_merges_our_own_ready_pull_request(self):
        self.assertEqual(pick([OURS]), '7')

    def test_merges_a_pull_request_the_actions_bot_opened(self):
        self.assertEqual(pick([but(author={'login': 'app/github-actions', 'is_bot': True})]), '7')

    def test_never_merges_a_fork(self):
        self.assertEqual(pick([but(isCrossRepository=True)]), '')
        self.assertEqual(pick([but(headRepositoryOwner={'login': 'stranger'})]), '')

    def test_never_merges_a_stranger(self):
        self.assertEqual(pick([but(author={'login': 'stranger'})]), '')
        self.assertEqual(pick([but(author=None)]), '')

    def test_leaves_drafts_and_other_commits_alone(self):
        self.assertEqual(pick([but(isDraft=True)]), '')
        self.assertEqual(pick([but(headRefOid='b' * 40)]), '')
        self.assertEqual(pick([]), '')

    def test_workflow_waits_on_this_repositorys_own_checks(self):
        wf = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('workflows: ["check"]', wf)
        self.assertRegex(wf, r'CHECKS: check\n')
        self.assertIn('workflow_run.head_repository.full_name == github.repository', wf)
        self.assertIn("workflow_run.event == 'pull_request'", wf)
        self.assertIn('-f .github/scripts/auto-merge-pick.jq', wf)
        self.assertIn('isCrossRepository,author,headRepositoryOwner', wf)


if __name__ == '__main__':
    unittest.main()
