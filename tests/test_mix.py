"""The weekly mix, its volume and its learning (Ruling, Krish, 2026-10-29), on synthetic fixtures only."""
import collections
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from engine import cc_loop, intensity, mix
from engine.core import write_json
from engine.run import spec as spec_module
from engine.social import FLOOD_CHANNELS, inventory, max_daily_posts

ROOT = Path(__file__).resolve().parents[1]
WEEK = '2026-11-09'


def piece(n, status='unamplified', made=()):
    """A synthetic backlog piece; n orders them oldest first."""
    pairs = [('instagram', 'carousel'), ('tiktok', 'carousel'), ('youtube', 'short-video'), ('x', 'single-image'),
             ('instagram', 'meme')]
    return {'piece_id': 'piece_%020x' % (n + 1), 'url': 'https://home.makeyourmindup.ai/p/synthetic-%02d' % n,
            'title': 'TEST FIXTURE piece %02d' % n, 'kind': 'article',
            'published_at': '2026-%02d-%02dT12:00:00+00:00' % (1 + n // 28, 1 + n % 28), 'video_post_url': None,
            'status': status, 'editions': [], 'channels_open': [],
            'formats_open': [{'channel': c, 'format': f} for c, f in pairs if (c, f) not in made]}


def inventory_of(count=30):
    return {'schema_version': 1, 'kind': 'backlog_inventory', 'pieces': [piece(n) for n in range(count)]}


def ideas():
    out = []
    for n in range(8):
        out.append({'idea_id': 'meme-%d' % n, 'lane': 'meme', 'idea': 'TEST FIXTURE meme %d' % n,
                    'claim': 'Synthetic meme line %d.' % n, 'source_url': None, 'source_date': None})
    for n in range(5):
        out.append({'idea_id': 'news-%d' % n, 'lane': 'positive_news', 'idea': 'TEST FIXTURE good news %d' % n,
                    'claim': 'Synthetic good news %d.' % n, 'source_url': 'https://example.org/news-%d' % n,
                    'source_date': '2026-11-05'})
    for n in range(3):
        out.append({'idea_id': 'move-%d' % n, 'lane': 'level_up', 'idea': 'TEST FIXTURE one move %d' % n,
                    'claim': 'Synthetic move %d.' % n, 'source_url': None, 'source_date': None})
    return out


def mocks_for(result):
    """Synthetic mock hashes and claims for every concept in a first pass."""
    out = {}
    for i, c in enumerate(result['concepts']):
        out[c['concept_id']] = {'claim': c['claim'] or 'Synthetic claim %d.' % i,
                                'mock_sha256': ['%064x' % (1000 + 10 * i + k) for k in range(3)]}
    return out


def full_plan(**kw):
    first = mix.plan(inventory_of(), WEEK, ideas(), urgency=4)
    return mix.plan(inventory_of(), WEEK, ideas(), mocks_for(first), urgency=4, **kw)


class Volume(unittest.TestCase):
    def test_four_channels_take_four_a_day_with_a_floor_of_three(self):
        records = inventory(ROOT)['channel']
        self.assertEqual(sorted(FLOOD_CHANNELS), ['instagram', 'tiktok', 'x', 'youtube'])
        for name in FLOOD_CHANNELS:
            self.assertEqual((records[name]['daily_posts_target'], records[name]['daily_posts_floor']), (4, 3), name)
            self.assertEqual(max_daily_posts(name), 4)
            for level in (None, 1, 2, 3, 4, 5):
                self.assertGreaterEqual(intensity.daily_cap(records[name], level, ROOT), 3,
                                        'no urgency caps ' + name + ' below three')
        for name in ('facebook', 'threads', 'substack-notes'):
            self.assertLessEqual(records[name]['daily_posts_target'], 2, name + ' keeps its own bound')
        self.assertIsNone(records['linkedin']['daily_posts_target'], 'LinkedIn stays his click')

    def test_a_floor_above_its_target_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            import shutil
            root = Path(folder)
            shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
            for name in ('docs', 'jobs'):
                shutil.copytree(str(ROOT / name), str(root / name))
            path = root / 'social' / 'channels' / 'x.json'
            record = json.loads(path.read_text(encoding='utf-8'))
            record['daily_posts_floor'] = 3
            record['daily_posts_target'] = 3
            path.write_text(json.dumps(record), encoding='utf-8')
            inventory(root)
            record['daily_posts_floor'] = 4
            record['daily_posts_target'] = 3
            path.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'floor'):
                inventory(root)

    def test_run_lint_takes_four_scheduled_x_posts_a_day_and_refuses_a_fifth(self):
        base = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        template = {'slot_id': 'x', 'channel': 'x', 'format': 'text', 'play': None,
                    'words': 'TEST FIXTURE ONLY. A pilot earns its budget line when one number is agreed on day one.'
                             ' More from Mindmake: https://mindmake.co/',
                    'assets': [], 'link_placement': None, 'cta': False, 'forward_line': 'not shared',
                    'experiment_arm': None, 'publish_mode': 'engine', 'buffer_draft_id': None,
                    'ecosystem_cta': {'route': 'mindmake', 'url': 'https://mindmake.co/', 'placement': 'in_post'}}
        spec = copy.deepcopy(base)
        spec['slots'] = []
        for n, hour in enumerate(('08', '12', '17', '20')):
            spec['slots'].append(dict(copy.deepcopy(template), slot_id='x-%d' % n,
                                      due_at='2026-11-03T%s:30:00-05:00' % hour))
        spec = spec_module.computed(spec)
        self.assertNotIn('posts_per_day', {e['code'] for e in spec_module.lint(spec)['errors']})
        spec['slots'].append(dict(copy.deepcopy(template), slot_id='x-4', due_at='2026-11-03T22:30:00-05:00'))
        spec = spec_module.computed(spec)
        self.assertIn('posts_per_day', {e['code'] for e in spec_module.lint(spec)['errors']})


class Layout(unittest.TestCase):
    def test_every_channel_gets_three_or_four_a_day_and_never_under_the_floor(self):
        result = full_plan()
        per_day = collections.Counter((s['channel'], s['day']) for s in result['slots'])
        for channel in FLOOD_CHANNELS:
            for day in mix.DAYS:
                expected = 3 if day in ('Monday', 'Wednesday', 'Friday') else 4
                self.assertEqual(per_day[(channel, day)], expected, channel + ' ' + day)
        self.assertEqual(sum(per_day.values()), 4 * 25)
        self.assertEqual(result['external_writes'], 0)

    def test_the_default_ratio_is_half_repurposed_carousels(self):
        result = full_plan()
        self.assertEqual(result['weights'], {'repurposed_carousel': 50, 'meme': 25, 'positive_news': 15, 'level_up': 10})
        for channel in FLOOD_CHANNELS:
            self.assertEqual(result['per_channel'][channel],
                             {'repurposed_carousel': 13, 'meme': 6, 'positive_news': 4, 'level_up': 2})

    def test_lanes_are_interleaved_through_the_week_not_bunched(self):
        result = full_plan()
        order = [s['lane'] for s in result['slots'] if s['channel'] == 'instagram']
        for a, b in zip(order, order[1:]):
            self.assertFalse(a == b == 'meme', 'two memes never run back to back')
        days = collections.defaultdict(set)
        for s in result['slots']:
            days[(s['channel'], s['day'])].add(s['lane'])
        self.assertTrue(all('repurposed_carousel' in lanes for lanes in days.values()),
                        'a repurposed carousel every day on every channel')

    def test_oldest_unamplified_first_and_no_repeat_on_a_channel(self):
        inv = inventory_of()
        inv['pieces'].insert(0, piece(99, status='partial'))  # partial sorts after unamplified in the inventory
        inv['pieces'].append(inv['pieces'].pop(0))
        result = mix.plan(inv, WEEK, ideas(), urgency=4)
        firsts = [s['concept_id'] for s in result['slots'] if s['channel'] == 'instagram'
                  and s['lane'] == 'repurposed_carousel']
        self.assertEqual(firsts[0], 'carousel-' + piece(0)['piece_id'][6:], 'the oldest unamplified piece leads')
        self.assertNotIn('carousel-' + piece(99)['piece_id'][6:], firsts, 'partial pieces wait for unamplified ones')
        for channel in FLOOD_CHANNELS:
            used = [s['concept_id'] for s in result['slots'] if s['channel'] == channel and s['concept_id']]
            self.assertEqual(len(used), len(set(used)), 'no piece or idea twice on ' + channel + ' in a week')

    def test_a_format_already_made_on_a_channel_is_not_made_again(self):
        inv = {'pieces': [piece(0, status='partial', made=(('instagram', 'carousel'),))]}
        result = mix.plan(inv, WEEK, (), urgency=4)
        concept = result['concepts'][0]
        self.assertNotIn({'channel': 'instagram', 'format': 'carousel'}, concept['placements'])
        self.assertIn({'channel': 'tiktok', 'format': 'carousel'}, concept['placements'])

    def test_empty_slots_are_shortfalls_never_filled(self):
        result = mix.plan({'pieces': []}, WEEK, (), urgency=4)
        self.assertEqual(len(result['shortfalls']), 100)
        self.assertTrue(all(s['concept_id'] is None for s in result['slots']))
        self.assertEqual(result['concepts'], [])

    def test_positive_news_needs_a_fresh_primary_source(self):
        bad = [{'idea_id': 'n1', 'lane': 'positive_news', 'idea': 'TEST FIXTURE', 'claim': 'x', 'source_url': None,
                'source_date': None},
               {'idea_id': 'n2', 'lane': 'positive_news', 'idea': 'TEST FIXTURE', 'claim': 'x',
                'source_url': 'https://example.org/old', 'source_date': '2026-10-01'}]
        result = mix.plan(inventory_of(), WEEK, bad, urgency=4)
        self.assertEqual(sorted(r['idea_id'] for r in result['refused_ideas']), ['n1', 'n2'])
        self.assertFalse(any(s['concept_id'] for s in result['slots'] if s['lane'] == 'positive_news'))

    def test_the_plan_is_deterministic(self):
        self.assertEqual(json.dumps(full_plan(), sort_keys=True), json.dumps(full_plan(), sort_keys=True))


class OnePress(unittest.TestCase):
    def test_one_plan_proposal_behind_strategy_lists_every_ready_concept_hash(self):
        result = full_plan()
        item = result['proposal']
        self.assertIsNone(result['proposal_hold'])
        self.assertEqual((item['stage'], item['wall'], item['kind']), ('plan', 'strategy', 'advice'))
        self.assertEqual(item['proposal_id'], 'makeyourmindup:mix:2026-W46')
        ready = [c for c in result['concepts'] if c['ready']]
        self.assertEqual(len(ready), len(result['concepts']))
        for c in ready:
            self.assertIn('Hash ' + c['concept_sha256'], item['exact_payload'])
        self.assertLessEqual(len(item['exact_payload']), 8000)
        self.assertNotIn('\u2014', item['exact_payload'], 'no em dash in his words')
        self.assertIn('LinkedIn stays your click', item['exact_payload'])

    def test_a_concept_without_its_mock_is_not_ready_and_carries_no_hash(self):
        result = mix.plan(inventory_of(), WEEK, ideas(), urgency=4)
        carousel = next(c for c in result['concepts'] if c['lane'] == 'repurposed_carousel')
        self.assertFalse(carousel['ready'])
        self.assertIsNone(carousel['concept_sha256'])
        self.assertIn(carousel['concept_id'] + ' (repurposed carousels)', result['proposal']['exact_payload'])
        self.assertEqual(mix.spec_concepts(result), [], 'only ready concepts reach the spec')

    def test_his_amended_payload_leaves_out_the_concepts_he_deleted(self):
        result = full_plan()
        everything = mix.approved_map(result)
        drop = sorted(everything)[0]
        text = '\n'.join(line for line in result['proposal']['exact_payload'].split('\n')
                         if not line.startswith('- ' + drop + ' '))
        kept = mix.approved_map(result, text)
        self.assertNotIn(drop, kept)
        self.assertEqual(len(kept), len(everything) - 1)

    def test_run_new_mix_carries_the_ready_concepts_into_the_week(self):
        result = full_plan()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mix.json'
            write_json(path, result)
            out = Path(folder) / 'spec.json'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(spec_module.main(['new', '--start', WEEK, '--mix', str(path), '--out', str(out)]), 0)
            spec = json.loads(out.read_text(encoding='utf-8'))
        self.assertEqual(len(spec['concepts']), len(result['concepts']))
        report = spec_module.lint(spec)
        self.assertFalse([e for e in report['errors'] if e['code'].startswith('concept')], report['errors'])
        wrong = copy.deepcopy(result)
        wrong['week_of'] = '2026-11-16'
        with self.assertRaisesRegex(ValueError, 'another week'):
            spec_module.with_mix(spec_module.skeleton(WEEK), wrong)

    def test_the_sunday_report_carries_next_weeks_mix_as_its_plan(self):
        result = full_plan()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            now = '2026-11-08T12:00:00-05:00'
            self.assertEqual(cc_loop.mix_proposal(root, now), (None, None), 'no mix file, no ask')
            write_json(root / '.scratch' / 'mix' / ('plan-' + WEEK + '.json'), result)
            item, hold = cc_loop.mix_proposal(root, now)
            self.assertIsNone(hold)
            self.assertEqual(item['proposal_id'], result['proposal']['proposal_id'])
            report = cc_loop.workspace_report('report', 'makeyourmindup:2026-11-08:report', now, rev='fixture',
                                              root=root)[0]
            self.assertEqual([p['proposal_id'] for p in report['proposals']], [item['proposal_id']])
            self.assertEqual(report['proposals'][0]['stage'], 'plan')
            daily = cc_loop.workspace_report('daily', 'makeyourmindup:2026-11-08:daily', now, rev='fixture', root=root)[0]
            self.assertEqual(daily['proposals'], [], 'only the Sunday report carries the mix')
            broken = dict(result, proposal=None, proposal_hold='over 8000 characters')
            write_json(root / '.scratch' / 'mix' / ('plan-' + WEEK + '.json'), broken)
            item, hold = cc_loop.mix_proposal(root, now)
            self.assertIsNone(item)
            self.assertIn('over 8000', hold['detail'])


class Learning(unittest.TestCase):
    def verdicts(self, folder, lane_results):
        """A spec of concept slots and their verdict files under a synthetic run folder."""
        spec = spec_module.skeleton(WEEK)
        spec['concepts'], spec['slots'] = [], []
        n = 0
        for lane, results in lane_results.items():
            cid = lane.replace('_', '-') + '-c'
            spec['concepts'].append({'concept_id': cid, 'lane': lane, 'idea': 'x', 'claim': 'x', 'source_url': None,
                                     'piece_id': None, 'mock_sha256': [], 'placements': [{'channel': 'x', 'format': 'text'}]})
            for verdict in results:
                sid = 'slot-%d' % n
                n += 1
                spec['slots'].append({'slot_id': sid, 'channel': 'x', 'concept_id': cid})
                write_json(spec_module.run_dir(spec, folder) / 'verdict' / (sid + '.json'), {'verdict': verdict})
        return spec

    def test_verdicts_are_joined_to_concept_and_lane(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = self.verdicts(folder, {'meme': ['works', 'works', 'neutral', 'insufficient'],
                                          'level_up': ['fails', 'fails', 'fails']})
            learned = mix.learn([spec], folder)
        self.assertEqual(learned['lanes']['meme'], {'works': 2, 'neutral': 1, 'fails': 0, 'insufficient': 1})
        self.assertEqual(learned['channels']['x']['fails'], 3)
        self.assertEqual({r['lane'] for r in learned['posts']}, {'meme', 'level_up'})

    def test_the_ratio_moves_one_step_inside_its_bounds_on_judged_posts_only(self):
        cfg = mix.load(ROOT)
        learned = {'lanes': {'meme': {'works': 3, 'neutral': 0, 'fails': 0, 'insufficient': 9},
                             'level_up': {'works': 0, 'neutral': 0, 'fails': 3, 'insufficient': 0},
                             'positive_news': {'works': 1, 'neutral': 0, 'fails': 0, 'insufficient': 20}}}
        weights, moved = mix.weights(cfg, learned)
        self.assertEqual(weights['meme'], 30)
        self.assertEqual(weights['level_up'], 5)
        self.assertEqual(weights['positive_news'], 15, 'one judged post is not enough; insufficient never counts')
        self.assertEqual(set(moved), {'meme', 'level_up'})
        weights, _ = mix.weights(cfg, {'lanes': {'level_up': {'works': 0, 'neutral': 0, 'fails': 9}}})
        cfg['lanes']['level_up']['weight'] = cfg['lanes']['level_up']['min']
        weights, _ = mix.weights(cfg, {'lanes': {'level_up': {'works': 0, 'neutral': 0, 'fails': 9}}})
        self.assertEqual(weights['level_up'], cfg['lanes']['level_up']['min'], 'never under its min')

    def test_the_next_plan_reads_what_was_learned(self):
        learned = {'lanes': {'meme': {'works': 4, 'neutral': 0, 'fails': 0, 'insufficient': 0}}}
        result = full_plan(learned=learned)
        self.assertEqual(result['weights']['meme'], 30)
        self.assertIn('Learned from last week: memes 25 to 30', result['proposal']['exact_payload'])
        self.assertGreater(result['per_channel']['x']['meme'], 6)


if __name__ == '__main__':
    unittest.main()
