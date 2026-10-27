"""The V1 posting calendar (calendar/v1.json) and growth.py run calendar lint. Synthetic only."""
import contextlib
import copy
import io
import json
import unittest

from engine.run import cli
from engine.run.calendar import CALENDAR, WEEKDAYS, lint, resolve, timezone_errors
from engine.run.invariants import ROOT, load_authority
from engine.social import inventory


def v1():
    return json.loads(CALENDAR.read_text(encoding='utf-8'))


def codes(calendar):
    return {e['code'] for e in lint(calendar)['errors']}


def row(calendar, row_id):
    return next(r for r in calendar['wave'] + calendar['weekly'] if r['id'] == row_id)


class CalendarTests(unittest.TestCase):
    def test_v1_calendar_lints_clean_and_meets_its_floors(self):
        calendar = v1()
        result = lint(calendar)
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['valid'])
        self.assertEqual(calendar['preview_until'], load_authority()['show_before_post_until'])
        self.assertEqual([p['series'] for p in calendar['pieces']],
                         ['follow.the.money', 'under.the.hood', 'mind.the.gap'])
        self.assertEqual([p['weekday'] for p in calendar['pieces']], ['MO', 'WE', 'FR'])
        for day in WEEKDAYS:
            counts = result['week'][day]
            self.assertEqual(counts['substack-notes'], 2, day)
            self.assertGreaterEqual(counts['threads'], 1, day)
            self.assertGreaterEqual(counts['x'], 1, day)
        self.assertEqual(sum(c.get('linkedin', 0) for c in result['week'].values()), 4)
        # Threads and X take 1 a day under their records; the calendar's "up to 2" is held for Krish.
        self.assertEqual(len(result['held']), 2)
        self.assertTrue(all('waits for Krish' in h for h in result['held']))

    def test_every_row_is_in_the_lane_authority_gives_it(self):
        calendar = v1()
        everything = calendar['wave'] + calendar['weekly']
        for r in everything:
            if r['channel'] == 'linkedin':
                self.assertEqual((r['lane'], r['at'], r['producer']), ('L3_hands', 'draft', 'words'))
            if r['class'] in ('carousel', 'meme', 'scorecard', 'poll'):
                self.assertEqual(r['lane'], 'L2_eyes', r['id'])
        self.assertEqual({row(calendar, i)['lane'] for i in ('note-quote', 'receipt-x', 'short-tiktok',
                                                             'story-hook-instagram')}, {'L1_judgement'})
        self.assertEqual(row(calendar, 'carousel-instagram')['format'], 'carousel')
        for channel in ('instagram', 'facebook'):
            self.assertEqual(row(calendar, 'carousel-' + channel)['days'], [0, 0])

    def test_a_wrong_lane_is_refused(self):
        for row_id, lane, expected in (('linkedin-mo', 'L1_judgement', {'lane', 'linkedin_not_l3', 'draft_timing',
                                                                        'new_format_not_eyes'}),
                                       ('carousel-instagram', 'L1_judgement', {'lane', 'new_format_not_eyes'}),
                                       ('meme-tiktok-tu', 'L1_judgement', {'lane', 'new_format_not_eyes'}),
                                       ('receipt-x', 'L2_eyes', {'lane'})):
            calendar = v1()
            row(calendar, row_id)['lane'] = lane
            self.assertEqual(codes(calendar), expected, row_id)

    def test_formats_producers_and_templates_must_exist(self):
        calendar = v1()
        row(calendar, 'receipt-x')['format'] = 'hologram'
        self.assertIn('unknown_format', codes(calendar))
        calendar = v1()
        row(calendar, 'meme-instagram-tu')['format'] = 'hologram'  # a declared new format may be ahead of its record
        self.assertNotIn('unknown_format', codes(calendar))
        calendar = v1()
        row(calendar, 'short-youtube')['format'] = 'note'
        self.assertIn('format_not_allowed', codes(calendar))
        calendar = v1()
        row(calendar, 'receipt-x').update(producer='content-engine', template=None)
        self.assertIn('producer', codes(calendar))
        calendar = v1()
        row(calendar, 'receipt-x')['template'] = 'story-hook'
        self.assertIn('template_size', codes(calendar))
        calendar = v1()
        calendar['templates']['note-image'] = 'billboard'
        self.assertIn('template', codes(calendar))
        calendar = v1()
        row(calendar, 'poll-result-x')['requires'] = 'nothing-here'
        self.assertIn('requires', codes(calendar))

    def test_floors_and_caps_are_checked_on_the_resolved_week(self):
        calendar = v1()
        calendar['wave'] = [r for r in calendar['wave'] if r['id'] != 'recut-x']
        self.assertIn('x has 0 on TU, below its floor of 1', [e['message'] for e in lint(calendar)['errors']])
        calendar = v1()
        extra = dict(row(calendar, 'linkedin-mo'), id='linkedin-th', weekday='TH')
        calendar['weekly'].append(extra)
        self.assertIn('cap', codes(calendar))
        calendar = v1()
        calendar['weekly'].append(dict(row(calendar, 'meme-instagram-tu'), id='meme-x-mo', channel='x',
                                       weekday='MO', template='meme-square', priority=1))
        self.assertIn('day0_bumped', codes(calendar))  # X takes one a day; a day-0 receipt must never be cut
        calendar = v1()
        calendar['memes']['max'] = 2
        self.assertIn('memes', codes(calendar))
        calendar = v1()
        calendar['wave'] = [r for r in calendar['wave'] if r['id'] != 'story-proof-facebook']
        self.assertIn('stories', codes(calendar))
        calendar = v1()
        calendar['floors'][0]['min'] = 3
        self.assertIn('floor_over_cap', codes(calendar))

    def test_caps_are_quoted_from_the_corpus(self):
        calendar = v1()
        sources = {c['channel']: c['source_file'] for c in calendar['caps']}
        self.assertEqual(sources['substack-notes'], 'social/guides/other-channels.md')
        records = inventory()['channel']
        for name in ('x', 'threads', 'instagram', 'facebook', 'tiktok', 'youtube'):
            self.assertEqual(records[name]['daily_posts_target'], 1, name)
        calendar['caps'][0]['quote'] = 'Approved Notes, up to nine a day as signed'
        self.assertIn('cap_quote', codes(calendar))
        calendar = v1()
        calendar['caps'][0]['source_file'] = '../outside.md'
        self.assertIn('cap_source', codes(calendar))

    def test_a_result_card_runs_only_after_its_poll(self):
        kept, bumped = resolve(v1(), inventory()['channel'])
        ran = {(k['piece'], k['row']['id']) for k in kept}
        for item in kept:
            if item['row']['requires']:
                self.assertIn((item['piece'], item['row']['requires']), ran)
        self.assertTrue(any(b['why'] == 'requires' for b in bumped))
        self.assertTrue(all(b['priority'] > 1 for b in bumped))

    def test_timezone_and_preview_date_are_checked(self):
        self.assertEqual(timezone_errors('America/New_York'), [])
        self.assertTrue(timezone_errors('Europe/London'))
        self.assertTrue(timezone_errors('Mars/Olympus_Mons'))
        calendar = v1()
        calendar['tz'] = 'Mars/Olympus_Mons'
        self.assertIn('timezone', codes(calendar))
        calendar = v1()
        calendar['preview_until'] = '2026-11-15'
        self.assertIn('preview_until', codes(calendar))
        calendar = v1()
        calendar['surprise'] = True
        self.assertEqual(codes(calendar), {'schema'})

    def test_calendar_lint_is_a_run_route(self):
        self.assertEqual(cli.ROUTES['calendar'], 'calendar')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(['calendar', 'lint']), 0)
        self.assertTrue(json.loads(out.getvalue())['valid'])
        self.assertTrue((ROOT / 'specs' / 'schema' / 'calendar.schema.json').is_file())


if __name__ == '__main__':
    unittest.main()
