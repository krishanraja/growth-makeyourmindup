"""W2.8: content-engine's piece manifest, one go-live per post, and Pull as his No.

Local stand-ins for Control Center and Buffer only. Every word, id, digest and
byte here is synthetic.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from test_autonomy import CapableStandIn
    from test_run_autorelease import BufferStandIn, fetch, sha
    from test_run_handoff import (Fixture, IMAGE, NOW, P_LINKEDIN, P_THREADS, P_X, RELEASE_NOW, ROOT, WORDS)
except ImportError:  # run as tests.test_piece_manifest
    from tests.test_autonomy import CapableStandIn
    from tests.test_run_autorelease import BufferStandIn, fetch, sha
    from tests.test_run_handoff import (Fixture, IMAGE, NOW, P_LINKEDIN, P_THREADS, P_X, RELEASE_NOW, ROOT, WORDS)

from engine.run import autorelease, handoff, piece_manifest
from engine.run.autorelease import parse_manifest
from engine.run.handoff import GO_LIVE

URL = 'https://drive.example.invalid/synthetic-manifest-download'


def manifest(**change):
    value = {'schema': piece_manifest.SCHEMA, 'piece_id': 'synthetic-piece-2026-11-02',
             'approval_sha256': 'a' * 64, 'qa': {'state': 'passed', 'checked_at': '2026-11-02T10:00:00Z'},
             'assets': [{'name': 'cover.png', 'drive_id': 'SYNTHETICdriveid0001', 'sha256': sha(IMAGE), 'order': 1}],
             'channels': {'threads': {'words': WORDS[P_THREADS], 'alt_text': ['Synthetic alt text'], 'assets': ['cover.png']},
                          'x': {'words': WORDS[P_X], 'alt_text': None, 'assets': []},
                          'linkedin': {'words': WORDS[P_LINKEDIN], 'alt_text': None, 'assets': []}}}
    value.update(change)
    return value


def encoded(value):
    data = json.dumps(value, sort_keys=True).encode('utf-8')
    return data, hashlib.sha256(data).hexdigest()


class ParseTests(unittest.TestCase):
    def test_a_passed_manifest_reads_and_anything_else_is_refused_by_code(self):
        data, digest = encoded(manifest())
        self.assertEqual(piece_manifest.parse(data, digest)['piece_id'], 'synthetic-piece-2026-11-02')
        cases = {'manifest_sha_mismatch': (data, 'b' * 64),
                 'manifest_qa_not_passed': encoded(manifest(qa={'state': 'held', 'checked_at': '2026-11-02T10:00:00Z'})),
                 'manifest_unapproved': encoded(manifest(approval_sha256='not-a-digest')),
                 'manifest_malformed': encoded(dict(manifest(), extra=1)),
                 'manifest_unreadable': (b'', hashlib.sha256(b'').hexdigest())}
        for code, (body, sha256) in cases.items():
            with self.assertRaises(piece_manifest.ManifestRejected) as caught:
                piece_manifest.parse(body, sha256)
            self.assertEqual(caught.exception.code, code)
        bad_channel = manifest()
        bad_channel['channels']['myspace'] = bad_channel['channels']['x']
        with self.assertRaises(piece_manifest.ManifestRejected):
            piece_manifest.parse(*encoded(bad_channel))
        unknown_asset = manifest()
        unknown_asset['channels']['x']['assets'] = ['missing.png']
        with self.assertRaises(piece_manifest.ManifestRejected):
            piece_manifest.parse(*encoded(unknown_asset))

    def test_youtube_long_video_and_short_are_told_apart_by_format(self):
        value = manifest()
        value['channels']['youtube:long-video'] = {'words': 'Synthetic long video words.', 'alt_text': None, 'assets': []}
        value['channels']['youtube:short-video'] = {'words': 'Synthetic short words.', 'alt_text': None, 'assets': []}
        piece_manifest.validate(value)
        long_line = {'channel': 'youtube', 'format': 'long-video', 'words': 'Synthetic long video words.', 'assets': [],
                     'meta': None}
        self.assertIsNone(piece_manifest.line_hold(value, long_line))
        self.assertEqual(piece_manifest.line_hold(value, dict(long_line, format='short-video')), 'manifest_differs')
        self.assertIsNone(piece_manifest.line_hold(value, dict(long_line, format='short-video',
                                                               words='Synthetic short words.')))
        plain = {'channel': 'x', 'format': 'text', 'words': WORDS[P_X], 'assets': [], 'meta': None}
        self.assertIsNone(piece_manifest.line_hold(value, plain), 'a plain channel entry still serves its channel')
        bad = manifest()
        bad['channels']['youtube:Long Video'] = bad['channels']['x']
        with self.assertRaises(piece_manifest.ManifestRejected):
            piece_manifest.validate(bad)

    def test_one_byte_changed_in_a_line_is_held(self):
        value = manifest()
        line = {'channel': 'x', 'words': WORDS[P_X], 'assets': [], 'meta': None}
        self.assertIsNone(piece_manifest.line_hold(value, line))
        self.assertEqual(piece_manifest.line_hold(value, dict(line, words=WORDS[P_X] + '!')), 'manifest_differs')
        self.assertEqual(piece_manifest.line_hold(value, dict(line, channel='tiktok')), 'manifest_has_no_channel')
        image = {'channel': 'threads', 'words': WORDS[P_THREADS], 'assets': [sha(IMAGE)],
                 'meta': {'assets': [{'image': {'sha256': sha(IMAGE), 'metadata': {'altText': 'Synthetic alt text'}}}]}}
        self.assertIsNone(piece_manifest.line_hold(value, image))
        wrong_alt = json.loads(json.dumps(image))
        wrong_alt['meta']['assets'][0]['image']['metadata']['altText'] = 'Other alt text'
        self.assertEqual(piece_manifest.line_hold(value, wrong_alt), 'manifest_differs')
        self.assertEqual(piece_manifest.line_hold(value, dict(image, assets=['c' * 64])), 'manifest_differs')


class HandoffWithManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = CapableStandIn().__enter__()
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.fix = Fixture(self.cc, self.buf)
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'handoff.json'

    def tearDown(self):
        self.tmp.cleanup()

    def run_handoff(self, body, payload=None):
        data, digest = body
        payload = payload or self.fix.payload(piece_manifest={'url': URL, 'sha256': digest})
        return handoff.handoff(GO_LIVE, payload, self.cc.client(), self.buf.client(), NOW, True, fetch, ROOT,
                               self.out, fetch_bytes=lambda url: data)

    def golives(self):
        return [p for r in self.cc.reports.values() for p in r['proposals'] if p.get('stage') == 'go_live']

    def test_drafts_that_match_the_manifest_are_proposed(self):
        summary, code = self.run_handoff(encoded(manifest()))
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'proposed': 3})

    def test_a_draft_edited_away_from_the_manifest_is_held(self):
        value = manifest()
        value['channels']['x']['words'] = WORDS[P_X] + ' Approved on the board in other words.'
        summary, _ = self.run_handoff(encoded(value))
        self.assertEqual(summary['holds'], {'manifest_differs': 1})
        [item] = self.golives()
        self.assertNotIn('x-1', parse_manifest(item['exact_payload']))

    def test_a_manifest_that_is_not_passed_holds_every_slot(self):
        data, digest = encoded(manifest(qa={'state': 'failed', 'checked_at': '2026-11-02T10:00:00Z'}))
        summary, _ = self.run_handoff((data, digest))
        self.assertEqual(summary['holds'], {'manifest_qa_not_passed': 3})
        self.assertEqual(self.golives(), [])

    def test_a_manifest_that_does_not_hash_to_its_sha_holds_every_slot(self):
        data, digest = encoded(manifest())
        summary, _ = self.run_handoff((data + b' ', digest))
        self.assertEqual(summary['holds'], {'manifest_sha_mismatch': 3})

    def test_a_bad_manifest_reference_is_refused_before_any_call(self):
        payload = self.fix.payload(piece_manifest={'url': 'http://insecure.example.invalid/m', 'sha256': 'a' * 64})
        summary, code = self.run_handoff(encoded(manifest()), payload)
        self.assertEqual(summary['error'], 'payload_rejected_bad_piece_manifest_url')
        self.assertEqual(self.cc.posts('reports'), [])

    def test_one_go_live_per_post_and_a_no_on_one_pulls_only_that_post(self):
        """Each post its own go-live (per_item_review); his No on one before its slot is the Pull."""
        for slot in self.fix.slots:
            slot['per_item_review'] = True
        summary, code = self.run_handoff(encoded(manifest()))
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['proposals'], {'go_live': 3})
        by_slot = {next(iter(parse_manifest(p['exact_payload']))): p for p in self.golives()}
        self.assertEqual(sorted(by_slot), ['linkedin-1', 'threads-1', 'x-1'])
        for slot_id, item in by_slot.items():
            verdict = 'declined' if slot_id == 'x-1' else 'approved'
            self.cc.decisions.append(self.fix.decision(item, '2026-11-03T14:30:00Z', decision=verdict))
        with mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02')):
            released, code = autorelease.autorelease(self.cc.client(), self.buf.client(), RELEASE_NOW, True, fetch)
        self.assertEqual(code, 0, released)
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'scheduled')
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft', 'his No pulled this one post')
        self.assertEqual(self.buf.posts[P_LINKEDIN]['status'], 'draft', 'LinkedIn stays his click')

    def test_a_pull_after_the_post_is_scheduled_is_loud_and_never_unscheduled(self):
        for slot in self.fix.slots:
            slot['per_item_review'] = True
        self.run_handoff(encoded(manifest()))
        x = next(p for p in self.golives() if 'x-1' in parse_manifest(p['exact_payload']))
        self.cc.decisions.append(self.fix.decision(x, '2026-11-03T14:30:00Z'))
        with mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02')):
            autorelease.autorelease(self.cc.client(), self.buf.client(), RELEASE_NOW, True, fetch)
            self.assertEqual(self.buf.posts[P_X]['status'], 'scheduled')
            self.cc.decisions.append(self.fix.decision(x, '2026-11-04T13:20:00Z', decision='declined'))
            released, code = autorelease.autorelease(self.cc.client(), self.buf.client(), '2026-11-04T13:25:00Z',
                                                     True, fetch)
        self.assertEqual(code, 1, 'loud: GitHub emails Krish')
        self.assertIn('scheduled_after_decline', json.dumps(released))
        self.assertEqual(self.buf.posts[P_X]['status'], 'scheduled', 'unscheduling is his call')


if __name__ == '__main__':
    unittest.main()
