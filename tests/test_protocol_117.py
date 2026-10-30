"""Protocol 1.17.0 (control-center main 58308115): buffer_channels, post_metrics and offdays, offline only.

Every plan, id and number here is synthetic or this engine's own pinned table. No test reaches Control Center.
"""
import datetime as dt
from pathlib import Path
import re
import tempfile
import unittest

try:
    from test_mix import WEEK, full_plan
except ImportError:
    from tests.test_mix import WEEK, full_plan

from engine import buffer_channels, cc_loop
from engine.control_center import CHANNELS_VERSION, build_report, objective
from engine.core import write_json

NOW = dt.datetime.fromisoformat(WEEK + 'T15:00:00+00:00')


def report(**extra):
    return build_report('makeyourmindup:test:117', 'synthetic', NOW, 'abc123', NOW, 'held',
                        [objective('paid_boosts_usd', reason='Nothing is spent')], [{'line': 'TEST FIXTURE ONLY.'}],
                        [], [], [{'reason': 'Nothing to do', 'detail': None}], **extra)


class Protocol117Tests(unittest.TestCase):
    def test_a_report_without_the_new_fields_keeps_its_old_version(self):
        self.assertNotEqual(report()['schema_version'], CHANNELS_VERSION)
        self.assertNotIn('buffer_channels', report())

    def test_buffer_channels_name_every_pinned_channel_and_deny_the_other_ventures(self):
        field = buffer_channels.report_field()
        self.assertEqual(field['allowed'], buffer_channels.BUFFER_CHANNEL_ID)
        self.assertEqual(set(field['denied']), set(buffer_channels.DENIED_CHANNELS))
        for name, bid in field['allowed'].items():
            self.assertRegex(name, r'^[a-z][a-z0-9_-]{0,31}$')
            self.assertRegex(bid, r'^[A-Za-z0-9]{8,64}$')
        built = report(buffer_channels=field)
        self.assertEqual((built['schema_version'], built['buffer_channels']), (CHANNELS_VERSION, field))

    def test_an_id_both_allowed_and_denied_is_refused_locally(self):
        field = buffer_channels.report_field()
        bad = dict(field, denied=field['denied'] + [field['allowed']['x']])
        with self.assertRaisesRegex(ValueError, 'both allowed and denied'):
            report(buffer_channels=bad)
        with self.assertRaisesRegex(ValueError, 'not a protocol field'):
            report(buffer_channels=dict(field, extra=[]))

    def test_post_metrics_take_null_never_zero_and_refuse_fractions(self):
        row = {'proposal_id': None, 'slot_id': 'buffer:' + 'a' * 24, 'channel': 'instagram',
               'posted_at': '2026-11-02T17:30:00Z', 'url': None, 'measured_at': '2026-11-03T07:00:00Z',
               'reach': 120, 'sends': None, 'saves': 3, 'likes': None, 'comments': 0}
        self.assertEqual(report(post_metrics=[row])['post_metrics'], [row])
        with self.assertRaises(ValueError):
            report(post_metrics=[dict(row, reach=1.5)])
        with self.assertRaises(ValueError):
            report(post_metrics=[dict(row, colour='red')])

    def test_offdays_go_out_from_the_kept_plan_with_only_the_read_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(cc_loop.offdays_field(folder, NOW))
            write_json(Path(folder) / cc_loop.MIX_DIR / ('plan-' + WEEK + '.json'), full_plan())
            field = cc_loop.offdays_field(folder, NOW)
        self.assertEqual((field['schema'], field['week_of']), ('growth-offdays/1', WEEK))
        self.assertLessEqual(len(field['days']), 7)
        options = [o for day in field['days'].values() for o in day]
        self.assertTrue(options)
        for option in options:
            self.assertEqual(set(option), {'concept_id', 'lane', 'ready'})
            self.assertRegex(option['concept_id'], r'^[a-z0-9][a-z0-9-]{0,63}$')
        self.assertEqual(report(offdays=field)['schema_version'], CHANNELS_VERSION)

    def test_the_offday_clock_line_matches_control_centers_parser(self):
        offday_line = re.compile(r'^Clock offday for the week of (\d{4}-\d{2}-\d{2}): offday_stocked (yes|no), '
                                 r'(\d+) of (\d+) filler slots ready(?:, (\d+) of (\d+) filler slots filled)?')
        with tempfile.TemporaryDirectory() as folder:
            write_json(Path(folder) / cc_loop.MIX_DIR / ('plan-' + WEEK + '.json'), full_plan())
            lines = [line for line in cc_loop.clock_lines(folder, NOW) if line.startswith('Clock offday')]
        self.assertTrue(lines and all(offday_line.match(line) for line in lines), lines)


if __name__ == '__main__':
    unittest.main()
