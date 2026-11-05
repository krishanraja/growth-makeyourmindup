"""The Publishing engine (engine/engines/publishing.py) and its acceptance replay from the 5 Nov review.

"Holds the affected Buffer video route, preserves the verified photo route, and distinguishes the Facebook
grid from the player. Keeps the YouTube continuation open until it works from the public Short." The route
lookups read the real social/ records; the edition fixtures are synthetic, written through core.append into a
temp root that also carries the committed seeds, and read back by core.start.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine import social
from engine.engines import core, publishing as pub

ROOT = Path(__file__).resolve().parents[1]
REVIEW = {'kind': 'review', 'ref': 'docs/reviews/2026-11-05-growth-engine-review.md', 'observed_at': '2026-11-05'}
SAVED = {'kind': 'private_file', 'ref': '.scratch/engines/saved-settings.json', 'observed_at': '2026-11-05'}
PAYLOAD = core.digest('synthetic approved edition')


def edition(rid, channel, format_id, route='buffer', state='public', post_id='post-1', **changes):
    value = {'id': rid, 'engine': 'publishing', 'kind': 'edition', 'title': 'Synthetic ' + channel + ' edition',
             'state': state, 'source': REVIEW, 'next_owner': 'publishing', 'next_action': 'read back the reader view',
             'revisit_when': 'after every check is read back', 'links': [], 'updated_at': '2026-11-05',
             'detail': {'channel': channel, 'format': format_id, 'route': route, 'payload_sha256': PAYLOAD,
                        'post_id': post_id, 'due_on': '2026-11-05'}}
    value.update(changes)
    return value


def check(rid, edition_id, name, channel, format_id, state='open', post_id='post-1', **changes):
    value = {'id': rid, 'engine': 'publishing', 'kind': 'check', 'title': 'Synthetic ' + name + ' check',
             'state': state, 'source': REVIEW, 'next_owner': 'publishing', 'next_action': 'read back ' + name,
             'revisit_when': 'after the public readback', 'links': [edition_id], 'updated_at': '2026-11-05',
             'detail': {'check': name, 'channel': channel, 'format': format_id, 'post_id': post_id}}
    value.update(changes)
    return value


class AcceptanceReplay(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines')

    def start(self, now='2026-11-05'):
        return core.start('publishing', self.root, now=now, private=False)

    def test_holds_the_buffer_video_route_and_preserves_the_photo_route(self):
        video = social.route('tiktok', 'short-video', as_of='2026-11-05')
        self.assertEqual(video['holds'], ['route_held_after_provider_rejection'])
        self.assertNotIn('capability_not_verified_for_selected_channel_and_format', video['holds'])
        self.assertEqual(video['route_hold']['held_since'], '2026-11-05')
        self.assertIn('native TikTok uploader', video['route_hold']['alternative'])
        self.assertIn('tiktok-buffer-video-hold', [x['id'] for x in video['lessons']])
        photo = social.route('tiktok', 'carousel', as_of='2026-10-27')
        self.assertEqual((photo['holds'], photo['known_capability']['status']), ([], 'verified'))
        self.assertIsNone(photo['route_hold'])
        recovered = self.start()['recover']
        self.assertEqual([(h['route'], h['tool_record'], h['record']) for h in recovered['route_holds']],
                         [('buffer tiktok short-video', 'held', 'pub-buffer-tiktok-video-hold')])
        self.assertEqual(recovered['route_hold_mismatches'], [])
        core.append('publishing', edition('ed-tiktok', 'tiktok', 'short-video', state='approved', post_id=None),
                    self.root)
        blocked = self.start()['recover']['blocked_editions']
        self.assertEqual([b['id'] for b in blocked], ['ed-tiktok'])
        self.assertIn('native TikTok uploader', blocked[0]['alternative'])

    def test_facebook_grid_and_player_are_separate_checks_on_one_post(self):
        self.assertEqual(pub.applicable_checks('facebook', 'short-video'),
                         ('scheduled', 'public', 'grid_cover', 'player_cover'))
        core.append('publishing', edition('ed-fb', 'facebook', 'short-video'), self.root)
        for name in pub.applicable_checks('facebook', 'short-video'):
            core.append('publishing', check('ck-fb-' + name.replace('_', '-'), 'ed-fb', name, 'facebook',
                                            'short-video'), self.root)
        records = core.load('publishing', self.root, private=False)
        for name in ('scheduled', 'public', 'grid_cover'):
            line = pub.readback(records['ck-fb-' + name.replace('_', '-')], True, '2026-11-05', 'public grid')
            core.append('publishing', line, self.root)
        player = pub.readback(records['ck-fb-player-cover'], False, '2026-11-05', 'public player',
                              recheck_on='2026-11-12')
        core.append('publishing', player, self.root)
        records = core.load('publishing', self.root, private=False)
        status = pub.edition_status(records['ed-fb'], records)
        self.assertEqual(status['checks']['grid_cover'], 'passed')
        self.assertEqual(status['checks']['player_cover'], 'discrepancy')
        self.assertEqual((status['remaining'], status['done']), (['player_cover'], False))
        self.assertEqual(records['ck-fb-player-cover']['detail']['post_id'], 'post-1')
        with self.assertRaisesRegex(ValueError, 'open checks: player_cover'):
            pub.close_edition(records['ed-fb'], records, '2026-11-05')
        with self.assertRaisesRegex(ValueError, 'on post post-1'):
            pub.readback(records['ck-fb-player-cover'], True, '2026-11-12', 'public player', post_id='post-2')
        recovered = self.start(now='2026-11-12')['recover']
        self.assertIn('ck-fb-player-cover', recovered['overdue_rechecks'])
        # The seed's post ID is unknown, so its recheck is undated until the post ID is recovered.
        self.assertNotIn('pub-facebook-reels-player-cover', recovered['overdue_rechecks'])
        core.append('publishing', pub.readback(records['ck-fb-player-cover'], True, '2026-11-12', 'public player'),
                    self.root)
        records = core.load('publishing', self.root, private=False)
        done = pub.close_edition(records['ed-fb'], records, '2026-11-12')
        self.assertEqual((done['state'], done['next_owner']), ('done', 'measurement'))
        core.append('publishing', done, self.root)
        self.assertEqual(core.check(self.root), [])

    def test_saved_settings_never_close_a_check(self):
        core.append('publishing', edition('ed-fb', 'facebook', 'short-video'), self.root)
        saved = check('ck-grid', 'ed-fb', 'grid_cover', 'facebook', 'short-video', state='passed', source=SAVED,
                      next_owner='none', next_action=None, revisit_when=None)
        with self.assertRaisesRegex(ValueError, 'saved settings never do'):
            core.append('publishing', saved, self.root)
        undated = check('ck-player', 'ed-fb', 'player_cover', 'facebook', 'short-video', state='discrepancy')
        with self.assertRaisesRegex(ValueError, 'bounded recheck'):
            core.append('publishing', undated, self.root)

    def facebook_edition(self, rid='ed-fb', post_id='post-1'):
        """A Facebook Reels edition with scheduled, public and grid cover passed by live readback."""
        core.append('publishing', edition(rid, 'facebook', 'short-video', post_id=post_id), self.root)
        for name in ('scheduled', 'public', 'grid_cover'):
            line = check(rid + '-' + name.replace('_', '-'), rid, name, 'facebook', 'short-video', post_id=post_id)
            core.append('publishing', pub.readback(line, True, '2026-11-05', 'public view'), self.root)

    def test_a_check_closes_only_as_passed_on_a_readback(self):
        self.facebook_edition()
        for state in ('not_applicable', 'closed', 'done', 'released'):
            line = check('ck-player', 'ed-fb', 'player_cover', 'facebook', 'short-video', state=state, source=SAVED,
                         next_owner='none', next_action=None, revisit_when=None)
            with self.assertRaisesRegex(ValueError, 'check state must be one of open, discrepancy, passed|is not a state of check'):
                core.append('publishing', line, self.root)
        records = core.load('publishing', self.root, private=False)
        with self.assertRaisesRegex(ValueError, 'open checks: player_cover'):
            pub.close_edition(records['ed-fb'], records, '2026-11-05')

    def test_a_check_on_another_post_never_closes_the_editions_check(self):
        self.facebook_edition()
        player = check('ck-player', 'ed-fb', 'player_cover', 'facebook', 'short-video')
        core.append('publishing', pub.readback(player, False, '2026-11-05', 'public player', recheck_on='2026-11-12'),
                    self.root)
        other = check('ck-player-z', 'ed-fb', 'player_cover', 'facebook', 'short-video', post_id='OTHER-POST')
        core.append('publishing', pub.readback(other, True, '2026-11-06', 'public player'), self.root)
        records = core.load('publishing', self.root, private=False)
        status = pub.edition_status(records['ed-fb'], records)
        self.assertEqual((status['checks']['player_cover'], status['done']), ('discrepancy', False))
        with self.assertRaisesRegex(ValueError, 'open checks: player_cover'):
            pub.close_edition(records['ed-fb'], records, '2026-11-06')
        self.assertEqual([e.split(': ', 1)[1] for e in core.check(self.root)],
                         ['ck-player-z: linked to edition ed-fb on another channel, format or post'])

    def test_engine_check_refuses_a_done_edition_with_an_open_check(self):
        self.facebook_edition()
        player = check('ck-player', 'ed-fb', 'player_cover', 'facebook', 'short-video')
        core.append('publishing', pub.readback(player, False, '2026-11-05', 'public player', recheck_on='2026-11-12'),
                    self.root)
        records = core.load('publishing', self.root, private=False)
        core.append('publishing', dict(records['ed-fb'], state='done', revisit_when=None), self.root)
        self.assertEqual([e.split(': ', 1)[1] for e in core.check(self.root)],
                         ['ed-fb: done edition with checks not passed on its post: player_cover'])
        for state in ('released', 'passed', 'not_applicable', 'closed'):
            line = edition('ed-li', 'linkedin', 'carousel', route='krish_click', state=state, post_id=None,
                           revisit_when=None)
            with self.assertRaisesRegex(ValueError, 'edition state must be one of|is not a state of edition'):
                core.append('publishing', line, self.root)

    def test_channel_is_a_known_channel_id(self):
        with self.assertRaisesRegex(ValueError, 'channel id in social/channels'):
            core.append('publishing', edition('ed-li', 'LinkedIn', 'carousel', state='scheduled'), self.root)
        with self.assertRaisesRegex(ValueError, 'channel id in social/channels'):
            core.append('publishing', check('ck-x', 'ed-x', 'public', 'Facebook', 'short-video'), self.root)

    def test_a_due_edition_on_a_held_route_points_at_the_alternative(self):
        core.append('publishing', edition('ed-tiktok', 'tiktok', 'short-video', state='approved', post_id=None),
                    self.root)
        result = self.start()
        self.assertNotIn('ed-tiktok', result['recover']['due_slots'])
        self.assertEqual((result['next_action']['id'], result['next_action']['next_owner']), ('ed-tiktok', 'krish'))
        self.assertIn('held route buffer: offer native TikTok uploader', result['next_action']['next_action'])

    def test_youtube_continuation_stays_open_until_it_works_from_the_public_short(self):
        seed = core.load('publishing', self.root, private=False)['pub-youtube-short-continuation']
        self.assertEqual((seed['state'], seed['detail']['check'], seed['detail']['post_id']),
                         ('open', 'continuation_link', None))
        unresolved = {c['id']: c for c in self.start()['recover']['unresolved_checks']}
        self.assertIn('pub-youtube-short-continuation', unresolved)
        self.assertIn('pub-facebook-reels-player-cover', unresolved)
        # Scheduled correctly is not enough, and no Short ID means nothing to read back.
        no_id = dict(seed, state='passed', source=dict(REVIEW, kind='live_readback'), revisit_when=None)
        self.assertIn('a passed check names the post ID it was read on', core.validate(no_id))
        core.append('publishing', edition('ed-yt', 'youtube', 'short-video', post_id='short-1'), self.root)
        core.append('publishing', check('ck-yt-cont', 'ed-yt', 'continuation_link', 'youtube', 'short-video',
                                        post_id='short-1'), self.root)
        records = core.load('publishing', self.root, private=False)
        self.assertIn('continuation_link', pub.edition_status(records['ed-yt'], records)['remaining'])
        works = pub.readback(records['ck-yt-cont'], True, '2026-11-06', 'public Short continuation')
        self.assertEqual((works['state'], works['source']['kind']), ('passed', 'live_readback'))

    def test_linkedin_follows_its_human_publication_rule(self):
        self.assertEqual(pub.applicable_checks('linkedin', 'carousel'), ('public',))
        with self.assertRaisesRegex(ValueError, 'human publication rule'):
            core.append('publishing', edition('ed-li', 'linkedin', 'carousel', state='scheduled'), self.root)
        core.append('publishing', edition('ed-li', 'linkedin', 'carousel', route='krish_click', state='approved',
                                          post_id=None), self.root)
        with self.assertRaisesRegex(ValueError, 'does not apply'):
            core.append('publishing', check('ck-li', 'ed-li', 'scheduled', 'linkedin', 'carousel'), self.root)

    def test_start_reads_only_and_names_the_first_action(self):
        before = sorted(p for p in self.root.rglob('*'))
        result = self.start()
        self.assertEqual(sorted(p for p in self.root.rglob('*')), before)
        self.assertEqual(result['entry_request'], 'Run Publishing')
        self.assertEqual(result['next_action']['id'], 'pub-facebook-reels-player-cover')
        self.assertTrue(set(result['recover']) >= {'due_slots', 'approved_editions', 'provider_records',
                                                   'route_holds', 'unresolved_checks'})


class CommittedRecords(unittest.TestCase):
    def test_seeds_pass_check_and_cite_the_review(self):
        self.assertEqual(core.check(ROOT), [])
        seeds = core.load('publishing', ROOT, private=False)
        self.assertEqual(set(seeds), {'pub-buffer-tiktok-video-hold', 'pub-facebook-reels-player-cover',
                                      'pub-youtube-short-continuation'})
        for r in seeds.values():
            self.assertEqual(r['source'], REVIEW)
            self.assertNotEqual(r['state'], 'passed')

    def test_held_capability_needs_its_fields(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(ROOT / 'social', tmp / 'social')
        for ref in ('docs', 'BROWSER.md', 'AGENTS.md'):
            src = ROOT / ref
            (shutil.copytree if src.is_dir() else shutil.copy)(src, tmp / ref)
        social.inventory(tmp)
        path = tmp / 'social' / 'tools' / 'buffer.json'
        buffer = json.loads(path.read_text(encoding='utf-8'))
        held = next(c for c in buffer['capabilities'] if c['status'] == 'held')
        del held['recheck_when']
        path.write_text(json.dumps(buffer, indent=2), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'held capability requires held_since, failure, recheck_when'):
            social.inventory(tmp)


if __name__ == '__main__':
    unittest.main()
