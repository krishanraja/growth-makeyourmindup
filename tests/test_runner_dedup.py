"""The GitHub runner sends each ask once (plan item D2, 2026-10-29).

A clean runner keeps no state, so Control Center is its ledger: Krish's
decisions and the latest earlier runner report. The standing W45 to W52 plan
goes once as a stage plan behind strategy; an ask he answered, or one still
waiting on him, is never sent again; and the 26 October carousel pilot is
reported by its verdict path, never as a proposal. Synthetic fixtures only,
against the local stand-in.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import growth
from engine import cc_loop
from engine.cc_loop import already_sent, pilot_lines, runner_report, run_id_for, standing_plan
from engine.control_center import ProtocolError, build_report, objective, validate_report
from engine.core import instant, read_json, write_json
from engine.run.spec import ladder
from test_autonomy import CapableStandIn, decision
from test_control_center import NOW, TOKEN, checks

PLAN_ID = 'makeyourmindup:plan:w45-w52'
EXPERIMENTS = ['makeyourmindup:experiment:' + e['experiment_id']
               for e in read_json(Path(__file__).resolve().parents[1] / 'experiments.json')['experiments']]
ROOT = Path(__file__).resolve().parents[1]
YESTERDAY = run_id_for('runner', instant(NOW).replace(day=16))


def workspace(folder):
    for name in ('experiments.json', 'channels.json', 'journeys.json', 'automations.json',
                 'specs/standing-plan.json', 'lists/pilots.json'):
        (Path(folder) / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, Path(folder) / name)
    return folder


def ids(report):
    return [p['proposal_id'] for p in report['proposals']]


def holds(report, reason):
    return [h['detail'] for h in report['holds'] if h['reason'] == reason]


class FakeClient:
    """Answers decisions and report reads from memory; any listed failure raises."""

    def __init__(self, decisions=(), reports=None, fail=None):
        self._decisions, self._reports, self._fail, self.reads = list(decisions), dict(reports or {}), fail, []

    def decisions(self, since):
        if self._fail == 'decisions':
            raise ProtocolError('server_error', 500)
        return copy.deepcopy(self._decisions)

    def read_report(self, run_id):
        self.reads.append(run_id)
        if self._fail == 'reports':
            raise ProtocolError('server_error', 500)
        if run_id not in self._reports:
            raise ProtocolError('not_found', 404)
        return {'accepted': True, 'report': copy.deepcopy(self._reports[run_id])}


class StandingPlanTests(unittest.TestCase):
    def test_plan_is_a_stage_plan_behind_strategy_with_its_words(self):
        plan = standing_plan(ROOT)
        self.assertEqual((plan['proposal_id'], plan['stage'], plan['wall'], plan['parent_proposal_id']),
                         (PLAN_ID, 'plan', 'strategy', None))
        self.assertLessEqual(len(plan['exact_payload']), 8000)
        self.assertNotIn('\u2014', plan['exact_payload'] + plan['title'] + plan['why'])

    def test_plan_names_every_channel_record_and_each_week_s_ladder_rung(self):
        record = read_json(ROOT / 'specs/standing-plan.json')
        words = record['exact_payload']
        channels = {path.stem for path in (ROOT / 'social/channels').glob('*.json')}
        self.assertEqual(set(record['channels']), channels)
        for channel in channels:
            self.assertIn('- ' + channel, words.replace('x and tiktok', 'x\n- tiktok')
                          .replace('instagram (makeyourmind.up), facebook and youtube',
                                   'instagram\n- facebook\n- youtube'))
        rungs = ladder(ROOT)
        self.assertEqual(len(record['weeks']), 8)
        for number, week in enumerate(record['weeks'], 45):
            target = rungs[instant(week + 'T12:00:00Z').date()]
            self.assertIn('W' + str(number) + ' ' + format(target, ','), words)


class AlreadySentTests(unittest.TestCase):
    def test_reads_decisions_and_the_latest_earlier_runner_report_only(self):
        earlier = runner_report(ROOT, YESTERDAY, NOW, checks(), 'synthetic', True, 'fixture', sent={})[0]
        older = run_id_for('runner', instant(NOW).replace(day=10))
        client = FakeClient([{'proposal_id': EXPERIMENTS[0], 'decision': 'declined', 'decided_at': NOW}],
                            {YESTERDAY: earlier, older: {'proposals': [{'proposal_id': 'makeyourmindup:old'}], 'holds': []}})
        known = already_sent(client, instant(NOW))
        self.assertEqual(known[EXPERIMENTS[0]], 'declined')
        self.assertEqual(known[PLAN_ID], 'pending')
        self.assertNotIn('makeyourmindup:old', known)  # Stops at the latest report it finds.
        self.assertNotIn(run_id_for('runner', instant(NOW)), client.reads)  # A rerun today replays.

    def test_waiting_hold_carries_pending_asks_forward_across_quiet_days(self):
        day_one = runner_report(ROOT, 'makeyourmindup:2026-10-14:runner', NOW, checks(), 'synthetic', True, 'fixture',
                                sent={})[0]
        day_two = runner_report(ROOT, 'makeyourmindup:2026-10-15:runner', NOW, checks(), 'synthetic', True, 'fixture',
                                sent=already_sent(FakeClient(reports={'makeyourmindup:2026-10-14:runner': day_one}),
                                                  instant('2026-10-15T18:00:00Z')))[0]
        self.assertEqual(day_two['proposals'], [])
        # No report on the 16th; the 17th still finds every ask in the 15th's waiting hold.
        known = already_sent(FakeClient(reports={'makeyourmindup:2026-10-15:runner': day_two}), instant(NOW))
        self.assertEqual({pid for pid, state in known.items() if state == 'pending'}, {PLAN_ID, *EXPERIMENTS})

    def test_a_failed_read_returns_none(self):
        self.assertIsNone(already_sent(FakeClient(fail='decisions'), instant(NOW)))
        self.assertIsNone(already_sent(FakeClient(fail='reports'), instant(NOW)))


class RunnerDedupTests(unittest.TestCase):
    def report(self, sent):
        return runner_report(ROOT, 'makeyourmindup:2026-10-17:runner', NOW, checks(), 'synthetic', True, 'fixture',
                             sent=sent)[0]

    def test_first_run_proposes_the_plan_once(self):
        report = self.report({EXPERIMENTS[i]: 'pending' for i in range(len(EXPERIMENTS))})
        self.assertEqual(ids(report), [PLAN_ID])
        self.assertEqual(report['schema_version'], '1.1.0')
        self.assertEqual(holds(report, cc_loop.WAITING), [', '.join(EXPERIMENTS)])

    def test_pending_plan_is_not_sent_again(self):
        report = self.report({PLAN_ID: 'pending', **{e: 'pending' for e in EXPERIMENTS}})
        self.assertEqual(report['proposals'], [])
        self.assertIn(PLAN_ID, holds(report, cc_loop.WAITING)[0])

    def test_decided_plan_is_never_proposed_again(self):
        for verdict in ('approved', 'declined', 'done'):
            report = self.report({PLAN_ID: verdict, **{e: 'pending' for e in EXPERIMENTS}})
            self.assertNotIn(PLAN_ID, ids(report))
            self.assertNotIn(PLAN_ID, ' '.join(holds(report, cc_loop.WAITING)))
            self.assertIn('The standing W45 to W52 plan is answered (' + verdict + '); not proposed again',
                          [a['line'] for a in report['activity']])

    def test_answered_experiments_are_never_sent_again(self):
        sent = {PLAN_ID: 'pending', EXPERIMENTS[0]: 'declined', EXPERIMENTS[1]: 'approved'}
        report = self.report(sent)
        self.assertEqual(ids(report), EXPERIMENTS[2:])
        self.assertIn('Experiment asks Krish has answered: 2; none sent again', [a['line'] for a in report['activity']])

    def test_unread_ledger_proposes_nothing(self):
        report = self.report(None)
        self.assertEqual(report['proposals'], [])
        self.assertEqual(holds(report, cc_loop.UNREAD), ['decisions or earlier runner reports could not be read'])


class PilotVerdictTests(unittest.TestCase):
    def pilot(self, folder, **change):
        data = read_json(ROOT / 'lists/pilots.json')
        data['pilots'][0].update(change)
        write_json(Path(folder) / 'lists/pilots.json', data)
        return pilot_lines(folder, instant('2026-10-29T12:00:00Z'))

    def test_committed_pilot_awaits_measurement_with_what_closes_it(self):
        activity, held = pilot_lines(ROOT, instant('2026-10-30T12:00:00Z'))
        self.assertEqual(activity, [])
        self.assertEqual([h['reason'] for h in held], ['Pilot awaiting measurement'])
        self.assertIn('amplify-carousel-20261026: published 2026-10-26', held[0]['detail'])
        self.assertIn('judge window ended 2026-10-29', held[0]['detail'])
        self.assertIn("closed by the What-Works Analyst's verdict", held[0]['detail'])

    def test_measured_pilot_without_verdict_says_so(self):
        with tempfile.TemporaryDirectory() as folder:
            activity, held = self.pilot(folder, measured=[{'window': '72h', 'captured_at': '2026-10-29T19:00:00Z'}])
        self.assertEqual(activity, [])
        self.assertEqual(held[0]['reason'], 'Pilot measured, verdict not recorded yet')
        self.assertIn('measured at 72h; its judge window ends 2026-10-29', held[0]['detail'])

    def test_recorded_verdict_is_reported_not_proposed(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            activity, held = self.pilot(folder, verdict='insufficient', verdict_recorded_at='2026-11-01T15:00:00Z',
                                        measured=[{'window': '72h', 'captured_at': '2026-10-29T19:00:00Z'}])
            self.assertEqual(held, [])
            self.assertEqual(activity, [{'line': 'Pilot amplify-carousel-20261026 verdict: insufficient '
                                                 '(recorded 2026-11-01 by the What-Works Analyst)'}])
            report = runner_report(folder, 'r1', NOW, checks(), 'synthetic', True, 'fixture', sent={})[0]
            self.assertIn(activity[0], [{'line': a['line']} for a in report['activity']])
            self.assertFalse(any('pilot' in pid or 'carousel' in pid for pid in ids(report)))

    def test_unknown_verdict_is_refused_not_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            activity, held = self.pilot(folder, verdict='great', verdict_recorded_at='2026-11-01T15:00:00Z')
        self.assertEqual(activity, [])
        self.assertEqual(held[0]['reason'], 'Pilot record unreadable')


class RunnerCliDedupTests(unittest.TestCase):
    def runner(self, stand, folder):
        out = io.StringIO()
        with patch.object(growth, 'engine_client', lambda: stand.client()), patch.object(growth, 'ROOT', Path(folder)), \
                patch.object(cc_loop, 'runner_checks', lambda r: checks()), \
                patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': TOKEN}), contextlib.redirect_stdout(out):
            code = growth.main(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW])
        return code, out.getvalue()

    def test_two_days_send_each_ask_once_and_a_decision_ends_it(self):
        with CapableStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            # Yesterday's report, as the runner sent it before this change: the four experiments daily.
            stand.reports[YESTERDAY] = build_report(
                YESTERDAY, 'synthetic', NOW, 'fixture', NOW, 'held',
                [objective('new_subscribers', reason='Fixture: not measured')], [{'line': 'Fixture run'}],
                cc_loop.experiment_proposals(folder))
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            today = stand.reports[run_id_for('runner', instant(NOW))]
            validate_report(today)
            self.assertEqual(ids(today), [PLAN_ID])
            self.assertEqual(today['proposals'][0]['stage'], 'plan')

            # The next day: nothing to send, the plan and experiments wait on him.
            code, text = self.runner_on(stand, folder, '2026-10-18T18:00:00Z')
            self.assertEqual(code, 0, text)
            tomorrow = stand.reports['makeyourmindup:2026-10-18:runner']
            self.assertEqual(tomorrow['proposals'], [])
            self.assertEqual(set(holds(tomorrow, cc_loop.WAITING)[0].split(', ')), {PLAN_ID, *EXPERIMENTS})

            # He approves the plan: it is answered, and still never sent again.
            stand.decisions = [decision(today['proposals'][0], at='2026-10-18T20:00:00Z')]
            code, text = self.runner_on(stand, folder, '2026-10-19T18:00:00Z')
            self.assertEqual(code, 0, text)
            after = stand.reports['makeyourmindup:2026-10-19:runner']
            self.assertEqual(after['proposals'], [])
            self.assertNotIn(PLAN_ID, holds(after, cc_loop.WAITING)[0])
            self.assertIn('The standing W45 to W52 plan is answered (approved); not proposed again',
                          [a['line'] for a in after['activity']])
            self.assertEqual(['Pilot awaiting measurement'],
                             [h['reason'] for h in after['holds'] if h['reason'].startswith('Pilot')])

    def runner_on(self, stand, folder, now):
        out = io.StringIO()
        with patch.object(growth, 'engine_client', lambda: stand.client()), patch.object(growth, 'ROOT', Path(folder)), \
                patch.object(cc_loop, 'runner_checks', lambda r: checks()), \
                patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': TOKEN}), contextlib.redirect_stdout(out):
            code = growth.main(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', now])
        return code, out.getvalue()

    def test_an_unreadable_ledger_sends_no_ask(self):
        with CapableStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            with patch.object(cc_loop, 'already_sent', lambda *a, **k: None):
                code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            self.assertEqual(report['proposals'], [])
            self.assertIn(cc_loop.UNREAD, [h['reason'] for h in report['holds']])


if __name__ == '__main__':
    unittest.main()
