"""Concept approval goes live: his decision on the week's mix plan becomes decision.json (R101, R104).

Ruling (Krish, 2026-10-29): approval moves to the idea and the mock on
Instagram, YouTube, TikTok and X. Synthetic fixtures only; nothing here reaches
Buffer, Control Center or any network.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine import cc_loop, concepts, mix
from engine.control_center import amended_digest, match_decisions, sha256_hex
from engine.core import read_json, write_json
from engine.run import decision as decide, release, spec as spec_module
from engine.social import validate
from tests import test_concepts
from tests.test_mix import WEEK, full_plan, ideas, inventory_of

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-08T18:00:00-05:00'
DECIDED = '2026-11-08T17:00:00-05:00'
PID = 'makeyourmindup:mix:2026-W46'


def yes(item, **extra):
    return dict({'proposal_id': item['proposal_id'], 'decision': 'approved', 'decided_at': DECIDED,
                 'payload_sha256': item['payload_sha256']}, **extra)


def amended(item, text):
    return yes(item, amended=True, exact_payload=text, amount_usd=None, amended_sha256=amended_digest(None, text))


def week_spec(result):
    return spec_module.with_mix(spec_module.skeleton(WEEK), result)


class Readback(unittest.TestCase):
    def setUp(self):
        self.mix = full_plan()
        self.item = self.mix['proposal']
        self.cfg = mix.load()
        self.reported = [dict(self.item)]

    def read(self, decisions, ledger=None, mix_doc=None):
        return decide.readback(mix_doc or self.mix, self.cfg, self.reported, match_decisions(decisions, self.reported),
                               ledger, NOW)

    def test_his_yes_approves_every_ready_concept_at_its_hash(self):
        record, why = self.read([yes(self.item)])
        self.assertIsNone(why)
        self.assertEqual(record['decision'], 'approved')
        self.assertEqual(record['approved'], mix.approved_map(self.mix))
        self.assertEqual((record['stopped_concepts'], record['plan_lines_changed']), ([], 0))
        self.assertEqual(record['plan_payload_sha256'], self.item['payload_sha256'])

    def test_his_amended_plan_stops_the_concepts_he_deleted_or_changed(self):
        ids = sorted(mix.approved_map(self.mix))
        drop, edit = ids[0], ids[1]
        lines = []
        for line in self.item['exact_payload'].split('\n'):
            if line.startswith('- ' + drop + ' '):
                continue
            if line.startswith('- ' + edit + ' '):
                line = line.replace('Claim: "', 'Claim: "His sharper words. ')
            lines.append(line)
        record, why = self.read([amended(self.item, '\n'.join(lines))])
        self.assertIsNone(why)
        self.assertTrue(record['amended'])
        self.assertNotIn(drop, record['approved'])
        self.assertNotIn(edit, record['approved'], 'his edited words are never swapped in for the hashed mock')
        self.assertEqual(record['stopped_concepts'], sorted([drop, edit]))
        self.assertEqual(record['changed_concepts'], [edit])
        self.assertEqual(len(record['approved']), len(ids) - 2)

    def test_his_changed_plan_terms_approve_nothing(self):
        # His version, not the engine's: a changed cap, channel or wall line cannot be enforced, so nothing goes.
        text = self.item['exact_payload']
        cap = 'room under its channel\'s daily cap when it goes out (at most Instagram 4,'
        self.assertIn(cap, text)
        for edit in (text.replace(cap, cap.replace('Instagram 4', 'Instagram 1')),
                     text.replace('Planned slots a day on all four channels:',
                                  'Planned slots a day on all four channels (no TikTok this week):'),
                     text.replace('Walls: spend 0;', 'Walls: spend 0, and keep it light;')):
            record, why = self.read([amended(self.item, edit)])
            self.assertIsNone(why)
            self.assertEqual((record['decision'], record['approved'], record['plan_lines_changed']), ('held', {}, 1))
            self.assertTrue(record['hold'].startswith(decide.HOLD_TERMS))
            spec = week_spec(self.mix)
            decision, _ = decide.apply(spec, record, None, dict(test_concepts.CAPS), self.item['payload_sha256'],
                                       now=NOW)
            self.assertEqual(decision['concepts'], {})
            self.assertTrue(decision['concept_hold'].startswith(decide.HOLD_TERMS))
        approved = self.read([yes(self.item)])[0]
        self.assertEqual(decide.sticky(approved, record)['approved'], {}, 'his later amendment replaces his yes')

    def test_a_decline_is_read_before_the_plan_file_is_trusted(self):
        cfg = copy.deepcopy(self.cfg)
        cfg['reserved']['days'] = {k: 0 for k in cfg['reserved']['days']}
        self.cfg = cfg
        with self.assertRaisesRegex(ValueError, 'changed after its proposal'):
            self.read([yes(self.item)])
        record, why = self.read([dict(yes(self.item), decision='declined')])
        self.assertIsNone(why)
        self.assertEqual((record['decision'], record['approved']), ('declined', {}))
        record, _ = self.read([dict(yes(self.item), decision='declined', payload_sha256='0' * 64, decided_at=None)])
        self.assertEqual(record['decision'], 'declined', 'a no counts on any digest, dated or not')

    def test_a_declined_check_in_not_yet_matched_holds_every_concept(self):
        checkin = {'proposal_id': 'makeyourmindup:checkin:unknown', 'decision': 'declined', 'decided_at': DECIDED,
                   'payload_sha256': 'a' * 64, 'stage': 'check_in'}
        rows = match_decisions([yes(self.item), checkin], self.reported)
        self.assertEqual(rows[1]['stage'], 'check_in', 'match_decisions keeps the stage')
        record, why = self.read([yes(self.item), checkin])
        self.assertIsNone(record)
        self.assertTrue(why.startswith(decide.HOLD_UNRESOLVED), why)
        record, why = self.read([yes(self.item)], {'unresolved': {'makeyourmindup:checkin:unknown': {}}})
        self.assertIsNone(record, 'an unresolved stop kept in the go-live ledger holds too')

    def test_a_decline_or_a_stopped_plan_stops_every_concept(self):
        record, _ = self.read([dict(yes(self.item), decision='declined')])
        self.assertEqual((record['decision'], record['approved']), ('declined', {}))
        self.assertEqual(record['stopped_concepts'], sorted(mix.approved_map(self.mix)))
        ledger = {'stopped': {PID: {'by': 'makeyourmindup:checkin', 'decided_at': DECIDED}}}
        record, _ = self.read([yes(self.item)], ledger)
        self.assertEqual(record['decision'], 'declined', 'a stop in the go-live ledger beats a later yes')

    def test_a_stop_never_lifts(self):
        declined = self.read([dict(yes(self.item), decision='declined')])[0]
        approved = self.read([yes(self.item)])[0]
        self.assertEqual(decide.sticky(declined, approved), declined)
        partly = dict(approved, stopped_concepts=[sorted(approved['approved'])[0]])
        later = decide.sticky(partly, approved)
        self.assertNotIn(sorted(approved['approved'])[0], later['approved'])

    def test_a_stale_yes_a_bad_amendment_or_no_decision_records_nothing(self):
        self.assertEqual(self.read([])[0], None)
        stale = yes(self.item, payload_sha256='f' * 64)
        record, why = self.read([stale])
        self.assertIsNone(record)
        self.assertIn('stale_approval', why)
        bad = amended(self.item, self.item['exact_payload'])
        bad['amended_sha256'] = 'e' * 64
        record, why = self.read([bad])
        self.assertIsNone(record)
        self.assertIn('amended_digest_mismatch', why)
        record, why = self.read([yes(self.item, decided_at=None)])
        self.assertIsNone(record)
        self.assertIn('no readable time', why)
        self.reported = []
        self.assertIn('not been reported', self.read([yes(self.item)])[1])

    def test_a_plan_file_changed_after_its_proposal_is_refused(self):
        edited = copy.deepcopy(self.mix)
        edited['concepts'][0]['claim'] = 'A claim changed after the proposal was built.'
        with self.assertRaisesRegex(ValueError, 'changed after its proposal'):
            self.read([yes(self.item)], mix_doc=edited)
        self.reported = [dict(self.item, payload_sha256='d' * 64)]
        with self.assertRaisesRegex(ValueError, 'not this plan file'):
            self.read([yes(self.item)])

    def test_match_decisions_keeps_his_amended_words_only_when_amended(self):
        text = self.item['exact_payload'] + '\nHis line.'
        rows = match_decisions([amended(self.item, text), yes(self.item)], self.reported)
        self.assertEqual(rows[0]['exact_payload'], text)
        self.assertEqual(rows[0]['amended_sha256'], amended_digest(None, text))
        self.assertIsNone(rows[1]['exact_payload'])


class Apply(unittest.TestCase):
    def setUp(self):
        self.mix = full_plan()
        self.spec = week_spec(self.mix)
        self.cfg = mix.load()
        reported = [self.mix['proposal']]
        self.record = decide.readback(self.mix, self.cfg, reported, match_decisions([yes(self.mix['proposal'])],
                                                                                    reported), None, NOW)[0]
        self.sha = self.mix['proposal']['payload_sha256']

    def test_concept_only_decision_and_signature(self):
        decision, signature = decide.apply(self.spec, self.record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        self.assertEqual((decision['proposal_id'], decision['decision'], decision['slots']), (None, None, {}))
        self.assertEqual(decision['concepts'], mix.approved_map(self.mix))
        self.assertEqual(decision['concept_proposal_id'], PID)
        self.assertEqual(signature['concept_proposal_id'], PID)
        self.assertEqual(signature['concepts_digest'], concepts.concepts_digest(decision['concepts']))
        self.assertEqual((signature['go_live_proposal_id'], signature['decision_digest']), (None, sha256_hex({})))
        self.assertEqual(decision['concept_daily_caps'], test_concepts.CAPS)
        signed = dict(self.spec, signature=signature)
        self.assertTrue(release.concept_only(signed, decision))
        self.assertEqual(release._signed_digests(signed, decision), {})
        self.assertIsNone(spec_module.decision_errors(signed, decision))

    def test_each_manifest_entry_recomputes_to_its_approved_hash_and_matches_the_schema(self):
        decision, _ = decide.apply(self.spec, self.record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        validate(decision, read_json(ROOT / 'specs' / 'schema' / 'decision.schema.json'))
        self.assertEqual(sorted(e['concept_id'] for e in decision['concept_manifest']), sorted(decision['concepts']))
        for entry in decision['concept_manifest']:
            self.assertEqual(concepts.concept_sha256(entry), decision['concepts'][entry['concept_id']])
            self.assertEqual(entry['concept_sha256'], decision['concepts'][entry['concept_id']])
        broken = copy.deepcopy(decision)
        broken['concept_manifest'][0]['mock_sha256'] = ['not hex']
        with self.assertRaises(ValueError):
            validate(broken, read_json(ROOT / 'specs' / 'schema' / 'decision.schema.json'))

    def test_a_concept_whose_hash_differs_in_the_spec_is_not_applied(self):
        cid = sorted(self.record['approved'])[0]
        record = copy.deepcopy(self.record)
        record['approved'][cid] = 'a' * 64
        decision, _ = decide.apply(self.spec, record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        self.assertNotIn(cid, decision['concepts'])

    def test_a_declined_week_applies_no_concept_and_releases_nothing(self):
        # Even a record that lists no concept stops every concept the spec carries.
        record = dict(self.record, decision='declined', approved=dict(self.record['approved']), stopped_concepts=[])
        decision, signature = decide.apply(self.spec, record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        self.assertEqual(decision['concepts'], {})
        self.assertEqual(sorted(decision['stopped_concepts']), sorted(concepts.by_id(self.spec)))
        signed = dict(self.spec, signature=signature)
        with self.assertRaisesRegex(ValueError, 'nothing releases'):
            release._signed_digests(signed, decision)
        self.assertIn('no go-live and no concept', spec_module.decision_errors(signed, decision))

    def test_a_concept_only_decision_under_a_go_live_signature_is_refused(self):
        decision, signature = decide.apply(self.spec, self.record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        signed = dict(self.spec, signature=dict(signature, go_live_proposal_id='makeyourmindup:golive:w46'))
        self.assertFalse(release.concept_only(signed, decision))
        with self.assertRaisesRegex(ValueError, 'no approved go-live decision'):
            release._signed_digests(signed, decision)
        unsigned = dict(self.spec, signature={k: v for k, v in signature.items() if k != 'go_live_proposal_id'})
        self.assertFalse(release.concept_only(unsigned, decision))

    def test_an_earlier_stop_in_decision_json_stays(self):
        cid = sorted(self.record['approved'])[0]
        first, signature = decide.apply(self.spec, self.record, None, dict(test_concepts.CAPS), self.sha, now=NOW)
        first['stopped_concepts'] = [cid]
        decision, _ = decide.apply(dict(self.spec, signature=signature), self.record, first, dict(test_concepts.CAPS), self.sha, now=NOW)
        self.assertNotIn(cid, decision['concepts'])
        self.assertIn(cid, decision['stopped_concepts'])

    def test_the_go_live_part_is_kept_and_must_match_its_signature(self):
        slots = {'notes-1': 'b' * 64}
        existing = {'run_id': self.spec['run_id'], 'proposal_id': 'makeyourmindup:golive:w46', 'decision': 'approved',
                    'decided_at': DECIDED, 'slots': slots}
        spec = dict(self.spec, signature={'go_live_proposal_id': 'makeyourmindup:golive:w46',
                                          'decision_digest': sha256_hex(slots), 'signed_at': DECIDED})
        decision, signature = decide.apply(spec, self.record, existing, dict(test_concepts.CAPS), self.sha, now=NOW)
        self.assertEqual((decision['proposal_id'], decision['slots']), ('makeyourmindup:golive:w46', slots))
        self.assertEqual(signature['decision_digest'], sha256_hex(slots))
        self.assertFalse(release.concept_only(dict(spec, signature=signature), decision))
        tampered = dict(existing, slots={'notes-1': 'c' * 64})
        with self.assertRaisesRegex(ValueError, 'does not match the spec signature'):
            decide.apply(spec, self.record, tampered, dict(test_concepts.CAPS), self.sha, now=NOW)

    def test_a_channel_with_no_readable_cap_applies_nothing(self):
        with self.assertRaisesRegex(ValueError, 'no daily cap in the approved plan'):
            decide.apply(self.spec, self.record, None, {'instagram': 4}, self.sha, now=NOW)

    def test_another_week_is_refused(self):
        other = spec_module.skeleton('2026-11-16')
        other['concepts'] = self.spec['concepts']
        with self.assertRaisesRegex(ValueError, 'does not match the mix plan'):
            decide.apply(other, self.record, None, dict(test_concepts.CAPS), self.sha, now=NOW)


class ConceptOnlyRelease(unittest.TestCase):
    """The release fixture with no go-live at all: only the post made from the approved concept releases."""

    sign, plan, holds, tearDown = test_concepts.ReleaseByConcept.sign, test_concepts.ReleaseByConcept.plan, test_concepts.ReleaseByConcept.holds, \
        test_concepts.ReleaseByConcept.tearDown

    def setUp(self):
        test_concepts.ReleaseByConcept.setUp(self)
        self.decision = {'run_id': self.spec['run_id'], 'proposal_id': None, 'decision': None, 'decided_at': None,
                         'slots': {}, 'concepts': {'carousel-synthetic': self.concept['concept_sha256']},
                         'concept_proposal_id': 'makeyourmindup:mix:2026-W45'}
        self.spec['signature'] = {'go_live_proposal_id': None, 'decision_digest': sha256_hex({}),
                                  'signed_at': '2026-11-01T11:00:00-05:00'}
        self.sign()

    def test_the_approved_mix_plan_is_the_go_live_for_its_concept_posts_only(self):
        result = self.plan()
        self.assertEqual([c['slot_id'] for c in result['calls']], ['tiktok-photo-1'])
        holds = self.holds(result)
        for sid in ('notes-1', 'threads-1', 'ig-story-1', 'x-1', 'linkedin-1'):
            self.assertEqual(holds[sid], 'unsigned_or_changed_since_signing', sid)

    def test_a_concept_only_decision_that_signs_a_slot_is_refused(self):
        self.decision['slots'] = {'x-1': 'a' * 64}
        self.sign()
        with self.assertRaisesRegex(ValueError, 'signs no slot'):
            self.plan()

    def test_a_concept_only_decision_on_another_mix_plan_is_refused(self):
        self.decision['concept_proposal_id'] = 'makeyourmindup:mix:2026-W46'
        with self.assertRaisesRegex(ValueError, 'concept_proposal_id'):
            self.plan()


class LoopHook(unittest.TestCase):
    """after_readback, which the loop calls right after it matches decisions, writes the record and decision.json."""

    def workspace(self, folder):
        root = Path(folder)
        for name in ('mix.json', 'intensity.json'):
            shutil.copy(ROOT / name, root / name)
        shutil.copytree(ROOT / 'social', root / 'social')
        shutil.copytree(ROOT / 'docs', root / 'docs')
        return root

    def test_his_yes_reaches_decision_json_in_the_same_run_and_a_later_no_stops_it(self):
        result = full_plan()
        item = result['proposal']
        with tempfile.TemporaryDirectory() as folder:
            root = self.workspace(folder)
            write_json(root / '.scratch' / 'mix' / ('plan-' + WEEK + '.json'), result)
            spec = week_spec(result)
            spec_path = spec_module.run_dir(spec, None, root) / 'spec.json'
            write_json(spec_path, spec)
            report = {'run_id': 'makeyourmindup:2026-11-08:report', 'proposals': [item]}
            matched = cc_loop.remember(root, report, [yes(item)], NOW)
            lines = decide.after_readback(root, matched, NOW)
            self.assertTrue(any('approved, ' + str(len(mix.approved_map(result))) + ' concepts' in l for l in lines),
                            lines)
            written = read_json(spec_path.parent / 'decision.json')
            self.assertEqual(written['concepts'], mix.approved_map(result))
            signed = read_json(spec_path)
            self.assertEqual(signed['signature']['concepts_digest'], concepts.concepts_digest(written['concepts']))
            self.assertIsNone(spec_module.decision_errors(signed, written))
            no = dict(yes(item), decision='declined', decided_at='2026-11-09T07:00:00-05:00')
            matched = cc_loop.remember(root, report, [no], '2026-11-09T07:30:00-05:00')
            decide.after_readback(root, matched, '2026-11-09T07:30:00-05:00')
            written = read_json(spec_path.parent / 'decision.json')
            self.assertEqual(written['concepts'], {})
            self.assertEqual(sorted(written['stopped_concepts']), sorted(concepts.by_id(spec)))
            again = matched = cc_loop.remember(root, report, [dict(yes(item), decided_at='2026-11-09T08:00:00-05:00')],
                                               '2026-11-09T08:30:00-05:00')
            decide.after_readback(root, again, '2026-11-09T08:30:00-05:00')
            self.assertEqual(read_json(spec_path.parent / 'decision.json')['concepts'], {}, 'a stop never lifts')

    def test_the_command_writes_a_run_decision_from_the_week_record(self):
        result = full_plan()
        with tempfile.TemporaryDirectory() as folder:
            root = self.workspace(folder)
            write_json(decide.plan_path(root, WEEK), result)
            spec = week_spec(result)
            spec_path = spec_module.run_dir(spec, None, root) / 'spec.json'
            write_json(spec_path, spec)
            self.assertIn('nothing written', decide.write_run(root, spec_path, NOW))
            reported = [result['proposal']]
            record = decide.readback(result, mix.load(root), reported,
                                     match_decisions([yes(result['proposal'])], reported), None, NOW)[0]
            write_json(decide.record_path(root, WEEK), record)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(decide.main(['decide', str(spec_path), '--now', NOW], root), 0)
            self.assertEqual(read_json(spec_path.parent / 'decision.json')['concepts'], mix.approved_map(result))

    def test_the_loop_calls_the_hook_right_after_it_remembers_decisions(self):
        source = (ROOT / 'engine' / 'cc_loop.py').read_text(encoding='utf-8')
        at = source.index('matched = remember(root, outcome[')
        self.assertIn('after_readback(root, matched, now)', source[at:at + 600])


class FailClosed(unittest.TestCase):
    """Every run checks the approval again; what no longer holds is withdrawn from decision.json."""

    workspace = LoopHook.workspace

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = self.workspace(self.folder.name)
        self.result = full_plan()
        self.item = self.result['proposal']
        write_json(decide.plan_path(self.root, WEEK), self.result)
        self.spec = week_spec(self.result)
        self.spec_path = spec_module.run_dir(self.spec, None, self.root) / 'spec.json'
        write_json(self.spec_path, self.spec)
        self.report = {'run_id': 'makeyourmindup:2026-11-08:report', 'proposals': [self.item]}
        self.loop([yes(self.item)], NOW)
        self.assertEqual(self.written()['concepts'], mix.approved_map(self.result))

    def tearDown(self):
        self.folder.cleanup()

    def loop(self, decisions, at, proposals=None):
        report = dict(self.report, proposals=proposals or self.report['proposals'])
        matched = cc_loop.remember(self.root, report, decisions, at)
        return decide.after_readback(self.root, matched, at)

    def written(self):
        return read_json(self.spec_path.parent / 'decision.json')

    def assert_withdrawn(self, code):
        written = self.written()
        self.assertEqual(written['concepts'], {})
        self.assertTrue((written['concept_hold'] or '').startswith(code), written['concept_hold'])
        signed = read_json(self.spec_path)
        self.assertEqual(signed['signature']['concepts_digest'], concepts.concepts_digest({}))
        self.assertIsNone(concepts.decision_errors(signed, written))

    def test_a_decline_after_the_config_changed_still_stops_every_concept(self):
        cfg = read_json(self.root / 'mix.json')
        cfg['reserved']['days'] = {k: 0 for k in cfg['reserved']['days']}
        write_json(self.root / 'mix.json', cfg)
        self.loop([], '2026-11-09T07:00:00-05:00')
        self.assert_withdrawn(decide.UNTRUSTED)
        lines = self.loop([dict(yes(self.item), decision='declined', decided_at='2026-11-09T08:00:00-05:00')],
                         '2026-11-09T08:30:00-05:00')
        self.assertEqual(read_json(decide.record_path(self.root, WEEK))['decision'], 'declined', lines)
        self.assertEqual(sorted(self.written()['stopped_concepts']), sorted(concepts.by_id(self.spec)))
        self.assertIn('makeyourmindup:mix:2026-W46', release.stopped_plans(self.root))

    def test_a_yes_on_a_plan_since_changed_approves_nothing(self):
        # The plan file is rebuilt and reported with a new digest; his yes was on the old one.
        changed = copy.deepcopy(self.result)
        changed['concepts'] = [c for c in changed['concepts'] if c['concept_id'] != sorted(mix.approved_map(
            self.result))[0]]
        changed['proposal'] = mix.plan_proposal(changed, mix.load(self.root))
        self.assertNotEqual(changed['proposal']['payload_sha256'], self.item['payload_sha256'])
        write_json(decide.plan_path(self.root, WEEK), changed)
        self.loop([], '2026-11-09T07:00:00-05:00', [changed['proposal']])
        self.assertEqual(read_json(decide.record_path(self.root, WEEK))['decision'], 'approved')
        self.assert_withdrawn(decide.STALE)

    def test_an_unmatched_declined_check_in_withdraws_and_is_kept_in_the_ledger(self):
        checkin = {'proposal_id': 'makeyourmindup:checkin:unknown', 'decision': 'declined',
                   'decided_at': '2026-11-09T07:00:00-05:00', 'payload_sha256': 'a' * 64, 'stage': 'check_in'}
        self.loop([checkin], '2026-11-09T07:30:00-05:00')
        self.assert_withdrawn(decide.HOLD_UNRESOLVED)
        self.assertEqual(release.unresolved_stops(self.root), ('makeyourmindup:checkin:unknown',))
        self.loop([], '2026-11-09T08:30:00-05:00')
        self.assert_withdrawn(decide.HOLD_UNRESOLVED)

    def test_a_record_that_cannot_be_applied_is_withdrawn_not_left_standing(self):
        path = decide.record_path(self.root, WEEK)
        write_json(path, dict(read_json(path), decided_at='not a time'))
        line = decide.write_run(self.root, self.spec_path, '2026-11-09T07:00:00-05:00')
        self.assertIn('held: not_applied', line)
        self.assert_withdrawn('not_applied')

    def test_a_declined_check_in_on_the_plan_stops_it(self):
        checkin = proposal_for_checkin(self.item)
        self.loop([{'proposal_id': checkin['proposal_id'], 'decision': 'declined',
                   'decided_at': '2026-11-09T07:00:00-05:00', 'payload_sha256': checkin['payload_sha256']}],
                 '2026-11-09T07:30:00-05:00', [self.item, checkin])
        self.assertEqual(self.written()['concepts'], {})
        self.assertEqual(read_json(decide.record_path(self.root, WEEK))['decision'], 'declined')


def proposal_for_checkin(plan_item):
    from engine.control_center import proposal
    return proposal('makeyourmindup:checkin:mix-w46', 'On track?', 'How the week is going.', 'advice', 'strategy',
                    'plan_on_track', exact_payload='On track.', reference='docs/MIX.md', stage='check_in',
                    parent_proposal_id=plan_item['proposal_id'])


class PlanWords(unittest.TestCase):
    """What Krish reads in the mix plan is exactly what release does."""

    def test_counts_say_which_slots_are_ready_waiting_or_empty(self):
        first = mix.plan(inventory_of(3), WEEK, ideas()[:2], urgency=4)
        text = first['proposal']['exact_payload']
        self.assertIn('Day by day on Instagram:', text)
        rows = [s for s in first['slots'] if s['channel'] == 'instagram']
        empty = sum(1 for s in rows if s['concept_id'] is None)
        waiting = sum(1 for s in rows if s['concept_id'] is not None)
        self.assertIn('Instagram: ' + str(len(rows)) + ' slots', text)
        self.assertIn('0 with a ready concept, ' + str(waiting) + ' waiting for a mock, ' + str(empty) + ' empty', text)
        self.assertIn('Not ready, so not approved', text)

    def test_it_promises_no_post_beyond_what_release_allows(self):
        text = full_plan()['proposal']['exact_payload']
        for claim in ('makes and posts every post', 'never under', 'Delete a concept\'s line to leave it out'):
            self.assertNotIn(claim, text)
        for rule in ('passing review of its own exact words', "room under its channel's daily cap when it goes out"
                     ' (at most Instagram 4, YouTube Shorts 4, TikTok 4, X 4 a day)', 'copy lint', 'channel lock',
                     'Change or add any other line and no concept is approved until a plan carrying your change is'
                     ' approved', 'once on each a week',
                     'capability check', 'change a concept\'s line and that concept and every post from it stop',
                     'Your no stops them all', 'LinkedIn stays your click'):
            self.assertIn(rule, text)
        self.assertNotIn('\u2014', text)
        self.assertLessEqual(len(text), 8000)

    def test_a_concept_line_names_its_channels_and_its_mock(self):
        result = full_plan()
        c = next(c for c in result['concepts'] if c['ready'])
        line = mix.concept_line(c)
        self.assertIn('Hash ' + c['concept_sha256'], line)
        self.assertIn(str(len(c['mock_sha256'])) + ' mock files', line)
        self.assertIn(line, result['proposal']['exact_payload'].split('\n'))


if __name__ == '__main__':
    unittest.main()
