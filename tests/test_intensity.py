"""Intensity: the North Star gap and the volume caps it raises. Synthetic roots only.

Ruling (Krish, 2026-10-29): At U3 to U5, engines and Control Center may raise
volume caps up to each repo's existing policy bounds without a signed week
spec. This is volume only: walls unchanged.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine import intensity
from engine.cc_loop import runner_report, workspace_report
from engine.run.measure import state_line
from engine.run.spec import computed, lint

ROOT = Path(__file__).resolve().parents[1]
RECORDS = json.loads((ROOT / 'specs' / 'fixtures' / 'social-records.json').read_text(encoding='utf-8'))
NORTH_STAR = """# North Star (TEST FIXTURE ONLY)

```yaml north-star-metric
metric: "synthetic"
target: 2500
deadline: 2026-12-28
ladder:
  - [2026-10-26, 25]
  - [2026-11-02, 86]
  - [2026-11-09, 162]
```
"""
NOW = '2026-10-29T15:00:00Z'


def synthetic(folder, current=None, as_of=None, urgency=4, reason='not measured yet', week='2026-10-26', target=25):
    root = Path(folder)
    (root / 'docs').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'NORTH_STAR.md').write_text(NORTH_STAR, encoding='utf-8')
    line = state_line(week, target, current, as_of, None, urgency, reason)
    (root / 'NOW.md').write_text('# Now (TEST FIXTURE ONLY)\n\n## Where it is right now\n' + line + '\n', encoding='utf-8')
    for name in ('intensity.json', 'experiments.json', 'channels.json', 'journeys.json'):
        shutil.copy(ROOT / name, root / name)
    return root


def checks():
    return [{'name': n, 'ok': True, 'stdout': '', 'stderr': ''} for n in ('self_test', 'doctor_offline', 'dry_run')]


class Intensity(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = temp.name

    def test_gap_line_reads_x_of_y_urgency_and_shortfall(self):
        gap = intensity.state(synthetic(self.folder, 5, '2026-10-28', 4, '5 of 25; under two fifths'), NOW)
        self.assertEqual((gap['current'], gap['week_target'], gap['urgency']), (5, 25, 4))
        self.assertTrue(intensity.gap_line(gap).startswith('5 of 25, U4, short by 20 ('), intensity.gap_line(gap))
        self.assertNotIn('5 of 25; ', intensity.gap_line(gap), 'the count is said once')

    def test_an_unmeasured_or_other_week_is_u4_and_never_zero(self):
        gap = intensity.state(synthetic(self.folder, 3, '2026-10-27', week='2026-10-26'), '2026-11-03T15:00:00Z')
        self.assertEqual((gap['current'], gap['week_target'], gap['urgency']), (None, 86, 4))
        self.assertTrue(intensity.gap_line(gap).startswith('not measured of 86, U4, short by unknown'))

    def test_on_pace_stays_at_default_caps(self):
        root = synthetic(self.folder, 30, '2026-10-28', 1, "at or above this week's target")
        gap = intensity.state(root, NOW)
        self.assertEqual(gap['urgency'], 1)
        self.assertEqual(intensity.daily_cap({'daily_posts_target': 1}, gap['urgency'], root), 1)
        self.assertEqual(intensity.engagement_taps(gap['urgency'], root), 5)

    def test_u3_and_above_raise_caps_to_the_policy_bounds_only(self):
        root = synthetic(self.folder)
        for level, taps in ((3, 10), (4, 15), (5, 20)):
            for name in ('instagram', 'facebook', 'x', 'threads', 'tiktok', 'youtube'):
                self.assertEqual(intensity.daily_cap({'id': name, 'daily_posts_target': 1}, level, root), 1,
                                 name + ' stays at its policy bound of one a day')
            self.assertEqual(intensity.daily_cap({'id': 'substack-notes', 'daily_posts_target': 1}, level, root), 2,
                             'Substack Notes rises to its ruled two')
            self.assertEqual(intensity.daily_cap({'id': 'substack-notes', 'daily_posts_target': 2}, level, root), 2, 'never above the bound')
            self.assertIsNone(intensity.daily_cap({'id': 'linkedin', 'daily_posts_target': None}, level, root),
                              'a human-only channel stays manual')
            self.assertEqual(intensity.engagement_taps(level, root), taps)
        self.assertLessEqual(max(intensity.bounds(root)['engagement_taps']['by_urgency'].values()), 25,
                             "within Control Center's copy_open bound")

    def test_directive_urgency_can_raise_but_never_lower(self):
        root = synthetic(self.folder, 30, '2026-10-28', 1, "at or above this week's target")
        directive = {'directive': {'north_star': {'intensity': {'urgency': 3}}}}
        self.assertEqual(intensity.state(root, NOW, directive)['urgency'], 3)
        low = synthetic(self.folder)
        self.assertEqual(intensity.state(low, NOW, {'directive': {'north_star': {'intensity': {'urgency': 1}}}})['urgency'], 4)

    def test_no_target_raises_nothing(self):
        gap = intensity.state(synthetic(self.folder), '2026-10-14T12:00:00Z')
        self.assertIsNone(gap['urgency'])
        self.assertFalse(intensity.raised(gap['urgency']))
        self.assertIn('no North Star target', intensity.gap_line(gap))

    def test_spec_lint_caps_follow_urgency(self):
        spec = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        threads = next(s for s in spec['slots'] if s['slot_id'] == 'w45-mon-threads-1')
        second = copy.deepcopy(threads)
        second.update(slot_id='w45-mon-threads-2', due_at='2026-11-02T20:00:00-05:00', experiment_arm=None)
        spec['slots'].append(second)
        codes = lambda level: {e['code'] for e in lint(computed(spec), RECORDS, urgency=level)['errors']} - {'week_target'}
        self.assertEqual(codes(None), {'posts_per_day'})
        self.assertEqual(codes(2), {'posts_per_day'})
        for level in (3, 4, 5):
            self.assertEqual(codes(level), {'posts_per_day'}, 'Threads stays at one a day at U' + str(level))
        self.assertIn('at U4 it takes at most 1 a day', ' '.join(
            e['message'] for e in lint(computed(spec), RECORDS, urgency=4)['errors'] if e['code'] == 'posts_per_day'))

    def test_reports_lead_with_the_gap_line(self):
        root = synthetic(self.folder, 0, '2026-10-27', 4, '0 of 25; under two fifths')
        runner = runner_report(root, 'r1', NOW, checks(), 'synthetic', True, 'fixture', sent={})[0]
        self.assertTrue(runner['activity'][0]['line'].startswith('0 of 25, U4, short by 25'))
        work = workspace_report('radar', 'r1', NOW, rev='fixture', root=root)[0]
        self.assertTrue(work['activity'][0]['line'].startswith('0 of 25, U4, short by 25'))
        self.assertIn('15 engagement taps a day', work['activity'][1]['line'])
        self.assertIn('walls, spend and approvals unchanged', work['activity'][1]['line'])


if __name__ == '__main__':
    unittest.main()
