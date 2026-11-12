"""Any off-day post or idea moves to any day at Krish's press, and the move updates every place that names its day
(Ruling, Krish, 2026-11-12). The day lives in one place, content-engine's offday_items, read here through the board's
GET /api/board/<Monday>/pieces. This engine follows it three ways:

- it binds each option he approved to the day the board says, never the day its own plan first put it on, so a post he
  moved goes out on its new day and is held on the day it left (autorelease.bound_options, outside_mix);
- it hands its own options to the board through that place (POST /api/board/<Monday>/offdays), never a second file
  the board must merge (board_tick.offer);
- it writes back every off-day post it made, scheduled or posted, from its own record (POST /api/board/<Monday>/
  offday-posts), so the board shows it out and says plainly when one is still scheduled for a day it left
  (board_tick.post_rows, record_rows).

Every word, id and date here is synthetic; nothing reaches content.krishraja.com or api.buffer.com.
"""
import datetime as dt
import unittest
import unittest.mock

from engine.run import autorelease, board_tick

WEEK, NEXT = '2026-11-16', '2026-11-23'
KEPT = {'tue': [{'concept_id': 'meme-a', 'lane': 'meme', 'formats': ['instagram:meme'], 'draft': 'Synthetic a.'}],
        'thu': [{'concept_id': 'meme-b', 'lane': 'meme', 'formats': ['x:meme'], 'draft': 'Synthetic b.'}]}


def approved(day, cid, **extra):
    row = {'id': 'off-' + day + '-' + cid, 'day': day, 'option_id': cid, 'format': None, 'idea': {'hook': 'Synthetic'},
           'direction': None, 'mock': None, 'approved_at': '2026-11-12T15:00:00Z'}
    row.update(extra)
    return row


class BindingFollowsTheBoard(unittest.TestCase):
    def test_a_moved_option_is_bound_to_the_day_the_board_says(self):
        # He moved meme-a from Tuesday, where this engine planned it, to Friday.
        options = autorelease.bound_options(KEPT, [approved('fri', 'meme-a'), approved('thu', 'meme-b')])
        self.assertEqual(options, {'fri': {'meme-a': 'instagram:meme'}, 'thu': {'meme-b': 'x:meme'}})
        state = {'mix': {'options': options, 'days': {key: sorted(set(row.values())) for key, row in options.items()}}}
        tuesday = dt.datetime(2026, 11, 17, 17, 30, tzinfo=dt.timezone.utc)
        friday = dt.datetime(2026, 11, 20, 17, 30, tzinfo=dt.timezone.utc)
        self.assertTrue(autorelease.outside_mix(state, 'meme-a', 'instagram', 'meme', tuesday), 'never on the day it left')
        self.assertFalse(autorelease.outside_mix(state, 'meme-a', 'instagram', 'meme', friday), 'on its new day')

    def test_only_what_this_engine_proposed_binds(self):
        self.assertEqual(autorelease.bound_options(KEPT, [approved('fri', 'someone-else')]), {})
        recorded = {'tue': [dict(KEPT['tue'][0], kind='recorded')]}
        self.assertEqual(autorelease.bound_options(recorded, [approved('tue', 'meme-a')]), {})

    def test_the_board_read_carries_where_the_day_lives(self):
        row = approved('fri', 'meme-a', date='2026-11-20', item='growth:2026-11-16:meme-a', version=3,
                       moved_from={'week': WEEK, 'day': 'tue'})
        read = board_tick.board_offdays({'offdays': [row]})[0]
        self.assertEqual((read['day'], read['date'], read['item'], read['moved_from']), ('fri', '2026-11-20', 'growth:2026-11-16:meme-a', {'week': WEEK, 'day': 'tue'}))
        older = board_tick.board_offdays({'offdays': [approved('tue', 'meme-a')]})[0]
        self.assertEqual((older['date'], older['item'], older['moved_from']), (None, None, None))


class Board:
    def __init__(self, listed=None, answer=None):
        self.listed, self.answer, self.sent = listed or {}, answer or {'ok': True, 'offered': 2}, []

    def pieces(self, monday):
        return self.listed.get(monday, {'offdays': []})

    def offer(self, monday, doc):
        self.sent.append(('offdays', monday, doc))
        return self.answer

    def posts(self, monday, posts):
        self.sent.append(('posts', monday, posts))
        return {'ok': True, 'items': len({p['option'] for p in posts}), 'unknown': 0}


class GrowthHandsItsOptionsOver(unittest.TestCase):
    DOC = {'schema': 'growth-offdays/1', 'week_of': WEEK, 'short': [], 'days': {
        '2026-11-17': [{'concept_id': 'meme-a', 'lane': 'meme', 'formats': ['instagram:meme'], 'source_url': None,
                        'draft': 'Synthetic a.', 'share_line': None, 'needs': [], 'ready': True}],
        '2026-11-19': [{'concept_id': 'meme-b', 'lane': 'meme', 'formats': ['x:meme'], 'source_url': None,
                        'draft': 'Synthetic b.', 'share_line': None, 'needs': [], 'ready': True}]}}

    def test_a_dry_run_counts_and_sends_nothing(self):
        board = Board()
        self.assertEqual(board_tick.offer(board, self.DOC), {'week': WEEK, 'options': 2, 'deliver': False})
        self.assertEqual(board.sent, [])

    def test_delivered_through_the_one_place(self):
        board = Board(answer={'ok': True, 'offered': 2, 'his': 0, 'taken': 0, 'withdrawn': 1, 'left': [{'id': 'x', 'why': 'rest_day'}]})
        summary = board_tick.offer(board, self.DOC, deliver=True)
        self.assertEqual(summary, {'week': WEEK, 'options': 2, 'deliver': True, 'offered': 2, 'his': 0, 'taken': 0, 'withdrawn': 1, 'left': 1})
        self.assertEqual(board.sent[0][:2], ('offdays', WEEK))
        self.assertEqual(set(board.sent[0][2]), {'schema', 'week_of', 'days'})

    def test_anything_but_its_own_file_is_refused(self):
        with self.assertRaises(ValueError):
            board_tick.offer(Board(), {'schema': 'something-else', 'days': {}})
        with self.assertRaises(ValueError):
            board_tick.offer(Board(), dict(self.DOC, week_of='2026-11-17'))


class ItsOwnPostsGoBackToTheBoard(unittest.TestCase):
    """Tue 10 Nov's carousel went out on six channels and the board still said "With Growth": the write-back took only
    a day with a piece. Each off-day post this engine made, scheduled or posted now goes back to the board's one place,
    from its own record, and nothing it did not post."""

    def test_made_scheduled_and_live_from_its_own_record_under_the_week_the_option_is_on_now(self):
        listed = {WEEK: {'offdays': []}, NEXT: {'offdays': [approved('thu', 'meme-a')]}}
        placed = board_tick.placed_options(listed)
        self.assertEqual(placed, {'meme-a': (NEXT, 'thu', 'off-thu-meme-a')})
        entry = lambda channel, pid: {'concept_id': 'meme-a', 'channel': channel, 'due_at': '2026-11-26T17:30:00Z', 'buffer_draft_id': pid}
        entries = [entry('instagram', 'p1'), entry('x', 'p2'), entry('tiktok', 'p3'), entry('threads', 'p4'),
                   {'concept_id': 'not-approved', 'channel': 'x', 'due_at': '2026-11-26T17:30:00Z', 'buffer_draft_id': 'p5'}]
        status = {'p2': ('scheduled', '2026-11-26T17:30:00Z'), 'p3': ('draft', None), 'p4': ('error', None), 'p5': ('scheduled', '2026-11-26T17:30:00Z')}
        sent = {'p1': {'post_id': 'p1', 'channel': 'instagram', 'sent_at': '2026-11-26T17:34:00Z', 'external_link': 'https://www.instagram.com/p/synthetic1/'}}
        with unittest.mock.patch.object(board_tick, 'native_host', lambda channel, url, account=None: str(url).startswith('https://www.instagram.com/')):
            rows = board_tick.post_rows(entries, placed, status.get, sent)
        self.assertEqual(rows, {NEXT: [
            {'state': 'live', 'channel': 'instagram', 'url': 'https://www.instagram.com/p/synthetic1/', 'at': '2026-11-26T17:34:00Z', 'option': 'off-thu-meme-a', 'buffer_post_id': 'p1'},
            {'state': 'scheduled', 'channel': 'x', 'due_at': '2026-11-26T17:30:00Z', 'option': 'off-thu-meme-a', 'buffer_post_id': 'p2'},
            {'state': 'made', 'option': 'off-thu-meme-a', 'buffer_post_id': 'p3'}]},
            'a draft is made, an errored post is not reported, and what he never approved is not his item')

    def test_a_pieces_scheduled_posts_go_back_as_the_pieces_own(self):
        """Fri 13 Nov was scheduled while the board said "Ready to post: Growth posts it on the day" (Ruling, Krish,
        2026-11-12: the board shows exactly where everything is): a post of this engine's own that Buffer has scheduled
        on a day with a piece goes back as that piece's entry, with its time, and nothing for a post sent or unscheduled."""
        piece = '11111111-2222-4333-8444-555555555555'
        listed = {WEEK: {'offdays': [], 'days': [{'day': 'fri', 'date': '2026-11-20', 'piece_id': piece, 'channels': ['substack-notes']}]}}
        pieces = board_tick.piece_days(listed)
        self.assertEqual(pieces, {'2026-11-20': (WEEK, 'fri', piece)})
        entries = [{'concept_id': 'fri-note', 'channel': 'substack-notes', 'due_at': '2026-11-20T17:40:00Z', 'buffer_draft_id': 'n1'},
                   {'concept_id': 'fri-x', 'channel': 'x', 'due_at': '2026-11-20T17:40:00Z', 'buffer_draft_id': 'n2'},
                   {'concept_id': 'sat-x', 'channel': 'x', 'due_at': '2026-11-21T17:40:00Z', 'buffer_draft_id': 'n3'},
                   {'concept_id': 'fri-ig', 'channel': 'instagram', 'due_at': '2026-11-20T17:40:00Z', 'buffer_draft_id': 'n4'}]
        status = {'n1': ('scheduled', '2026-11-20T17:40:00.000Z'), 'n2': ('draft', None), 'n3': ('scheduled', '2026-11-21T17:40:00Z'), 'n4': ('scheduled', None)}
        sent = {'n4': {'post_id': 'n4'}}
        rows = board_tick.post_rows(entries, {}, status.get, sent, pieces=pieces)
        self.assertEqual(rows, {WEEK: [{'piece_id': piece, 'day': 'fri', 'state': 'scheduled', 'channel': 'substack-notes',
                                       'due_at': '2026-11-20T17:40:00Z', 'buffer_post_id': 'n1'}]},
                         'scheduled only, on a day with a piece, under its box; a draft, a day with no piece and a post sent are not')

    def test_live_only_with_the_posts_own_link_on_its_channel(self):
        placed = {'meme-a': (WEEK, 'tue', 'off-tue-meme-a')}
        sent = {'p1': {'post_id': 'p1', 'channel': 'instagram', 'sent_at': '2026-11-17T17:34:00Z', 'external_link': 'https://elsewhere.example/x'}}
        with unittest.mock.patch.object(board_tick, 'native_host', lambda channel, url, account=None: False):
            rows = board_tick.post_rows([{'concept_id': 'meme-a', 'channel': 'instagram', 'due_at': 'x', 'buffer_draft_id': 'p1'}], placed, lambda _p: None, sent)
        self.assertEqual(rows, {})

    def test_a_sessions_receipts_go_back_only_for_options_he_approved(self):
        placed = {'meme-a': (WEEK, 'tue', 'off-tue-meme-a')}
        rows = board_tick.record_rows([{'option': 'off-tue-meme-a', 'state': 'live', 'channel': 'instagram', 'url': 'https://www.instagram.com/p/x/', 'at': '2026-11-17T17:34:00Z'}], placed)
        self.assertEqual(rows, {WEEK: [{'state': 'live', 'channel': 'instagram', 'url': 'https://www.instagram.com/p/x/', 'at': '2026-11-17T17:34:00Z', 'option': 'off-tue-meme-a'}]})
        for bad in ([{'option': 'off-tue-other', 'state': 'live', 'channel': 'x', 'url': 'https://x.com/1'}],
                    [{'option': 'off-tue-meme-a', 'state': 'live', 'channel': 'x'}], [{'option': 'off-tue-meme-a', 'state': 'posted'}], {}):
            with self.assertRaises(ValueError):
                board_tick.record_rows(bad, placed)

    def test_delivered_to_the_boards_one_place(self):
        board = Board(listed={WEEK: {'offdays': [approved('tue', 'meme-a')]}})
        summary = board_tick.report_posts(board, None, None, {}, now='2026-11-17T20:00:00Z', deliver=True,
                                          record=[{'option': 'off-tue-meme-a', 'state': 'made', 'at': '2026-11-16T10:00:00Z'}])
        self.assertEqual((summary['posts'], summary['reported'], summary['error']), (1, 1, None))
        self.assertEqual(board.sent, [('posts', WEEK, [{'state': 'made', 'at': '2026-11-16T10:00:00Z', 'option': 'off-tue-meme-a'}])])


if __name__ == '__main__':
    unittest.main()
