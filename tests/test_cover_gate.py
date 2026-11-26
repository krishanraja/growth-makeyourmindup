"""Every video goes out with its designed cover (Ruling, Krish, 2026-11-15; F133).

His words: "the thumbnail is ridiculously poor, and that must never be the case." A Buffer reel went out with
thumbnailOffset null and showed frame 0, an AI scene. Content-engine makes the cover and bakes it into the cut
(Ruling, Krish, 2026-11-26); Growth keeps only the release gate (engine/run/cover_gate.py). Every value is synthetic.
"""
import unittest

from engine.engines import publishing
from engine.run import cover_gate, piece_manifest, release
from engine.social import inventory



class CoverRulesTests(unittest.TestCase):
    def call(self, channel, metadata):
        body = {'url': 'https://example.invalid/cut.mp4'}
        if metadata is not None:
            body['metadata'] = metadata
        return [{'video': body}]

    def test_a_video_with_no_offset_is_refused_on_every_cover_channel(self):
        for channel in cover_gate.COVER_CHANNELS:
            errors = release.cover_errors(channel, self.call(channel, None))
            self.assertTrue(errors and errors[0].startswith('video_without_designed_cover'), channel)
            self.assertTrue(release.cover_errors(channel, self.call(channel, {'thumbnailOffset': None})))
            self.assertEqual(release.cover_errors(channel, self.call(channel, {'thumbnailOffset': 61500})), [])

    def test_pictures_and_text_need_no_cover_frame(self):
        self.assertEqual(release.cover_errors('instagram', [{'image': {'url': 'https://example.invalid/a.png'}}]), [])
        self.assertEqual(release.cover_errors('substack-notes', self.call('substack-notes', None)), [])

    def test_the_slot_digest_binds_the_cover_frame_only_when_one_is_set(self):
        slot = {'channel': 'instagram', 'format': 'short-video', 'words': 'w', 'link_placement': None,
                'due_at': None, 'publish_mode': 'engine', 'meta': None, 'buffer_channel_id': None,
                'assets': [{'name': 'cut.mp4', 'sha256': 'a' * 64, 'url': None, 'bytes': 1}]}
        before = release.slot_digest(slot)
        slot['assets'][0]['cover_offset_ms'] = 61500
        with_cover = release.slot_digest(slot)
        slot['assets'][0]['cover_offset_ms'] = 0
        self.assertNotEqual(before, with_cover)
        self.assertNotEqual(with_cover, release.slot_digest(slot))
        del slot['assets'][0]['cover_offset_ms']
        self.assertEqual(before, release.slot_digest(slot), 'a digest signed before covers is unchanged')

    def test_a_built_video_call_carries_its_slot_cover_frame(self):
        asset = {'name': 'cut.mp4', 'sha256': 'a' * 64, 'url': 'https://example.invalid/cut.mp4', 'bytes': 1,
                 'cover_offset_ms': 61500}
        self.assertEqual(release._asset_input(asset, {}), {'video': {'url': asset['url'],
                                                                     'metadata': {'thumbnailOffset': 61500}}})
        stored = {('cover', asset['url']): 1000}
        with self.assertRaisesRegex(ValueError, 'cover_offset_mismatch'):
            release._asset_input(asset, stored)
        self.assertEqual(release._asset_input(dict(asset, cover_offset_ms=1000), stored)['video']['metadata'],
                         {'thumbnailOffset': 1000})

    def test_every_video_route_closes_against_its_cover(self):
        for channel, fmt in (('instagram', 'short-video'), ('tiktok', 'short-video'), ('youtube', 'short-video'),
                             ('youtube', 'long-video'), ('facebook', 'short-video'), ('threads', 'short-video'),
                             ('x', 'short-video')):
            checks = publishing.applicable_checks(channel, fmt)
            self.assertTrue({'grid_cover', 'player_cover'} & set(checks), (channel, fmt))

    def test_every_buffer_video_capability_says_how_its_cover_is_set(self):
        for cap in inventory()['tool']['buffer']['capabilities']:
            if cap['format'] in ('short-video', 'long-video') and cap['channel'] in cover_gate.COVER_CHANNELS:
                self.assertIn('thumbnailOffset', cap.get('cover', ''), cap)


class ManifestCoverTests(unittest.TestCase):
    def manifest(self, offset=61500):
        return {'schema': piece_manifest.SCHEMA, 'piece_id': 'synthetic-piece', 'approval_sha256': 'a' * 64,
                'qa': {'state': 'passed', 'checked_at': '2026-11-15T10:00:00Z'},
                'assets': [{'name': 'cut.mp4', 'drive_id': 'SYNTHETICdriveid0001', 'sha256': 'b' * 64, 'order': 1},
                           {'name': 'cover.png', 'drive_id': 'SYNTHETICdriveid0002', 'sha256': 'c' * 64, 'order': 2}],
                'channels': {'instagram': {'words': 'Synthetic words.', 'alt_text': None, 'assets': ['cut.mp4'],
                                           'cover': {'asset': 'cover.png', 'sha256': 'c' * 64,
                                                     'cover_offset_ms': offset}}}}

    def line(self, offset):
        return {'channel': 'instagram', 'format': 'short-video', 'words': 'Synthetic words.', 'assets': ['b' * 64],
                'meta': {'assets': [{'video': {'sha256': 'b' * 64, 'metadata': {'thumbnailOffset': offset}}}]}}

    def test_a_cover_field_is_read_and_checked(self):
        value = piece_manifest.validate(self.manifest())
        self.assertEqual(piece_manifest.cover_for(value, 'instagram')['asset'], 'cover.png')
        self.assertIsNone(piece_manifest.line_hold(value, self.line(61500)))
        self.assertEqual(piece_manifest.line_hold(value, self.line(0)), 'cover_offset_mismatch')
        self.assertEqual(piece_manifest.line_hold(value, self.line(None)), 'video_without_cover_offset')
        no_frame = piece_manifest.validate(self.manifest(offset=None))
        self.assertIsNone(piece_manifest.line_hold(no_frame, self.line(3)))
        self.assertEqual(piece_manifest.line_hold(no_frame, self.line(None)), 'video_without_cover_offset')

    def test_a_cover_naming_no_asset_is_malformed(self):
        bad = self.manifest()
        bad['channels']['instagram']['cover']['asset'] = 'missing.png'
        with self.assertRaisesRegex(piece_manifest.ManifestRejected, 'manifest_malformed'):
            piece_manifest.validate(bad)


class GateTests(unittest.TestCase):
    def test_an_offset_is_a_whole_number_of_milliseconds_never_null(self):
        self.assertTrue(cover_gate.offset_ok(0))
        self.assertTrue(cover_gate.offset_ok(61500))
        for bad in (None, -1, True, 1.5, '61500'):
            self.assertFalse(cover_gate.offset_ok(bad), bad)

    def test_only_a_video_on_a_cover_channel_needs_its_cover(self):
        self.assertTrue(cover_gate.needs_cover('instagram', ('video',)))
        self.assertTrue(cover_gate.needs_cover('twitter', ('video',)))
        self.assertFalse(cover_gate.needs_cover('instagram', ('image',)))
        self.assertFalse(cover_gate.needs_cover('substack-notes', ('video',)))
