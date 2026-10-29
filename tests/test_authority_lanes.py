"""Krish's 27 Oct 2026 rulings as data: invariants/authority.json and lanes.json (R101 to R103).

Synthetic fixtures only. Every autonomous action must be provably inside his authority. The lanes are
L0 code, L2 his eyes and L3 his hands: there are no Claude routines (Krish, 29 Oct 2026).
"""
import copy
import datetime
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.run.invariants import (HANDS, LANE_JOBS, ROOT, check_authority, check_lanes, load_authority,
                                   load_lanes, may_post_alone, needs_preview, posting_lane, preview_end)


def copy_root(folder, *names):
    root = Path(folder)
    for name in names:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(str(source), str(root / name))
        else:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source), str(root / name))
    return root


def write(root, name, data):
    (Path(root) / name).write_text(json.dumps(data, indent=2), encoding='utf-8')


class AuthorityTests(unittest.TestCase):
    def test_authority_encodes_the_27_october_standing_approval(self):
        data = load_authority()
        self.assertEqual(check_authority(data), [])
        self.assertEqual(data['source_file'], 'CHANGES.md')
        self.assertEqual((data['first_signed_week'], data['show_before_post_until']), ('2026-W45', '2026-11-29'))
        self.assertEqual(preview_end('2026-W45'), datetime.date(2026, 11, 29))  # W45 to W48, Monday weeks
        self.assertEqual(data['publish_board']['includes'], ['article', 'assets', 'video-recordings'])
        derivative = {e['class']: e['formats'] for e in data['derivative_formats']}
        for name in ('quote-card', 'receipt-card', 'note-quote', 'post-quote', 'story-from-assets', 'video-cut',
                     'article-reshare'):
            self.assertIn(name, derivative)
        self.assertEqual(derivative['video-cut'], ['short-video'])
        self.assertIn('note', derivative['note-quote'])
        new = {e['class'] for e in data['new_formats_need_eyes']}
        self.assertTrue({'carousel', 'meme', 'opinion', 'reactive'} <= new)
        self.assertEqual(data['any_other_class'], 'needs_eyes')
        self.assertEqual({e['id'] for e in data['krish_hands']}, set(HANDS))
        quote = 'you should be able to just go for gold everywhere else'
        self.assertIn(quote, ' '.join((ROOT / 'CHANGES.md').read_text(encoding='utf-8').split()))

    def test_authority_refuses_a_malformed_register(self):
        good = json.loads((ROOT / 'invariants' / 'authority.json').read_text(encoding='utf-8'))
        broken = []
        for change, message in (
                (lambda d: d.update(extra=True), 'needs exactly'),
                (lambda d: d.update(show_before_post_until='2026-12-31'), 'four weeks'),
                (lambda d: d.update(first_signed_week='W45'), '2026-W45'),
                (lambda d: d['publish_board'].update(includes=['article']), 'publish board'),
                (lambda d: d['new_formats_need_eyes'].append(dict(d['derivative_formats'][0])), 'once'),
                (lambda d: d.update(new_formats_need_eyes=[e for e in d['new_formats_need_eyes']
                                                           if e['class'] != 'carousel']), 'always need his eyes'),
                (lambda d: d.update(any_other_class='derivative'), 'needs his eyes'),
                (lambda d: d.update(krish_hands=d['krish_hands'][1:]), 'once each'),
                (lambda d: d['krish_hands'][0].update(channels=[]), 'LinkedIn')):
            data = copy.deepcopy(good)
            change(data)
            broken.append((data, message))
        with tempfile.TemporaryDirectory() as folder:
            for data, message in broken:
                root = Path(tempfile.mkdtemp(dir=folder))
                (root / 'invariants').mkdir()
                write(root / 'invariants', 'authority.json', good)
                self.assertEqual(load_authority(root)['kind'], 'authority')
                write(root / 'invariants', 'authority.json', data)
                with self.assertRaisesRegex(ValueError, message):
                    load_authority(root)

    def test_derivatives_wait_for_board_and_preview_then_post_alone(self):
        data = load_authority()
        self.assertEqual(posting_lane(data, 'receipt-card', 'x', 'receipt-card'), 'L0_code')  # release.yml, alone
        self.assertTrue(needs_preview(data, '2026-11-29'))
        self.assertFalse(needs_preview(data, datetime.date(2026, 11, 30)))
        cases = [(dict(day='2026-11-10'), (False, 'publish_board_not_approved')),
                 (dict(day='2026-11-10', board_approved=True), (False, 'preview_packet_needed')),
                 (dict(day='2026-11-29', board_approved=True), (False, 'preview_packet_needed')),
                 (dict(day='2026-11-10', board_approved=True, preview_approved=True), (True, 'derivative')),
                 (dict(day='2026-11-30', board_approved=True), (True, 'derivative')),
                 (dict(day='2026-11-30'), (False, 'publish_board_not_approved'))]
        for kwargs, expected in cases:
            day = kwargs.pop('day')
            # Instagram, YouTube and TikTok are named in the ruling: derivatives go there too.
            for channel, fmt, name in (('instagram', 'story-frame', 'story-from-assets'),
                                       ('youtube', 'short-video', 'video-cut'), ('tiktok', 'short-video', 'video-cut'),
                                       ('substack-notes', 'note', 'note-quote')):
                self.assertEqual(may_post_alone(data, name, channel, fmt, day, **kwargs), expected, (channel, day))

    def test_new_formats_and_unlisted_classes_need_eyes(self):
        data = load_authority()
        for name, channel, fmt in (('carousel', 'instagram', 'carousel'), ('meme', 'tiktok', 'meme'),
                                   ('opinion', 'threads', 'text'), ('reactive', 'x', 'text'),
                                   ('scorecard', 'threads', 'scorecard'), ('poll', 'x', 'poll'),
                                   ('never-heard-of-it', 'x', 'text'),
                                   ('receipt-card', 'x', 'meme')):  # a derivative class on the wrong format
            self.assertEqual(posting_lane(data, name, channel, fmt), 'L2_eyes', name)
            self.assertEqual(may_post_alone(data, name, channel, fmt, '2026-12-15', True, True),
                             (False, 'needs_eyes'), name)
            self.assertEqual(may_post_alone(data, name, channel, fmt, '2026-12-15', item_approved=True),
                             (True, 'item_approved'), name)

    def test_linkedin_is_never_posted_alone(self):
        data = load_authority()
        for name in ('note-quote', 'carousel', 'post-quote', 'linkedin-draft'):
            self.assertEqual(posting_lane(data, name, 'linkedin', 'text'), 'L3_hands')
            self.assertEqual(may_post_alone(data, name, 'linkedin', 'text', '2027-01-04', True, True, True),
                             (False, 'krish_hands'))

    def test_authority_formats_and_hands_exist_in_the_social_records(self):
        data = load_authority()
        data['derivative_formats'][0]['formats'].append('hologram')
        data['krish_hands'][0]['channels'] = ['myspace']
        errors = check_authority(data)
        self.assertIn('derivative_formats.quote-card: unknown format hologram', errors)
        self.assertIn('krish_hands: unknown channel myspace', errors)
        self.assertIn('linkedin is human_publish_only but not in krish_hands', errors)


class LanesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = copy_root(temp.name, 'lanes.json', 'automations.json', 'jobs', '.github')
        self.lanes = load_lanes()
        self.authority = load_authority()

    def errors(self, lanes=None):
        return check_lanes(lanes or self.lanes, self.authority, self.root)

    def test_every_workflow_and_job_is_in_one_lane(self):
        self.assertEqual(check_lanes(self.lanes, self.authority), [])
        self.assertEqual(self.errors(), [])
        by_id = {job['id']: job for job in self.lanes['jobs']}
        for lane, names in LANE_JOBS.items():
            for name in names:
                self.assertEqual(by_id[name]['lane'], lane, name)
        workflows = {p.name for p in (ROOT / '.github' / 'workflows').glob('*.yml')}
        declared = {job['workflow'] for job in self.lanes['jobs'] if job['workflow']}
        self.assertTrue(workflows <= declared)
        self.assertTrue({'release.yml', 'measure.yml'} <= declared)  # being added by other items
        config = json.loads((ROOT / 'automations.json').read_text(encoding='utf-8'))['automations']
        mapped = {e['name']: e for e in self.lanes['automations']}
        for entry in config:
            self.assertEqual(mapped[entry['name']]['status'], 'kept-until-W46')
            self.assertIn(entry['job'], mapped[entry['name']]['jobs'])
        self.assertEqual(tuple(self.lanes['lanes']), ('L0_code', 'L2_eyes', 'L3_hands'))
        self.assertTrue(all(lane['model'] is False for lane in self.lanes['lanes'].values()))

    def test_there_are_no_claude_routines(self):
        # Krish, 29 Oct 2026: "I want zero Claude routines. No Claude schedules of any kind in this architecture".
        self.assertFalse((ROOT / 'routines').exists())
        by_id = {job['id']: job for job in self.lanes['jobs']}
        for name in ('make', 'plan', 'watch'):
            self.assertNotIn(name, by_id)
        self.assertEqual({job['workflow'] for job in self.lanes['jobs'] if job['lane'] == 'L0_code'},
                         {p.name for p in (ROOT / '.github' / 'workflows').glob('*.yml')})
        self.assertTrue(all(job['workflow'] is None for job in self.lanes['jobs'] if job['lane'] != 'L0_code'))
        (self.root / 'routines').mkdir()
        (self.root / 'routines' / 'make.md').write_text('# synthetic\n', encoding='utf-8')
        self.assertTrue(any(e.startswith('routines/ exists') for e in self.errors()))

    def test_an_unlisted_workflow_fails_but_a_declared_missing_one_passes(self):
        folder = self.root / '.github' / 'workflows'
        for name in ('release.yml', 'measure.yml', 'keys.yml'):
            if (folder / name).exists():
                (folder / name).unlink()
        self.assertEqual(self.errors(), [], 'a declared workflow another item is still building may be missing')
        (folder / 'release.yml').write_text('name: release\n', encoding='utf-8')
        self.assertEqual(self.errors(), [])
        (folder / 'surprise.yml').write_text('name: surprise\n', encoding='utf-8')
        self.assertEqual(self.errors(), ['workflow not in lanes.json: surprise.yml'])

    def test_every_job_file_and_automation_is_named_exactly_once(self):
        (self.root / 'jobs' / 'brand-new.md').write_text('# synthetic\n', encoding='utf-8')
        self.assertIn('job file in no automation: jobs/brand-new.md', self.errors())
        lanes = copy.deepcopy(self.lanes)
        lanes['automations'][0]['jobs'].append('jobs/radar.md')
        self.assertIn('job file named more than once: jobs/radar.md', self.errors(lanes))
        lanes = copy.deepcopy(self.lanes)
        lanes['automations'] = lanes['automations'][1:]
        self.assertIn('lanes.json automations must name every automations.json entry once', self.errors(lanes))
        lanes = copy.deepcopy(self.lanes)
        lanes['jobs'].append(dict(next(j for j in lanes['jobs'] if j['id'] == 'publish-board')))
        self.assertIn('named more than once: publish-board', self.errors(lanes))
        lanes = copy.deepcopy(self.lanes)
        lanes['jobs'] = [j for j in lanes['jobs'] if j['id'] != 'handoff']
        self.assertIn('missing job handoff', self.errors(lanes))

    def test_no_l0_job_holds_his_hands_or_his_eyes(self):
        for job_id, action, message in (('handoff', 'linkedin-posting', 'holds his hands'),
                                        ('release', 'plan-purchase', 'holds his hands'),
                                        ('measure', 'account-connection', 'holds his hands'),
                                        ('control-center', 'sign-week', 'holds his eyes'),
                                        ('handoff', 'approve-new-format-item', 'holds his eyes')):
            lanes = copy.deepcopy(self.lanes)
            next(j for j in lanes['jobs'] if j['id'] == job_id)['actions'].append(action)
            self.assertTrue(any(message in e and e.startswith(job_id) for e in self.errors(lanes)), action)
        lanes = copy.deepcopy(self.lanes)
        next(j for j in lanes['jobs'] if j['id'] == 'one-time-setup')['actions'] = ['credential-creation']
        self.assertIn('no L3 job holds account-connection', self.errors(lanes))

    def test_the_engine_key_lives_only_on_the_github_runner(self):
        # Krish, 27 Oct: "Surely we can have a less fragile way of doing this than a session engine token".
        text = (ROOT / '.github' / 'workflows' / 'control-center.yml').read_text(encoding='utf-8')
        self.assertIn('secrets.CONTROL_CENTER_ENGINE_TOKEN', text)
        by_id = {job['id']: job for job in self.lanes['jobs']}
        self.assertIn('CONTROL_CENTER_ENGINE_TOKEN', by_id['control-center']['secrets'])
        self.assertEqual([j['id'] for j in self.lanes['jobs'] if j['secrets'] and j['lane'] != 'L0_code'], [])
        check = self.root / '.github' / 'workflows' / 'check.yml'
        check.write_text(check.read_text(encoding='utf-8') + '\n# ${{ secrets.CONTROL_CENTER_ENGINE_TOKEN }}\n',
                         encoding='utf-8')
        self.assertEqual(self.errors(), ['check.yml reads CONTROL_CENTER_ENGINE_TOKEN but job check does not declare it'])
        lanes = copy.deepcopy(self.lanes)
        next(j for j in lanes['jobs'] if j['id'] == 'publish-board')['secrets'] = ['CONTROL_CENTER_ENGINE_TOKEN']
        self.assertIn('publish-board: only L0 code on the GitHub runner holds a key',
                      check_lanes(lanes, self.authority))

    def test_lanes_register_refuses_a_bad_shape(self):
        good = json.loads((ROOT / 'lanes.json').read_text(encoding='utf-8'))
        changes = ((lambda d: d['jobs'][0].update(workflow=None), 'names its workflow'),
                   (lambda d: d['jobs'][6].update(workflow='publish-board.yml'), 'names its workflow'),
                   (lambda d: d['jobs'][0].update(never=[]), 'never do'),
                   (lambda d: d['jobs'][0].update(lane='L5_magic'), 'lane is one of'),
                   (lambda d: d['lanes']['L0_code'].update(model=True), 'no lane runs a model'),
                   (lambda d: d['lanes'].update(L1_judgement={'who': 'Claude routines', 'runs_on': 'a schedule',
                                                              'model': True}), 'lanes are'),
                   (lambda d: d['automations'][0].update(lane='L1_judgement'), 'needs exactly'),
                   (lambda d: d['automations'][0].update(status='retired'), 'kept-until-W46'),
                   (lambda d: d.update(extra=1), 'needs exactly'))
        with tempfile.TemporaryDirectory() as folder:
            for change, message in changes:
                data = copy.deepcopy(good)
                change(data)
                root = Path(tempfile.mkdtemp(dir=folder))
                write(root, 'lanes.json', data)
                with self.assertRaisesRegex(ValueError, message):
                    load_lanes(root)


if __name__ == '__main__':
    unittest.main()
