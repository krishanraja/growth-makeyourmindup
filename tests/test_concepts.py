"""Concept approval: one yes on the idea and its mock covers every post made from it (R101).

Ruling (Krish, 2026-10-29): "I just need to be in control of the idea and the
mocks and then I'm happy to let you let that engine just go for gold."
Synthetic fixtures only. Nothing here reaches Buffer, Control Center or any network.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from engine import concepts
from engine.core import write_json
from engine.run import release, spec as spec_module
from engine.share import compare_send_test, slot_send_test_request

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'release'
NOW = '2026-11-01T12:00:00-05:00'
MIX_PLAN = 'makeyourmindup:mix:2026-W45'
W45 = {'start': '2026-11-02T00:00:00-05:00', 'end': '2026-11-09T00:00:00-05:00', 'tz': 'America/New_York'}
SHARE = {'sender': 'a head of operations at a mid-size insurer', 'receiver': 'her CFO, who signs off the pilot budget',
         'job': 'settles_it', 'dm_line': 'This is the six-week rule I meant: one number agreed on day one.',
         'moment': 'the quarterly budget review where the pilot question comes back', 'standalone': True}
CAPS = {'instagram': 4, 'youtube': 4, 'tiktok': 4, 'x': 4}


def send_test_pass(slot):
    """A synthetic blind reader's pass on this slot's exact payload, as run send-test --record writes it."""
    request = slot_send_test_request(slot)
    answer = {'would_send': True, 'receiver': 'my CFO', 'job': 'settles_it', 'dm_line': 'Synthetic line.',
              'why': 'Synthetic.', 'request_sha256': request['request_sha256']}
    return {'slot_id': slot['slot_id'], 'verdict': 'pass', 'lens': 'send-test',
            'payload_sha256': slot['payload_sha256'], 'send_test': compare_send_test(slot['share'], answer, request)}


def load(name):
    return json.loads((FIX / (name + '.json')).read_text(encoding='utf-8'))


class ReleaseByConcept(unittest.TestCase):
    """tiktok-photo-1 loses its own digest and is covered by its approved concept instead."""

    def setUp(self):
        self.spec = load('spec')
        self.decision = load('decision')
        self.channels = load('channels')
        self.targets = load('targets')
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for n in range(1, 6):
            (self.dir / ('frame-' + str(n) + '.png')).write_bytes(('synthetic release fixture frame ' + str(n) + '\n').encode())
        self.slot = next(s for s in self.spec['slots'] if s['slot_id'] == 'tiktok-photo-1')
        self.claim = ' '.join(self.slot['words'].split()[:6])
        self.concept = {'concept_id': 'carousel-synthetic', 'lane': 'repurposed_carousel',
                        'idea': 'TEST FIXTURE carousel', 'claim': self.claim, 'source_url': None, 'piece_id': None,
                        'mock_sha256': [a['sha256'] for a in self.slot['assets']],
                        'placements': [{'channel': 'tiktok', 'format': 'carousel'}]}
        self.concept['concept_sha256'] = concepts.concept_sha256(self.concept)
        self.spec['concepts'] = [self.concept]
        self.spec['window'] = dict(W45)
        self.slot['concept_id'] = 'carousel-synthetic'
        self.slot['share'] = dict(SHARE)
        del self.decision['slots']['tiktok-photo-1']
        self.decision['concepts'] = {'carousel-synthetic': self.concept['concept_sha256']}
        self.sign()

    def tearDown(self):
        self.tmp.cleanup()

    def sign(self):
        self.spec['signature']['decision_digest'] = release.decision_digest(self.decision)
        self.spec['signature']['concepts_digest'] = concepts.concepts_digest(self.decision.get('concepts') or {})
        self.spec['signature']['concept_proposal_id'] = MIX_PLAN

    def plan(self, stopped=(), unresolved=(), reviews=None, caps=None, other=None, ledger=None):
        paths = {s['slot_id']: [self.dir / a['name'] for a in s['assets']] for s in self.spec['slots']}
        if reviews is None:
            reviews = {s['slot_id']: send_test_pass(s) for s in self.spec['slots'] if s.get('share')}
        return release.release_plan(self.spec, self.decision, ledger, paths, self.channels, NOW, self.targets,
                                    stopped_proposals=stopped, unresolved_stops=unresolved, reviews=reviews,
                                    caps=dict(CAPS) if caps is None else caps, other_scheduled=other)

    def holds(self, result):
        return {h['slot_id']: h['hold'] for h in result['holds']}

    def test_an_approved_concept_releases_its_post_without_a_digest_of_its_own(self):
        result = self.plan()
        self.assertEqual(self.holds(result), {})
        call = next(c for c in result['calls'] if c['slot_id'] == 'tiktok-photo-1')
        self.assertEqual(call['payload_sha256'], self.slot['payload_sha256'])
        entry = result['ledger']['released']['tiktok-photo-1']
        self.assertEqual((entry['concept_id'], entry['concept_sha256']),
                         ('carousel-synthetic', self.concept['concept_sha256']))

    def test_a_post_whose_words_drop_the_claim_is_held(self):
        self.slot['words'] = 'TEST FIXTURE ONLY. Different words that never carry the approved line.'
        self.slot['payload_sha256'] = release.slot_digest(self.slot)
        hold = self.holds(self.plan())['tiktok-photo-1']
        self.assertTrue(hold.startswith(concepts.DEPARTS), hold)
        self.assertIn('claim', hold)

    def test_a_post_with_a_file_that_is_not_the_mock_is_held(self):
        self.slot['assets'][1] = {'name': 'frame-4.png', 'sha256': self.spec['inputs'][0]['manifest']['files'][3]['sha256'],
                                  'url': self.slot['assets'][1]['url'], 'bytes': 34}
        self.slot['payload_sha256'] = release.slot_digest(self.slot)
        hold = self.holds(self.plan())['tiktok-photo-1']
        self.assertTrue(hold.startswith(concepts.DEPARTS), hold)
        self.assertIn('not the approved mock files', hold)

    def test_a_post_on_a_placement_he_did_not_approve_is_held(self):
        self.concept['placements'] = [{'channel': 'instagram', 'format': 'carousel'}]
        self.concept['concept_sha256'] = concepts.concept_sha256(self.concept)
        self.decision['concepts'] = {'carousel-synthetic': self.concept['concept_sha256']}
        self.sign()
        self.assertIn('placements', self.holds(self.plan())['tiktok-photo-1'])

    def test_a_concept_approved_at_another_hash_covers_nothing(self):
        self.concept['idea'] = 'TEST FIXTURE carousel, changed after his yes'
        self.concept['concept_sha256'] = concepts.concept_sha256(self.concept)
        self.assertIn('not approved at this concept_sha256', self.holds(self.plan())['tiktok-photo-1'])

    def test_a_concepts_map_that_does_not_match_the_signature_refuses_the_run(self):
        self.decision['concepts']['carousel-other'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'concepts_digest'):
            self.plan()

    def test_his_purge_on_a_concept_stops_every_post_from_it_even_one_signed_alone(self):
        self.decision['slots']['tiktok-photo-1'] = self.slot['payload_sha256']
        self.decision['stopped_concepts'] = ['carousel-synthetic']
        self.sign()
        hold = self.holds(self.plan())['tiktok-photo-1']
        self.assertTrue(hold.startswith(concepts.STOPPED), hold)

    def test_a_stop_on_the_mix_plan_stops_every_concept_it_carried(self):
        hold = self.holds(self.plan(stopped=(MIX_PLAN,)))['tiktok-photo-1']
        self.assertTrue(hold.startswith(concepts.STOPPED), hold)
        self.assertEqual(self.holds(self.plan(stopped=('another-plan',))), {})

    def test_one_concept_never_posts_past_the_channel_daily_cap(self):
        # Reviewer probe: nine copies of an approved post on the same day, each with new words after the claim.
        for n in range(9):
            twin = copy.deepcopy(self.slot)
            twin['slot_id'] = 'twin-%d' % n
            twin['words'] = self.slot['words'] + ' Variant %d, a sentence nobody reviewed.' % n
            twin['payload_sha256'] = release.slot_digest(twin)
            self.spec['slots'].append(twin)
        reviews = {s['slot_id']: send_test_pass(s) for s in self.spec['slots'] if s.get('share')}
        result = self.plan(reviews=reviews)
        made = [c['slot_id'] for c in result['calls'] if c['slot_id'] == 'tiktok-photo-1' or c['slot_id'].startswith('twin')]
        self.assertEqual(len(made), 4, 'at most four a New York day on TikTok')
        capped = [h for sid, h in self.holds(result).items() if sid.startswith('twin')]
        self.assertEqual(len(capped), 6)
        self.assertTrue(all(h.startswith('concept_daily_cap_reached') for h in capped), capped)
        # Unreviewed words never ride on the claim: without their own review the twins hold.
        result = self.plan(reviews={'tiktok-photo-1': send_test_pass(self.slot)})
        made = [c['slot_id'] for c in result['calls'] if c['slot_id'].startswith('twin')]
        self.assertEqual(made, [])
        self.assertTrue(all(h.startswith('concept_post_not_reviewed') for sid, h in self.holds(result).items()
                            if sid.startswith('twin')))

    def test_the_cap_counts_other_runs_and_this_runs_ledger(self):
        day = [{'channel': 'tiktok', 'due_at': '2026-11-03T08:30:00-05:00'}] * 4
        hold = self.holds(self.plan(other=day))['tiktok-photo-1']
        self.assertTrue(hold.startswith('concept_daily_cap_reached'), hold)
        self.assertEqual(self.holds(self.plan(other=day[:3])), {})
        other_day = [{'channel': 'tiktok', 'due_at': '2026-11-04T08:30:00-05:00'}] * 4
        self.assertEqual(self.holds(self.plan(other=other_day)), {}, 'another New York day has its own four')
        hold = self.holds(self.plan(caps={'tiktok': None}))['tiktok-photo-1']
        self.assertTrue(hold.startswith('concept_daily_cap_unknown'), hold)
        entry = self.plan()['ledger']['released']['tiktok-photo-1']
        self.assertEqual(entry['due_at'], self.slot['due_at'], 'the ledger records the day it lands on')

    def test_the_cap_his_plan_states_is_kept_under_a_higher_live_cap(self):
        # decision.json concept_daily_caps is the most a day the approved plan stated; release keeps the lower.
        day = [{'channel': 'tiktok', 'due_at': '2026-11-03T08:30:00-05:00'}] * 2
        self.decision['concept_daily_caps'] = {'tiktok': 2}
        hold = self.holds(self.plan(other=day))['tiktok-photo-1']
        self.assertTrue(hold.startswith('concept_daily_cap_reached'), hold)
        self.assertIn('at most 2 a day', hold)
        self.decision['concept_daily_caps'] = {'tiktok': 'four'}
        hold = self.holds(self.plan())['tiktok-photo-1']
        self.assertTrue(hold.startswith('concept_daily_cap_unknown'), hold)
        self.decision['concept_daily_caps'] = {'tiktok': 9}
        self.assertEqual(self.holds(self.plan(other=day)), {})
        hold = self.holds(self.plan(other=day * 2))['tiktok-photo-1']
        self.assertIn('at most 4 a day', hold, 'a higher stated cap never lifts the live one')

    def test_a_held_decision_cannot_approve_a_concept(self):
        self.decision['concept_hold'] = 'stale_approval: test'
        self.assertIn('holds its concepts', concepts.decision_errors(self.spec, self.decision))

    def test_the_release_command_counts_other_runs_ledgers_for_the_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(release.other_scheduled(root, 'this-run'), [])
            write_json(root / '.scratch' / 'runs' / 'other' / 'ledger.json', {'run_id': 'other-run', 'released': {
                'a': {'channel': 'tiktok', 'due_at': '2026-11-03T08:30:00-05:00'},
                'b': {'channel': 'linkedin', 'scheduled': False}}})
            write_json(root / '.scratch' / 'runs' / 'mine' / 'ledger.json', {'run_id': 'this-run', 'released': {
                'c': {'channel': 'tiktok', 'due_at': '2026-11-03T12:30:00-05:00'}}})
            found = release.other_scheduled(root, 'this-run')
            self.assertEqual([(f['channel'], f['due_at']) for f in found], [('tiktok', '2026-11-03T08:30:00-05:00')])
            (root / '.scratch' / 'runs' / 'other' / 'ledger.json').write_text('not json', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'cannot be read'):
                release.other_scheduled(root, 'this-run')

    def test_a_concept_post_with_no_passing_review_is_held(self):
        hold = self.holds(self.plan(reviews={}))['tiktok-photo-1']
        self.assertTrue(hold.startswith('concept_post_not_reviewed'), hold)
        stale = send_test_pass(self.slot)
        stale['payload_sha256'] = '0' * 64
        hold = self.holds(self.plan(reviews={'tiktok-photo-1': stale}))['tiktok-photo-1']
        self.assertIn('payload_sha256', hold)

    def test_an_unresolved_decline_holds_every_concept_post(self):
        hold = self.holds(self.plan(unresolved=('some-check-in',)))['tiktok-photo-1']
        self.assertTrue(hold.startswith(release.STOP_UNRESOLVED), hold)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(release.unresolved_stops(root), ())
            write_json(root / '.scratch' / 'cc' / 'golive-ledger.json',
                       {'acted': {}, 'stopped': {}, 'unresolved': {'check-in-1': 'declined'}})
            self.assertEqual(release.unresolved_stops(root), ('check-in-1',))

    def test_concepts_without_the_mix_plan_in_the_signature_refuse_the_run(self):
        # Reviewer probe: with no concept_proposal_id a no on the mix plan could not stop the concept.
        del self.spec['signature']['concept_proposal_id']
        with self.assertRaisesRegex(ValueError, 'concept_proposal_id'):
            self.plan(stopped=(MIX_PLAN,))
        self.spec['signature']['concept_proposal_id'] = 'makeyourmindup:mix:2026-W46'
        with self.assertRaisesRegex(ValueError, 'concept_proposal_id'):
            self.plan()
        self.spec['signature']['concept_proposal_id'] = MIX_PLAN
        del self.spec['window']
        with self.assertRaisesRegex(ValueError, 'window'):
            self.plan()

    def test_the_release_command_reads_stopped_plans_from_the_loop_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(release.stopped_plans(root), ())
            write_json(root / '.scratch' / 'cc' / 'golive-ledger.json', {'acted': {}, 'stopped': {MIX_PLAN: 'declined'},
                                                                         'unresolved': {}})
            self.assertEqual(release.stopped_plans(root), (MIX_PLAN,))
            (root / '.scratch' / 'cc' / 'golive-ledger.json').write_text('not json', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'cannot be read'):
                release.stopped_plans(root)

    def test_linkedin_and_other_channels_are_never_covered_by_a_concept(self):
        linked = next(s for s in self.spec['slots'] if s['slot_id'] == 'linkedin-1')
        errors = concepts.match_errors(linked, dict(self.concept, placements=[{'channel': 'linkedin',
                                                                               'format': 'single-image'}]))
        self.assertTrue(any('not one of the concept channels' in e for e in errors))
        self.assertTrue(any('LinkedIn stays his click' in e for e in errors))
        self.assertTrue(concepts.concept_errors(dict(self.concept, placements=[{'channel': 'threads', 'format': 'text'}])))

    def test_a_text_post_on_x_from_a_concept_with_mocks_is_not_held_for_carrying_none(self):
        # level_up places X as text (max_assets 0) beside carousels that carry the mock files.
        concept = dict(self.concept, placements=[{'channel': 'tiktok', 'format': 'carousel'},
                                                 {'channel': 'x', 'format': 'text'}])
        x_post = dict(self.slot, channel='x', format='text', assets=[])
        self.assertEqual(concepts.match_errors(x_post, concept), [])
        unknown = concepts.match_errors(x_post, concept, formats={})
        self.assertIn('the post carries none of the approved mock files', unknown,
                      'a format whose records cannot be read is not text only')
        carousel = dict(self.slot, assets=[])
        self.assertIn('the post carries none of the approved mock files', concepts.match_errors(carousel, concept))

    def test_copy_lint_still_holds_a_concept_post(self):
        self.slot['words'] = self.claim + ' Generated by AI.'
        self.slot['payload_sha256'] = release.slot_digest(self.slot)
        hold = self.holds(self.plan())['tiktok-photo-1']
        self.assertTrue(hold.startswith('copy_lint_refused'), hold)


class LintAndStatus(unittest.TestCase):
    def spec(self):
        base = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        words = ('TEST FIXTURE ONLY. A pilot earns its budget line when one number is agreed on day one.'
                 ' More from Mindmake: https://mindmake.co/')
        base['concepts'] = [{'concept_id': 'level-up-pilot', 'lane': 'level_up', 'idea': 'TEST FIXTURE one move',
                             'claim': 'A pilot earns its budget line when one number is agreed on day one.',
                             'source_url': None, 'piece_id': None, 'mock_sha256': [],
                             'placements': [{'channel': 'x', 'format': 'text'}], 'concept_sha256': '0' * 64}]
        base['slots'] = [{'slot_id': 'x-concept', 'channel': 'x', 'format': 'text', 'play': None,
                          'due_at': '2026-11-03T08:30:00-05:00', 'words': words, 'assets': [], 'link_placement': None,
                          'cta': False, 'forward_line': 'not shared', 'experiment_arm': None, 'publish_mode': 'engine',
                          'buffer_draft_id': None, 'concept_id': 'level-up-pilot',
                          'ecosystem_cta': {'route': 'mindmake', 'url': 'https://mindmake.co/', 'placement': 'in_post'},
                          'payload_sha256': '0' * 64}]
        return spec_module.computed(base)

    def codes(self, spec):
        return {e['code'] for e in spec_module.lint(spec)['errors']}

    def test_a_concept_slot_that_matches_lints_clean_and_its_hash_is_computed(self):
        spec = self.spec()
        self.assertEqual(spec['concepts'][0]['concept_sha256'], concepts.concept_sha256(spec['concepts'][0]))
        self.assertEqual(self.codes(spec), set(), spec_module.lint(spec)['errors'])
        spec['concepts'][0]['concept_sha256'] = '1' * 64
        self.assertIn('concept', self.codes(spec), 'concept_sha256 is computed, never typed')

    def test_a_slot_that_departs_from_its_concept_is_a_lint_error(self):
        spec = self.spec()
        spec['slots'][0]['words'] = spec['slots'][0]['words'].replace('one number', 'two numbers')
        self.assertIn('concept_mismatch', self.codes(spec_module.computed(spec)))
        spec = self.spec()
        spec['slots'][0]['concept_id'] = 'nowhere'
        self.assertIn('unknown_concept', self.codes(spec))
        spec = self.spec()
        spec['concepts'][0]['lane'] = 'invented_lane'
        self.assertIn('concept', self.codes(spec_module.computed(spec)))

    def test_signing_the_concept_approves_its_mock_for_the_posts_made_from_it(self):
        spec = self.spec()
        mock = 'ab' * 32
        spec['concepts'][0].update(mock_sha256=[mock], placements=[{'channel': 'x', 'format': 'single-image'}])
        spec['slots'][0].update(format='single-image', assets=[{'name': 'card.png', 'sha256': mock, 'url': None,
                                                                 'bytes': 10}])
        spec = spec_module.computed(spec)
        self.assertNotIn('creative_not_approved', self.codes(spec))
        spec['slots'][0]['concept_id'] = None
        self.assertIn('creative_not_approved', self.codes(spec_module.computed(spec)),
                      'without the concept the file is in no approved manifest')

    def test_a_narrowed_pack_carries_only_the_concepts_its_posts_are_made_from(self):
        from engine.run.pack import spec_slice
        spec = self.spec()
        spec['concepts'].append(dict(spec['concepts'][0], concept_id='meme-unused'))
        part = spec_slice(spec, channel='x')
        self.assertEqual([c['concept_id'] for c in part['concepts']], ['level-up-pilot'])
        self.assertEqual(spec_slice(spec, channel='threads')['concepts'], [])
        self.assertEqual(len(spec_slice(spec)['concepts']), 2, 'the whole spec keeps every concept')

    def test_status_counts_a_concept_post_as_signed_and_a_stopped_one_as_not(self):
        spec = self.spec()
        slot = spec['slots'][0]
        decision = {'run_id': spec['run_id'], 'proposal_id': 'p', 'decision': 'approved', 'decided_at': 'x',
                    'slots': {}, 'concepts': {'level-up-pilot': spec['concepts'][0]['concept_sha256']}}
        self.assertEqual(spec_module.signed_digest(slot, decision, None, spec), (slot['payload_sha256'], None))
        self.assertEqual(spec_module.signed_digest(slot, decision)[1], 'decision.json has no entry for this slot',
                         'without the spec a slot needs its own digest')
        stopped = dict(decision, stopped_concepts=['level-up-pilot'])
        self.assertTrue(spec_module.signed_digest(slot, stopped, None, spec)[1].startswith(concepts.STOPPED))
        spec['signature'] = {'go_live_proposal_id': 'p', 'decision_digest': spec_module.sha256_hex({}),
                             'signed_at': '2026-11-01T10:00:00-05:00'}
        self.assertIn('concepts_digest', spec_module.decision_errors(spec, decision))
        spec['signature']['concepts_digest'] = concepts.concepts_digest(decision['concepts'])
        self.assertIn('concept_proposal_id', spec_module.decision_errors(spec, decision))
        spec['signature']['concept_proposal_id'] = MIX_PLAN
        self.assertIsNone(spec_module.decision_errors(spec, decision))


if __name__ == '__main__':
    unittest.main()
