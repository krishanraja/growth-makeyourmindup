"""Release Gate regression tests: past Buffer failures encoded as code.

Synthetic fixtures only. Nothing here reaches Buffer or any network.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'release'
_spec = importlib.util.spec_from_file_location('growth_release_under_test', ROOT / 'engine' / 'run' / 'release.py')
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)

NOW = '2026-11-01T12:00:00-05:00'


def load(name):
    return json.loads((FIX / (name + '.json')).read_text(encoding='utf-8'))


def resign(slot, decision=None):
    slot['payload_sha256'] = release.slot_digest(slot)
    if decision is not None:
        decision['slots'][slot['slot_id']] = slot['payload_sha256']
    return slot


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.spec = load('spec')
        self.decision = load('decision')
        self.channels = load('channels')
        self.slots = {s['slot_id']: s for s in self.spec['slots']}
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for n in range(1, 6):
            (self.dir / ('frame-%d.png' % n)).write_bytes(('synthetic release fixture frame %d\n' % n).encode())

    def tearDown(self):
        self.tmp.cleanup()

    def paths(self, spec=None):
        spec = spec or self.spec
        return {s['slot_id']: [self.dir / a['name'] for a in s['assets']] for s in spec['slots']}

    def plan(self, spec=None, decision=None, ledger=None):
        spec = spec or self.spec
        return release.release_plan(spec, decision or self.decision, ledger, self.paths(spec), self.channels, NOW)

    def by_slot(self, result):
        return {c['slot_id']: c for c in result['calls']}

    def test_fixture_plan_releases_every_signed_slot_once(self):
        result = self.plan()
        self.assertEqual(result['holds'], [])
        self.assertEqual(set(self.by_slot(result)), set(self.slots))
        for call in result['calls']:
            self.assertEqual(call['server'], 'Buffer')
            self.assertEqual(release.argument_errors(call, self.slots[call['slot_id']]), [])
        notes = self.by_slot(result)['notes-1']
        self.assertEqual(notes['tool'], 'create_post')
        self.assertEqual(notes['arguments'], {
            'channelId': 'cccccccccccccccccccccc01', 'text': self.slots['notes-1']['words'], 'assets': [],
            'mode': 'customScheduled', 'schedulingType': 'automatic', 'saveToDraft': False,
            'dueAt': '2026-11-02T08:30:00-05:00'})

    def test_draft_save_sets_saveToDraft_without_dueAt(self):
        slot = resign(copy.deepcopy(self.slots['threads-1']))
        slot['due_at'] = None
        resign(slot)
        args = release.call_arguments(slot, self.channels['threads'], NOW)['arguments']
        self.assertIs(args['saveToDraft'], True)
        self.assertNotIn('dueAt', args)
        self.assertNotIn('mode', args)
        self.assertEqual(args['schedulingType'], 'automatic')
        bad = {'tool': 'create_post', 'arguments': dict(args, dueAt='2026-11-02T12:00:00-05:00')}
        self.assertIn('a draft save carries no dueAt and no mode', release.argument_errors(bad, slot))
        queue = {'tool': 'create_post', 'arguments': {k: v for k, v in args.items() if k != 'saveToDraft'}}
        self.assertTrue(any('never rely on the default queue' in e for e in release.argument_errors(queue, slot)))

    def test_edit_sends_complete_payload(self):
        call = self.by_slot(self.plan())['ig-story-1']
        self.assertEqual(call['tool'], 'edit_post')
        args = call['arguments']
        self.assertEqual(args['postId'], 'aaaaaaaaaaaaaaaaaaaaaa01')
        self.assertEqual(args['text'], self.slots['ig-story-1']['words'])
        self.assertEqual(args['assets'], [{'image': {'url': 'https://example.org/synthetic/frame-1.png'}}])
        self.assertEqual(args['metadata'], {'instagram': {'type': 'story', 'shouldShareToFeed': False}})
        self.assertEqual((args['mode'], args['schedulingType'], args['saveToDraft'], args['dueAt']),
                         ('customScheduled', 'automatic', False, '2026-11-02T18:00:00-05:00'))
        scheduling_only = {'tool': 'edit_post', 'arguments': {
            'postId': args['postId'], 'mode': 'customScheduled', 'saveToDraft': False, 'dueAt': args['dueAt']}}
        self.assertIn('an edit must send the complete payload, never a scheduling-only edit',
                      release.argument_errors(scheduling_only, self.slots['ig-story-1']))

    def test_tiktok_photo_never_sets_ai_flag(self):
        slot = self.slots['tiktok-photo-1']
        args = self.by_slot(self.plan())['tiktok-photo-1']['arguments']
        self.assertNotIn('isAiGenerated', json.dumps(args))
        self.assertEqual(len(args['assets']), 2)
        flagged = {'tool': 'create_post', 'arguments': dict(args, metadata={'tiktok': {'isAiGenerated': True}})}
        self.assertIn('TikTok photo posts never set the AI-generated flag', release.argument_errors(flagged, slot))

    def test_preview_clear_uses_mutation_not_null(self):
        slot = self.slots['linkedin-1']
        hold = release.preview_clear_hold(slot)
        self.assertEqual(hold['hold'], 'preview_clear_needs_introspected_mutation')
        self.assertEqual(hold['route']['tool'], 'execute_mutation')
        self.assertEqual(hold['route']['input_type'], 'EditPostInput!')
        self.assertIn('editPost', hold['route']['mutation'])
        self.assertNotIn('arguments', hold)
        args = self.by_slot(self.plan())['linkedin-1']['arguments']
        self.assertNotIn('linkAttachment', json.dumps(args))
        nulled = {'tool': 'edit_post', 'arguments': dict(args, metadata={'linkedin': {'linkAttachment': None}})}
        self.assertTrue(any('linkAttachment null' in e for e in release.argument_errors(nulled, slot)))

    def test_scheduled_is_not_sent(self):
        slot = self.slots['threads-1']
        scheduled = load('readback-queued')['threads-1']
        evidence = release.check_readback(slot, scheduled, 'queued')
        self.assertEqual(evidence['status'], 'scheduled')
        self.assertIs(evidence['published'], False)
        self.assertIsNone(evidence['native_url'])
        scheduled['externalLink'] = 'https://www.threads.com/@synthetic/post/SYNTHETIC1'
        with self.assertRaisesRegex(ValueError, 'scheduled is never sent'):
            release.check_readback(slot, scheduled, 'live')
        live = release.check_readback(slot, load('readback-live')['threads-1'], 'live')
        self.assertIs(live['published'], True)

    def test_live_needs_native_url_per_destination(self):
        native = {'substack-notes': 'https://substack.com/@synthetic/note/c-1',
                  'threads': 'https://www.threads.com/@synthetic/post/S1',
                  'x': 'https://x.com/synthetic/status/1', 'instagram': 'https://www.instagram.com/p/S1/',
                  'facebook': 'https://www.facebook.com/synthetic/posts/1',
                  'tiktok': 'https://www.tiktok.com/@synthetic/photo/1',
                  'youtube': 'https://www.youtube.com/shorts/S1', 'linkedin': 'https://www.linkedin.com/feed/update/1'}
        self.assertEqual(set(native), set(release.CHANNELS))
        for channel, url in native.items():
            self.assertTrue(release.native_host(channel, url), channel)
            self.assertFalse(release.native_host(channel, url.replace('https://', 'http://')), channel)
            others = [u for c, u in native.items() if c != channel]
            self.assertFalse(any(release.native_host(channel, u) for u in others), channel)
        self.assertFalse(release.native_host('tiktok', 'https://vm.tiktok.com/S1'))
        self.assertFalse(release.native_host('instagram', 'https://instagram.com.example.org/p/S1/'))
        slot = self.slots['threads-1']
        post = load('readback-live')['threads-1']
        for bad in (None, 'https://x.com/synthetic/status/1', 'http://www.threads.com/@synthetic/post/S1'):
            post['externalLink'] = bad
            with self.assertRaisesRegex(ValueError, 'native URL'):
                release.check_readback(slot, post, 'live')

    def test_link_sticker_never_claimed_automatic(self):
        slot = copy.deepcopy(self.slots['ig-story-1'])
        slot['link_placement'] = 'link_sticker'
        resign(slot)
        with self.assertRaisesRegex(ValueError, 'link sticker is never set or claimed automatic'):
            release.check_slot(slot)
        call = self.by_slot(self.plan())['ig-story-1']
        self.assertNotIn('link', call['arguments']['metadata']['instagram'])
        self.assertNotIn('stickerFields', call['arguments']['metadata']['instagram'])
        stickered = copy.deepcopy(call)
        stickered['arguments']['metadata']['instagram']['link'] = 'https://example.org/synthetic'
        self.assertIn('an Instagram Story link sticker is never set or claimed automatic',
                      release.argument_errors(stickered, self.slots['ig-story-1']))
        evidence = release.check_readback(self.slots['ig-story-1'], load('readback-live')['ig-story-1'], 'live')
        self.assertEqual(evidence['link_sticker'], 'not_set_not_claimed')

    def test_story_one_frame_per_post_dedupe_by_media_url(self):
        slot = copy.deepcopy(self.slots['ig-story-1'])
        slot['assets'].append(copy.deepcopy(self.slots['x-1']['assets'][0]))
        resign(slot)
        with self.assertRaisesRegex(ValueError, 'one frame per post'):
            release.check_slot(slot)
        post = load('readback-live')['ig-story-1']
        frame = post['assets'][0]
        post['assets'] = [frame, dict(frame, thumbnail='https://buffer.example.org/synthetic/thumb.png')]
        self.assertEqual(release.story_frame(post), frame['source'])
        release.check_readback(self.slots['ig-story-1'], post, 'live')
        post['assets'] = [frame, dict(frame, source='https://buffer.example.org/synthetic/other.png')]
        with self.assertRaisesRegex(ValueError, 'exactly one frame'):
            release.check_readback(self.slots['ig-story-1'], post, 'live')
        one = {'assets': [{'source': 'https://buffer.example.org/synthetic/a.png'}]}
        two = {'assets': [{'source': 'https://buffer.example.org/synthetic/b.png'}]}
        self.assertEqual(len(release.story_sequence([one, two])), 2)
        with self.assertRaisesRegex(ValueError, 'repeats an earlier frame'):
            release.story_sequence([one, two, copy.deepcopy(one)])

    def test_imported_posts_not_engine_publications(self):
        ledger = self.plan()['ledger']
        ledger['released']['threads-1']['post_id'] = 'bbbbbbbbbbbbbbbbbbbbbb01'
        live = load('readback-live')
        imported = dict(live['threads-1'], id='dddddddddddddddddddddd01', via='network')
        other = dict(live['threads-1'], id='dddddddddddddddddddddd02', via='buffer')
        counted = release.engine_publications([live['threads-1'], imported, other, live['ig-story-1']], ledger)
        self.assertEqual([p['id'] for p in counted], ['bbbbbbbbbbbbbbbbbbbbbb01', 'aaaaaaaaaaaaaaaaaaaaaa01'])
        with self.assertRaisesRegex(ValueError, 'imported from the network'):
            release.check_readback(self.slots['threads-1'], imported, 'live', ledger)
        with self.assertRaisesRegex(ValueError, 'not the one the engine released'):
            release.check_readback(self.slots['threads-1'], other, 'live', ledger)
        with self.assertRaisesRegex(ValueError, 'absent from the release ledger'):
            release.check_readback(self.slots['threads-1'], live['threads-1'], 'live',
                                   {'run_id': self.spec['run_id'], 'released': {}})

    def test_release_refuses_changed_asset_bytes(self):
        slot = self.slots['tiktok-photo-1']
        paths = self.paths()['tiktok-photo-1']
        self.assertTrue(release.verify_asset_bytes(slot, paths))
        paths[1].write_bytes(b'synthetic release fixture frame 3?')
        with self.assertRaisesRegex(ValueError, 'asset bytes differ from the signed slot'):
            release.verify_asset_bytes(slot, paths)
        with self.assertRaisesRegex(ValueError, 'expected 2 asset files'):
            release.verify_asset_bytes(slot, paths[:1])
        result = self.plan()
        self.assertNotIn('tiktok-photo-1', self.by_slot(result))
        self.assertNotIn('tiktok-photo-1', result['ledger']['released'])
        self.assertIn('tiktok-photo-1', [h['slot_id'] for h in result['holds']])
        unchecked = release.release_plan(self.spec, self.decision, None, None, self.channels, NOW)
        self.assertEqual({c['slot_id'] for c in unchecked['calls']}, {'notes-1', 'threads-1'})

    def test_release_once_per_slot(self):
        first = self.plan()
        self.assertEqual(len(first['calls']), len(self.slots))
        second = self.plan(ledger=first['ledger'])
        self.assertEqual(second['calls'], [])
        self.assertEqual({h['hold'] for h in second['holds']}, {'already_released_once'})
        spec = copy.deepcopy(self.spec)
        changed = spec['slots'][0]
        changed['words'] += ' Amended.'
        decision = copy.deepcopy(self.decision)
        resign(changed, decision)
        third = self.plan(spec, decision, first['ledger'])
        self.assertEqual(third['calls'], [])
        self.assertIn({'slot_id': 'notes-1', 'hold': 'released_earlier_with_another_payload'}, third['holds'])

    def test_release_refuses_unsigned_or_mismatched_slot(self):
        spec = copy.deepcopy(self.spec)
        decision = copy.deepcopy(self.decision)
        del decision['slots']['notes-1']
        spec['slots'][1]['words'] += ' Edited after signing.'
        resign(spec['slots'][1])
        result = self.plan(spec, decision)
        calls = self.by_slot(result)
        self.assertNotIn('notes-1', calls)
        self.assertNotIn('threads-1', calls)
        holds = {h['slot_id']: h['hold'] for h in result['holds']}
        self.assertEqual(holds['notes-1'], 'unsigned_or_changed_since_signing')
        self.assertEqual(holds['threads-1'], 'payload_does_not_match_signed_digest')
        tampered = copy.deepcopy(self.spec)
        tampered['slots'][0]['words'] += ' Hand edit.'
        with self.assertRaisesRegex(ValueError, 'not this slot\'s computed digest'):
            self.plan(tampered)
        for change in ({'decision': 'declined'}, {'run_id': 'synthetic:other'}, {'proposal_id': 'synthetic-other'}):
            with self.assertRaises(ValueError):
                self.plan(decision=dict(self.decision, **change))

    def test_linkedin_release_is_draft_only(self):
        call = self.by_slot(self.plan())['linkedin-1']
        args = call['arguments']
        self.assertEqual(call['tool'], 'edit_post')
        self.assertIs(args['saveToDraft'], True)
        for key in ('dueAt', 'mode'):
            self.assertNotIn(key, args)
        slot = copy.deepcopy(self.slots['linkedin-1'])
        slot['publish_mode'] = 'engine'
        resign(slot)
        with self.assertRaisesRegex(ValueError, 'never released by the engine'):
            release.check_slot(slot)
        scheduled = {'tool': 'edit_post', 'arguments': dict(args, saveToDraft=False, mode='customScheduled',
                                                            dueAt=self.slots['linkedin-1']['due_at'])}
        self.assertIn('a krish_click slot only ever gets an unscheduled draft',
                      release.argument_errors(scheduled, self.slots['linkedin-1']))

    def test_cli_writes_ledger_and_evidence_only_under_scratch(self):
        root = self.dir / 'repo'
        root.mkdir()
        argv = ['release', 'plan', str(FIX / 'spec.json'), '--decision', str(FIX / 'decision.json'),
                '--assets', str(self.dir), '--channels', str(FIX / 'channels.json'), '--now', NOW]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(release.main(argv, root), 0)
        self.assertEqual(len(json.loads(out.getvalue())), len(self.slots))
        run_dir = root / '.scratch' / 'runs' / 'synthetic_2026-W45_week'
        self.assertTrue((run_dir / 'ledger.json').is_file())
        for stage in ('queued', 'live'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = release.main(['release', 'check', str(FIX / 'spec.json'), '--readback',
                                     str(FIX / ('readback-' + stage + '.json')), '--stage', stage, '--now', NOW], root)
            self.assertEqual(code, 0, out.getvalue())
            self.assertTrue((run_dir / stage / 'threads-1.json').is_file())
        ledger = json.loads((run_dir / 'ledger.json').read_text(encoding='utf-8'))
        self.assertEqual(ledger['released']['threads-1']['post_id'], 'bbbbbbbbbbbbbbbbbbbbbb01')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(release.main(argv[:-2] + ['--ledger', str(self.dir / 'outside.json')], root), 1)
            empty = self.dir / 'empty'
            empty.mkdir()
            self.assertEqual(release.main(['check', str(FIX / 'spec.json'), '--readback',
                                           str(FIX / 'readback-live.json'), '--stage', 'live'], empty), 1)
        self.assertFalse((self.dir / 'outside.json').exists())


if __name__ == '__main__':
    unittest.main()
