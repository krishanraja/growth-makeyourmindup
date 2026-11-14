"""His approved floor from the directive (audit 2026-11-14, I-14), read tolerantly behind features.taste_floor.
Synthetic standards only."""
import unittest

from engine import cc_loop


def std(n, standing='approved', formats=(), statement=None):
    return {'id': 's' + str(n), 'layer': 'copy', 'formats': list(formats),
            'statement': statement if statement is not None else 'TEST FIXTURE ONLY standard ' + str(n),
            'how_to_check': None, 'his_words': None, 'standing': standing, 'support_n': 1}


def directive(standards, flag=True, venture='publication', voice=None):
    taste = {'floor': {'rule': 'TEST FIXTURE ONLY.', 'venture': venture, 'as_of': '2026-11-14', 'standards': standards}}
    if voice is not None:
        taste['approved_voice_rules'] = voice
    return {'directive': {'features': {cc_loop.FLOOR_FEATURE: flag}, 'taste': taste}}


class TasteFloorTests(unittest.TestCase):
    def test_only_behind_its_flag_and_only_this_venture(self):
        # Control Center names this venture 'publication' (lane D, control-center #815); the slug is accepted too.
        self.assertEqual(cc_loop.taste_floor(directive([std(1)], venture='makeyourmindup'))[0], 'standards')
        self.assertEqual(cc_loop.taste_floor(directive([std(1)], venture=None))[0], 'standards')
        self.assertEqual(cc_loop.taste_floor(directive([std(1)], flag=False))[0], 'absent')
        self.assertEqual(cc_loop.taste_floor(directive([std(1)], venture='heartside'))[0], 'absent')
        self.assertEqual(cc_loop.taste_floor(directive([std(1)]))[0], 'standards')
        self.assertEqual(cc_loop.taste_floor(None)[0], 'absent')

    def test_drafts_and_malformed_standards_never_reach_the_maker_and_at_most_forty(self):
        rows = [std(1, standing='draft'), std(2, statement=' '), 'junk'] + [std(n) for n in range(3, 50)]
        state, _, standards = cc_loop.taste_floor(directive(rows))
        self.assertEqual((state, len(standards), standards[0]['id']), ('standards', cc_loop.FLOOR_MAX, 's3'))
        self.assertEqual(cc_loop.taste_floor(directive([std(1, standing='draft')]))[0], 'none')

    def test_the_ledger_formats_map_onto_the_makers_formats(self):
        d = directive([std(1, formats=['carousel']), std(2, formats=['card']), std(3, formats=['short_video']),
                       std(4, formats=['all']), std(5, formats=['captions']), std(6, formats=['thumbnail'])])
        def ids(fmt):
            return [line[-1] for line in cc_loop.never_beneath(d, fmt)]
        self.assertEqual(ids('carousel'), ['1', '2', '4', '5'])
        self.assertEqual(ids('short-video'), ['3', '4', '5', '6'])
        self.assertEqual(ids('text'), ['4', '5'])
        self.assertEqual(ids('a-format-nobody-knows'), ['4', '5'])

    def test_never_beneath_matches_the_format_and_carries_the_voice_rules(self):
        d = directive([std(1, formats=['Carousel']), std(2, formats=['short']), std(3)],
                      voice=[{'layer': 'copy', 'rule': 'TEST FIXTURE ONLY voice', 'his_words': 'TEST FIXTURE ONLY words'}])
        lines = cc_loop.never_beneath(d, 'carousel')
        self.assertEqual(lines, ['TEST FIXTURE ONLY voice', 'TEST FIXTURE ONLY standard 1', 'TEST FIXTURE ONLY standard 3'])
        self.assertNotIn('TEST FIXTURE ONLY words', ' '.join(lines))

    def test_taste_state_says_read_none_or_absent(self):
        self.assertEqual(cc_loop.taste_state(directive([std(1)])), 'read')
        self.assertEqual(cc_loop.taste_state(directive([], voice=[])), 'none')
        self.assertEqual(cc_loop.taste_state(directive([std(1)], flag=False)), 'absent')
        self.assertEqual(cc_loop.taste_state(None), 'absent')
