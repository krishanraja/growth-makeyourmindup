"""The content backlog: every published piece against channel and format. Synthetic fixtures only."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from engine import backlog
from engine.backlog import build, channel_matrix, for_runner, pilot_editions, read_ledger, record, summary_line
from engine.catalog import parse_feed
from engine.cc_loop import backlog_line, runner_report
from engine.core import read_json, write_json
from engine.social import validate

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-20T12:00:00Z'
FEED = (ROOT / 'tests' / 'fixtures' / 'feed.xml').read_bytes()
ARTICLE = 'https://home.makeyourmindup.ai/p/test-fixture'
VIDEO = 'https://home.makeyourmindup.ai/p/test-fixture-video'
OLD = {'schema_version': 2, 'pieces': {'piece_00000000000000000001': {
    'piece_id': 'piece_00000000000000000001', 'date': '2026-01-05', 'published_at': '2026-01-05T15:00:00+00:00',
    'title': 'TEST FIXTURE: an older piece the feed no longer carries', 'url': 'https://home.makeyourmindup.ai/p/test-old',
    'kind': 'article', 'subtitle': '', 'text': 'TEST FIXTURE ONLY.', 'links': [], 'revision': 'revision_x',
    'observed_at': '2026-01-06T00:00:00+00:00', 'evidence_status': 'available',
    'first_seen_at': '2026-01-06T00:00:00+00:00'}}}


def rows():
    return parse_feed(FEED, 366, NOW)


class Backlog(unittest.TestCase):
    def test_every_piece_is_listed_oldest_unamplified_first(self):
        result = build(rows(), OLD, {}, ROOT, NOW)
        self.assertEqual(result['pieces'][0]['url'], 'https://home.makeyourmindup.ai/p/test-old',
                         'a piece kept only in the catalog state is still in the backlog')
        self.assertTrue(all(p['status'] == 'unamplified' for p in result['pieces']))
        dates = [p['published_at'] for p in result['pieces']]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(result['summary']['remaining'], result['summary']['pieces'])
        self.assertNotIn('substack', [c['channel'] for c in result['channels']], 'the home is never an open edition')

    def test_editions_move_a_piece_to_partial_then_covered_and_behind_unamplified(self):
        matrix = channel_matrix(ROOT)
        one = {ARTICLE: [{'channel': 'x', 'format': 'text', 'source': 'ledger', 'native_url': 'https://x.com/i/1'}]}
        result = build(rows(), OLD, one, ROOT, NOW)
        statuses = [p['status'] for p in result['pieces']]
        self.assertEqual(statuses, sorted(statuses, key=backlog.STATUSES.index), 'unamplified before partial')
        mine = [p for p in result['pieces'] if p['url'] == ARTICLE]
        self.assertEqual(mine[0]['status'], 'partial')
        self.assertNotIn('x', mine[0]['channels_open'])
        every = {ARTICLE: [{'channel': c, 'format': None, 'source': 'ledger', 'native_url': None} for c in matrix]}
        covered = [p for p in build(rows(), OLD, every, ROOT, NOW)['pieces'] if p['url'] == ARTICLE][0]
        self.assertEqual((covered['status'], covered['channels_open']), ('covered', []))

    def test_a_video_post_with_an_explicit_link_folds_into_its_article(self):
        result = build(rows(), None, {VIDEO: [{'channel': 'youtube', 'format': 'short-video', 'source': 'ledger',
                                               'native_url': None}]}, ROOT, NOW)
        self.assertNotIn(VIDEO, [p['url'] for p in result['pieces']], 'the fixture pair links explicitly')
        self.assertEqual(result['pieces'][0]['video_post_url'], VIDEO)
        self.assertEqual(result['pieces'][0]['status'], 'partial', "the video post's edition counts for the story")

    def test_ledger_records_once_and_refuses_unknown_channels_and_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'amplified.json'
            self.assertTrue(record(path, ARTICLE + '?utm_source=x', 'x', 'text', 'https://x.com/i/1', NOW))
            self.assertFalse(record(path, ARTICLE, 'x', 'text', 'https://x.com/i/1', NOW), 'the same edition is not added twice')
            self.assertEqual(list(read_ledger(path, channel_matrix(ROOT))), [ARTICLE], 'tracking is stripped from the piece')
            for channel, fmt, url in (('substack', 'article', 'https://x.com/i/2'), ('x', 'carousel', 'https://x.com/i/2'),
                                      ('x', 'text', 'http://x.com/i/2')):
                with self.assertRaises(ValueError):
                    record(path, ARTICLE, channel, fmt, url, NOW)

    def test_pilot_records_count_with_their_piece(self):
        found = pilot_editions(ROOT)
        self.assertIn('https://home.makeyourmindup.ai/p/can-metas-muse-or-grok-bot-run-my', found)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'lists').mkdir()
            write_json(root / 'lists' / 'pilots.json', {'pilots': [{'pilot_id': 'p', 'channels': ['x']}]})
            self.assertEqual(pilot_editions(root, channel_matrix(ROOT)), {}, 'a pilot that names no piece counts for none')

    def test_the_committed_fixture_matches_the_schema_and_holds_no_live_data(self):
        fixture = read_json(ROOT / 'backlog' / 'fixture.json')
        validate(fixture, read_json(ROOT / 'backlog' / 'inventory.schema.json'))
        self.assertTrue(all(p['title'].startswith('TEST FIXTURE') for p in fixture['pieces']))
        ignored = (ROOT / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('.scratch/', ignored, 'the live inventory and ledger stay in ignored .scratch/')
        self.assertEqual(str(backlog.LEDGER.parts[0]), '.scratch')
        self.assertEqual(str(backlog.INVENTORY.parts[0]), '.scratch')

    def test_summary_line_names_the_remaining_count_and_the_oldest(self):
        line = summary_line(build(rows(), OLD, {}, ROOT, NOW))
        self.assertTrue(line.startswith('Backlog remaining 2: 2 of 2'), line)
        self.assertIn('Oldest unamplified: TEST FIXTURE: an older piece', line)

    def test_runner_report_carries_backlog_remaining(self):
        checks = [{'name': n, 'ok': True, 'stdout': '', 'stderr': ''} for n in ('self_test', 'doctor_offline', 'dry_run')]
        inventory, reason = for_runner(ROOT, NOW, fetch=lambda days, now: rows())
        self.assertIsNone(reason)
        lines = [a['line'] for a in runner_report(ROOT, 'r1', NOW, checks, 'synthetic', True, 'fixture', sent={},
                                                  backlog=(inventory, None))[0]['activity']]
        self.assertTrue(any(l.startswith('Backlog remaining 1: 1 of 1') for l in lines), lines)
        self.assertTrue(any('not visible to the runner' in l for l in lines))

        def broken(days, now):
            raise OSError('offline')
        unread = for_runner(ROOT, NOW, fetch=broken)
        self.assertEqual(unread[0], None)
        self.assertEqual(backlog_line(unread), 'Backlog remaining: not counted, ' + unread[1])
        self.assertTrue(backlog_line(None).startswith('Backlog remaining: not counted'))

    def test_cli_writes_the_inventory_locally(self):
        import growth
        with tempfile.TemporaryDirectory() as folder:
            feed, out = Path(folder) / 'feed.xml', Path(folder) / 'inventory.json'
            feed.write_bytes(FEED)
            with contextlib.redirect_stdout(io.StringIO()) as text:
                code = growth.main(['backlog', '--feed-file', str(feed), '--now', NOW, '--out', str(out),
                                    '--catalog', str(Path(folder) / 'none.json'), '--ledger', str(Path(folder) / 'none.json')])
            self.assertEqual(code, 0)
            self.assertIn('Backlog remaining', text.getvalue())
            validate(read_json(out), read_json(ROOT / 'backlog' / 'inventory.schema.json'))


if __name__ == '__main__':
    unittest.main()
