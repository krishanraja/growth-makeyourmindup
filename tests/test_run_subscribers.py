"""The weekly Substack subscriber read (jobs/subscribers.md) on synthetic fixtures.

Ruling (Krish, 2026-11-12): the engine reads subscribers every week and judges posts by subscribers, not
engagement. Every figure, label and URL here is invented.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from engine.core import read_json
from engine.run import subscribers
from engine.run.measure import current_state, read_ledger

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'measure'
APPROVED = FIXTURES / 'sources-approved.json'
NOW = '2026-11-16T12:00:00Z'  # a Monday morning in New York
STAR = '''# North Star

```yaml north-star-metric
metric: "Synthetic subscribers a week, zero paid"
unit: count
direction: up
target: 100
deadline: 2026-11-30
ladder_shape: front-loaded
source: "Synthetic source"
status: active
ladder:
  - [2026-11-02, 20]
  - [2026-11-09, 50]
  - [2026-11-16, 80]
  - [2026-11-23, 100]
```
'''
NOW_MD = ('# Synthetic\n\n## Where it is right now (as of 2026-11-05)\n\n'
          '<!-- north-star-state {"week_of": "2026-11-02", "week_target": 20, "current": 1, '
          '"current_as_of": "2026-11-05", "current_source": "synthetic", "urgency": 5, '
          '"urgency_reason": "1 of 20; under two fifths two weeks running"} --> **North Star number: U5, stalled.** Old.\n'
          '\nMore text.\n')


def root(tmp):
    (Path(tmp) / 'docs').mkdir()
    (Path(tmp) / 'docs' / 'NORTH_STAR.md').write_text(STAR, encoding='utf-8')
    (Path(tmp) / 'NOW.md').write_text(NOW_MD, encoding='utf-8')
    return Path(tmp)


def sources(start='2026-11-09', end='2026-11-15', rows=None, total=7):
    rows = [{'source': 'Synthetic Notes', 'new_free': 5, 'new_paid': 1},
            {'source': 'Synthetic Direct', 'new_free': 2, 'new_paid': 0}] if rows is None else rows
    return {'kind': 'substack_growth_sources', 'captured_at': '2026-11-16T06:20:00-05:00',
            'source_url': 'https://synthetic.substack.com/publish/stats/subscribers',
            'window': {'label': 'Custom', 'start': start, 'end': end, 'tz': 'America/New_York'},
            'settled': {'label_seen': 'Custom', 'values_seen_after_label': True},
            'metric': 'new_subscribers', 'rows': rows, 'total_new_free': total}


def taken(**changes):
    capture = {'kind': 'substack_subscribers_weekly', 'week_of': '2026-11-09',
               'captured_at': '2026-11-16T06:25:00-05:00', 'read': 'taken', 'not_taken': None,
               'growth_sources': sources(),
               'total_subscribers': {'value': 321, 'free': 300, 'paid': 21, 'reason': None,
                                     'source_url': 'https://synthetic.substack.com/publish/subscribers'},
               'items_view': 'per_item',
               'items': [{'kind': 'note', 'url': 'https://substack.com/@synthetic/note/c-1',
                          'window_label': 'All time', 'new_free': 2, 'new_paid': 0},
                         {'kind': 'post', 'url': 'https://home.makeyourmindup.ai/p/synthetic-piece',
                          'window_label': 'All time', 'new_free': 0, 'new_paid': 0},
                         {'kind': 'note', 'url': 'https://substack.com/@synthetic/note/c-2',
                          'window_label': 'All time', 'new_free': None, 'new_paid': None}]}
    capture.update(changes)
    return capture


def missed(code='signed_out'):
    return taken(read='not_taken', not_taken={'code': code, 'detail': None}, growth_sources=None,
                 total_subscribers=None, items_view='not_checked', items=[])


def run(argv, tmp):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = subscribers.main(argv + ['--root', str(tmp)], out=print, root=tmp)
    return code, out.getvalue()


class TemplateTests(unittest.TestCase):
    def test_template_is_last_week_and_stays_private(self):
        self.assertEqual(subscribers.template(NOW)['week_of'], '2026-11-09')
        self.assertEqual(subscribers.template('2026-11-15T23:00:00-05:00')['week_of'], '2026-11-02')  # still Sunday
        with tempfile.TemporaryDirectory() as tmp:
            code, text = run(['template', '--now', NOW], root(tmp))
            self.assertEqual(code, 0, text)
            path = Path(tmp) / '.scratch' / 'substack' / 'week-2026-11-09.json'
            self.assertEqual(read_json(path)['read'], 'not_taken')
            code, text = run(['template', '--now', NOW], tmp)
            self.assertEqual(code, 1)
            self.assertIn('never overwritten', text)
            code, text = run(['template', '--now', NOW, '--out', str(Path(tmp) / 'lists' / 'x.json')], tmp)
            self.assertEqual(code, 1)
            self.assertIn('out of the public repository', text)


class ValidateTests(unittest.TestCase):
    def test_the_capture_is_closed_and_never_guesses(self):
        subscribers.validate(taken(), NOW)
        subscribers.validate(missed(), NOW)
        bad = (
            (lambda c: c.update(extra=1), 'exactly'),
            (lambda c: c.update(week_of='2026-11-10'), 'Monday'),
            (lambda c: c.update(captured_at='2026-11-17T06:25:00-05:00'), 'future'),
            (lambda c: c.update(read='maybe'), 'taken or not_taken'),
            (lambda c: c['growth_sources']['settled'].update(values_seen_after_label=False), 'F54'),
            (lambda c: c.update(items_view='category_only'), 'per post or per Note'),
            (lambda c: c['items'][0].update(url='https://example.com/x'), 'on Substack itself'),
            (lambda c: c['items'].append(dict(c['items'][0])), 'once'),
            (lambda c: c['total_subscribers'].update(reason='not shown'), 'not both'),
            (lambda c: c['total_subscribers'].update(value=-1), 'non-negative'),
        )
        for change, message in bad:
            capture = taken()
            change(capture)
            with self.assertRaisesRegex(ValueError, message):
                subscribers.validate(capture, NOW)
        guessed = missed()
        guessed['growth_sources'] = sources()
        with self.assertRaisesRegex(ValueError, 'nothing is guessed'):
            subscribers.validate(guessed, NOW)
        with self.assertRaisesRegex(ValueError, 'names its code'):
            subscribers.validate(missed('tired'), NOW)


class IngestTests(unittest.TestCase):
    def test_a_whole_week_read_on_monday_counts_for_that_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = root(tmp)
            dry = subscribers.ingest(taken(), base, False, NOW, APPROVED)
            self.assertEqual(dry['now_md'], 'would replace')
            self.assertEqual((base / 'NOW.md').read_text(encoding='utf-8'), NOW_MD)  # a dry run writes nothing
            done = subscribers.ingest(taken(), base, True, NOW, APPROVED)
            state = current_state(base)
            self.assertEqual((state['week_of'], state['week_target'], state['current']), ('2026-11-09', 50, 5))
            self.assertEqual(state['current_as_of'], '2026-11-15')
            self.assertEqual(done['ledger'], 'appended')
            self.assertEqual(read_ledger(base), [state])
            # A re-run records nothing twice.
            again = subscribers.ingest(taken(), base, True, NOW, APPROVED)
            self.assertEqual((again['now_md'], again['ledger']), ('already current', 'already recorded'))
            self.assertEqual(len(read_ledger(base)), 1)
            # The total, the sources and the per-item rows stay in the ignored .scratch, never the ledger.
            kept = [json.loads(x) for x in (base / '.scratch/substack/weekly.jsonl').read_text().splitlines()]
            self.assertEqual(kept[-1]['total_subscribers']['value'], 321)
            self.assertEqual(kept[-1]['items'], {'recorded': 3, 'with_a_new_subscriber': 1, 'with_none': 1,
                                                 'not_shown': 1})
            # Substack's own per-item numbers are judged by subscribers too: a zero with no visit count is no fail.
            self.assertEqual(kept[-1]['items_by_subscribers'], {'works': 1, 'neutral': 0, 'fails': 0, 'insufficient': 2})
            self.assertNotIn('321', (base / 'lists' / 'northstar-history.jsonl').read_text())

    def test_unapproved_classification_is_not_counted_and_says_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = root(tmp)
            # Krish approved the repository's own map on 2026-11-12, so the unapproved case reads the fixture.
            subscribers.ingest(taken(), base, True, NOW, FIXTURES / 'sources-unapproved.json')
            state = current_state(base)
            self.assertIsNone(state['current'])
            self.assertIn('all sources 7', state['current_source'])
            self.assertIn("awaits Krish's approval", state['current_source'])
            self.assertEqual(state['urgency'], 4)

    def test_a_window_that_misses_the_week_is_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = root(tmp)
            capture = taken(growth_sources=sources('2026-11-10', '2026-11-16'))
            capture['captured_at'] = '2026-11-16T09:00:00-05:00'
            capture['growth_sources']['captured_at'] = '2026-11-16T09:00:00-05:00'
            result = subscribers.ingest(capture, base, False, '2026-11-16T20:00:00Z', APPROVED)
            self.assertIsNone(result['state']['current'])
            self.assertIn('only bounds this week', result['not_counted_because'])

    def test_a_read_not_taken_is_unknown_with_its_reason_and_never_replaces_a_measured_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = root(tmp)
            result = subscribers.ingest(missed(), base, True, NOW, APPROVED)
            state = current_state(base)
            self.assertEqual(result['now_md'], 'replaced')
            self.assertEqual((state['week_of'], state['current'], state['urgency']), ('2026-11-09', None, 4))
            self.assertIn('signed_out', state['current_source'])
            self.assertEqual(read_ledger(base)[-1], state)
            # A measured reading of the same week is never replaced by an unknown one; the ledger still records it.
            subscribers.ingest(taken(), base, True, NOW, APPROVED)
            later = missed('page_changed')
            later['captured_at'] = '2026-11-16T07:00:00-05:00'
            result = subscribers.ingest(later, base, True, '2026-11-16T13:00:00Z', APPROVED)
            self.assertTrue(result['now_md'].startswith('kept'))
            self.assertEqual(current_state(base)['current'], 5)
            self.assertIn('page_changed', read_ledger(base)[-1]['current_source'])

    def test_the_command_runs_through_growth_py_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = root(tmp)
            path = base / '.scratch' / 'week.json'
            path.parent.mkdir()
            path.write_text(json.dumps(taken()), encoding='utf-8')
            code, text = run(['subscribers', 'ingest', str(path), '--now', NOW, '--sources', str(APPROVED)], base)
            self.assertEqual(code, 0, text)
            self.assertIn('Week of 2026-11-09: 5 of 50', text)
            self.assertIn('Dry run', text)
            broken = copy.deepcopy(taken())
            broken['read'] = 'perhaps'
            path.write_text(json.dumps(broken), encoding='utf-8')
            code, text = run(['ingest', str(path), '--now', NOW], base)
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(text)['valid'])
            from engine.run.cli import ROUTES
            self.assertEqual(ROUTES['subscribers'], 'subscribers')


if __name__ == '__main__':
    unittest.main()
