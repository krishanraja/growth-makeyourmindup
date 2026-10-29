"""The Control Center protocol client, against a local stand-in server only.

No test reaches controlcenter.krishraja.com. Every report here is synthetic.
"""
import argparse
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import logging
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

import growth
from engine import cc_loop
from engine.cc_loop import (Loop, completion_events, describe, new_subscribers, run, runner_report,
                            voice_block, voice_rules, week_start, workspace_report)
from engine.control_center import (ENGINE_ID, Client, ProtocolError, build_report, canonical_json,
                                   load_schema, match_decisions, objective, payload_digest, proposal,
                                   report_digest, schema_errors, validate_report, whole)
from engine.core import identity, read_json, write_json
from engine.packs import seal

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-17T18:00:00Z'
TOKEN = 'gen1_' + 'StandInOnlyNeverReal' * 3
PRIVATE = 'directive text that must stay off a public runner log'
PREFIX = '/api/growth/engines/makeyourmindup/'


class StandIn:
    """A local stand-in for Control Center's engine routes."""

    def __init__(self, token=TOKEN):
        self.token = token
        self.attempts, self.reports, self.calls = {}, {}, []
        self.decisions = []
        self.inactive = False
        self.redirect = False
        self.directive_extra = {}
        stand = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body, headers=None):
                data = json.dumps(body).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def handle_any(self, method):
                parts = urlsplit(self.path)
                body = None
                if method == 'POST':
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                stand.calls.append({'method': method, 'path': parts.path, 'query': parts.query,
                                    'auth': self.headers.get('Authorization'),
                                    'key': self.headers.get('Idempotency-Key'), 'body': body})
                if self.headers.get('Authorization') != 'Bearer ' + stand.token:
                    return self.reply(401, {'error': 'unauthorized'})
                if stand.redirect:
                    return self.reply(302, {}, {'Location': 'http://127.0.0.1:9/elsewhere'})
                if not parts.path.startswith(PREFIX):
                    return self.reply(404, {'error': 'not_found'})
                route = parts.path[len(PREFIX):]
                if method == 'POST' and route == 'attempts':
                    old = stand.attempts.get(body['attempt_id'])
                    if old and old['status'] != 'started' and old != body:
                        return self.reply(409, {'error': 'conflict'})
                    stand.attempts[body['attempt_id']] = body
                    return self.reply(200, {'ok': True, 'attempt': body, 'replayed': old == body})
                if method == 'GET' and route == 'directive':
                    return self.reply(200, {'ok': True, 'chosen_by': 'rule', 'directive': {
                        'schema_version': '1.0.0', 'directive_id': 'makeyourmindup:2026-10-17',
                        'engine_id': ENGINE_ID, 'for_date': '2026-10-17', 'aim': None, 'objectives': [],
                        'next_action': {'proposal_id': None, 'instruction': PRIVATE, 'why': PRIVATE,
                                        'close_condition': None},
                        'decisions_since': [], 'constraints': {'walls': 'fixture', 'spend_cap_usd': 0, 'max_actions': 5},
                        **stand.directive_extra}})
                if method == 'POST' and route == 'reports':
                    if self.headers.get('Idempotency-Key') != body.get('run_id') or report_digest(body) != body.get('payload_sha256'):
                        return self.reply(400, {'error': 'bad_request'})
                    if stand.inactive and body['mode'] == 'live':
                        return self.reply(409, {'error': 'engine_inactive'})
                    old = stand.reports.get(body['run_id'])
                    if old and old['payload_sha256'] != body['payload_sha256']:
                        return self.reply(409, {'error': 'conflict'})
                    stand.reports[body['run_id']] = body
                    return self.reply(200, {'accepted': True, 'run_id': body['run_id'],
                                            'payload_sha256': body['payload_sha256'], 'replayed': bool(old)})
                if method == 'GET' and route.startswith('reports/'):
                    found = stand.reports.get(unquote(route[len('reports/'):]))
                    if not found:
                        return self.reply(404, {'error': 'not_found'})
                    return self.reply(200, {'accepted': True, 'run_id': found['run_id'], 'mode': found['mode'],
                                            'payload_sha256': found['payload_sha256'], 'accepted_at': NOW,
                                            'report': found})
                if method == 'GET' and route == 'decisions':
                    parse_qs(parts.query)['since']
                    return self.reply(200, {'ok': True, 'decisions': stand.decisions})
                return self.reply(404, {'error': 'not_found'})

            def do_GET(self):
                self.handle_any('GET')

            def do_POST(self):
                self.handle_any('POST')

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base(self):
        return 'http://127.0.0.1:' + str(self.server.server_address[1])

    def client(self, token=TOKEN):
        return Client(token, self.base, loopback_for_tests=True, timeout=5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def posts(self, route):
        return [c for c in self.calls if c['method'] == 'POST' and c['path'] == PREFIX + route]


def clock():
    from engine.core import instant
    return instant(NOW)


def synthetic_report(run_id='makeyourmindup:2026-10-17:test', line='Fixture run'):
    return build_report(run_id, 'synthetic', NOW, 'fixture', NOW, 'held',
                        [objective('new_subscribers', reason='Fixture: not measured')],
                        [{'line': line}], [], [], [{'reason': 'Fixture hold'}])


def envelope(text='TEST FIXTURE ONLY. I asked one useful question.'):
    url = 'https://home.makeyourmindup.ai/p/test-fixture'
    eid = identity('evidence', url, text)
    pack = {'pack_date': '2026-10-17', 'kind': 'daily', 'headline': 'Test fixture',
            'items': [{'platform': 'x', 'text': text}, {'platform': 'linkedin', 'text': text + ' Second.'}]}
    meta = [{'asset_id': 'piece_fixture', 'placement': 'thread', 'variant': 'a', 'evidence_ids': [eid],
             'priority': 1, 'minutes': 3, 'why_now': 'Fixture only.', 'success_check': 'Fixture source compared.'},
            {'asset_id': 'piece_fixture', 'placement': 'native-post', 'variant': 'a', 'evidence_ids': [eid],
             'priority': 2, 'minutes': 4, 'why_now': 'Fixture only.', 'success_check': 'Fixture source compared.',
             'blocked_by': ['video pair not verified']}]
    evidence = [{'evidence_id': eid, 'kind': 'published_piece', 'url': url, 'excerpt': text, 'observed_at': NOW}]
    return seal(pack, evidence, meta, NOW)


def observation(start, end, value):
    return {'platform': 'substack', 'metric': 'new_free', 'unit': 'people', 'window_kind': 'interval',
            'source': 'https://home.makeyourmindup.ai/publish/stats', 'scope': 'publication',
            'start': start, 'end': end, 'captured_at': NOW, 'timezone': 'America/New_York',
            'availability': 'available', 'value': value}


def checks(ok=True):
    return [{'name': 'self_test', 'ok': ok, 'stdout': '', 'stderr': 'Ran 9 tests in 0.1s'},
            {'name': 'doctor_offline', 'ok': True, 'stdout': 'ready', 'stderr': ''},
            {'name': 'dry_run', 'ok': True, 'stdout': json.dumps({'pieces_seen': 2, 'replay_new_tasks': 0,
                                                                   'external_writes': 0}), 'stderr': ''}]


class DigestTests(unittest.TestCase):
    def test_worked_example_digest(self):
        example = read_json(ROOT / 'docs/control-center/engine-report.example.json')
        self.assertEqual(report_digest(example), 'f4351324e84aa1baf6afd1bc4d2ffadb3039ab6399b2309c2717b89a26a0a517')
        self.assertEqual(report_digest(example), example['payload_sha256'])

    def test_canonical_form(self):
        self.assertEqual(canonical_json({'b': [2, {'d': 1, 'c': 'é'}], 'a': None}), '{"a":null,"b":[2,{"c":"é","d":1}]}')

    def test_whole_numbers_are_ints_never_point_zero(self):
        with self.assertRaises(ValueError):
            canonical_json({'value': 1.0})
        self.assertEqual(canonical_json(whole({'value': 1.0, 'x': [2.0, 2.5]})), '{"value":1,"x":[2,2.5]}')

    def test_payload_digest_binds_exact_words_channel_and_target(self):
        base = payload_digest('post', 'x', 'Exact words.', 'https://home.makeyourmindup.ai/p/a')
        self.assertEqual(base, payload_digest('post', 'x', 'Exact words.', 'https://home.makeyourmindup.ai/p/a'))
        self.assertNotEqual(base, payload_digest('post', 'x', 'Exact words!', 'https://home.makeyourmindup.ai/p/a'))
        self.assertNotEqual(base, payload_digest('post', 'linkedin', 'Exact words.', 'https://home.makeyourmindup.ai/p/a'))
        self.assertNotEqual(payload_digest('spend', amount_usd=5, target='a'), payload_digest('spend', amount_usd=6, target='a'))


class ReportTests(unittest.TestCase):
    def test_example_is_valid_against_the_schema(self):
        example = read_json(ROOT / 'docs/control-center/engine-report.example.json')
        self.assertEqual(schema_errors(example, load_schema()), [])

    def test_unknown_fields_are_refused_locally(self):
        report = synthetic_report()
        for mutate in (lambda r: r.update(extra=1), lambda r: r['activity'][0].update(extra=1),
                       lambda r: r['holds'][0].update(send_at='now'), lambda r: r['source'].update(extra=1)):
            bad = copy.deepcopy(report)
            mutate(bad)
            bad['payload_sha256'] = report_digest(bad)
            with self.assertRaisesRegex(ValueError, 'not a protocol field'):
                validate_report(bad)

    def test_unknown_objective_is_null_with_reason_never_zero(self):
        item = objective('new_subscribers', 5, 'missing', reason='Not shown')
        self.assertIsNone(item['value'])
        with self.assertRaises(ValueError):
            objective('new_subscribers', reason=None)
        self.assertEqual(objective('new_subscribers', 0, 'measured')['value'], 0)

    def test_walls_need_their_payloads(self):
        with self.assertRaises(ValueError):
            proposal('p1', 'Post', 'Why', 'prepared', 'post', 'published')
        with self.assertRaises(ValueError):
            proposal('p1', 'Spend', 'Why', 'prepared', 'spend', 'spent')
        with self.assertRaises(ValueError):
            proposal('p1', 'Auto', 'Why', 'autonomous', 'post', 'published', exact_payload='x')

    def test_tampered_digest_refused(self):
        report = synthetic_report()
        report['activity'][0]['line'] = 'Changed after sealing'
        with self.assertRaisesRegex(ValueError, 'payload_sha256'):
            validate_report(report)

    def test_workspace_report_maps_drafts_holds_and_completions(self):
        completions = [{'label': 'Published', 'item_id': 'item_fixture', 'at': NOW, 'confirmed_by': 'Krish',
                        'evidence_url': 'https://x.com/therealkrisho/status/1'}]
        report, error = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()],
                                         completions=completions, mode='synthetic', rev='fixture')
        self.assertIsNone(error)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(len(report['proposals']), 1)
        item = report['proposals'][0]
        self.assertEqual((item['wall'], item['kind'], item['channel']), ('post', 'prepared', 'x'))
        self.assertEqual(item['exact_payload'], 'TEST FIXTURE ONLY. I asked one useful question.')
        self.assertEqual(item['close_condition'], {'event': 'published', 'reference': 'Fixture source compared.'})
        self.assertTrue(item['why'].startswith('Fixture only.'))
        self.assertEqual(item['payload_sha256'], payload_digest('post', 'x', item['exact_payload'], None))
        self.assertEqual(report['holds'][0]['reason'], 'Deferred: prerequisite is not verified')
        self.assertIn('video pair not verified', report['holds'][0]['detail'])
        self.assertEqual(report['events'], [{'event': 'published', 'proposal_id': 'makeyourmindup:item_fixture',
                                             'at': NOW, 'evidence_url': 'https://x.com/therealkrisho/status/1'}])
        self.assertEqual([o['availability'] for o in report['objectives']], ['missing', 'missing'])
        self.assertTrue(all(o['value'] is None and o['reason'] for o in report['objectives']))
        validate_report(report)

    def test_proposal_id_is_stable_and_digest_follows_the_words(self):
        first = workspace_report('daily', 'r1', NOW, [envelope()], rev='fixture')[0]['proposals'][0]
        self.assertEqual(first, workspace_report('daily', 'r1', NOW, [envelope()], rev='fixture')[0]['proposals'][0])
        edited = workspace_report('daily', 'r1', NOW, [envelope('TEST FIXTURE ONLY. I asked a better question.')],
                                  rev='fixture')[0]['proposals'][0]
        self.assertEqual(first['proposal_id'], edited['proposal_id'])
        self.assertNotEqual(first['payload_sha256'], edited['payload_sha256'])

    def test_a_draft_that_names_him_is_held_not_proposed(self):
        # Krish, 2026-10-28: "Remember, no content refers to Krish, ever." An envelope the report reads
        # unsealed, edited after sealing, still meets the copy lint before it becomes a post proposal.
        env = envelope()
        env['pack']['items'][0]['text'] = 'TEST FIXTURE ONLY. Krish asked one useful question.'
        self.assertEqual(len(workspace_report('daily', 'r1', NOW, [envelope()], rev='fixture')[0]['proposals']), 1)
        report = workspace_report('daily', 'r1', NOW, [env], rev='fixture')[0]
        self.assertEqual(report['proposals'], [])
        held = [h['detail'] for h in report['holds'] if h['reason'] == 'Draft could not become a proposal']
        self.assertEqual(len(held), 1)
        self.assertIn('the draft fails the copy lint: copy lint no_name', held[0])

    def test_a_merged_queue_reports_only_this_jobs_work(self):
        env = envelope()
        selected = [{**env['pack']['items'][0], **env['metadata'][0], 'pack_kind': 'daily'},
                    {**env['pack']['items'][0], **env['metadata'][0], 'pack_kind': 'radar', 'item_id': 'item_radar'}]
        queue = {'budget_minutes': 20, 'items': selected, 'deferred': [{'item_id': 'item_radar_2', 'reason': 'daily budget'}]}
        report = workspace_report('daily', 'r1', NOW, [env], queue=queue, rev='fixture')[0]
        self.assertEqual([p['proposal_id'] for p in report['proposals']], ['makeyourmindup:' + env['metadata'][0]['item_id']])

    def test_outreach_is_control_centers_so_pitches_swaps_and_partners_are_held(self):
        # Ruling (Krish, 2026-10-21): People and Visibility own outreach to shows and guests.
        for kind in ('pitches', 'swaps', 'partners'):
            env = envelope()
            env['pack']['kind'] = kind
            report = workspace_report(kind, 'r1', NOW, [env], rev='fixture')[0]
            self.assertEqual(report['proposals'], [], kind)
            self.assertIn("Control Center's People and Visibility own outreach to shows and guests", [h['reason'] for h in report['holds']], kind)
        env = envelope()
        report = workspace_report('daily', 'r1', NOW, [env], rev='fixture')[0]
        self.assertEqual(report['proposals'][0]['wall'], 'post', 'posts still go to Krish')

    def test_completion_needs_krish_and_evidence(self):
        for row in ({'label': 'Published', 'item_id': 'i', 'at': NOW, 'evidence_url': 'https://a.b/c'},
                    {'label': 'Published', 'item_id': 'i', 'at': NOW, 'confirmed_by': 'Krish'},
                    {'label': 'Skipped', 'item_id': 'i', 'at': NOW, 'confirmed_by': 'Krish', 'evidence_url': 'https://a.b/c'}):
            with self.assertRaises(ValueError):
                completion_events([row], NOW)

    def test_new_subscribers_measured_only_from_this_new_york_week(self):
        start = week_start(NOW)
        self.assertEqual(start.isoformat(), '2026-10-12T04:00:00+00:00')
        rows = [observation('2026-10-12T04:00:00Z', '2026-10-13T04:00:00Z', 3),
                observation('2026-10-13T04:00:00Z', '2026-10-14T04:00:00Z', 0)]
        item = new_subscribers(rows, NOW)
        self.assertEqual((item['value'], item['availability']), (3, 'measured'))
        self.assertEqual(item['window_start'], '2026-10-12T04:00:00Z')
        zero = new_subscribers([observation('2026-10-12T04:00:00Z', '2026-10-13T04:00:00Z', 0)], NOW)
        self.assertEqual((zero['value'], zero['availability']), (0, 'measured'))
        gap = new_subscribers([rows[1]], NOW)
        self.assertEqual((gap['value'], gap['availability']), (None, 'missing'))
        unread = new_subscribers([dict(rows[0], availability='signed_out', value=None, reason='signed out')], NOW)
        self.assertIsNone(unread['value'])
        self.assertIn('not shown', unread['reason'])

    def test_numbers_job_without_a_reading_is_degraded(self):
        report = workspace_report('numbers', 'r1', NOW, rev='fixture')[0]
        self.assertEqual(report['status'], 'degraded')

    def test_runner_report_is_honest_about_what_it_cannot_measure(self):
        report, error = runner_report(ROOT, 'makeyourmindup:2026-10-17:runner', NOW, checks(), 'synthetic', True, 'fixture')
        self.assertIsNone(error)
        self.assertEqual(report['status'], 'held')
        for item in report['objectives']:
            self.assertEqual((item['value'], item['availability']), (None, 'missing'))
            self.assertTrue(item['reason'].startswith('Measured only in the publication workspace'))
        self.assertEqual({p['wall'] for p in report['proposals']}, {'strategy'})
        # One strategy proposal per planned experiment template, no more.
        planned = json.loads((ROOT / 'experiments.json').read_text(encoding='utf-8'))['experiments']
        self.assertEqual(len(report['proposals']), sum(e['status'] == 'planned' for e in planned))
        self.assertIn('makeyourmindup:experiment:answer-first-pieces', {p['proposal_id'] for p in report['proposals']})
        self.assertTrue(any('9 tests' in a['line'] for a in report['activity']))
        failed, error = runner_report(ROOT, 'r1', NOW, checks(False), 'synthetic', True, 'fixture')
        self.assertEqual((failed['status'], error), ('degraded', 'offline_checks_failed'))

    def test_report_text_has_no_em_dash(self):
        report = runner_report(ROOT, 'r1', NOW, checks(), 'synthetic', True, 'fixture')[0]
        self.assertNotIn('\u2014', json.dumps(report, ensure_ascii=False))


class ClientTests(unittest.TestCase):
    def test_origin_and_token_rules(self):
        for base in ('http://controlcenter.krishraja.com', 'https://example.com', 'https://controlcenter.krishraja.com.evil'):
            with self.assertRaisesRegex(ProtocolError, 'origin_refused'):
                Client(TOKEN, base)
        with self.assertRaisesRegex(ProtocolError, 'origin_refused'):
            Client(TOKEN, 'http://example.com:80', loopback_for_tests=True)
        with self.assertRaisesRegex(ProtocolError, 'missing_token'):
            Client('', 'https://controlcenter.krishraja.com')
        self.assertNotIn(TOKEN, repr(Client(TOKEN, 'https://controlcenter.krishraja.com')))

    def test_full_loop_in_order(self):
        with StandIn() as stand:
            report = synthetic_report()
            outcome = run(stand.client(), 'test', report['run_id'], lambda d: (report, None), NOW, clock)
            self.assertEqual(outcome['status'], 'succeeded')
            self.assertTrue(outcome['attempt_journaled'])
            sequence = [(c['method'], c['path'][len(PREFIX):]) for c in stand.calls]
            self.assertEqual(sequence, [('POST', 'attempts'), ('GET', 'directive'), ('POST', 'reports'),
                                        ('GET', 'reports/' + report['run_id'].replace(':', '%3A')),
                                        ('GET', 'decisions'), ('POST', 'attempts')])
            started, terminal = (c['body'] for c in stand.posts('attempts'))
            self.assertEqual(started['attempt_id'], terminal['attempt_id'])
            self.assertEqual(started['status'], 'started')
            self.assertNotIn('finished_at', started)
            self.assertEqual((terminal['status'], terminal['error_code']), ('succeeded', None))
            self.assertIn('finished_at', terminal)
            self.assertEqual(stand.posts('reports')[0]['key'], report['run_id'])
            self.assertEqual(outcome['posted'], {'accepted': True, 'conflict': False, 'replayed': False,
                                                 'stored_payload_sha256': report['payload_sha256'], 'readback_matches': True})
            self.assertTrue(all(c['auth'] == 'Bearer ' + TOKEN for c in stand.calls))

    def test_replay_is_answered_replayed(self):
        with StandIn() as stand:
            client, report = stand.client(), synthetic_report()
            self.assertFalse(client.post_report(report)['replayed'])
            again = client.post_report(report)
            self.assertTrue(again['replayed'])
            self.assertTrue(again['readback_matches'])

    def test_conflict_is_read_back_never_retried(self):
        with StandIn() as stand:
            client = stand.client()
            first = synthetic_report()
            client.post_report(first)
            second = synthetic_report(line='A different payload for the same run')
            before = len(stand.posts('reports'))
            outcome = client.post_report(second)
            self.assertEqual(len(stand.posts('reports')), before + 1)
            self.assertTrue(outcome['conflict'])
            self.assertFalse(outcome['accepted'])
            self.assertEqual(outcome['stored_payload_sha256'], first['payload_sha256'])
            self.assertFalse(outcome['readback_matches'])
            self.assertEqual(stand.reports[first['run_id']], first)

    def test_conflict_ends_the_attempt_failed_with_a_code(self):
        with StandIn() as stand:
            stand.client().post_report(synthetic_report())
            changed = synthetic_report(line='Changed')
            outcome = run(stand.client(), 'test', changed['run_id'], lambda d: (changed, None), NOW, clock)
            self.assertEqual((outcome['status'], outcome['error_code']), ('failed', 'report_conflict'))
            self.assertEqual(stand.posts('attempts')[-1]['body']['error_code'], 'report_conflict')

    def test_inactive_engine_is_not_a_conflict(self):
        with StandIn() as stand:
            stand.inactive = True
            live = build_report('makeyourmindup:2026-10-17:live', 'live', NOW, 'fixture', NOW, 'held')
            with self.assertRaisesRegex(ProtocolError, 'engine_inactive'):
                stand.client().post_report(live)

    def test_unauthorized_is_a_failed_attempt_with_a_code(self):
        with StandIn() as stand:
            report = synthetic_report()
            outcome = run(stand.client('gen1_' + 'WrongStandInToken' * 3), 'test', report['run_id'],
                          lambda d: (report, None), NOW, clock)
            self.assertEqual((outcome['status'], outcome['error_code']), ('failed', 'unauthorized'))
            self.assertFalse(outcome['attempt_journaled'])
            self.assertEqual(stand.reports, {})

    def test_failure_after_start_is_journaled(self):
        with StandIn() as stand:
            def broken(directive):
                raise ValueError('source unreadable')
            outcome = run(stand.client(), 'test', 'makeyourmindup:2026-10-17:test', broken, NOW, clock)
            self.assertEqual((outcome['status'], outcome['error_code']), ('failed', 'work_failed'))
            self.assertEqual(stand.posts('attempts')[-1]['body']['status'], 'failed')

    def test_redirect_is_refused(self):
        with StandIn() as stand:
            stand.redirect = True
            with self.assertRaisesRegex(ProtocolError, 'redirect_refused'):
                stand.client().directive()
            self.assertEqual(len(stand.calls), 1)

    def test_unreachable_has_a_code(self):
        client = Client(TOKEN, 'http://127.0.0.1:9', loopback_for_tests=True, timeout=2)
        with self.assertRaises(ProtocolError) as caught:
            client.capabilities()
        self.assertIn(caught.exception.code, ('unreachable', 'timeout'))
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_decisions_bind_to_the_exact_payload(self):
        item = proposal('makeyourmindup:item_a', 'Post', 'Why', 'prepared', 'post', 'published',
                        channel='x', exact_payload='Exact words.')
        result = match_decisions([
            {'proposal_id': 'makeyourmindup:item_a', 'decision': 'approved', 'decided_at': NOW, 'payload_sha256': item['payload_sha256']},
            {'proposal_id': 'makeyourmindup:item_a', 'decision': 'approved', 'decided_at': NOW, 'payload_sha256': 'f' * 64},
            {'proposal_id': 'makeyourmindup:other', 'decision': 'declined', 'decided_at': NOW, 'payload_sha256': 'e' * 64}], [item])
        self.assertEqual([r['usable_approval'] for r in result], [True, False, False])


class CliTests(unittest.TestCase):
    def capture(self, argv, stand, root):
        out, err, logs = io.StringIO(), io.StringIO(), io.StringIO()
        handler = logging.StreamHandler(logs)
        logging.getLogger().addHandler(handler)
        try:
            with patch.object(growth, 'engine_client', lambda: stand.client()), patch.object(growth, 'ROOT', Path(root)), \
                    patch.object(cc_loop, 'runner_checks', lambda r: checks()), patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': TOKEN}), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = growth.main(argv)
        finally:
            logging.getLogger().removeHandler(handler)
        return code, out.getvalue() + err.getvalue() + logs.getvalue()

    def workspace(self, folder):
        for name in ('experiments.json', 'channels.json', 'journeys.json'):
            write_json(Path(folder) / name, read_json(ROOT / name))
        path = Path(folder) / 'envelope.json'
        write_json(path, envelope())
        return str(path)

    def test_workspace_start_then_finish_uses_one_attempt_and_never_logs_the_token(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            env = self.workspace(folder)
            stand.decisions = []
            code, text = self.capture(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 0)
            self.assertIn(PRIVATE, text)  # The local workspace shows Krish the directive.
            code, more = self.capture(['cc', 'finish', '--job', 'daily', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                       '--now', NOW], stand, folder)
            self.assertEqual(code, 0, more)
            text += more
            attempts = [c['body'] for c in stand.posts('attempts')]
            self.assertEqual([a['status'] for a in attempts], ['started', 'succeeded'])
            self.assertEqual(len({a['attempt_id'] for a in attempts}), 1)
            self.assertEqual(len(stand.posts('reports')), 1)
            self.assertIn('readback digest matches', text)
            self.assertNotIn(TOKEN, text)
            ledger = read_json(Path(folder) / '.scratch/cc/proposals.json')
            self.assertEqual(len(ledger), 1)
            self.assertFalse((Path(folder) / '.scratch/cc/daily.state.json').exists())

    def test_approval_on_reported_words_is_reported_and_nothing_is_sent(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            env = self.workspace(folder)
            report = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [read_json(env)], rev='x')[0]
            item = report['proposals'][0]
            stand.decisions = [{'proposal_id': item['proposal_id'], 'decision': 'approved', 'decided_at': NOW,
                                'payload_sha256': item['payload_sha256']}]
            code, text = self.capture(['cc', 'run', '--job', 'daily', '--envelope', env, '--deliver', '--mode', 'synthetic',
                                       '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            self.assertIn('approved exactly: ' + item['proposal_id'], text)
            saved = read_json(Path(folder) / '.scratch/cc/decisions.json')['decisions']
            self.assertTrue(saved[0]['usable_approval'])
            self.assertEqual({c['path'] for c in stand.calls if c['method'] == 'POST'},
                             {PREFIX + 'attempts', PREFIX + 'reports'})

    def test_runner_output_keeps_directive_and_token_off_the_public_log(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            code, text = self.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            self.assertNotIn(PRIVATE, text)
            self.assertNotIn(TOKEN, text)
            report = stand.posts('reports')[0]['body']
            self.assertEqual(report['run_id'], 'makeyourmindup:2026-10-17:runner')
            self.assertEqual(report['mode'], 'synthetic')

    def test_unauthorized_cli_exits_non_zero_without_the_token(self):
        with StandIn('gen1_' + 'TheServerExpectsAnother' * 2) as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            code, text = self.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 1)
            self.assertIn('failed unauthorized', text)
            self.assertNotIn(TOKEN, text)

    def test_dry_runs_make_no_call_and_read_no_key(self):
        with tempfile.TemporaryDirectory() as folder:
            env = self.workspace(folder)
            out = io.StringIO()
            with patch.object(growth, 'engine_client', side_effect=AssertionError('key read')), patch.object(growth, 'ROOT', Path(folder)), \
                    patch.object(cc_loop, 'runner_checks', lambda r: checks()), contextlib.redirect_stdout(out):
                self.assertEqual(growth.main(['cc', 'start', '--job', 'daily']), 0)
                self.assertEqual(growth.main(['cc', 'finish', '--job', 'daily', '--envelope', env, '--now', NOW]), 0)
                self.assertEqual(growth.main(['cc', 'runner', '--now', NOW]), 0)
            self.assertIn('no Control Center call', out.getvalue())
            validate_report(read_json(Path(folder) / '.scratch/cc/report-daily.json'))

    def test_missing_key_is_named_without_a_value(self):
        with patch.object(growth, 'ENGINE_TOKEN_FILE', Path('/nonexistent/engine-token')), patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': ''}):
            with self.assertRaisesRegex(ValueError, 'CONTROL_CENTER_ENGINE_TOKEN'):
                growth.engine_client()

    def test_dispatch_for_another_engine_is_refused(self):
        with patch.dict('os.environ', {'CC_DISPATCH_ENGINE_ID': 'growth-heartside'}), contextlib.redirect_stdout(io.StringIO()):
            args = argparse.Namespace(cc_cmd='runner', now=NOW, run_id=None, deliver=True, mode='synthetic')
            self.assertEqual(cc_loop.cli(args, ROOT, lambda: (_ for _ in ()).throw(AssertionError('client'))), 1)

    def test_workflow_is_least_privilege_and_wired_to_the_dispatch(self):
        text = (ROOT / '.github/workflows/control-center.yml').read_text(encoding='utf-8')
        for needle in ('cc-growth-directive', 'workflow_dispatch', 'contents: read', 'concurrency:', 'timeout-minutes:',
                       '${{ secrets.CONTROL_CENTER_ENGINE_TOKEN }}', '${{ vars.CONTROL_CENTER_URL }}',
                       'python growth.py cc runner --deliver'):
            self.assertIn(needle, text)
        self.assertNotIn('upload-artifact', text)


# Protocol 1.5.0: Krish's approved voice rules ride the directive. Synthetic rules only.
TASTE_RULE = 'Follow these for how it is written, never to choose what it is about.'
SYNTHETIC_RULE = {'layer': 'sentence', 'rule': 'Synthetic rule: lead with the noun', 'his_words': 'synthetic words',
                  'what_it_means': 'Synthetic meaning for the fixture'}


def directive_with(**extra):
    body = {'schema_version': '1.5.0', 'directive_id': 'makeyourmindup:2026-10-26', 'engine_id': ENGINE_ID,
            'for_date': '2026-10-26', 'aim': None, 'objectives': [],
            'next_action': {'proposal_id': None, 'instruction': 'fixture', 'why': 'fixture', 'close_condition': None},
            'decisions_since': [], 'constraints': {'walls': 'fixture', 'spend_cap_usd': 0, 'max_actions': 5}}
    body.update(extra)
    return {'ok': True, 'chosen_by': 'rule', 'directive': body}


class VoiceRuleTests(unittest.TestCase):
    def test_approved_rules_reach_drafting_as_a_labelled_block(self):
        directive = directive_with(taste={'rule': TASTE_RULE, 'approved_voice_rules': [SYNTHETIC_RULE]})
        self.assertEqual(voice_rules(directive)[0], 'rules')
        text = '\n'.join(describe(directive))
        self.assertIn("KRISH'S APPROVED VOICE RULES", text)
        self.assertIn('[sentence] Synthetic rule: lead with the noun', text)
        self.assertIn('his words: "synthetic words"', text)
        self.assertIn('what it means: Synthetic meaning for the fixture', text)
        self.assertIn('never to choose what it is about', text)
        self.assertIn('never to judge, score, rank or check a draft', text)
        self.assertIn(TASTE_RULE, text)

    def test_empty_means_none_approved_and_nothing_is_invented(self):
        directive = directive_with(taste={'rule': TASTE_RULE, 'approved_voice_rules': []})
        self.assertEqual(voice_rules(directive), ('none', TASTE_RULE, []))
        text = '\n'.join(voice_block(directive))
        self.assertIn('None approved yet. Do not invent one', text)
        self.assertNotIn('1. ', text)

    def test_absent_or_malformed_means_unknown(self):
        for directive in (directive_with(), directive_with(taste=None), directive_with(taste={'rule': 'x'}),
                          directive_with(taste='rules'), {}, None):
            self.assertEqual(voice_rules(directive)[0], 'absent')
            self.assertIn('Could not be read today', '\n'.join(voice_block(directive)))
        partial = directive_with(taste={'rule': TASTE_RULE, 'approved_voice_rules': [{'rule': ''}, 'x', SYNTHETIC_RULE]})
        self.assertEqual(len(voice_rules(partial)[2]), 1)

    def test_rules_never_feed_a_judge_scorer_ranker_or_gate(self):
        # The check, the queue (ranker) and the report builder never read the directive's taste.
        for name in ('engine/packs.py', 'engine/operations.py', 'engine/control_center.py', 'engine/core.py'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertNotIn('taste', text, name)
            self.assertNotIn('voice_rules', text, name)
        source = (ROOT / 'engine/cc_loop.py').read_text(encoding='utf-8')
        for name in ('def workspace_report', 'def runner_report', 'def item_proposal', 'def _items'):
            start = source.index(name)
            end = source.index('\ndef ', start + 1)
            self.assertNotIn('voice', source[start:end], name)
        plain = workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()], rev='x')[0]
        self.assertEqual(plain, workspace_report('daily', 'makeyourmindup:2026-10-17:daily', NOW, [envelope()], rev='x')[0])


class VoiceRuleCliTests(unittest.TestCase):
    capture = CliTests.capture
    workspace = CliTests.workspace

    def run_start(self, extra):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            stand.directive_extra = extra
            code, text = self.capture(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', NOW],
                                      stand, folder)
            path = Path(folder) / '.scratch/cc/voice-rules.txt'
            saved = path.read_text(encoding='utf-8') if path.exists() else None
        return code, text, saved

    def test_schema_1_5_0_with_taste_and_unknown_fields_is_accepted_and_printed(self):
        code, text, saved = self.run_start({'schema_version': '1.5.0', 'some_future_field': {'x': 1},
                                            'taste': {'rule': TASTE_RULE, 'approved_voice_rules': [SYNTHETIC_RULE]}})
        self.assertEqual(code, 0, text)
        self.assertIn('Synthetic rule: lead with the noun', text)
        self.assertIn('Synthetic rule: lead with the noun', saved)
        self.assertNotIn(TOKEN, text + saved)

    def test_directive_without_taste_is_accepted_and_says_unknown(self):
        code, text, saved = self.run_start({'schema_version': '1.5.0'})
        self.assertEqual(code, 0, text)
        self.assertIn('Could not be read today', saved)

    def test_dry_run_start_clears_stale_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            stale = Path(folder) / '.scratch/cc/voice-rules.txt'
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text('yesterday', encoding='utf-8')
            with patch.object(growth, 'engine_client', side_effect=AssertionError('key read')), \
                    patch.object(growth, 'ROOT', Path(folder)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(growth.main(['cc', 'start', '--job', 'daily']), 0)
            self.assertFalse(stale.exists())

    def test_runner_never_prints_the_rules(self):
        with StandIn() as stand, tempfile.TemporaryDirectory() as folder:
            self.workspace(folder)
            stand.directive_extra = {'schema_version': '1.5.0',
                                     'taste': {'rule': TASTE_RULE, 'approved_voice_rules': [SYNTHETIC_RULE]}}
            code, text = self.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', NOW], stand, folder)
            self.assertEqual(code, 0, text)
            self.assertNotIn('synthetic words', text)
            self.assertNotIn('voice', canonical_json(stand.posts('reports')[0]['body']).lower())


if __name__ == '__main__':
    unittest.main()
