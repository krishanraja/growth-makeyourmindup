"""The AI-tips carousel builder (scripts/ai_tips_deck.py): its checks are the format's standard.

Each rule is shown to fail on a planted week: too few tools, a stale source, a prompt out of sync
with its image, a repeat within four weeks, quote marks round the prompt, a long caption, a series
colour. Synthetic data only: this repository is public. No rendering here.
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ai_tips_deck', ROOT / 'scripts' / 'ai_tips_deck.py')
deck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deck)


def tool(name, logo='claude', checked='2026-11-05'):
    return dict(name=name, logo=logo, url='example.com/' + logo, checked=checked)


def job(n):
    return dict(label='Job %d' % n, headline='Sort the inbox %d' % n, accent='in a minute',
                tools=[tool('Tool %d' % n), tool('Other %d' % n, 'chatgpt')],
                prompt='Sort my inbox by who needs a reply today.',
                steps=['Open your inbox', 'Ask for a sort', 'Reply to the top three'],
                image=dict(file='shots/%02d.png' % n, shows='An inbox sorted by reply', credit='Owner screenshot'))


def week(date='2026-11-05', jobs=5):
    return dict(date=date, jobs=[job(n) for n in range(1, jobs + 1)],
                cover=dict(headline='What could you', accent='hand to AI?', dek='Five jobs to try.',
                           scene=dict(file='covers/scene.png', credit='Generated')),
                close=dict(headline='Pick one job.', accent='Try it this week.', line='Links are in the caption.'),
                caption=dict(intro='Five jobs to hand to AI this week.', outro='Some need a paid plan.'))


class Shape(unittest.TestCase):
    def test_the_example_passes(self):
        self.assertEqual(deck.check_week(week()), [])

    def test_the_committed_week_passes(self):
        w = json.loads((ROOT / 'calendar' / 'ai-tips' / '2026-11-05.json').read_text())
        self.assertEqual(deck.check_week(w), [])
        self.assertEqual(deck.check_caption(deck.caption(w)), [])

    def test_one_tool_fails(self):
        w = week()
        w['jobs'][0]['tools'] = w['jobs'][0]['tools'][:1]
        self.assertTrue(any('tools' in e for e in deck.check_week(w)))

    def test_too_few_jobs_fails(self):
        self.assertTrue(deck.check_week(week(jobs=4)))

    def test_two_steps_fail(self):
        w = week()
        w['jobs'][1]['steps'] = w['jobs'][1]['steps'][:2]
        self.assertTrue(any('three steps' in e for e in deck.check_week(w)))


class Sources(unittest.TestCase):
    def test_stale_check_fails(self):
        w = week()
        w['jobs'][0]['tools'][0]['checked'] = '2026-10-20'
        self.assertTrue(any('checked' in e for e in deck.check_week(w)))

    def test_missing_page_fails(self):
        w = week()
        del w['jobs'][0]['tools'][1]['url']
        self.assertTrue(any('vendor page' in e for e in deck.check_week(w)))


class Sync(unittest.TestCase):
    def test_image_out_of_sync_fails(self):
        w = week()
        w['jobs'][2]['image']['shows'] = 'A spreadsheet chart'
        self.assertTrue(any('out of sync' in e for e in deck.check_week(w)))

    def test_quoted_prompt_fails(self):
        w = week()
        w['jobs'][0]['prompt'] = '"Sort my inbox."'
        self.assertTrue(any('quote marks' in e for e in deck.check_week(w)))

    def test_caption_leads_with_the_tool_in_the_image(self):
        w = week()
        w['jobs'][0]['image']['tool'] = 'Other 1'
        self.assertIn('1. Job 1: Other 1, example.com/chatgpt. Also Tool 1.', deck.caption(w))


class Freshness(unittest.TestCase):
    def test_repeat_within_four_weeks_fails(self):
        self.assertTrue(any('repeat' in e for e in deck.check_week(week(), [week('2026-10-20')])))

    def test_repeat_after_four_weeks_passes(self):
        self.assertEqual(deck.check_week(week(), [week('2026-10-01')]), [])


class Words(unittest.TestCase):
    def test_em_dash_and_series_name_fail(self):
        w = week()
        w['jobs'][0]['headline'] = 'Mind the gap — now'
        errs = deck.check_words(deck.build_jobs(w, '/assets'))
        self.assertTrue(any('series' in e for e in errs))
        self.assertTrue(any('dash' in e for e in errs))

    def test_long_caption_fails(self):
        self.assertTrue(any('2200' in e for e in deck.check_caption('word ' * 500)))


class Paint(unittest.TestCase):
    def test_series_colour_and_off_kit_font_fail(self):
        errs = deck.check_paint([dict(out='01-tip.png', colours=['#0C1512', '#FFD84D'], fonts=['Anton', 'Arial'])])
        self.assertEqual(len(errs), 2)

    def test_jobs_use_the_kit_and_number_the_cards(self):
        jobs = deck.build_jobs(week(), '/assets')
        self.assertEqual([j['out'] for j in jobs][:2], ['00-cover.png', '01-tip.png'])
        self.assertEqual(jobs[1]['fields']['count'], '01 / 05')
        self.assertEqual(jobs[1]['template'], 'piece:ai-tips-screen/tip')
        self.assertEqual(jobs[-1]['out'], '06-close.png')


if __name__ == '__main__':
    unittest.main()
