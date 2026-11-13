"""Which Buffer channel each post is on, so an edit (which names only its post) is gated by its channel.

Ruling (Krish, 2026-11-13): growth-mindmake owns his personal LinkedIn; this engine never edits a post there.
The map is filled from the answers to get_post, list_posts and create_post, and seeded from this engine's release
ledgers. Synthetic ids only; no Buffer call is made.
"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import post_channels
from engine.buffer_channels import BUFFER_CHANNEL_ID, HANDED_OFF_CHANNELS
from engine.run import release

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'release'
NOW = '2026-11-01T12:00:00-05:00'

LINKEDIN = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
X, THREADS = BUFFER_CHANNEL_ID['x'], BUFFER_CHANNEL_ID['threads']
P1, P2, P3 = 'b' * 23 + '1', 'b' * 23 + '2', 'b' * 23 + '3'


class Answers(unittest.TestCase):
    def test_each_answer_shape_gives_its_posts_channels(self):
        # get_post as a plain post, with its channel as an id or as an object.
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1},
                                                 {'id': P1, 'channelId': LINKEDIN, 'text': 'Words.'}), [(P1, LINKEDIN)])
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1},
                                                 {'post': {'id': P1, 'channel': {'id': LINKEDIN, 'service': 'linkedin'}}}),
                         [(P1, LINKEDIN)])
        # An MCP answer as content blocks of JSON text.
        blocks = [{'type': 'text', 'text': json.dumps({'id': P1, 'channelId': X})}]
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1}, blocks), [(P1, X)])
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1}, json.dumps(blocks)), [(P1, X)])
        # get_post that answers with the channel and not the post's own id is the post asked for.
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1}, {'channelId': LINKEDIN}),
                         [(P1, LINKEDIN)])
        # list_posts, as a list or a GraphQL connection.
        listed = {'posts': {'edges': [{'node': {'id': P1, 'channelId': LINKEDIN}}, {'node': {'id': P2, 'channelId': X}}]}}
        self.assertEqual(sorted(post_channels.from_call('mcp__Buffer__list_posts', {}, listed)),
                         [(P1, LINKEDIN), (P2, X)])
        # create_post that answers with the new id only is on the channel the call named.
        self.assertEqual(post_channels.from_call('mcp__Buffer__create_post', {'channelId': THREADS},
                                                 {'post': {'id': P3, 'status': 'draft'}}), [(P3, THREADS)])
        # Any other tool, or an answer naming no post, gives nothing.
        self.assertEqual(post_channels.from_call('mcp__Buffer__edit_post', {'postId': P1}, {'id': P1, 'channelId': X}), [])
        self.assertEqual(post_channels.from_call('mcp__Buffer__get_post', {'postId': P1}, 'not found'), [])

    def test_the_map_keeps_ids_only_newest_last_and_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(post_channels.record(root, [(P1, LINKEDIN), (P2, X), ('not an id', X)]), 2)
            self.assertEqual(post_channels.record(root, [(P1, LINKEDIN)]), 0)
            self.assertEqual(post_channels.record(root, [(P2, THREADS)]), 1)
            stored = json.loads((root / post_channels.MAP).read_text(encoding='utf-8'))
            self.assertEqual(stored, {'schema': post_channels.SCHEMA, 'posts': {P1: LINKEDIN, P2: THREADS}})
            self.assertEqual(post_channels.known(root), {P1: LINKEDIN, P2: THREADS})
        ignored = (Path(__file__).resolve().parents[1] / '.gitignore').read_text(encoding='utf-8').split()
        self.assertEqual(post_channels.MAP.parts[0], '.scratch')
        self.assertIn('.scratch/', ignored)

    def test_the_release_ledger_as_release_writes_it_seeds_the_map(self):
        # The fixture is written by the real writer (engine/run/release.py: plan, then the queued readback), never by
        # hand, so the seed reads the shape the ledger really has. The L0 handoff's output is not a seed: it carries a
        # draft's channel only inside a go-live's exact payload text, and an unmapped post's edit waits for get_post.
        self.assertEqual([seed[1] for seed in post_channels.SEEDS], ['*/ledger.json'])
        with tempfile.TemporaryDirectory() as tmp:
            root, assets = Path(tmp) / 'repo', Path(tmp) / 'assets'
            root.mkdir()
            assets.mkdir()
            for n in range(1, 6):
                (assets / ('frame-' + str(n) + '.png')).write_bytes(
                    ('synthetic release fixture frame ' + str(n) + '\n').encode())
            unverified = {'holds': ['capability_not_verified_for_selected_channel_and_format']}
            with patch.object(release, 'route', lambda *a, **k: dict(unverified)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(release.main(['plan', str(FIX / 'spec.json'), '--decision', str(FIX / 'decision.json'),
                                               '--assets', str(assets), '--channels', str(FIX / 'channels.json'),
                                               '--targets', str(FIX / 'targets.json'), '--now', NOW], root), 0)
                self.assertEqual(release.main(['check', str(FIX / 'spec.json'), '--readback',
                                               str(FIX / 'readback-queued.json'), '--stage', 'queued', '--now', NOW],
                                              root), 0)
            [path] = (root / '.scratch' / 'runs').glob('*/ledger.json')
            released = json.loads(path.read_text(encoding='utf-8'))['released']
            written = {e['post_id']: e['channel_id'] for e in released.values() if e.get('post_id')}
            self.assertTrue(written)
            self.assertEqual(written[json.loads((FIX / 'readback-queued.json').read_text(encoding='utf-8'))
                                     ['threads-1']['id']], THREADS)
            self.assertEqual(post_channels.seeded(root), written)
            # A ledger that cannot be read adds nothing.
            broken = root / '.scratch' / 'runs' / 'broken' / 'ledger.json'
            broken.parent.mkdir()
            broken.write_text('{not json', encoding='utf-8')
            self.assertEqual(post_channels.seeded(root), written)
            # What the hook read is the newest reading and wins.
            post, _ = next(iter(written.items()))
            post_channels.record(root, [(post, LINKEDIN)])
            self.assertEqual(post_channels.known(root), dict(written, **{post: LINKEDIN}))

if __name__ == '__main__':
    unittest.main()
