"""North Star attribution, urgency and What-Works verdicts on synthetic fixtures."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.run.measure import (AWAITS, FAILS_AT_OR_BELOW, LEDGER, MIN_HISTORY, ROOT, WORKS_AT_OR_ABOVE,
                                classify, current_state, followers_daily, judge, main, north_star, northstar,
                                paid_week, read_ledger, state_line, urgency, validate_capture, verdict,
                                week_target, write_now)

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'measure'
NOW = '2026-11-05T00:00:00Z'
SYNTHETIC_STAR = '''# North Star

## The number

```yaml north-star-metric
metric: "Synthetic subscribers a week, zero paid"  # a comment
unit: count
direction: up
target: 100
deadline: 2026-11-16
ladder_shape: front-loaded
source: "Synthetic source"
status: active
ladder:
  - [2026-10-26, 10]
  - [2026-11-02, 20]
  - [2026-11-09, 50]
  - [2026-11-16, 100]
```
'''
SYNTHETIC_NOW = ('# Synthetic\r\n\r\n## Where it is right now (as of 2026-10-27)\r\n\r\n'
                 '<!-- north-star-state {"week_of": "2026-10-26", "week_target": 10, "current": 0, '
                 '"current_as_of": "2026-10-27", "current_source": "synthetic", "urgency": 4, '
                 '"urgency_reason": "0 of 10; under two fifths"} --> **North Star number: U4, far behind.** Old.\r\n'
                 '\r\nLater text mentions <!-- north-star-state only inline.\r\n')


def capture_on(day, start=None, rows=(), total=0):
    """A settled synthetic capture read at 20:00 New York time on day."""
    capture = load('capture-settled.json')
    capture.update(captured_at=day + 'T20:00:00-05:00', rows=[dict(r) for r in rows], total_new_free=total)
    capture['window'].update(start=start or day, end=day)
    return capture


def star_root(tmp, star=SYNTHETIC_STAR, now=SYNTHETIC_NOW):
    (Path(tmp) / 'docs').mkdir()
    (Path(tmp) / 'docs' / 'NORTH_STAR.md').write_text(star, encoding='utf-8')
    (Path(tmp) / 'NOW.md').write_bytes(now.encode('utf-8'))


def run_northstar(tmp, capture, day, *extra):
    """Run the northstar command on a temp root; return (exit code, printed text)."""
    path = Path(tmp) / 'capture.json'
    path.write_text(json.dumps(capture), encoding='utf-8')
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(['northstar', '--capture', str(path), '--today', day, '--root', str(tmp),
                     '--now', '2027-02-01T00:00:00Z'] + list(extra))
    return code, out.getvalue()


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


class SourcesTests(unittest.TestCase):
    def test_growth_sources_read_must_be_settled(self):
        validate_capture(load('capture-settled.json'), NOW)
        with self.assertRaisesRegex(ValueError, 'F54'):
            validate_capture(load('capture-unsettled.json'), NOW)
        moved = load('capture-settled.json')
        moved['settled']['label_seen'] = '90 days'  # the old table under the new label
        with self.assertRaisesRegex(ValueError, 'F54'):
            validate_capture(moved, NOW)
        bad = []
        for change in (lambda c: c.update(captured_at='2026-11-06T00:00:00Z'),
                       lambda c: c.update(source_url='http://example.substack.com/x'),
                       lambda c: c.update(total_new_free=8),
                       lambda c: c['rows'][0].update(new_free=-1),
                       lambda c: c['rows'][0].update(new_paid=True),
                       lambda c: c['window'].update(tz='UTC'),
                       lambda c: c['window'].update(end='2026-11-05'),
                       lambda c: c.update(extra=1)):
            capture = load('capture-settled.json')
            change(capture)
            with self.assertRaises(ValueError):
                validate_capture(capture, NOW)
            bad.append(capture)
        self.assertEqual(len(bad), 8)

    def test_organic_only_with_approved_sources(self):
        capture = validate_capture(load('capture-settled.json'), NOW)
        for path in ('missing-sources.json', FIXTURES / 'sources-unapproved.json'):
            result = classify(capture, path, FIXTURES)
            self.assertEqual(result['all_source'], {'value': 7, 'reason': None})
            for name in ('organic', 'unattributed', 'paid'):
                self.assertIsNone(result[name]['value'])
                self.assertEqual(result[name]['reason'], AWAITS)
        known = copy.deepcopy(capture)
        known['rows'] = [r for r in known['rows'] if r['source'] != 'Synthetic Mystery']
        known['total_new_free'] = 6
        result = classify(known, FIXTURES / 'sources-approved.json')
        self.assertEqual((result['organic']['value'], result['unattributed']['value'], result['paid']['value']), (4, 2, 0))
        self.assertTrue(result['approved'])
        self.assertEqual(paid_week(capture), {'value': 1, 'reason': None, 'window_start': '2026-11-02',
                                              'window_end': '2026-11-04'})
        capture['rows'][1]['new_paid'] = None
        self.assertIsNone(paid_week(capture)['value'])
        capture.update(rows=[], total_new_free=0)
        self.assertEqual(paid_week(capture)['value'], 0)  # an empty table under a zero total

    def test_unknown_source_labels_are_listed(self):
        capture = validate_capture(load('capture-settled.json'), NOW)
        result = classify(capture, FIXTURES / 'sources-approved.json')
        self.assertEqual(result['unknown_labels'], ['Synthetic Mystery'])
        self.assertIsNone(result['organic']['value'])
        self.assertIn('Synthetic Mystery', result['organic']['reason'])
        capture['rows'][2]['new_free'] = 0
        capture['total_new_free'] = 6
        result = classify(capture, FIXTURES / 'sources-approved.json')
        self.assertEqual(result['unknown_labels'], ['Synthetic Mystery'])
        self.assertEqual(result['organic']['value'], 4)  # an unknown zero cannot change any count

    def test_classify_reads_repo_sources_json(self):
        # The committed map keeps lower-case labels under "categories"; the page shows "Direct".
        capture = validate_capture(load('capture-settled.json'), NOW)
        capture['rows'] = [{'source': 'Direct', 'new_free': 3, 'new_paid': 0},
                           {'source': 'Substack Notes', 'new_free': 2, 'new_paid': 1},
                           {'source': 'Synthetic Mystery', 'new_free': 0, 'new_paid': 0}]
        capture['total_new_free'] = 5
        repo = json.loads((ROOT / 'invariants' / 'sources.json').read_text(encoding='utf-8'))
        self.assertIn('categories', repo)
        for result in (classify(capture), classify(capture, 'invariants/sources.json', ROOT)):
            self.assertEqual(result['all_source'], {'value': 5, 'reason': None})
            self.assertEqual(result['unknown_labels'], ['Synthetic Mystery'])
            self.assertIsNone(result['organic']['value'])
            self.assertEqual(result['organic']['reason'], AWAITS)
            self.assertEqual(result['approved'], repo['approved'])
        if repo['approved'] is not True:
            with tempfile.TemporaryDirectory() as tmp:
                approved = dict(repo, approved=True, approved_by='Synthetic approver', approved_at='2026-10-27')
                path = Path(tmp) / 'sources.json'
                path.write_text(json.dumps(approved), encoding='utf-8')
                capture['rows'][0]['source'] = ' DIRECT '
                result = classify(capture, path)
                self.assertEqual((result['organic']['value'], result['unattributed']['value']), (2, 3))
                path.write_text(json.dumps({'approved': True, 'sources': {'direct': 'unattributed'}}), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'categories'):
                    classify(capture, path)
                path.write_text(json.dumps(dict(repo, approved_by='Someone')), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'names no approver'):
                    classify(capture, path)
                path.write_text(json.dumps(dict(approved, categories={'Direct': 'organic', 'direct': 'unattributed'})),
                                encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'classified twice'):
                    classify(capture, path)

    def test_followers_per_channel_per_day(self):
        def snap(day, value, captured='T23:00:00-05:00', availability='available'):
            return {'platform': 'threads', 'source': 'https://example.com/insights', 'scope': 'synthetic',
                    'metric': 'followers', 'unit': 'accounts', 'window_kind': 'snapshot', 'timezone': 'America/New_York',
                    'start': day + 'T20:00:00-05:00', 'end': day + 'T20:00:00-05:00', 'captured_at': day + captured,
                    'availability': availability, 'value': value if availability == 'available' else None,
                    'reason': None if availability == 'available' else 'signed_out'}
        rows = followers_daily([snap('2026-11-02', 10), snap('2026-11-03', 13), snap('2026-11-03', 12, 'T22:00:00-05:00'),
                                snap('2026-11-05', 15), snap('2026-11-06', None, availability='signed_out')])
        days = rows[0]['days']
        self.assertEqual([d['net_change'] for d in days], [None, 3, None, None])
        self.assertEqual(days[1]['value'], 13)
        self.assertEqual(days[3]['reason'], 'signed_out')


class NorthStarTests(unittest.TestCase):
    def test_ladder_parses_without_yaml(self):
        # Krish owns the real ladder, so only its shape is checked here.
        metric = north_star()
        ladder = metric['ladder']
        self.assertTrue(ladder)
        self.assertEqual([d for d, _ in ladder], sorted(set(d for d, _ in ladder)))
        self.assertTrue(all(d.weekday() == 0 and isinstance(v, int) and v > 0 for d, v in ladder))
        self.assertEqual(week_target(ladder[0][0], metric), ladder[0][1])
        with self.assertRaises(ValueError):
            week_target(ladder[0][0] + dt.timedelta(days=1), metric)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'NORTH_STAR.md'
            path.write_text(SYNTHETIC_STAR, encoding='utf-8')
            metric = north_star(path)
            self.assertEqual(metric['metric'], 'Synthetic subscribers a week, zero paid')
            self.assertEqual(week_target('2026-11-09', metric), 50)
            path.write_text(SYNTHETIC_STAR.replace('[2026-11-09, 50]', '[2026-11-10, 50]'), encoding='utf-8')
            with self.assertRaises(ValueError):
                north_star(path)
            # The contract's own example: a key whose value is only a comment.
            path.write_text(SYNTHETIC_STAR.replace('ladder:\n', 'ladder:               # one row per week\n')
                            .replace('ladder_shape: front-loaded', 'ladder_shape:   # front-loaded'), encoding='utf-8')
            metric = north_star(path)
            self.assertEqual((len(metric['ladder']), metric['ladder_shape']), (4, None))

    def test_urgency_levels_follow_the_contract(self):
        day = '2026-11-04'
        cases = [(20, 1), (25, 1), (15, 2), (19, 2), (8, 3), (14, 3), (7, 4), (0, 4)]
        for current, level in cases:
            result = urgency(current, 20, day, day)
            self.assertEqual(result['urgency'], level, current)
        self.assertEqual(urgency(15, 20, day, day)['urgency_reason'], '15 of 20; at least three quarters')
        self.assertEqual(urgency(7, 20, day, day)['label'], 'far behind')
        # No movement for 14 days, and past the deadline off target, both stall.
        flat = [{'week_of': '2026-10-19', 'week_target': 4, 'current': 3, 'current_as_of': '2026-10-21'},
                {'week_of': '2026-10-26', 'week_target': 4, 'current': 3, 'current_as_of': '2026-10-28'}]
        self.assertEqual(urgency(3, 4, day, day, flat)['urgency'], 5)
        self.assertEqual(urgency(3, 4, day, day, flat[1:])['urgency'], 2)
        self.assertEqual(urgency(10, 20, '2026-11-23', '2026-11-23', deadline='2026-11-16')['urgency'], 5)
        self.assertEqual(urgency(20, 20, '2026-11-23', '2026-11-23', deadline='2026-11-16')['urgency'], 1)
        with self.assertRaises(ValueError):
            urgency(1, 20, '2026-11-05', day)

    def test_unmeasured_is_u4(self):
        result = urgency(None, 25, None, '2026-10-27')
        self.assertEqual((result['urgency'], result['label'], result['urgency_reason']), (4, 'far behind', 'not measured yet'))

    def test_stale_reading_is_u4(self):
        self.assertEqual(urgency(30, 25, '2026-10-20', '2026-10-27')['urgency'], 1)
        result = urgency(30, 25, '2026-10-19', '2026-10-27')
        self.assertEqual(result['urgency'], 4)
        self.assertIn('more than 7 days old', result['urgency_reason'])

    def test_two_weeks_under_two_fifths_is_u5(self):
        last = [{'week_of': '2026-10-26', 'week_target': 25, 'current': 9, 'current_as_of': '2026-11-01'}]
        result = urgency(10, 86, '2026-11-04', '2026-11-04', last)
        self.assertEqual((result['urgency'], result['label']), (5, 'stalled'))
        self.assertEqual(result['urgency_reason'], '10 of 86; under two fifths two weeks running')
        last[0]['current'] = 10  # exactly two fifths last week is not under
        self.assertEqual(urgency(10, 86, '2026-11-04', '2026-11-04', last)['urgency'], 4)

    def test_state_line_format(self):
        line = state_line('2026-10-26', 25, 0, '2026-10-27', 'synthetic source', 4, '0 of 25; under two fifths')
        self.assertEqual(line, '<!-- north-star-state {"week_of": "2026-10-26", "week_target": 25, "current": 0, '
                               '"current_as_of": "2026-10-27", "current_source": "synthetic source", "urgency": 4, '
                               '"urgency_reason": "0 of 25; under two fifths"} --> **North Star number: U4, far behind.** '
                               '0 of 25 new publication subscribers this week from organic posts and shares, '
                               'read on 27 October 2026.')
        self.assertIn('not measured yet', state_line('2026-10-26', 1312, None, None, None, 4, 'not measured yet'))
        for reason, sentence in (('0 of 25; under 40%', None), ('fine', 'A ' + chr(0x2014) + ' dash.'), ('ten per cent', None)):
            with self.assertRaises(ValueError):
                state_line('2026-10-26', 25, 0, '2026-10-27', 'synthetic', 4, reason, sentence)

    def test_write_now_replaces_only_the_state_line(self):
        line = state_line('2026-11-02', 20, 3, '2026-11-04', 'synthetic', 4, '3 of 20; under two fifths')
        with tempfile.TemporaryDirectory() as tmp:
            now = Path(tmp) / 'NOW.md'
            now.write_bytes(SYNTHETIC_NOW.encode('utf-8'))
            diff = write_now(tmp, line)
            self.assertEqual(now.read_bytes(), SYNTHETIC_NOW.encode('utf-8'), 'the default only shows a diff')
            self.assertEqual([x for x in diff.splitlines() if x[:1] in '+-' and x[:3] not in ('+++', '---')],
                             ['-' + SYNTHETIC_NOW.splitlines()[4], '+' + line])
            write_now(tmp, line, write=True)
            before, after = SYNTHETIC_NOW.encode('utf-8').split(b'\r\n'), now.read_bytes().split(b'\r\n')
            self.assertEqual(len(before), len(after))
            self.assertEqual([i for i, (a, b) in enumerate(zip(before, after)) if a != b], [4])
            self.assertEqual(after[4].decode('utf-8'), line)
            self.assertEqual(write_now(tmp, line), '')
            for broken in (SYNTHETIC_NOW.replace('## Where it is right now', '## Elsewhere'),
                           SYNTHETIC_NOW.replace('\r\n\r\n<!-- north', '\r\n\r\nInterloper.\r\n<!-- north'),
                           SYNTHETIC_NOW + '<!-- north-star-state {} -->\r\n'):
                now.write_bytes(broken.encode('utf-8'))
                with self.assertRaises(ValueError):
                    write_now(tmp, line, write=True)
                self.assertEqual(now.read_bytes(), broken.encode('utf-8'))
            with self.assertRaises(ValueError):
                write_now(tmp, 'not a state line')
            # The real NOW.md keeps the structure the writer needs; checked on a copy.
            shutil.copyfile(ROOT / 'NOW.md', now)
            original = now.read_bytes()
            self.assertTrue(write_now(tmp, line))
            self.assertEqual(now.read_bytes(), original)
            self.assertEqual(current_state(ROOT)['week_of'], current_state(tmp)['week_of'])

    def test_northstar_counts_organic_and_bounds_with_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'docs').mkdir()
            (Path(tmp) / 'docs' / 'NORTH_STAR.md').write_text(SYNTHETIC_STAR, encoding='utf-8')
            (Path(tmp) / 'NOW.md').write_bytes(SYNTHETIC_NOW.encode('utf-8'))
            capture = load('capture-settled.json')
            result = northstar(capture, '2026-11-04', tmp, FIXTURES / 'sources-approved.json', [], NOW)
            self.assertIsNone(json.loads(result['line'].split(' ', 2)[2].split(' -->')[0])['current'])
            self.assertEqual(result['urgency']['urgency'], 4)
            self.assertIn('1 unknown source label needs classification', result['line'])
            self.assertNotIn('Synthetic Mystery', result['line'])  # page text stays out of the state line
            capture['rows'] = []
            capture['total_new_free'] = 0
            result = northstar(capture, '2026-11-04', tmp, 'invariants/sources.json', [], NOW)
            state = json.loads(result['line'][len('<!-- north-star-state '):result['line'].index(' -->')])
            self.assertEqual((state['current'], state['week_target'], state['urgency']), (0, 20, 4))
            history = Path(tmp) / 'history.json'
            history.write_text('[]', encoding='utf-8')
            capture_file = Path(tmp) / 'capture.json'
            old = load('capture-settled.json')
            old.update(captured_at='2026-10-27T20:00:00-04:00', rows=[], total_new_free=0)
            old['window'].update(start='2026-10-21', end='2026-10-27')
            capture_file.write_text(json.dumps(old), encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['northstar', '--capture', str(capture_file), '--today', '2026-10-27',
                                       '--root', tmp, '--history', str(history), '--now', NOW]), 0)
            self.assertIn('not written', out.getvalue())
            self.assertEqual((Path(tmp) / 'NOW.md').read_bytes(), SYNTHETIC_NOW.encode('utf-8'))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['northstar', '--capture', str(capture_file), '--today', '2026-10-27',
                                       '--root', tmp, '--write', '--now', NOW]), 0)
            self.assertEqual(current_state(tmp)['current_as_of'], '2026-10-27')
            self.assertIn('U4, far behind', (Path(tmp) / 'NOW.md').read_text(encoding='utf-8'))
            self.assertEqual(read_ledger(tmp), [current_state(tmp)])

    def test_u5_holds_for_the_rest_of_the_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            star_root(tmp)  # last week: 0 of 10, under two fifths
            for day in ('2026-11-02', '2026-11-03', '2026-11-04'):
                code, text = run_northstar(tmp, capture_on(day, '2026-10-27'), day, '--write')
                self.assertEqual(code, 0, text)
                self.assertEqual((current_state(tmp)['urgency'], current_state(tmp)['urgency_reason']),
                                 (5, '0 of 20; under two fifths two weeks running'), day)
            self.assertEqual(len(read_ledger(tmp)), 3)
            # Without the ledger, the stall NOW.md already shows still holds for the week.
            (Path(tmp) / LEDGER).unlink()
            code, text = run_northstar(tmp, capture_on('2026-11-05', '2026-10-30'), '2026-11-05', '--write')
            self.assertEqual((code, current_state(tmp)['urgency']), (0, 5), text)
        held = [{'week_of': '2026-11-02', 'week_target': 20, 'current': 0, 'current_as_of': '2026-11-02',
                 'urgency': 5, 'urgency_reason': '0 of 20; under two fifths two weeks running'}]
        self.assertEqual(urgency(1, 20, '2026-11-03', '2026-11-03', held)['urgency'], 5)
        self.assertEqual(urgency(8, 20, '2026-11-03', '2026-11-03', held)['urgency'], 3)  # no longer under
        held[0]['urgency_reason'] = '0 of 20; no movement for 14 days'
        self.assertEqual(urgency(0, 20, '2026-11-04', '2026-11-04', held)['urgency'], 5)
        self.assertEqual(urgency(1, 20, '2026-11-04', '2026-11-04', held)['urgency'], 4)  # it moved

    def test_no_movement_for_14_days_from_daily_runs(self):
        star = SYNTHETIC_STAR.replace('[2026-11-02, 20]', '[2026-11-02, 10]').replace('[2026-11-09, 50]', '[2026-11-09, 10]')
        start = SYNTHETIC_NOW.replace('"week_of": "2026-10-26", "week_target": 10, "current": 0, "current_as_of": "2026-10-27"',
                                      '"week_of": "2026-10-19", "week_target": 10, "current": null, "current_as_of": null')
        organic = [{'source': 'Synthetic Notes', 'new_free': 5, 'new_paid': 0}]
        with tempfile.TemporaryDirectory() as tmp:
            star_root(tmp, star, start)
            shutil.copyfile(FIXTURES / 'sources-approved.json', Path(tmp) / 'sources.json')
            seen = []
            for offset in range(15):
                day = (dt.date(2026, 10, 26) + dt.timedelta(days=offset)).isoformat()
                monday = (dt.date(2026, 10, 26) + dt.timedelta(days=offset - offset % 7)).isoformat()
                code, text = run_northstar(tmp, capture_on(day, monday, organic, 5), day, '--write',
                                           '--sources', 'sources.json')
                self.assertEqual(code, 0, text)
                seen.append(current_state(tmp)['urgency'])
            self.assertEqual(seen[:14], [3] * 14)  # 5 of 10 each day, inside the fortnight
            self.assertEqual((seen[14], current_state(tmp)['urgency_reason']), (5, '5 of 10; no movement for 14 days'))

    def test_past_the_deadline_off_target_is_u5(self):
        with tempfile.TemporaryDirectory() as tmp:
            star_root(tmp)  # deadline week of 16 November, last ladder row 100
            result = northstar(capture_on('2026-11-24', '2026-11-17'), '2026-11-24', tmp, 'invariants/sources.json',
                               [], '2026-11-26T00:00:00Z')
            self.assertEqual((result['week_target'], result['urgency']['urgency']), (100, 5))
            self.assertTrue(result['urgency']['urgency_reason'].startswith('0 of 100; past the deadline'))
            code, text = run_northstar(tmp, capture_on('2026-11-24', '2026-11-17'), '2026-11-24')
            self.assertEqual(code, 0, text)
            self.assertIn('U5, stalled', text)
            paused = SYNTHETIC_STAR.replace('status: active', 'status: paused')
            (Path(tmp) / 'docs' / 'NORTH_STAR.md').write_text(paused, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'paused'):
                northstar(capture_on('2026-11-24', '2026-11-17'), '2026-11-24', tmp, now='2026-11-26T00:00:00Z')

    def test_unmeasured_capture_never_replaces_a_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            star_root(tmp)  # NOW.md holds 0 of 10 read on 27 October
            before = (Path(tmp) / 'NOW.md').read_bytes()
            uncounted = capture_on('2026-10-28', '2026-10-22', [{'source': 'Synthetic Notes', 'new_free': 2,
                                                                  'new_paid': 0}], 2)
            for flags in ((), ('--write',)):
                code, text = run_northstar(tmp, uncounted, '2026-10-28', *flags)
                self.assertEqual(code, 1, text)
                self.assertIn('does not count', json.loads(text)['error'])
                self.assertIn('27 October 2026 for this week stays', json.loads(text)['error'])
                self.assertEqual((Path(tmp) / 'NOW.md').read_bytes(), before)
            self.assertFalse((Path(tmp) / LEDGER).exists())
            # Next week an unmeasured reading may stand: last week's reading is not this week's.
            code, text = run_northstar(tmp, capture_on('2026-11-03', '2026-10-28', [{'source': 'Synthetic Notes',
                                                                                    'new_free': 2, 'new_paid': 0}], 2),
                                       '2026-11-03', '--write')
            self.assertEqual(code, 0, text)
            self.assertIsNone(current_state(tmp)['current'])

    def test_older_capture_never_replaces_a_newer_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            star_root(tmp)
            code, text = run_northstar(tmp, capture_on('2026-11-04', '2026-10-29'), '2026-11-04', '--write')
            self.assertEqual((code, current_state(tmp)['current_as_of']), (0, '2026-11-04'), text)
            after = (Path(tmp) / 'NOW.md').read_bytes()
            code, text = run_northstar(tmp, capture_on('2026-11-03', '2026-10-28'), '2026-11-04', '--write')
            self.assertEqual(code, 1, text)
            self.assertIn('older than the reading of 4 November 2026', text)
            code, text = run_northstar(tmp, capture_on('2026-10-29', '2026-10-23'), '2026-10-29', '--write')
            self.assertEqual(code, 1, text)
            self.assertIn('earlier week', text)
            self.assertEqual((Path(tmp) / 'NOW.md').read_bytes(), after)
            self.assertEqual(len(read_ledger(tmp)), 1)


class VerdictTests(unittest.TestCase):
    def test_verdict_insufficient_below_six_or_before_window(self):
        case = load('verdict.json')
        self.assertEqual(MIN_HISTORY, 6)
        self.assertEqual(verdict(case['post'], case['history'][:5], 48, 50), 'insufficient')
        # Another channel's history never makes up the count.
        self.assertEqual(verdict(case['post'], case['history'][:5] + case['history'][6:], 48, 50), 'insufficient')
        self.assertEqual(verdict(case['post'], case['history'], 48, 47.5), 'insufficient')
        self.assertEqual(judge(case['post'], case['history'], 48, 47.5)['reason'], 'the judge window has not elapsed')

    def test_verdict_bands(self):
        case = load('verdict.json')
        self.assertEqual((WORKS_AT_OR_ABOVE, FAILS_AT_OR_BELOW), (1.5, 0.5))
        result = judge(case['post'], case['history'], 48, 50)
        self.assertEqual((result['median'], result['observations']), (5.0, 6))
        self.assertEqual(result['verdict'], 'works')  # 9 against a median of 5
        for value, expected in ((7.5, 'works'), (7, 'neutral'), (3, 'neutral'), (2.5, 'fails'), (0, 'fails')):
            post = dict(case['post'], value=value)
            self.assertEqual(verdict(post, case['history'], 48, 50), expected, value)
        self.assertIn('proposed', result['bands']['status'])
        with self.assertRaises(ValueError):
            verdict(dict(case['post'], value=-1), case['history'], 48, 50)
        for history in ([None] * 6, 'not a list'):
            with self.assertRaises(ValueError):
                verdict(case['post'], history, 48, 50)
        zeros = [dict(r, value=0) for r in case['history']]
        self.assertEqual(judge(dict(case['post'], value=3), zeros, 48, 50)['verdict'], 'insufficient')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['verdict', str(FIXTURES / 'verdict.json')]), 0)
        self.assertEqual(json.loads(out.getvalue())['verdict'], 'works')

    def test_sources_command_reports_both_counts(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['measure', 'sources', str(FIXTURES / 'capture-unsettled.json'), '--now', NOW]), 1)
        self.assertIn('F54', out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['measure', 'sources', str(FIXTURES / 'capture-settled.json'), '--now', NOW,
                                   '--sources', str(FIXTURES / 'sources-approved.json')]), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result['classification']['all_source']['value'], 7)
        self.assertEqual(result['classification']['unknown_labels'], ['Synthetic Mystery'])
        self.assertEqual(result['paid_subscribers']['value'], 1)


if __name__ == '__main__':
    unittest.main()
