"""Lanes and one-time set-up: the standing text a fresh session follows.

There are no Claude routines (Krish, 29 Oct 2026): "I want zero Claude routines. No Claude schedules of any
kind in this architecture". A new schedule is a GitHub Actions job.
"""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = re.compile('[–—]')
LINK = re.compile(r'\]\(([^)\s]+)\)')
# Files other parts of V1 add; a doc names them and a maker stops when they are missing.
ADDED_ELSEWHERE = {'lanes.json', 'calendar/v1.json', 'social/brand/kit.json'}


def text(path):
    return (ROOT / path).read_text(encoding='utf-8')


class LaneDocTests(unittest.TestCase):
    def test_lanes_page_is_plain(self):
        lanes = text('docs/LANES.md')
        self.assertFalse(EM_DASH.search(lanes))
        for needle in ('## L0', '## L2', '## L3', '`lanes.json`', 'LinkedIn', 'The Buffer plan',
                       'One-time set-up', '05:10', '29 November 2026', 'UTC', 'London',
                       'There are no Claude routines (Krish, 29 Oct 2026)', '## Who makes', '`docs/TASTE.md`',
                       '`repository_dispatch`', 'I want zero Claude routines. No Claude schedules of any kind'):
            self.assertIn(needle, ' '.join(lanes.split()), needle)
        self.assertNotIn('## L1', lanes)
        run = text('docs/RUN.md')
        self.assertIn('## Lanes', run)
        self.assertIn('docs/LANES.md', run)
        self.assertIn('docs/LANES.md', text('README.md'))

    def test_setup_once_has_exact_steps(self):
        setup = text('docs/SETUP-ONCE.md')
        self.assertFalse(EM_DASH.search(setup))
        for needle in ('**API**', '**Personal Access**', '**New Key**', '**1 year**', '`BUFFER_API_KEY`',
                       'https://github.com/krishanraja/growth-makeyourmindup/settings/secrets/actions',
                       '`CONTROL_CENTER_ENGINE_TOKEN`'):
            self.assertIn(needle, setup, needle)
        # No step creates a Claude routine or any Claude schedule (Krish, 29 Oct 2026).
        for gone in ('New routine', 'routines/', 'Cron', '* * *'):
            self.assertNotIn(gone, setup, gone)

    def test_no_session_is_told_to_hold_the_engine_key(self):
        key = ' '.join(text('docs/KEY.md').split())
        self.assertIn('A Claude session (cloud or interactive) holds no engine key', key)
        self.assertIn('Control Center connector', key)
        for path in ('docs/GET-GOING.md', 'docs/SESSION-HANDOVER.md', 'AGENTS.md'):
            self.assertIn('Control Center connector', text(path), path)
        plan = text('docs/plans/2026-10-27-engine-architecture.md')
        line = [ln for ln in plan.splitlines() if 'Claude environment secret' in ln]
        self.assertTrue(all('Superseded' in ln for ln in line))

    def test_doc_links_resolve(self):
        docs = ['README.md', 'AGENTS.md', 'docs/RUN.md', 'docs/LANES.md', 'docs/SETUP-ONCE.md', 'docs/KEY.md',
                'docs/GET-GOING.md', 'docs/SESSION-HANDOVER.md', 'docs/TASTE.md', 'jobs/daily-growth.md']
        for doc in docs:
            body = text(doc)
            base = (ROOT / doc).parent
            for target in LINK.findall(body):
                if re.match(r'[a-z]+:', target) or target.startswith('#'):
                    continue
                self.assertTrue((base / target.split('#')[0]).exists(), (doc, target))
            for target in re.findall(r'`((?:docs|routines|jobs)/[A-Za-z0-9_./-]+\.md)`', body):
                if target not in ADDED_ELSEWHERE:
                    self.assertTrue((ROOT / target).exists(), (doc, target))


    def test_nothing_points_at_a_routine(self):
        # CHANGES.md and the dated history keep what was true when they were written.
        kept = {'CHANGES.md', 'NOW.md'}
        stale = re.compile(r'routines/[a-z]|routine-(?:make|plan|watch)|\bL1(?:_judgement)?\b|Claude (?:cloud )?routine')
        for folder, dirs, files in os.walk(str(ROOT)):
            # tests/ probes the old names on purpose; docs/history keeps what was true then.
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'history', 'tests')]
            for name in files:
                path = Path(folder) / name
                rel = path.relative_to(ROOT).as_posix()
                if rel in kept or path.suffix not in ('.md', '.json', '.py', '.yml', '.mjs'):
                    continue
                flat = ' '.join(path.read_text(encoding='utf-8').split())
                for match in stale.finditer(flat):
                    # "no Claude routines", "zero Claude routines", "never a Claude routine", "not a Claude
                    # routine" and "no L1" say the ruling itself.
                    before = flat[max(0, match.start() - 10):match.start()]
                    if not re.search(r'\b(?:no|zero|never an?|not an?) $', before, re.I):
                        self.fail('%s still names a Claude routine: %s'
                                  % (rel, flat[max(0, match.start() - 60):match.end() + 60]))


if __name__ == '__main__':
    unittest.main()
