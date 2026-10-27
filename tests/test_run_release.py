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
THREADS_POST = 'bbbbbbbbbbbbbbbbbbbbbb01'


def load(name):
    return json.loads((FIX / (name + '.json')).read_text(encoding='utf-8'))


def resign(slot, decision=None, spec=None):
    slot['payload_sha256'] = release.slot_digest(slot)
    if decision is not None:
        decision['slots'][slot['slot_id']] = slot['payload_sha256']
        if spec is not None:
            sign(spec, decision)
    return slot


def sign(spec, decision):
    spec['signature']['decision_digest'] = release.decision_digest(decision)
    return spec


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.spec = load('spec')
        self.decision = load('decision')
        self.channels = load('channels')
        self.targets = load('targets')
        self.slots = {s['slot_id']: s for s in self.spec['slots']}
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for n in range(1, 6):
            (self.dir / ('frame-' + str(n) + '.png')).write_bytes(('synthetic release fixture frame ' + str(n) + '\n').encode())

    def tearDown(self):
        self.tmp.cleanup()

    def paths(self, spec=None):
        spec = spec or self.spec
        return {s['slot_id']: [self.dir / a['name'] for a in s['assets']] for s in spec['slots']}

    def plan(self, spec=None, decision=None, ledger=None, targets=None, channels=None):
        spec = spec or self.spec
        return release.release_plan(spec, decision or self.decision, ledger, self.paths(spec),
                                    self.channels if channels is None else channels, NOW,
                                    self.targets if targets is None else targets)

    def channel(self, service):
        return [c for c in self.channels if c['service'] == service][0]

    def ledger(self):
        """A ledger as it stands after plan and a queued check of threads-1."""
        ledger = self.plan()['ledger']
        ledger['released']['threads-1']['post_id'] = THREADS_POST
        return ledger

    def by_slot(self, result):
        return {c['slot_id']: c for c in result['calls']}

    def holds(self, result):
        return {h['slot_id']: h['hold'] for h in result['holds']}

    def test_fixture_plan_releases_every_signed_slot_once(self):
        result = self.plan()
        self.assertEqual(result['holds'], [])
        self.assertEqual(set(self.by_slot(result)), set(self.slots))
        for call in result['calls']:
            self.assertEqual(call['server'], 'Buffer')
            self.assertEqual(release.argument_errors(call, self.slots[call['slot_id']]), [])
        notes = self.by_slot(result)['notes-1']
        self.assertEqual(notes['tool'], 'create_post')
        self.assertEqual((notes['service'], notes['channel_id']), ('substack', 'cccccccccccccccccccccc01'))
        self.assertEqual(notes['arguments'], {
            'channelId': 'cccccccccccccccccccccc01', 'text': self.slots['notes-1']['words'], 'assets': [],
            'mode': 'customScheduled', 'schedulingType': 'automatic', 'saveToDraft': False,
            'dueAt': '2026-11-02T08:30:00-05:00'})
        self.assertEqual(result['ledger']['released']['x-1']['channel_id'], 'cccccccccccccccccccccc06')

    def test_draft_save_sets_saveToDraft_without_dueAt(self):
        slot = resign(copy.deepcopy(self.slots['threads-1']))
        slot['due_at'] = None
        resign(slot)
        args = release.call_arguments(slot, self.channel('threads'), NOW)['arguments']
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
        self.assertEqual(args['assets'], [{'image': {'url': 'https://example.org/synthetic/frame-1.png',
                                                     'metadata': {'altText': 'Synthetic alt text for frame one.'}}}])
        self.assertEqual(args['metadata'], {'instagram': {'type': 'story', 'shouldShareToFeed': False,
                                                          'isAiGenerated': True}})
        self.assertEqual((args['mode'], args['schedulingType'], args['saveToDraft'], args['dueAt']),
                         ('customScheduled', 'automatic', False, '2026-11-02T18:00:00-05:00'))
        scheduling_only = {'tool': 'edit_post', 'arguments': {
            'postId': args['postId'], 'mode': 'customScheduled', 'saveToDraft': False, 'dueAt': args['dueAt']}}
        self.assertIn('an edit must send the complete payload, never a scheduling-only edit',
                      release.argument_errors(scheduling_only, self.slots['ig-story-1']))

    def test_edit_carries_alt_text_and_ai_flag_forward(self):
        targets = copy.deepcopy(self.targets)
        targets['x-1']['metadata']['isAiGenerated'] = True
        targets['x-1']['assets'][0]['image']['altText'] = 'Synthetic alt text for frame five.'
        args = self.by_slot(self.plan(targets=targets))['x-1']['arguments']
        self.assertEqual(args['assets'][0]['image']['metadata'], {'altText': 'Synthetic alt text for frame five.'})
        self.assertEqual(args['metadata'], {'twitter': {'isAiGenerated': True}})
        moved = copy.deepcopy(self.targets)
        moved['ig-story-1']['assets'][0]['source'] = 'https://buffer.example.org/synthetic/elsewhere.png'
        result = self.plan(targets=moved)
        self.assertNotIn('ig-story-1', self.by_slot(result))
        self.assertEqual(self.holds(result)['ig-story-1'], 'edit_would_drop_alt_text_or_ai_label')

    def test_tiktok_photo_never_sets_ai_flag(self):
        slot = self.slots['tiktok-photo-1']
        args = self.by_slot(self.plan())['tiktok-photo-1']['arguments']
        self.assertNotIn('isAiGenerated', json.dumps(args))
        self.assertEqual(len(args['assets']), 2)
        flagged = {'tool': 'create_post', 'arguments': dict(args, metadata={'tiktok': {'isAiGenerated': True}})}
        self.assertIn('TikTok photo posts never set the AI-generated flag', release.argument_errors(flagged, slot))
        drafted = copy.deepcopy(slot)
        drafted['buffer_draft_id'] = 'aaaaaaaaaaaaaaaaaaaaaa04'
        target = {'id': drafted['buffer_draft_id'], 'channelId': 'cccccccccccccccccccccc04',
                  'channelService': 'tiktok', 'status': 'draft', 'via': 'api', 'assets': [],
                  'metadata': {'isAiGenerated': True}}
        with self.assertRaisesRegex(ValueError, 'edit_would_drop_alt_text_or_ai_label'):
            release.call_arguments(drafted, self.channel('tiktok'), NOW, target)

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
        targets = copy.deepcopy(self.targets)
        stale = {'url': 'https://example.org/synthetic/old', 'title': 'Old', 'text': '', 'thumbnails': []}
        targets['linkedin-1']['metadata']['linkAttachment'] = stale
        result = self.plan(targets=targets)
        self.assertNotIn('linkedin-1', self.by_slot(result))
        self.assertIn(hold, result['holds'])
        ledger = self.plan()['ledger']
        draft = dict(targets['linkedin-1'])
        with self.assertRaisesRegex(ValueError, 'still carries a link preview'):
            release.check_readback(slot, draft, 'queued', ledger)
        draft['metadata'] = {'type': 'post', 'linkAttachment': None}
        self.assertEqual(release.check_readback(slot, draft, 'queued', ledger)['status'], 'draft')

    def test_scheduled_is_not_sent(self):
        slot = self.slots['threads-1']
        ledger = self.ledger()
        scheduled = load('readback-queued')['threads-1']
        evidence = release.check_readback(slot, scheduled, 'queued', ledger)
        self.assertEqual(evidence['status'], 'scheduled')
        self.assertIs(evidence['published'], False)
        self.assertIsNone(evidence['native_url'])
        scheduled['externalLink'] = 'https://www.threads.com/@synthetic/post/SYNTHETIC1'
        with self.assertRaisesRegex(ValueError, 'scheduled is never sent'):
            release.check_readback(slot, scheduled, 'live', ledger)
        live = release.check_readback(slot, load('readback-live')['threads-1'], 'live', ledger)
        self.assertIs(live['published'], True)
        unbound = self.plan()['ledger']
        with self.assertRaisesRegex(ValueError, 'check queued first'):
            release.check_readback(slot, load('readback-live')['threads-1'], 'live', unbound)

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
        self.assertFalse(release.native_host('substack-notes', 'https://anyone.substack.com/p/S1'))
        account = 'https://x.com/synthetic'
        self.assertTrue(release.native_host('x', 'https://x.com/Synthetic/status/1', account))
        self.assertFalse(release.native_host('x', 'https://x.com/someoneelse/status/1', account))
        self.assertFalse(release.native_host('tiktok', native['tiktok'], 'https://www.tiktok.com/@other'))
        accounts = release.load_accounts()
        self.assertEqual(set(accounts), set(release.HANDLE_IN_PATH))
        slot = self.slots['threads-1']
        post = load('readback-live')['threads-1']
        for bad in (None, 'https://x.com/synthetic/status/1', 'http://www.threads.com/@synthetic/post/S1'):
            post['externalLink'] = bad
            with self.assertRaisesRegex(ValueError, 'native URL'):
                release.check_readback(slot, post, 'live', self.ledger())

    def test_link_sticker_never_claimed_automatic(self):
        for placement in ('link_sticker', 'Link Sticker', 'story-link-sticker'):
            slot = copy.deepcopy(self.slots['ig-story-1'])
            slot['link_placement'] = placement
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
        ledger = self.ledger()
        slot = self.slots['ig-story-1']
        evidence = release.check_readback(slot, load('readback-live')['ig-story-1'], 'live', ledger)
        self.assertEqual(evidence['link_sticker'], 'not_set_not_claimed')
        linked = load('readback-live')['ig-story-1']
        linked['metadata']['link'] = 'https://example.org/synthetic/x'
        with self.assertRaisesRegex(ValueError, 'link sticker is never set or claimed automatic'):
            release.check_readback(slot, linked, 'live', ledger)
        keyed = load('readback-live')['ig-story-1']
        keyed['metadata'] = {'instagram': dict(keyed['metadata'], stickerFields={'other': 'synthetic link'})}
        with self.assertRaisesRegex(ValueError, 'link sticker is never set or claimed automatic'):
            release.check_readback(slot, keyed, 'live', ledger)
        notify = load('readback-queued')['ig-story-1']
        notify['schedulingType'] = 'notification'
        with self.assertRaisesRegex(ValueError, 'never automatic'):
            release.check_readback(slot, notify, 'queued', ledger)

    def test_story_one_frame_per_post_dedupe_by_media_url(self):
        slot = copy.deepcopy(self.slots['ig-story-1'])
        slot['assets'].append(copy.deepcopy(self.slots['x-1']['assets'][0]))
        resign(slot)
        with self.assertRaisesRegex(ValueError, 'one frame per post'):
            release.check_slot(slot)
        ledger = self.ledger()
        post = load('readback-live')['ig-story-1']
        frame = post['assets'][0]
        post['assets'] = [frame, dict(frame, thumbnail='https://buffer.example.org/synthetic/thumb.png')]
        self.assertEqual(release.story_frame(post), frame['source'])
        release.check_readback(self.slots['ig-story-1'], post, 'live', ledger)
        post['assets'] = [frame, dict(frame, source='https://buffer.example.org/synthetic/other.png')]
        with self.assertRaisesRegex(ValueError, 'exactly one frame'):
            release.check_readback(self.slots['ig-story-1'], post, 'live', ledger)
        feed = load('readback-live')['ig-story-1']
        feed['metadata']['type'] = 'post'
        with self.assertRaisesRegex(ValueError, 'not stored as a Story'):
            release.check_readback(self.slots['ig-story-1'], feed, 'live', ledger)
        one = {'assets': [{'source': 'https://buffer.example.org/synthetic/a.png'}]}
        two = {'assets': [{'source': 'https://buffer.example.org/synthetic/b.png'}]}
        self.assertEqual(len(release.story_sequence([one, two])), 2)
        with self.assertRaisesRegex(ValueError, 'repeats an earlier frame'):
            release.story_sequence([one, two, copy.deepcopy(one)])

    def test_imported_posts_not_engine_publications(self):
        ledger = self.ledger()
        live = load('readback-live')
        imported = dict(live['threads-1'], id='dddddddddddddddddddddd01', via='network')
        other = dict(live['threads-1'], id='dddddddddddddddddddddd02', via='buffer')
        unlinked = dict(live['ig-story-1'], externalLink='https://example.org/not-native')
        counted = release.engine_publications([live['threads-1'], imported, other, live['ig-story-1']], ledger)
        self.assertEqual([p['id'] for p in counted], [THREADS_POST, 'aaaaaaaaaaaaaaaaaaaaaa01'])
        self.assertEqual(release.engine_publications([unlinked], ledger), [])
        with self.assertRaisesRegex(ValueError, 'imported from the network'):
            release.check_readback(self.slots['threads-1'], imported, 'live', ledger)
        with self.assertRaisesRegex(ValueError, 'not the one the engine released'):
            release.check_readback(self.slots['threads-1'], other, 'live', ledger)
        for empty in ({'run_id': self.spec['run_id'], 'released': {}}, None):
            with self.assertRaisesRegex(ValueError, 'absent from the release ledger'):
                release.check_readback(self.slots['threads-1'], live['threads-1'], 'live', empty)
        unbound = self.plan()['ledger']
        queued = load('readback-queued')['threads-1']
        with self.assertRaisesRegex(ValueError, 'came via the api'):
            release.check_readback(self.slots['threads-1'], dict(queued, via='buffer'), 'queued', unbound)

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
        unchecked = release.release_plan(self.spec, self.decision, None, None, self.channels, NOW, self.targets)
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
        resign(changed, decision, spec)
        third = self.plan(spec, decision, first['ledger'])
        self.assertEqual(third['calls'], [])
        self.assertIn({'slot_id': 'notes-1', 'hold': 'released_earlier_with_another_payload'}, third['holds'])

    def test_release_refuses_unsigned_or_mismatched_slot(self):
        spec = copy.deepcopy(self.spec)
        decision = copy.deepcopy(self.decision)
        del decision['slots']['notes-1']
        sign(spec, decision)
        spec['slots'][1]['words'] += ' Edited after signing.'
        resign(spec['slots'][1])
        x1 = spec['slots'][5]
        x1['link_placement'] = 'first_reply'
        resign(x1, decision, spec)
        result = self.plan(spec, decision)
        calls = self.by_slot(result)
        for sid in ('notes-1', 'threads-1', 'x-1'):
            self.assertNotIn(sid, calls)
        holds = self.holds(result)
        self.assertEqual(holds['notes-1'], 'unsigned_or_changed_since_signing')
        self.assertEqual(holds['threads-1'], 'payload_does_not_match_signed_digest')
        self.assertEqual(holds['x-1'], 'link_placement not expressible as one Buffer call: first_reply')
        tampered = copy.deepcopy(self.spec)
        tampered['slots'][0]['words'] += ' Hand edit.'
        with self.assertRaisesRegex(ValueError, 'not this slot\'s computed digest'):
            self.plan(tampered)
        for change in ({'decision': 'declined'}, {'run_id': 'synthetic:other'}, {'proposal_id': 'synthetic-other'}):
            with self.assertRaises(ValueError):
                self.plan(decision=dict(self.decision, **change))
        widened = copy.deepcopy(self.decision)
        widened['slots']['extra-1'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'signed decision_digest'):
            self.plan(decision=widened)
        for field in ('go_live_proposal_id', 'decision_digest'):
            unsigned = copy.deepcopy(self.spec)
            unsigned['signature'][field] = None
            with self.assertRaisesRegex(ValueError, 'not signed'):
                self.plan(unsigned)

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
        on_linkedin = dict(scheduled, service='linkedin')
        errors = release.argument_errors(on_linkedin, self.slots['x-1'])
        self.assertIn('LinkedIn is only ever an unscheduled draft; Krish makes the final click', errors)
        self.assertIn('the call is for another service than the slot', errors)

    def test_edit_target_must_be_same_service_draft(self):
        linkedin_draft = self.slots['linkedin-1']['buffer_draft_id']
        spec = copy.deepcopy(self.spec)
        spec['slots'][5]['buffer_draft_id'] = linkedin_draft
        targets = copy.deepcopy(self.targets)
        targets['x-1'] = copy.deepcopy(self.targets['linkedin-1'])
        result = self.plan(spec, targets=targets)
        self.assertNotIn('x-1', self.by_slot(result))
        self.assertIn('edit target is on another service', self.holds(result)['x-1'])
        for change, reason in (({'status': 'scheduled'}, 'not a draft'), ({'via': 'network'}, 'imported'),
                               ({'id': 'aaaaaaaaaaaaaaaaaaaaaa09'}, 'not the signed draft'),
                               ({'channelId': 'cccccccccccccccccccccc09'}, 'another Buffer channel')):
            targets = copy.deepcopy(self.targets)
            targets['x-1'].update(change)
            result = self.plan(targets=targets)
            self.assertNotIn('x-1', self.by_slot(result))
            self.assertIn(reason, self.holds(result)['x-1'])
        missing = self.plan(targets={})
        self.assertEqual({c['slot_id'] for c in missing['calls']}, {'notes-1', 'threads-1', 'tiktok-photo-1'})
        self.assertIn('was not read back', self.holds(missing)['linkedin-1'])

    def test_channel_id_bound_to_service(self):
        slot = self.slots['notes-1']
        with self.assertRaisesRegex(ValueError, 'live substack entry'):
            release.call_arguments(slot, self.channel('linkedin'), NOW)
        with self.assertRaisesRegex(ValueError, 'live substack entry'):
            release.call_arguments(slot, 'cccccccccccccccccccccc05', NOW)
        no_x = [c for c in self.channels if c['service'] != 'twitter']
        result = self.plan(channels=no_x)
        self.assertNotIn('x-1', self.by_slot(result))
        self.assertIn('never guess', self.holds(result)['x-1'])
        twice = self.channels + [dict(self.channel('threads'), id='cccccccccccccccccccccc07')]
        self.assertIn('more than one', self.holds(self.plan(channels=twice))['threads-1'])
        self.assertIn('never guess', self.holds(self.plan(channels={'threads': 'cccccccccccccccccccccc02'}))['threads-1'])

    def test_readback_requires_channel_service(self):
        slot = self.slots['threads-1']
        ledger = self.ledger()
        post = load('readback-queued')['threads-1']
        del post['channelService']
        with self.assertRaisesRegex(ValueError, 'no channelService'):
            release.check_readback(slot, post, 'queued', ledger)
        moved = dict(load('readback-queued')['threads-1'], channelId='ffffffffffffffffffffff01')
        with self.assertRaisesRegex(ValueError, 'another Buffer channel'):
            release.check_readback(slot, moved, 'queued', ledger)

    def test_krish_click_channels_match_profiles(self):
        for path in sorted((ROOT / 'social' / 'channels').glob('*.json')):
            profile = json.loads(path.read_text(encoding='utf-8'))
            channels = [c for c, p in release.CHANNEL_PROFILE.items() if p == profile['id']]
            self.assertTrue(channels, profile['id'])
            if profile['publication_mode'] == 'human_publish_only':
                for channel in channels:
                    self.assertIn(channel, release.KRISH_CLICK_ONLY)
        self.assertEqual(set(release.CHANNEL_PROFILE), set(release.CHANNELS))
        self.assertNotEqual(release.safe_name('a:b'), release.safe_name('a_b'))

    def test_cli_writes_ledger_and_evidence_only_under_scratch(self):
        root = self.dir / 'repo'
        root.mkdir()
        argv = ['release', 'plan', str(FIX / 'spec.json'), '--decision', str(FIX / 'decision.json'),
                '--assets', str(self.dir), '--channels', str(FIX / 'channels.json'),
                '--targets', str(FIX / 'targets.json'), '--now', NOW]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(release.main(argv, root), 0)
        self.assertEqual(len(json.loads(out.getvalue())), len(self.slots))
        run_dir = root / '.scratch' / 'runs' / release.safe_name(self.spec['run_id'])
        self.assertTrue((run_dir / 'ledger.json').is_file())
        self.assertFalse((run_dir / 'ledger.json.lock').exists())
        for stage in ('queued', 'live'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = release.main(['release', 'check', str(FIX / 'spec.json'), '--readback',
                                     str(FIX / ('readback-' + stage + '.json')), '--stage', stage, '--now', NOW], root)
            self.assertEqual(code, 0, out.getvalue())
            self.assertTrue((run_dir / stage / 'threads-1.json').is_file())
        ledger = json.loads((run_dir / 'ledger.json').read_text(encoding='utf-8'))
        self.assertEqual(ledger['released']['threads-1']['post_id'], THREADS_POST)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(release.main(argv[:-2] + ['--ledger', str(self.dir / 'outside.json')], root), 1)
            other = root / '.scratch' / 'other.json'
            self.assertEqual(release.main(argv[:-2] + ['--ledger', str(other)], root), 1)
            empty = self.dir / 'empty'
            empty.mkdir()
            self.assertEqual(release.main(['check', str(FIX / 'spec.json'), '--readback',
                                           str(FIX / 'readback-live.json'), '--stage', 'live'], empty), 1)
            ledger['run_id'] = 'synthetic:other'
            (run_dir / 'ledger.json').write_text(json.dumps(ledger), encoding='utf-8')
            self.assertEqual(release.main(['check', str(FIX / 'spec.json'), '--readback',
                                           str(FIX / 'readback-live.json'), '--stage', 'live'], root), 1)
        self.assertFalse((self.dir / 'outside.json').exists())
        self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
