"""The directive's subscribers block (audit 2026-11-14, I-09): new subscribers by source as Control Center counts
them from Substack's notices, read tolerantly behind features.subscriber_sources. Synthetic figures only."""
import datetime as dt
from pathlib import Path
import tempfile
import unittest

from engine import cc_loop
from engine.core import read_json
from engine.run import learn

BLOCK = {'rule': 'TEST FIXTURE ONLY. Counted from Substack new-subscriber notices.', 'week_of': '2026-11-09',
         'total': 7, 'organic': 5, 'paid': 0, 'by_source': {'Substack Notes': 3, 'instagram': 2, 'Direct': 2},
         'unclassified': ['TEST FIXTURE ONLY'], 'this_week_so_far': 2, 'read_on': '2026-11-14T05:10:00Z'}


def directive(block=BLOCK, flag=True):
    body = {'directive_id': 'TEST', 'features': {cc_loop.SUBSCRIBERS_FEATURE: flag}}
    if block is not None:
        body['subscribers'] = block
    return {'directive': body}


class SubscribersBlockTests(unittest.TestCase):
    def test_served_behind_its_flag_only(self):
        self.assertEqual(cc_loop.subscribers_block(directive())['by_source'],
                         {'Direct': 2, 'Substack Notes': 3, 'instagram': 2})
        self.assertIsNone(cc_loop.subscribers_block(directive(flag=False)))
        self.assertIsNone(cc_loop.subscribers_block(directive(block=None)))
        self.assertIsNone(cc_loop.subscribers_block(None))

    def test_a_missing_figure_stays_missing_never_zero(self):
        block = dict(BLOCK, total=None, paid='3', organic=-1)
        del block['this_week_so_far']
        got = cc_loop.subscribers_block(directive(block))
        self.assertEqual((got['total'], got['paid'], got['organic'], got['this_week_so_far']), (None, None, None, None))

    def test_by_source_as_a_list_and_malformed_rows_are_left_out(self):
        rows = [{'source': 'Substack Notes', 'count': 3}, {'source': 'x', 'count': 'two'}, {'count': 1}, 'junk',
                {'source': 'x', 'count': 1}]
        got = cc_loop.subscribers_block(directive(dict(BLOCK, by_source=rows)))
        self.assertEqual(got['by_source'], {'Substack Notes': 3, 'x': 1})
        self.assertIsNone(cc_loop.subscribers_block(directive(dict(BLOCK, week_of='last week'))))

    def test_kept_locally_and_removed_when_not_served(self):
        with tempfile.TemporaryDirectory() as folder:
            path = cc_loop.keep_subscribers(folder, directive())
            self.assertEqual(read_json(path)['week_of'], '2026-11-09')
            self.assertIsNone(cc_loop.keep_subscribers(folder, directive(flag=False)))
            self.assertFalse(path.exists())

    def test_the_log_line_says_shape_never_a_count(self):
        line = cc_loop.subscribers_line(cc_loop.subscribers_block(directive()))
        self.assertEqual(line, 'subscribers by source: read for the week of 2026-11-09, 3 sources, 1 unclassified')
        self.assertIn('jobs/subscribers.md stands', cc_loop.subscribers_line(None))

    def test_learn_keeps_a_tally_beside_its_verdicts_and_says_its_own_week(self):
        tally = learn.by_source_tally(directive(), dt.date(2026, 11, 2))
        self.assertEqual((tally['read'], tally['week_of'], tally['same_week'], tally['by_source']['Substack Notes']),
                         ('served', '2026-11-09', False, 3))
        self.assertEqual(learn.by_source_tally(directive(flag=False), dt.date(2026, 11, 2)), {'read': 'absent'})
