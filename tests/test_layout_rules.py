"""Content-engine's judges see the cards (Ruling, Krish, 2026-11-15). Every value here is synthetic.

The layout checks that lived here (kit layout, cover distinctness, the tall clear box) left with Growth's renderer:
content-engine's v5 Library checks every layout at make time (Ruling, Krish, 2026-11-26).
"""
import unittest

from engine.run import judges


class JudgesSeeTheCards(unittest.TestCase):
    class Board:
        def __init__(self):
            self.bodies = []

        def judge(self, monday, body):
            self.bodies.append(body)
            return {'verdict': 'pass', 'artifact_sha256': judges.artifact_sha256(
                {'format': body['format'], 'channel': body['channel']}, body['words'], body['assets'])}

    def test_every_picture_goes_with_its_view_link_and_a_blind_ask_holds(self):
        slot = {'slot_id': 's1', 'format': 'carousel', 'channel': 'instagram'}
        assets = [{'name': 'mock-1.png', 'sha256': 'a' * 64, 'view_url': 'https://drive.example.invalid/1'}]
        board = self.Board()
        judges.judge(board, '2026-11-16', slot, {}, 'Synthetic words.', assets)
        self.assertEqual(board.bodies[0]['assets'][0]['view_url'], 'https://drive.example.invalid/1')
        with self.assertRaisesRegex(judges.JudgesHeld, 'judges_cannot_see'):
            judges.judge(board, '2026-11-16', slot, {}, 'Synthetic words.', [{'name': 'm.png', 'sha256': 'a' * 64}])
        self.assertEqual(len(board.bodies), 1, 'a blind ask is never sent')
