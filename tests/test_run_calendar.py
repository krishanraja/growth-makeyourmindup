"""The V1 posting calendar (calendar/v1.json) and growth.py run calendar lint. Synthetic only."""
import contextlib
import copy
import io
import json
import unittest

from engine import intensity
from engine.run import cli
from engine.run.calendar import CALENDAR, WEEKDAYS, daily_caps, lint, resolve, timezone_errors
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
        # Threads takes 1 a day under its record, so the calendar's "up to 2" is held for Krish. X takes
        # four a day since main's 29 Oct ruling (R102), so its "up to 2" fits and is not held.
        self.assertEqual(len(result['held']), 1)
        self.assertIn('threads', result['held'][0])
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
                                                             'story-hook-instagram')}, {'L0_code'})
        self.assertEqual(row(calendar, 'carousel-instagram')['format'], 'carousel')
        for channel in ('instagram', 'facebook'):
            self.assertEqual(row(calendar, 'carousel-' + channel)['days'], [0, 0])

    def test_a_wrong_lane_is_refused(self):
        for row_id, lane, expected in (('linkedin-mo', 'L0_code', {'lane', 'linkedin_not_l3', 'draft_timing',
                                                                   'new_format_not_eyes'}),
                                       ('carousel-instagram', 'L0_code', {'lane', 'new_format_not_eyes'}),
                                       ('meme-tiktok-tu', 'L0_code', {'lane', 'new_format_not_eyes'}),
                                       ('receipt-x', 'L2_eyes', {'lane'}),
                                       # No L1: there are no Claude routines (Krish, 29 Oct 2026).
                                       ('receipt-x', 'L1_judgement', {'schema'})):
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
        calendar['weekly'].append(dict(row(calendar, 'meme-instagram-tu'), id='meme-threads-mo', channel='threads',
                                       weekday='MO', template='meme-square', priority=1))
        # Threads takes one a day; a day-0 receipt must never be cut (X takes four since R102).
        self.assertIn('day0_bumped', codes(calendar))
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
        self.assertEqual(sources['linkedin'], 'docs/plans/2026-10-27-engine-architecture.md')
        records = inventory()['channel']
        for name in ('threads', 'facebook'):
            self.assertEqual(records[name]['daily_posts_target'], 1, name)
        for name in ('x', 'instagram', 'tiktok', 'youtube'):
            # Main's 29 Oct ruling (R102): four a day with a floor of three on the concept channels.
            self.assertEqual((records[name]['daily_posts_target'], records[name]['daily_posts_floor']), (4, 3), name)
        calendar['caps'][0]['quote'] = 'LinkedIn at most nine a week'
        self.assertIn('cap_quote', codes(calendar))
        calendar = v1()
        calendar['caps'][0]['source_file'] = '../outside.md'
        self.assertIn('cap_source', codes(calendar))

    def test_daily_caps_come_only_from_the_channel_records_and_intensity(self):
        # Main's merge: social/channels and intensity.json are the one home for a daily cap.
        # The calendar plans its own volume (a floor's max) and defers: it never restates a cap.
        calendar = v1()
        self.assertEqual([c for c in calendar['caps'] if c['per'] == 'day'], [])
        records = inventory()['channel']
        for urgency in (None, 1, 4):
            expected = {n: intensity.daily_cap(r, urgency) for n, r in records.items()
                        if intensity.daily_cap(r, urgency) is not None}
            self.assertEqual(daily_caps(calendar, records, urgency), expected, urgency)
        calendar['caps'].append({'channel': 'x', 'per': 'day', 'max': 4, 'source_file': 'docs/LANES.md',
                                 'quote': 'There are no Claude routines (Krish, 29 Oct 2026)'})
        self.assertIn('daily_cap_restated', codes(calendar))
        # A floor's max above the cap holds for Krish; it never raises or lowers the cap.
        calendar = v1()
        calendar['floors'][1]['max'] = 4
        result = lint(calendar)
        self.assertTrue(result['valid'], result['errors'])
        self.assertIn('threads: the calendar allows 4 a day, but the cap is 1', ' '.join(result['held']))
        calendar['floors'][0]['max'] = 1
        self.assertEqual(daily_caps(calendar, records)['substack-notes'], 2)

    def test_a_result_card_runs_only_after_its_poll(self):
        # On a channel taking one a day a poll can be bumped and its result card must drop with it. X took one
        # a day until main's 29 Oct ruling (R102: four); the rule is proved on a record kept at one.
        records = copy.deepcopy(inventory()['channel'])
        records['x']['daily_posts_target'] = 1
        records['x']['daily_posts_floor'] = None
        kept, bumped = resolve(v1(), records)
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
