"""Lane L0 release against local stand-ins for Control Center and Buffer only.

No test reaches controlcenter.krishraja.com, api.buffer.com or any media host.
Every word, id, digest and byte here is synthetic.
"""
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

try:
    from test_control_center import TOKEN, StandIn
except ImportError:  # run as tests.test_run_autorelease
    from tests.test_control_center import TOKEN, StandIn

from engine.control_center import amended_digest, build_report, objective, proposal
from engine.run import autorelease, buffer_api
from engine.run.autorelease import (line_digest, may_release, parse_manifest, show_before_post_until,
                                    staged_report_run_id, standing_derivative_allowed)
from engine.run.buffer_api import Buffer, BufferAuthError, BufferError, CarryHold

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-03T15:00:00Z'
DUE = '2026-11-04T14:00:00Z'
BKEY = 'buffer-stand-in-key-' + 'NeverReal' * 3
PLAN = 'makeyourmindup:plan:w45-w52'
GOLIVE = 'makeyourmindup:golive:2026-W45:week'
P_THREADS, P_X, P_LINKEDIN, P_UNSIGNED = ('aaaaaaaaaaaaaaaaaaaaaa01', 'aaaaaaaaaaaaaaaaaaaaaa02',
                                          'aaaaaaaaaaaaaaaaaaaaaa03', 'aaaaaaaaaaaaaaaaaaaaaa09')
CH_THREADS, CH_X, CH_LINKEDIN = ('cccccccccccccccccccccc01', 'cccccccccccccccccccccc02', 'cccccccccccccccccccccc03')
WORDS_THREADS = 'Synthetic fixture words for the threads slot.'
WORDS_X = 'Synthetic fixture words for the x slot.'
WORDS_LINKEDIN = 'Synthetic fixture words for the linkedin slot.'
IMAGE = b'synthetic autorelease image bytes\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BufferStandIn:
    """A local stand-in for Buffer's GraphQL endpoint and its media host."""

    def __init__(self, key=BKEY):
        self.key = key
        self.posts, self.media, self.calls = {}, {}, []
        self.fail_next = []  # HTTP statuses to answer before the real reply
        self.refuse_edit = None
        stand = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body, raw=None):
                data = raw if raw is not None else json.dumps(body).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                name = self.path.rsplit('/', 1)[-1]
                stand.calls.append({'op': 'media', 'name': name, 'auth': self.headers.get('Authorization')})
                if name not in stand.media:
                    return self.reply(404, {})
                return self.reply(200, None, stand.media[name])

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                op = body.get('operationName')
                variables = body.get('variables') or {}
                stand.calls.append({'op': op, 'variables': copy.deepcopy(variables), 'query': body.get('query')})
                if self.headers.get('Authorization') != 'Bearer ' + stand.key:
                    return self.reply(401, {'errors': [{'message': 'unauthorized'}]})
                if stand.fail_next:
                    return self.reply(stand.fail_next.pop(0), {'errors': [{'message': 'fixture'}]})
                if op == 'AccountCheck':
                    return self.reply(200, {'data': {'account': {'id': 'acct', 'organizations': [{'id': 'org1'}]}}})
                if op == 'GetPost':
                    post = stand.posts.get(variables['input']['id'])
                    if post is None:
                        return self.reply(200, {'errors': [{'message': 'not found', 'extensions': {'code': 'NOT_FOUND'}}]})
                    return self.reply(200, {'data': {'post': copy.deepcopy(post)}})
                if op == 'ListPosts':
                    wanted = (variables['input'].get('filter') or {}).get('status')
                    nodes = [p for p in stand.posts.values() if not wanted or p['status'] in wanted]
                    return self.reply(200, {'data': {'posts': {'edges': [{'node': n} for n in nodes],
                                                               'pageInfo': {'hasNextPage': False, 'endCursor': None}}}})
                if op == 'ScheduleDraft':
                    data = variables['input']
                    if stand.refuse_edit:
                        return self.reply(200, {'data': {'editPost': {'__typename': stand.refuse_edit, 'message': 'x'}}})
                    post = stand.posts[data['id']]
                    post.update(text=data['text'], dueAt=data['dueAt'].replace('Z', '.000Z'), status='scheduled')
                    return self.reply(200, {'data': {'editPost': {'__typename': 'PostActionSuccess',
                                                                  'post': copy.deepcopy(post)}}})
                return self.reply(400, {'errors': [{'message': 'unknown operation'}]})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)

    @property
    def base(self):
        return 'http://127.0.0.1:' + str(self.server.server_address[1])

    def reset(self):
        self.posts, self.media, self.calls, self.fail_next, self.refuse_edit = {}, {}, [], [], None

    def client(self, key=BKEY):
        return Buffer(key, self.base, timeout=5, loopback_for_tests=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def mutations(self):
        return [c for c in self.calls if c['op'] == 'ScheduleDraft']

    def touched(self, post_id):
        return [c for c in self.calls if json.dumps(c.get('variables', {})).find(post_id) >= 0]


def fetch(url):
    return buffer_api.download_sha256(url, loopback_for_tests=True)


def line(slot_id, channel, words, draft, assets=(), mode='engine', due=DUE):
    item = {'slot_id': slot_id, 'channel': channel, 'format': 'post', 'due_at': due, 'link_placement': None,
            'publish_mode': mode, 'buffer_draft_id': draft, 'words': words, 'assets': list(assets),
            'payload_sha256': None}
    item['payload_sha256'] = line_digest(item)
    return item


def manifest(lines):
    return json.dumps({'schema': 'growth-golive-manifest/1', 'run_id': 'makeyourmindup:2026-W45:week',
                       'slots': lines}, sort_keys=True, separators=(',', ':'))


def staged_report(item):
    run_id = staged_report_run_id(item['proposal_id'], item['payload_sha256'])
    objectives = [objective('new_subscribers', reason='synthetic fixture'),
                  objective('paid_boosts_usd', reason='synthetic fixture')]
    return build_report(run_id, 'live', '2026-11-01T12:00:00Z', 'synthetic-revision', '2026-11-01T12:00:00Z',
                        'ready', objectives, [], [item], [], [])


class Fixture:
    """One standing plan, one go-live of three slots, Buffer drafts for each and
    one unsigned draft that nothing may touch."""

    def __init__(self, cc, buf):
        self.cc, self.buf = cc, buf
        buf.media['img1.png'] = IMAGE
        self.lines = [line('threads-1', 'threads', WORDS_THREADS, P_THREADS, [sha(IMAGE)]),
                      line('x-1', 'x', WORDS_X, P_X),
                      line('linkedin-1', 'linkedin', WORDS_LINKEDIN, P_LINKEDIN, mode='krish_click', due=None)]
        image = {'type': 'image', 'source': buf.base + '/media/img1.png', 'mimeType': 'image/png',
                 'image': {'altText': 'Synthetic alt text', 'userTags': None}}
        common = {'status': 'draft', 'dueAt': None, 'schedulingType': 'automatic', 'via': 'api'}
        buf.posts = {
            P_THREADS: dict(common, id=P_THREADS, text=WORDS_THREADS, channelId=CH_THREADS, channelService='threads',
                            assets=[image], metadata={'__typename': 'ThreadsPostMetadata', 'type': 'post',
                                                      'threadCount': 0, 'linkAttachment': None}),
            P_X: dict(common, id=P_X, text=WORDS_X, channelId=CH_X, channelService='twitter', assets=[],
                      metadata={'__typename': 'TwitterPostMetadata', 'type': 'post', 'isAiGenerated': False,
                                'threadCount': 0, 'retweet': None}),
            P_LINKEDIN: dict(common, id=P_LINKEDIN, text=WORDS_LINKEDIN, channelId=CH_LINKEDIN,
                             channelService='linkedin', assets=[], metadata=None),
            P_UNSIGNED: dict(common, id=P_UNSIGNED, text='Synthetic unsigned draft.', channelId=CH_THREADS,
                             channelService='threads', assets=[], metadata=None)}
        self.plan = proposal(PLAN, 'Synthetic standing plan', 'Synthetic why', 'advice', 'strategy', 'reviewed',
                             exact_payload='Synthetic standing plan words.', stage='plan')
        self.publish(self.lines)
        cc.decisions = [self.decision(self.plan, '2026-11-01T12:00:00Z'),
                        self.decision(self.golive, '2026-11-03T14:00:00Z')]

    def publish(self, lines):
        self.golive = proposal(GOLIVE, 'Synthetic go-live', 'Synthetic why', 'prepared', 'post', 'published',
                               channel='buffer', exact_payload=manifest(lines), stage='go_live',
                               parent_proposal_id=PLAN)
        for item in (self.plan, self.golive):
            report = staged_report(item)
            self.cc.reports[report['run_id']] = report
        return self.golive

    @staticmethod
    def decision(item, at, **extra):
        return dict({'proposal_id': item['proposal_id'], 'decision': 'approved', 'decided_at': at,
                     'payload_sha256': item['payload_sha256'], 'stage': item['stage'], 'amended': False}, **extra)


class AutoreleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = StandIn().__enter__()
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.fix = Fixture(self.cc, self.buf)

    def run_once(self, deliver=True, now=NOW, buffer=None):
        summary, code = autorelease.autorelease(self.cc.client(), buffer or self.buf.client(), now, deliver, fetch)
        return summary, code

    def test_happy_path_schedules_once_with_the_full_payload(self):
        summary, code = self.run_once()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'krish_click': 1, 'scheduled': 2})
        self.assertEqual(summary['mutations'], 2)
        self.assertEqual(len(self.buf.mutations()), 2)
        threads = self.buf.posts[P_THREADS]
        self.assertEqual((threads['status'], threads['text']), ('scheduled', WORDS_THREADS))
        sent = [c['variables']['input'] for c in self.buf.mutations() if c['variables']['input']['id'] == P_THREADS][0]
        # F01: the edit carries words, every asset with its alt text, metadata and the exact time.
        self.assertEqual(sent['mode'], 'customScheduled')
        self.assertEqual(sent['dueAt'], DUE)
        self.assertEqual(sent['schedulingType'], 'automatic')
        self.assertIs(sent['saveToDraft'], False)
        self.assertEqual(sent['assets'], [{'image': {'url': self.buf.base + '/media/img1.png',
                                                     'metadata': {'altText': 'Synthetic alt text'}}}])
        self.assertEqual(sent['metadata'], {'threads': {'type': 'post'}})
        self.assertEqual(sent['text'], WORDS_THREADS)
        # The media download never carries a key.
        self.assertTrue(all(c['auth'] is None for c in self.buf.calls if c['op'] == 'media'))

    def test_a_second_run_is_a_no_op(self):
        self.run_once()
        before = len(self.buf.mutations())
        summary, code = self.run_once()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.buf.mutations()), before)
        self.assertEqual(summary['mutations'], 0)
        self.assertEqual(summary['slots'], {'already_scheduled': 2, 'krish_click': 1})

    def test_one_changed_asset_byte_holds(self):
        self.buf.media['img1.png'] = IMAGE[:-1] + b'!'
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'draft_differs_from_signed': 1})
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')
        self.assertNotIn(P_THREADS, json.dumps([c['variables'] for c in self.buf.mutations()]))

    def test_one_changed_word_holds(self):
        self.buf.posts[P_X]['text'] = WORDS_X.replace('words', 'word')
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'draft_differs_from_signed': 1})
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')
        self.assertEqual(summary['slots'].get('scheduled'), 1)

    def test_a_missing_asset_download_holds(self):
        del self.buf.media['img1.png']
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'asset_download_failed': 1})
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')

    def test_an_unsigned_slot_is_never_touched(self):
        self.run_once()
        self.assertEqual(self.buf.touched(P_UNSIGNED), [])
        self.assertEqual(self.buf.posts[P_UNSIGNED]['status'], 'draft')

    def test_no_approved_go_live_touches_nothing(self):
        self.cc.decisions = [d for d in self.cc.decisions if d['stage'] != 'go_live']
        summary, code = self.run_once()
        self.assertEqual(code, 0)
        self.assertEqual(summary['golives']['releasable'], 0)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'GetPost'], [])

    def test_an_unapproved_plan_or_missing_report_releases_nothing(self):
        self.cc.decisions = [d for d in self.cc.decisions if d['stage'] != 'plan']
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['releasable'], 0)
        self.assertIn('plan_not_approved', summary['golives']['held'])
        self.assertEqual(self.buf.mutations(), [])
        # A go-live whose report cannot be read back by its decided digest is never guessed.
        self.cc.decisions = [Fixture.decision(self.fix.plan, '2026-11-01T12:00:00Z'),
                             Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', payload_sha256='e' * 64)]
        summary, _ = self.run_once()
        self.assertEqual(summary['golives'], {'releasable': 0, 'held': {'golive_report_missing': 1}})
        self.assertEqual(self.buf.mutations(), [])
        # A synthetic report never releases.
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z')
        for report in self.cc.reports.values():
            report['mode'] = 'synthetic'
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['releasable'], 0)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_declined_go_live_stops(self):
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-03T14:30:00Z', decision='declined'))
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['releasable'], 0)
        self.assertEqual(self.buf.mutations(), [])

    def test_an_amended_decision_posts_his_version(self):
        his_words = 'Synthetic words Krish amended for the threads slot.'
        amended = [dict(self.fix.lines[0], words=his_words), self.fix.lines[2]]  # he also dropped x-1
        text = manifest(amended)
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None,
                                                 amended_sha256=amended_digest(None, text))
        summary, code = self.run_once()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'krish_click': 1, 'scheduled': 1, 'unsigned': 1})
        self.assertEqual(self.buf.posts[P_THREADS]['text'], his_words)
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')
        self.assertEqual(self.buf.touched(P_X), [])
        # A second run counts his version as done.
        summary, _ = self.run_once()
        self.assertEqual(summary['mutations'], 0)
        self.assertEqual(summary['slots']['already_scheduled'], 1)

    def test_an_amendment_with_a_bad_digest_releases_nothing(self):
        text = manifest([dict(self.fix.lines[0], words='Synthetic other words.')])
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None, amended_sha256='0' * 64)
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['held'], {'amended_digest_mismatch': 1})
        self.assertEqual(self.buf.mutations(), [])

    def test_an_amendment_that_moves_the_draft_holds(self):
        moved = [dict(self.fix.lines[0], buffer_draft_id=P_UNSIGNED)]
        text = manifest(moved)
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None,
                                                 amended_sha256=amended_digest(None, text))
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'amendment_not_releasable': 1})
        self.assertEqual(self.buf.mutations(), [])

    def test_linkedin_stays_a_draft_and_is_never_read(self):
        self.run_once()
        self.assertEqual(self.buf.posts[P_LINKEDIN]['status'], 'draft')
        self.assertEqual(self.buf.touched(P_LINKEDIN), [])
        # Even a manifest line claiming engine mode on LinkedIn is never scheduled.
        lines = [dict(self.fix.lines[2], publish_mode='engine', due_at=DUE)]
        lines[0]['payload_sha256'] = line_digest(lines[0])
        golive = self.fix.publish(lines)
        self.cc.decisions[-1] = Fixture.decision(golive, '2026-11-03T14:00:00Z')
        summary, _ = self.run_once()
        self.assertEqual(summary['slots'], {'krish_click': 1})
        self.assertEqual(self.buf.posts[P_LINKEDIN]['status'], 'draft')

    def test_a_past_due_time_holds(self):
        summary, _ = self.run_once(now='2026-11-04T13:56:00Z')
        self.assertEqual(summary['holds'], {'due_time_passed': 2})
        self.assertEqual(self.buf.mutations(), [])

    def test_a_refused_key_fails_loudly(self):
        summary, code = self.run_once(buffer=self.buf.client('buffer-wrong-key'))
        self.assertEqual(code, 1)
        self.assertEqual(summary['error'], 'buffer_key_refused')
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(self.cc.calls, [])

    def test_the_dry_run_sends_no_mutation(self):
        summary, code = self.run_once(deliver=False)
        self.assertEqual(code, 0)
        self.assertEqual(summary['slots'], {'krish_click': 1, 'would_schedule': 2})
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')

    def test_a_refused_edit_is_read_back_and_held_never_resent(self):
        self.buf.refuse_edit = 'InvalidInputError'
        summary, code = self.run_once()
        self.assertEqual(code, 0)
        self.assertEqual(summary['holds'], {'edit_refused_invalid_input_error': 2})
        self.assertEqual(len(self.buf.mutations()), 2)

    def test_scheduled_in_other_words_is_held_loudly_not_counted(self):
        self.buf.posts[P_X].update(status='scheduled', dueAt=DUE, text='Synthetic words someone else scheduled.')
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'live_post_differs_from_signed': 1})

    def test_the_summary_carries_no_words_urls_or_ids(self):
        out = io.StringIO()
        code = autorelease.main(['autorelease', '--deliver', '--now', NOW], make_cc=self.cc.client,
                                make_buffer=self.buf.client, fetch=fetch, out=lambda s: out.write(s + '\n'))
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        summary = json.loads(text)
        self.assertEqual(summary['slots']['scheduled'], 2)
        for secret in (WORDS_THREADS, WORDS_X, WORDS_LINKEDIN, 'http', P_THREADS, P_X, CH_THREADS, GOLIVE, PLAN,
                       BKEY, TOKEN, self.fix.golive['payload_sha256']):
            self.assertNotIn(secret, text)


class BufferClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.buf.__exit__()

    def setUp(self):
        self.buf.reset()
        Fixture(StandInless(), self.buf)

    def test_one_retry_on_5xx_only(self):
        api = self.buf.client()
        self.buf.fail_next = [502]
        self.assertEqual(api.get_post(P_X)['id'], P_X)
        self.assertEqual(api.requests, 2)
        api = self.buf.client()
        self.buf.fail_next = [502, 503]
        with self.assertRaises(BufferError) as caught:
            api.get_post(P_X)
        self.assertEqual((caught.exception.code, api.requests), ('buffer_server_error', 2))
        api = self.buf.client()
        self.buf.fail_next = [400]
        with self.assertRaises(BufferError) as caught:
            api.get_post(P_X)
        self.assertEqual((caught.exception.code, api.requests), ('buffer_rejected', 1))

    def test_401_and_403_are_auth_errors_never_retried(self):
        api = self.buf.client('wrong-key')
        with self.assertRaises(BufferAuthError) as caught:
            api.account_check()
        self.assertEqual((caught.exception.code, api.requests), ('buffer_key_refused', 1))
        api = self.buf.client()
        self.buf.fail_next = [403]
        with self.assertRaises(BufferAuthError):
            api.list_posts('org1', 'draft')

    def test_errors_carry_no_key_or_url(self):
        api = self.buf.client('wrong-key')
        try:
            api.get_post(P_X)
        except BufferError as error:
            self.assertNotIn('wrong-key', str(error))
            self.assertNotIn('127.0.0.1', str(error))
        self.assertNotIn('wrong-key', repr(api))

    def test_reads(self):
        api = self.buf.client()
        self.assertEqual(api.account_check(), {'account': True, 'organization_ids': ['org1']})
        self.assertEqual(len(api.list_posts('org1', 'draft', [CH_THREADS], NOW)), 4)
        with self.assertRaises(BufferError):
            api.get_post('not-an-id')

    def test_only_a_draft_is_scheduled_and_documents_and_stickers_hold(self):
        api = self.buf.client()
        post = api.get_post(P_X)
        post['status'] = 'scheduled'
        with self.assertRaisesRegex(BufferError, 'not_a_draft'):
            api.schedule_draft(post, DUE)
        self.assertEqual(api.mutations, 0)
        doc = dict(post, status='draft', assets=[{'type': 'document', 'source': 'https://example.invalid/a.pdf'}])
        with self.assertRaisesRegex(CarryHold, 'document_asset_held'):
            buffer_api.edit_input(doc, DUE)
        story = dict(post, status='draft', metadata={'__typename': 'InstagramPostMetadata', 'type': 'story',
                                                     'shouldShareToFeed': False, 'link': 'https://example.invalid'})
        with self.assertRaisesRegex(CarryHold, 'instagram_link_sticker'):
            buffer_api.edit_input(story, DUE)

    def test_the_endpoint_and_asset_urls_are_pinned(self):
        with self.assertRaises(BufferError):
            Buffer(BKEY, 'https://elsewhere.invalid')
        with self.assertRaises(BufferError):
            Buffer('', buffer_api.ENDPOINT)
        with self.assertRaisesRegex(BufferError, 'asset_url_refused'):
            buffer_api.download_sha256('http://example.invalid/a.png')

    def test_an_asset_over_the_cap_holds(self):
        with self.assertRaisesRegex(BufferError, 'asset_too_large'):
            buffer_api.download_sha256(self.buf.base + '/media/img1.png', cap=4, loopback_for_tests=True)


class StandInless:
    def __init__(self):
        self.reports, self.decisions = {}, []


class SourceAndWorkflowTests(unittest.TestCase):
    def test_no_immediate_publish_or_removal_path_exists(self):
        for name in ('buffer_api.py', 'autorelease.py'):
            text = (ROOT / 'engine' / 'run' / name).read_text(encoding='utf-8')
            for word in ('shareNow', 'deletePost', 'shareNext', 'addToQueue'):
                self.assertNotIn(word, text, name)
        self.assertEqual(re.findall(r'mutation (\w+)', buffer_api.SCHEDULE_MUTATION), ['ScheduleDraft'])
        self.assertIn('editPost(input: $input)', buffer_api.SCHEDULE_MUTATION)
        self.assertEqual(buffer_api.SCHEDULE_MODE, 'customScheduled')

    def test_the_workflow_names_only_the_expected_secrets(self):
        text = (ROOT / '.github' / 'workflows' / 'release.yml').read_text(encoding='utf-8')
        self.assertEqual(set(re.findall(r'secrets\.([A-Z_]+)', text)), {'CONTROL_CENTER_ENGINE_TOKEN', 'BUFFER_API_KEY'})
        self.assertEqual(set(re.findall(r'vars\.([A-Z_]+)', text)), {'CONTROL_CENTER_URL'})
        for needle in ("cron: '*/30 * * * *'", 'workflow_dispatch', 'contents: read', 'group: release',
                       'cancel-in-progress: false', 'timeout-minutes: 10', "python-version: '3.12'",
                       'actions/checkout@v7.0.1', 'actions/setup-python@v7.0.0', 'persist-credentials: false',
                       'python growth.py run autorelease --deliver', 'exit 0', 'exit 1'):
            self.assertIn(needle, text)
        for banned in ('upload-artifact', 'GITHUB_TOKEN', 'contents: write', 'set -x'):
            self.assertNotIn(banned, text)
        # Not configured is a notice and a clean exit; a missing Control Center key fails loudly.
        self.assertLess(text.index('BUFFER_API_KEY" ]'), text.index('exit 0'))
        self.assertLess(text.index('CONTROL_CENTER_ENGINE_TOKEN" ]'), text.index('exit 1'))

    def test_the_cli_routes_and_refuses_without_a_key(self):
        import growth
        out = io.StringIO()
        with patch.dict('os.environ', {'BUFFER_API_KEY': ''}), contextlib.redirect_stdout(out):
            self.assertEqual(growth.main(['run', 'autorelease']), 1)
        self.assertEqual(json.loads(out.getvalue())['error'], 'buffer_key_missing')
        out = io.StringIO()
        with patch.dict('os.environ', {'BUFFER_API_KEY': BKEY, 'CONTROL_CENTER_ENGINE_TOKEN': '',
                                       'GROWTH_ENGINE_TOKEN': ''}), contextlib.redirect_stdout(out):
            self.assertEqual(growth.main(['run', 'autorelease', '--deliver']), 1)
        self.assertEqual(json.loads(out.getvalue())['error'], 'control_center_missing_token')


class ManifestTests(unittest.TestCase):
    def test_engine_lines_must_recompute(self):
        good = line('x-1', 'x', WORDS_X, P_X)
        self.assertIn('x-1', parse_manifest(manifest([good])))
        bad = dict(good, words=WORDS_X + ' Edited.')
        with self.assertRaisesRegex(ValueError, 'manifest_line_digest_mismatch'):
            parse_manifest(manifest([bad]))
        self.assertIn('x-1', parse_manifest(manifest([bad]), engine=False))
        for broken in ('not json', manifest([good, good]), json.dumps({'schema': 'other', 'slots': []}),
                       manifest([dict(good, extra=1)]), manifest([dict(good, buffer_draft_id='nope')])):
            with self.assertRaises(ValueError):
                parse_manifest(broken)

    def test_report_address_is_bound_to_the_decided_digest(self):
        self.assertEqual(staged_report_run_id(GOLIVE, 'ab' * 32), GOLIVE + ':' + 'ab' * 6)
        self.assertIsNone(staged_report_run_id(GOLIVE, 'not-a-digest'))
        self.assertIsNone(staged_report_run_id('x' * 110, 'ab' * 32))


class ShowBeforePostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.slot = {'format': 'quote-card'}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, value):
        (self.root / 'invariants').mkdir(exist_ok=True)
        (self.root / 'invariants' / 'authority.json').write_text(json.dumps(value), encoding='utf-8')

    def test_the_real_authority_file_names_derivatives_and_opens_after_the_date(self):
        # Krish, 27 Oct: derivatives of an approved piece go out everywhere once the preview weeks end.
        from engine.run.autorelease import derivative_formats
        real = derivative_formats()
        self.assertTrue({'quote-card', 'receipt-card', 'note', 'story-frame', 'short-video'} <= real)
        self.assertFalse({'carousel', 'meme'} & real, 'new formats need his eyes, item by item')
        slot = {'format': 'quote-card'}
        self.assertFalse(standing_derivative_allowed(slot, {'decision': 'approved'}, '2026-11-29'))
        self.assertTrue(standing_derivative_allowed(slot, {'decision': 'approved'}, '2026-11-30'))
        self.assertFalse(standing_derivative_allowed({'format': 'carousel'}, {'decision': 'approved'}, '2026-11-30'))

    def test_absent_file_defaults_and_stays_shut(self):
        self.assertEqual(show_before_post_until(self.root), '2026-11-29')
        for day in ('2026-11-03', '2026-11-29', '2026-11-30', '2027-01-01'):
            self.assertFalse(standing_derivative_allowed(self.slot, {'decision': 'approved'}, day, self.root))

    def test_both_sides_of_the_date(self):
        self.write({'show_before_post_until': '2026-11-29', 'derivative_formats': ['quote-card']})
        approved = {'decision': 'approved'}
        self.assertFalse(standing_derivative_allowed(self.slot, approved, '2026-11-29', self.root))
        self.assertTrue(standing_derivative_allowed(self.slot, approved, '2026-11-30', self.root))
        self.assertFalse(standing_derivative_allowed(self.slot, {'decision': 'declined'}, '2026-11-30', self.root))
        self.assertFalse(standing_derivative_allowed(self.slot, None, '2026-11-30', self.root))
        self.assertFalse(standing_derivative_allowed({'format': 'note'}, approved, '2026-11-30', self.root))
        # The go-live path is unaffected by the date; without a go-live, the gate decides.
        golive = {'decision': 'approved', 'stage': 'go_live'}
        self.assertTrue(may_release({'format': 'note'}, golive, None, '2026-11-03', self.root))
        self.assertFalse(may_release(self.slot, {'decision': 'approved', 'stage': 'plan'}, approved,
                                     '2026-11-29', self.root))
        self.assertTrue(may_release(self.slot, None, approved, '2026-11-30', self.root))

    def test_the_date_is_read_from_the_file(self):
        self.write({'show_before_post_until': '2026-12-15', 'format_classes': {'derivative': ['quote-card']}})
        self.assertFalse(standing_derivative_allowed(self.slot, {'decision': 'approved'}, '2026-12-15', self.root))
        self.assertTrue(standing_derivative_allowed(self.slot, {'decision': 'approved'}, '2026-12-16', self.root))


if __name__ == '__main__':
    unittest.main()
