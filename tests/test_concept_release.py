"""The concept path on GitHub Actions: a mix plan dispatched, proposed, approved; a derived post drafted, its
review reported; L0 autorelease schedules it, read back only from Control Center (Krish, 29 Oct 2026).

Everything runs against the local stand-ins for Control Center and Buffer; every word, id, digest and
byte is synthetic. Nothing here reaches controlcenter.krishraja.com, api.buffer.com or a media host.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from test_autonomy import CapableStandIn as StandIn
    from test_run_autorelease import BufferStandIn, Fixture, account, fetch, manifest, line as golive_line
    from test_concepts import SHARE, send_test_pass
    from test_mix import WEEK, full_plan, inventory_of
except ImportError:  # run as tests.test_concept_release
    from tests.test_autonomy import CapableStandIn as StandIn
    from tests.test_run_autorelease import BufferStandIn, Fixture, account, fetch, manifest, line as golive_line
    from tests.test_concepts import SHARE, send_test_pass
    from tests.test_mix import WEEK, full_plan, inventory_of

from engine import concepts, mix
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.control_center import ProtocolError, amended_digest, proposal
from engine.run import autorelease, cc_records, decision as decide, handoff, release
from engine.run.autorelease import draft_line, spec_digest

ROOT = Path(__file__).resolve().parents[1]
PID = 'makeyourmindup:mix:2026-W46'
DUE = '2026-11-10T14:00:00Z'  # Tuesday 09:00 in New York
NOW = '2026-11-10T13:00:00Z'  # an hour before: inside the release window
PLANNED = '2026-11-08T12:00:00Z'
DECIDED = '2026-11-08T17:00:00Z'
CLAIM = 'A pilot earns its budget line when one number is agreed on day one.'
WORDS = CLAIM + ' Synthetic fixture words after the claim, about the pilot budget.'
P_DERIVED, P_OTHER = 'bbbbbbbbbbbbbbbbbbbbbb01', 'bbbbbbbbbbbbbbbbbbbbbb02'
MOCK, MOCK2, NOT_MOCK = (b'synthetic concept mock bytes one\n', b'synthetic concept mock bytes two\n',
                         b'synthetic bytes that are not the mock\n')
RUN_ID = 'makeyourmindup:2026-W46:week'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def small_plan():
    """One past piece as a carousel concept, ready with its claim and two mock files."""
    first = mix.plan(inventory_of(1), WEEK, (), None, urgency=4)
    cid = first['concepts'][0]['concept_id']
    return mix.plan(inventory_of(1), WEEK, (), {cid: {'claim': CLAIM, 'mock_sha256': [sha(MOCK), sha(MOCK2)]}},
                    urgency=4)


def dispatch_of(plan, links=True):
    """The growth-mix-plan client_payload: the plan file's own fields (ten top-level keys at most)."""
    body = {key: copy.deepcopy(plan[key]) for key in handoff.MIX_KEYS}
    for concept in body['concepts']:
        if links:
            concept['mock_links'] = ['https://drive.google.com/synthetic-view/' + concept['concept_id']]
    return body


class Stage:
    """Krish's week end to end: the plan handed off, his decision, a derived post drafted and handed off."""

    def __init__(self, cc, buf, plan=None):
        self.cc, self.buf = cc, buf
        self.plan = plan or small_plan()
        self.concept = next(c for c in self.plan['concepts'] if c['ready'])
        buf.media['mock1.png'] = MOCK
        buf.media['other.png'] = NOT_MOCK
        self.post = {'id': P_DERIVED, 'status': 'draft', 'dueAt': None, 'schedulingType': 'automatic', 'via': 'api',
                     'text': WORDS, 'channelId': BUFFER_CHANNEL_ID['x'], 'channelService': 'twitter',
                     'channel': account('x'),
                     'assets': [{'type': 'image', 'source': buf.base + '/media/mock1.png', 'mimeType': 'image/png',
                                 'image': {'altText': 'Synthetic alt text', 'userTags': None}}],
                     'metadata': {'__typename': 'TwitterPostMetadata', 'type': 'post', 'isAiGenerated': False,
                                  'threadCount': 0, 'retweet': None}}
        buf.posts[P_DERIVED] = self.post

    def handoff(self, event, payload, now=PLANNED):
        summary, code = handoff.handoff(event, payload, self.cc.client(), self.buf.client(), now, True, fetch, ROOT,
                                        str(Path(self.tmp) / 'handoff.json'))
        return summary, code

    def propose(self):
        summary, code = self.handoff(handoff.MIX_PLAN, dispatch_of(self.plan))
        assert code == 0, summary
        return [r['proposals'][0] for r in self.cc.reports.values() if r['proposals']
                and r['proposals'][0]['proposal_id'].startswith(PID)]

    def decide(self, item, verdict='approved', **extra):
        self.cc.decisions.append(dict({'proposal_id': item['proposal_id'], 'decision': verdict, 'decided_at': DECIDED,
                                       'payload_sha256': item['payload_sha256'], 'stage': 'plan', 'amended': False},
                                      **extra))

    def derived_slot(self, review_sha=None, slot_id='x-derived-1'):
        """The manifest slot for the drafted post: its digest rebuilt from the draft, its blind review."""
        fields = {'slot_id': slot_id, 'format': 'single-image', 'due_at': DUE, 'link_placement': None,
                  'publish_mode': 'engine', 'buffer_draft_id': P_DERIVED}
        line = draft_line(copy.deepcopy(self.buf.posts[P_DERIVED]), fields, fetch)
        digest = spec_digest(line)
        reviewed = {'slot_id': slot_id, 'format': 'single-image', 'words': line['words'],
                    'assets': [{'name': 'mock1.png', 'sha256': h} for h in line['assets']],
                    'payload_sha256': review_sha or digest, 'share': dict(SHARE)}
        record = send_test_pass(reviewed)
        return {'slot': slot_id, 'channel': 'x', 'buffer_draft_id': P_DERIVED, 'payload_sha256': digest,
                'per_item_review': False, 'format': 'single-image', 'due_at': DUE, 'link_placement': None,
                'publish_mode': 'engine', 'concept_id': self.concept['concept_id'],
                'review': {'slot_id': slot_id, 'verdict': record['verdict'], 'lens': record['lens'],
                           'payload_sha256': record['payload_sha256'],
                           'reader_answer': record['send_test']['reader_answer'], 'share': dict(SHARE),
                           'asset_names': ['mock1.png']}}

    def hand_derived(self, slot=None):
        summary, code = self.handoff(handoff.GO_LIVE, {'run_id': RUN_ID, 'slots': [slot or self.derived_slot()]})
        assert code == 0 and summary['slots'].get('derived_recorded') == 1, summary
        return summary


class ConceptReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = StandIn().__enter__()
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stage = Stage(self.cc, self.buf)
        self.stage.tmp = self.tmp.name
        # The x single-image route stands as recorded passed; test_an_unverified_route_holds_a_derived_post
        # reads the real records.
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def release(self, now=NOW, deliver=True):
        return autorelease.autorelease(self.cc.client(), self.buf.client(), now, deliver, fetch)

    def approved_week(self):
        items = self.stage.propose()
        for item in items:
            self.stage.decide(item)
        self.stage.hand_derived()
        return items

    # End to end -------------------------------------------------------------------------

    def test_end_to_end_a_dispatched_plan_he_approves_schedules_its_derived_post_in_the_window(self):
        items = self.stage.propose()
        self.assertEqual([i['proposal_id'] for i in items], [PID], 'a small week is one ask')
        self.assertEqual(items[0]['exact_payload'], mix.payload_text(self.stage.plan, mix.load()),
                         'the words he reads are the plan file the loop would ask, recomputed by the runner')
        self.assertEqual(items[0]['evidence'][0]['url'],
                         'https://drive.google.com/synthetic-view/' + self.stage.concept['concept_id'])
        self.assertIn(cc_records.version_run_id('2026-W46', 1), self.cc.reports)
        self.stage.decide(items[0])
        self.stage.hand_derived()
        digest = self.stage.derived_slot()['payload_sha256']
        self.assertIn(cc_records.review_run_id(digest), self.cc.reports, 'keyed by the first 12 hex of its sha')
        record = cc_records.read_record(self.cc.client(), cc_records.review_run_id(digest), cc_records.REVIEW)
        self.assertEqual(record['payload_sha256'], digest, 'the full sha in the body')
        # More than ninety minutes out it is never read or edited: not even its review is read.
        self.buf.calls = []
        summary, code = self.release(now='2026-11-10T11:00:00Z')
        self.assertEqual((code, summary['slots'], summary['derived']['read']), (0, {}, 0), summary)
        self.assertEqual([c for c in self.buf.calls if c['op'] in ('GetPost', 'ScheduleDraft')], [])
        summary, code = self.release()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'scheduled': 1}, summary)
        self.assertEqual(summary['derived'], {'read': 1, 'weeks': {'2026-W46': 'approved'}})
        post = self.buf.posts[P_DERIVED]
        self.assertEqual((post['status'], post['text']), ('scheduled', WORDS))
        sent = self.buf.mutations()[0]['variables']['input']
        self.assertEqual((sent['dueAt'], sent['mode']), (DUE, 'customScheduled'))
        self.assertNotIn(WORDS[:20], json.dumps(summary), 'the summary carries codes, never words')
        # A second run counts it as done.
        summary, code = self.release()
        self.assertEqual((code, summary['slots'], summary['mutations']), (0, {'already_scheduled': 1}, 0))

    def test_his_no_on_the_plan_holds_the_derived_post(self):
        items = self.stage.propose()
        self.stage.decide(items[0], 'declined')
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {concepts.STOPPED: 1}), summary)
        self.assertEqual(self.buf.mutations(), [])
        # A post from it still scheduled after his No is loud, and never unscheduled.
        self.buf.posts[P_DERIVED].update(status='scheduled', dueAt=DUE)
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (1, {'scheduled_after_decline': 1}), summary)
        self.assertEqual(self.buf.posts[P_DERIVED]['status'], 'scheduled')

    def test_an_amended_plan_that_changes_the_concept_line_holds_the_derived_post(self):
        items = self.stage.propose()
        line = mix.concept_line(self.stage.concept)
        text = items[0]['exact_payload'].replace(line, line.replace('Claim: "', 'Claim: "Edited: '))
        self.assertNotEqual(text, items[0]['exact_payload'])
        self.stage.decide(items[0], amended=True, exact_payload=text, amount_usd=None,
                          amended_sha256=amended_digest(None, text))
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {concepts.STOPPED: 1}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_an_amended_plan_line_other_than_a_concept_holds_every_derived_post_loudly(self):
        items = self.stage.propose()
        text = items[0]['exact_payload'].replace('Walls: spend 0', 'Walls: spend 5')
        self.stage.decide(items[0], amended=True, exact_payload=text, amount_usd=None,
                          amended_sha256=amended_digest(None, text))
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds'], summary['derived']['weeks']),
                         (1, {'concept_hold': 1}, {'2026-W46': 'amended_plan_terms'}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_derived_post_whose_asset_is_not_the_mock_holds(self):
        self.buf.posts[P_DERIVED]['assets'][0]['source'] = self.buf.base + '/media/other.png'
        self.approved_week()
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {concepts.DEPARTS: 1}), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_derived_post_that_drops_the_claim_holds(self):
        self.buf.posts[P_DERIVED]['text'] = 'Synthetic fixture words that never carry the approved line.'
        self.approved_week()
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {concepts.DEPARTS: 1}, summary)

    def test_a_derived_slot_is_never_a_go_live_and_the_mix_plan_is_no_go_lives_plan(self):
        items = self.approved_week()
        golives = [p for r in self.cc.reports.values() for p in r['proposals'] if p.get('stage') == 'go_live']
        self.assertEqual(golives, [], 'a post made from an approved concept needs no go-live of its own')
        plan, reason = handoff.open_plan(self.cc.client(), self.cc.decisions, PLANNED)
        self.assertEqual((plan, reason), (None, 'no_open_plan'), 'his yes on the mix plan never parents a go-live')
        self.assertEqual(items[0]['stage'], 'plan')

    # The review, read back by its exact sha --------------------------------------------------

    def test_a_review_for_another_sha_is_refused(self):
        # The review the dispatch carries was of other words: the runner refuses to record it.
        other = self.stage.derived_slot(review_sha='e' * 64)
        summary, code = self.stage.handoff(handoff.GO_LIVE, {'run_id': RUN_ID, 'slots': [other]})
        self.assertEqual(summary['holds'], {'review_for_another_payload': 1}, summary)
        # A record at the sha's address whose body names another sha never counts.
        items = self.stage.propose()
        self.stage.decide(items[0])
        self.stage.hand_derived()
        digest = self.stage.derived_slot()['payload_sha256']
        run_id = cc_records.review_run_id(digest)
        record = cc_records.record_of(self.cc.reports[run_id], cc_records.REVIEW)
        forged = dict(record, payload_sha256=digest[:12] + 'f' * 52)
        self.cc.reports[run_id] = cc_records.record_report(run_id, cc_records.REVIEW, forged, ['Synthetic'], PLANNED,
                                                           'synthetic-revision')
        summary, code = self.release()
        self.assertEqual(summary['holds'], {'review_for_another_payload': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])
        # And a review of the draft before its words changed is a review of another payload (spec.review_reason).
        self.cc.reports[run_id] = cc_records.record_report(run_id, cc_records.REVIEW, record, ['Synthetic'], PLANNED,
                                                           'synthetic-revision')
        self.buf.posts[P_DERIVED]['text'] = WORDS + ' One more sentence nobody reviewed.'
        summary, code = self.release()
        self.assertEqual(summary['holds'], {'concept_post_not_reviewed': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_an_unreadable_review_record_holds_loudly_and_never_guesses(self):
        self.approved_week()
        digest = self.stage.derived_slot()['payload_sha256']
        report = copy.deepcopy(self.cc.reports[cc_records.review_run_id(digest)])
        report['activity'] = [a for a in report['activity'] if not a['line'].endswith(report['activity'][-1]['line'][-8:])]
        report['payload_sha256'] = autorelease.report_digest(report)
        self.cc.reports[report['run_id']] = report
        summary, code = self.release()
        self.assertEqual((code, summary['holds'], summary['error']), (1, {'review_unreadable': 1}, None), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_the_review_is_judged_only_by_spec_review_reason(self):
        self.approved_week()
        calls = []
        real = release.concept_post_hold

        def spy(slot, decision, review, caps, per_day, formats=None):
            calls.append(review)
            return real(slot, decision, review, caps, per_day, formats)
        with mock.patch.object(release, 'concept_post_hold', spy), \
                mock.patch('engine.run.spec.review_reason', return_value='synthetic: judged here') as judge:
            summary, _ = self.release()
        self.assertEqual(summary['holds'], {'concept_post_not_reviewed': 1}, summary)
        self.assertEqual(judge.call_count, 1, 'the one judge, fed the Control Center readback')
        self.assertEqual(calls[0]['lens'], 'send-test')

    # The week's holds, loud ------------------------------------------------------------------

    def test_a_week_with_no_plan_in_control_center_holds_loudly(self):
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds'], summary['derived']['weeks']),
                         (1, {'concept_hold': 1}, {'2026-W46': 'mix_plan_not_reported'}), summary)

    def test_an_unresolved_stop_holds_every_derived_post_loudly(self):
        self.approved_week()
        self.cc.decisions.append({'proposal_id': 'makeyourmindup:checkin:unknown', 'decision': 'declined',
                                  'decided_at': DECIDED, 'payload_sha256': 'c' * 64, 'stage': 'check_in'})
        summary, code = self.release()
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary['holds'].get('concept_stop_unresolved'), 1, summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_plan_he_has_not_answered_holds_quietly(self):
        self.stage.propose()
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['holds']), (0, {'concept_not_approved': 1}), summary)

    def test_a_newer_plan_version_withdraws_his_earlier_yes(self):
        items = self.stage.propose()
        self.stage.decide(items[0])
        self.stage.hand_derived()
        changed = copy.deepcopy(self.stage.plan)
        changed['weights'] = dict(changed['weights'], meme=changed['weights']['meme'] + 5,
                                  repurposed_carousel=changed['weights']['repurposed_carousel'] - 5)
        summary, code = self.stage.handoff(handoff.MIX_PLAN, dispatch_of(changed))
        self.assertEqual(code, 0, summary)
        self.assertIn(cc_records.version_run_id('2026-W46', 2), self.cc.reports)
        summary, code = self.release()
        self.assertEqual((code, summary['derived']['weeks']), (1, {'2026-W46': 'stale_approval'}), summary)
        self.assertEqual(self.buf.mutations(), [])
        # The same plan sent again is the same version: nothing new is reported.
        before = len(self.cc.reports)
        self.stage.handoff(handoff.MIX_PLAN, dispatch_of(changed))
        self.assertEqual(len(self.cc.reports), before)

    def test_the_daily_cap_counts_every_post_scheduled_that_new_york_day_from_buffer(self):
        self.approved_week()
        for n in range(4):
            post_id = 'bbbbbbbbbbbbbbbbbbbbbb1%d' % n
            self.buf.posts[post_id] = {'id': post_id, 'status': 'scheduled', 'dueAt': '2026-11-10T2%d:00:00.000Z' % n,
                                       'text': 'Synthetic other post.', 'channelId': BUFFER_CHANNEL_ID['x'],
                                       'channelService': 'twitter', 'channel': account('x'), 'assets': [],
                                       'schedulingType': 'automatic', 'via': 'api', 'metadata': None}
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {'concept_daily_cap_reached': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])
        # Another day's posts, or another channel's, leave room.
        for n in range(4):
            self.buf.posts['bbbbbbbbbbbbbbbbbbbbbb1%d' % n]['dueAt'] = '2026-11-11T2%d:00:00.000Z' % n
        summary, _ = self.release()
        self.assertEqual(summary['slots'], {'scheduled': 1}, summary)

    def test_a_derived_post_never_bumps_a_post_he_signed_for_that_day(self):
        self.approved_week()
        lines = [golive_line('x-signed-%d' % n, 'x', 'Synthetic signed words %d.' % n, 'cccccccccccccccccccccc0%d' % n,
                             due='2026-11-10T2%d:00:00Z' % n) for n in range(4)]
        plan = proposal('makeyourmindup:plan:w45-w52', 'Synthetic plan', 'Synthetic why', 'advice', 'strategy',
                        'reviewed', exact_payload='Synthetic standing plan words.', stage='plan')
        golive = proposal('makeyourmindup:golive:2026-11-10:piece', 'Synthetic go-live', 'Synthetic why', 'prepared',
                          'post', 'published', channel='buffer', exact_payload=manifest(lines), stage='go_live',
                          parent_proposal_id=plan['proposal_id'])
        from test_run_autorelease import staged_report
        for item in (plan, golive):
            report = staged_report(item)
            self.cc.reports[report['run_id']] = report
        self.cc.decisions += [Fixture.decision(plan, '2026-11-01T12:00:00Z'),
                              Fixture.decision(golive, '2026-11-09T12:00:00Z')]
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {'concept_daily_cap_reached': 1}, summary)
        self.assertEqual(self.buf.posts[P_DERIVED]['status'], 'draft')

    def test_an_unverified_route_holds_a_derived_post(self):
        self.approved_week()
        self.buf.calls = []
        with mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: (['not_verified'], True, None)):
            summary, _ = self.release()
        self.assertEqual(summary['holds'], {'route_not_verified': 1})
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'GetPost'], [], 'held before any read')

    def forge(self):
        """Report the draft as it now stands straight into the stand-in, past the runner's own checks,
        so only autorelease's gates stand between it and Buffer."""
        slot = self.stage.derived_slot()
        line = draft_line(copy.deepcopy(self.buf.posts[P_DERIVED]), {
            'slot_id': slot['slot'], 'format': slot['format'], 'due_at': slot['due_at'], 'link_placement': None,
            'publish_mode': 'engine', 'buffer_draft_id': P_DERIVED}, fetch)
        reports, days = handoff.derived_reports([handoff.review_record(slot, line)], PLANNED, ROOT)
        for report in reports + [handoff.index_report(day, 9, entries, PLANNED, ROOT) for day, entries in days.items()]:
            self.cc.reports[report['run_id']] = report
        for n in range(1, 9):
            self.cc.reports.setdefault(cc_records.index_run_id('2026-11-10', n),
                                       handoff.index_report('2026-11-10', n, [], PLANNED, ROOT))

    def test_a_derived_post_on_another_account_or_failing_copy_lint_holds(self):
        self.approved_week()
        self.buf.posts[P_DERIVED]['channel'] = dict(account('x'), name='SomeoneElse')
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {'wrong_account': 1})
        self.buf.posts[P_DERIVED]['channel'] = account('x')
        # His name in the words, reviewed at exactly those words: the copy lint still holds it.
        self.buf.posts[P_DERIVED]['text'] = WORDS + ' Krish Raja said so.'
        self.forge()
        summary, _ = self.release()
        # The review of the words as first handed off no longer matches the draft either.
        self.assertEqual(summary['holds'], {'concept_post_not_reviewed': 1, 'copy_lint_refused': 1}, summary)
        # And in the alt text the edit would carry.
        self.buf.posts[P_DERIVED]['text'] = WORDS
        self.buf.posts[P_DERIVED]['assets'][0]['image']['altText'] = 'Krish Raja holding the chart.'
        self.forge()
        summary, _ = self.release()
        # The review of the words as first handed off no longer matches the draft either.
        self.assertEqual(summary['holds'], {'concept_post_not_reviewed': 1, 'copy_lint_refused': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_share_ask_in_a_derived_post_holds(self):
        self.approved_week()
        self.buf.posts[P_DERIVED]['text'] = WORDS + ' Please share this with your team.'
        self.forge()
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {'concept_post_not_reviewed': 1, 'share_ask_refused': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])

    # The mix plan dispatch --------------------------------------------------------------------

    def test_the_mix_plan_payload_is_closed_and_recomputed(self):
        payload = dispatch_of(self.stage.plan)
        summary, _ = self.stage.handoff(handoff.MIX_PLAN, dict(payload, extra=1))
        self.assertEqual(summary['error'], 'payload_rejected_payload_unknown_key')
        bad = copy.deepcopy(payload)
        bad['concepts'][0]['concept_sha256'] = 'a' * 64
        summary, _ = self.stage.handoff(handoff.MIX_PLAN, bad)
        self.assertEqual(summary['error'], 'payload_rejected_concept_concept_sha256_differs')
        bad = copy.deepcopy(payload)
        bad['concepts'][0]['placements'] = bad['concepts'][0]['placements'][:1]
        summary, _ = self.stage.handoff(handoff.MIX_PLAN, bad)
        self.assertEqual(summary['error'], 'payload_rejected_concept_placements_differ_from_slots')
        bad = copy.deepcopy(payload)
        bad['targets']['x']['target'] = 40
        summary, _ = self.stage.handoff(handoff.MIX_PLAN, bad)
        self.assertEqual(summary['error'], 'payload_rejected_bad_targets')
        self.assertEqual(self.cc.reports, {}, 'nothing refused is reported')
        self.assertLessEqual(len(handoff.MIX_KEYS), 10, 'a client_payload holds at most ten top-level keys')

    def test_a_full_week_over_eight_thousand_characters_comes_in_parts_in_order(self):
        plan = full_plan()
        stage = Stage(self.cc, self.buf, plan)
        stage.tmp = self.tmp.name
        items = stage.propose()
        self.assertGreater(len(items), 1, 'a full week is more than one ask')
        self.assertEqual([i['proposal_id'] for i in items],
                         [mix.part_id(WEEK, n) for n in range(1, len(items) + 1)])
        self.assertTrue(all(len(i['exact_payload']) <= 8000 for i in items))
        self.assertTrue(all(len(i['evidence']) <= 12 for i in items))
        ready = [c for c in plan['concepts'] if c['ready']]
        stood = [c for c in ready if any(mix.concept_line(c) in i['exact_payload'] for i in items)]
        self.assertEqual(len(stood), len(ready), 'every concept line stands in exactly one part')
        version = cc_records.read_record(self.cc.client(), cc_records.version_run_id('2026-W46', 1), cc_records.VERSION)
        self.assertEqual([p['proposal_id'] for p in version['parts']], [i['proposal_id'] for i in items])
        cfg = mix.load()
        read = [autorelease.read_part(self.cc.client(), i['proposal_id'], i['payload_sha256']) for i in items]
        # Only part 1 answered: its concepts are approved, the later parts' are not yet.
        stage.decide(items[0])
        record, _ = decide.cc_readback(WEEK, read, cfg, self.cc.decisions)
        first = {c['concept_id'] for c in read[0][1]['concepts'] if c['ready']}
        self.assertEqual(set(record['approved']), first)
        # Every part answered: every ready concept.
        for item in items[1:]:
            stage.decide(item)
        record, _ = decide.cc_readback(WEEK, read, cfg, self.cc.decisions)
        self.assertEqual(set(record['approved']), {c['concept_id'] for c in ready})
        # His no on any one part stops every concept of the week, before anything is trusted.
        stage.decide(items[-1], 'declined')
        record, _ = decide.cc_readback(WEEK, read, cfg, self.cc.decisions)
        self.assertEqual((record['decision'], record['approved']), ('declined', {}))
        self.assertEqual(set(record['stopped_concepts']),
                         {c['concept_id'] for _, part in read for c in part['concepts']})
        record, _ = decide.cc_readback(WEEK, [(i, None) for i, _ in read], cfg, self.cc.decisions)
        self.assertEqual(record['decision'], 'declined', 'read before any part record is trusted')
        # A part without his yes keeps part 1's concepts out until part 1 is answered.
        self.cc.decisions = [d for d in self.cc.decisions if d['proposal_id'] != items[0]['proposal_id']
                             and d['decision'] != 'declined']
        record, why = decide.cc_readback(WEEK, read, cfg, self.cc.decisions)
        self.assertIsNone(record)
        self.assertIn('no decision', why)

    def test_a_record_rides_whole_through_whitespace_collapse(self):
        record = {'schema': cc_records.REVIEW, 'words': 'two  spaces,\ttab and\nnewline ' * 40}
        report = cc_records.record_report('makeyourmindup:review:' + 'a' * 12, cc_records.REVIEW, record,
                                          ['Synthetic'], PLANNED, 'synthetic-revision')
        self.assertEqual(cc_records.record_of(report, cc_records.REVIEW), record)
        self.assertTrue(all(len(a['line']) <= 500 for a in report['activity']))
        broken = copy.deepcopy(report)
        del broken['activity'][2]
        with self.assertRaisesRegex(ValueError, 'record_unreadable'):
            cc_records.record_of(broken, cc_records.REVIEW)
        with self.assertRaisesRegex(ValueError, 'record_too_large'):
            cc_records.record_lines(cc_records.REVIEW, {'blob': 'x' * 30000})

    def test_handoff_workflow_takes_the_mix_plan_from_the_event_file(self):
        text = (ROOT / '.github' / 'workflows' / 'handoff.yml').read_text(encoding='utf-8')
        self.assertIn('growth-mix-plan', text.split('types:')[1].split('\n')[0])
        self.assertIn('growth-mix-plan', text.split('options:')[1].split('\n')[0])
        self.assertIn("os.environ['GITHUB_EVENT_PATH']", text)
        self.assertNotIn('client_payload', ''.join(line for line in text.splitlines() if 'env:' in line or '${{' in line
                                                   and 'client_payload' in line))


class ClaimTests(unittest.TestCase):
    """claim_golives on GitHub Actions: the go-lives this lane finished are recorded in Control Center (F114)."""

    @classmethod
    def setUpClass(cls):
        cls.cc = StandIn().__enter__()
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.fix = Fixture(self.cc, self.buf)
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_once(self, deliver=True, now='2026-11-04T13:00:00Z'):
        return autorelease.autorelease(self.cc.client(), self.buf.client(), now, deliver, fetch)

    def claims(self):
        return {k: r for k, r in self.cc.reports.items() if ':claimed:' in k}

    def test_a_finished_go_live_is_claimed_in_control_center_and_acts_once(self):
        summary, code = self.run_once()
        self.assertEqual((code, summary['golives']['claimed']), (0, 1), summary)
        (run_id, report), = self.claims().items()
        record = cc_records.record_of(report, cc_records.CLAIM)
        self.assertEqual(record['proposal_id'], self.fix.golive['proposal_id'])
        self.assertEqual(record['outcomes'], {'krish_click': 1, 'scheduled': 2})
        # The next clean runner reads the claim back: the go-live is acted on, only checked.
        summary, code = self.run_once()
        self.assertEqual(summary['golives']['held'], {'already_acted': 1}, summary)
        self.assertEqual((summary['slots'], summary['mutations']), ({'already_scheduled': 2, 'krish_click': 1}, 0))
        # A post of a claimed go-live put back to a draft is never scheduled a second time.
        self.buf.posts['aaaaaaaaaaaaaaaaaaaaaa01'].update(status='draft', dueAt=None)
        before = len(self.buf.mutations())
        summary, code = self.run_once()
        self.assertEqual(summary['holds'], {'acted_once_now_a_draft': 1}, summary)
        self.assertEqual(len(self.buf.mutations()), before)
        # Without the claim it would have been scheduled again: the claim is what stops it.
        for key in list(self.claims()):
            del self.cc.reports[key]
        summary, _ = self.run_once()
        self.assertEqual(summary['slots'].get('scheduled'), 1, summary)

    def test_a_go_live_with_a_line_still_to_come_is_not_claimed(self):
        later = '2026-11-04T20:00:00Z'
        lines = [self.fix.lines[0], golive_line('x-1', 'x', self.fix.lines[1]['words'], 'aaaaaaaaaaaaaaaaaaaaaa02',
                                                 meta=self.fix.lines[1]['meta'], due=later), self.fix.lines[2]]
        golive = self.fix.publish(lines)
        self.cc.decisions[-1] = Fixture.decision(golive, '2026-11-03T14:00:00Z')
        summary, _ = self.run_once()
        self.assertEqual((summary['slots'].get('not_yet_due'), summary['golives']['claimed']), (1, 0), summary)
        self.assertEqual(self.claims(), {})
        summary, _ = self.run_once(deliver=False, now='2026-11-04T19:00:00Z')
        self.assertEqual(self.claims(), {}, 'a dry run claims nothing')

    def test_a_claim_that_cannot_be_read_fails_closed(self):
        real = self.cc.client

        class Refusing:
            def __init__(self, inner):
                self.inner = inner

            def __getattr__(self, name):
                return getattr(self.inner, name)

            def read_report(self, run_id):
                if ':claimed:' in run_id:
                    raise ProtocolError('server_error', 500)
                return self.inner.read_report(run_id)
        summary, code = autorelease.autorelease(Refusing(real()), self.buf.client(), '2026-11-04T13:00:00Z', True,
                                                fetch)
        self.assertEqual((code, summary['error']), (1, 'control_center_server_error'))
        self.assertEqual(self.buf.mutations(), [])

    def test_a_go_live_naming_two_new_york_days_holds(self):
        # R94: approving a day authorises exactly that day's posts (F111).
        lines = [self.fix.lines[0], dict(self.fix.lines[1], due_at='2026-11-05T14:00:00Z'), self.fix.lines[2]]
        lines[1]['payload_sha256'] = autorelease.line_digest(lines[1])
        golive = self.fix.publish(lines)
        self.cc.decisions[-1] = Fixture.decision(golive, '2026-11-03T14:00:00Z')
        summary, code = self.run_once()
        self.assertEqual((code, summary['holds']), (0, {'golive_spans_days': 3}), summary)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(autorelease.spans_days({'a': lines[0], 'b': lines[2]}),
                         [autorelease.ny_time(lines[0]['due_at']).date()], 'a line with no time rides along')


if __name__ == '__main__':
    unittest.main()
