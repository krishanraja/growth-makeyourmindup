"""The engine takes back its own asks once their week or window is over (Ruling, Krish, 2026-11-12: nothing on his
list is stale; an engine withdraws its own asks once their week or window has passed).

Krish sees one of this engine's asks at a time, so an ask about a week that is over holds every live one behind it.
Each runner report takes back (protocol 1.10.0 `withdrawn[]`) its own undecided asks whose week or window is over,
with a reason, carries what it took back forward so it is never taken back twice, never touches one he decided or one
still live, and nothing new is asked about a week that is over. Synthetic fixtures only, against local stand-ins.
"""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import growth
from engine import cc_loop, mix, stale_asks
from engine.cc_loop import already_sent, runner_report, run_id_for
from engine.control_center import ProtocolError, build_report, objective, validate_report
from engine.core import instant, read_json, write_json
from engine.run import cc_records, handoff, maker
from test_control_center import TOKEN, StandIn, checks
from test_runner_dedup import EXPERIMENTS, PLAN_ID, QUESTIONS_ID, ids, holds, workspace

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-13T12:00:00Z'  # Friday of the week of 9 November (W46): the week of 2 November (W45) is over
W45 = ['makeyourmindup:mix:2026-W45', 'makeyourmindup:mix:2026-W45:p2', 'makeyourmindup:mix:2026-W45:p3']
ASK_W45, ASK_W46 = 'makeyourmindup:mixask:2026-W45', 'makeyourmindup:mixask:2026-W46'
LIVE = {PLAN_ID: 'pending', **{e: 'pending' for e in EXPERIMENTS}, QUESTIONS_ID: 'pending'}


def setUpModule():
    # The runner reads the public feed for its backlog line; unit tests stay offline.
    global _OFFLINE
    from engine import backlog
    _OFFLINE = patch.object(backlog, 'read_feed', side_effect=OSError('offline test'))
    _OFFLINE.start()


def tearDownModule():
    _OFFLINE.stop()


def version_record(week_of, parts, number=1, now='2026-10-29T15:06:26Z'):
    version = {'schema': cc_records.VERSION, 'week_of': week_of,
               'parts': [{'proposal_id': pid, 'payload_sha256': str(n) * 64} for n, pid in enumerate(parts, 1)]}
    return handoff.version_report(week_of, number, version, now, ROOT)


class Records:
    """Control Center's report reads, as the route answers them: 404 for an address with nothing there."""

    def __init__(self, reports=(), fail=None):
        self.reports = {r['run_id']: r for r in reports}
        self.fail, self.reads = fail, []

    def read_report(self, run_id):
        self.reads.append(run_id)
        if self.fail:
            raise ProtocolError(self.fail, 500)
        if run_id not in self.reports:
            raise ProtocolError('not_found', 404)
        report = copy.deepcopy(self.reports[run_id])
        return {'accepted': True, 'run_id': run_id, 'mode': report['mode'],
                'payload_sha256': report['payload_sha256'], 'report': report}


def w45_records():
    return Records([version_record('2026-11-02', W45), maker.ask_report('2026-11-02', 'mix_not_approved', NOW, ROOT),
                    maker.ask_report('2026-11-09', 'mix_not_approved', NOW, ROOT)])


class WeekTests(unittest.TestCase):
    def test_a_week_ends_at_midnight_in_new_york_the_monday_after(self):
        self.assertEqual(stale_asks.week_ends('2026-11-09'), instant('2026-11-16T05:00:00Z'))
        self.assertEqual(stale_asks.week_ends('2026-10-26'), instant('2026-11-02T05:00:00Z'))  # after the clock change
        self.assertTrue(stale_asks.week_over('2026-11-02', NOW))
        self.assertFalse(stale_asks.week_over('2026-11-09', NOW))
        self.assertFalse(stale_asks.week_over('2026-11-09', '2026-11-16T04:59:59Z'))
        self.assertTrue(stale_asks.week_over('2026-11-09', '2026-11-16T05:00:00Z'))

    def test_a_window_closes_after_its_last_day_and_no_end_never_closes(self):
        self.assertFalse(stale_asks.window_over(None, NOW))
        self.assertFalse(stale_asks.window_over('not a day', NOW))
        self.assertFalse(stale_asks.window_over('2026-11-13', NOW))  # its last day is today
        self.assertTrue(stale_asks.window_over('2026-11-12', NOW))
        self.assertTrue(stale_asks.window_over('2026-11-13T11:00:00Z', NOW))

    def test_the_standing_plan_ends_with_its_last_week(self):
        plan = read_json(ROOT / 'specs/standing-plan.json')
        self.assertFalse(stale_asks.standing_over(plan, NOW))
        self.assertFalse(stale_asks.standing_over(plan, '2026-12-28T04:59:59Z'))
        self.assertTrue(stale_asks.standing_over(plan, '2026-12-28T05:00:00Z'))


class CandidateTests(unittest.TestCase):
    def test_every_part_of_an_ended_week_s_plan_and_its_ask_and_nothing_live(self):
        records = w45_records()
        found, error = stale_asks.week_candidates(records, instant(NOW))
        self.assertIsNone(error)
        self.assertEqual([pid for pid, _ in found], W45 + [ASK_W45])
        self.assertIn('2026-W45 (2026-11-02 to 2026-11-08), is over', found[0][1])
        # This week (W46) is live: neither its plan nor its ask is read as a candidate.
        self.assertNotIn(ASK_W46, [pid for pid, _ in found])
        self.assertFalse(any('2026-W46' in run_id for run_id in records.reads))
        # No week before the first mix plan is read.
        self.assertFalse(any('2026-W4' + str(n) in run_id for n in range(0, 5) for run_id in records.reads))

    def test_every_version_s_parts_count_once(self):
        records = Records([version_record('2026-11-02', W45), version_record('2026-11-02', W45[:2] + [W45[2] + '0'], 2)])
        found, _ = stale_asks.week_candidates(records, instant(NOW))
        self.assertEqual([pid for pid, _ in found], W45[:2] + [W45[2], W45[2] + '0'])

    def test_unread_records_take_nothing_back(self):
        self.assertEqual(stale_asks.week_candidates(Records(fail='server_error'), instant(NOW)),
                         ([], 'week_records_server_error'))

    def test_the_standing_plan_and_a_closed_experiment_window(self):
        self.assertEqual(stale_asks.local_candidates(ROOT, instant(NOW)), [])
        with tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            data = read_json(ROOT / 'experiments.json')
            data['experiments'][0]['end'] = '2026-11-12'
            write_json(Path(folder) / 'experiments.json', data)
            found = stale_asks.local_candidates(folder, instant(NOW))
            self.assertEqual([pid for pid, _ in found], [EXPERIMENTS[0]])
            self.assertIn('window closed on 2026-11-12', found[0][1])
            self.assertNotIn(EXPERIMENTS[0], [p['proposal_id'] for p in cc_loop.experiment_proposals(folder, instant(NOW))])
        later = stale_asks.local_candidates(ROOT, instant('2026-12-28T12:00:00Z'))
        self.assertEqual([pid for pid, _ in later], [PLAN_ID])

    def test_decided_ones_stay_withdrawn_ones_are_carried_and_the_cap_holds(self):
        cands = [(W45[0], 'over'), (W45[1], 'over'), (W45[2], 'over'), (ASK_W45, 'over'), (W45[0], 'twice')]
        out, carried = stale_asks.withdrawals(cands, {W45[1]: 'approved', W45[2]: stale_asks.WITHDRAWN})
        self.assertEqual(out, [{'proposal_id': W45[0], 'reason': 'over'}, {'proposal_id': ASK_W45, 'reason': 'over'}])
        self.assertEqual(carried, [W45[0], W45[2], ASK_W45])
        many = [('makeyourmindup:mix:2026-W45:p' + str(n), 'over') for n in range(2, 50)]
        out, carried = stale_asks.withdrawals(many, {})
        self.assertEqual((len(out), len(carried)), (40, 40))
        out, _ = stale_asks.withdrawals(cands, {}, proposed=[W45[0]])
        self.assertNotIn(W45[0], [w['proposal_id'] for w in out])


class RunnerTests(unittest.TestCase):
    def report(self, sent, weeks=None, now=NOW, run_id='makeyourmindup:2026-11-13:runner', root=ROOT):
        return runner_report(root, run_id, now, checks(), 'synthetic', True, 'fixture', sent=sent, weeks=weeks)[0]

    def test_the_ended_week_s_plan_is_taken_back_and_every_live_ask_stays(self):
        weeks = stale_asks.week_candidates(w45_records(), instant(NOW))
        report = self.report(dict(LIVE), weeks)
        validate_report(report)
        self.assertEqual([w['proposal_id'] for w in report['withdrawn']], W45 + [ASK_W45])
        self.assertTrue(all('is over, so it can no longer be approved' in w['reason'] for w in report['withdrawn']))
        self.assertEqual(report['schema_version'], '1.10.0')
        self.assertEqual(report['proposals'], [])
        self.assertEqual(set(holds(report, cc_loop.WAITING)[0].split(', ')), set(LIVE))
        self.assertEqual(holds(report, stale_asks.WITHDREW), [', '.join(W45 + [ASK_W45])])
        self.assertTrue(any(a['line'].startswith('Withdrew 4 of its own asks whose week or window is over')
                            for a in report['activity']))

        # The next day reads it back: nothing is taken back twice, and the hold still carries them.
        known = already_sent(_Ledger(report), instant('2026-11-14T12:00:00Z'), mode='synthetic')
        self.assertEqual({pid: known[pid] for pid in W45 + [ASK_W45]}, {pid: 'withdrawn' for pid in W45 + [ASK_W45]})
        tomorrow = self.report(known, stale_asks.week_candidates(w45_records(), instant('2026-11-14T12:00:00Z')),
                               '2026-11-14T12:00:00Z', 'makeyourmindup:2026-11-14:runner')
        self.assertNotIn('withdrawn', tomorrow)
        self.assertEqual(holds(tomorrow, stale_asks.WITHDREW), [', '.join(W45 + [ASK_W45])])
        self.assertEqual(tomorrow['proposals'], [])

    def test_a_part_he_decided_is_left_as_it_is(self):
        weeks = stale_asks.week_candidates(w45_records(), instant(NOW))
        report = self.report(dict(LIVE, **{W45[0]: 'declined'}), weeks)
        self.assertEqual([w['proposal_id'] for w in report['withdrawn']], W45[1:] + [ASK_W45])

    def test_an_unread_ledger_or_unread_records_take_nothing_back(self):
        weeks = stale_asks.week_candidates(w45_records(), instant(NOW))
        self.assertNotIn('withdrawn', self.report(None, weeks))
        report = self.report(dict(LIVE), ([], 'week_records_server_error'))
        self.assertNotIn('withdrawn', report)
        self.assertEqual(holds(report, stale_asks.UNREAD_WEEKS), ['week_records_server_error'])

    def test_after_its_last_week_the_standing_plan_is_never_asked_and_taken_back_if_it_waits(self):
        late = '2026-12-28T12:00:00Z'
        fresh = self.report({e: 'pending' for e in EXPERIMENTS}, ([], None), late, 'makeyourmindup:2026-12-28:runner')
        self.assertNotIn(PLAN_ID, ids(fresh))
        waiting = self.report(dict(LIVE), ([], None), late, 'makeyourmindup:2026-12-28:runner')
        self.assertEqual([w['proposal_id'] for w in waiting['withdrawn']], [PLAN_ID])
        self.assertNotIn(PLAN_ID, ' '.join(holds(waiting, cc_loop.WAITING)))
        decided = self.report(dict(LIVE, **{PLAN_ID: 'approved'}), ([], None), late, 'makeyourmindup:2026-12-28:runner')
        self.assertNotIn('withdrawn', decided)

    def test_a_closed_experiment_is_never_asked_and_taken_back_if_it_waits(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            data = read_json(ROOT / 'experiments.json')
            data['experiments'][0]['end'] = '2026-11-12'
            write_json(Path(folder) / 'experiments.json', data)
            fresh = self.report({PLAN_ID: 'pending'}, ([], None), root=folder)
            self.assertNotIn(EXPERIMENTS[0], ids(fresh))
            self.assertIn(EXPERIMENTS[1], ids(fresh))
            waiting = self.report(dict(LIVE), ([], None), root=folder)
            self.assertEqual([w['proposal_id'] for w in waiting['withdrawn']], [EXPERIMENTS[0]])


class _Ledger:
    """Yesterday's runner report and no decisions, as already_sent reads them."""

    def __init__(self, report):
        self.report = report

    def decisions(self, since):
        return []

    def read_report(self, run_id):
        if run_id != self.report['run_id']:
            raise ProtocolError('not_found', 404)
        return {'accepted': True, 'report': copy.deepcopy(self.report)}


class ProtocolTests(unittest.TestCase):
    def report(self, withdrawn, proposals=()):
        return build_report('makeyourmindup:2026-11-13:test', 'synthetic', NOW, 'fixture', NOW, 'held',
                            [objective('new_subscribers', reason='Fixture: not measured')], [{'line': 'Fixture run'}],
                            list(proposals), withdrawn=withdrawn)

    def test_the_field_is_checked_as_control_center_checks_it(self):
        self.assertEqual(self.report([{'proposal_id': W45[0], 'reason': 'Its week is over.'}])['schema_version'], '1.10.0')
        self.assertNotIn('withdrawn', self.report([]))
        for bad in ([{'proposal_id': 'growth-mindmake:x', 'reason': 'Not ours.'}],
                    [{'proposal_id': W45[0], 'reason': 'Write to someone@example.org.'}],
                    [{'proposal_id': W45[0], 'reason': ''}],
                    [{'proposal_id': W45[0], 'reason': 'x' * 301}],
                    [{'proposal_id': W45[0], 'reason': 'Once.'}, {'proposal_id': W45[0], 'reason': 'Twice.'}]):
            with self.assertRaises(ValueError):
                self.report(bad)
        item = cc_loop.experiment_proposals(ROOT)[0]
        with self.assertRaises(ValueError):
            self.report([{'proposal_id': item['proposal_id'], 'reason': 'Both.'}], [item])

    def test_it_goes_only_where_control_center_serves_withdrawn(self):
        report = self.report([{'proposal_id': W45[0], 'reason': 'Its week is over.'}])
        with StandIn() as stand:
            stand.capabilities = {'schema_versions': ['1.0.0', '1.10.0'], 'features': {'withdrawn': False}}
            with self.assertRaises(ProtocolError) as caught:
                stand.client().post_report(report)
            self.assertEqual(caught.exception.code, 'withdrawn_unsupported')
            self.assertEqual(stand.posts('reports'), [])
            stand.capabilities['features']['withdrawn'] = True
            self.assertTrue(stand.client().post_report(report)['accepted'])
            self.assertEqual(stand.reports[report['run_id']]['withdrawn'], report['withdrawn'])


class NoNewAskTests(unittest.TestCase):
    def test_a_week_s_plan_expires_when_its_week_ends(self):
        from test_mix import full_plan, WEEK
        cfg = mix.load(ROOT)
        plan = full_plan()
        built, _ = mix.part_proposals(plan, cfg)
        self.assertTrue(built)
        self.assertEqual({p['expires_at'] for p in built}, {'2026-11-16T05:00:00Z'})
        self.assertEqual(mix.plan_proposal(plan, cfg)['expires_at'], '2026-11-16T05:00:00Z')
        self.assertEqual(WEEK, '2026-11-09')

    def test_the_handoff_refuses_a_plan_for_a_week_that_is_over(self):
        from test_concept_release import dispatch_of, small_plan, stage_fetch
        with tempfile.TemporaryDirectory() as folder:
            summary, code = handoff.handoff(handoff.MIX_PLAN, dispatch_of(small_plan()), None, None,
                                            '2026-11-16T05:00:00Z', False, stage_fetch, ROOT,
                                            str(Path(folder) / 'handoff.json'))
        self.assertEqual((code, summary['error']), (1, 'payload_rejected_week_over'))
        self.assertEqual(summary['reports']['built'], 0)

    def test_the_maker_raises_no_ask_for_a_week_that_is_over(self):
        class Work:
            now = instant('2026-11-16T05:00:00Z')
            deliver = True
            cc = Records(fail='server_error')  # never read: the week is over first
            root = ROOT
        self.assertEqual(maker.raise_ask(Work, '2026-11-09', 'mix_not_approved'), 'week_over')
        self.assertEqual(Work.cc.reads, [])
        self.assertEqual(maker.ask_run_id('2026-W46'), ASK_W46)


class RunnerCliTests(unittest.TestCase):
    def test_the_runner_takes_back_the_ended_week_s_plan_in_its_report(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            workspace(folder)
            stand.capabilities = {'schema_versions': ['1.0.0', '1.1.0', '1.10.0'], 'features': {'withdrawn': True}}
            for report in w45_records().reports.values():
                stand.reports[report['run_id']] = report
            # Yesterday's runner report: the standing plan, the experiments and the questions wait on him.
            stand.reports['makeyourmindup:2026-11-12:runner'] = build_report(
                'makeyourmindup:2026-11-12:runner', 'synthetic', NOW, 'fixture', NOW, 'held',
                [objective('new_subscribers', reason='Fixture: not measured')], [{'line': 'Fixture run'}], [], [],
                cc_loop.id_holds(cc_loop.WAITING, sorted(LIVE)))
            out = io.StringIO()
            with patch.object(growth, 'engine_client', lambda: stand.client()), \
                    patch.object(growth, 'ROOT', Path(folder)), \
                    patch.object(cc_loop, 'runner_checks', lambda r: checks()), \
                    patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': TOKEN}), contextlib.redirect_stdout(out):
                code = growth.main(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW])
            self.assertEqual(code, 0, out.getvalue())
            today = stand.reports[run_id_for('runner', instant(NOW))]
            validate_report(today)
            self.assertEqual([w['proposal_id'] for w in today['withdrawn']], W45 + [ASK_W45])
            self.assertEqual(today['proposals'], [])
            self.assertIn('asks taken back, their week or window over: 4', out.getvalue())
            self.assertNotIn('2026-W45', out.getvalue())  # the public log carries counts, never ids


if __name__ == '__main__':
    unittest.main()
