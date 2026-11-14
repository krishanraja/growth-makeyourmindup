"""Closeout notes and the fold into NOW.md (engine/closeout.py). Offline, synthetic NOW.md only.

Ruling (Krish, 2026-10-28): pull requests never edit NOW.md at once; each session writes a note and the fold
on main writes it into NOW.md. ai-harness excludes this repository from its publisher, so the fold is ours.
"""
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest

import growth
from engine import closeout
from engine.run.measure import _state_index

ROOT = Path(__file__).resolve().parents[1]
STATE = ('<!-- north-star-state {"week_of": "2026-11-09", "week_target": 162, "current": null, "urgency": 4} --> '
         '**North Star number: U4, not measured.** TEST FIXTURE ONLY.')
NOW_MD = '\n'.join([
    '---', 'repo: synthetic/fixture', 'as_of: 2026-11-05', 'head: 0000000', '---', '',
    '# Fixture: where it is right now', '',
    '## Where it is right now (as of 2026-11-05)', '', STATE, '',
    'One paragraph of prose about the engine.', '',
    '- An older status. (2026-11-05)', '',
    '## What changed recently', '',
    '- 2026-11-05 **An older change.** It happened.', '',
    '## What is next and what is waiting on Krish', '',
    '- Next (2026-11-05): an old next step', '  that wraps onto a second line.',
    '- Waiting on Krish: a ruling he has not given.',
    '- North Star check (2026-11-05): 1 of 86, U5 stalled; holds, no recalibration proposed.',
    '- Earlier check (2026-10-29): holds.', '',
    '## Read next', '', '- README.md', ''])
LOG_MD = '# History log\n\nNewest first.\n\n## 2026-10-29\n\nOlder entry.\n'


def note(status='The fold writes each closeout note into NOW.md on main.', nxt='Krish reads NOW.md once.',
         day='2026-11-12', changed=None, check=None):
    lines = ['Status: ' + status]
    if changed:
        lines.append('Changed: ' + changed)
    lines += ['Next: ' + nxt, check or 'North Star check (' + day + '): holds.']
    return '\n'.join(lines) + '\n'


class Repo:
    def __init__(self, now=NOW_MD, log=LOG_MD):
        self.root = Path(tempfile.mkdtemp())
        (self.root / 'now-notes').mkdir()
        (self.root / 'docs' / 'history').mkdir(parents=True)
        (self.root / 'NOW.md').write_bytes(now.encode('utf-8'))
        (self.root / 'docs' / 'history' / 'LOG.md').write_bytes(log.encode('utf-8'))

    def note(self, name, text):
        (self.root / 'now-notes' / name).write_text(text, encoding='utf-8')

    def now(self):
        return (self.root / 'NOW.md').read_bytes().decode('utf-8')

    def section(self, heading):
        lines = self.now().split('\n')
        span = closeout._section(lines, heading)
        return [l for l in lines[span[0] + 1:span[1]] if l.strip()]


class ParseTests(unittest.TestCase):
    def test_a_good_note_parses_and_wrapped_lines_join(self):
        n = closeout.parse_note('2026-11-12-fold.md', 'Status: one\n  two words and more here.\nNext: do it now\n'
                                                     'North Star check (2026-11-12): holds.\n')
        self.assertEqual(n['problems'], [])
        self.assertEqual((n['date'], n['status']), ('2026-11-12', 'one two words and more here.'))
        n = closeout.parse_note('2026-11-12-fold.md', note(check='North Star check (2026-11-12): recalibration '
                                                                   'proposed. The ladder is too steep.'))
        self.assertEqual(n['problems'], [])

    def test_what_the_fold_cannot_place_is_a_problem(self):
        for name, text, needle in (
                ('notes.md', note(), 'is not named'),
                ('2026-11-12-Fold.md', note(), 'is not named'),
                ('2026-11-12-x.md', '# Heading\n' + note(), 'cannot place'),
                ('2026-11-12-x.md', note(status='short'), 'needs "Status'),
                ('2026-11-12-x.md', note(check='North Star check (2026-11-12): holds. Still 1 of 86.'), 'needs one line'),
                ('2026-11-12-x.md', 'Status: something long enough to count\nNorth Star check (2026-11-12): holds.\n',
                 'needs "Next'),
                ('2026-11-12-x.md', note(status='A status with a — dash in it here'), 'em dash')):
            problems = closeout.parse_note(name, text)['problems']
            self.assertTrue(any(needle in p for p in problems), (name, problems))


class FoldTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(shutil.rmtree, self.repo.root)

    def test_a_note_lands_in_each_section_and_is_removed(self):
        self.repo.note('2026-11-12-fold.md', note(changed='**The fold.** Notes reach NOW.md.'))
        result = closeout.fold(self.repo.root, head='abcdef1234', day='2026-11-12')
        self.assertEqual((result['folded'], result['problems']), (['now-notes/2026-11-12-fold.md'], []))
        self.assertFalse((self.repo.root / 'now-notes' / '2026-11-12-fold.md').exists())
        text = self.repo.now()
        self.assertIn('as_of: 2026-11-12', text)
        self.assertIn('head: abcdef1', text)
        self.assertIn('## Where it is right now (as of 2026-11-12)', text)
        where = self.repo.section(closeout.WHERE)
        self.assertEqual(where[0], STATE)  # the state line stays directly under the heading
        self.assertEqual(where[2], '- The fold writes each closeout note into NOW.md on main. (2026-11-12)')
        self.assertEqual(where[3], '- An older status. (2026-11-05)')
        lines = text.split('\n')
        self.assertEqual(lines[_state_index([l + '\n' for l in lines])], STATE)  # measure can still write it
        self.assertEqual(self.repo.section(closeout.RECENT)[0], '- 2026-11-12 **The fold.** Notes reach NOW.md.')
        self.assertEqual(self.repo.section(closeout.WAITING), [
            '- Next (2026-11-12): Krish reads NOW.md once.',
            '- Waiting on Krish: a ruling he has not given.',
            '- North Star check (2026-11-12): holds.'])

    def test_a_drop_removes_the_one_waiting_item_it_names_and_a_miss_is_a_problem(self):
        # Audit 2026-11-14: stale waiting lines had no way out but an edit of NOW.md.
        self.repo.note('2026-11-12-drop.md', note() + 'Drop: Waiting on Krish: a ruling he\n  has not given.\n')
        result = closeout.fold(self.repo.root, head='abcdef1234', day='2026-11-12')
        self.assertEqual(result['problems'], [])
        self.assertEqual(self.repo.section(closeout.WAITING), [
            '- Next (2026-11-12): Krish reads NOW.md once.', '- North Star check (2026-11-12): holds.'])
        parsed = closeout.parse_note('2026-11-13-x.md', note(day='2026-11-13') + 'Drop: Waiting on Krish: no such line here.\n')
        self.assertEqual(parsed['drop'], ['Waiting on Krish: no such line here.'])
        self.repo.note('2026-11-13-miss.md', note(day='2026-11-13') + 'Drop: Waiting on Krish: no such line here.\n')
        result = closeout.fold(self.repo.root, head='abcdef1234', day='2026-11-13')
        self.assertEqual(len(result['problems']), 1)
        self.assertIn('matches 0 items', result['problems'][0])
        self.assertTrue((self.repo.root / 'now-notes' / '2026-11-13-miss.md').exists())
        short = closeout.parse_note('2026-11-13-y.md', note(day='2026-11-13') + 'Drop: Waiting\n')
        self.assertTrue(any('shorter than 20' in p for p in short['problems']))

    def test_notes_fold_oldest_first_and_dates_never_go_back(self):
        self.repo.note('2026-11-10-first.md', note(status='The first status is long enough.', nxt='First next.',
                                                   day='2026-11-10'))
        self.repo.note('2026-11-12-second.md', note(status='The second status is long enough.', nxt='Second next.'))
        closeout.fold(self.repo.root, day='2026-11-12')
        waiting = self.repo.section(closeout.WAITING)
        self.assertEqual(waiting[0], '- Next (2026-11-12): Second next.')
        self.assertEqual(sum(1 for l in waiting if l.startswith('- Next')), 1)
        self.assertEqual(waiting[-1], '- North Star check (2026-11-12): holds.')
        self.assertEqual(self.repo.section(closeout.WHERE)[2:4], ['- The second status is long enough. (2026-11-12)',
                                                                 '- The first status is long enough. (2026-11-10)'])
        self.repo.note('2026-11-01-late.md', note(status='A late note from an earlier day.', day='2026-11-01'))
        closeout.fold(self.repo.root, day='2026-11-12')
        self.assertIn('as_of: 2026-11-12', self.repo.now())

    def test_a_bad_note_stays_and_the_rest_fold(self):
        self.repo.note('2026-11-12-bad.md', '# Not a note\n')
        self.repo.note('2026-11-12-good.md', note())
        result = closeout.fold(self.repo.root, day='2026-11-12')
        self.assertEqual(result['folded'], ['now-notes/2026-11-12-good.md'])
        self.assertTrue(result['problems'])
        self.assertTrue((self.repo.root / 'now-notes' / '2026-11-12-bad.md').exists())

    def test_nothing_to_fold_writes_nothing(self):
        before = self.repo.now()
        self.assertEqual(closeout.fold(self.repo.root)['folded'], [])
        shutil.rmtree(self.repo.root / 'now-notes')
        self.assertEqual(closeout.fold(self.repo.root)['folded'], [])
        self.assertEqual(self.repo.now(), before)

    def test_a_dry_run_writes_nothing(self):
        self.repo.note('2026-11-12-fold.md', note())
        before = self.repo.now()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = closeout.command(['fold', '--dry-run'], self.repo.root)
        self.assertEqual(code, 0)
        self.assertIn('would fold now-notes/2026-11-12-fold.md', out.getvalue())
        self.assertEqual(self.repo.now(), before)
        self.assertTrue((self.repo.root / 'now-notes' / '2026-11-12-fold.md').exists())

    def test_crlf_files_keep_their_line_endings(self):
        repo = Repo(NOW_MD.replace('\n', '\r\n'), LOG_MD.replace('\n', '\r\n'))
        self.addCleanup(shutil.rmtree, repo.root)
        repo.note('2026-11-12-fold.md', note())
        closeout.fold(repo.root, day='2026-11-12')
        raw = (repo.root / 'NOW.md').read_bytes()
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertIn(b'- Next (2026-11-12): Krish reads NOW.md once.\r\n', raw)


class TrimTests(unittest.TestCase):
    def test_old_lines_move_to_the_history_log_verbatim_to_keep_the_cap(self):
        recent = ['- 2026-10-%02d **Change %d.** ' % (d, d) + 'Words. ' * 400 for d in range(10, 20)]
        now = NOW_MD.replace('- 2026-11-05 **An older change.** It happened.', '\n'.join(reversed(recent)))
        repo = Repo(now)
        self.addCleanup(shutil.rmtree, repo.root)
        repo.note('2026-11-12-fold.md', note(changed='**Newest.** Kept.'))
        result = closeout.fold(repo.root, day='2026-11-12')
        self.assertEqual(result['problems'], [])
        self.assertLessEqual(len((repo.root / 'NOW.md').read_bytes()), closeout.NOW_CAP)
        kept = repo.section(closeout.RECENT)
        self.assertEqual(kept[0], '- 2026-11-12 **Newest.** Kept.')
        log = (repo.root / 'docs' / 'history' / 'LOG.md').read_text(encoding='utf-8')
        moved = result['moved'][closeout.RECENT]
        self.assertEqual(moved[-1], recent[0])  # the oldest went first, verbatim
        self.assertTrue(all(item in log for item in moved))
        self.assertLess(log.index('## 2026-11-12'), log.index('## 2026-10-29'))  # newest first
        self.assertIn('Moved verbatim from `NOW.md`', log)
        self.assertFalse(set(moved) & set(kept))

    def test_status_bullets_past_the_newest_eight_move_too(self):
        statuses = ['- Status number %d is here. (2026-11-%02d)' % (n, n) for n in range(1, 10)]
        repo = Repo(NOW_MD.replace('- An older status. (2026-11-05)', '\n'.join(reversed(statuses))))
        self.addCleanup(shutil.rmtree, repo.root)
        repo.note('2026-11-12-fold.md', note())
        result = closeout.fold(repo.root, day='2026-11-12')
        where = [l for l in repo.section(closeout.WHERE) if l.startswith('- ')]
        self.assertEqual(len(where), closeout.MAX_STATUS)
        self.assertEqual(result['moved'][closeout.WHERE], [statuses[1], statuses[0]])


class RepositoryNotesTests(unittest.TestCase):
    def test_every_note_in_this_repository_is_one_the_fold_can_place(self):
        problems = [p for n in closeout.read_notes(ROOT) for p in n['problems']]
        self.assertEqual(problems, [], 'fix the note (AGENTS.md, "Closeout"); the fold on main cannot place it')

    def test_now_md_has_every_section_the_fold_writes(self):
        lines = (ROOT / 'NOW.md').read_text(encoding='utf-8').split('\n')
        for heading in (closeout.WHERE, closeout.RECENT, closeout.WAITING):
            self.assertIsNotNone(closeout._section(lines, heading), heading)

    def test_the_fold_job_runs_on_main_only_and_writes_only_its_files(self):
        text = (ROOT / '.github' / 'workflows' / 'check.yml').read_text(encoding='utf-8')
        fold = text[text.index('  fold:'):]
        for needle in ("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", 'contents: write',
                       'python growth.py closeout fold', 'git add -A -- NOW.md now-notes docs/history/LOG.md',
                       'docs(closeout): fold closeout notes into NOW.md'):
            self.assertIn(needle, fold)
        self.assertIn('python growth.py closeout check', text[:text.index('  fold:')])
        self.assertNotIn('secrets.', text)

    def test_the_route_is_wired(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = growth.main(['closeout', 'check'])
        self.assertIn('closeout note(s)', out.getvalue())
        self.assertEqual(code, int('0 problem(s)' not in out.getvalue()))


if __name__ == '__main__':
    unittest.main()
