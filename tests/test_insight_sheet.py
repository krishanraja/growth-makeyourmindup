"""The insight desk adapter (Ruling, Krish, 2026-11-24): the sheet check and `mix plan --insight`.

Synthetic fixtures only. Nothing here reads the network or a real sheet.
"""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from engine import insight_sheet, mix
from engine.core import write_json

ROOT = Path(__file__).resolve().parents[1]
WEEK = '2026-11-09'
LANES = {'meme', 'positive_news', 'level_up'}


def passed(reason='TEST FIXTURE reason'):
    return {'result': 'pass', 'reason': reason}


def idea(iid, level='campaign', analogue=True, method='invert-the-default'):
    return {'id': iid, 'claim': 'TEST FIXTURE claim for ' + iid + '.', 'mechanic': 'TEST FIXTURE mechanic ' + iid,
            'idea_level': level, 'method': method, 'channel_role': 'carousel',
            'conversion_path': {'offer': 'the free publication', 'link': 'tracked link', 'why_act': 'synthetic'},
            'kill_condition': 'Synthetic: no new subscribers in two weeks.',
            'tests': {'specificity': passed(), 'share': passed(),
                      'analogue': dict(passed(), url='https://example.org/analogue', read_at='2026-11-24')
                      if analogue else {'result': 'unavailable', 'reason': 'none found', 'url': None,
                                        'read_at': None},
                      'floor': passed(), 'kill_the_favourite': passed()}}


def sheet(**changes):
    value = {'schema': 'insight-sheet/1', 'venture': 'makeyourmindup', 'repo': 'example-owner/example-engine',
             'harness_skill_sha': '0' * 40, 'made_at': '2026-11-24T09:00:00Z',
             'north_star': {'metric': 'Synthetic weekly subscribers', 'urgency': 5, 'current': 0,
                            'as_of': '2026-11-24'},
             'stall_check': {'diagnosis': 'idea', 'evidence': 'Synthetic fixture.'},
             'insights': [{'audience': 'synthetic leaders', 'wants': 'x', 'but': 'y', 'because': 'z',
                           'assumption': True}],
             'chosen_insight': 0,
             'discarded_obvious': ['Obvious one', 'Obvious two', 'Obvious three'],
             'ideas': [idea('first-move'), idea('second-move', analogue=False)],
             'consults': [{'engine': 'divergent-thinker', 'op': 'score', 'result': 'unavailable',
                           'ref': 'fixture: not served'}],
             'lead': 'first-move',
             'blind_passes': [{'reader': 'reader one', 'order': ['first-move', 'second-move'], 'lead': 'first-move'},
                              {'reader': 'reader two', 'order': ['second-move', 'first-move'], 'lead': 'first-move'}]}
    value.update(changes)
    value['sheet_sha256'] = insight_sheet.sheet_sha(value)
    return value


def inventory():
    pairs = [('instagram', 'carousel'), ('tiktok', 'carousel'), ('youtube', 'short-video'), ('x', 'single-image')]
    return {'schema_version': 1, 'kind': 'backlog_inventory', 'pieces': [
        {'piece_id': 'piece_%020x' % (n + 1), 'url': 'https://home.makeyourmindup.ai/p/synthetic-%02d' % n,
         'title': 'TEST FIXTURE piece %02d' % n, 'kind': 'article',
         'published_at': '2026-01-%02dT12:00:00+00:00' % (n + 1), 'video_post_url': None, 'status': 'unamplified',
         'editions': [], 'channels_open': [], 'formats_open': [{'channel': c, 'format': f} for c, f in pairs]}
        for n in range(20)]}


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mix.command(argv, ROOT, client_factory=None)
    return code, out.getvalue(), err.getvalue()


class AdapterTest(unittest.TestCase):
    def test_the_adapter_names_the_skill_its_hook_and_a_lane_that_takes_ideas(self):
        cfg = insight_sheet.adapter(ROOT)
        self.assertEqual(cfg['schema'], 'insight-desk-adapter/1')
        self.assertEqual(cfg['skill']['name'], 'insight-desk')
        self.assertEqual(cfg['venture'], 'makeyourmindup')
        self.assertEqual(cfg['divergent']['namespace'], 'growth-makeyourmindup:ideas')
        self.assertFalse(cfg['sheets']['committed'])
        self.assertTrue(cfg['sheets']['path'].startswith('.scratch/'))
        idea_lanes = {n for n, lane in mix.load(ROOT)['lanes'].items() if lane['source'] == 'ideas'}
        self.assertEqual(set(cfg['hook']['lanes']), idea_lanes)
        self.assertIn(cfg['hook']['default_lane'], idea_lanes)
        for path in cfg['floor'] + [cfg['north_star']['doc'], cfg['humour']['command'], cfg['divergent']['client']]:
            self.assertTrue((ROOT / path).exists(), path)

    def test_agents_md_carries_the_insight_desk_section(self):
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('## Insight desk', text)
        self.assertIn('config/insight-desk.json', text)

    def test_the_adapter_and_module_carry_no_em_dash(self):
        for path in ('config/insight-desk.json', 'engine/insight_sheet.py'):
            self.assertNotIn(chr(0x2014), (ROOT / path).read_text(encoding='utf-8'), path)


class CheckTest(unittest.TestCase):
    def test_a_good_sheet_passes(self):
        self.assertEqual(insight_sheet.check(sheet()), [])

    def test_a_changed_sheet_fails_its_hash(self):
        bad = sheet()
        bad['ideas'][0]['claim'] = 'Changed after hashing.'
        self.assertTrue(any('sheet_sha256' in e for e in insight_sheet.check(bad)))

    def test_a_stall_that_is_not_the_idea_makes_no_sheet(self):
        errors = insight_sheet.check(sheet(stall_check={'diagnosis': 'distribution', 'evidence': 'Synthetic.'}))
        self.assertTrue(any('not the idea' in e for e in errors))

    def test_at_u4_with_nothing_measured_only_measurement_ideas(self):
        bad = sheet(north_star={'metric': 'm', 'urgency': 4, 'current': None, 'as_of': None})
        self.assertTrue(any('measurement idea' in e for e in insight_sheet.check(bad)))

    def test_a_lead_needs_every_test_and_both_blind_passes(self):
        unlinked = sheet(lead='second-move', blind_passes=[
            {'reader': 'reader one', 'order': ['first-move', 'second-move'], 'lead': 'second-move'},
            {'reader': 'reader two', 'order': ['second-move', 'first-move'], 'lead': 'second-move'}])
        self.assertTrue(any('every test passed' in e for e in insight_sheet.check(unlinked)))
        split = sheet(blind_passes=[
            {'reader': 'reader one', 'order': ['first-move', 'second-move'], 'lead': 'first-move'},
            {'reader': 'reader two', 'order': ['second-move', 'first-move'], 'lead': 'second-move'}])
        self.assertTrue(any('same lead' in e for e in insight_sheet.check(split)))
        same_order = sheet(blind_passes=[
            {'reader': 'reader one', 'order': ['first-move', 'second-move'], 'lead': 'first-move'},
            {'reader': 'reader two', 'order': ['first-move', 'second-move'], 'lead': 'first-move'}])
        self.assertTrue(any('shuffled' in e for e in insight_sheet.check(same_order)))

    def test_no_scores_and_no_conversionless_idea(self):
        scored = sheet()
        scored['ideas'][0]['tests']['share']['score'] = 9
        scored['sheet_sha256'] = insight_sheet.sheet_sha(scored)
        self.assertTrue(any('no scores' in e for e in insight_sheet.check(scored)))
        held = sheet()
        held['ideas'][0]['conversion_path']['link'] = ''
        held['sheet_sha256'] = insight_sheet.sheet_sha(held)
        self.assertTrue(any('conversion path' in e for e in insight_sheet.check(held)))

    def test_an_unavailable_consult_is_never_a_pass_and_an_unknown_result_is_refused(self):
        bad = sheet(consults=[{'engine': 'divergent-thinker', 'op': 'score', 'result': 'skipped', 'ref': 'x'}])
        self.assertTrue(any('never pass' in e for e in insight_sheet.check(bad)))

    def test_methods_are_checked_by_name_when_the_skill_is_readable(self):
        self.assertEqual(insight_sheet.check(sheet(), {'invert-the-default'}), [])
        self.assertTrue(any('not one of the skill' in e for e in insight_sheet.check(sheet(), {'other'})))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'candidates' / 'insight-desk' / 'references' / 'methods-by-category.md'
            path.parent.mkdir(parents=True)
            path.write_text('# Methods\n\n### `invert-the-default`\n\nSynthetic.\n', encoding='utf-8')
            self.assertEqual(insight_sheet.known_methods(folder), {'invert-the-default'})
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(insight_sheet.known_methods())

    def test_the_command_line_checks_and_prints_the_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sheet.json'
            good = sheet()
            write_json(path, good)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(insight_sheet.main([str(path)]), 0)
                self.assertEqual(insight_sheet.main([str(path), '--print-sha']), 0)
            self.assertIn('VALID insight-sheet/1', out.getvalue())
            self.assertIn(good['sheet_sha256'], out.getvalue())
            good['lead'] = 'nobody'
            write_json(path, good)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(insight_sheet.main([str(path)]), 1)


class ToIdeasTest(unittest.TestCase):
    def test_each_idea_takes_the_mix_idea_shape(self):
        ideas, refused, record = insight_sheet.to_ideas(sheet(), 'level_up', LANES)
        self.assertEqual(refused, [])
        self.assertEqual([i['idea_id'] for i in ideas], ['first-move', 'second-move'])
        first = ideas[0]
        self.assertEqual(set(first), {'idea_id', 'lane', 'idea', 'claim', 'source_url', 'source_date', 'source'})
        self.assertEqual((first['lane'], first['idea'], first['claim']),
                         ('level_up', 'TEST FIXTURE mechanic first-move', 'TEST FIXTURE claim for first-move.'))
        self.assertIsNone(first['source_url'])
        self.assertEqual(first['source'], 'insight-sheet:' + sheet()['sheet_sha256'])
        self.assertEqual((record['sheet_sha256'], record['harness_skill_sha'], record['lead']),
                         (sheet()['sheet_sha256'], '0' * 40, 'first-move'))

    def test_failed_measurement_and_duplicate_ideas_are_refused_with_why(self):
        failed = idea('failed-move')
        failed['tests']['share'] = {'result': 'fail', 'reason': 'nobody would send it'}
        value = sheet(ideas=[failed, idea('measure-it', level='measurement'), idea('first-move')], lead=None,
                      blind_passes=[{'reader': 'r1', 'order': ['failed-move', 'measure-it', 'first-move'], 'lead': None},
                                    {'reader': 'r2', 'order': ['first-move', 'measure-it', 'failed-move'], 'lead': None}])
        self.assertEqual(insight_sheet.check(value), [])
        ideas, refused, _ = insight_sheet.to_ideas(value, 'meme', LANES, taken={'first-move'})
        self.assertEqual(ideas, [])
        self.assertEqual([r['idea_id'] for r in refused], ['failed-move', 'measure-it', 'first-move'])
        self.assertIn('share', refused[0]['why'])

    def test_a_lane_that_takes_no_ideas_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'takes no ideas'):
            insight_sheet.to_ideas(sheet(), 'repurposed_carousel', LANES)


class MixPlanTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)
        self.inventory = self.dir / 'inventory.json'
        write_json(self.inventory, inventory())
        self.sheet = self.dir / 'sheet.json'
        write_json(self.sheet, sheet())

    def tearDown(self):
        self.folder.cleanup()

    def plan(self, *extra):
        out = self.dir / ('mix-%d.json' % len(list(self.dir.glob('mix-*.json'))))
        code, _, err = run(['plan', '--week-of', WEEK, '--inventory', str(self.inventory), '--no-learn',
                            '--urgency', '4', '--offline', '--out', str(out)] + list(extra))
        self.assertEqual(code, 0, err)
        return json.loads(out.read_text(encoding='utf-8'))

    def test_without_insight_the_plan_is_exactly_as_before(self):
        before = mix.plan(inventory(), WEEK, (), urgency=4)
        self.assertEqual(json.loads(json.dumps(before)), self.plan())
        self.assertNotIn('insight', self.plan())

    def test_sheet_ideas_are_laid_out_like_ideas_given_by_hand(self):
        with_sheet = self.plan('--insight', str(self.sheet))
        by_hand_ideas = [{'idea_id': i['idea_id'], 'lane': i['lane'], 'idea': i['idea'], 'claim': i['claim'],
                          'source_url': None, 'source_date': None}
                         for i in insight_sheet.to_ideas(sheet(), 'level_up', LANES)[0]]
        by_hand = self.dir / 'ideas.json'
        write_json(by_hand, by_hand_ideas)
        plain = self.plan('--ideas', str(by_hand))
        record = with_sheet.pop('insight')
        self.assertEqual(with_sheet, plain)
        self.assertEqual(record['ideas'], ['first-move', 'second-move'])
        self.assertEqual(record['sheet_sha256'], sheet()['sheet_sha256'])
        ids = {c['concept_id'] for c in with_sheet['concepts']}
        self.assertTrue({'level-up-first-move', 'level-up-second-move'} <= ids)
        self.assertNotIn(sheet()['sheet_sha256'], with_sheet['proposal']['exact_payload'])

    def test_concept_sha256_is_unchanged_by_the_route_an_idea_took(self):
        mocks = {cid: {'claim': 'Synthetic claim.', 'mock_sha256': ['%064x' % 7]}
                 for cid in ('level-up-first-move', 'level-up-second-move')}
        mocks_path = self.dir / 'mocks.json'
        write_json(mocks_path, mocks)
        with_sheet = self.plan('--insight', str(self.sheet), '--mocks', str(mocks_path))
        by_hand = self.dir / 'ideas.json'
        write_json(by_hand, [{k: v for k, v in i.items() if k != 'source'}
                             for i in insight_sheet.to_ideas(sheet(), 'level_up', LANES)[0]])
        plain = self.plan('--ideas', str(by_hand), '--mocks', str(mocks_path))
        sha = lambda m: {c['concept_id']: c['concept_sha256'] for c in m['concepts']}
        self.assertEqual(sha(with_sheet), sha(plain))
        self.assertTrue(sha(with_sheet)['level-up-first-move'])

    def test_the_lane_is_chosen_and_an_invalid_sheet_makes_no_plan(self):
        memes = self.plan('--insight', str(self.sheet), '--insight-lane', 'meme')
        self.assertEqual(memes['insight']['lane'], 'meme')
        self.assertIn('meme-first-move', {c['concept_id'] for c in memes['concepts']})
        bad = copy.deepcopy(sheet())
        bad['lead'] = 'second-move'
        write_json(self.sheet, bad)
        code, _, err = run(['plan', '--week-of', WEEK, '--inventory', str(self.inventory), '--no-learn',
                            '--urgency', '4', '--offline', '--insight', str(self.sheet)])
        self.assertEqual(code, 1)
        self.assertIn('not valid', err)
        self.assertTrue(re.search(r'sheet_sha256 does not match', err))


if __name__ == '__main__':
    unittest.main()
