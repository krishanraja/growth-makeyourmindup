"""Cloud routines, lanes and one-time set-up: the standing text a fresh session follows."""
from pathlib import Path
import re
import unittest

from engine.run.cost import job_kind

ROOT = Path(__file__).resolve().parents[1]
ROUTINES = ('make', 'plan', 'watch')
EM_DASH = re.compile('[–—]')
LINK = re.compile(r'\]\(([^)\s]+)\)')
# Files other parts of V1 add; a routine names them and stops when they are missing.
ADDED_ELSEWHERE = {'lanes.json', 'calendar/v1.json', 'social/brand/kit.json'}


def text(path):
    return (ROOT / path).read_text(encoding='utf-8')


def standing(name):
    return 'Clone krishanraja/growth-makeyourmindup (main) and follow routines/' + name + '.md'


class RoutineTests(unittest.TestCase):
    def test_each_routine_is_standalone_small_and_walled(self):
        for name in ROUTINES:
            path = ROOT / 'routines' / (name + '.md')
            # Measured with LF endings: a Windows checkout adds a CR per line (F49).
            raw = path.read_bytes().replace(b'\r\n', b'\n')
            self.assertLessEqual(len(raw), 6 * 1024, name)
            body = raw.decode('utf-8')
            self.assertIn(standing(name), body.replace('\n', ' ').replace('"', ''), name)
            for connector in ('**Canva**', '**Buffer**', '**Control Center**'):
                self.assertIn(connector, body, name)
            flat = ' '.join(body.split())
            for wall in ('Never publish, schedule, send, delete or spend. Only drafts and proposals.',
                         'Never print a secret, token or key', 'No figures in the public repository',
                         'The Codex in-app browser rules do not apply', 'Stop and report on any uncertainty',
                         '`shareNow`, `shareNext`, `customScheduled`, `addToQueue`',
                         'No session holds the Control Center token', 'run cost self'):
                self.assertIn(wall, flat, (name, wall))
            self.assertNotIn('CONTROL_CENTER_ENGINE_TOKEN', body, name)
            self.assertFalse(EM_DASH.search(body), name)

    def test_make_names_its_sources_and_handoff(self):
        flat = ' '.join(text('routines/make.md').split())
        for needle in ('kAHZOJ-K6I8', 'social/brand/kit.json', 'calendar/v1.json', 'docs/ACCOUNT-VOICE.md',
                       '`saveToDraft: true`', 'no `dueAt`', 'buffer_draft_id', 'payload_sha256',
                       'repository_dispatch', 'gh api repos/krishanraja/growth-makeyourmindup/dispatches',
                       'LinkedIn', 'krish_click', '29 Nov 2026', 'per item', 'run plain', 'run canva lint',
                       'run cost baseline --claude-dir ~/.claude/projects --since <today>'):
            self.assertIn(needle, flat, needle)
        self.assertIn('Sundays, 05:30 UTC', text('routines/plan.md'))
        self.assertIn('registered experiment', text('routines/plan.md'))
        self.assertIn('07:30, 12:30 and 17:30 UTC', text('routines/watch.md'))
        self.assertIn('list_ideas', text('routines/watch.md'))

    def test_standing_text_is_a_routine_to_the_cost_meter(self):
        setup = text('docs/SETUP-ONCE.md')
        for name in ROUTINES:
            self.assertIn('`' + standing(name) + '`', setup, name)
            self.assertEqual(job_kind(standing(name)), 'routine-' + name)


class LaneDocTests(unittest.TestCase):
    def test_lanes_page_is_plain(self):
        lanes = text('docs/LANES.md')
        self.assertFalse(EM_DASH.search(lanes))
        for needle in ('## L0', '## L1', '## L2', '## L3', '`lanes.json`', 'LinkedIn', 'The Buffer plan',
                       'One-time set-up', '05:10', '06:00', '05:30', '07:30, 12:30, 17:30', '29 November 2026',
                       'UTC', 'London'):
            self.assertIn(needle, lanes, needle)
        run = text('docs/RUN.md')
        self.assertIn('## Lanes', run)
        self.assertIn('docs/LANES.md', run)
        self.assertIn('docs/LANES.md', text('README.md'))

    def test_setup_once_has_exact_steps(self):
        setup = text('docs/SETUP-ONCE.md')
        self.assertFalse(EM_DASH.search(setup))
        for needle in ('**API**', '**Personal Access**', '**New Key**', '**1 year**', '`BUFFER_API_KEY`',
                       'https://github.com/krishanraja/growth-makeyourmindup/settings/secrets/actions',
                       '`CONTROL_CENTER_ENGINE_TOKEN`', '**Canva**', '**Buffer**', '**Control Center**',
                       '`0 6 * * *`', '`30 5 * * 0`', '`30 7,12,17 * * *`'):
            self.assertIn(needle, setup, needle)

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
                'docs/GET-GOING.md', 'docs/SESSION-HANDOVER.md', 'jobs/daily-growth.md']
        docs += ['routines/%s.md' % name for name in ROUTINES]
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


if __name__ == '__main__':
    unittest.main()
