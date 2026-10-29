"""Lane L0 release against local stand-ins for Control Center and Buffer only.

No test reaches controlcenter.krishraja.com, api.buffer.com or any media host.
Every word, id, digest and byte here is synthetic.
"""
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import http.client
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest import mock
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
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.run.release import BUFFER_NAME, CHANNELS

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-04T13:00:00Z'  # an hour before DUE: inside the release window
DUE = '2026-11-04T14:00:00Z'
BKEY = 'buffer-stand-in-key-' + 'NeverReal' * 3
PLAN = 'makeyourmindup:plan:w45-w52'
GOLIVE = 'makeyourmindup:golive:2026-W45:week'
P_THREADS, P_X, P_LINKEDIN, P_UNSIGNED = ('aaaaaaaaaaaaaaaaaaaaaa01', 'aaaaaaaaaaaaaaaaaaaaaa02',
                                          'aaaaaaaaaaaaaaaaaaaaaa03', 'aaaaaaaaaaaaaaaaaaaaaa09')
# The pinned Buffer channelIds (engine/buffer_channels.py): main's channel lock refuses any other.
CH_THREADS, CH_X, CH_LINKEDIN = (BUFFER_CHANNEL_ID['threads'], BUFFER_CHANNEL_ID['x'], BUFFER_CHANNEL_ID['linkedin'])
CH_FOR = {'threads': CH_THREADS, 'x': CH_X, 'linkedin': CH_LINKEDIN}
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
        self.refuse_create = None
        self.on_schedule = None  # a callable that changes the stored post as Buffer saves the edit
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
                if op in ('ListPosts', 'ListSentPosts', 'ListSentPostsLinked'):
                    wanted = (variables['input'].get('filter') or {}).get('status')
                    nodes = [p for p in stand.posts.values() if not wanted or p['status'] in wanted]
                    return self.reply(200, {'data': {'posts': {'edges': [{'node': n} for n in nodes],
                                                               'pageInfo': {'hasNextPage': False, 'endCursor': None}}}})
                if op == 'CreateDraft':
                    # The maker's draft save (engine/run/buffer_drafts.py): a new post on the pinned channel.
                    data = variables['input']
                    if stand.refuse_create:
                        return self.reply(200, {'data': {'createPost': {'__typename': stand.refuse_create,
                                                                        'message': 'x'}}})
                    post = created_post(stand, data)
                    stand.posts[post['id']] = post
                    return self.reply(200, {'data': {'createPost': {'__typename': 'PostActionSuccess',
                                                                    'post': copy.deepcopy(post)}}})
                if op == 'ScheduleDraft':
                    data = variables['input']
                    if stand.refuse_edit:
                        return self.reply(200, {'data': {'editPost': {'__typename': stand.refuse_edit, 'message': 'x'}}})
                    post = stand.posts[data['id']]
                    post.update(text=data['text'], dueAt=data['dueAt'].replace('Z', '.000Z'), status='scheduled')
                    if stand.on_schedule:
                        stand.on_schedule(post)
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
        self.on_schedule = None
        self.refuse_create = None

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


def created_post(stand, data):
    """The post Buffer stores for a createPost, as get_post reads it back (synthetic, shaped as the live one)."""
    channel = next(c for c, i in BUFFER_CHANNEL_ID.items() if i == data['channelId'])
    service = CHANNELS[channel][0]
    assets = []
    for asset in data.get('assets') or []:
        (kind, body), = asset.items()
        inner = {'altText': None, 'userTags': None} if kind == 'image' else {'title': None, 'thumbnailOffset': None}
        assets.append({'type': kind, 'source': body['url'], 'mimeType': 'image/png' if kind == 'image' else 'video/mp4',
                       kind: inner})
    given = (data.get('metadata') or {}).get(service) or {}
    metadata = {
        'instagram': lambda: {'__typename': 'InstagramPostMetadata', 'type': given.get('type'),
                              'shouldShareToFeed': given.get('shouldShareToFeed'), 'isAiGenerated': None,
                              'firstComment': None, 'link': None, 'stickerFields': None, 'geolocation': None},
        'youtube': lambda: {'__typename': 'YoutubePostMetadata', 'type': None, 'title': given.get('title'),
                            'category': {'categoryId': given.get('categoryId')}, 'privacy': given.get('privacy'),
                            'madeForKids': given.get('madeForKids'), 'notifySubscribers': None, 'embeddable': None,
                            'license': None, 'isAiGenerated': None},
        'tiktok': lambda: {'__typename': 'TiktokPostMetadata', 'type': None, 'isAiGenerated': None, 'title': None},
        'twitter': lambda: {'__typename': 'TwitterPostMetadata', 'type': 'post', 'isAiGenerated': False,
                            'threadCount': 0, 'retweet': None},
    }.get(service, lambda: None)()
    number = len([p for p in stand.posts if p.startswith('dddddddddddddddddddd')])
    post_id = 'dddddddddddddddddddd%04d' % number
    return {'id': post_id, 'status': 'draft' if data.get('saveToDraft') is True else 'scheduled',
            'dueAt': None if data.get('saveToDraft') is True else data.get('dueAt'), 'text': data['text'],
            'channelId': data['channelId'], 'channelService': service, 'schedulingType': data.get('schedulingType'),
            'via': 'api', 'channel': account(channel, data['channelId']), 'assets': assets, 'metadata': metadata}


def fetch(url):
    return buffer_api.download_sha256(url, loopback_for_tests=True)


def account(channel, channel_id=None):
    """The Buffer channel a post is on, as get_post reads it back."""
    return {'id': channel_id or CH_FOR[channel], 'name': BUFFER_NAME[channel], 'service': CHANNELS[channel][0],
            'isDisconnected': False, 'isLocked': False}


def line(slot_id, channel, words, draft, assets=(), mode='engine', due=DUE, meta=None, channel_id=None, fmt=None):
    # The format matches the draft's shape (release.FORMAT_SHAPE): one image is single-image, none is text.
    fmt = fmt or ('single-image' if len(assets) == 1 else 'text')
    item = {'slot_id': slot_id, 'channel': channel, 'format': fmt, 'due_at': due, 'link_placement': None,
            'publish_mode': mode, 'buffer_draft_id': draft, 'words': words, 'assets': list(assets),
            'meta': meta, 'buffer_channel_id': channel_id or CH_FOR.get(channel, CH_THREADS), 'payload_sha256': None}
    item['payload_sha256'] = line_digest(item)
    return item


def meta_of(post, hashes=()):
    return buffer_api.signed_meta(post, list(hashes))


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
        image = {'type': 'image', 'source': buf.base + '/media/img1.png', 'mimeType': 'image/png',
                 'image': {'altText': 'Synthetic alt text', 'userTags': None}}
        common = {'status': 'draft', 'dueAt': None, 'schedulingType': 'automatic', 'via': 'api'}
        buf.posts = {
            P_THREADS: dict(common, id=P_THREADS, text=WORDS_THREADS, channelId=CH_THREADS, channelService='threads',
                            channel=account('threads'), assets=[image],
                            metadata={'__typename': 'ThreadsPostMetadata', 'type': 'post', 'threadCount': 0,
                                      'linkAttachment': None, 'topic': None, 'locationId': None, 'locationName': None}),
            P_X: dict(common, id=P_X, text=WORDS_X, channelId=CH_X, channelService='twitter', channel=account('x'),
                      assets=[], metadata={'__typename': 'TwitterPostMetadata', 'type': 'post', 'isAiGenerated': False,
                                           'threadCount': 0, 'retweet': None}),
            P_LINKEDIN: dict(common, id=P_LINKEDIN, text=WORDS_LINKEDIN, channelId=CH_LINKEDIN,
                             channelService='linkedin', channel=account('linkedin'), assets=[], metadata=None),
            P_UNSIGNED: dict(common, id=P_UNSIGNED, text='Synthetic unsigned draft.', channelId=CH_THREADS,
                             channelService='threads', channel=account('threads'), assets=[], metadata=None)}
        posts = buf.posts
        self.lines = [line('threads-1', 'threads', WORDS_THREADS, P_THREADS, [sha(IMAGE)],
                           meta=meta_of(posts[P_THREADS], [sha(IMAGE)])),
                      line('x-1', 'x', WORDS_X, P_X, meta=meta_of(posts[P_X])),
                      line('linkedin-1', 'linkedin', WORDS_LINKEDIN, P_LINKEDIN, mode='krish_click', due=None,
                           meta=meta_of(posts[P_LINKEDIN]))]
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
        # The fixture's routes stand as recorded passed; test_an_unverified_route_holds proves the real record.
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def resign(self):
        """Sign the threads and x lines again from their drafts as they now stand."""
        posts = self.buf.posts
        lines = [line('threads-1', 'threads', posts[P_THREADS]['text'], P_THREADS, [sha(IMAGE)],
                      meta=meta_of(posts[P_THREADS], [sha(IMAGE)])),
                 line('x-1', 'x', posts[P_X]['text'], P_X, meta=meta_of(posts[P_X])), self.fix.lines[2]]
        golive = self.fix.publish(lines)
        self.cc.decisions = [Fixture.decision(self.fix.plan, '2026-11-01T12:00:00Z'),
                             Fixture.decision(golive, '2026-11-03T14:00:00Z')]

    def test_a_word_failing_main_copy_lint_holds_before_any_edit(self):
        # Krish, 28 Oct 2026: "Remember, no content refers to Krish, ever." L0 release runs the same
        # copy lint as `run release` on every word it would schedule, even one he signed.
        self.buf.posts[P_X]['text'] = 'Synthetic words: Krish Raja on the chip money.'
        self.buf.posts[P_THREADS]['assets'][0]['image']['altText'] = 'Krish Raja holding the chart.'
        self.resign()
        summary, code = self.run_once()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['holds'], {'copy_lint_refused': 2})
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual((self.buf.posts[P_X]['status'], self.buf.posts[P_THREADS]['status']), ('draft', 'draft'))
        self.assertNotIn('Krish Raja', json.dumps(summary), 'the summary carries codes, never words')
        # The same draft with clean words and alt text schedules.
        self.buf.posts[P_X]['text'] = WORDS_X
        self.buf.posts[P_THREADS]['assets'][0]['image']['altText'] = 'Synthetic alt text'
        self.resign()
        summary, _ = self.run_once()
        self.assertEqual(summary['slots'], {'krish_click': 1, 'scheduled': 2})

    def test_an_unverified_route_holds_and_a_share_ask_holds(self):
        # Main's R95 on the L0 path: a route not verified and fresh releases only its one capability
        # check, through `run release`; here it holds, with no read and no edit of the draft.
        mock.patch.stopall()
        holds, known, _ = autorelease.route_holds(self.fix.lines[0], '2026-11-04')
        self.assertTrue(known and holds, 'social/tools/buffer.json records no Threads text route as passed yet')
        summary, code = self.run_once()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['holds'], {'route_not_verified': 2})
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'GetPost'], [])
        # Main's R99 on the L0 path: a snackable post that asks for the share holds.
        snack = dict(self.fix.lines[1], format='note', words='Please share this with your team.')
        self.assertTrue(autorelease.share_ask_errors(snack, snack['words']))
        self.assertEqual(autorelease.share_ask_errors(self.fix.lines[1], WORDS_X), [])

    def test_a_share_ask_in_a_snackable_line_holds_before_any_read(self):
        lines = [dict(self.fix.lines[1], format='note', words='Please share this with your team.')]
        run = autorelease.Run(self.buf.client(), NOW, True, fetch)
        run.slot(lines[0], lines[0], {'decision': 'approved', 'stage': 'go_live'})
        self.assertEqual(run.holds, {'share_ask_refused': 1})
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'GetPost'], [])

    def test_carried_titles_and_first_comments_run_the_copy_lint(self):
        # buffer_api carries a video title, a TikTok title and a first comment that `run release`
        # never builds; edit_input lints them through release's own media_copy_errors.
        api = self.buf.client()
        post = api.get_post(P_X)
        video = {'type': 'video', 'source': 'https://example.invalid/v.mp4', 'video': {'title': "Krish's test"}}
        cases = (dict(post, assets=[video]),
                 dict(post, metadata={'__typename': 'TiktokPostMetadata', 'title': 'A chart by @TheRealKrisho',
                                      'isAiGenerated': False}),
                 dict(post, metadata={'__typename': 'FacebookPostMetadata', 'type': 'post',
                                      'firstComment': 'Krish Raja wrote the long read.', 'linkAttachment': None}))
        for case in cases:
            with self.assertRaisesRegex(CarryHold, 'copy_lint_refused'):
                buffer_api.edit_input(case, DUE)
            with self.assertRaisesRegex(CarryHold, 'copy_lint_refused'):
                api.schedule_draft(case, DUE)
        with self.assertRaisesRegex(CarryHold, 'copy_lint_refused'):
            buffer_api.edit_input(post, DUE, 'Signed words naming Krish.')
        self.assertEqual(api.mutations, 0)
        self.assertEqual(buffer_api.edit_input(post, DUE)['text'], WORDS_X)

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
        self.assertEqual(summary['golives'], {'releasable': 0, 'held': {'golive_report_missing': 1}, 'claimed': 0})
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
        # His words never name him (no_name, Krish, 28 Oct 2026), even in a fixture.
        his_words = 'Synthetic words he amended for the threads slot.'
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
        summary, code = self.run_once(now='2026-11-04T13:56:00Z')
        self.assertEqual(summary['holds'], {'due_time_passed': 2})
        self.assertEqual(self.buf.mutations(), [])
        # S1: a signed draft still unscheduled at its time is held loudly, so GitHub emails Krish.
        self.assertEqual((code, summary['loud']), (1, ['due_time_passed']))

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
        summary, code = self.run_once()
        self.assertEqual(summary['holds'], {'live_post_differs_from_signed': 1})
        self.assertEqual((code, summary['loud']), (1, ['live_post_differs_from_signed']))

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

    # B1: the digest covers everything the edit sends ------------------------------

    def test_a_metadata_change_after_approval_holds(self):
        # Krish approved the post with no topic, no tags and this alt text. A topic,
        # a tagged account or other alt text added in Buffer after his yes is not his.
        for change in (lambda p: p['metadata'].update(topic='Synthetic topic added later'),
                       lambda p: p['assets'][0]['image'].update(userTags=[{'handle': 'synthetic.someone',
                                                                            'x': 0.5, 'y': 0.25}]),
                       lambda p: p['assets'][0]['image'].update(altText='Synthetic other alt text')):
            self.setUp()
            change(self.buf.posts[P_THREADS])
            summary, _ = self.run_once()
            self.assertEqual(summary['holds'], {'draft_differs_from_signed': 1})
            self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')
            self.assertEqual(summary['slots'].get('scheduled'), 1)

    # B2: the account, not just the service ----------------------------------------

    def test_a_draft_on_another_account_holds(self):
        # Same service, another venture's channel in the shared organisation.
        self.buf.posts[P_X]['channel']['name'] = 'synthetic-other-venture'
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'wrong_account': 1})
        self.assertNotIn(P_X, json.dumps([c['variables'] for c in self.buf.mutations()]))
        # The right name on another channel id than the one Krish signed holds too.
        self.setUp()
        other = 'cccccccccccccccccccccc09'
        self.buf.posts[P_X].update(channelId=other, channel=account('x', other))
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'wrong_account': 1})
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')

    # S1: schedule only near the due time ----------------------------------------------

    def test_a_slot_more_than_ninety_minutes_out_is_never_read_or_edited(self):
        summary, code = self.run_once(now='2026-11-04T12:29:00Z')  # 91 minutes before DUE
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'krish_click': 1, 'not_yet_due': 2})
        self.assertEqual([c for c in self.buf.calls if c['op'] in ('GetPost', 'media', 'ScheduleDraft')], [])
        summary, code = self.run_once(now='2026-11-04T12:30:00Z')  # exactly 90 minutes
        self.assertEqual(summary['slots'], {'krish_click': 1, 'scheduled': 2})

    def test_a_no_before_the_window_stops_it(self):
        summary, _ = self.run_once(now='2026-11-04T11:00:00Z')
        self.assertEqual(summary['slots']['not_yet_due'], 2)
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-04T11:30:00Z', decision='declined'))
        summary, code = self.run_once()
        self.assertEqual((code, summary['golives']['releasable']), (0, 0))
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')

    # S4: the scheduled-after-decline alarm ----------------------------------------------

    def test_a_no_after_scheduling_is_loud_and_never_unscheduled(self):
        self.run_once()
        self.assertEqual(self.buf.posts[P_X]['status'], 'scheduled')
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-04T13:10:00Z', decision='declined'))
        summary, code = self.run_once(now='2026-11-04T13:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary['loud'], ['scheduled_after_decline'])
        self.assertEqual(summary['holds'], {'scheduled_after_decline': 2})
        self.assertEqual(summary['mutations'], 0)
        # Krish unschedules it himself; the engine has no removal path.
        self.assertEqual((self.buf.posts[P_THREADS]['status'], self.buf.posts[P_X]['status']), ('scheduled', 'scheduled'))

    def test_a_changed_approval_after_scheduling_is_loud(self):
        self.run_once()
        his_words = 'Synthetic words he amended after the first yes.'
        text = manifest([dict(self.fix.lines[0], words=his_words), self.fix.lines[1], self.fix.lines[2]])
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-04T13:10:00Z', amended=True,
                                                  exact_payload=text, amount_usd=None,
                                                  amended_sha256=amended_digest(None, text)))
        summary, code = self.run_once(now='2026-11-04T13:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('scheduled_after_decline', summary['loud'])
        # Only the post whose approved version changed; x is exactly what he still approves.
        self.assertEqual(summary['holds']['scheduled_after_decline'], 1)
        self.assertEqual(summary['slots'].get('already_scheduled'), 1)
        self.assertEqual(summary['mutations'], 0)

    def test_a_stopped_plan_after_scheduling_is_loud(self):
        self.run_once()
        self.cc.decisions.append(Fixture.decision(self.fix.plan, '2026-11-04T13:10:00Z', decision='declined'))
        summary, code = self.run_once(now='2026-11-04T13:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary['golives']['held'], {'plan_stopped': 1})
        self.assertEqual(summary['holds'], {'scheduled_after_decline': 2})

    def test_no_alarm_when_nothing_was_scheduled(self):
        self.cc.decisions.append(Fixture.decision(self.fix.golive, '2026-11-04T12:00:00Z', decision='declined'))
        summary, code = self.run_once()
        self.assertEqual((code, summary['loud'], summary['holds']), (0, [], {}))

    # S3: read order -----------------------------------------------------------------------

    def old_golives(self, prefix, count=30):
        for n in range(count):
            item = proposal(prefix + '%02d' % n, 'Synthetic old go-live', 'Synthetic why', 'prepared', 'post',
                            'published', channel='buffer', exact_payload='Synthetic old manifest %d.' % n,
                            stage='go_live', parent_proposal_id=PLAN)
            self.cc.decisions.insert(1, Fixture.decision(item, '2026-11-02T%02d:%02d:00Z' % (n // 60, n % 60)))

    def test_old_go_lives_never_starve_a_new_one(self):
        # 30 older approvals, still in date, whose ids sort before the new one's.
        self.old_golives('makeyourmindup:golive:2026-11-02:piece:')
        summary, code = self.run_once()
        self.assertEqual(summary['slots'], {'krish_click': 1, 'scheduled': 2}, summary)
        self.assertEqual(summary['golives']['releasable'], 1)

    def test_an_ended_go_live_is_skipped_before_it_uses_a_read(self):
        self.old_golives('makeyourmindup:golive:2026-W43:week:')  # its run ended on 26 October
        summary, _ = self.run_once()
        self.assertEqual(summary['golives']['held'], {'golive_ended_unread': 30})
        reads = [c for c in self.cc.calls if c['method'] == 'GET' and '/reports/' in c['path']]
        self.assertEqual(len([c for c in reads if '2026-W43' in c['path']]), 0)  # no ended go-live is read
        # The new go-live and its plan; its claim, looked up first and read back once reported; today's
        # derived index.
        self.assertEqual(len([c for c in reads if '%3Agolive%3A' in c['path'] or '%3Aplan%3A' in c['path']]), 2)
        self.assertEqual(len(reads), 5, [c['path'] for c in reads])
        self.assertEqual(summary['slots']['scheduled'], 2)

    # S5: an impossible date ------------------------------------------------------------------

    def test_an_impossible_due_date_holds_that_slot_only(self):
        lines = [dict(self.fix.lines[0], due_at='2026-02-30T14:00:00Z'), self.fix.lines[1], self.fix.lines[2]]
        lines[0]['payload_sha256'] = line_digest(lines[0])
        golive = self.fix.publish(lines)
        self.cc.decisions[-1] = Fixture.decision(golive, '2026-11-03T14:00:00Z')
        summary, code = self.run_once()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['holds'], {'bad_due_at': 1})
        self.assertEqual(summary['slots'], {'held': 1, 'krish_click': 1, 'scheduled': 1})
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')
        # Krish's amended line with an impossible date holds alone too.
        self.setUp()
        text = manifest([dict(self.fix.lines[0], due_at='2026-11-31T14:00:00Z'), self.fix.lines[1]])
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None,
                                                 amended_sha256=amended_digest(None, text))
        summary, code = self.run_once()
        self.assertEqual((code, summary['holds']), (0, {'bad_due_at': 1}))
        self.assertEqual(summary['slots'].get('scheduled'), 1)

    # Nits ---------------------------------------------------------------------------------------

    def test_already_scheduled_means_the_full_digest_not_words_and_time(self):
        self.run_once()
        # Scheduled in the signed words at the signed time, but the image bytes behind it changed.
        self.buf.media['img1.png'] = IMAGE + b'changed after scheduling\n'
        summary, code = self.run_once()
        self.assertEqual(summary['holds'], {'live_post_differs_from_signed': 1})
        self.assertEqual(summary['slots']['already_scheduled'], 1)
        self.assertEqual(code, 1)
        # And with the bytes back, a first comment added to the scheduled post is not his either.
        self.buf.media['img1.png'] = IMAGE
        self.buf.posts[P_THREADS]['metadata']['topic'] = 'Synthetic topic added to the scheduled post'
        summary, _ = self.run_once()
        self.assertEqual(summary['holds'], {'live_post_differs_from_signed': 1})

    def test_the_clock_is_read_again_before_each_margin_check(self):
        from engine.core import instant
        late = instant('2026-11-04T13:57:00Z')

        def clock():
            # The asset download took long: by the time it is done the slot is within five minutes.
            return late if any(c['op'] == 'media' for c in self.buf.calls) else instant(NOW)
        summary, code = autorelease.autorelease(self.cc.client(), self.buf.client(), None, True, fetch, clock=clock)
        self.assertEqual(summary['holds'], {'due_time_passed': 2}, summary)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(code, 1)

    def test_the_readback_checks_the_meta(self):
        # Buffer adds a topic to the Threads post as it saves the edit (a field Threads carries).
        self.buf.on_schedule = lambda post: (post.get('metadata') or {}).update(topic='Synthetic topic Buffer added') \
            if post.get('channelService') == 'threads' else None
        summary, code = self.run_once()
        self.assertEqual((code, summary['loud']), (1, ['readback_mismatch']))
        self.assertEqual(summary['holds'], {'readback_mismatch': 1})
        self.assertEqual(summary['slots']['scheduled'], 1)

    # The second adversarial review of the posting path, 29 Oct 2026 ------------------------

    def page_like_control_center(self):
        """The stand-in serves only decisions after since, 100 a read, as the real route does."""
        self.cc.honour_since = True
        self.addCleanup(setattr, self.cc, 'honour_since', False)

    @staticmethod
    def filler(count, start='2026-10-20T00:00:00Z'):
        """count older decisions on proposals that are not go-lives, one a minute from start."""
        import datetime as dt
        from engine.core import instant
        base = instant(start)
        return [{'proposal_id': 'makeyourmindup:experiment:e%03d' % n, 'decision': 'declined', 'stage': None,
                 'decided_at': (base + dt.timedelta(minutes=n)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'payload_sha256': 'e' * 64, 'amended': False} for n in range(count)]

    def test_his_no_past_the_hundredth_decision_stops_the_release(self):
        # F100: Control Center serves 100 decisions a read, the oldest first. His No is the 101st.
        self.page_like_control_center()
        no = Fixture.decision(self.fix.golive, '2026-11-04T12:30:00Z', decision='declined')
        self.cc.decisions = self.filler(98) + self.cc.decisions + [no]
        summary, code = self.run_once()
        self.assertEqual(summary['decisions_read'], 101, summary)
        self.assertEqual(summary['golives']['releasable'], 0)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(code, 0, summary)

    def test_a_tie_at_the_page_boundary_is_never_dropped(self):
        # F100: the 100th decision (his yes) and the 101st (his No) share one decided_at. A next
        # page read strictly after that time would drop the No; it is read again and kept once.
        self.page_like_control_center()
        no = Fixture.decision(self.fix.golive, '2026-11-03T14:00:00Z', decision='declined')
        self.cc.decisions = self.filler(98) + self.cc.decisions + [no]
        summary, code = self.run_once()
        self.assertEqual(summary['decisions_read'], 101, summary)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(code, 0, summary)

    def test_decisions_that_never_page_out_fail_loud(self):
        # F100: a route that keeps serving the same full page (or pages past the cap) is never
        # read as complete: the run fails closed and loud, and touches nothing.
        self.cc.decisions = self.filler(150) + self.cc.decisions
        summary, code = self.run_once()
        self.assertEqual((code, summary['error']), (1, 'decisions_unpaged'), summary)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'GetPost'], [])

    def test_a_format_label_that_is_not_the_draft_holds(self):
        # F101: the dispatch's format is signed, but a video on X labelled single-image is not one.
        video = b'synthetic autorelease video bytes\n'
        self.buf.media['v.mp4'] = video
        self.buf.posts[P_X]['assets'] = [{'type': 'video', 'source': self.buf.base + '/media/v.mp4',
                                          'mimeType': 'video/mp4', 'video': {'title': None, 'thumbnailOffset': None}}]
        lines = [self.fix.lines[0], line('x-1', 'x', WORDS_X, P_X, [sha(video)], fmt='single-image',
                                         meta=meta_of(self.buf.posts[P_X], [sha(video)])), self.fix.lines[2]]
        golive = self.fix.publish(lines)
        self.cc.decisions[-1] = Fixture.decision(golive, '2026-11-03T14:00:00Z')
        summary, code = self.run_once()
        self.assertEqual(summary['holds'], {'format_differs_from_draft': 1}, summary)
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')
        self.assertEqual(summary['slots'].get('scheduled'), 1)
        # A Reel labelled carousel is refused where the line is rebuilt, whichever lane rebuilds it.
        reel = {'id': P_UNSIGNED, 'text': 'Synthetic reel words.', 'channelService': 'instagram',
                'channelId': BUFFER_CHANNEL_ID['instagram'],
                'assets': [{'type': 'video', 'source': self.buf.base + '/media/v.mp4',
                            'video': {'title': None, 'thumbnailOffset': None}}],
                'metadata': {'__typename': 'InstagramPostMetadata', 'type': 'reel', 'shouldShareToFeed': True}}
        fields = {'slot_id': 'ig-1', 'format': 'carousel', 'due_at': DUE, 'link_placement': None,
                  'publish_mode': 'engine', 'buffer_draft_id': P_UNSIGNED}
        with self.assertRaisesRegex(CarryHold, 'format_differs_from_draft'):
            autorelease.draft_line(reel, fields, fetch)
        self.assertEqual(autorelease.draft_line(reel, dict(fields, format='short-video'), fetch)['format'],
                         'short-video')

    def test_an_unresolved_stop_is_loud_and_lists_what_is_scheduled(self):
        # F103: a declined check-in whose report cannot be read may stop the plan behind these posts.
        self.run_once()
        self.assertEqual((self.buf.posts[P_THREADS]['status'], self.buf.posts[P_X]['status']), ('scheduled', 'scheduled'))
        self.cc.decisions.append({'proposal_id': 'makeyourmindup:checkin:2026-W45', 'decision': 'declined',
                                  'stage': 'check_in', 'decided_at': '2026-11-04T13:10:00Z',
                                  'payload_sha256': 'b' * 64, 'amended': False})
        summary, code = self.run_once(now='2026-11-04T13:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('stop_unresolved', summary['loud'])
        self.assertIn('scheduled_after_decline', summary['loud'])
        self.assertEqual(summary['holds'], {'scheduled_after_decline': 2})
        self.assertEqual(summary['mutations'], 0)

    def test_a_capped_read_or_an_undated_decision_is_loud(self):
        # F103: his plan No, with the go-live behind it past the read cap: what it scheduled is listed.
        self.run_once()
        self.cc.decisions.append(Fixture.decision(self.fix.plan, '2026-11-04T13:10:00Z', decision='declined'))
        with mock.patch.object(autorelease, 'MAX_REPORT_READS', 0):
            summary, code = self.run_once(now='2026-11-04T13:20:00Z')
        self.assertEqual(code, 1, summary)
        self.assertIn('too_many_reads', summary['loud'])
        self.assertEqual(summary['holds'], {'scheduled_after_decline': 2})
        # A decision whose time cannot be read holds its go-live, loudly.
        self.setUp()
        self.cc.decisions.append(dict(Fixture.decision(self.fix.golive, None), decided_at=None, decision='declined'))
        summary, code = self.run_once()
        self.assertEqual(summary['golives']['held'], {'undated_decision': 1})
        self.assertEqual((code, summary['loud']), (1, ['undated_decision']), summary)
        self.assertEqual(self.buf.mutations(), [])

    def test_a_golive_line_digest_is_never_a_run_spec_slot_digest(self):
        # F105: the same words, time and draft hash differently on the two paths, so one
        # approval can never be replayed as the other.
        from engine.run import release
        for item in self.fix.lines:
            as_slot = dict(item, assets=[{'sha256': h} for h in item['assets']])
            self.assertNotEqual(line_digest(item), release.slot_digest(as_slot))
            self.assertEqual(autorelease.spec_digest(item), release.slot_digest(as_slot))

    def test_an_amended_time_outside_the_run_window_holds(self):
        # F108: the W45 go-live's run starts at New York midnight on Monday 2 November; he moved
        # the threads post to Sunday 1 November.
        early = '2026-11-01T14:00:00Z'
        text = manifest([dict(self.fix.lines[0], due_at=early), self.fix.lines[2]])
        self.cc.decisions[-1] = Fixture.decision(self.fix.golive, '2026-11-01T10:00:00Z', amended=True,
                                                 exact_payload=text, amount_usd=None,
                                                 amended_sha256=amended_digest(None, text))
        summary, code = self.run_once(now='2026-11-01T13:00:00Z')
        self.assertEqual(summary['holds'], {'due_outside_run_window': 1}, summary)
        self.assertEqual(self.buf.mutations(), [])
        self.assertEqual(self.buf.posts[P_THREADS]['status'], 'draft')


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

    def test_the_edit_is_never_resent(self):
        # F107: a 5xx on editPost may have landed, so the mutation is sent once; the caller reads back.
        api = self.buf.client()
        post = api.get_post(P_X)
        self.buf.fail_next = [503]
        with self.assertRaises(BufferError) as caught:
            api.schedule_draft(post, DUE)
        self.assertEqual(caught.exception.code, 'buffer_server_error')
        self.assertEqual(len(self.buf.mutations()), 1)
        self.assertEqual(self.buf.posts[P_X]['status'], 'draft')

    def test_a_field_read_but_never_carried_holds(self):
        # F109: an edit is a whole post, so a field the edit cannot carry (a Facebook title) would be lost.
        post = self.buf.client().get_post(P_X)
        facebook = dict(post, metadata={'__typename': 'FacebookPostMetadata', 'type': 'post', 'firstComment': None,
                                        'title': 'Synthetic title the edit cannot carry', 'linkAttachment': None})
        with self.assertRaisesRegex(CarryHold, 'uncarried_field_set'):
            buffer_api.edit_input(facebook, DUE)
        image = {'type': 'image', 'source': 'https://example.invalid/a.png', 'mimeType': 'image/png',
                 'image': {'altText': 'Synthetic alt text', 'userTags': None, 'caption': 'Synthetic caption'}}
        with self.assertRaisesRegex(CarryHold, 'uncarried_field_set'):
            buffer_api.edit_input(dict(post, assets=[image]), DUE)
        facebook['metadata']['title'] = None
        self.assertEqual(buffer_api.edit_input(facebook, DUE)['metadata'], {'facebook': {'type': 'post'}})

    def test_every_carried_free_text_field_runs_the_copy_lint(self):
        # F102: the Threads topic and location, the Instagram location and every tagged handle are
        # public words too, and no public word names Krish (no_name, 28 Oct 2026).
        from engine.run.release import media_copy_errors
        post = self.buf.client().get_post(P_X)
        image = {'type': 'image', 'source': 'https://example.invalid/a.png',
                 'image': {'altText': 'A synthetic chart', 'userTags': [{'handle': 'krishraja', 'x': 0.5, 'y': 0.5}]}}
        cases = (dict(post, assets=[image]),
                 dict(post, metadata={'__typename': 'InstagramPostMetadata', 'type': 'post', 'shouldShareToFeed': True,
                                      'geolocation': {'id': '1', 'text': 'Krish Raja HQ'}}),
                 dict(post, metadata={'__typename': 'ThreadsPostMetadata', 'type': 'post', 'threadCount': 0,
                                      'topic': 'Krish Raja'}),
                 dict(post, metadata={'__typename': 'ThreadsPostMetadata', 'type': 'post', 'threadCount': 0,
                                      'locationName': 'TheRealKrisho studio'}))
        for case in cases:
            with self.assertRaisesRegex(CarryHold, 'copy_lint_refused'):
                buffer_api.edit_input(case, DUE)
        # Every string an edit carries, bar ids, links, times and fixed codes, is read by the lint.
        not_words = {'id', 'url', 'dueAt', 'mode', 'schedulingType', 'type', 'categoryId', 'privacy',
                     'license', 'locationId'}
        full = [dict(post, assets=[dict(image, image={'altText': 'A synthetic chart',
                                                      'userTags': [{'handle': 'synthetic.someone', 'x': 0.5, 'y': 0.5}]}),
                                   {'type': 'video', 'source': 'https://example.invalid/v.mp4',
                                    'video': {'title': 'A synthetic title', 'thumbnailOffset': 3}}]),
                dict(post, metadata={'__typename': 'InstagramPostMetadata', 'type': 'post', 'shouldShareToFeed': True,
                                     'firstComment': 'A synthetic comment', 'geolocation': {'id': '1', 'text': 'A place'}}),
                dict(post, metadata={'__typename': 'ThreadsPostMetadata', 'type': 'post', 'threadCount': 0,
                                     'topic': 'A topic', 'locationId': '1', 'locationName': 'A place'}),
                dict(post, metadata={'__typename': 'FacebookPostMetadata', 'type': 'post', 'firstComment': 'A comment'}),
                dict(post, assets=[{'type': 'video', 'source': 'https://example.invalid/v.mp4', 'video': {}}],
                     metadata={'__typename': 'TiktokPostMetadata', 'type': 'post', 'title': 'A title'}),
                dict(post, metadata={'__typename': 'YoutubePostMetadata', 'type': 'video', 'title': 'A title',
                                     'category': {'categoryId': '22'}, 'privacy': 'public', 'license': 'youtube'})]

        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from leaves(item, path + (key,))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    yield from leaves(item, path + (index,))
            elif isinstance(value, str) and path[-1] not in not_words and path != ('text',):
                yield path  # the post's own text is copy_errors', not media_copy_errors'

        checked = 0
        for case in full:
            payload = buffer_api.edit_input(case, DUE)
            self.assertEqual(media_copy_errors(payload), [])
            for path in leaves(payload):
                named = copy.deepcopy(payload)
                spot = named
                for key in path[:-1]:
                    spot = spot[key]
                spot[path[-1]] = 'Krish Raja'
                self.assertTrue(any('no_name' in e for e in media_copy_errors(named)), path)
                checked += 1
        self.assertGreaterEqual(checked, 10)

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

    def test_a_cut_off_body_is_transient_and_carries_a_code(self):
        api = self.buf.client()
        real, cuts = api._send, [http.client.IncompleteRead(b'')]

        def send(body):
            if cuts:
                raise cuts.pop()
            return real(body)
        api._send = send
        self.assertEqual(api.get_post(P_X)['id'], P_X)  # one retry, as for any transient failure
        api = self.buf.client()
        api._send = lambda body: (_ for _ in ()).throw(http.client.IncompleteRead(b''))
        with self.assertRaises(BufferError) as caught:
            api.get_post(P_X)
        self.assertEqual(caught.exception.code, 'buffer_unreachable')

    def test_an_asset_over_the_cap_holds(self):
        with self.assertRaisesRegex(BufferError, 'asset_too_large'):
            buffer_api.download_sha256(self.buf.base + '/media/img1.png', cap=4, loopback_for_tests=True)



class SignedMetaTests(unittest.TestCase):
    """B1: the review's probe, as tests. Every field the edit sends moves the digest."""
    FIELDS = {'slot_id': 's1', 'format': 'single-image', 'due_at': DUE, 'link_placement': None, 'publish_mode': 'engine',
              'buffer_draft_id': 'a' * 24}

    @staticmethod
    def fetch(url):
        return 'a' * 64, 10

    def base(self, service, assets, metadata):
        return {'id': 'a' * 24, 'status': 'draft', 'text': 'Synthetic words.', 'channelService': service,
                'channelId': 'c' * 24, 'via': 'api', 'assets': assets, 'metadata': metadata}

    def digest(self, post):
        # Each draft is signed as the format it is (release.FORMAT_SHAPE, F101).
        kind = (post.get('metadata') or {}).get('type')
        video = any(a.get('type') == 'video' for a in post['assets'])
        fmt = 'story' if kind == 'story' else 'short-video' if video else 'single-image'
        return autorelease.draft_line(post, dict(self.FIELDS, format=fmt), self.fetch)['payload_sha256']

    def instagram(self, kind, first_comment, tags=None):
        image = {'type': 'image', 'source': 'https://example.invalid/a.png',
                 'image': {'altText': 'Synthetic alt', 'userTags': tags}}
        return self.base('instagram', [image], {'__typename': 'InstagramPostMetadata', 'type': kind,
                                                'shouldShareToFeed': True, 'isAiGenerated': None,
                                                'firstComment': first_comment, 'link': None,
                                                'stickerFields': None, 'geolocation': None})

    def youtube(self, title, privacy):
        video = {'type': 'video', 'source': 'https://example.invalid/v.mp4', 'video': {'title': None,
                                                                                       'thumbnailOffset': None}}
        return self.base('youtube', [video], {'__typename': 'YoutubePostMetadata', 'title': title,
                                              'category': {'categoryId': '22'}, 'privacy': privacy})

    def test_the_probe_cases_change_the_digest(self):
        plain = self.instagram('post', None)
        story = self.instagram('story', 'Synthetic first comment https://example.invalid',
                               [{'handle': 'synthetic.someone', 'x': 0.1, 'y': 0.1}])
        self.assertNotEqual(self.digest(plain), self.digest(story))
        self.assertNotEqual(self.digest(plain), self.digest(self.instagram('post', 'Synthetic first comment')))
        self.assertNotEqual(self.digest(self.youtube('Synthetic title', 'private')),
                            self.digest(self.youtube('Synthetic other title', 'private')))
        self.assertNotEqual(self.digest(self.youtube('Synthetic title', 'private')),
                            self.digest(self.youtube('Synthetic title', 'public')))
        tiktok = self.base('tiktok', [{'type': 'video', 'source': 'https://example.invalid/v.mp4', 'video': {}}],
                           {'__typename': 'TiktokPostMetadata', 'title': 'Synthetic title', 'isAiGenerated': False})
        self.assertNotEqual(self.digest(tiktok), self.digest(dict(tiktok, metadata=dict(tiktok['metadata'], title='Other'))))
        # The Buffer account is signed too.
        self.assertNotEqual(self.digest(plain), self.digest(dict(plain, channelId='d' * 24)))

    def test_the_signed_meta_is_exactly_what_the_edit_sends(self):
        for post in (self.instagram('story', 'Synthetic comment', [{'handle': 'synthetic.someone', 'x': 0.5, 'y': 1.0}]),
                     self.youtube('Synthetic title', 'unlisted')):
            sent = buffer_api.edit_input(post, DUE, 'Synthetic words.')
            for key in ('id', 'text', 'dueAt', 'mode'):
                sent.pop(key)
            for asset in sent['assets']:
                (inner,) = asset.values()
                inner['sha256'] = 'a' * 64
                del inner['url']
            expected = json.loads(json.dumps(sent), parse_float=str)
            self.assertEqual(buffer_api.signed_meta(post, ['a' * 64]), expected)

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
        # GROWTH_WRITEBACK_TOKEN only on the board tick step (R122), never on release's own.
        self.assertEqual(set(re.findall(r'secrets\.([A-Z_]+)', text)),
                         {'CONTROL_CENTER_ENGINE_TOKEN', 'BUFFER_API_KEY', 'GROWTH_WRITEBACK_TOKEN'})
        release_step = text[:text.index('Tick the publish board')]
        self.assertNotIn('GROWTH_WRITEBACK_TOKEN', release_step)
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
