"""The concept posting path holds against every way Krish says no (review 3 of PR #19, 29 Oct 2026).

Each test is one of the review's probes, turned the right way up: his no on a part a
later version dropped, a line he adds to his amended yes, a concept he stopped in an
earlier version, a second draft of one concept on one channel, a declined week with a
post scheduled for later, a past-due draft, a claim inside a longer number, and a
go-live claimed under an earlier decision. Local stand-ins only; synthetic fixtures.
"""
import copy
import tempfile
import unittest
from unittest import mock

try:
    import test_concept_release as T
    from test_concepts import SHARE, send_test_pass
    from test_mix import full_plan
    from test_run_autorelease import Fixture, manifest, P_X
except ImportError:  # run as tests.test_concept_holds
    from tests import test_concept_release as T
    from tests.test_concepts import SHARE, send_test_pass
    from tests.test_mix import full_plan
    from tests.test_run_autorelease import Fixture, manifest, P_X

from engine import concepts, mix
from engine.control_center import amended_digest
from engine.run import autorelease, cc_records, handoff
from engine.run.autorelease import draft_line, spec_digest


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = T.StandIn().__enter__()
        cls.buf = T.BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stage = self.new_stage()
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def new_stage(self, plan=None):
        stage = T.Stage(self.cc, self.buf, plan)
        stage.tmp = self.tmp.name
        return stage

    def release(self, now=T.NOW):
        return autorelease.autorelease(self.cc.client(), self.buf.client(), now, True, T.fetch,
                                       board=self.stage.board)

    def approved_week(self):
        items = self.stage.propose()
        self.stage.board.press(self.stage.plan)
        self.stage.hand_derived()
        self.items = items
        return items

    def amend(self, item, text, decided_at=T.DECIDED):
        self.cc.decisions.append({'proposal_id': item['proposal_id'], 'decision': 'approved', 'decided_at': decided_at,
                                  'payload_sha256': item['payload_sha256'], 'stage': 'plan', 'amended': True,
                                  'exact_payload': text, 'amount_usd': None,
                                  'amended_sha256': amended_digest(None, text)})

    def second_version(self):
        changed = copy.deepcopy(self.stage.plan)
        changed['weights'] = dict(changed['weights'], meme=changed['weights']['meme'] + 5,
                                  repurposed_carousel=changed['weights']['repurposed_carousel'] - 5)
        summary, code = self.stage.handoff(handoff.MIX_PLAN, T.dispatch_of(changed))
        self.assertEqual(code, 0, summary)
        return cc_records.read_record(self.cc.client(), cc_records.version_run_id('2026-W46', 2), cc_records.VERSION)


class HisNoHolds(Base):
    def test_a_no_on_a_part_a_later_version_dropped_still_stops_the_week(self):
        # B1: three parts, he declines the last; a shorter version (one part) he approves releases nothing.
        big = self.new_stage(full_plan())
        items = big.propose()
        self.assertGreater(len(items), 1)
        big.decide(items[-1], 'declined')
        small = self.new_stage()
        fresh = [i for i in small.propose() if i['proposal_id'] == T.PID
                 and i['payload_sha256'] != items[0]['payload_sha256']]
        self.assertEqual(len(fresh), 1)
        self.cc.decisions.append({'proposal_id': T.PID, 'decision': 'approved', 'decided_at': '2026-11-08T18:00:00Z',
                                  'payload_sha256': fresh[0]['payload_sha256'], 'stage': 'plan', 'amended': False})
        small.hand_derived()
        summary, _ = self.release()
        self.assertEqual(summary['slots'], {'held': 1}, summary)
        self.assertEqual(summary['derived']['weeks'], {'2026-W46': 'declined'}, summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_line_he_adds_to_his_amended_yes_holds_every_concept(self):
        # B2: "Nothing on X this week" is his term; the engine cannot enforce it, so nothing is approved.
        items = self.stage.propose()
        self.amend(items[0], items[0]['exact_payload'] + '\nNothing on X this week, and nothing before 17:00.')
        self.stage.hand_derived()
        summary, code = self.release()
        self.assertEqual((code, summary['slots']), (1, {'held': 1}), summary)
        self.assertEqual(summary['derived']['weeks'], {'2026-W46': 'amended_plan_terms'}, summary)
        # A blank line he adds, or his edit of a concept's own line, is not a new term.
        engine_words = items[0]['exact_payload']
        self.assertEqual(mix.lines_changed(engine_words, engine_words + '\n\n'), 0)
        line = mix.concept_line(self.stage.concept)
        self.assertEqual(mix.lines_changed(engine_words, engine_words.replace(line, line + ' Shorter, please.')), 0)
        self.assertEqual(mix.lines_changed(engine_words, engine_words + '\n- nothing on X'), 1)
        # Review 4: a note naming a concept whose own line still stands is his term, not an edit of it.
        cid = self.stage.concept['concept_id']
        self.assertEqual(mix.lines_changed(engine_words, engine_words + '\n- ' + cid + ' (not on X, please)'), 1)
        twice = engine_words.replace(line, line + ' Shorter.\n- ' + cid + ' (and not on X)')
        self.assertEqual(mix.lines_changed(engine_words, twice), 1, 'one edit is excused, the second line is a term')

    def test_a_concept_he_stopped_in_an_earlier_version_stays_stopped(self):
        # S1: version 1 approved with the concept's line deleted; version 2 re-lists it and he approves it plainly.
        items = self.stage.propose()
        self.stage.board.press(self.stage.plan)
        line = mix.concept_line(self.stage.concept)
        self.amend(items[0], items[0]['exact_payload'].replace(line + '\n', ''))
        self.stage.hand_derived()
        summary, _ = self.release()
        self.assertEqual(summary['holds'], {concepts.STOPPED: 1}, summary)
        version = self.second_version()
        self.cc.decisions.append({'proposal_id': T.PID, 'decision': 'approved', 'decided_at': '2026-11-08T19:00:00Z',
                                  'payload_sha256': version['parts'][0]['payload_sha256'], 'stage': 'plan',
                                  'amended': False})
        summary, _ = self.release()
        self.assertEqual(summary['slots'], {'held': 1}, summary)
        self.assertEqual(summary['holds'], {concepts.STOPPED: 1}, summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_declined_week_with_a_post_scheduled_for_later_is_loud_now(self):
        # S3: scheduled by another path, due in three hours, then his no: loud at once, not near its time.
        self.approved_week()
        self.buf.posts[T.P_DERIVED].update(status='scheduled', dueAt=T.DUE)
        self.cc.decisions.append({'proposal_id': T.PID, 'decision': 'declined', 'decided_at': '2026-11-09T12:00:00Z',
                                  'payload_sha256': self.items[0]['payload_sha256'], 'stage': 'plan',
                                  'amended': False})
        summary, code = self.release(now='2026-11-10T11:00:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('scheduled_after_decline', summary['loud'])
        # A route that went stale never hides it.
        with mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: (['stale'], True, None)):
            summary, code = self.release()
        self.assertEqual(code, 1, summary)
        self.assertIn('scheduled_after_decline', summary['loud'])
        self.assertNotIn('route_not_verified', summary['holds'])


class AfterHisNo(Base):
    def decline(self, at):
        self.cc.decisions.append({'proposal_id': T.PID, 'decision': 'declined', 'decided_at': at,
                                  'payload_sha256': self.items[0]['payload_sha256'], 'stage': 'plan',
                                  'amended': False})

    def test_a_post_sent_after_his_no_is_loud_and_one_sent_before_is_not(self):
        # Review 4: declined at 13:50; the post was due 14:00 and the run at 14:10 sees it sent.
        self.approved_week()
        self.buf.posts[T.P_DERIVED].update(status='sent', dueAt=T.DUE)
        self.decline('2026-11-10T13:50:00Z')
        summary, code = self.release(now='2026-11-10T14:10:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('sent_after_decline', summary['loud'])
        self.cc.decisions[-1]['decided_at'] = '2026-11-10T14:05:00Z'
        summary, code = self.release(now='2026-11-10T14:10:00Z')
        self.assertEqual((code, summary['holds']), (0, {concepts.STOPPED: 1}), summary)

    def test_a_stopped_week_is_checked_even_when_its_review_cannot_be_read(self):
        # Review 4: the stop reads the post by its draft id, so a missing review never hides it.
        self.approved_week()
        self.buf.posts[T.P_DERIVED].update(status='scheduled', dueAt=T.DUE)
        for run_id in [r for r in self.cc.reports if ':review:' in r]:
            del self.cc.reports[run_id]
        self.decline('2026-11-09T12:00:00Z')
        summary, code = self.release(now='2026-11-10T11:00:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('scheduled_after_decline', summary['loud'])


class OneConceptOnce(Base):
    def second_draft(self, post_id, due):
        post = copy.deepcopy(self.buf.posts[T.P_DERIVED])
        post.update(id=post_id, status='draft', dueAt=None)
        self.buf.posts[post_id] = post
        slot = self.stage.derived_slot(slot_id='x-derived-2')
        fields = {'slot_id': 'x-derived-2', 'format': 'meme', 'due_at': due, 'link_placement': None,
                  'publish_mode': 'engine', 'buffer_draft_id': post_id}
        line = draft_line(copy.deepcopy(post), fields, T.fetch)
        digest = spec_digest(line)
        reviewed = {'slot_id': 'x-derived-2', 'format': 'meme', 'words': line['words'],
                    'assets': [{'name': 'mock1.png', 'sha256': h} for h in line['assets']],
                    'payload_sha256': digest, 'share': dict(SHARE)}
        record = send_test_pass(reviewed)
        slot.update(buffer_draft_id=post_id, payload_sha256=digest, due_at=due)
        slot['review'].update(payload_sha256=digest, reader_answer=record['send_test']['reader_answer'])
        return slot

    def test_one_concept_posts_once_per_channel_a_week(self):
        # S2: a second draft of the same concept on X the same day holds; the first goes out.
        self.approved_week()
        summary, code = self.stage.handoff(handoff.GO_LIVE, {'run_id': T.RUN_ID,
                                                             'slots': [self.second_draft(T.P_OTHER,
                                                                                         '2026-11-10T14:20:00Z')]})
        self.assertEqual(code, 0, summary)
        summary, _ = self.release()
        self.assertEqual(summary['slots'], {'held': 1, 'scheduled': 1}, summary)
        self.assertEqual(summary['holds'], {'concept_once_per_channel_week': 1}, summary)
        self.assertEqual(self.buf.posts[T.P_DERIVED]['status'], 'scheduled')
        self.assertEqual(self.buf.posts[T.P_OTHER]['status'], 'draft')

    def test_an_earlier_second_draft_never_joins_one_already_live(self):
        # Review 4: the first is scheduled; a second draft due earlier is indexed after it. Buffer decides.
        self.approved_week()
        summary, _ = self.release(now='2026-11-10T12:35:00Z')
        self.assertEqual(summary['slots'], {'scheduled': 1}, summary)
        summary, code = self.stage.handoff(handoff.GO_LIVE, {'run_id': T.RUN_ID,
                                                             'slots': [self.second_draft(T.P_OTHER,
                                                                                         '2026-11-10T13:50:00Z')]})
        self.assertEqual(code, 0, summary)
        summary, code = self.release(now='2026-11-10T12:40:00Z')
        self.assertEqual(self.buf.posts[T.P_OTHER]['status'], 'draft', summary)
        self.assertEqual(summary['holds'], {'concept_once_per_channel_week': 1}, summary)
        self.assertEqual((code, summary['slots'].get('already_scheduled')), (0, 1), 'the live one is still checked')
        # Two live at once (another path scheduled the second) is loud.
        self.buf.posts[T.P_OTHER].update(status='scheduled', dueAt='2026-11-10T13:50:00Z')
        summary, code = self.release(now='2026-11-10T12:45:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('concept_twice_on_channel_week', summary['loud'])

    def test_a_replacement_draft_goes_out_when_the_first_never_did(self):
        # Review 4: the first draft was deleted in Buffer; the maker's replacement is the concept's one post.
        self.approved_week()
        summary, code = self.stage.handoff(handoff.GO_LIVE, {'run_id': T.RUN_ID,
                                                             'slots': [self.second_draft(T.P_OTHER,
                                                                                         '2026-11-10T14:20:00Z')]})
        self.assertEqual(code, 0, summary)
        self.buf.posts[T.P_DERIVED]['status'] = 'error'
        summary, _ = self.release()
        self.assertEqual(self.buf.posts[T.P_OTHER]['status'], 'scheduled', summary)


class AlarmsStayMeaningful(Base):
    def test_a_past_due_draft_is_loud_once_then_quiet(self):
        # S6: approved late; the 09:00 New York post is still a draft.
        self.approved_week()
        summary, code = self.release(now='2026-11-10T14:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('due_time_passed', summary['loud'])
        for now in ('2026-11-10T16:00:00Z', '2026-11-10T22:00:00Z', '2026-11-11T04:30:00Z'):
            summary, code = self.release(now=now)
            self.assertEqual((code, summary['loud']), (0, []), summary)
        self.assertEqual(self.buf.mutations(), [])


class ClaimWordForWord(unittest.TestCase):
    def test_a_claim_is_carried_as_whole_words(self):
        claim = '10% of pilots fail'
        self.assertFalse(concepts.carries(claim, 'Nobody says 110% of pilots fail. It is false.'))
        self.assertFalse(concepts.carries(claim, '10% of pilots failed.'))
        self.assertTrue(concepts.carries(claim, 'They say 10% of pilots fail, and here is why.'))
        self.assertTrue(concepts.carries(claim, '10% of pilots fail'))
        self.assertTrue(concepts.carries('"Quoted."', 'He said "Quoted." and left.'))
        self.assertFalse(concepts.carries('', 'anything'))


class MockLinks(Base):
    def test_a_mock_link_must_be_one_of_the_files_he_approves(self):
        # S7: the picture he opens from the ask is the file whose hash he approves.
        body = T.dispatch_of(self.stage.plan)
        concept = next(c for c in body['concepts'] if c['mock_sha256'])
        concept['mock_links'] = ['https://drive.google.com/synthetic-view/' + 'e' * 64]
        summary, code = self.stage.handoff(handoff.MIX_PLAN, body)
        self.assertEqual((code, summary['error']), (1, 'payload_rejected_mock_link_differs_from_mock'), summary)
        self.assertEqual([r for r in self.cc.reports if ':mixplan:' in r], [], 'nothing is half shown')


class GoLiveActsOnce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = T.StandIn().__enter__()
        cls.buf = T.BufferStandIn().__enter__()

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

    def run_once(self, now='2026-11-04T13:00:00Z'):
        return autorelease.autorelease(self.cc.client(), self.buf.client(), now, True, T.fetch)

    def test_a_go_live_claimed_under_an_earlier_decision_never_acts_again(self):
        # S4: his amended yes drops the X line and the go-live is claimed; a later plain yes schedules nothing new.
        text = manifest([self.fix.lines[0], self.fix.lines[2]])
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None,
                                                 amended_sha256=amended_digest(None, text))
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['claimed'], 1, summary)
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-04T12:00:00Z'))
        summary, _ = self.run_once()
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft', summary)
        self.assertIn('already_acted', summary['golives']['held'], summary)


if __name__ == '__main__':
    unittest.main()
