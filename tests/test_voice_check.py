"""Krish's personal-account words pass Control Center's voice check before Buffer holds them.

Ruling (Krish, 2026-11-07): everything on his personal socials sounds like him; a hard
krish-voice fail holds the draft for one rewrite. Synthetic words only; no network.
"""
import unittest

from engine.control_center import ProtocolError
from engine.run import maker


class CC:
    def __init__(self, hard=None, error=None):
        self.hard, self.error, self.calls = hard or [], error, []

    def voice_check(self, text, channel, subject=None):
        self.calls.append((text, channel))
        if self.error:
            raise ProtocolError(self.error)
        return {'hard': self.hard, 'distance': 0.2}


class VoiceReasonsTests(unittest.TestCase):
    def test_a_personal_post_with_a_hard_fail_is_refused_with_the_rule(self):
        cc = CC(hard=[{'rule': 'us_spellings', 'message': 'US spelling "organize". Krish writes British: "organise".'}])
        found = maker.voice_reasons(cc, 'personal', 'x', 'We organize it.')
        self.assertEqual(found, ['US spelling "organize". Krish writes British: "organise".'])
        self.assertEqual(cc.calls, [('We organize it.', 'x')])

    def test_each_channel_is_checked_as_its_own_account(self):
        cc = CC()
        for ch in ('x', 'linkedin', 'threads', 'substack-notes', 'tiktok', 'instagram', 'facebook', 'youtube', 'substack'):
            maker.voice_reasons(cc, 'any', ch, 'Words.')
        self.assertEqual([c[1] for c in cc.calls],
                         ['x', 'linkedin', 'threads', 'substack_note', 'instagram', 'caption', 'caption', 'caption', 'substack'])

    def test_the_publication_is_checked_too_absolutely_everything(self):
        cc = CC(hard=[{'rule': 'publication:exclamation', 'message': "Make Your Mind Up's canon (exclamation)."}])
        self.assertEqual(maker.voice_reasons(cc, 'publication', 'instagram', 'Big news!'), ["Make Your Mind Up's canon (exclamation)."])

    def test_a_verdict_the_check_cannot_give_is_none_never_a_pass_of_a_broken_rule(self):
        self.assertIsNone(maker.voice_reasons(CC(error='not_found'), 'personal', 'x', 'Words.'))

    def test_the_hold_code_is_voice_refused_after_the_copy_lint(self):
        slot = {'channel': 'x', 'format': 'single_image'}
        concept = {'claim': 'A claim.'}
        names = [n for n, _ in maker.word_checks(slot, concept, 'A claim. More.', '', ['a broken rule'])]
        self.assertIn('voice_refused', names)


if __name__ == '__main__':
    unittest.main()
