"""Regression gates for Krish's 27 Oct 2026 rulings: Notes, Threads and the Canva lane."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.social import DELEGATED_PERSONAL, ROOT, inventory, preflight, route

MEME_CHANNELS = {'instagram', 'facebook', 'tiktok', 'youtube', 'x', 'threads'}


def package(channel, account_url, context, format_id, owner='content-engine', due=None):
    return {'schema_version': 1, 'kind': 'package', 'id': 'synthetic-package',
            'channel': channel, 'account_url': account_url, 'account_context': context,
            'format': format_id, 'tool': 'buffer', 'source_url': 'https://example.com/verified-test',
            'caption': 'Synthetic test copy.', 'assets': [],
            'production': {'owner': owner, 'approved': True, 'evidence_ref': 'synthetic-only'},
            'voice_review_passed': True, 'proposed_due_at': due,
            'platform_metadata': {'ai_generated': None, 'share_to_feed': None,
                                  'post_type': None, 'link_preview_url': None},
            'publication_approval': {'approved': False, 'payload_sha256': None, 'evidence_ref': None}}


class NewChannelsTests(unittest.TestCase):
    def test_threads_has_delegated_cadence_with_personal_voice(self):
        # Krish, 27 Oct 2026 (CHANGES.md): Threads added, personal voice like X and TikTok.
        self.assertIn('threads', DELEGATED_PERSONAL)
        threads = inventory()['channel']['threads']
        self.assertEqual(threads['account_url'], 'https://www.threads.com/@krishraja1')
        self.assertEqual(threads['account_context'], 'personal')
        self.assertEqual(threads['publication_mode'], 'approved_content_cadence')
        self.assertEqual(threads['daily_posts_target'], 1)
        self.assertEqual(threads['voice_policy'], 'docs/ACCOUNT-VOICE.md')
        self.assertTrue({'text', 'single-image'} <= set(threads['formats']))
        self.assertTrue({'personal-account-register', 'notes-threads-in-scope'} <= set(threads['lessons']))
        p = package('threads', threads['account_url'], 'personal', 'text', due='2026-11-02T14:00:00+00:00')
        result = preflight(p, '2026-10-27')
        self.assertEqual(result['publication_mode'], 'approved_content_cadence')
        self.assertNotIn('personal_account_human_final_publication_required', result['holds'])
        self.assertFalse(result['publication_authorized'])
        p['account_context'] = 'publication'
        with self.assertRaisesRegex(ValueError, 'speaking context'):
            preflight(p, '2026-10-27')

    def test_substack_notes_is_personal_cadence(self):
        # Notes post from Krish's own Substack profile (substack-notes-identity, 27 Oct).
        notes = inventory()['channel']['substack-notes']
        self.assertEqual(notes['account_url'], 'https://substack.com/@mindmakerlive')
        self.assertEqual(notes['account_context'], 'personal')
        self.assertEqual(notes['publication_mode'], 'approved_content_cadence')
        self.assertEqual(notes['daily_posts_target'], 2)
        self.assertEqual(notes['formats'], ['note'])
        self.assertTrue(any('mindmakerlive' in x and 'held for Krish' in x for x in notes['live_checks']))
        self.assertIn('notes-threads-in-scope', notes['lessons'])
        self.assertIn('substack-notes-identity', notes['lessons'])
        p = package('substack-notes', notes['account_url'], 'personal', 'note',
                    owner='growth-canva', due='2026-11-02T13:00:00+00:00')
        result = preflight(p, '2026-10-27')
        self.assertEqual(result['publication_mode'], 'approved_content_cadence')
        self.assertNotIn('personal_account_human_final_publication_required', result['holds'])
        self.assertFalse(result['publication_authorized'])
        p['account_context'] = 'publication'
        with self.assertRaisesRegex(ValueError, 'speaking context'):
            preflight(p, '2026-10-27')

    def test_meme_and_note_are_owned_by_growth_canva(self):
        records = inventory()
        formats = records['format']
        # 27 Oct evening: the V1 calendar's cards, polls and Story frames join the Canva lane
        # (invariants/boundary.json owners; story artwork itself stays content-engine's).
        canva = ('note', 'meme', 'receipt-card', 'quote-card', 'scorecard', 'poll', 'story-frame')
        for name in canva:
            self.assertEqual(formats[name]['production_owner'], 'growth-canva')
            self.assertEqual(formats[name]['production_reference'], 'social/guides/canva.md')
            self.assertIn('canva-lane-boundary', formats[name]['lessons'])
        for name, obj in formats.items():
            if name not in canva:
                self.assertEqual(obj['production_owner'], 'content-engine', name)
        self.assertEqual(set(formats['meme']['channels']), MEME_CHANNELS)
        self.assertEqual(formats['note']['channels'], ['substack-notes'])
        lesson = records['lesson']['canva-lane-boundary']
        self.assertEqual((lesson['status'], lesson['evidence']['kind']), ('accepted', 'user_ruling'))
        guide = ROOT / 'social' / 'guides' / 'canva.md'
        self.assertLessEqual(len(guide.read_bytes()), 2048)
        text = guide.read_text(encoding='utf-8')
        for phrase in ('brand kit', 'approved template', 'literal match', 'AI label',
                       'real video', 'Never publish', '4 Growth', 'docs/ASSET-STORAGE.md'):
            self.assertIn(phrase, text)
        # A meme package claiming content-engine ownership is refused.
        threads = records['channel']['threads']
        p = package('threads', threads['account_url'], 'personal', 'meme')
        with tempfile.TemporaryDirectory() as tmp:
            asset = Path(tmp) / 'meme.bin'
            asset.write_bytes(b'synthetic meme export, not a real post')
            p['assets'] = [{'path': str(asset), 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
                            'alt_text': 'Synthetic meme export.'}]
            with self.assertRaisesRegex(ValueError, 'production owner'):
                preflight(p, '2026-10-27')
            p['production']['owner'] = 'growth-canva'
            self.assertTrue(preflight(p, '2026-10-27')['structurally_valid'])

    def test_substack_article_has_no_daily_target(self):
        # G8: "Substack retains its approved editorial rhythm" (PUBLISHING-AUTHORITY.md).
        substack = inventory()['channel']['substack']
        self.assertIsNone(substack['daily_posts_target'])
        self.assertEqual(substack['publication_mode'], 'approved_brand_content')
        self.assertEqual(substack['formats'], ['article'])

    def test_unknown_personal_account_is_still_human_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
            (root / 'docs').mkdir()
            for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
                shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
            text_path = root / 'social' / 'formats' / 'text.json'
            text = json.loads(text_path.read_text(encoding='utf-8'))
            text['channels'].append('synthetic-personal')
            text_path.write_text(json.dumps(text, indent=2), encoding='utf-8')
            channel = json.loads((root / 'social' / 'channels' / 'threads.json').read_text(encoding='utf-8'))
            channel.update(id='synthetic-personal', account_url='https://example.com/@synthetic',
                           formats=['text'])
            path = root / 'social' / 'channels' / 'synthetic-personal.json'

            def attempt(**fields):
                channel.update(fields)
                path.write_text(json.dumps(channel, indent=2), encoding='utf-8')
                return inventory(root)

            with self.assertRaisesRegex(ValueError, 'cannot expand publication authority'):
                attempt(publication_mode='approved_content_cadence')
            with self.assertRaisesRegex(ValueError, 'cannot expand publication authority'):
                attempt(publication_mode='approved_brand_content')
            with self.assertRaisesRegex(ValueError, 'no automatic posting quota'):
                attempt(publication_mode='human_publish_only')
            records = attempt(publication_mode='human_publish_only', daily_posts_target=None)
            self.assertEqual(records['channel']['synthetic-personal']['publication_mode'], 'human_publish_only')
            decision = route('synthetic-personal', 'text', as_of='2026-10-27', root=root)
            self.assertEqual(decision['channel']['publication_mode'], 'human_publish_only')
            # Even a delegated personal account cannot take a publication's two-a-day target.
            threads_path = root / 'social' / 'channels' / 'threads.json'
            threads = json.loads(threads_path.read_text(encoding='utf-8'))
            threads['daily_posts_target'] = 2
            threads_path.write_text(json.dumps(threads, indent=2), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'only Substack Notes has a two-a-day target'):
                inventory(root)
            # A delegated personal identity cannot be relabelled as a publication.
            threads.update(daily_posts_target=1, account_context='publication',
                           publication_mode='approved_brand_content')
            threads_path.write_text(json.dumps(threads, indent=2), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'cannot expand publication authority'):
                inventory(root)
            threads.update(account_context='personal', publication_mode='approved_content_cadence')
            threads_path.write_text(json.dumps(threads, indent=2), encoding='utf-8')
            inventory(root)
            # Two a day belongs to Substack Notes alone, not to every branded channel.
            insta_path = root / 'social' / 'channels' / 'instagram.json'
            insta = json.loads(insta_path.read_text(encoding='utf-8'))
            insta['daily_posts_target'] = 2
            insta_path.write_text(json.dumps(insta, indent=2), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'only Substack Notes has a two-a-day target'):
                inventory(root)

    def test_route_for_threads_text_holds_unverified_capability(self):
        decision = route('threads', 'text', as_of='2026-10-27')
        self.assertEqual(decision['holds'], ['capability_not_verified_for_selected_channel_and_format'])
        self.assertFalse(decision['publication_authorized'])
        cap = decision['known_capability']
        self.assertEqual((cap['status'], cap['verified_at'], cap['verified_operations']), ('unverified', None, []))
        self.assertIn('Not verified', cap['evidence_ref'])
        self.assertIn('notes-threads-in-scope', [x['id'] for x in decision['lessons']])
        self.assertIn('docs/ACCOUNT-VOICE.md', decision['read'])
        buffer = inventory()['tool']['buffer']
        new = [c for c in buffer['capabilities']
               if c['channel'] in ('threads', 'substack-notes') or c['format'] == 'meme']
        self.assertEqual({(c['channel'], c['format']) for c in new},
                         {('threads', 'text'), ('threads', 'single-image'), ('substack-notes', 'note')}
                         | {(c, 'meme') for c in MEME_CHANNELS})
        for c in new:
            self.assertEqual((c['status'], c['verified_at'], c['verified_operations']), ('unverified', None, []))
            self.assertIn('Not verified', c['evidence_ref'])
        notes = next(c for c in new if c['channel'] == 'substack-notes')
        self.assertIn('Not verified', notes['evidence_ref'])  # connected 27 Oct; posting still unchecked


if __name__ == '__main__':
    unittest.main()
