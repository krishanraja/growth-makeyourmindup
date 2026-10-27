"""Run spec lint and computed readiness, on synthetic fixtures only."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine.core import write_json
from engine.run import cli
from engine.run.spec import (computed, lint, main, payload_sha256, run_dir, skeleton, status,
                             week_target)
from engine.social import inventory

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'specs' / 'fixtures'
RECORDS = json.loads((FIXTURES / 'social-records.json').read_text(encoding='utf-8'))


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def codes(spec, records=RECORDS):
    return {e['code'] for e in lint(spec, records)['errors']}


def slot(spec, slot_id):
    return next(s for s in spec['slots'] if s['slot_id'] == slot_id)


class RunSpecLintTests(unittest.TestCase):
    def test_good_spec_lints_clean(self):
        result = lint(fixture('w45-week'), RECORDS)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])
        channels = {s['channel'] for s in fixture('w45-week')['slots']}
        self.assertEqual(channels, {'substack-notes', 'threads'})

    @unittest.skipUnless({'substack-notes', 'threads'} <= set(inventory()['channel']),
                         'the Notes and Threads records are another work item (27 Oct ruling)')
    def test_good_spec_lints_clean_against_repo_records(self):
        self.assertEqual(lint(fixture('w45-week'))['errors'], [])

    def test_seeded_bad_spec_fails_with_expected_errors(self):
        result = lint(fixture('bad-spec'), RECORDS)
        self.assertEqual({e['code'] for e in result['errors']},
                         {'week_target', 'payload_sha256', 'prose', 'unknown_channel', 'format_not_allowed',
                          'publish_mode', 'krish_click_due_at', 'spend', 'experiment_per_channel',
                          'experiment_arm', 'asset_sha256', 'notes_per_day'})
        by_code = {}
        for e in result['errors']:
            by_code.setdefault(e['code'], []).append(e)
        self.assertEqual([e['slot_id'] for e in by_code['payload_sha256']], ['w45-mon-note-2'])
        self.assertEqual([e['slot_id'] for e in by_code['publish_mode']], ['w45-linkedin-1'])
        self.assertEqual(len(by_code['prose']), 3)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['lint', str(FIXTURES / 'bad-spec.json')]), 1)
        self.assertFalse(json.loads(out.getvalue())['valid'])

    def test_schema_is_closed_and_errors_stop_there(self):
        spec = fixture('w45-week')
        spec['slots'][0]['status'] = 'live'
        self.assertEqual(codes(spec), {'schema'})
        spec = fixture('w45-week')
        spec['slots'][0]['due_at'] = '2026-11-02T09:30:00'
        self.assertEqual(codes(spec), {'schema'}, 'due_at needs an offset')
        spec = fixture('w45-week')
        spec['budgets']['spend_usd'] = 0.5
        self.assertEqual(codes(spec), {'schema'})

    def test_week_target_is_computed_from_ladder(self):
        self.assertEqual(week_target('2026-11-02T00:00:00-05:00'), 86)
        # Sunday 23:30 in New York is already Monday in UTC: the New York week counts.
        self.assertEqual(week_target('2026-11-09T04:30:00Z'), 86)
        self.assertEqual(week_target('2026-11-09T05:00:00Z'), 162)
        self.assertEqual(week_target('2026-10-28T12:00:00-04:00'), 25)
        with self.assertRaisesRegex(ValueError, 'no North Star ladder rung'):
            week_target('2027-01-04T00:00:00-05:00')
        spec = fixture('w45-week')
        spec['north_star']['week_target'] = 85
        self.assertEqual(codes(spec), {'week_target'})
        spec['north_star']['week_target'] = 86
        self.assertEqual(codes(spec), set())
        new = skeleton('2026-11-04')
        self.assertEqual(new['run_id'], 'makeyourmindup:2026-W45:week')
        self.assertEqual(new['window']['start'], '2026-11-02T00:00:00-05:00')
        self.assertEqual(new['window']['end'], '2026-11-09T00:00:00-05:00')
        self.assertEqual(new['north_star']['week_target'], 86)
        # 1 November 2026 is the autumn clock change: midnight is still daylight time.
        self.assertEqual(skeleton('2026-11-01', 'express')['window']['start'], '2026-11-01T00:00:00-04:00')
        self.assertEqual(codes(new), set())

    def test_payload_digest_recomputed(self):
        spec = fixture('w45-week')
        first = spec['slots'][0]
        body = {'channel': first['channel'], 'format': first['format'], 'words': first['words'],
                'assets': [a['sha256'] for a in first['assets']], 'link_placement': first['link_placement'],
                'due_at': first['due_at'], 'publish_mode': first['publish_mode']}
        expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                             ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(payload_sha256(first), expected)
        self.assertEqual(first['payload_sha256'], expected)
        before = payload_sha256(first)
        for key, value in (('forward_line', 'TEST FIXTURE ONLY. Someone else forwards it.'), ('play', 'P2'),
                           ('cta', True), ('buffer_draft_id', 'synthetic-draft')):
            changed = dict(first, **{key: value})
            self.assertEqual(payload_sha256(changed), before, key + ' is not part of the signed payload')
        for key, value in (('words', first['words'] + ' One more line.'), ('due_at', '2026-11-02T10:30:00-05:00'),
                           ('link_placement', 'first_reply'), ('assets', [dict(first['assets'][0], sha256='a' * 64)])):
            changed = copy.deepcopy(spec)
            changed['slots'][0][key] = value
            self.assertNotEqual(payload_sha256(changed['slots'][0]), before, key)
            self.assertEqual(codes(changed), {'payload_sha256'}, key + ' edited by hand is refused')
            self.assertEqual(codes(computed(changed)), set(), 'run new --from recomputes it')
        reordered = copy.deepcopy(first)
        reordered['assets'] = [dict(first['assets'][0], name='renamed.png', url='https://example.com/a.png')]
        self.assertEqual(payload_sha256(reordered), before, 'only the asset bytes hash is signed')

    def test_linkedin_slot_must_be_krish_click(self):
        spec = fixture('w45-week')
        draft = dict(spec['slots'][3], slot_id='w45-linkedin-1', channel='linkedin', experiment_arm=None,
                     link_placement=None, words='TEST FIXTURE ONLY. A LinkedIn draft for Krish to post himself.')
        spec['slots'].append(draft)
        for mode, due, expected in (('engine', None, {'publish_mode'}),
                                    ('engine', '2026-11-05T09:00:00-05:00', {'publish_mode'}),
                                    ('krish_click', '2026-11-05T09:00:00-05:00', {'krish_click_due_at'}),
                                    ('krish_click', None, set())):
            draft.update(publish_mode=mode, due_at=due)
            self.assertEqual(codes(computed(spec)), expected, (mode, due))
        spec['slots'][3]['publish_mode'] = 'krish_click'
        spec['slots'][3]['due_at'] = None
        self.assertEqual(codes(computed(spec)), {'publish_mode'}, 'Threads is engine, not krish_click')

    def test_notes_per_day_counts_new_york_days(self):
        spec = fixture('w45-week')
        extra = copy.deepcopy(spec['slots'][1])
        extra.update(slot_id='w45-mon-note-3', due_at='2026-11-02T18:00:00-05:00')
        spec['slots'].append(extra)
        self.assertEqual(codes(computed(spec)), set(), 'three Notes on one day are allowed')
        late = copy.deepcopy(extra)
        # 02:00 UTC on Tuesday is still Monday evening in New York.
        late.update(slot_id='w45-mon-note-4', due_at='2026-11-03T02:00:00Z')
        spec['slots'].append(late)
        self.assertEqual(codes(computed(spec)), {'notes_per_day'})

    def test_cli_new_writes_computed_fields_and_never_replaces_a_skeleton(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            draft = Path(folder) / 'draft.json'
            spec = fixture('w45-week')
            spec['slots'][0]['payload_sha256'] = '0' * 64
            spec['north_star']['week_target'] = 1
            write_json(draft, spec)
            self.assertEqual(main(['new', '--from', str(draft), '--out', str(draft)]), 0)
            self.assertEqual(json.loads(draft.read_text(encoding='utf-8')), fixture('w45-week'))
            self.assertEqual(main(['new', '--start', '2026-11-02', '--out', str(draft)]), 1)
            self.assertEqual(json.loads(draft.read_text(encoding='utf-8')), fixture('w45-week'))

    def test_cli_routes_lazily_and_reports_unbuilt_modules(self):
        with patch.dict(cli.ROUTES, {'zzz': 'zzz_not_built'}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(['zzz', 'x']), 2)
        self.assertEqual(out.getvalue().strip(), 'zzz: not built yet')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([]), 2)
        import growth
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(growth.main(['run', 'lint', str(FIXTURES / 'w45-week.json')]),
                             int(not {'substack-notes', 'threads'} <= set(inventory()['channel'])))
        self.assertIn('"errors"', out.getvalue())


class RunStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runs = self.temp.name
        self.spec = fixture('w45-week')
        self.folder = run_dir(self.spec, self.runs)
        self.slot = slot(self.spec, 'w45-mon-threads-1')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, value):
        write_json(self.folder / name, value)

    def stage(self, slot_id='w45-mon-threads-1'):
        rows = {r['slot_id']: r for r in status(self.spec, self.runs)['slots']}
        return rows[slot_id]['stage'], rows[slot_id]['reason']

    def signed(self, digest=None, amended=None):
        sid = self.slot['slot_id']
        self.put('lint.json', {'run_id': self.spec['run_id'], 'spec_sha256': lint_digest(self.spec),
                               'errors': [], 'warnings': []})
        self.put('review/' + sid + '.json', {'slot_id': sid, 'verdict': 'pass', 'lens': 'threads'})
        self.put('decision.json', {'run_id': self.spec['run_id'], 'slots': {sid: {
            'approved': True, 'digest': digest or self.slot['payload_sha256'], 'amended': amended}}})

    def test_status_walks_every_stage_from_evidence_only(self):
        sid = self.slot['slot_id']
        self.assertEqual(self.stage()[0], 'drafted')
        self.put('lint.json', {'run_id': self.spec['run_id'], 'spec_sha256': 'f' * 64, 'errors': [], 'warnings': []})
        self.assertEqual(self.stage(), ('drafted', 'lint.json is for another version of this spec; run lint --record again'))
        with contextlib.redirect_stdout(io.StringIO()):
            main(['lint', str(FIXTURES / 'w45-week.json'), '--record', '--runs-dir', self.runs])
        lint_record = json.loads((self.folder / 'lint.json').read_text(encoding='utf-8'))
        self.assertEqual(lint_record['spec_sha256'], lint_digest(self.spec))
        if lint_record['errors']:  # Live records lack Notes or Threads until that work item lands.
            self.put('lint.json', dict(lint_record, errors=[]))
        self.assertEqual(self.stage()[0], 'linted')
        self.put('review/' + sid + '.json', {'verdict': 'fail', 'lens': 'threads'})
        self.assertEqual(self.stage()[0], 'linted')
        self.signed()
        self.assertEqual(self.stage()[0], 'signed')
        self.put('queued/' + sid + '.json', {'status': 'scheduled', 'payload_sha256': self.slot['payload_sha256']})
        self.assertEqual(self.stage()[0], 'queued')
        self.put('live/' + sid + '.json', {'status': 'sent', 'native_url': 'https://www.threads.com/@fixture/post/1'})
        self.assertEqual(self.stage()[0], 'live')
        self.put('measured/' + sid + '-48h.json', {'slot_id': sid, 'metrics': {}})
        self.assertEqual(self.stage()[0], 'live', 'a measurement needs captured_at')
        self.put('measured/' + sid + '-48h.json', {'slot_id': sid, 'captured_at': '2026-11-04T12:00:00-05:00'})
        self.assertEqual(self.stage()[0], 'measured')
        self.put('verdict/' + sid + '.json', {'verdict': 'great'})
        self.assertEqual(self.stage()[0], 'measured')
        self.put('verdict/' + sid + '.json', {'verdict': 'insufficient'})
        self.assertEqual(self.stage(), ('verdict', None))
        self.assertEqual(self.stage('w45-mon-note-1')[0], 'linted', 'other slots keep their own evidence')

    def test_scheduled_never_counts_as_live(self):
        sid = self.slot['slot_id']
        self.signed()
        self.put('queued/' + sid + '.json', {'status': 'scheduled', 'payload_sha256': self.slot['payload_sha256']})
        self.assertEqual(self.stage()[0], 'queued')
        for live in ({'status': 'scheduled', 'native_url': 'https://www.threads.com/@fixture/post/1'},
                     {'status': 'draft', 'native_url': 'https://www.threads.com/@fixture/post/1'},
                     {'status': 'sent'},
                     {'status': 'sent', 'native_url': 'http://www.threads.com/@fixture/post/1'},
                     {'status': 'sent', 'native_url': 'not a url'},
                     {'status': 'sent', 'native_url': 'https://www.threads.com/@fixture/post/1', 'payload_sha256': 'a' * 64}):
            self.put('live/' + sid + '.json', live)
            stage, reason = self.stage()
            self.assertEqual(stage, 'queued', live)
            self.assertTrue(reason)
        self.put('live/' + sid + '.json', {'status': 'scheduled', 'native_url': 'https://www.threads.com/@fixture/post/1'})
        self.assertIn('not live', self.stage()[1])
        self.put('measured/' + sid + '-48h.json', {'captured_at': '2026-11-04T12:00:00-05:00'})
        self.put('verdict/' + sid + '.json', {'verdict': 'works'})
        self.assertEqual(self.stage()[0], 'queued', 'later evidence never skips a missing live readback')

    def test_decision_digest_mismatch_never_signed(self):
        sid = self.slot['slot_id']
        self.signed(digest='a' * 64)
        self.assertEqual(self.stage(), ('reviewed', 'decision digest does not match payload_sha256; a mismatch is never signed'))
        other = slot(self.spec, 'w45-wed-threads-1')['payload_sha256']
        self.signed(digest=other)
        self.assertEqual(self.stage()[0], 'reviewed', "another slot's digest never signs this one")
        self.signed()
        self.put('decision.json', {'run_id': self.spec['run_id'], 'slots': {sid: {
            'approved': False, 'digest': self.slot['payload_sha256']}}})
        self.assertEqual(self.stage()[0], 'reviewed')
        self.put('decision.json', {'run_id': 'makeyourmindup:2026-W46:week', 'slots': {sid: {
            'approved': True, 'digest': self.slot['payload_sha256']}}})
        self.assertEqual(self.stage()[0], 'reviewed')
        # Krish amends: his version is what is signed, and only its digest may be queued.
        amended = {k: self.slot[k] for k in ('channel', 'format', 'link_placement', 'due_at', 'publish_mode')}
        amended.update(words='TEST FIXTURE ONLY. Krish reworded this line.', assets=[])
        from engine.control_center import sha256_hex
        self.signed(digest=sha256_hex(amended), amended=amended)
        self.assertEqual(self.stage()[0], 'signed')
        self.put('queued/' + sid + '.json', {'status': 'scheduled', 'payload_sha256': self.slot['payload_sha256']})
        self.assertEqual(self.stage()[0], 'signed', 'the unamended payload is not what Krish signed')
        self.put('queued/' + sid + '.json', {'status': 'scheduled', 'payload_sha256': sha256_hex(amended)})
        self.assertEqual(self.stage()[0], 'queued')
        self.signed(digest=sha256_hex(amended), amended=dict(amended, words='Changed after signing.'))
        self.assertEqual(self.stage()[0], 'reviewed', 'an amended digest must recompute')
        moved = dict(amended, channel='x')
        self.signed(digest=sha256_hex(moved), amended=moved)
        self.assertEqual(self.stage()[0], 'reviewed', 'an amendment cannot move the channel')

    def test_krish_click_slot_is_only_ever_queued_as_a_draft(self):
        spec = fixture('w45-week')
        spec['slots'].append(dict(spec['slots'][3], slot_id='w45-linkedin-1', channel='linkedin', due_at=None,
                                  publish_mode='krish_click', experiment_arm=None, link_placement=None))
        self.spec = computed(spec)
        self.slot = slot(self.spec, 'w45-linkedin-1')
        self.signed()
        self.put('queued/w45-linkedin-1.json', {'status': 'scheduled', 'payload_sha256': self.slot['payload_sha256']})
        self.assertEqual(self.stage('w45-linkedin-1'), ('signed', 'a krish_click slot is only ever an unscheduled draft'))
        self.put('queued/w45-linkedin-1.json', {'status': 'draft', 'payload_sha256': self.slot['payload_sha256']})
        self.assertEqual(self.stage('w45-linkedin-1')[0], 'queued')


def lint_digest(spec):
    from engine.control_center import sha256_hex
    return sha256_hex(spec)


if __name__ == '__main__':
    unittest.main()
