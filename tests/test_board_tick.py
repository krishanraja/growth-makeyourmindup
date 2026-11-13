"""The board tick (`growth.py run board tick`), against fakes only.

Every post, piece id and URL here is synthetic. No test reaches Buffer or the board.
"""
import datetime as dt
import unittest
import unittest.mock

from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.run import board_tick
from engine.run.release import BUFFER_NAME

NOW = '2026-11-02T19:00:00Z'  # Monday 2 November, 14:00 New York (EST)
MONDAY = '2026-11-02'
PIECE = '00000000-0000-4000-8000-000000000001'
WED_PIECE = '00000000-0000-4000-8000-000000000003'
SERVICES = {'instagram': 'instagram', 'youtube': 'youtube', 'tiktok': 'tiktok', 'x': 'twitter'}
URLS = {'instagram': 'https://www.instagram.com/reel/SYNTHETIC1/', 'youtube': 'https://www.youtube.com/shorts/SYNTHETIC1',
        'x': 'https://x.com/synthetic/status/1'}


def post(n, cid, due, link='native', status='sent'):
    return {'id': '{:024x}'.format(0xb0a000 + n), 'status': status, 'via': 'api', 'text': 'TEST FIXTURE ONLY.',
            'dueAt': due, 'sentAt': due, 'metrics': [],
            'externalLink': URLS.get(cid) if link == 'native' else link,
            'channelId': BUFFER_CHANNEL_ID[cid], 'channelService': SERVICES[cid],
            'channel': {'id': BUFFER_CHANNEL_ID[cid], 'name': BUFFER_NAME[cid], 'service': SERVICES[cid],
                        'isDisconnected': False, 'isLocked': False}}


class FakeBuffer:
    def __init__(self, posts):
        self.posts = posts

    def list_posts(self, status, since):
        return {'edges': [{'node': p} for p in self.posts]}

    def get_post(self, post_id):
        raise AssertionError('every listed post carries metrics')


class FakeBoard:
    def __init__(self, days=None, answers=None, refuse_pieces=None):
        self.days = days if days is not None else [
            {'day': 'mon', 'date': MONDAY, 'piece_id': PIECE, 'channels': ['substack', 'youtube', 'shorts', 'tiktok', 'reels']},
            {'day': 'wed', 'date': '2026-11-04', 'piece_id': WED_PIECE, 'channels': ['shorts', 'reels']}]
        self.answers, self.refuse_pieces = list(answers or []), refuse_pieces
        self.posts, self.reads = [], []

    def pieces(self, monday):
        self.reads.append(monday)
        if self.refuse_pieces:
            raise board_tick.BoardError(self.refuse_pieces, 401)
        return {'week': monday, 'days': self.days}

    def posted(self, monday, row):
        self.posts.append((monday, row))
        answer = self.answers.pop(0) if self.answers else {'ok': True}
        if isinstance(answer, board_tick.BoardError):
            raise answer
        return answer


SLOT = '2026-11-02T12:30:00-05:00'


class BoardTickTest(unittest.TestCase):
    def run_tick(self, posts, board=None, deliver=True):
        board = board or FakeBoard()
        return board, board_tick.tick(board, FakeBuffer(posts), now=NOW, deliver=deliver)

    def test_the_pieces_cut_at_its_series_slot_ticks_its_box_with_the_post_and_its_time(self):
        board, summary = self.run_tick([post(1, 'instagram', SLOT), post(2, 'youtube', SLOT)])
        self.assertEqual(summary['filed'], 2, summary)
        rows = {row['channel']: (monday, row) for monday, row in board.posts}
        self.assertEqual(set(rows), {'reels', 'shorts'})
        monday, row = rows['reels']
        self.assertEqual(monday, MONDAY)
        self.assertEqual(set(row), {'day', 'piece_id', 'channel', 'post_url', 'posted_at', 'buffer_post_id'})
        self.assertEqual((row['day'], row['piece_id'], row['post_url']), ('mon', PIECE, URLS['instagram']))
        self.assertEqual(row['posted_at'], '2026-11-02T17:30:00Z')
        self.assertEqual(row['buffer_post_id'], '{:024x}'.format(0xb0a001))

    def test_a_mix_post_at_another_time_that_day_is_never_ticked_as_the_piece(self):
        board, summary = self.run_tick([post(1, 'instagram', '2026-11-02T08:30:00-05:00')])
        self.assertEqual(board.posts, [])
        self.assertEqual(summary['left'], {'not_the_piece_slot': 1})

    def test_a_channel_the_day_has_no_box_for_is_left_alone(self):
        board, summary = self.run_tick([post(1, 'x', SLOT)])
        self.assertEqual(board.posts, [])
        self.assertEqual(summary['left'], {'no_box_for_channel': 1})

    def test_the_board_tick_never_ticks_linkedin(self):
        # Ruling (Krish, 2026-11-13): his personal LinkedIn is growth-mindmake's, so its box is that engine's to
        # tick. A LinkedIn post this engine sent before the handover is still read (judged as history), but at the
        # piece's own slot on a day whose board has a LinkedIn box it is left, never ticked.
        from engine import owners
        from engine.buffer_channels import HANDED_OFF_CHANNELS
        linkedin = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
        sent = {'id': '{:024x}'.format(0xb0a0ff), 'status': 'sent', 'via': 'api', 'text': 'TEST FIXTURE ONLY.',
                'dueAt': SLOT, 'sentAt': SLOT, 'metrics': [],
                'externalLink': 'https://www.linkedin.com/feed/update/urn:li:activity:7300000000000000000/',
                'channelId': linkedin, 'channelService': 'linkedin',
                'channel': {'id': linkedin, 'name': 'krish-raja', 'service': 'linkedin', 'isDisconnected': False,
                            'isLocked': False}}
        days = [{'day': 'mon', 'date': MONDAY, 'piece_id': PIECE, 'channels': ['linkedin', 'reels']}]
        board, summary = self.run_tick([sent, post(1, 'instagram', SLOT)], FakeBoard(days))
        self.assertEqual([row['channel'] for _, row in board.posts], ['reels'])
        self.assertEqual(summary['left'], {owners.HOLD: 1})
        self.assertNotIn('linkedin', board_tick.BOXES)
        entry = {'channel': 'linkedin', 'buffer_draft_id': sent['id'], 'due_at': SLOT}
        self.assertIsNone(board_tick.piece_row(entry, {MONDAY: (MONDAY, 'mon', PIECE)},
                                               lambda post_id: ('scheduled', SLOT), set()))

    def test_a_post_without_a_native_url_on_its_own_host_waits(self):
        board, summary = self.run_tick([post(1, 'instagram', SLOT, link=None),
                                        post(2, 'youtube', SLOT, link='https://example.org/not-native')])
        self.assertEqual(board.posts, [])
        self.assertEqual(summary['left'], {'no_native_url': 2})

    def test_a_scheduled_post_is_not_ticked_until_buffer_shows_it_sent(self):
        board, summary = self.run_tick([post(1, 'instagram', SLOT, status='scheduled')])
        self.assertEqual((board.posts, summary['sent']), ([], 0))

    def test_a_replay_answers_duplicate_and_a_wrong_day_is_counted_not_fatal(self):
        board = FakeBoard(answers=[{'ok': True, 'duplicate': True}, board_tick.BoardError('not_this_day', 409)])
        _, summary = self.run_tick([post(1, 'instagram', SLOT), post(2, 'youtube', SLOT)], board)
        self.assertEqual((summary['filed'], summary['duplicate'], summary['refused']), (0, 1, {'not_this_day': 1}))
        self.assertIsNone(summary['error'])

    def test_a_refused_token_stops_the_run_loudly(self):
        board = FakeBoard(refuse_pieces='board_token_refused')
        _, summary = self.run_tick([post(1, 'instagram', SLOT)], board)
        self.assertEqual(summary['error'], 'board_token_refused')
        self.assertEqual(board.posts, [])

    def test_a_dry_run_reads_and_posts_nothing(self):
        board, summary = self.run_tick([post(1, 'instagram', SLOT)], deliver=False)
        self.assertEqual((board.posts, summary['rows'], summary['deliver']), ([], 1, False))

    def test_a_board_day_with_a_bad_piece_id_or_date_is_ignored(self):
        days = board_tick.board_days({'days': [
            {'day': 'mon', 'date': '2026-11-03', 'piece_id': PIECE, 'channels': ['reels']},
            {'day': 'wed', 'piece_id': 'not-a-uuid', 'channels': ['reels']},
            {'day': 'fri', 'piece_id': PIECE, 'channels': ['reels'], 'slot': '17:30'}]}, dt.date(2026, 11, 2))
        self.assertEqual(list(days), ['fri'])
        self.assertEqual(days['fri']['slot'], '17:30')

    def test_a_slot_the_board_names_for_a_day_wins_over_the_series_time(self):
        board = FakeBoard(days=[{'day': 'mon', 'piece_id': PIECE, 'channels': ['reels'], 'slot': '08:30'}])
        _, summary = self.run_tick([post(1, 'instagram', '2026-11-02T08:30:00-05:00'), post(2, 'instagram', SLOT)], board)
        self.assertEqual((summary['filed'], summary['left']), (1, {'not_the_piece_slot': 1}), summary)

    def test_the_sent_listing_asks_buffer_for_when_it_went_out_and_its_native_url(self):
        from engine.run import buffer_api
        self.assertIn(' sentAt externalLink }', buffer_api.LINKED_QUERY)
        self.assertIn(' sentAt }', buffer_api.SENT_QUERY)
        self.assertNotIn('externalLink', buffer_api.SENT_QUERY, 'the measure job never depends on an unread field')
        self.assertNotIn('sentAt', buffer_api.POSTS_QUERY, 'the edit path never selects them')

    def test_without_the_token_the_cli_says_not_configured_and_exits_zero(self):
        lines = []
        with unittest.mock.patch.dict('os.environ', {board_tick.TOKEN_ENV: ''}):
            self.assertEqual(board_tick.main(['board', 'tick'], out=lines.append), 0)
        self.assertTrue(lines[0].startswith(board_tick.NOT_CONFIGURED))



class JudgedLiveTest(unittest.TestCase):
    """Each sent post goes to content-engine's judges as live, so each carousel or Short they passed counts once it
    goes out (Ruling, Krish, 2026-11-12: "each one that passes and goes live counts"), the mix posts included."""

    class JudgingBoard(FakeBoard):
        def __init__(self):
            super().__init__()
            self.judged = []

        def judge(self, monday, body):
            self.judged.append((monday, body))
            return {'marked': len(body.get('posts') or [])}

    def test_every_sent_post_with_its_native_link_is_reported_live_even_one_the_board_does_not_tick(self):
        board = self.JudgingBoard()
        mix = post(1, 'instagram', '2026-11-02T08:30:00-05:00')
        summary = board_tick.tick(board, FakeBuffer([mix, post(2, 'youtube', SLOT), post(3, 'x', SLOT, link=None)]), now=NOW, deliver=True)
        self.assertEqual(summary['judged_live'], 2, summary)
        (monday, body), = board.judged
        self.assertEqual((monday, body['op']), (MONDAY, 'live'))
        self.assertEqual([p['buffer_post_id'] for p in body['posts']], ['{:024x}'.format(0xb0a001), '{:024x}'.format(0xb0a002)])
        self.assertEqual(body['posts'][0]['url'], URLS['instagram'])

    def test_a_board_with_no_judges_route_reports_none(self):
        _, summary = BoardTickTest.run_tick(BoardTickTest(), [post(1, 'instagram', SLOT)])
        self.assertEqual(summary['judged_live'], 0)

if __name__ == '__main__':
    unittest.main()
