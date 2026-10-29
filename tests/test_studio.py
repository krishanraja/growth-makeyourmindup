"""W2.11 one local layout and W2.12 the NOW.md byte cap. Offline."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from engine import studio

ROOT = Path(__file__).resolve().parents[1]
# A folder on Krish's own machine, in either slash style, case aside.
HARD_PATH = re.compile(r'C:[\\/]+Users[\\/]+krish[\\/]+dev[\\/]', re.I)
ALLOWED = ('config/studio.json', 'tests/test_studio.py')
# Krish's saved briefs are kept verbatim; they describe the layout, they are not readers of it.
ALLOWED_DIRS = ('docs/briefs/waves/',)
NOW_CAP = 16384


def tracked(root=ROOT):
    names = subprocess.run(['git', 'ls-files'], cwd=root, capture_output=True, text=True, check=True).stdout.split('\n')
    return [n for n in names if n and not n.startswith('tests/fixtures/')]


def planted_paths(files, root=ROOT):
    hits = []
    for name in files:
        if name in ALLOWED or name.startswith(ALLOWED_DIRS):
            continue
        try:
            text = (Path(root) / name).read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if HARD_PATH.search(text):
            hits.append(name)
    return hits


class LocalLayout(unittest.TestCase):
    def test_no_tracked_file_hard_codes_a_folder_on_his_machine(self):
        self.assertEqual(planted_paths(tracked()), [])

    def test_the_guard_fails_on_a_planted_path(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'planted.md').write_text('Work from C:/Users/krish/dev/mindmake/x', encoding='utf-8')
            (Path(folder) / 'other.md').write_text('Work from C:\\\\Users\\\\Krish\\\\dev\\\\x', encoding='utf-8')
            self.assertEqual(sorted(planted_paths(['planted.md', 'other.md'], folder)), ['other.md', 'planted.md'])

    def test_every_root_resolves_from_config(self):
        self.assertTrue(studio.local_root('repos', 'growth-makeyourmindup').endswith('\\growth-makeyourmindup'))
        self.assertIn('\\.worktrees\\growth-makeyourmindup\\claude\\x',
                      studio.local_root('worktrees', 'growth-makeyourmindup', 'claude/x'))
        self.assertIn('LOCALAPPDATA', studio.local_root('runtime'))
        with self.assertRaises(ValueError):
            studio.local_root('repos')


class NowCap(unittest.TestCase):
    def test_now_md_stays_under_its_byte_cap(self):
        size = len((ROOT / 'NOW.md').read_bytes())
        self.assertLessEqual(size, NOW_CAP, 'move older lines to docs/history/LOG.md verbatim (W2.12)')

    def test_history_keeps_what_left_now_md(self):
        log = (ROOT / 'docs' / 'history' / 'LOG.md').read_text(encoding='utf-8')
        self.assertIn('Moved verbatim from `NOW.md`', log)


if __name__ == '__main__':
    unittest.main()
