"""The maker's briefs read Krish's voice profile live from ai-harness (Krish, 2026-10-31: "yes do it all")."""
import unittest

from engine.run import maker, voice_profile

PROFILE = """# Krish voice profile

## Core: what holds everywhere

1. **He leads with the point, often as a verdict.** "Contrarian take" (LinkedIn).
2. **Then he reframes the question.** "So the question isn't" (LinkedIn).

## Channels: one baseline, six branches

| Branch | Speaks as | What changes from the baseline | Source |
|---|---|---|---|
| **LinkedIn** | Krish, first person | "first person and sincere". One emoji for feeling is allowed. | Rulings 1, 3, 5 |
| **Make Your Mind Up articles** | "we", the publication | "more like a professional media channel". His personal habits stay out. | Ruling 5 |

## Rulings (Krish, 31 Oct 2026)
"""


class VoiceProfileTest(unittest.TestCase):
    def test_each_account_gets_its_own_branch_and_only_personal_gets_his_habits(self):
        got = voice_profile.read(lambda url: PROFILE)
        self.assertIn('first person and sincere', got['personal'])
        self.assertIn('He leads with the point', got['personal'])
        self.assertIn('professional media channel', got['publication'])
        self.assertNotIn('He leads with the point', got['publication'])

    def test_the_writer_rules_win_over_the_profile(self):
        got = voice_profile.read(lambda url: PROFILE)
        for text in got.values():
            self.assertTrue(text.endswith(voice_profile.PRECEDENCE))
            self.assertIn('add no fact', text)

    def test_an_unreadable_profile_is_none_never_a_guess(self):
        def broken(url):
            raise OSError('offline')
        self.assertIsNone(voice_profile.read(broken))
        self.assertIsNone(voice_profile.read(lambda url: '# no channel table here'))

    def test_the_brief_carries_the_profile_after_the_account_voice(self):
        slot = {'channel': next(iter(maker.NAMES)), 'format': 'text'}
        concept = {'idea': 'an idea', 'claim': 'a claim.'}
        profile = voice_profile.read(lambda url: PROFILE)
        brief = maker.brief_of(slot, concept, 'personal', [], profile)
        self.assertLess(brief.index(maker.VOICE['personal']), brief.index('From the voice profile'))
        self.assertEqual(maker.brief_of(slot, concept, 'personal', []),
                         maker.brief_of(slot, concept, 'personal', [], None))
        self.assertNotIn('voice profile', maker.brief_of(slot, concept, 'personal', []))


if __name__ == '__main__':
    unittest.main()
