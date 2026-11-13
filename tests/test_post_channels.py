"""Which Buffer channel each post is on, so an edit (which names only its post) is gated by its channel.

Ruling (Krish, 2026-11-13): growth-mindmake owns his personal LinkedIn; this engine never edits a post there.
The map is filled from the answers to get_post, list_posts and create_post, and seeded from this engine's own
ledgers. Synthetic ids only; no Buffer call is made.
"""
import json
from pathlib import Path
import tempfile
import unittest

from engine import post_channels
from engine.buffer_channels import BUFFER_CHANNEL_ID, HANDED_OFF_CHANNELS

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

    def test_its_own_ledgers_seed_the_map(self):
        # The release run's ledger and the handoff's output already pair a post with its channel.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / '.scratch' / 'runs' / 'run-1'
            run.mkdir(parents=True)
            (run / 'ledger.json').write_text(json.dumps({'run_id': 'run-1', 'released': {
                'x-1': {'channel': 'x', 'channel_id': X, 'post_id': P1}}}), encoding='utf-8')
            cc = root / '.scratch' / 'cc'
            cc.mkdir(parents=True)
            (cc / 'handoff-go_live.json').write_text(json.dumps({'reports': [{'proposals': [{'lines': [
                {'buffer_draft_id': P2, 'buffer_channel_id': LINKEDIN}]}]}]}), encoding='utf-8')
            (cc / 'handoff-broken.json').write_text('{not json', encoding='utf-8')
            self.assertEqual(post_channels.seeded(root), {P1: X, P2: LINKEDIN})
            # What the hook read is the newest reading and wins.
            post_channels.record(root, [(P1, THREADS)])
            self.assertEqual(post_channels.known(root), {P1: THREADS, P2: LINKEDIN})


if __name__ == '__main__':
    unittest.main()
