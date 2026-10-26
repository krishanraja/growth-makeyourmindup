"""Offline regression gates for reusable social procedures and exact packages."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from engine.social import ROOT, inventory, package_digest, preflight, route, validate


class SocialContractsTests(unittest.TestCase):
    def test_registry_and_known_channel_routes(self):
        records = inventory()
        self.assertEqual(set(records['channel']), {'instagram', 'linkedin', 'x', 'tiktok', 'youtube', 'substack'})
        ig = route('instagram', 'carousel', as_of='2026-10-26')
        self.assertEqual(ig['holds'], [])
        self.assertEqual(ig['channel']['account_context'], 'publication')
        self.assertFalse(ig['publication_authorized'])
        self.assertIn('clipboard-image-upload', [x['id'] for x in ig['lessons']])
        li = route('linkedin', 'single-image', as_of='2026-10-26')
        self.assertEqual(li['channel']['account_context'], 'personal')
        self.assertEqual(li['holds'], [])

    def test_unknown_document_route_is_not_inferred_from_png_success(self):
        result = route('linkedin', 'carousel', as_of='2026-10-26')
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
                'channel': 'linkedin', 'account_url': 'https://www.linkedin.com/in/krish-raja/',
                'account_context': 'personal', 'format': 'single-image', 'tool': 'buffer',
                'source_url': 'https://example.com/verified-test', 'caption': 'Synthetic test copy.',
                'assets': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'alt_text': 'Synthetic regression asset.'}],
                'production': {'owner': 'content-engine', 'approved': True, 'evidence_ref': 'synthetic-only'},
                'voice_review_passed': True, 'proposed_due_at': '2026-10-27T14:00:00+00:00',
                'platform_metadata': {'ai_generated': None, 'share_to_feed': None,
                                      'post_type': None, 'link_preview_url': None},
                'publication_approval': {'approved': False, 'payload_sha256': None, 'evidence_ref': None}}

    def test_missing_approval_survives_valid_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = preflight(self.fixture(Path(tmp) / 'asset.bin'), '2026-10-26')
            self.assertTrue(result['structurally_valid'])
            self.assertIn('exact_publication_approval_missing', result['holds'])
            self.assertFalse(result['publication_authorized'])

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

    def test_exact_approval_cannot_survive_caption_time_order_or_metadata_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self.fixture(Path(tmp) / 'asset.bin')
            original.update(channel='instagram', account_url='https://www.instagram.com/makeyourmind.up',
                            account_context='publication', format='carousel')
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
