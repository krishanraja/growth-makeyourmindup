"""Krish's instruction and this engine's state on every place (protocol 1.20.0).

Ruling (Krish, 2026-11-11): every growth engine's priorities, obsessions, next steps and outstanding items
feed live across Control Centre, and Krish instructs each engine with his next best action, which starts it.

The engine reads his instruction from the directive, acts on it first inside the walls, and acks it by id
(received, then started, done or blocked), never quoting his words: this repository and its Actions logs
are public. A second wake the same day reports under its own run_id. Synthetic fixtures only, against the
local stand-in; no test reaches Control Center.
"""
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import growth
from engine import cc_loop, engine_state
from engine.cc_loop import run_id_for, runner_run_id, workspace_report
from engine.control_center import (STATE_FIELDS, build_report, objective, report_digest, validate_report,
                                   without_state)
from engine.core import instant, read_json, write_json
from test_control_center import NOW, PREFIX, TOKEN, StandIn, checks, envelope
from test_runner_dedup import workspace

ROOT = Path(__file__).resolve().parents[1]
IID = 'ki_' + '0123456789abcdef01234567'
OLD = 'ki_' + 'f' * 24
WORDS = ('SYNTHETIC FIXTURE WORDS: lead the radar with recommendation swap asks to three named newsletters '
         'before anything else this week')
SERVED = {'engine_state': True, 'krish_instruction': True}
HELD_RULE = ('Krish has held this engine until it is ready. Propose nothing and ask him nothing. Report one '
             'hold that names what stops you being ready and what would clear it.')
ALL = ['1.0.0', '1.1.0', '1.14.0', '1.16.0', '1.17.0', '1.20.0']
ENGINE_FILES = ('config/engine-state.json', 'docs/NORTH_STAR.md', 'CHANGES.md', 'AGENTS.md', 'NOW.md',
                'docs/GET-GOING.md', 'intensity.json')


def setUpModule():
    # The runner reads the public feed for its backlog line; unit tests stay offline.
    global _OFFLINE
    from engine import backlog
    _OFFLINE = patch.object(backlog, 'read_feed', side_effect=OSError('offline test'))
    _OFFLINE.start()


def tearDownModule():
    _OFFLINE.stop()


def given(words=WORDS, iid=IID):
    return {'id': iid, 'words': words, 'given_at': '2026-10-17T16:00:00Z', 'given_by': 'krish', 'supersedes': None}


def directive(instruction=None, features=SERVED, held=False, carry=True):
    body = {'directive_id': 'makeyourmindup:2026-10-17', 'next_action': {'instruction': HELD_RULE if held else 'Rule pick'}}
    if carry:
        body['krish_instruction'] = instruction
    if features is not None:
        body['features'] = features
    return {'ok': True, 'chosen_by': 'rule', 'directive': body}


def engine_files(folder):
    for name in ENGINE_FILES:
        (Path(folder) / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, Path(folder) / name)
    shutil.copytree(ROOT / 'now-notes', Path(folder) / 'now-notes')
    return folder


def strings(value):
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    return [value] if isinstance(value, str) else []


class StateStandIn(StandIn):
    """The stand-in serving capabilities with 1.20.0 and engine_state, and GET reports?recent=n."""

    def __init__(self, versions=ALL, features=None):
        super().__init__()
        self.capabilities = {'schema_version': '1.20.0', 'schema_versions': list(versions), 'engine_id': 'growth-makeyourmindup',
                             'product_slug': 'publication', 'idempotency': True,
                             'features': dict(features if features is not None else
                                              {'engine_state': True, 'krish_instruction': True, 'copy_open': True})}
        stand, base = self, self.server.RequestHandlerClass

        class Handler(base):
            def handle_any(self, method):
                parts = urlsplit(self.path)
                query = parse_qs(parts.query)
                if method == 'GET' and parts.path == PREFIX + 'reports' and 'recent' in query:
                    stand.calls.append({'method': method, 'path': parts.path, 'query': parts.query, 'key': None,
                                        'body': None, 'auth': self.headers.get('Authorization')})
                    if self.headers.get('Authorization') != 'Bearer ' + stand.token:
                        return self.reply(401, {'error': 'unauthorized'})
                    rows = [{'run_id': r['run_id'], 'accepted_at': NOW, 'status': r['status'], 'activity': r['activity']}
                            for r in reversed(list(stand.reports.values()))]
                    return self.reply(200, {'ok': True, 'reports': rows[:int(query['recent'][0])]})
                return base.handle_any(self, method)

        self.server.RequestHandlerClass = Handler


def run_cli(argv, stand, folder):
    out = io.StringIO()
    with patch.object(growth, 'engine_client', lambda: stand.client()), patch.object(growth, 'ROOT', Path(folder)), \
            patch.object(cc_loop, 'runner_checks', lambda r: checks()), \
            patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': TOKEN}), contextlib.redirect_stdout(out):
        code = growth.main(argv)
    return code, out.getvalue()


def lines(report):
    return [a['line'] for a in report['activity']]


class DirectiveTests(unittest.TestCase):
    def test_an_instruction_is_read_and_a_malformed_one_never_repaired(self):
        self.assertEqual(engine_state.instruction(directive(given()))[0], 'open')
        self.assertEqual(engine_state.instruction(directive(None)), ('none', None))
        self.assertEqual(engine_state.instruction(directive(carry=False)), ('absent', None))
        self.assertEqual(engine_state.instruction({'ok': True}), ('absent', None))
        for bad in ({'id': 'ki_short', 'words': 'x'}, {'id': IID, 'words': ''}, {'id': IID, 'words': 'x' * 2001}, 'text'):
            self.assertEqual(engine_state.instruction(directive(bad))[0], 'absent', bad)

    def test_nothing_new_is_reported_until_the_directive_serves_engine_state(self):
        self.assertTrue(engine_state.served(directive(given())))
        for features in (None, {}, {'engine_state': False, 'krish_instruction': True}, {'engine_state': 'true'}):
            d = directive(given(), features=features)
            self.assertFalse(engine_state.served(d))
            self.assertEqual(engine_state.report_part(d, NOW, 'runner'), ([], []))
            self.assertEqual(engine_state.fields(ROOT, {'urgency': 4, 'week_target': 162}, d), {})

    def test_an_ack_never_repeats_his_words(self):
        self.assertTrue(engine_state.quotes_words('Done: lead the radar with recommendation swap asks to three', WORDS))
        self.assertFalse(engine_state.quotes_words('Drafted three swap asks first and put them at his gate', WORDS))
        self.assertTrue(engine_state.quotes_words('I will grow the newsletter now', 'grow the newsletter now'))
        self.assertFalse(engine_state.quotes_words('Went ahead', 'Go'))
        item = engine_state.instruction(directive(given()))[1]
        self.assertIn("repeats Krish's words", '; '.join(engine_state.workspace_ack_errors(
            'done', 'lead the radar with recommendation swap asks to three named newsletters', None, item)))
        self.assertEqual(engine_state.workspace_ack_errors('done', 'Drafted the swap asks first', None, item), [])
        self.assertIn('no instruction', '; '.join(engine_state.workspace_ack_errors('done', 'Did it', None, None)))
        self.assertTrue(engine_state.workspace_ack_errors('received', 'Did it', None, item))
        self.assertTrue(engine_state.workspace_ack_errors('done', 'Mailed hello@example.org', None, item))


class StateFieldTests(unittest.TestCase):
    def test_obsessions_are_his_quoted_words_checked_against_their_source(self):
        found = engine_state.obsessions(ROOT)
        self.assertEqual(len(found), 3)
        for item in found:
            self.assertTrue(item['line'].startswith('"') and item['line'].endswith('"'))
            self.assertLessEqual(len(item['line']), 200)
        with tempfile.TemporaryDirectory() as folder:
            engine_files(folder)
            config = read_json(Path(folder) / 'config/engine-state.json')
            config['obsessions'][1]['line'] = '"a goal nobody quoted"'
            write_json(Path(folder) / 'config/engine-state.json', config)
            self.assertEqual(len(engine_state.obsessions(folder)), 2)  # never invented: a line not in its source drops
            (Path(folder) / 'config/engine-state.json').unlink()
            self.assertEqual(engine_state.obsessions(folder), [])

    def test_priorities_lead_with_the_gap_and_end_with_zero_paid(self):
        gap = {'week_of': '2026-11-09', 'week_target': 162, 'current': 1, 'urgency': 5, 'reason': 'x'}
        found = engine_state.priorities(ROOT, gap)
        self.assertEqual([p['rank'] for p in found], [1, 2, 3, 4, 5])
        self.assertIn('1 of 162 this week, U5, short by 161', found[0]['line'])
        self.assertIn('5 one-person Substack outreach drafts', found[2]['line'])
        self.assertIn('25 engagement taps', found[3]['line'])
        self.assertEqual(found[-1]['objective_key'], 'paid_boosts_usd')
        low = engine_state.priorities(ROOT, dict(gap, urgency=1))
        self.assertEqual(len(low), 2)  # no levers below U3: only the gap and the constraint
        unknown = engine_state.priorities(ROOT, {'urgency': None, 'week_target': None, 'reason': 'the North Star is paused'})
        self.assertIn('not known', unknown[0]['line'])

    def test_next_steps_come_from_now_notes_now_md_and_get_going(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'now-notes').mkdir()
            (Path(folder) / 'docs').mkdir()
            (Path(folder) / 'now-notes/2026-11-01-old.md').write_text('Status: x\nNext: Krish presses the old thing.\n')
            (Path(folder) / 'now-notes/2026-11-02-quiet.md').write_text('Status: x\nNext: none for this.\n')
            (Path(folder) / 'now-notes/2026-11-03-new.md').write_text('Status: x\nNext: Release the `W46` posts once he approves.\n')
            (Path(folder) / 'NOW.md').write_text(
                '# x\n\n## What is next and what is waiting on Krish\n\n- Waiting on Krish: a ruling.\n'
                '- Next (5 November): Krish runs one engine session ("Run Acquisition" first) to start the shadow '
                'week, and rules on the one open conflict: ' + 'the review keeps every ready draft open, ' * 4
                + 'which BROWSER.md does not allow.\n\n## Read next\n')
            (Path(folder) / 'docs/GET-GOING.md').write_text(
                '# Get going\n\n## The build\n\n- [x] **Done step.** Finished.\n- [ ] **Complete the live baseline.**'
                ' Profiles, pins and 30 days of posts. More text here.\n  Wrapped.\n- [ ] **Later.** Not this.\n')
            item = {'id': IID, 'words': WORDS}
            steps = engine_state.next_steps(folder, item)
            self.assertEqual([s['line'] for s in steps], [
                "Act on Krish's open instruction first, in the next publication workspace job, inside the walls",
                'Release the W46 posts once he approves.',
                'Krish presses the old thing.',
                'Krish runs one engine session ("Run Acquisition" first) to start the shadow week',
                'Complete the live baseline: Profiles, pins and 30 days of posts.'])
            self.assertEqual([s['waits_on'] for s in steps], ['engine', 'engine', 'krish', 'krish', 'engine'])
            self.assertTrue(all(s['when'] is None and len(s['line']) <= 200 for s in steps))
            # Acked done in this run: the instruction step goes; nothing is ever more than five.
            self.assertNotIn('open instruction', ' '.join(s['line'] for s in engine_state.next_steps(folder, item, done=True)))
        live = engine_state.next_steps(ROOT)
        self.assertTrue(1 <= len(live) <= 5)
        self.assertTrue(all(not engine_state.state_line_errors('x', s['line'], 200) for s in live))

    def test_the_report_refuses_a_bad_state_field(self):
        good = {'priorities': [{'rank': 1, 'line': 'Grow', 'objective_key': 'new_subscribers'}],
                'next_steps': [{'line': 'Do it', 'waits_on': 'engine', 'when': None}],
                'obsessions': [{'line': '"His aim"', 'since': '2026-11-11'}],
                'instruction_acks': [engine_state.ack(IID, 'received', 'Received', NOW)]}
        report = self.report(good)
        self.assertEqual(report['schema_version'], '1.20.0')
        for key, bad in (('priorities', [{'rank': 6, 'line': 'x', 'objective_key': None}]),
                         ('priorities', [{'rank': 1, 'line': 'Write to hello@example.org', 'objective_key': None}]),
                         ('next_steps', [{'line': 'x', 'waits_on': 'nobody', 'when': None}]),
                         ('next_steps', [{'line': 'two\nlines', 'waits_on': 'engine', 'when': None}]),
                         ('obsessions', [{'line': 'x', 'since': '2026-02-30'}]),
                         ('obsessions', [{'line': ' ', 'since': None}]),
                         ('instruction_acks', [dict(good['instruction_acks'][0], instruction_id='ki_bad')]),
                         ('instruction_acks', [dict(good['instruction_acks'][0], line='x' * 281)]),
                         ('priorities', [{'rank': 1, 'line': 'x', 'objective_key': None}] * 6)):
            with self.assertRaises(ValueError, msg=key):
                self.report(dict(good, **{key: bad}))
        # A state field under an older version is refused.
        stale = dict(report, schema_version='1.17.0')
        stale['payload_sha256'] = report_digest(stale)
        with self.assertRaises(ValueError):
            validate_report(stale)
        # Without them the report goes back to its own version, and no line naming his instruction stays.
        report = self.report(good, activity=[{'line': 'Gap'}, {'line': "Received Krish's instruction " + IID}])
        plain = without_state(report)
        self.assertFalse(set(STATE_FIELDS) & set(plain))
        self.assertEqual(plain['schema_version'], '1.0.0')
        self.assertEqual(lines(plain), ['Gap'])

    def report(self, state, activity=({'line': 'Fixture run'},)):
        return build_report('makeyourmindup:2026-10-17:test', 'synthetic', NOW, 'fixture', NOW, 'held',
                            [objective('new_subscribers', reason='Fixture: not measured')], list(activity), state=state)


class RunnerTests(unittest.TestCase):
    def runner(self, stand, folder, *extra):
        return run_cli(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW] + list(extra), stand, folder)

    def test_instruction_present_the_runner_acks_received_by_id_and_never_prints_his_words(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            stand.directive_extra = {'krish_instruction': given(), 'features': SERVED}
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            validate_report(report)
            self.assertEqual(report['schema_version'], '1.20.0')
            self.assertTrue(lines(report)[0].startswith('North Star gap') or ' of ' in lines(report)[0])  # the gap leads
            self.assertEqual(lines(report)[1], "Received Krish's instruction " + IID + '; the next publication '
                             'workspace job acts on it first, inside the walls')
            self.assertEqual([(a['instruction_id'], a['state']) for a in report['instruction_acks']], [(IID, 'received')])
            self.assertEqual(report['next_steps'][0]['line'].split(' first')[0], "Act on Krish's open instruction")
            # No state or ack line carries the id: its hex can hold ten digits in a row, which reads as a phone number.
            self.assertFalse(any(IID in s for key in STATE_FIELDS for item in report.get(key, []) for s in strings(
                {k: v for k, v in item.items() if k != 'instruction_id'})))
            self.assertEqual(len(report['obsessions']), 3)
            self.assertEqual(report['priorities'][0]['objective_key'], 'new_subscribers')
            # His words are nowhere in the report or the public log; the id is.
            self.assertFalse(any('SYNTHETIC FIXTURE WORDS' in s or 'recommendation swap asks to three' in s
                                 for s in strings(report)))
            self.assertNotIn('SYNTHETIC FIXTURE WORDS', text)
            self.assertIn("Krish's instruction " + IID + ': received', text)
            # The capabilities say 1.20.0 and engine_state before the report goes.
            self.assertTrue(any(c['path'] == PREFIX + 'capabilities' for c in stand.calls))

    def test_instruction_absent_or_none_open_sends_no_ack(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            stand.directive_extra = {'krish_instruction': None, 'features': SERVED}
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            self.assertNotIn('instruction_acks', report)
            self.assertFalse(any("Krish's instruction" in l for l in lines(report)))
            self.assertEqual(report['schema_version'], '1.20.0')  # the state still rides: priorities and the rest
            self.assertIn("Krish's instruction: none open", text)
        # Before Control Center serves 1.20.0 the report is exactly as it was.
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            stand.directive_extra = {}
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            self.assertFalse(set(STATE_FIELDS) & set(report))
            self.assertEqual(report['schema_version'], '1.1.0')
            self.assertIn("Krish's instruction: not in today's directive", text)

    def test_held_engine_is_told_nothing_and_blocks_an_instruction_it_is_handed(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            # As Control Center sends a held engine: HELD_RULE and krish_instruction null.
            stand.directive_extra = {'krish_instruction': None, 'features': SERVED,
                                     'next_action': {'proposal_id': None, 'instruction': HELD_RULE, 'why': 'held',
                                                     'close_condition': None}}
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            self.assertNotIn('instruction_acks', report)
        # Handed one while held (it should not be): received, then blocked, engine held. It acts on nothing.
        told, acks = engine_state.report_part(directive(given(), held=True), NOW, 'runner')
        self.assertEqual([a['state'] for a in acks], ['received', 'blocked'])
        self.assertTrue(acks[1]['line'].startswith('engine held'))
        self.assertEqual(told, ["Received Krish's instruction " + IID + '; blocked while Krish holds this engine'])
        self.assertIn('held in Control Center', '\n'.join(engine_state.block(directive(given(), held=True))))

    def test_a_second_wake_the_same_day_reports_under_its_own_run_id(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            code, text = self.runner(stand, folder)  # the morning's push, before he instructs
            self.assertEqual(code, 0, text)
            morning = stand.reports[run_id_for('runner', instant(NOW))]
            sealed = morning['payload_sha256']
            stand.directive_extra = {'krish_instruction': given(), 'features': SERVED}
            code, text = self.runner(stand, folder, '--wake', 'gh123456.1')
            self.assertEqual(code, 0, text)
            wake_id = run_id_for('runner', instant(NOW)) + ':wake-gh123456.1'
            self.assertEqual(wake_id, runner_run_id(NOW, wake='gh123456.1'))
            wake = stand.reports[wake_id]
            self.assertEqual(stand.reports[morning['run_id']]['payload_sha256'], sealed)  # never overwritten
            self.assertEqual([a['state'] for a in wake['instruction_acks']], ['received'])
            self.assertEqual(wake['proposals'], [])  # what the morning proposed is not proposed again
            self.assertNotIn('report conflict', text)
            # A third wake: the instruction was already named, so 'received' is not sent again.
            code, text = self.runner(stand, folder, '--wake', 'gh123457.1')
            self.assertEqual(code, 0, text)
            third = stand.reports[run_id_for('runner', instant(NOW)) + ':wake-gh123457.1']
            self.assertNotIn('instruction_acks', third)
            self.assertEqual(lines(third)[1], "Krish's instruction " + IID + ' is open; the next publication '
                             'workspace job acts on it first, inside the walls')
            for bad in ('', 'has space', 'x' * 41, '../up'):
                with self.assertRaises(ValueError):
                    runner_run_id(NOW, wake=bad)

    def test_the_workflow_wakes_with_its_own_run_id_and_prints_only_the_id(self):
        text = (ROOT / '.github/workflows/control-center.yml').read_text(encoding='utf-8')
        self.assertIn('CC_DISPATCH_INSTRUCTION_ID: ${{ github.event.client_payload.instruction_id }}', text)
        self.assertIn('--wake "gh${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}"', text)
        self.assertNotIn('echo "$CC_DISPATCH_INSTRUCTION_ID', text)

    def test_control_center_without_1_20_0_still_gets_the_run_without_the_new_fields(self):
        with StateStandIn(versions=['1.0.0', '1.1.0', '1.17.0']) as stand, tempfile.TemporaryDirectory() as folder:
            engine_files(workspace(folder))
            stand.directive_extra = {'krish_instruction': given(), 'features': SERVED}
            code, text = self.runner(stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('runner', instant(NOW))]
            self.assertFalse(set(STATE_FIELDS) & set(report))
            self.assertFalse(any("Krish's instruction" in l for l in lines(report)))  # never claims an ack it did not send
            self.assertIn('engine state not taken (schema_version_unsupported); reported without it', text)


class WorkspaceTests(unittest.TestCase):
    def folder(self, folder):
        engine_files(folder)
        for name in ('experiments.json', 'channels.json', 'journeys.json'):
            write_json(Path(folder) / name, read_json(ROOT / name))
        path = Path(folder) / 'envelope.json'
        write_json(path, envelope())
        return str(path)

    def test_the_job_reads_his_instruction_first_acts_and_acks_done(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            env = self.folder(folder)
            stand.directive_extra = {'krish_instruction': given(), 'features': SERVED}
            code, text = run_cli(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            self.assertTrue(text.startswith("KRISH'S INSTRUCTION"), text[:200])  # first, before the directive
            self.assertIn(WORDS, text)  # the local workspace shows Krish's words to the job that acts on them
            kept = (Path(folder) / '.scratch/cc/instruction.txt').read_text(encoding='utf-8')
            self.assertIn(WORDS, kept)
            self.assertIn('never an approval', kept)
            code, text = run_cli(['cc', 'finish', '--job', 'daily', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                  '--now', NOW, '--ack', 'done', '--ack-line',
                                  'Drafted three swap asks first and put them at his gate; nothing sent'], stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('daily', instant(NOW))]
            self.assertEqual([a['state'] for a in report['instruction_acks']], ['received', 'done'])
            self.assertEqual(lines(report)[1], "Acted on Krish's instruction " + IID + ' in the daily job: done')
            self.assertFalse(any('open instruction' in s['line'] for s in report['next_steps']))
            self.assertFalse(any('SYNTHETIC FIXTURE WORDS' in s for s in strings(report)))
            ledger = read_json(Path(folder) / '.scratch/cc/instructions.json')
            self.assertEqual([a['state'] for a in ledger[IID]['acks']], ['received', 'done'])
            # The next job here is told it is done, and never sends 'received' again.
            code, text = run_cli(['cc', 'start', '--job', 'radar', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertIn('acked done in an earlier job here; do not act on it again', text)
            self.assertNotIn(WORDS, text)
            code, text = run_cli(['cc', 'finish', '--job', 'radar', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                  '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            radar = stand.reports[run_id_for('radar', instant(NOW))]
            self.assertNotIn('instruction_acks', radar)

    def test_an_ack_line_that_quotes_him_is_refused_before_anything_is_reported(self):
        with StateStandIn() as stand, tempfile.TemporaryDirectory() as folder:
            env = self.folder(folder)
            stand.directive_extra = {'krish_instruction': given(), 'features': SERVED}
            run_cli(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            code, text = run_cli(['cc', 'finish', '--job', 'daily', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                  '--now', NOW, '--ack', 'started', '--ack-line',
                                  'Started: lead the radar with recommendation swap asks to three named newsletters'],
                                 stand, folder)
            self.assertEqual(code, 1)
            self.assertIn("repeats Krish's words", text)
            self.assertEqual(stand.posts('reports'), [])
            # Fixed, the same finish runs once more under the same attempt.
            code, text = run_cli(['cc', 'finish', '--job', 'daily', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                  '--now', NOW, '--ack', 'blocked', '--ack-line',
                                  'Blocked: two of the three newsletters have no public contact route yet'], stand, folder)
            self.assertEqual(code, 0, text)
            report = stand.reports[run_id_for('daily', instant(NOW))]
            self.assertEqual([a['state'] for a in report['instruction_acks']], ['received', 'blocked'])
            self.assertEqual([a['status'] for a in (c['body'] for c in stand.posts('attempts'))], ['started', 'succeeded'])

    def test_the_measure_lane_carries_the_state_but_never_an_ack(self):
        from engine.run import measure_auto
        from engine.run.ga4 import load_config
        d = directive(given())
        state = engine_state.fields(ROOT, {'urgency': 4, 'week_target': 162, 'current': None}, d)
        report, _, _ = measure_auto.build({'note': 'Buffer not configured'}, None, instant(NOW), ROOT, 'synthetic',
                                          load_config(ROOT), True, state)
        self.assertEqual(report['schema_version'], '1.20.0')
        self.assertTrue(report['priorities'] and report['obsessions'] and report['next_steps'])
        self.assertNotIn('instruction_acks', report)
        self.assertFalse(any("Krish's instruction" in l for l in lines(report)))

    def test_no_instruction_means_the_job_reports_as_before(self):
        report, _ = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()], rev='x',
                                     directive=directive(None, features=None))
        self.assertFalse(set(STATE_FIELDS) & set(report))
        report, _ = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()], rev='x',
                                     directive=directive(None), root=ROOT)
        self.assertNotIn('instruction_acks', report)
        self.assertEqual(report['schema_version'], '1.20.0')
        self.assertTrue(report['priorities'] and report['obsessions'] and report['next_steps'])


if __name__ == '__main__':
    unittest.main()
