"""Offline regression gates for reusable social procedures and exact packages."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from engine.buffer_channels import BUFFER_CHANNEL_ID, DENIED_CHANNELS, HANDED_OFF_CHANNELS
from engine.social import (ROOT, command, draft_target_errors, inventory, package_digest, preflight, route,
                           validate)

# A realistic share block (Krish, 2026-10-28: every snackable package says why one person sends it to another).
SHARE = {'sender': 'a head of marketing at a mid-size retailer',
         'receiver': 'her CEO, who keeps asking when the AI pilot pays back',
         'job': 'settles_it',
         'dm_line': 'This is the six-week rule I meant: agree one number on day one, then decide.',
         'moment': 'the Monday leadership meeting where the pilot budget comes up again',
         'standalone': True}


SYNTHETIC_ID = 'f' * 24


@contextlib.contextmanager
def human_only_root():
    """A copy of the records with one synthetic personal account that has no delegated cadence
    (human_publish_only), as any personal identity beyond X, TikTok, Threads and Notes is. LinkedIn was the live
    one until 13 Nov 2026, when it went to growth-mindmake (Ruling, Krish, 2026-11-13), so the personal guard is
    proved on this synthetic account and its synthetic pinned Buffer id."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
        (root / 'docs').mkdir()
        for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
            shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
        fmt_path = root / 'social' / 'formats' / 'single-image.json'
        fmt = json.loads(fmt_path.read_text(encoding='utf-8'))
        fmt['channels'].append('synthetic-personal')
        fmt_path.write_text(json.dumps(fmt, indent=2), encoding='utf-8')
        channel = json.loads((root / 'social' / 'channels' / 'x.json').read_text(encoding='utf-8'))
        channel.update(id='synthetic-personal', account_url='https://example.com/@synthetic', formats=['single-image'],
                       publication_mode='human_publish_only', daily_posts_target=None)
        channel.pop('daily_posts_floor', None)
        (root / 'social' / 'channels' / 'synthetic-personal.json').write_text(json.dumps(channel, indent=2),
                                                                             encoding='utf-8')
        tool_path = root / 'social' / 'tools' / 'buffer.json'
        tool = json.loads(tool_path.read_text(encoding='utf-8'))
        tool['capabilities'].append({'channel': 'synthetic-personal', 'format': 'single-image', 'status': 'verified',
                                     'verified_at': '2026-10-26', 'evidence_ref': 'synthetic',
                                     'verified_operations': ['draft']})
        tool_path.write_text(json.dumps(tool, indent=2), encoding='utf-8')
        with mock.patch.dict(BUFFER_CHANNEL_ID, {'synthetic-personal': SYNTHETIC_ID}):
            yield root


def human_only(package):
    """The package moved onto the synthetic human-only personal account."""
    package.update(channel='synthetic-personal', account_url='https://example.com/@synthetic',
                   account_context='personal', buffer_channel_id=SYNTHETIC_ID)
    return package


class SocialContractsTests(unittest.TestCase):
    def test_registry_and_known_channel_routes(self):
        records = inventory()
        # Threads and Substack Notes joined the live set on 27 Oct 2026 (CHANGES.md).
        self.assertEqual(set(records['channel']), {'instagram', 'facebook', 'linkedin', 'x', 'tiktok', 'youtube',
                                                   'substack', 'substack-notes', 'threads'})
        ig = route('instagram', 'carousel', as_of='2026-10-26')
        self.assertEqual(ig['holds'], [])
        self.assertEqual(ig['channel']['account_context'], 'publication')
        self.assertFalse(ig['publication_authorized'])
        self.assertIn('clipboard-image-upload', [x['id'] for x in ig['lessons']])
        x = route('x', 'single-image', as_of='2026-10-26')
        self.assertEqual(x['channel']['account_context'], 'personal')
        self.assertEqual(x['holds'], [])
        # The LinkedIn record stays, marked as growth-mindmake's (Ruling, Krish, 2026-11-13); it routes nothing.
        self.assertEqual(records['channel']['linkedin']['owned_by']['engine'], 'growth-mindmake')
        with self.assertRaisesRegex(ValueError, "growth-mindmake's since 2026-11-13"):
            route('linkedin', 'single-image', as_of='2026-10-26')

    def test_unknown_document_route_is_not_inferred_from_png_success(self):
        # The LinkedIn document route this once held is growth-mindmake's since 13 Nov 2026: refused outright.
        with self.assertRaisesRegex(ValueError, "growth-mindmake's"):
            route('linkedin', 'carousel', as_of='2026-10-26')
        # A verified route still never vouches for its unverified neighbour on the same channel.
        result = route('instagram', 'single-image', as_of='2026-10-26')
        self.assertIn('capability_not_verified_for_selected_channel_and_format', result['holds'])
        with self.assertRaises(ValueError):
            route('youtube', 'carousel', as_of='2026-10-26')

    def test_stale_and_future_observations_require_bounded_recheck(self):
        for day in ('2026-11-03', '2026-10-25'):
            result = route('instagram', 'carousel', as_of=day)
            self.assertIn('capability_observation_requires_recheck', result['holds'])
        self.assertEqual(route('instagram', 'carousel', as_of='2026-11-02')['holds'], [])

    def fixture(self, path):
        path.write_bytes(b'synthetic accepted asset, not a real post')
        return {'schema_version': 1, 'kind': 'package', 'id': 'synthetic-package',
                'channel': 'x', 'account_url': 'https://x.com/therealkrisho',
                'account_context': 'personal', 'format': 'single-image', 'tool': 'buffer',
                'buffer_channel_id': BUFFER_CHANNEL_ID['x'],
                'source_url': 'https://example.com/verified-test', 'caption': 'Synthetic test copy.',
                'share': copy.deepcopy(SHARE),
                'assets': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'alt_text': 'Synthetic regression asset.'}],
                'production': {'owner': 'content-engine', 'approved': True, 'evidence_ref': 'synthetic-only'},
                'voice_review_passed': True, 'proposed_due_at': None,
                'platform_metadata': {'ai_generated': None, 'share_to_feed': None,
                                      'post_type': None, 'link_preview_url': None},
                'publication_approval': {'approved': False, 'payload_sha256': None, 'evidence_ref': None}}

    def test_missing_approval_survives_valid_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = preflight(self.fixture(Path(tmp) / 'asset.bin'), '2026-10-26')
            self.assertTrue(result['structurally_valid'])
            self.assertFalse(result['publication_authorized'])
            self.assertIn('live_identity_schema_and_authority_readback_required_before_external_action',
                          result['holds'])
            with human_only_root() as root:
                result = preflight(human_only(self.fixture(Path(tmp) / 'asset.bin')), '2026-10-26', root=root)
                self.assertTrue(result['structurally_valid'])
                self.assertIn('exact_publication_approval_missing', result['holds'])
                self.assertFalse(result['publication_authorized'])

    def test_linkedin_is_never_prepared_here(self):
        # Ruling (Krish, 2026-11-13): growth-mindmake owns his personal LinkedIn, posts and replies. No package
        # for it passes preflight, on its old pinned Buffer channel or any other, and its id is refused anywhere.
        linkedin = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
        self.assertNotIn('linkedin', BUFFER_CHANNEL_ID)
        self.assertNotIn(linkedin, BUFFER_CHANNEL_ID.values())
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            for channel_id in (linkedin, BUFFER_CHANNEL_ID['x']):
                p.update(channel='linkedin', account_url='https://www.linkedin.com/in/krish-raja/',
                         buffer_channel_id=channel_id)
                with self.assertRaisesRegex(ValueError, "growth-mindmake's since 2026-11-13"):
                    preflight(p, '2026-10-26')
            # Its old Buffer channel is refused on a channel this engine does own, too.
            p = self.fixture(Path(tmp) / 'asset.bin')
            p['buffer_channel_id'] = linkedin
            with self.assertRaisesRegex(ValueError, "growth-mindmake's"):
                preflight(p, '2026-10-26')
            path = Path(tmp) / 'package.json'
            path.write_text(json.dumps(dict(p, channel='linkedin')), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(command(['route', 'linkedin', 'text', '--as-of', '2026-10-26']), 1)
                self.assertEqual(command(['preflight', str(path), '--as-of', '2026-10-26']), 1)
            self.assertIn('growth-mindmake', out.getvalue())

    def test_asset_change_and_missing_alt_text_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'asset.bin'
            p = self.fixture(path)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed production asset'):
                preflight(p, '2026-10-26')
            p = self.fixture(path)
            p['assets'][0]['alt_text'] = ' '
            with self.assertRaises(ValueError):
                preflight(p, '2026-10-26')

    def test_wrong_account_context_and_unreviewed_voice_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self.fixture(Path(tmp) / 'asset.bin')
            for field, value in [('account_context', 'publication'), ('account_url', 'https://example.com/company'),
                                 ('voice_review_passed', False)]:
                p = copy.deepcopy(original)
                p[field] = value
                with self.assertRaises(ValueError):
                    preflight(p, '2026-10-26')

    def test_personal_accounts_cannot_receive_a_scheduled_time(self):
        with tempfile.TemporaryDirectory() as tmp, human_only_root() as root:
            p = human_only(self.fixture(Path(tmp) / 'asset.bin'))
            p['proposed_due_at'] = '2026-10-27T14:00:00+00:00'
            with self.assertRaisesRegex(ValueError, 'remain unscheduled'):
                preflight(p, '2026-10-26', root=root)
            p['proposed_due_at'] = None
            p['publication_approval'] = {'approved': True, 'payload_sha256': package_digest(p),
                                        'evidence_ref': 'synthetic approval cannot widen authority'}
            result = preflight(p, '2026-10-26', root=root)
            self.assertIn('personal_account_human_final_publication_required', result['holds'])
            self.assertFalse(result['publication_authorized'])
            # LinkedIn, the human-only account this guarded until 13 Nov 2026, is not prepared here at all.
            p.update(channel='linkedin', account_url='https://www.linkedin.com/in/krish-raja/')
            with self.assertRaisesRegex(ValueError, "growth-mindmake's"):
                preflight(p, '2026-10-26')

    def test_approved_brand_content_has_delegated_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            p.update(channel='instagram', account_url='https://www.instagram.com/makeyourmind.up',
                     account_context='publication', proposed_due_at='2026-10-26T18:30:00+00:00',
                     buffer_channel_id=BUFFER_CHANNEL_ID['instagram'])
            result = preflight(p, '2026-10-26')
            self.assertEqual(result['publication_mode'], 'approved_brand_content')
            self.assertNotIn('exact_publication_approval_missing', result['holds'])
            self.assertFalse(result['publication_authorized'])

    def test_x_and_tiktok_have_explicit_delegated_cadence_but_personal_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            for channel, url, count in [('x', 'https://x.com/therealkrisho', 1),
                                        ('tiktok', 'https://www.tiktok.com/@therealkrisho', 2)]:
                p = self.fixture(Path(tmp) / 'asset.bin')
                p.update(channel=channel, account_url=url, format='single-image' if count == 1 else 'carousel',
                         proposed_due_at='2026-10-26T18:45:00+00:00', buffer_channel_id=BUFFER_CHANNEL_ID[channel])
                if count == 2:
                    p['assets'].append(copy.deepcopy(p['assets'][0]))
                    p['assets'][1]['alt_text'] = 'Second frame in the synthetic test sequence.'
                result = preflight(p, '2026-10-26')
                self.assertEqual(result['publication_mode'], 'approved_content_cadence')
                self.assertNotIn('personal_account_human_final_publication_required', result['holds'])
                self.assertFalse(result['publication_authorized'])
                self.assertEqual(route(channel, p['format'], as_of='2026-10-26')['channel']['account_context'], 'personal')

    def test_public_illustration_boilerplate_is_rejected_without_banning_ai_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            for caption in ['The scorecard illustration was generated with AI.',
                            'Scenes are AI-generated editorial illustrations.',
                            'AI-generated illustrations.']:
                p['caption'] = caption
                with self.assertRaisesRegex(ValueError, 'boilerplate'):
                    preflight(p, '2026-10-26')
            p['caption'] = 'AI-generated music changes who gets paid.'
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])

    def test_copy_lint_refuses_eyebrows_asterisks_ai_notes_and_take_labels(self):
        # Krish, 28 Oct 2026: "don't add stupid eyebrow text and asterisks and "generated by AI"
        # and "Krish's take" verbal diahorrea like you tend to."
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            for caption in ['BREAKING: Disney is hiring the team.', 'The *real* cost is the lock-in.',
                            'Disney hires the team. Generated by AI.', "Krish's take: watch the lawyers."]:
                p['caption'] = caption
                with self.assertRaisesRegex(ValueError, 'fails the copy lint'):
                    preflight(p, '2026-10-26')
            p['caption'] = 'Why is Disney eating the scraps of bankrupt Character.AI?'
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])

    def test_his_name_is_refused_in_the_caption_and_the_alt_text(self):
        # Krish, 2026-10-28: "Remember, no content refers to Krish, ever." On his personal accounts
        # too: first person is allowed there, his name in the text never is.
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            for caption in ('A test by Krish Raja on the chip money.', 'More at krishraja.com',
                            'Follow @TheRealKrisho for the next one.'):
                p['caption'] = caption
                with self.assertRaisesRegex(ValueError, 'fails the copy lint: copy lint no_name'):
                    preflight(p, '2026-10-26')
            p['caption'] = 'I ran the test on the chip money. Here is what we found.'
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])
            p['assets'][0]['alt_text'] = 'Krish holding the chart of chip spending.'
            with self.assertRaisesRegex(ValueError, 'asset 1 alt text fails the copy lint: copy lint no_name'):
                preflight(p, '2026-10-26')
            p['assets'][0]['alt_text'] = 'A man holding the chart of chip spending.'
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])

    def test_buffer_package_names_this_engines_pinned_channel_id(self):
        # Plan of 28 Oct 2026, W5: never the Full Time or Heartside channels. The daily draft job
        # saves Buffer drafts through the connector, so preflight holds it to release's table.
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            p.update(channel='instagram', account_url='https://www.instagram.com/makeyourmind.up',
                     account_context='publication', buffer_channel_id=BUFFER_CHANNEL_ID['instagram'])
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])
            for channel_id, why in [('6ae096d32f1f5ed648e99e98', 'Heartside Facebook'),
                                    ('6ae09bba2f1f5ed648e9cbfc', 'fulltime.fm TikTok'),
                                    ('6ae096872f1f5ed648e99b6d', 'yourdoghasnotes Instagram'),
                                    (BUFFER_CHANNEL_ID['facebook'], 'not this engine\'s pinned instagram'),
                                    ('6adccb3a778b240e2fafbb64', 'not this engine\'s pinned instagram'),
                                    (None, 'must be text')]:
                p['buffer_channel_id'] = channel_id
                with self.assertRaisesRegex(ValueError, why):
                    preflight(p, '2026-10-26')
            self.assertEqual(set(DENIED_CHANNELS) & set(BUFFER_CHANNEL_ID.values()), set())
            # The id is part of what an exact approval binds.
            p['buffer_channel_id'] = BUFFER_CHANNEL_ID['instagram']
            digest = package_digest(p)
            del p['buffer_channel_id']
            with self.assertRaisesRegex(ValueError, 'missing buffer_channel_id'):
                preflight(p, '2026-10-26')
            p['buffer_channel_id'] = BUFFER_CHANNEL_ID['facebook']
            self.assertNotEqual(package_digest(p), digest)
            # Substack articles are not a Buffer route: no pinned id, so nothing is saved there.
            p.update(channel='substack', account_url='https://home.makeyourmindup.ai', account_context='publication',
                     format='article', assets=[], buffer_channel_id=BUFFER_CHANNEL_ID['substack-notes'])
            with self.assertRaisesRegex(ValueError, 'not this engine\'s pinned substack channel'):
                preflight(p, '2026-10-26')

    def test_reused_draft_is_edited_only_on_the_pinned_channel(self):
        # edit_post names a postId and no channelId, and the organisation is shared: the daily job reads
        # the draft with get_post and preflight refuses any target that is not this package's own draft.
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            p.update(channel='instagram', account_url='https://www.instagram.com/makeyourmind.up',
                     account_context='publication', buffer_channel_id=BUFFER_CHANNEL_ID['instagram'])
            draft = {'id': 'cccccccccccccccccccccc01', 'channelId': BUFFER_CHANNEL_ID['instagram'],
                     'channelService': 'instagram', 'status': 'draft', 'via': 'api'}
            self.assertEqual(draft_target_errors(p, draft), [])
            self.assertEqual(draft_target_errors(p, {'post': draft}), [], 'the get_post envelope is read too')
            result = preflight(p, '2026-10-26', target=draft)
            self.assertTrue(result['edit_target_checked'])
            self.assertFalse(preflight(p, '2026-10-26')['edit_target_checked'])
            for change, why in [({'channelId': '6ae096d32f1f5ed648e99e98', 'channelService': 'facebook'},
                                 'Heartside Facebook'),
                                ({'channelId': '6ae096872f1f5ed648e99b6d'}, 'yourdoghasnotes Instagram'),
                                ({'channelId': BUFFER_CHANNEL_ID['facebook'], 'channelService': 'facebook'},
                                 "not this engine's pinned instagram"),
                                ({'status': 'scheduled'}, 'not a draft'),
                                ({'via': 'network'}, 'imported from the network'),
                                ({'id': None}, 'not read back with get_post')]:
                target = dict(draft, **change)
                self.assertTrue(any(why in e for e in draft_target_errors(p, target)), change)
                with self.assertRaisesRegex(ValueError, 'edit_post target refused: .*' + why):
                    preflight(p, '2026-10-26', target=target)
            # The command line takes the readback with --target.
            path = Path(tmp) / 'package.json'
            path.write_text(json.dumps(p), encoding='utf-8')
            bad = Path(tmp) / 'target.json'
            bad.write_text(json.dumps(dict(draft, channelId='6ae09bba2f1f5ed648e9cbfc')), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(command(['preflight', str(path), '--as-of', '2026-10-26', '--target', str(bad)]), 1)
            self.assertIn('fulltime.fm TikTok', out.getvalue())

    def test_exact_approval_cannot_survive_caption_time_order_or_metadata_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self.fixture(Path(tmp) / 'asset.bin')
            original.update(channel='instagram', account_url='https://www.instagram.com/makeyourmind.up',
                            account_context='publication', format='carousel',
                            buffer_channel_id=BUFFER_CHANNEL_ID['instagram'])
            second = Path(tmp) / 'other.bin'
            second.write_bytes(b'other accepted asset')
            original['assets'].append({'path': str(second), 'sha256': hashlib.sha256(second.read_bytes()).hexdigest(),
                                       'alt_text': 'Second synthetic asset.'})
            original['publication_approval'] = {'approved': True, 'payload_sha256': package_digest(original),
                                                'evidence_ref': 'synthetic exact approval'}
            self.assertFalse(preflight(original, '2026-10-26')['publication_authorized'])
            for field, value in [('caption', 'Changed copy'), ('proposed_due_at', '2026-10-28T14:00:00+00:00'),
                                 ('assets', list(reversed(original['assets']))),
                                 ('platform_metadata', {**original['platform_metadata'], 'ai_generated': True})]:
                p = copy.deepcopy(original)
                p[field] = value
                with self.assertRaisesRegex(ValueError, 'exact package'):
                    preflight(p, '2026-10-26')

    def test_closed_schema_and_timezone_fail_closed(self):
        schema = json.loads((ROOT / 'social/schemas/package.schema.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            p = self.fixture(Path(tmp) / 'asset.bin')
            p['surprise_publish_flag'] = True
            with self.assertRaises(ValueError):
                validate(p, schema)
            del p['surprise_publish_flag']
            p['proposed_due_at'] = '2026-10-27T14:00:00'
            with self.assertRaisesRegex(ValueError, 'timezone'):
                validate(p, schema)
        with self.assertRaisesRegex(ValueError, 'unsupported schema'):
            validate('anything', {'type': 'string', 'unimplemented': True})


if __name__ == '__main__':
    unittest.main()
