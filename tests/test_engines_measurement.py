"""The Measurement & Allocation engine (engine/engines/measurement.py) and its replay of the 5 November incident.

The acceptance replay runs through the normal entry point, `growth.py engine start measurement`, on a copy of the
committed seeds: it counts Substack > Notes as one subscriber, leaves specific-post and outreach attribution
unknown, and makes a proportionate allocation recommendation with a revisit condition. Other cases are synthetic.
"""
import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import growth
from engine.engines import core
from engine.engines import measurement as msr

ROOT = Path(__file__).resolve().parents[1]
SUBS = 'msr-substack-new-subscribers'
MEMO = 'msr-allocation-2026-11-05'
SOURCE = {'kind': 'review', 'ref': 'docs/reviews/x.md', 'observed_at': '2026-11-05'}


def cli(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = growth.main(argv)
    return code, json.loads(buffer.getvalue())


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}


NOTES_ROWS = [{'path': ['Substack'], 'count': 1}, {'path': ['Substack', 'Notes'], 'count': 1}]


def reading(value=1, attribution=None, source_rows=NOTES_ROWS, **detail):
    base = {'metric': 'new_subscribers', 'value': value, 'unit': 'people', 'data_source': 'Substack',
            'read_at': '2026-11-05', 'week_of': '2026-11-02', 'window_start': None, 'window_end': None,
            'window_days': 7, 'source_rows': source_rows,
            'attribution': msr.attribute(source_rows) if attribution is None else attribution}
    base.update(detail)
    return {'id': 'msr-test-reading', 'engine': 'measurement', 'kind': 'observation', 'title': 'A reading',
            'state': 'recorded', 'source': SOURCE, 'next_owner': 'measurement', 'next_action': None,
            'revisit_when': 'next week', 'links': [], 'updated_at': '2026-11-05', 'detail': base}


def seeded_memo():
    return copy.deepcopy(core.load('measurement', ROOT, private=False)[MEMO])


def shared(*changed):
    """check_shared over the committed history with some records replaced."""
    everything = copy.deepcopy(core.all_records(ROOT, private=False))
    for r in changed:
        everything[r['engine']][r['id']] = r
    return msr.check_shared(everything)


class AcceptanceReplay(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines')

    def test_notes_is_one_subscriber_with_post_and_outreach_unknown_and_a_proportionate_memo(self):
        before = files(self.root)
        code, result = cli(['engine', 'start', 'measurement', '--now', '2026-11-05', '--root', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(files(self.root), before)
        rec = result['recover']
        now = rec['current_number']
        self.assertEqual((now['value'], now['counted'], now['week_target']), (1, 1, 86))
        self.assertEqual(now['attribution'], [{'class': 'source', 'count': 1, 'source_path': ['Substack', 'Notes'],
                                               'post': 'unknown', 'outreach': 'unknown'}])
        self.assertFalse(now['freshness']['stale'])
        self.assertFalse(rec['comparable_windows'][0]['comparable_with_current'])
        self.assertEqual(rec['largest_constraint']['stage'], 'acceptance')
        decision = rec['resource_decision']
        self.assertEqual(decision['question'], msr.QUESTION)
        self.assertEqual(result['next_action']['id'], MEMO)
        memo = core.load('measurement', self.root)[MEMO]
        self.assertEqual(msr.allocation_errors(memo['detail'], memo['links'], None), [])
        by_what = {r['what']: r for r in memo['detail']['recommendations']}
        notes = by_what['a bounded Notes follow-up']
        self.assertEqual((notes['action'], notes['basis']), ('test', 'performance'))
        self.assertIn('unknown', notes['uncertainty'])
        self.assertEqual(by_what['repeat Buffer video attempts']['action'], 'stop')
        self.assertEqual(memo['detail']['money']['proposed'] + memo['detail']['money']['approved'], [])
        for r in memo['detail']['recommendations']:
            self.assertTrue(r['reversal_condition'] and r['review_date'] == '2026-11-12')
            self.assertFalse(r['action'] == 'increase' and (r.get('cost') or 0) > 0)
        self.assertTrue(memo['revisit_when'])

    def test_the_30_october_reading_is_the_history_of_the_current_number(self):
        code, lines = cli(['engine', 'history', 'measurement', SUBS, '--root', str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual([(x['detail']['read_at'], x['detail']['value'], x['detail']['week_of']) for x in lines],
                         [('2026-10-30', 0, '2026-10-26'), ('2026-11-05', 1, '2026-11-02')])
        self.assertEqual(msr.ladder_target('2026-10-26'), 25)

    def test_committed_records_pass_check(self):
        self.assertEqual(core.check(ROOT), [])


class Attribution(unittest.TestCase):
    def test_a_parent_and_its_child_category_count_one_subscriber(self):
        rows = msr.attribute([{'path': ['Substack'], 'count': 1}, {'path': ['Substack', 'Notes'], 'count': 1}])
        self.assertEqual(rows, [{'class': 'source', 'count': 1, 'source_path': ['Substack', 'Notes'],
                                 'post': 'unknown', 'outreach': 'unknown'}])
        self.assertEqual(msr.counted(rows), 1)
        two = msr.attribute([{'path': ['Substack'], 'count': 3}, {'path': ['Substack', 'Notes'], 'count': 1}])
        self.assertEqual([(r['source_path'], r['count']) for r in two], [(['Substack'], 2), (['Substack', 'Notes'], 1)])
        with self.assertRaises(ValueError):
            msr.attribute([{'path': ['Substack'], 'count': 0}, {'path': ['Substack', 'Notes'], 'count': 1}])

    def test_source_never_implies_activity_and_double_counting_is_refused(self):
        self.assertEqual(core.validate(reading()), [])
        named = reading(attribution=[dict(msr.attribute([{'path': ['Substack', 'Notes'], 'count': 1}])[0],
                                          post='pub-some-note')])
        self.assertTrue(any('never implies an activity' in e for e in core.validate(named)))
        twice = reading(attribution=msr.attribute([{'path': ['Substack'], 'count': 1}])
                        + msr.attribute([{'path': ['Substack', 'Notes'], 'count': 1}]))
        self.assertTrue(any('once' in e for e in core.validate(twice)))

    def test_attribution_is_recomputed_from_the_platform_rows(self):
        # Substack 1 and Substack > Notes 1 can only come out as one subscriber.
        doubled = reading(value=2, attribution=msr.attribute([{'path': ['Substack'], 'count': 1}])
                          + msr.attribute([{'path': ['Substack', 'Notes'], 'count': 1}]))
        self.assertTrue(any('attribute(source_rows)' in e for e in core.validate(doubled)))
        self.assertTrue(core.validate(reading(attribution=msr.attribute(NOTES_ROWS), source_rows=None)))
        self.assertTrue(core.validate(reading(value=0, attribution=[])))
        self.assertEqual(core.validate(reading(value=0, attribution=[], source_rows=[])), [])

    def test_a_missing_reading_is_unavailable_never_zero(self):
        self.assertTrue(any('unavailable_reason' in e for e in core.validate(
            reading(value=None, attribution=[], source_rows=[]))))
        missing = reading(value=None, attribution=[], source_rows=[], unavailable_reason='not_shown')
        self.assertEqual(core.validate(missing), [])
        card = msr.scorecard(missing, '2026-11-05')
        self.assertEqual((card['organic_subscribers'], card['unavailable']), (None, {'new_subscribers': 'not_shown'}))

    def test_scorecard_reads_the_ladder_and_paid_never_counts(self):
        paid = [{'class': 'source', 'count': 2, 'source_path': ['Paid'], 'post': 'unknown', 'outreach': 'unknown',
                 'paid': True}] + msr.attribute([{'path': ['Substack', 'Notes'], 'count': 1}])
        card = msr.scorecard(reading(value=3, attribution=paid, source_rows=NOTES_ROWS), '2026-11-14')
        self.assertEqual((card['week_target'], card['organic_subscribers']), (86, 1))
        self.assertTrue(card['freshness']['stale'])
        self.assertFalse(card['paid_counted'])

    def test_a_scorecard_matches_the_ladder_and_its_linked_observation(self):
        card = copy.deepcopy(core.load('measurement', ROOT, private=False)['msr-scorecard-2026-11-02'])
        self.assertEqual(shared(card), [])
        card['detail']['week_target'] = 10
        self.assertTrue(any('ladder' in e for e in core.validate(card)))
        card['detail'].update(week_target=86, organic_subscribers=50)
        self.assertEqual(core.validate(card), [])
        self.assertTrue(any('scorecard()' in e for e in shared(card)))


class Allocation(unittest.TestCase):
    def errors(self, change):
        memo = seeded_memo()
        change(memo['detail'])
        return core.validate(memo)

    def shared(self, change):
        memo = seeded_memo()
        change(memo['detail'])
        return core.validate(memo) + shared(memo)

    def test_the_seeded_memo_is_valid(self):
        self.assertEqual(self.errors(lambda d: None), [])
        self.assertEqual(self.shared(lambda d: None), [])

    def test_a_basis_label_must_be_backed_by_its_evidence(self):
        for basis in ('standing_rule', 'owner_correction', 'operational_failure'):
            errors = self.shared(lambda d: d['recommendations'][2].update(action='increase', basis=basis))
            self.assertTrue(errors, basis)
        # A performance change needs a linked experiment that experiment_decision itself approves.
        self.assertTrue(self.shared(lambda d: d['recommendations'][2].update(action='increase',
                                                                           decision='review: trust me')))
        def trust_me(d):
            d['recommendations'][2].update(action='increase', experiment='msr-substack-new-subscribers')
        self.assertTrue(any('no experiment record' in e for e in self.shared(trust_me)))
        experiment = {'id': 'acq-notes-test', 'engine': 'acquisition', 'kind': 'experiment', 'state': 'running',
                      'source': SOURCE, 'detail': {'experiment_id': 'notes', 'status': 'running'}}
        memo = seeded_memo()
        memo['links'].append('acq-notes-test')
        memo['detail']['recommendations'][2].update(action='increase', experiment='acq-notes-test')
        self.assertTrue(any('experiment_decision' in e for e in shared(memo, experiment)))
        # A verified hold still applies at once; a stop on an owner correction needs Krish as the source.
        hold = ['pub-buffer-tiktok-video-hold']
        self.assertEqual(self.shared(lambda d: d['recommendations'][3].update(evidence=hold)), [])
        self.assertTrue(self.shared(lambda d: d['recommendations'][3].update(basis='owner_correction')))

    def test_the_question_and_every_field_are_required(self):
        self.assertTrue(self.errors(lambda d: d.update(question='What next?')))
        for name in ('reversal_condition', 'review_date', 'uncertainty', 'owner', 'evidence', 'from', 'to'):
            self.assertTrue(self.errors(lambda d: d['recommendations'][0].pop(name)), name)
        self.assertTrue(self.errors(lambda d: d['recommendations'][0].pop('sizing')))
        self.assertTrue(self.errors(lambda d: d['recommendations'][0].update(evidence=['msr-not-linked'])))

    def test_one_notes_subscriber_cannot_scale_notes(self):
        def scale(d):
            d['recommendations'][2]['action'] = 'increase'
        self.assertTrue(any('experiment_decision' in e for e in self.errors(scale)))
        with self.assertRaises(ValueError):
            msr.performance_decision({'minimum_observations': 5}, [], '2026-11-05')

    def test_operational_failures_apply_at_once(self):
        def stop(d):
            d['recommendations'][3].update(action='stop', basis='operational_failure')
        self.assertEqual(self.errors(stop), [])

    def test_money_rules(self):
        def spend(d):
            d['recommendations'][4].update(action='test', basis='owner_correction', cost=50)
        self.assertTrue(any('spend increase' in e for e in self.errors(spend)))
        # A declared spend case must be shown by the evidence: the funnel shows no placement, route or cost.
        for case in ('observed_placement', 'costed_bottleneck', 'conversion_route'):
            def spend_with_case(d):
                d['recommendations'][4].update(action='test', basis='owner_correction', cost=500, spend_case=case)
            self.assertEqual(self.errors(spend_with_case), [])
            self.assertTrue(any('evidence shows no' in e for e in self.shared(spend_with_case)), case)
        # A null cost does not skip the check when spending is what increases.
        def unsized(d):
            d['recommendations'][4].update(action='test', basis='owner_correction', cost=None, hours=None,
                                           sizing='Krish sizes')
        self.assertTrue(any('spend increase' in e for e in self.errors(unsized)))
        funnel = copy.deepcopy(core.load('measurement', ROOT, private=False)['msr-funnel-acquisition-2026-11-05'])
        funnel['detail']['losses'][0]['cost'] = 40
        def costed(d):
            d['recommendations'][4].update(action='test', basis='owner_correction', cost=500,
                                           spend_case='costed_bottleneck')
        memo = seeded_memo()
        costed(memo['detail'])
        self.assertEqual(shared(memo, funnel), [])
        # An increase also needs its basis shown: no committed record carries Krish as its source.
        memo['detail']['recommendations'][4]['action'] = 'increase'
        self.assertTrue(any('owner correction' in e for e in shared(memo, funnel)))
        boost = {'category': 'paid_boost', 'what': 'boost a post', 'amount': 20,
                 'spend_case': 'conversion_route', 'evidence': ['msr-funnel-acquisition-2026-11-05']}
        organic = dict(boost, counts_toward_north_star=True)
        self.assertTrue(self.errors(lambda d: d['money']['proposed'].append(organic)))
        self.assertEqual(self.errors(lambda d: d['money']['proposed'].append(
            dict(boost, counts_toward_north_star=False))), [])
        tool = {'category': 'tools', 'what': 'new tool', 'amount': 5000}
        self.assertTrue(any('spend_case' in e for e in self.errors(lambda d: d['money']['proposed'].append(tool))))
        unshown = dict(boost, counts_toward_north_star=False)
        self.assertTrue(self.shared(lambda d: d['money']['proposed'].append(unshown)))
        tool = {'category': 'tools', 'what': 'a tool', 'amount': 10}
        self.assertTrue(self.errors(lambda d: d['money']['approved'].append(tool)))
        self.assertEqual(self.errors(lambda d: d['money']['approved'].append(
            dict(tool, approved_by='krish', approved_at='2026-11-05'))), [])


class Recovery(unittest.TestCase):
    def test_judge_windows_and_overdue_handoffs(self):
        self.assertFalse(msr.judge_window_open('tiktok', '2026-11-03', '2026-11-05'))
        self.assertTrue(msr.judge_window_open('tiktok', '2026-11-02', '2026-11-05'))
        self.assertFalse(msr.judge_window_open('subscriber_impact', '2026-11-01', '2026-11-05'))
        edition = {'id': 'pub-x', 'next_owner': 'measurement', 'updated_at': '2026-11-01', 'state': 'done',
                   'detail': {'channel': 'tiktok', 'format': 'short-video'}}
        late = msr.overdue({}, {'publishing': {'pub-x': edition}}, '2026-11-05')
        self.assertEqual([(o['id'], o['due']) for o in late], [('pub-x', '2026-11-04')])
        self.assertEqual(msr.overdue({}, {'publishing': {'pub-x': edition}}, '2026-11-03'), [])


if __name__ == '__main__':
    unittest.main()
