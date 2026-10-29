"""W2.9 the off-day lane on top of the mix (Krish, 29 Oct: "Mix wins: every day"). Synthetic fixtures only."""
import datetime as dt
import unittest

try:
    from test_mix import WEEK, full_plan, ideas
except ImportError:
    from tests.test_mix import WEEK, full_plan, ideas

from engine import mix, offday
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.core import instant, ny_time

SHARE = {'sender': 'A head of finance', 'receiver': 'their chief executive, who keeps asking about AI budgets',
         'job': 'helps_them', 'moment': 'the Monday budget review when the AI line comes up again',
         'dm_line': 'This is the one I meant about the AI line', 'standalone': True}


class OffDays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = full_plan()

    def test_every_day_carries_two_or_three_filler_options_with_their_parts(self):
        board = offday.options(self.plan, ideas())
        self.assertEqual(len(board['days']), 7, 'every day, Monday to Sunday (Mix wins)')
        for day, opts in board['days'].items():
            self.assertLessEqual(len(opts), 3, day)
            for o in opts:
                self.assertIn(o['lane'], ('meme', 'positive_news', 'level_up'))
                self.assertTrue(o['formats'] and o['draft'])
                if o['lane'] == 'positive_news':
                    self.assertTrue(o['source_url'].startswith('https://'))
        self.assertTrue(all(s['options'] < 2 for s in board['short']))
        some = next(o for opts in board['days'].values() for o in opts)
        self.assertIsNone(some['share_line'])
        self.assertIn('needs its share block', some['needs'])

    def test_a_share_block_gives_its_share_line(self):
        with_share = [dict(i, share=SHARE) for i in ideas()]
        board = offday.options(self.plan, with_share)
        some = next(o for opts in board['days'].values() for o in opts)
        self.assertIn('sends it to', some['share_line'])

    def _scheduled(self, channel, day, n):
        due = mix.due_at(day, '08:30')
        return [{'id': '%024x' % (i + 1), 'status': 'scheduled', 'channelId': BUFFER_CHANNEL_ID[channel],
                 'dueAt': due} for i in range(n)]

    def test_topup_takes_the_next_free_filler_slot_and_never_the_series_slot(self):
        now = '2026-11-09T05:00:00Z'
        slot, why = offday.next_free_slot(self.plan, 'instagram', [], now)
        self.assertIsNone(why)
        self.assertIn(slot['lane'], ('meme', 'positive_news', 'level_up'))
        self.assertFalse(offday.reserved(slot, mix.load()))
        self.assertGreater(instant(slot['due_at']), instant(now) + dt.timedelta(minutes=90))
        # That day full on Buffer: the top-up moves to a later day.
        day = ny_time(instant(slot['due_at'])).date()
        full = self._scheduled('instagram', day, offday.day_cap(self.plan, 'instagram'))
        later, _ = offday.next_free_slot(self.plan, 'instagram', full, now)
        self.assertGreater(ny_time(instant(later['due_at'])).date(), day)
        taken, _ = offday.next_free_slot(self.plan, 'instagram', [], now, taken={slot['slot_id']})
        self.assertNotEqual(taken['slot_id'], slot['slot_id'])

    def test_no_topup_lands_over_a_cap_or_in_the_series_slot_across_every_hour_of_the_week(self):
        cfg = mix.load()
        start = instant('2026-11-08T12:00:00Z')
        for hours in range(0, 24 * 8, 3):
            now = (start + dt.timedelta(hours=hours)).isoformat()
            for channel in cfg['channels']:
                slot, why = offday.next_free_slot(self.plan, channel, [], now)
                if slot is None:
                    self.assertEqual(why, 'no_free_slot_this_week')
                    continue
                self.assertFalse(offday.reserved(slot, cfg), slot)
                self.assertEqual(slot['channel'], channel)

    def test_the_clock_facts(self):
        facts = offday.clock(self.plan, '2026-11-08T12:00:00Z')
        self.assertEqual(facts['stocked_by'][:16], '2026-11-08T20:00')
        self.assertFalse(facts['past_deadline'])
        self.assertEqual(facts['offday_stocked'], facts['stocked_slots'] == facts['filler_slots'])
        some = [s['slot_id'] for s in self.plan['slots'] if s['lane'] == 'meme'][:2]
        self.assertEqual(offday.clock(self.plan, '2026-11-09T12:00:00Z', some)['offday_slots_filled'], 2)

    def test_a_claim_with_a_figure_names_its_source(self):
        bad = [{'idea_id': 'x', 'lane': 'meme', 'idea': 'TEST FIXTURE', 'claim': 'AI cut costs 40% this year',
                'source_url': None, 'source_date': None}]
        result = mix.plan({'schema_version': 1, 'kind': 'backlog_inventory', 'pieces': []}, WEEK, bad, urgency=4)
        self.assertEqual(result['refused_ideas'][0]['why'], 'a claim with a number names the source that produced it')
        fine = [dict(bad[0], claim='Five moves for Monday at 9')]
        result = mix.plan({'schema_version': 1, 'kind': 'backlog_inventory', 'pieces': []}, WEEK, fine, urgency=4)
        self.assertEqual(result['refused_ideas'], [])


if __name__ == '__main__':
    unittest.main()


class ClockLines(unittest.TestCase):
    """W2.2 clock facts reach the report as activity lines until Control Center names their fields."""

    def test_offday_and_backstop_facts_are_reported_and_unknown_is_said(self):
        import json
        from pathlib import Path
        import tempfile
        from engine import cc_loop
        from engine.core import write_json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('mix.json',):
                (root / name).write_text((Path(mix.ROOT) / name).read_text(encoding='utf-8'), encoding='utf-8')
            import shutil
            shutil.copytree(Path(mix.ROOT) / 'social', root / 'social')
            shutil.copy(Path(mix.ROOT) / 'intensity.json', root / 'intensity.json')
            self.assertEqual(cc_loop.clock_lines(root, '2026-11-08T12:00:00Z'), [])
            write_json(root / cc_loop.MIX_DIR / ('plan-' + WEEK + '.json'), full_plan())
            (root / cc_loop.BACKSTOP_FILE).parent.mkdir(parents=True)
            (root / cc_loop.BACKSTOP_FILE).write_text(json.dumps({'posted': False}) + '\n' + json.dumps({'posted': True})
                                                      + '\n', encoding='utf-8')
            lines = cc_loop.clock_lines(root, '2026-11-08T12:00:00Z', taps=4)
        joined = ' | '.join(lines)
        self.assertIn('Clock engage: 4 engagement taps', joined)
        self.assertIn('Clock offday for the week of ' + WEEK + ': offday_stocked', joined)
        self.assertIn('Chat backstop: 1 flagged line', joined)
        self.assertIn('none sent', joined)
