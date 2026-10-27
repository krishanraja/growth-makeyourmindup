"""The autonomy loop (protocol 1.1.0), amendments and the North Star objective.

GET-GOING Step 1, proved against the local Control Center stand-in: an
approved plan never goes live, an approved go-live goes live once with
exactly its payload, an amended one goes live in his words, and a declined
check-in stops its plan. Every fixture is synthetic; nothing here posts.
"""
import copy
import hashlib
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit

from engine import cc_loop
from engine.cc_loop import (claim_golives, golive_ledger, new_subscribers, observation_line, runner_report,
                            workspace_report)
from engine.control_center import (AUTONOMY_VERSION, SCHEMA_VERSION, amended_digest, build_report,
                                   golive_actions, golive_review, match_decisions, objective, proposal,
                                   report_digest, validate_report)
from engine.core import read_json
from engine.operations import aggregate
from test_control_center import NOW, PREFIX, ROOT, TOKEN, StandIn, checks, clock, envelope, observation

PLAN_ID = 'makeyourmindup:plan:fixture-week'
PLAN_WORDS = 'TEST FIXTURE ONLY. Plan: one useful Note a day for the fixture week.'
GO_WORDS = 'TEST FIXTURE ONLY. The engine wrote this Note.'
HIS_WORDS = 'TEST FIXTURE ONLY. Krish rewrote this Note.'


def plan():
    return proposal(PLAN_ID, 'Plan the fixture week', 'Fixture plan.', 'advice', 'strategy', 'reviewed',
                    exact_payload=PLAN_WORDS, stage='plan')


def go_live(words=GO_WORDS, pid='makeyourmindup:golive:fixture-a', parent=PLAN_ID, channel='substack', **extra):
    return proposal(pid, 'Go live with the fixture Note', 'Fixture go-live.', 'prepared', 'post', 'published',
                    channel=channel, exact_payload=words, stage='go_live', parent_proposal_id=parent, **extra)


def check_in(pid='makeyourmindup:checkin:fixture'):
    return proposal(pid, 'On track?', 'Fixture check-in.', 'advice', 'strategy', 'reviewed',
                    exact_payload='TEST FIXTURE ONLY. Two of seven Notes live.', stage='check_in',
                    parent_proposal_id=PLAN_ID)


def decision(item, verdict='approved', at=NOW, **extra):
    row = {'proposal_id': item['proposal_id'], 'decision': verdict, 'decided_at': at,
           'payload_sha256': item['payload_sha256'], 'stage': item.get('stage'), 'amended': False}
    row.update(extra)
    return row


def amended(item, words, amount=None, at=NOW):
    return decision(item, at=at, amended=True, exact_payload=words, amount_usd=amount,
                    amended_sha256=amended_digest(amount, words))


class CapableStandIn(StandIn):
    """The stand-in, also serving capabilities with the versions given (None: no such route)."""

    def __init__(self, versions=(SCHEMA_VERSION, AUTONOMY_VERSION)):
        super().__init__()
        self.versions = None if versions is None else list(versions)
        stand, base = self, self.server.RequestHandlerClass

        class Handler(base):
            def handle_any(self, method):
                path = urlsplit(self.path).path
                if method == 'GET' and path == PREFIX + 'capabilities' and stand.versions is not None:
                    stand.calls.append({'method': method, 'path': path, 'query': '', 'key': None, 'body': None,
                                        'auth': self.headers.get('Authorization')})
                    if self.headers.get('Authorization') != 'Bearer ' + stand.token:
                        return self.reply(401, {'error': 'unauthorized'})
                    return self.reply(200, {'schema_version': '1.5.0', 'schema_versions': stand.versions,
                                            'autonomy': 'autonomous', 'engine_id': 'growth-makeyourmindup',
                                            'product_slug': 'publication', 'idempotency': True})
                return base.handle_any(self, method)

        self.server.RequestHandlerClass = Handler


def fixture_report(proposals, run_id='makeyourmindup:2026-10-17:autonomy'):
    return build_report(run_id, 'synthetic', NOW, 'fixture', NOW, 'ready',
                        [objective('new_subscribers', reason='Fixture: not measured')],
                        [{'line': 'Fixture run'}], proposals)


def round_trip(proposals, decisions):
    """Report the proposals to the stand-in, then read his decisions back through the client."""
    with CapableStandIn() as stand:
        stand.decisions = decisions
        client = stand.client()
        report = fixture_report(proposals)
        posted = client.post_report(report)
        if not posted['accepted']:
            raise AssertionError('the stand-in did not accept the fixture report')
        reported = copy.deepcopy(stand.reports[report['run_id']]['proposals'])
        read = client.decisions(NOW)
    return reported, read


class AutonomyLoopTests(unittest.TestCase):
    def test_approved_plan_never_goes_live(self):
        reported, read = round_trip([plan(), go_live()], [decision(plan())])
        review = golive_review(reported, read)
        self.assertEqual(review['actions'], [])
        self.assertEqual(review['holds'], [{'proposal_id': go_live()['proposal_id'], 'reason': 'not_approved'}])
        # Even approved on its exact digest, a plan alone is never an action.
        self.assertEqual(golive_actions([plan()], [decision(plan())]), [])
        # A go-live approved under a plan he has not approved does not act either.
        held = golive_review([plan(), go_live()], [decision(go_live())])
        self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'plan_not_approved'))
        # An approval with no readable decided_at is never taken as the newest decision.
        decline = decision(go_live(), 'declined', at='2026-10-17T19:00:00Z')
        for when in ('missing', None, 'not a time'):
            approval = decision(go_live())
            if when == 'missing':
                del approval['decided_at']
            else:
                approval['decided_at'] = when
            held = golive_review([plan(), go_live()], [decision(plan()), decline, approval])
            self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'undated_decision'))
            self.assertEqual(golive_actions([plan(), go_live()], [decision(plan()), approval]), [])
        # Nor does an undated decline let an earlier approval act.
        late = dict(decision(go_live(), 'declined'), decided_at='yesterday')
        held = golive_review([plan(), go_live()], [decision(plan()), decision(go_live()), late])
        self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'undated_decision'))

    def test_approved_go_live_goes_live_once_with_exact_payload(self):
        reported, read = round_trip([plan(), go_live()], [decision(plan()), decision(go_live())])
        actions = golive_actions(reported, read)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual((action['proposal_id'], action['parent_proposal_id']), (go_live()['proposal_id'], PLAN_ID))
        self.assertEqual((action['wall'], action['channel'], action['exact_payload']), ('post', 'substack', GO_WORDS))
        self.assertEqual(action['payload_sha256'], go_live()['payload_sha256'])
        self.assertFalse(action['amended'])
        with tempfile.TemporaryDirectory() as folder:
            first = claim_golives(folder, reported, read, NOW)
            self.assertEqual(first['actions'], actions)
            path = Path(folder) / '.scratch/cc/golive-ledger.json'
            self.assertTrue(path.exists())
            self.assertFalse(Path(str(path) + '.lock').exists())
            again = claim_golives(folder, reported, read, NOW)
            self.assertEqual(again['actions'], [])
            self.assertEqual(again['holds'], [{'proposal_id': action['proposal_id'], 'reason': 'already_acted'}])
            self.assertEqual(golive_actions(reported, read, golive_ledger(folder)), [])
            self.assertEqual(len(read_json(path)['acted']), 1)
            # Once claimed it never acts again: not on a later amendment of his...
            later = amended(go_live(), HIS_WORDS, at='2026-10-17T20:00:00Z')
            self.assertEqual(len(golive_actions(reported, read + [later])), 1, 'without the ledger it would act')
            again = claim_golives(folder, reported, read + [later], NOW)
            self.assertEqual((again['actions'], again['holds'][0]['reason']), ([], 'already_acted'))
            # ...nor when the engine changes its words and he approves them again.
            changed = go_live('TEST FIXTURE ONLY. The engine changed its words.')
            decisions = [decision(plan()), decision(changed, at='2026-10-17T20:00:00Z')]
            self.assertEqual(len(golive_actions([plan(), changed], decisions)), 1, 'without the ledger it would act')
            again = claim_golives(folder, [plan(), changed], decisions, NOW)
            self.assertEqual((again['actions'], again['holds'][0]['reason']), ([], 'already_acted'))
            self.assertEqual(len(read_json(path)['acted']), 1)

    def test_amended_go_live_goes_live_in_his_words(self):
        reported, read = round_trip([plan(), go_live()], [decision(plan()), amended(go_live(), HIS_WORDS)])
        actions = golive_actions(reported, read)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['exact_payload'], HIS_WORDS)
        self.assertTrue(actions[0]['amended'])
        self.assertEqual(actions[0]['amended_sha256'], amended_digest(None, HIS_WORDS))
        # His yes was still to the proposal he was shown.
        self.assertEqual(actions[0]['payload_sha256'], go_live()['payload_sha256'])

    def test_declined_check_in_stops_its_plan(self):
        reported, read = round_trip([plan(), go_live(), check_in()],
                                    [decision(plan()), decision(go_live()), decision(check_in(), 'declined')])
        review = golive_review(reported, read)
        self.assertEqual(review['actions'], [])
        self.assertEqual(review['holds'], [{'proposal_id': go_live()['proposal_id'], 'reason': 'plan_stopped'}])
        self.assertIn(PLAN_ID, review['stopped'])
        with tempfile.TemporaryDirectory() as folder:
            claim_golives(folder, reported, read, NOW)
            self.assertIn(PLAN_ID, golive_ledger(folder)['stopped'])
            # Later the purged check-in is gone and a new go-live under the plan is approved: it still never acts.
            later = go_live('TEST FIXTURE ONLY. A later Note.', pid='makeyourmindup:golive:fixture-b')
            proposals, decisions = [plan(), later], [decision(plan()), decision(later)]
            self.assertEqual(len(golive_actions(proposals, decisions)), 1, 'without the ledger the stop is unknown')
            stopped = claim_golives(folder, proposals, decisions, NOW)
            self.assertEqual(stopped['actions'], [])
            self.assertEqual(stopped['holds'][0]['reason'], 'plan_stopped')
        # A purged check-in whose own record is not at hand stops an unknown plan, so nothing acts.
        purge = decision(check_in(), 'declined')
        approvals = [decision(plan()), decision(go_live())]
        blind = golive_review([plan(), go_live()], approvals + [purge])
        self.assertEqual((blind['actions'], blind['holds'][0]['reason']), ([], 'stop_unresolved'))
        self.assertIn(check_in()['proposal_id'], blind['unresolved'])
        with tempfile.TemporaryDirectory() as folder:
            held = claim_golives(folder, [plan(), go_live()], approvals + [purge], NOW)
            self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'stop_unresolved'))
            # It stays held after the decline leaves the decisions read.
            held = claim_golives(folder, [plan(), go_live()], approvals, NOW)
            self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'stop_unresolved'))
            # The check-in reported earlier is read back from the workspace, and its plan stops.
            cc_loop.remember(folder, fixture_report([plan(), go_live(), check_in()]), [], NOW)
            held = claim_golives(folder, [plan(), go_live()], approvals, NOW)
            self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'plan_stopped'))
            ledger = golive_ledger(folder)
            self.assertEqual((ledger['stopped'][PLAN_ID]['by'], ledger['unresolved']), (check_in()['proposal_id'], {}))
            self.assertEqual(ledger['acted'], {})

    def test_expired_go_live_never_goes_live(self):
        old = go_live(expires_at='2026-10-16T18:00:00Z')
        decisions = [decision(plan()), decision(old)]
        with tempfile.TemporaryDirectory() as folder:
            review = claim_golives(folder, [plan(), old], decisions)  # Its defaults: now is the clock.
            self.assertEqual((review['actions'], review['holds'][0]['reason']), ([], 'expired'))
            self.assertEqual(golive_ledger(folder)['acted'], {})
        # Without a now an expiring go-live cannot be checked, so it is held, never offered.
        held = golive_review([plan(), old], decisions)
        self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'expiry_unchecked'))
        in_date = go_live(expires_at='2026-10-18T18:00:00Z')
        self.assertEqual(len(golive_actions([plan(), in_date], [decision(plan()), decision(in_date)], None, NOW)), 1)
        unreadable = dict(in_date, expires_at='soon')
        held = golive_review([plan(), unreadable], [decision(plan()), decision(in_date)], None, NOW)
        self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'bad_expiry'))

    def test_amended_payload_wins_and_binds(self):
        decisions = [decision(plan()), amended(go_live(), HIS_WORDS)]
        action = golive_actions([plan(), go_live()], decisions)[0]
        self.assertEqual(action['exact_payload'], HIS_WORDS)
        self.assertNotEqual(action['exact_payload'], go_live()['exact_payload'])
        self.assertTrue(match_decisions(decisions, [plan(), go_live()])[1]['usable_approval'])
        # The action digest binds his words: another wording is another action.
        other = golive_actions([plan(), go_live()], [decision(plan()), amended(go_live(), HIS_WORDS + ' More.')])[0]
        self.assertNotEqual(action['action_sha256'], other['action_sha256'])
        # If the engine changes its payload after his decision, his yes and his version both lapse.
        edited = go_live('TEST FIXTURE ONLY. The engine changed its mind.')
        review = golive_review([plan(), edited], decisions)
        self.assertEqual((review['actions'], review['holds'][0]['reason']), ([], 'stale_approval'))
        # An amended amount never spends: this engine has no spend authority.
        spend = golive_review([plan(), go_live()], [decision(plan()), amended(go_live(), HIS_WORDS, 5)])
        self.assertEqual((spend['actions'], spend['holds'][0]['reason']), ([], 'no_spend_authority'))
        # LinkedIn stays his own click, approved or not.
        for channel in ('linkedin', 'LinkedIn ', 'linkedin_personal'):
            linkedin = go_live(channel=channel)
            held = golive_review([plan(), linkedin], [decision(plan()), decision(linkedin)])
            self.assertEqual((held['actions'], held['holds'][0]['reason']), ([], 'linkedin_is_krish_click'))

    def test_amended_digest_mismatch_is_refused(self):
        # Exactly {amount_usd, exact_payload}, both keys, null when absent.
        canonical = '{"amount_usd":null,"exact_payload":"' + HIS_WORDS + '"}'
        self.assertEqual(amended_digest(None, HIS_WORDS), hashlib.sha256(canonical.encode('utf-8')).hexdigest())
        only_words = hashlib.sha256(('{"exact_payload":"' + HIS_WORDS + '"}').encode('utf-8')).hexdigest()
        bad = [amended(go_live(), HIS_WORDS), amended(go_live(), HIS_WORDS), amended(go_live(), HIS_WORDS)]
        bad[0]['exact_payload'] = HIS_WORDS + ' Tampered.'
        bad[1]['amended_sha256'] = only_words
        del bad[2]['amended_sha256']
        for row in bad:
            reported, read = round_trip([plan(), go_live()], [decision(plan()), row])
            review = golive_review(reported, read)
            self.assertEqual(review['actions'], [])
            self.assertEqual(review['holds'], [{'proposal_id': go_live()['proposal_id'],
                                                'reason': 'amended_digest_mismatch'}])
            self.assertFalse(match_decisions(read, reported)[1]['usable_approval'])


class SchemaVersionTests(unittest.TestCase):
    def test_report_stays_1_0_0_without_stage_fields(self):
        report = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()], rev='fixture')[0]
        self.assertEqual(report['schema_version'], '1.0.0')
        self.assertTrue(report['proposals'])
        for item in report['proposals']:
            self.assertNotIn('stage', item)
            self.assertNotIn('parent_proposal_id', item)
        self.assertEqual(fixture_report([])['schema_version'], '1.0.0')
        self.assertEqual(fixture_report([plan()])['schema_version'], '1.1.0')
        # A 1.0.0 report never carries a 1.1.0 field, and 1.1.0 is never claimed without one.
        older = copy.deepcopy(report)
        older['proposals'][0]['stage'] = None
        older['payload_sha256'] = report_digest(older)
        with self.assertRaisesRegex(ValueError, 'schema_version must be 1.1.0'):
            validate_report(older)
        raised = copy.deepcopy(report)
        raised['schema_version'] = '1.1.0'
        raised['payload_sha256'] = report_digest(raised)
        with self.assertRaisesRegex(ValueError, 'schema_version must be 1.0.0'):
            validate_report(raised)
        # The closed schema still refuses unknown fields at 1.1.0, and 1.2.0's subject_ref.
        for key in ('extra', 'subject_ref'):
            bad = fixture_report([plan()])
            bad['proposals'][0][key] = 'target:fixture'
            bad['payload_sha256'] = report_digest(bad)
            with self.assertRaises(ValueError):
                validate_report(bad)
        with self.assertRaisesRegex(ValueError, 'parent_proposal_id'):
            proposal('p1', 'Go', 'Why', 'prepared', 'post', 'published', channel='x', exact_payload='x', stage='go_live')
        with self.assertRaisesRegex(ValueError, 'parent_proposal_id'):
            proposal('p1', 'On track?', 'Why', 'advice', 'strategy', 'reviewed', exact_payload='x', stage='check_in')
        # A 1.0.0 report needs no capabilities read.
        with StandIn() as stand:
            stand.client().post_report(report)
            self.assertNotIn(PREFIX + 'capabilities', [c['path'] for c in stand.calls])

    def test_1_1_0_report_requires_capability(self):
        report = fixture_report([plan(), go_live()])
        self.assertEqual(report['schema_version'], AUTONOMY_VERSION)
        for versions, code in ((['1.0.0'], 'schema_version_unsupported'), (None, 'schema_version_unconfirmed')):
            with CapableStandIn(versions) as stand:
                outcome = cc_loop.run(stand.client(), 'test', report['run_id'], lambda d: (report, None), NOW, clock)
                self.assertEqual((outcome['status'], outcome['error_code']), ('failed', code))
                self.assertEqual(stand.posts('reports'), [], 'no silent downgrade: nothing is reported')
                self.assertEqual(stand.posts('attempts')[-1]['body']['error_code'], code)
        with CapableStandIn() as stand:
            outcome = cc_loop.run(stand.client(), 'test', report['run_id'], lambda d: (report, None), NOW, clock)
            self.assertEqual(outcome['status'], 'succeeded')
            paths = [c['path'][len(PREFIX):] for c in stand.calls]
            self.assertLess(paths.index('capabilities'), paths.index('reports'))
            self.assertEqual(stand.reports[report['run_id']]['schema_version'], '1.1.0')
            self.assertNotIn(TOKEN, repr(outcome))


class NorthStarTests(unittest.TestCase):
    def test_north_star_all_source_sum_survives_per_source_rows(self):
        monday, tuesday, wednesday = '2026-10-12T04:00:00Z', '2026-10-13T04:00:00Z', '2026-10-14T04:00:00Z'
        network = [dict(observation(monday, tuesday, 1), scope='source:fixture-network'),
                   dict(observation(tuesday, wednesday, 2), scope='source:fixture-network')]
        direct = [dict(observation(monday, wednesday, 2), scope='source:fixture-direct')]
        with self.assertRaises(ValueError):
            aggregate(network + direct)  # Why the objective used to go missing.
        item = new_subscribers(network + direct, NOW)
        self.assertEqual((item['value'], item['availability']), (5, 'measured'))
        self.assertEqual((item['window_start'], item['window_end']), (monday, wednesday))
        # The all-source reading wins; adding the sources to it would count people twice.
        whole = [observation(monday, wednesday, 5)]
        self.assertEqual(new_subscribers(whole + network + direct, NOW)['value'], 5)
        # Sources over different windows cannot be added, and that is missing, never a raise.
        short = [dict(observation(monday, tuesday, 2), scope='source:fixture-direct')]
        uneven = new_subscribers(network + short, NOW)
        self.assertEqual((uneven['value'], uneven['availability']), (None, 'missing'))
        self.assertIn('different times', uneven['reason'])
        # Only 'publication' (all sources) and 'source:<name>' rows are parts of the sum. A row
        # under any other scope, a post's say, makes the week missing rather than overstated.
        for scope in ('post:fixture', 'publication:all', 'source:', ['source:fixture'], None):
            odd = [dict(observation(monday, wednesday, 2), scope=scope)]
            for rows in (odd + network + direct, odd + whole):
                item = new_subscribers(rows, NOW)
                self.assertEqual((item['value'], item['availability']), (None, 'missing'))
                self.assertIn('neither the publication nor a source', item['reason'])


class HonestLineTests(unittest.TestCase):
    def test_validation_message_counts_only_what_was_validated(self):
        monday, tuesday = '2026-10-12T04:00:00Z', '2026-10-13T04:00:00Z'
        rows = [observation(monday, tuesday, 3),
                dict(observation(monday, tuesday, 1), scope='source:fixture-direct'),
                dict(observation(monday, tuesday, 1), scope='source:fixture-other', timezone='UTC'),
                observation('2026-10-05T04:00:00Z', '2026-10-06T04:00:00Z', 9),
                dict(observation(monday, tuesday, 40), platform='x', metric='reach')]
        self.assertEqual(observation_line(rows, NOW),
                         'Validated 2 Substack new-subscriber readings inside this New York week, 1 failed validation; '
                         '2 other supplied observations not checked')
        self.assertEqual(observation_line(rows[:1], NOW), 'Validated 1 Substack new-subscriber reading inside this New York week')
        report = workspace_report('numbers', 'r1', NOW, observations=rows, rev='fixture')[0]
        lines = [a['line'] for a in report['activity']]
        self.assertIn(observation_line(rows, NOW), lines)
        self.assertFalse(any('dashboard observation' in line for line in lines))


class AutomationCountTests(unittest.TestCase):
    def test_automation_count_strings_match_automations_json(self):
        number = len(read_json(ROOT / 'automations.json')['automations'])
        self.assertEqual(number, 9, 'doctor requires nine automations')
        report = runner_report(ROOT, 'r1', NOW, checks(), 'synthetic', True, 'fixture')[0]
        self.assertTrue(any(a['line'].startswith('Checked the ' + str(number) + ' automation definitions')
                            for a in report['activity']))
        self.assertTrue(report['holds'][0]['detail'].startswith('The automations defined in automations.json ('
                                                                + str(number) + ') draft'))
        source = (ROOT / 'engine/cc_loop.py').read_text(encoding='utf-8')
        words = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(Codex\s+)?(automation|jobs?\b)'
        self.assertIsNone(re.search(words, source, re.IGNORECASE))
        with tempfile.TemporaryDirectory() as folder:
            for name in ('experiments.json', 'channels.json', 'journeys.json'):
                (Path(folder) / name).write_text((ROOT / name).read_text(encoding='utf-8'), encoding='utf-8')
            bare = runner_report(folder, 'r1', NOW, checks(), 'synthetic', True, 'fixture')[0]
            self.assertTrue(any(a['line'].startswith('Checked the automation definitions') for a in bare['activity']))
            self.assertTrue(bare['holds'][0]['detail'].startswith('The automations defined in automations.json draft'))


if __name__ == '__main__':
    unittest.main()
