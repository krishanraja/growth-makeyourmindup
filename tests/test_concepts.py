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

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'release'
NOW = '2026-11-01T12:00:00-05:00'
MIX_PLAN = 'makeyourmindup:mix:2026-W45'


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
        self.slot['concept_id'] = 'carousel-synthetic'
        del self.decision['slots']['tiktok-photo-1']
        self.decision['concepts'] = {'carousel-synthetic': self.concept['concept_sha256']}
        self.sign()

    def tearDown(self):
        self.tmp.cleanup()

    def sign(self):
        self.spec['signature']['decision_digest'] = release.decision_digest(self.decision)
        self.spec['signature']['concepts_digest'] = concepts.concepts_digest(self.decision.get('concepts') or {})
        self.spec['signature']['concept_proposal_id'] = MIX_PLAN

    def plan(self, stopped=()):
        paths = {s['slot_id']: [self.dir / a['name'] for a in s['assets']] for s in self.spec['slots']}
        return release.release_plan(self.spec, self.decision, None, paths, self.channels, NOW, self.targets,
                                    stopped_proposals=stopped)

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
        self.assertIsNone(spec_module.decision_errors(spec, decision))


if __name__ == '__main__':
    unittest.main()
