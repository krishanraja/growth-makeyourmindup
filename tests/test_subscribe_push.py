"""The U4 and U5 subscriber push (Ruling, Krish, 2026-11-11). Synthetic data only.

Every post carries a subscribe route at the conversion urgency in intensity.json, beside the ecosystem
route; Acquisition prepares a daily batch of one-person outreach drafts; the volume walls rose (Substack
Notes four a day, engagement taps 25 at U5).
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine import intensity
from engine.engines import acquisition
from engine.share import cta_errors
from engine.social import max_daily_posts
from engine.run.spec import computed, lint
from tests import test_run_release as release_tests

ROOT = Path(__file__).resolve().parents[1]
RECORDS = json.loads((ROOT / 'specs' / 'fixtures' / 'social-records.json').read_text(encoding='utf-8'))
PAGE = 'https://home.makeyourmindup.ai/subscribe'
TAGGED = PAGE + '?utm_source=threads&utm_medium=organic&utm_campaign=growth&utm_content=w45-test'


def errors(cta, channel='threads', words='TEST FIXTURE ONLY. ' + TAGGED, placement=None, urgency=5):
    return intensity.subscribe_errors(cta, channel, words, placement, urgency)


class Bounds(unittest.TestCase):
    def root_with(self, folder, change):
        value = json.loads((ROOT / 'intensity.json').read_text(encoding='utf-8'))
        change(value)
        (Path(folder) / 'intensity.json').write_text(json.dumps(value), encoding='utf-8')
        return Path(folder)

    def test_the_repository_bounds_load(self):
        value = intensity.bounds()
        self.assertEqual(value['conversion']['applies_from_urgency'], 4)
        self.assertEqual(value['engagement_taps']['by_urgency']['5'], 25)

    def test_malformed_conversion_or_outreach_blocks_are_refused(self):
        for change in (lambda v: v.pop('conversion'),
                       lambda v: v['conversion'].update(applies_from_urgency=6),
                       lambda v: v['conversion'].update(subscribe_url='http://home.makeyourmindup.ai/subscribe'),
                       lambda v: v['conversion']['placements'].update(link_sticker='no'),
                       lambda v: v.pop('outreach_drafts'),
                       lambda v: v['outreach_drafts']['by_urgency'].update({'5': 50}),
                       lambda v: v['outreach_drafts']['by_urgency'].pop('1')):
            with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
                intensity.bounds(self.root_with(folder, change))


class Walls(unittest.TestCase):
    def test_notes_rise_to_four_and_no_further(self):
        self.assertEqual(max_daily_posts('substack-notes'), 4)
        self.assertEqual(intensity.daily_cap({'id': 'substack-notes', 'daily_posts_target': 2}, 5), 4)
        self.assertEqual(intensity.daily_cap({'id': 'threads', 'daily_posts_target': 1}, 5), 1)

    def test_u5_taps_sit_at_control_centers_ceiling(self):
        self.assertEqual(intensity.engagement_taps(5), 25)
        self.assertEqual(intensity.engagement_taps(4), 15)


class SubscribeRoute(unittest.TestCase):
    def test_required_only_at_u4_and_u5(self):
        for level in (None, 1, 2, 3):
            self.assertEqual(errors(None, urgency=level), [], 'U' + str(level))
        for level in (4, 5):
            self.assertIn('no subscribe route', errors(None, urgency=level)[0])

    def test_a_tagged_in_post_route_passes(self):
        self.assertEqual(errors({'url': TAGGED, 'placement': 'in_post'}), [])

    def test_the_route_is_the_tagged_subscribe_page(self):
        self.assertIn('not the subscribe page', errors({'url': 'https://makeyourmindup.ai/p/a', 'placement': 'in_post'})[0])
        self.assertIn('not the subscribe page', errors({'url': 'https://home.makeyourmindup.ai.evil.example/subscribe'
                                                               '?utm_source=x&utm_content=y', 'placement': 'in_post'})[0])
        self.assertIn('source tags', errors({'url': PAGE, 'placement': 'in_post'}, words=PAGE)[0])

    def test_placements(self):
        self.assertIn('URL in the words', errors({'url': TAGGED, 'placement': 'in_post'}, words='TEST FIXTURE ONLY.')[0])
        self.assertIn('link_placement first_reply', errors({'url': TAGGED, 'placement': 'first_reply'})[0])
        self.assertEqual(errors({'url': TAGGED, 'placement': 'first_reply'}, placement='first_reply'), [])
        self.assertIn('profile_link is only for', errors({'url': TAGGED, 'placement': 'profile_link'})[0])
        self.assertIn('point to the profile link', errors({'url': TAGGED, 'placement': 'profile_link'},
                                                          channel='instagram', words='TEST FIXTURE ONLY.')[0])
        self.assertEqual(errors({'url': TAGGED, 'placement': 'profile_link'}, channel='instagram',
                                words='TEST FIXTURE ONLY. The full playbook: link in bio.'), [])
        self.assertIn('unknown subscribe placement', errors({'url': TAGGED, 'placement': 'sticker'})[0])

    def test_a_subscribe_route_is_never_a_share_ask(self):
        self.assertEqual(cta_errors('TEST FIXTURE ONLY. Subscribe for the full playbook: ' + TAGGED), [])

    def test_spec_lint_refuses_a_routeless_slot_at_u5_and_accepts_a_routed_one(self):
        spec = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        routeless = [e for e in lint(computed(copy.deepcopy(spec)), RECORDS, urgency=5)['errors']
                     if e['code'] == 'subscribe_cta']
        self.assertEqual(len(routeless), len(spec['slots']))
        for slot in spec['slots']:
            slot['subscribe_cta'] = {'url': TAGGED, 'placement': 'first_reply'}
            slot['link_placement'] = 'first_reply'
        self.assertEqual([e for e in lint(computed(spec), RECORDS, urgency=5)['errors']
                          if e['code'] == 'subscribe_cta'], [])


class ReleaseHolds(unittest.TestCase):
    """release_plan holds a routeless slot at U5; the release fixture and its setup are reused, not rerun."""
    setUp = release_tests.ReleaseTests.setUp
    tearDown = release_tests.ReleaseTests.tearDown
    paths = release_tests.ReleaseTests.paths

    def plan(self, urgency):
        return release_tests.release.release_plan(self.spec, self.decision, None, self.paths(), self.channels,
                                                  release_tests.NOW, self.targets, urgency=urgency)

    def test_u5_holds_a_slot_without_a_subscribe_route(self):
        refused = lambda result: {h['slot_id'] for h in result['holds'] if h['hold'].startswith('subscribe_cta_refused')}
        self.assertEqual(refused(self.plan(3)), set())
        self.assertTrue(refused(self.plan(5)), 'at U5 a routeless slot never releases')
        self.assertFalse(self.plan(5)['calls'], 'and nothing routeless is released')


class PackagePreflight(unittest.TestCase):
    def test_u5_refuses_a_package_without_a_subscribe_route(self):
        from engine.social import preflight
        from tests import test_social
        with tempfile.TemporaryDirectory() as tmp:
            package = test_social.SocialContractsTests.fixture(None, Path(tmp) / 'asset.bin')
            preflight(copy.deepcopy(package), '2026-10-26', urgency=3)
            with self.assertRaisesRegex(ValueError, 'subscribe route'):
                preflight(copy.deepcopy(package), '2026-10-26', urgency=5)
            package['subscribe_cta'] = {'url': TAGGED, 'placement': 'in_post'}
            package['caption'] = 'Synthetic test copy. ' + TAGGED
            preflight(package, '2026-10-26', urgency=5)


class OutreachBatch(unittest.TestCase):
    def test_quota_follows_urgency(self):
        self.assertEqual([intensity.outreach_drafts(u) for u in (None, 1, 2, 3, 4, 5)], [0, 0, 0, 2, 3, 5])

    def test_recover_names_the_batch_and_counts_todays_drafts(self):
        today = {'id': 'o1', 'kind': 'outreach', 'state': 'approved', 'updated_at': '2026-11-11'}
        batch = acquisition.daily_outreach({'o1': today}, '2026-11-11', 5)
        self.assertEqual((batch['quota'], batch['drafted_today'], batch['remaining']), (5, 1, 4))
        self.assertTrue(batch['lean_on'])
        self.assertEqual(acquisition.daily_outreach({}, '2026-11-11', 2)['lean_on'], [])

    def test_recover_leads_with_the_batch_when_nothing_waits(self):
        found = acquisition.recover({}, {}, '2026-11-11', urgency=5)
        self.assertEqual(found['daily_outreach']['remaining'], 5)
        self.assertIn('Substack-native outreach', found['next_action']['title'])


if __name__ == '__main__':
    unittest.main()
