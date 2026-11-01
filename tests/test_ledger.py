"""The ledger (engine/ledger.py): one row per day per slot, read-only. Synthetic data only; no network."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine import ledger

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'fixtures' / 'ledger'
NOW = '2026-11-02T09:05:00Z'


def run(argv, root=None):
    lines = []
    code = ledger.command(argv, root or ROOT, now=NOW, out=lines.append)
    return code, '\n'.join(lines)


class LedgerFixtureTests(unittest.TestCase):
    def setUp(self):
        code, text = run(['--today', '2026-11-02', '--fixtures', str(FIXTURES), '--json'])
        self.assertEqual(code, 0)
        self.doc = json.loads(text)
        self.rows = {r['date']: r for r in self.doc['rows']}

    def test_fourteen_days_one_row_a_day_heroes_on_mon_wed_fri(self):
        self.assertEqual(self.doc['schema'], 'growth-ledger/1')
        self.assertEqual(len(self.doc['rows']), 14)
        self.assertEqual(self.doc['rows'][0]['date'], '2026-11-02')
        self.assertEqual(self.doc['rows'][-1]['date'], '2026-11-15')
        slots = [r['slot'] for r in self.doc['rows'][:7]]
        self.assertEqual(slots, ['hero', 'off-day', 'hero', 'off-day', 'hero', 'off-day', 'off-day'])
        self.assertEqual([self.rows[d]['series'] for d in ('2026-11-02', '2026-11-04', '2026-11-06')],
                         ['follow.the.money', 'under.the.hood', 'mind.the.gap'])
        for r in self.doc['rows']:
            for field in ('date', 'weekday', 'slot', 'series', 'format', 'piece_id', 'title_of_record', 'stage',
                          'assets', 'next_action', 'owner', 'due', 'posted', 'sources'):
                self.assertIn(field, r)
            self.assertEqual(set(r['assets']), {'board_url', 'drive_folder', 'manifest_sha256'})
        self.assertEqual(self.rows['2026-11-04']['assets']['board_url'],
                         'https://content.krishraja.com/board/2026-11-02#wed')

    def test_a_posted_hero_counts_only_its_own_slot_on_this_engines_channels(self):
        mon = self.rows['2026-11-02']
        self.assertEqual(mon['stage'], 7)
        self.assertEqual(mon['owner'], 'growth')
        self.assertEqual(mon['title_of_record'], 'Synthetic: a posted hero')
        self.assertEqual(mon['posted'], [{'channel': 'youtube', 'url': 'https://www.youtube.com/shorts/synthetic',
                                          'buffer_post_id': 'sent-mon-yt'}])
        self.assertEqual(mon['assets']['manifest_sha256'], 'b' * 64)

    def test_a_made_hero_day_waits_on_growth_to_schedule(self):
        fri = self.rows['2026-11-06']
        self.assertEqual((fri['stage'], fri['owner']), (6, 'growth'))
        self.assertIn('Schedule the sealed cut', fri['next_action'])
        self.assertEqual(fri['title_of_record'], 'Synthetic: a made hero')  # falls back to the board title
        self.assertEqual(fri['assets']['drive_folder'], 'https://drive.google.com/drive/folders/synthetic')

    def test_a_picked_not_made_hero_is_content_engines(self):
        wed = self.rows['2026-11-04']
        self.assertEqual((wed['stage'], wed['owner'], wed['posted']), (4, 'content-engine', []))
        self.assertIsNone(wed['title_of_record'])
        self.assertEqual(wed['piece_id'], '22222222-2222-4222-8222-222222222222')

    def test_an_off_day_in_the_approved_mix_is_growths_to_make(self):
        tue = self.rows['2026-11-03']
        self.assertEqual((tue['stage'], tue['owner'], tue['format']), (5, 'growth', 'instagram:carousel'))
        self.assertEqual(tue['sources']['mix'], 'approved')
        thu = self.rows['2026-11-05']
        self.assertEqual((thu['stage'], thu['owner']), (3, 'growth'))  # approved mix has nothing that day

    def test_an_off_day_piece_scheduled_at_its_own_slot(self):
        sat = self.rows['2026-11-07']
        self.assertEqual((sat['stage'], sat['owner']), (7, 'growth'))
        self.assertIn('09:00 New York', sat['next_action'])
        self.assertEqual(sat['posted'], [])

    def test_an_unpicked_week_waits_on_krish_by_the_sunday_before(self):
        for date in ('2026-11-09', '2026-11-10'):
            r = self.rows[date]
            self.assertEqual((r['stage'], r['owner'], r['due']), (3, 'krish', '2026-11-08'))
        self.assertEqual(self.rows['2026-11-10']['sources']['mix'], 'not_pressed')
        self.assertEqual(self.rows['2026-11-10']['sources']['board_manifest'], 'not_published')
        self.assertIsNone(self.rows['2026-11-10']['assets']['manifest_sha256'])


class LedgerMissingTokenTests(unittest.TestCase):
    def test_missing_tokens_never_fail_and_name_the_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in FIXTURES.iterdir():
                shutil.copy(path, folder)
            Path(folder, 'secrets.json').write_text(
                json.dumps({'GROWTH_WRITEBACK_TOKEN': False, 'BUFFER_API_KEY': False}), encoding='utf-8')
            code, text = run(['--today', '2026-11-02', '--fixtures', folder, '--json'])
        self.assertEqual(code, 0)
        rows = json.loads(text)['rows']
        self.assertEqual(len(rows), 14)
        for r in rows:
            self.assertIsNone(r['stage'])
            self.assertEqual(r['owner'], 'krish')
            self.assertIn('GROWTH_WRITEBACK_TOKEN', r['next_action'])
            self.assertEqual(r['sources']['buffer'], 'missing_secret:BUFFER_API_KEY')

    def test_buffer_missing_alone_is_named_on_rows_that_need_it(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in FIXTURES.iterdir():
                shutil.copy(path, folder)
            Path(folder, 'secrets.json').write_text(json.dumps({'BUFFER_API_KEY': False}), encoding='utf-8')
            code, text = run(['--today', '2026-11-02', '--fixtures', folder, '--json'])
        rows = {r['date']: r for r in json.loads(text)['rows']}
        self.assertEqual(rows['2026-11-06']['stage'], 6)
        self.assertIn('set BUFFER_API_KEY', rows['2026-11-06']['next_action'])
        self.assertEqual(rows['2026-11-02']['stage'], 4)  # its sent post is unread, so it stays at the board's word
        self.assertNotIn('BUFFER_API_KEY', rows['2026-11-04']['next_action'])

    def test_the_live_path_with_no_secrets_reads_nothing_and_still_builds(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ('GROWTH_WRITEBACK_TOKEN', 'BUFFER_API_KEY', ledger.FIXTURES_ENV)}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch('urllib.request.urlopen', side_effect=AssertionError('no network')):
            code, text = run(['--today', '2026-11-02', '--days', '3'])
        self.assertEqual(code, 0)
        self.assertIn('"rows": 3', text)
        self.assertIn('missing_secret:GROWTH_WRITEBACK_TOKEN', text)


class LedgerWriteTests(unittest.TestCase):
    def test_write_makes_the_json_and_a_short_table_and_logs_counts_only(self):
        with tempfile.TemporaryDirectory() as root:
            code, text = run(['--today', '2026-11-02', '--fixtures', str(FIXTURES), '--write'], root)
            self.assertEqual(code, 0)
            self.assertNotIn('Synthetic', text)  # the public log carries no titles
            doc = json.loads(Path(root, 'calendar', 'ledger.json').read_text(encoding='utf-8'))
            table = Path(root, 'calendar', 'LEDGER.md').read_text(encoding='utf-8')
        self.assertEqual(len(doc['rows']), 14)
        self.assertIn('| Date | Slot | Title | Stage | Next action | Owner |', table)
        self.assertEqual(table.count('\n| ') - 1, 14)  # header plus 14 rows
        self.assertIn('Synthetic: a posted hero', table)
        self.assertIn('piece `22222222`, no title of record yet', table)

    def test_week_must_be_a_monday(self):
        with self.assertRaises(ValueError):
            run(['--week', '2026-11-03', '--fixtures', str(FIXTURES)])
        code, text = run(['--week', '2026-11-09', '--fixtures', str(FIXTURES), '--days', '7', '--json'])
        self.assertEqual(json.loads(text)['from'], '2026-11-09')


class LedgerWorkflowTests(unittest.TestCase):
    def test_daily_before_the_maker_and_writes_only_an_artifact(self):
        text = (ROOT / '.github' / 'workflows' / 'ledger.yml').read_text(encoding='utf-8')
        for needle in ("cron: '5 4 * * *'", 'workflow_dispatch', 'contents: read', 'python growth.py ledger --write',
                       'secrets.GROWTH_WRITEBACK_TOKEN', 'secrets.BUFFER_API_KEY', 'calendar/ledger.json',
                       'calendar/LEDGER.md'):
            self.assertIn(needle, text)
        self.assertNotIn('git push', text)
        self.assertNotIn('ANTHROPIC', text)
        self.assertNotIn('claude', text.lower())


if __name__ == '__main__':
    unittest.main()
