"""Krish approves the week's mix once on the board, and Growth fills it (Ruling, Krish, 2026-10-30: "approve the
week's mix once, let Growth fill it"; R124).

The board's mix press (content-engine picks/mix, read from GET /api/board/<Monday>/pieces `mix`) is the approval
for the derived (filler) lane: a post goes out only when the press is approved on the hash of the mix Growth
itself proposes from its own kept plan, and only inside it. Every word, id, digest and byte here is synthetic;
nothing reaches content.krishraja.com, controlcenter.krishraja.com or api.buffer.com.
"""
import copy
import unittest
from unittest import mock

try:
    import test_concept_release as T
    from test_run_autorelease import Fixture
except ImportError:  # run as tests.test_board_mix
    from tests import test_concept_release as T
    from tests.test_run_autorelease import Fixture

from engine import offday
from engine.run import autorelease, board_tick

WEEK = '2026-11-09'
# A growth-offdays/1 file as `growth.py mix offdays` writes it. Its hash below was computed by content-engine's own
# scripts/post-pack/week_board.py (read_growth_offdays, read_offdays, week_mix at content-engine b214ca1) on this
# exact file: Monday keeps two options, Tuesday keeps its first three (one with no formats shows its lane), and
# Thursday (one option) and Sunday (none) are left off.
OFFDAYS = {'schema': 'growth-offdays/1', 'week_of': WEEK, 'short': [], 'days': {
    '2026-11-09': [{'concept_id': 'meme-a', 'lane': 'meme', 'formats': ['instagram:meme', 'x:meme'], 'source_url': None,
                    'draft': 'Synthetic line a.', 'share_line': None, 'needs': [], 'ready': True},
                   {'concept_id': 'news-b', 'lane': 'positive_news', 'formats': ['x:single-image'],
                    'source_url': 'https://example.org/b', 'draft': 'Synthetic line b.', 'share_line': None, 'needs': [],
                    'ready': True}],
    '2026-11-10': [{'concept_id': 'meme-c', 'lane': 'meme', 'formats': ['tiktok:meme'], 'source_url': None,
                    'draft': 'Synthetic line c.', 'share_line': None, 'needs': [], 'ready': True},
                   {'concept_id': 'move-d', 'lane': 'level_up', 'formats': [], 'source_url': None,
                    'draft': 'Synthetic line d.', 'share_line': None, 'needs': [], 'ready': False},
                   {'concept_id': 'meme-e', 'lane': 'meme', 'formats': ['tiktok:meme'], 'source_url': None,
                    'draft': 'Synthetic line e.', 'share_line': None, 'needs': [], 'ready': True},
                   {'concept_id': 'meme-f', 'lane': 'meme', 'formats': ['youtube:meme'], 'source_url': None,
                    'draft': 'Synthetic line f.', 'share_line': None, 'needs': [], 'ready': True}],
    '2026-11-12': [{'concept_id': 'meme-g', 'lane': 'meme', 'formats': ['x:meme'], 'source_url': None,
                    'draft': 'Synthetic line g.', 'share_line': None, 'needs': [], 'ready': True}],
    '2026-11-15': []}}
KNOWN_DAYS = {'mon': ['instagram:meme, x:meme', 'x:single-image'], 'tue': ['level_up', 'tiktok:meme']}
KNOWN_SHA = '7b1cdce92248cff9607f44f1236f6cc633d15c9be6675eaa33c0786e61893269'


class ProposedMix(unittest.TestCase):
    def test_proposed_mix_reproduces_the_hash_the_board_computes(self):
        self.assertEqual(offday.proposed_mix(OFFDAYS, WEEK), (KNOWN_DAYS, KNOWN_SHA))

    def test_a_recorded_option_is_not_in_the_mix_and_other_weeks_or_dates_are_refused(self):
        doc = copy.deepcopy(OFFDAYS)
        doc['days']['2026-11-09'].append(dict(doc['days']['2026-11-09'][0], concept_id='rec-h', kind='recorded',
                                              formats=['instagram:reel']))
        self.assertEqual(offday.proposed_mix(doc, WEEK)[0]['mon'], KNOWN_DAYS['mon'])
        with self.assertRaises(ValueError):
            offday.proposed_mix(OFFDAYS, '2026-11-16')
        doc = copy.deepcopy(OFFDAYS)
        doc['days']['2026-11-16'] = doc['days']['2026-11-09']
        with self.assertRaises(ValueError):
            offday.proposed_mix(doc, WEEK)

    def test_the_board_mix_is_read_as_pressed_and_anything_else_is_malformed(self):
        self.assertIsNone(board_tick.board_mix({'days': [], 'mix': None}))
        pressed = {'approved': True, 'days': KNOWN_DAYS, 'mix_sha256': KNOWN_SHA, 'at': '2026-11-08T18:00:00Z'}
        self.assertEqual(board_tick.board_mix({'days': [], 'mix': pressed}), pressed)
        for bad in (dict(pressed, approved='yes'), dict(pressed, mix_sha256='nope'), dict(pressed, days={'xmas': []}),
                    dict(pressed, days={'mon': 'meme'}), 'approved'):
            with self.assertRaises(board_tick.BoardError) as caught:
                board_tick.board_mix({'mix': bad})
            self.assertEqual(caught.exception.code, 'board_mix_malformed')


class TheOnePress(T.ReleaseBase):
    """The derived lane end to end against the stand-ins, with the board's press as the week's approval."""

    def pressed(self, **kw):
        self.stage.propose()
        days, digest = self.stage.board.press(self.stage.plan, **kw)
        return days, digest

    def test_approved_on_the_hash_growth_proposed_releases(self):
        days, digest = self.pressed()
        self.assertIn('x:meme', days['tue'][-1].split(', '))
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['slots']), (0, {'scheduled': 1}), summary)
        self.assertEqual(summary['derived']['weeks'], {'2026-W46': 'approved'})
        self.assertEqual(self.buf.posts[T.P_DERIVED]['status'], 'scheduled')
        self.assertEqual(self.cc.decisions, [], 'no Control Center decision was needed: his one press approved it')

    def test_not_approved_holds_quietly(self):
        self.pressed(approved=False)
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds'], summary['loud']), (0, {'mix_not_approved': 1}, []), summary)
        self.stage.board.pressed = None  # never pressed
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {'mix_not_approved': 1}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_board_not_configured_or_unreadable_approves_nothing(self):
        self.pressed()
        self.stage.hand_derived()
        summary, code = autorelease.autorelease(self.cc.client(), self.buf.client(), T.NOW, True, T.fetch)
        self.assertEqual((code, summary['holds']), (0, {'mix_board_not_configured': 1}), summary)
        self.stage.board.error = 'board_unreachable'
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (1, {'mix_board_unreadable': 1}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_hash_mismatch_holds_loudly_and_proposes_again(self):
        days, digest = offday.proposed_mix(offday.options(self.stage.plan), WEEK)
        self.pressed(digest='0' * 64)
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (1, {'mix_hash_mismatch': 1}), summary)
        self.assertEqual(summary['derived']['repropose'], {'2026-W46': {'mix_sha256': digest, 'days': days}})
        # The right hash on days other than the ones Growth proposed is a mismatch too.
        self.pressed(days=dict(days, sun=['x:meme']))
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (1, {'mix_hash_mismatch': 1}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_format_or_a_day_outside_the_mix_never_releases(self):
        self.pressed()
        # A format the day's option does not carry (x:single-image is not in the meme's line).
        self.stage.hand_derived(self.stage.derived_slot(fmt='single-image'))
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {'outside_approved_mix': 1}), summary)
        self.assertEqual(self.buf.mutations(), [])
        # A day the mix does not have: Wednesday (no off-day options), an hour before its time.
        self.cc.reports = {k: v for k, v in self.cc.reports.items() if ':review:' not in k and ':index:' not in k}
        self.stage.hand_derived(self.stage.derived_slot(due='2026-11-11T14:00:00Z'))
        summary, code = self.release(now='2026-11-11T13:00:00Z')
        self.assertEqual((code, summary['holds']), (0, {'outside_approved_mix': 1}), summary)
        self.assertEqual(self.buf.mutations(), [])
        # Already live outside the mix (another path scheduled it): loud, and never unscheduled here.
        self.buf.posts[T.P_DERIVED].update(status='scheduled', dueAt='2026-11-11T14:00:00Z')
        summary, code = self.release(now='2026-11-11T13:00:00Z')
        self.assertEqual((code, summary['holds']), (1, {'scheduled_outside_mix': 1}), summary)
        self.assertEqual(self.buf.posts[T.P_DERIVED]['status'], 'scheduled')

    def test_outside_mix_is_pure_and_fails_closed(self):
        state = {'mix': {'days': {'tue': ['x:meme, tiktok:meme']}, 'options': {'tue': {'c1': 'x:meme, tiktok:meme'}}}}
        tuesday = '2026-11-10T14:00:00Z'
        self.assertFalse(autorelease.outside_mix(state, 'c1', 'x', 'meme', tuesday))
        self.assertTrue(autorelease.outside_mix(state, 'c2', 'x', 'meme', tuesday), 'another concept that day')
        self.assertTrue(autorelease.outside_mix(state, 'c1', 'instagram', 'meme', tuesday), 'another channel')
        self.assertTrue(autorelease.outside_mix(state, 'c1', 'x', 'meme', '2026-11-11T14:00:00Z'), 'another day')
        self.assertTrue(autorelease.outside_mix({}, 'c1', 'x', 'meme', tuesday), 'no binding: nothing is inside')
        self.assertTrue(autorelease.outside_mix(state, 'c1', 'x', 'meme', 'not a time'))

    def test_his_no_in_control_center_still_stops_the_pressed_week(self):
        items = self.stage.propose()
        self.stage.board.press(self.stage.plan)
        self.stage.decide(items[0], 'declined')
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['derived']['weeks']), (0, {'2026-W46': 'declined'}), summary)
        self.assertEqual(self.buf.mutations(), [])


class SeriesGoLivesUnaffected(unittest.TestCase):
    """A Monday, Wednesday or Friday go-live is still his per-post Control Center go-live, whatever the board says."""

    @classmethod
    def setUpClass(cls):
        cls.cc = T.StandIn().__enter__()
        cls.buf = T.BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_with(self, board):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        Fixture(self.cc, self.buf)
        return autorelease.autorelease(self.cc.client(), self.buf.client(), '2026-11-04T13:00:00Z', True, T.fetch,
                                       board=board)

    def test_series_go_lives_are_unaffected_by_the_mix(self):
        unpressed, mismatched = T.BoardStandIn(), T.BoardStandIn()
        mismatched.pressed = {'approved': True, 'days': {'mon': ['x:meme']}, 'mix_sha256': '0' * 64, 'at': None}
        outcomes = []
        for board in (None, unpressed, mismatched):
            summary, code = self.run_with(board)
            outcomes.append((code, summary['slots'], summary['golives']['releasable']))
            self.assertEqual(getattr(board, 'reads', 0), 0, 'a go-live never reads the board')
        self.assertEqual(outcomes, [(0, {'krish_click': 1, 'scheduled': 2}, 1)] * 3, outcomes)


if __name__ == '__main__':
    unittest.main()
