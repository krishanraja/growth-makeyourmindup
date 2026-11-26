"""Lane L0, the maker: tomorrow's drafts of the assets and captions content-engine finished, from the ideas Krish
approved, against local stand-ins only.

Content-engine makes every asset and writes every caption (Ruling, Krish, 2026-11-26): the mix dispatch carries its
files and its captions, and the maker posts exactly those. Control Center and Buffer are the stand-ins the release
and handoff tests use; the Anthropic API is a stub that answers the share declaration and the blind review in the
schema the maker asks for; the Drive downloads are a dict. Every word, id, digest and
byte here is synthetic. Nothing reaches controlcenter.krishraja.com, api.buffer.com, api.anthropic.com
or Google Drive.
"""
import copy
import datetime
import email.utils
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest import mock

try:
    from test_autonomy import CapableStandIn as StandIn
    from test_run_autorelease import BKEY, BufferStandIn
    from test_concepts import SHARE
    from test_mix import WEEK, inventory_of
    from test_concept_release import BoardStandIn
except ImportError:  # run as tests.test_run_maker
    from tests.test_autonomy import CapableStandIn as StandIn
    from tests.test_run_autorelease import BKEY, BufferStandIn
    from tests.test_concepts import SHARE
    from tests.test_mix import WEEK, inventory_of
    from tests.test_concept_release import BoardStandIn

from engine import concepts, mix, route
from engine import buffer_channels
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.control_center import ProtocolError
from engine.run import anthropic_api, autorelease, buffer_api, buffer_drafts, cc_records, handoff, maker
from engine.run.buffer_api import BufferError

ROOT = Path(__file__).resolve().parents[1]
PID = 'makeyourmindup:mix:2026-W46'
PLANNED = '2026-11-07T12:00:00Z'
DECIDED = '2026-11-08T17:00:00Z'
NOW = '2026-11-10T04:30:00Z'  # Monday 23:30 in New York: the maker makes Tuesday
RELEASE_AT = '2026-11-10T12:30:00Z'  # an hour before Tuesday 08:30 New York
CLAIM = 'A pilot earns its budget line when one number is agreed on day one.'
WORDS = CLAIM + ' Synthetic fixture words after the claim, about the pilot budget.'
FRAME1 = b'\x89PNG\r\n\x1a\n' + b'synthetic maker frame one\n'
FRAME2 = b'\x89PNG\r\n\x1a\n' + b'synthetic maker frame two\n'
VIDEO = b'\x00\x00\x00\x18ftypmp42' + b'synthetic maker video\n'
VIDEO_COVER_MS = 61500  # the frame of the cover content-engine baked into the cut (engine/run/cover_gate.py)
DRIVE = {'SyntheticDriveFile0001': FRAME1, 'SyntheticDriveFile0002': FRAME2, 'SyntheticDriveFile0003': VIDEO}
ANSWER = {'would_send': True, 'receiver': 'my CFO', 'job': 'settles_it', 'dm_line': 'Synthetic line.',
          'why': 'Synthetic.'}


def tra_created_post():
    """The Buffer stand-in's own createPost, so a test can wrap what Buffer stores."""
    return sys.modules[BufferStandIn.__module__].created_post


def sha(data):
    return hashlib.sha256(data).hexdigest()


def outcomes(summary):
    """What happened to the concept's slots: the week's empty slots (no concept) left out."""
    return {k: v for k, v in summary['slots'].items() if k != 'empty_slot'}


IDEAS = ([{'idea_id': 'news-0', 'lane': 'positive_news', 'idea': 'TEST FIXTURE good news 0', 'claim': None,
           'source_url': 'https://example.org/news-0', 'source_date': '2026-11-05'}]
         + [{'idea_id': 'meme-%d' % n, 'lane': 'meme', 'idea': 'TEST FIXTURE meme %d' % n, 'claim': None,
             'source_url': None, 'source_date': None} for n in range(2)])
NEWS = 'positive-news-news-0'


def without_memes(summary):
    """The summary without the two not-ready memes' slots: Tuesday's second board option, which hold as
    concept_not_approved on every run (no claim, no mock), so each test reads only the news concept."""
    holds = dict(summary.get('holds') or {})
    memes = holds.pop('concept_not_approved', 0)
    if memes:
        slots = dict(summary['slots'])
        slots['held'] -= memes
        if not slots['held']:
            del slots['held']
        summary = dict(summary, holds=holds, slots=slots)
    return summary


def maker_plan():
    """One positive-news concept (carousels, a Short, one image on X: the same placements as a past piece's) on
    all four channels on Tuesday, ready with its claim and three mock files; two memes not ready yet, so
    Tuesday's Off days hold two options and the week's mix has a Tuesday (Ruling, Krish, 2026-10-30)."""
    return mix.plan(inventory_of(0), WEEK, IDEAS, {NEWS: {'claim': CLAIM, 'mock_sha256': [sha(d) for d in DRIVE.values()]}},
                    urgency=4)


TITLE = 'Synthetic fixture title'


def routed_words(words, channel):
    """A caption that already carries its channel's subscribe route, as content-engine's captions step writes it."""
    return words + ' ' + ('Subscribe free: link in bio.' if channel in ('instagram', 'tiktok')
                          else 'Subscribe: ' + route.subscribe_url(channel, 'maker-' + channel))


def captions_of(plan, words=WORDS, routed=False):
    """Content-engine's captions for the ready concept, one per channel it is placed on, the YouTube title with it
    (Ruling, Krish, 2026-11-26: content-engine writes every caption and title)."""
    concept = next(c for c in plan['concepts'] if c['ready'])
    out = {}
    for placement in concept['placements']:
        channel = placement['channel']
        entry = {'words': routed_words(words, channel) if routed else words}
        if channel == 'youtube':
            entry['title'] = TITLE
        out[channel] = entry
    return {concept['concept_id']: out}


def dispatch_of(plan, files=True, words=WORDS, routed=False):
    body = {key: copy.deepcopy(plan[key]) for key in handoff.MIX_KEYS}
    if files:
        body['mock_files'] = {sha(data): file_id for file_id, data in DRIVE.items()}
        body['mock_covers'] = {sha(VIDEO): VIDEO_COVER_MS}  # the designed cover baked into the cut (F133)
        body['mock_captions'] = captions_of(plan, words, routed)
    return body


class Drive:
    """The Drive download links: each file id serves its bytes; a test may change what one serves."""

    def __init__(self):
        self.files, self.calls = dict(DRIVE), []

    def fetch(self, url):
        self.calls.append(url)
        match = re.match(r'^https://drive\.usercontent\.google\.com/download\?id=([A-Za-z0-9_-]+)&export=download$', url)
        if not match or match.group(1) not in self.files:
            raise BufferError('asset_download_failed')
        data = self.files[match.group(1)]
        return sha(data), len(data), buffer_api.file_type(data[:16])


class Words:
    """A stub for the Anthropic API: the share declaration of the caption, then the blind reader's answer, in the
    schema asked. It never writes words: content-engine wrote them."""

    def __init__(self, answer=None):
        self.answer, self.calls = dict(answer or ANSWER), []

    def json_message(self, system, user, schema, max_tokens=None):
        self.calls.append({'system': system, 'user': user, 'schema': schema})
        if schema is maker.SHARE_SCHEMA:
            return {'share': {k: SHARE[k] for k in ('sender', 'receiver', 'job', 'dm_line', 'moment')}}
        return dict(self.answer)


class MakerTests(unittest.TestCase):
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
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.drive = Drive()
        self.words = Words()
        self.plan = maker_plan()
        self.concept = next(c for c in self.plan['concepts'] if c['ready'])
        self.board = BoardStandIn()
        patcher = mock.patch.object(autorelease, 'route_holds', lambda slot, as_of: ([], True, '2026-11-02'))
        patcher.start()
        self.addCleanup(patcher.stop)

    # The stage ----------------------------------------------------------------------------------

    def handoff(self, payload, now=PLANNED):
        return handoff.handoff(handoff.MIX_PLAN, payload, self.cc.client(), None, now, True, self.drive.fetch, ROOT,
                               str(Path(self.tmp.name) / 'handoff.json'))

    def propose(self, files=True, words=WORDS, routed=False):
        summary, code = self.handoff(dispatch_of(self.plan, files, words, routed))
        self.assertEqual(code, 0, summary)
        return [r['proposals'][0] for r in self.cc.reports.values() if r['proposals']
                and r['proposals'][0]['proposal_id'].startswith(PID)]

    def decide(self, items, verdict='approved'):
        """His answer: since 30 October a yes is his one press on the board's mix; a no is still his decline."""
        if verdict == 'approved':
            self.board.press(self.plan)
            return
        for item in items:
            self.cc.decisions.append({'proposal_id': item['proposal_id'], 'decision': verdict, 'decided_at': DECIDED,
                                      'payload_sha256': item['payload_sha256'], 'stage': 'plan', 'amended': False})

    def approved(self, words=WORDS, routed=False):
        items = self.propose(words=words, routed=routed)
        self.decide(items)
        return items

    def buffer(self):
        return buffer_drafts.DraftBuffer(BKEY, self.buf.base, timeout=5, loopback_for_tests=True)

    def make(self, deliver=True, anthropic=None, now=NOW, day=None):
        anthropic = self.words if anthropic is None else anthropic
        summary, code = maker.maker(self.cc.client(), self.buffer(), anthropic, now, deliver, self.drive.fetch, ROOT,
                                    str(Path(self.tmp.name) / 'maker-handoff.json'), day, board=self.board)
        return without_memes(summary), code

    def creates(self):
        return [c for c in self.buf.calls if c['op'] == 'CreateDraft']

    def release(self):
        return autorelease.autorelease(self.cc.client(), self.buf.client(), RELEASE_AT, True,
                                       lambda url: self.drive.fetch(url)[:2], board=self.board)

    # End to end ---------------------------------------------------------------------------------

    def test_end_to_end_the_maker_drafts_tomorrow_and_release_schedules_each_post(self):
        self.approved(routed=True)
        summary, code = self.make()
        self.assertEqual(code, 0, summary)
        self.assertEqual((summary['days'], summary['slots'].get('made'), summary['handoff']['recorded']),
                         (['2026-11-10'], 4, 4), summary)
        posts = [p for p in self.buf.posts.values()]
        # Content-engine's captions, word for word: the maker writes nothing (Ruling, Krish, 2026-11-26).
        for post in posts:
            channel = {v: k for k, v in {'x': 'twitter'}.items()}.get(post['channelService'], post['channelService'])
            self.assertEqual(post['text'], routed_words(WORDS, channel))
        self.assertEqual({c['schema'] is maker.SHARE_SCHEMA or c['schema'] is maker.REVIEW_SCHEMA
                          for c in self.words.calls}, {True}, 'the model only declares the share and reviews blind')
        self.assertEqual(sorted(p['channelService'] for p in posts), ['instagram', 'tiktok', 'twitter', 'youtube'])
        by_service = {p['channelService']: p for p in posts}
        # Only the approved mock files, each by its own Drive download link: every picture on a carousel,
        # the video on YouTube, the cover on X.
        sources = {s: [a['source'].split('id=')[1].split('&')[0] for a in p['assets']] for s, p in by_service.items()}
        self.assertEqual(sources, {'instagram': ['SyntheticDriveFile0001', 'SyntheticDriveFile0002'],
                                   'tiktok': ['SyntheticDriveFile0001', 'SyntheticDriveFile0002'],
                                   'youtube': ['SyntheticDriveFile0003'], 'twitter': ['SyntheticDriveFile0001']})
        self.assertEqual(by_service['youtube']['assets'][0]['type'], 'video')
        # Each post's review and the day's index are in Control Center, read back by the post's exact sha.
        week = autorelease.week_entries(self.cc.client(), WEEK, {})
        self.assertEqual(len(week), 4)
        for entry in week:
            record = cc_records.read_record(self.cc.client(), cc_records.review_run_id(entry['payload_sha256']),
                                            cc_records.REVIEW)
            self.assertEqual((record['review']['lens'], record['slot']['concept_id']),
                             ('send-test', self.concept['concept_id']))
        self.assertNotIn(WORDS[:20], json.dumps(summary), 'the summary carries codes, never words')
        # Release reads them back from Control Center and schedules each, under every gate.
        summary, code = self.release()
        self.assertEqual((code, summary['slots']), (0, {'scheduled': 4}), summary)

    def test_a_post_that_is_a_board_item_carries_its_item_and_channel_as_utm_content(self):
        # Audit 2026-11-14, I-09: Control Center's sweep binds a sent post to its board item when its utm_content is
        # content_of(<item>-<channel>) (agreed with lane C; control-center #848). The board serves each approved
        # option's item; a post of one carries it, and the release gate still passes it.
        self.approved()
        for row in self.board.approve(self.plan):
            row['item'] = 'engine:' + WEEK + ':' + row['option_id']
        items = {row['option_id']: row['item'] for row in self.board.approved}
        self.assertTrue(items)
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        by_service = {p['channelService']: p for p in self.buf.posts.values()}
        for service, channel in (('twitter', 'x'), ('youtube', 'youtube')):
            text = by_service[service]['text']
            expected = [route.subscribe_url(channel, route.item_content(item, channel)) for item in items.values()]
            self.assertTrue(any(text.endswith('Subscribe: ' + url) for url in expected), text)
            self.assertIn('utm_content=engine-' + WEEK + '-', text)
            self.assertTrue(text.endswith('-' + channel), text)

    def test_item_content_is_the_agreed_form(self):
        self.assertEqual(route.item_content('engine:2026-11-09:gitbroke', 'threads'), 'engine-2026-11-09-gitbroke-threads')
        with self.assertRaises(ValueError):
            route.item_content('engine:2026-11-09:gitbroke', 'linkedin')
        with self.assertRaises(ValueError):
            route.item_content('x' * 70, 'threads')

    def test_the_maker_adds_the_subscribe_route_to_a_caption_with_none_and_release_schedules_each_post(self):
        # Ruling (Krish, 2026-11-11): at U4 and U5 every post carries a subscribe route. Content-engine's caption here
        # carries none; the maker adds it itself, deterministically, after its checks (with_route), so release
        # schedules each post where it held all four as subscribe_route_missing (reverifier, 13 Nov 2026).
        from engine import intensity
        state = intensity.state
        self.approved()
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made'), summary['handoff']['recorded']), (0, 4, 4), summary)
        for call in self.words.calls:  # never by asking the model: it only sees the final words
            self.assertNotIn('subscribe', call['system'].lower())
        by_service = {p['channelService']: p for p in self.buf.posts.values()}
        slot_of = {}
        for entry in autorelease.week_entries(self.cc.client(), WEEK, {}):
            record = cc_records.read_record(self.cc.client(), cc_records.review_run_id(entry['payload_sha256']),
                                            cc_records.REVIEW)
            slot_of[record['slot']['channel']] = record['slot']['slot_id']
        for service, channel in (('twitter', 'x'), ('youtube', 'youtube')):
            text = by_service[service]['text']
            self.assertEqual(text, WORDS + '\nSubscribe: ' + route.subscribe_url(channel, slot_of[channel]))
        for service in ('instagram', 'tiktok'):
            self.assertEqual(by_service[service]['text'], WORDS + '\nSubscribe: link in bio.')
        for post in by_service.values():
            self.assertTrue(concepts.carries(CLAIM, post['text']), 'the claim, word for word')
            self.assertEqual(post['text'].count('Subscribe:'), 1)
        self.assertNotIn('utm_', json.dumps(summary), 'the summary carries codes, never words or URLs')
        with mock.patch.object(intensity, 'state', lambda *a, **k: dict(state(*a, **k), urgency=5)):
            summary, code = self.release()
        self.assertEqual((code, summary['slots'], summary['holds']), (0, {'scheduled': 4}, {}), summary)

    def test_words_that_carry_a_route_get_none_added(self):
        # Never twice: content-engine's caption carries the route, and the maker leaves it exactly so.
        self.approved(routed=True)
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        for post in self.buf.posts.values():
            self.assertEqual(post['text'].count('Subscribe'), 1, post['channelService'])
            self.assertTrue(post['text'].startswith(WORDS + ' Subscribe'))

    def test_a_route_that_would_pass_the_channels_limit_holds_the_slot_and_never_cuts_words(self):
        # X takes 280 weighted characters, a link as 23 (engine/packs.py x_weight): a caption of 260 passes the
        # 270 limit but leaves no room for the route line (35 weighted), so the X slot holds and the others are made.
        long_words = CLAIM + ' ' + ('Synthetic padding words. ' * 20)[:260 - len(CLAIM) - 1].rstrip() + '.'
        self.assertLessEqual(len(long_words), maker.WORDS_MAX['x'])
        self.approved(words=long_words)
        summary, code = self.make()
        self.assertEqual((summary['slots'].get('made'), summary['holds']), (3, {'subscribe_route_too_long': 1}),
                         summary)
        self.assertNotIn('twitter', [p['channelService'] for p in self.buf.posts.values()])
        for post in self.buf.posts.values():
            self.assertTrue(post['text'].startswith(long_words), 'the words are never cut')

    def test_with_route_by_channel(self):
        words = CLAIM + ' Synthetic fixture words.'
        x = maker.with_route({'channel': 'x', 'slot_id': 'X-2026-11-10-0830'}, words)
        self.assertEqual(x, words + '\nSubscribe: ' + route.subscribe_url('x', 'x-2026-11-10-0830'))
        self.assertEqual(maker.with_route({'channel': 'x', 'slot_id': 'x-1'}, x), x, 'never twice')
        self.assertEqual(maker.with_route({'channel': 'tiktok', 'slot_id': 't-1'}, words),
                         words + '\nSubscribe: link in bio.')
        self.assertEqual(maker.with_route({'channel': 'linkedin', 'slot_id': 'li-1'}, words), words, 'his click')
        # A link for another channel is no route here: X gets its own.
        other = words + ' ' + route.subscribe_url('youtube', 'yt-1')
        self.assertIn('utm_source=x', maker.with_route({'channel': 'x', 'slot_id': 'x-1'}, other))
        self.assertEqual(route.content_of('X.2026 11 10/0830'), 'x-2026-11-10-0830')
        with self.assertRaises(ValueError):
            route.content_of('...')

    # content-engine's 10/10 judges (Ruling, Krish, 2026-11-12: "Judge them; count passes."). Since 26 Nov 2026
    # content-engine's make flow asks them itself; the maker binds the pass to the post it saves. -------------------

    def test_every_carousel_and_short_is_bound_to_its_post_and_no_judge_is_asked(self):
        self.approved()
        summary, code = self.make()
        self.assertEqual(code, 0, summary)
        calls = [b for _, b in getattr(self.board, 'judge_calls', [])]
        self.assertEqual([b for b in calls if b.get('op') == 'judge'], [], 'the maker asks no judge')
        bound = [b for b in calls if b.get('op') == 'bind']
        posts = {p['id']: p for p in self.buf.posts.values()}
        judged = [p for p in posts.values() if p['channelService'] in ('instagram', 'tiktok', 'youtube')]
        self.assertEqual(sorted(b['buffer_post_id'] for b in bound), sorted(p['id'] for p in judged))
        self.assertEqual(summary['judges'], {'bound': len(judged)})
        for b in bound:  # the artifact is the saved post's format, channel, exact words and pictures
            self.assertRegex(b['artifact_sha256'], '^[0-9a-f]{64}$')

    def test_a_bind_that_does_not_land_is_counted_and_never_stops_the_post(self):
        self.approved()
        real = self.board.judge

        def refused(monday, body):
            from engine.run.board_tick import BoardError
            if body.get('op') == 'bind':
                raise BoardError('board_unreachable')
            return real(monday, body)
        self.board.judge = refused
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        self.assertEqual(summary['judges'], {'bind_failed': 3}, summary)

    def test_drafts_are_saved_to_draft_with_no_due_time_and_never_published(self):
        self.approved()
        self.make()
        for call in self.creates():
            sent = call['variables']['input']
            self.assertIs(sent['saveToDraft'], True)
            self.assertNotIn('dueAt', sent)
            self.assertIn(sent['channelId'], [BUFFER_CHANNEL_ID[c] for c in concepts.CONCEPT_CHANNELS])
            self.assertIn('createPost(input: $input)', call['query'])
        self.assertEqual(len(self.creates()), 4)
        self.assertEqual([c for c in self.buf.calls if c['op'] == 'ScheduleDraft'], [], 'the maker never schedules')
        self.assertTrue(all(p['status'] == 'draft' and p['dueAt'] is None for p in self.buf.posts.values()))

    def test_a_second_run_makes_nothing_new(self):
        self.approved()
        self.make()
        before = (len(self.buf.posts), len(self.cc.reports))
        summary, code = self.make()
        self.assertEqual((code, outcomes(summary)), (0, {'already_made': 4}), summary)
        self.assertEqual((len(self.buf.posts), len(self.cc.reports)), before)

    def test_a_draft_saved_but_never_handed_off_is_adopted_on_the_next_run_never_made_twice(self):
        # Review finding 2: a handoff that fails stops the run at once, and the next run adopts the draft it
        # stranded (rebuilt from Buffer, checked against the caption, its share declared, reviewed blind, handed off)
        # and makes the rest.
        self.approved(routed=True)
        failed = ({'slots': {}, 'holds': {}, 'error': 'synthetic'}, 1)
        with mock.patch.object(handoff, 'handoff', return_value=failed):
            summary, code = self.make()
        self.assertEqual((code, summary['loud'], len(self.creates())), (1, ['handoff_incomplete'], 1), summary)
        self.assertEqual(autorelease.week_entries(self.cc.client(), WEEK, {}), [])
        summary, code = self.make()
        self.assertEqual((code, outcomes(summary), summary['loud'], len(self.creates())),
                         (0, {'adopted': 1, 'made': 3, 'drafts_saved': 3}, [], 4), summary)
        declared = [c for c in self.words.calls if c['schema'] is maker.SHARE_SCHEMA]
        self.assertEqual(len(declared), 5, 'every caption has its share declared, its words never rewritten')
        self.assertEqual(len(autorelease.week_entries(self.cc.client(), WEEK, {})), 4)
        summary, code = self.make()
        self.assertEqual((code, outcomes(summary)), (0, {'already_made': 4}), summary)
        summary, code = self.release()
        self.assertEqual((code, summary['slots']), (0, {'scheduled': 4}), summary)

    def test_each_draft_is_handed_off_as_soon_as_it_is_saved(self):
        # Review finding 2: a refused key after the first draft never strands it.
        self.approved()

        class Refused(Words):
            def json_message(self, system, user, schema, max_tokens=None):
                if len(self.calls) >= 2:  # the first slot's share and review answer; then the key is refused
                    raise anthropic_api.AnthropicAuthError(401)
                return Words.json_message(self, system, user, schema, max_tokens)
        summary, code = self.make(anthropic=Refused())
        self.assertEqual((code, summary['error'], len(self.creates())), (1, 'anthropic_key_refused', 1), summary)
        self.assertEqual(len(autorelease.week_entries(self.cc.client(), WEEK, {})), 1, 'handed off before the error')
        summary, code = self.make()
        self.assertEqual((code, outcomes(summary), summary['loud']),
                         (0, {'already_made': 1, 'made': 3, 'drafts_saved': 3}, []), summary)

    def test_one_run_never_makes_two_drafts_of_one_concept_on_one_channel(self):
        # Review finding 2 (P2): the concept and channel are taken before the save, so a slot that holds after
        # its draft is saved never lets a second slot of the same concept and channel make another.
        self.approved()
        real_slots, real_line, seen = maker.week_slots, autorelease.draft_line, []

        def doubled(*args, **kwargs):
            slots = real_slots(*args, **kwargs)
            first = next(s for s in slots if s['channel'] == 'x' and s['concept_id'])
            return slots + [dict(first, slot_id=first['slot_id'] + '-twin')]

        def flaky(post, fields, fetch):
            if post.get('channelService') == 'twitter' and not seen:
                seen.append(1)
                raise buffer_api.CarryHold('format_differs_from_draft')
            return real_line(post, fields, fetch)
        with mock.patch.object(maker, 'week_slots', doubled), mock.patch.object(autorelease, 'draft_line', flaky):
            summary, code = self.make()
        x = [c for c in self.creates() if c['variables']['input']['channelId'] == BUFFER_CHANNEL_ID['x']]
        self.assertEqual((len(x), summary['holds']), (1, {'format_differs_from_draft': 1}), summary)

    def test_a_dry_run_mutates_nothing(self):
        self.approved()
        reports = copy.deepcopy(self.cc.reports)
        self.cc.calls = []
        summary, code = self.make(deliver=False)
        self.assertEqual((code, outcomes(summary), summary['mutations']), (0, {'would_make': 4}, 0), summary)
        self.assertEqual(self.creates(), [])
        self.assertEqual(self.buf.posts, {})
        self.assertEqual(self.cc.reports, reports)
        # The voice check is a POST that reads: it stores nothing (Control Center api/_voiceCheck.ts).
        self.assertEqual([c for c in self.cc.calls if c['method'] == 'POST' and not c['path'].endswith('/voice-check')], [],
                         'a dry run writes nothing to Control Center')

    def test_a_draft_buffer_reads_back_as_queued_stops_the_whole_run_at_once(self):
        # Review finding 1: saveToDraft ignored and the post queued. The readback stops the run loudly at the first
        # one; no further draft is made.
        self.approved()
        real = tra_created_post()

        def queued(stand, data):
            post = real(stand, data)
            post.update(status='scheduled', dueAt='2026-11-10T14:00:00.000Z')
            return post
        with mock.patch.object(sys.modules[BufferStandIn.__module__], 'created_post', queued):
            summary, code = self.make()
        self.assertEqual((code, len(self.creates()), summary['loud']), (1, 1, ['draft_not_a_draft']), summary)
        self.assertEqual(summary['holds'], {'draft_not_a_draft': 1}, summary)
        self.assertEqual(autorelease.week_entries(self.cc.client(), WEEK, {}), [], 'a queued post is never handed off')

    def test_a_draft_read_back_with_a_due_time_also_stops_and_one_with_no_due_key_is_a_draft(self):
        # Review findings 1 and 6: dueAt null or absent is a draft; a due time on a "draft" is not.
        self.approved()
        real = tra_created_post()

        def keyless(stand, data):
            post = real(stand, data)
            del post['dueAt']
            return post
        with mock.patch.object(sys.modules[BufferStandIn.__module__], 'created_post', keyless):
            summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        self.assertFalse(maker.is_draft({'status': 'draft', 'dueAt': '2026-11-10T14:00:00.000Z'}))
        self.assertFalse(maker.is_draft({'status': 'scheduled'}))
        self.assertTrue(maker.is_draft({'status': 'draft', 'dueAt': None}) and maker.is_draft({'status': 'draft'}))

    def test_instagram_says_not_ai_generated_and_drafts_are_listed_from_a_week_before_monday(self):
        # Review finding 6.
        self.approved()
        self.make()
        sent = {c['variables']['input']['channelId']: c['variables']['input'] for c in self.creates()}
        self.assertEqual(sent[BUFFER_CHANNEL_ID['instagram']]['metadata'],
                         {'instagram': {'type': 'post', 'shouldShareToFeed': True, 'isAiGenerated': False}})
        listed = [c['variables']['input']['filter'] for c in self.buf.calls if c['op'] == 'ListPosts']
        drafts = [f for f in listed if f.get('status') == ['draft']]
        self.assertEqual(len(drafts), 4, 'one draft listing per channel')
        self.assertEqual({f['createdAt']['start'] for f in drafts}, {'2026-11-02T00:00:00-05:00'}, drafts)
        self.assertTrue(all('dueAt' not in f for f in drafts), 'a draft has no due time to filter on')

    def test_an_anthropic_api_that_stays_busy_fails_the_run_loudly(self):
        # Review finding 5: after its retries a busy API is loud (exit 1), never a quiet per-slot hold.
        self.approved()

        class Busy(Words):
            def json_message(self, system, user, schema, max_tokens=None):
                self.calls.append(schema)
                raise anthropic_api.AnthropicError('anthropic_overloaded', 529)
        busy = Busy()
        summary, code = self.make(anthropic=busy)
        self.assertEqual((code, summary['loud'], len(busy.calls), self.creates()),
                         (1, ['anthropic_overloaded'], 1, []), summary)

    def test_no_slot_is_started_after_the_run_deadline(self):
        # Review finding 5: the run's deadline bounds it whatever the slot count; the rest waits, loudly.
        self.approved()
        clock = [0.0]

        class Slow(Words):
            def json_message(self, system, user, schema, max_tokens=None):
                clock[0] = maker.RUN_BUDGET + 1.0  # the first slot's calls use up the run's time
                return Words.json_message(self, system, user, schema, max_tokens)
        summary, code = maker.maker(self.cc.client(), self.buffer(), Slow(), NOW, True, self.drive.fetch, ROOT,
                                    str(Path(self.tmp.name) / 'maker-handoff.json'), None, lambda: clock[0],
                                    board=self.board)
        self.assertEqual((code, summary['slots'].get('made'), summary['loud']), (1, 1, ['maker_out_of_time']),
                         summary)
        self.assertEqual(len(autorelease.week_entries(self.cc.client(), WEEK, {})), 1)

    def test_the_worst_case_run_fits_the_job_limit(self):
        # Review finding 5: the worst case, computed. One call: three attempts of TIMEOUT and at most MAX_WAIT of
        # waiting. A run's Anthropic time is bounded by its deadline whatever the slot count, one slot's calls
        # fit inside it, and what is left of the job's limit is the last slot's Buffer and Control Center work.
        a = anthropic_api
        self.assertEqual(a.CALL_WORST, a.MAX_ATTEMPTS * a.TIMEOUT + a.MAX_WAIT)
        self.assertEqual((a.MAX_ATTEMPTS, a.CALL_WORST), (3, 240))
        self.assertLess(a.MAX_WAIT, 90)
        self.assertLessEqual(maker.CALLS_PER_SLOT * a.CALL_WORST, maker.RUN_BUDGET)
        self.assertGreaterEqual(maker.JOB_LIMIT - maker.RUN_BUDGET, 600)
        text = (ROOT / '.github' / 'workflows' / 'maker.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: ' + str(maker.JOB_LIMIT // 60), text)
        cfg = json.loads((ROOT / 'mix.json').read_text(encoding='utf-8'))
        per_day = len(cfg['slot_times']) * len(cfg['channels'])
        self.assertLessEqual(per_day, handoff.MAX_INDEX_PARTS, 'one index record per draft fits the day index')

    # His authority -----------------------------------------------------------------------------------

    def test_an_unapproved_concept_makes_no_draft(self):
        # Ruling (Krish, 2026-11-12): with no approved mix the week makes nothing and asks him once; nothing of his
        # concept reaches Buffer or the model.
        self.propose()
        summary, code = self.make()
        self.assertEqual((code, summary['holds'], summary['drafted_from']), (0, {}, {'2026-W46': 'no_approved_mix'}),
                         summary)
        self.assertEqual(summary['standing']['2026-W46'], {'why': 'mix_not_approved', 'ask': 'raised'})
        self.assertEqual((self.creates(), self.words.calls), ([], []))

    def test_a_stopped_week_makes_nothing(self):
        self.decide(self.propose(), 'declined')
        summary, code = self.make()
        self.assertEqual((code, outcomes(summary)), (0, {'week_stopped': 1}), summary)
        self.assertEqual((self.creates(), self.words.calls), ([], []))

    def test_a_concept_deleted_from_his_amended_yes_makes_nothing(self):
        items = self.propose()
        line = mix.concept_line(self.concept)
        text = items[0]['exact_payload'].replace(line + '\n', '')
        from engine.control_center import amended_digest
        self.cc.decisions.append({'proposal_id': items[0]['proposal_id'], 'decision': 'approved', 'decided_at': DECIDED,
                                  'payload_sha256': items[0]['payload_sha256'], 'stage': 'plan', 'amended': True,
                                  'exact_payload': text, 'amount_usd': None, 'amended_sha256': amended_digest(None, text)})
        self.board.press(self.plan)
        summary, _ = self.make()
        self.assertEqual(summary['holds'], {concepts.STOPPED: 4}, summary)
        self.assertEqual(self.creates(), [])

    def test_missing_anthropic_key_holds_loudly_and_reads_nothing(self):
        self.approved()
        self.cc.calls = []
        summary, code = maker.maker(self.cc.client(), self.buffer(), None, NOW, True, self.drive.fetch, ROOT)
        self.assertEqual((code, summary['holds'], summary['loud']),
                         (1, {'anthropic_key_missing': 1}, ['anthropic_key_missing']), summary)
        self.assertEqual((self.cc.calls, self.buf.calls, self.drive.calls), ([], [], []))
        out = []
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            code = maker.main(['maker', '--deliver', '--now', NOW], out=out.append)
        self.assertEqual((code, json.loads(out[0])['holds']), (1, {'anthropic_key_missing': 1}))

    # The mocks ---------------------------------------------------------------------------------------

    def test_a_mock_whose_bytes_differ_from_its_hash_makes_no_draft(self):
        self.approved()
        self.drive.files['SyntheticDriveFile0002'] = FRAME2 + b'one changed byte\n'
        summary, code = self.make()
        self.assertEqual(summary['holds'], {'mock_hash_mismatch': 4}, summary)
        self.assertEqual((self.creates(), self.words.calls), ([], []))

    def test_a_video_whose_designed_cover_frame_is_not_recorded_is_held_never_made(self):
        # F133 (Ruling, Krish, 2026-11-15): Buffer takes no cover image, and a null thumbnailOffset showed frame 0.
        payload = dispatch_of(self.plan)
        del payload['mock_covers']
        self.handoff(payload)
        self.decide([r['proposals'][0] for r in self.cc.reports.values() if r['proposals']])
        summary, code = self.make()
        self.assertEqual(summary['holds'], {'video_without_designed_cover': 1}, summary)
        self.assertIn('video_without_designed_cover', summary['loud'])
        self.assertEqual(code, 1)
        sent = [a for c in self.creates() for a in c['variables']['input']['assets']]
        self.assertTrue(sent and not any('video' in a for a in sent), 'no video draft is saved without its cover')

    def test_a_video_is_saved_pointing_at_its_designed_cover_frame(self):
        self.approved()
        self.make()
        videos = [a['video'] for c in self.creates() for a in c['variables']['input']['assets'] if 'video' in a]
        self.assertEqual(videos and [v['metadata'] for v in videos], [{'thumbnailOffset': VIDEO_COVER_MS}])

    def test_a_cover_for_a_file_the_manifest_does_not_name_is_refused(self):
        payload = dispatch_of(self.plan)
        payload['mock_covers'] = {'f' * 64: 1000}
        self.assertEqual(self.handoff(payload)[0]['error'], 'payload_rejected_bad_mock_covers')

    def test_a_mock_missing_from_the_manifest_holds(self):
        payload = dispatch_of(self.plan)
        del payload['mock_files'][sha(VIDEO)]
        del payload['mock_covers']
        summary, code = self.handoff(payload)
        self.assertEqual(summary['holds'], {'mock_file_missing': 1}, summary)
        self.decide([r['proposals'][0] for r in self.cc.reports.values() if r['proposals']])
        summary, code = self.make()
        self.assertEqual(summary['holds'], {'mock_file_missing': 4}, summary)
        self.assertEqual(self.creates(), [])

    def test_a_week_with_no_mock_manifest_holds_loudly(self):
        self.decide(self.propose(files=False))
        summary, code = self.make()
        self.assertEqual((code, summary['holds']), (1, {'mock_manifest_missing': 4}), summary)

    def test_the_manifest_refuses_a_file_the_plan_does_not_name_or_a_bad_id(self):
        payload = dispatch_of(self.plan)
        payload['mock_files']['f' * 64] = 'SyntheticDriveFile0009'
        self.assertEqual(self.handoff(payload)[0]['error'], 'payload_rejected_mock_file_not_in_plan')
        payload = dispatch_of(self.plan)
        payload['mock_files'][sha(VIDEO)] = 'not a drive id!'
        self.assertEqual(self.handoff(payload)[0]['error'], 'payload_rejected_bad_mock_files')

    def test_a_corrected_mock_manifest_is_the_next_version_and_the_maker_reads_the_highest(self):
        # Review finding 3: a records_only re-send with a corrected mock_files map is written as the next numbered
        # record; the keys must still be the plan's hashes and the bytes are still hash-checked.
        wrong = dispatch_of(self.plan)
        wrong['mock_files'][sha(FRAME2)] = 'SyntheticDriveFile0001'  # a slip: frame two mapped to frame one's file
        summary, code = self.handoff(wrong)
        self.assertEqual(code, 0, summary)
        self.decide([r['proposals'][0] for r in self.cc.reports.values() if r['proposals']])
        summary, _ = self.make()
        self.assertEqual(summary['holds'], {'mock_hash_mismatch': 4}, summary)
        parts = cc_records.read_record(self.cc.client(), cc_records.version_run_id('2026-W46', 1),
                                       cc_records.VERSION)['parts']
        mocks = lambda: sorted(k for k in self.cc.reports if ':mocks:2026-W46:' + cc_records.plan_key(parts) + ':' in k)
        before = mocks()
        summary, code = self.handoff(dict(dispatch_of(self.plan), records_only=True), now='2026-11-08T20:00:00Z')
        self.assertEqual((code, summary['loud'], summary['reports']['posted']), (0, [], 1), summary)
        after = mocks()
        self.assertEqual(len(after), len(before) + 1, 'the next numbered record')
        record = cc_records.record_of(self.cc.reports[after[-1]], cc_records.MOCKS)
        self.assertEqual((record['version'], record['files'][sha(FRAME2)]), (2, 'SyntheticDriveFile0002'))
        summary, code = self.handoff(dict(dispatch_of(self.plan), records_only=True), now='2026-11-08T21:00:00Z')
        self.assertEqual((code, summary['reports']['posted'], mocks()), (0, 0, after), 'the same map: nothing new')
        bad = dict(dispatch_of(self.plan), records_only=True)
        bad['mock_files']['f' * 64] = 'SyntheticDriveFile0009'
        self.assertEqual(self.handoff(bad)[0]['error'], 'payload_rejected_mock_file_not_in_plan')
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        self.assertIn('https://drive.usercontent.google.com/download?id=SyntheticDriveFile0002&export=download',
                      self.drive.calls, 'the corrected file is downloaded and hashed before use')

    # The words and the review --------------------------------------------------------------------------

    def test_a_slot_with_no_caption_holds_and_the_maker_writes_none(self):
        payload = dispatch_of(self.plan)
        cid = self.concept['concept_id']
        del payload['mock_captions'][cid]['x']
        self.handoff(payload)
        self.decide([r['proposals'][0] for r in self.cc.reports.values() if r['proposals']])
        summary, code = self.make()
        self.assertEqual((summary['holds'], summary['slots'].get('made')), ({'caption_missing': 1}, 3), summary)
        self.assertNotIn('twitter', [p['channelService'] for p in self.buf.posts.values()])

    def test_a_caption_for_a_concept_not_in_the_plan_or_malformed_is_refused(self):
        payload = dispatch_of(self.plan)
        payload['mock_captions']['no-such-concept'] = {'x': {'words': 'Synthetic.'}}
        self.assertEqual(self.handoff(payload)[0]['error'], 'payload_rejected_caption_not_in_plan')
        for bad in ({'x': {'words': ''}}, {'x': {'words': 'Synthetic.', 'extra': 1}}, {'myspace': {'words': 'S.'}},
                    {'x': 'Synthetic.'}, {}):
            payload = dispatch_of(self.plan)
            payload['mock_captions'][self.concept['concept_id']] = bad
            self.assertEqual(self.handoff(payload)[0]['error'], 'payload_rejected_bad_mock_captions', bad)

    def test_corrected_captions_are_the_next_mock_manifest_version(self):
        summary, code = self.handoff(dispatch_of(self.plan, words=WORDS + ' A first take.'))
        self.assertEqual(code, 0, summary)
        self.decide([r['proposals'][0] for r in self.cc.reports.values() if r['proposals']])
        summary, code = self.handoff(dict(dispatch_of(self.plan), records_only=True), now='2026-11-08T20:00:00Z')
        self.assertEqual((code, summary['reports']['posted']), (0, 1), summary)
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)
        for post in self.buf.posts.values():
            self.assertNotIn('A first take', post['text'], 'the highest version is the captions in force')

    def test_captions_missing_the_claim_hold(self):
        self.approved(words='Synthetic fixture words that never carry the approved line.')
        summary, code = self.make()
        self.assertEqual(summary['holds'], {'words_missing_claim': 4}, summary)
        self.assertEqual((self.creates(), self.words.calls), ([], []))

    def test_captions_failing_the_copy_lint_hold_and_are_never_rewritten(self):
        self.approved(words=WORDS + ' Krish says so.')
        summary, code = self.make()
        self.assertEqual(summary['holds'], {'copy_lint_refused': 4}, summary)
        self.assertEqual((self.creates(), self.words.calls), ([], []), 'no rewrite: it goes back to content-engine')

    def test_captions_asking_for_the_share_hold(self):
        self.approved(words=WORDS + ' Share this with your team.')
        summary, _ = self.make()
        self.assertEqual(summary['holds'], {'share_ask_refused': 4}, summary)

    def test_a_blind_reader_who_would_not_send_it_holds(self):
        self.approved()
        stub = Words(answer={'would_send': False, 'receiver': None, 'job': None, 'dm_line': None, 'why': 'Synthetic.'})
        summary, _ = self.make(anthropic=stub)
        self.assertEqual(summary['holds'], {'review_not_passed': 4}, summary)
        self.assertEqual(self.creates(), [])
        review = [c for c in stub.calls if c['schema'] is maker.REVIEW_SCHEMA][0]
        # The reader sees the lens and the post only: never the share block, the idea, the claim's source or a link.
        self.assertNotIn(SHARE['receiver'], review['user'] + review['system'])
        self.assertNotIn(self.concept['idea'], review['user'])
        self.assertNotIn('drive.usercontent', review['user'])

    # The slots record -------------------------------------------------------------------------------

    def test_slots_that_differ_from_the_plan_he_approved_hold_loudly(self):
        self.approved()
        parts = cc_records.read_record(self.cc.client(), cc_records.version_run_id('2026-W46', 1),
                                       cc_records.VERSION)['parts']
        ids = sorted(k for k in self.cc.reports if ':mixslots:2026-W46:' + cc_records.plan_key(parts) + ':' in k)
        self.assertGreater(len(ids), 1, 'a full week of slots rides in more than one chunk')
        original = {i: copy.deepcopy(self.cc.reports[i]) for i in ids}

        def tamper(change):
            for run_id in ids:
                record = cc_records.record_of(original[run_id], cc_records.SLOTS)
                if change(record['slots']):
                    self.cc.reports[run_id] = cc_records.record_report(run_id, cc_records.SLOTS, record,
                                                                       ['Synthetic'], PLANNED, 'synthetic-revision')
                    return
            self.fail('no slot to change')

        def concept_on_a_meme_slot(slots):
            # The concept moved to another lane's slot: its channels are no longer its approved placements.
            for slot in slots:
                if slot['concept_id'] is None and slot['channel'] == 'x' and slot['lane'] == 'meme':
                    slot['concept_id'] = self.concept['concept_id']
                    return True

        def concept_dropped(slots):
            # The concept taken off its X slot and the slot left empty: the plan lines he read count it.
            for slot in slots:
                if slot['concept_id'] == self.concept['concept_id'] and slot['channel'] == 'x':
                    slot['concept_id'] = None
                    return True

        for change in (concept_on_a_meme_slot, concept_dropped):
            for run_id in ids:
                self.cc.reports[run_id] = copy.deepcopy(original[run_id])
            tamper(change)
            summary, code = self.make()
            self.assertEqual((code, summary['holds']), (1, {'slots_differ_from_plan': 1}), (change, summary))
            self.assertEqual(self.creates(), [])

    def test_the_slots_record_is_written_by_a_re_dispatch_and_leaves_his_digests_unchanged(self):
        # As W45 was: the plan dispatched and decided before the slots and mock records existed.
        items = self.propose()
        self.decide(items)
        extra = {k for k in self.cc.reports if ':mixslots:' in k or ':mocks:' in k}
        self.assertTrue(extra)
        for key in extra:
            del self.cc.reports[key]
        before = {k: copy.deepcopy(v) for k, v in self.cc.reports.items()}
        summary, code = self.handoff(dispatch_of(self.plan), now='2026-11-08T20:00:00Z')
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['reports']['posted'], len(extra), 'only the new records are written')
        self.assertEqual(summary['reports']['already_reported'], len(items) + 1, 'every part and the version')
        for key, report in before.items():
            self.assertEqual(self.cc.reports[key], report, key)
        again = [r['proposals'][0] for r in self.cc.reports.values() if r['proposals']]
        self.assertEqual([(i['proposal_id'], i['payload_sha256']) for i in again],
                         [(i['proposal_id'], i['payload_sha256']) for i in items])
        state = autorelease.week_state(self.cc.client(), WEEK, self.cc.decisions, self.tmp.name, NOW, ROOT,
                                       board=self.board)
        self.assertEqual((state['hold'], state['stopped']), (None, False), state)
        summary, code = self.make()
        self.assertEqual((code, summary['slots'].get('made')), (0, 4), summary)

    def test_records_only_writes_the_records_and_refuses_a_plan_not_in_force(self):
        items = self.propose()
        self.decide(items)
        extra = sorted(k for k in self.cc.reports if ':mixslots:' in k or ':mocks:' in k)
        for key in extra:
            del self.cc.reports[key]
        before = {k: copy.deepcopy(v) for k, v in self.cc.reports.items()}
        # A plan that is not the one in force (here one weight moved) is refused whole: nothing is written,
        # so no new version can withdraw his yes.
        changed = copy.deepcopy(self.plan)
        changed['weights'] = dict(changed['weights'], meme=changed['weights']['meme'] + 5,
                                  repurposed_carousel=changed['weights']['repurposed_carousel'] - 5)
        summary, code = self.handoff(dict(dispatch_of(changed), records_only=True))
        self.assertEqual((code, summary['error']), (1, 'payload_rejected_records_only_plan_not_in_force'), summary)
        self.assertEqual(self.cc.reports, before)
        summary, code = self.handoff(dict(dispatch_of(self.plan), records_only='yes'))
        self.assertEqual(summary['error'], 'payload_rejected_bad_records_only')
        # The plan in force: only the slots and mock records are written; no part or version is even sent.
        self.cc.calls = []
        summary, code = self.handoff(dict(dispatch_of(self.plan), records_only=True))
        self.assertEqual((code, summary['reports']['posted'], summary['reports']['already_reported']),
                         (0, len(extra), 0), summary)
        self.assertEqual(sorted(set(self.cc.reports) - set(before)), extra)
        for key, report in before.items():
            self.assertEqual(self.cc.reports[key], report, key)
        posted = [c for c in self.cc.calls if c['method'] == 'POST']
        self.assertEqual(len(posted), len(extra))

    def test_a_week_whose_slots_were_never_recorded_holds_loudly(self):
        self.approved()
        for key in [k for k in self.cc.reports if ':mixslots:' in k]:
            del self.cc.reports[key]
        summary, code = self.make()
        self.assertEqual((code, summary['holds']), (1, {'slots_record_missing': 1}), summary)

    # With no approved mix: one ask a week, nothing drafted (Ruling, Krish, 2026-11-12 and 2026-11-26) -------------

    def asks(self):
        """Every ask on his list: the proposals with this title, across every report."""
        return [(k, item) for k, r in self.cc.reports.items() for item in r['proposals'] if item['title'] == maker.ASK_TITLE]

    def ask_posts(self):
        return [c for c in self.cc.calls if c['method'] == 'POST' and (c['key'] or '').startswith('makeyourmindup:mixask:')]

    def test_with_no_mix_reported_nothing_is_drafted_and_one_ask_is_raised(self):
        summary, code = self.make()  # Monday 23:30 in New York: Tuesday, with no plan reported for the week
        self.assertEqual((code, summary['loud'], summary['holds'], summary['error']), (0, [], {}, None), summary)
        self.assertEqual(summary['drafted_from'], {'2026-W46': 'no_approved_mix'})
        self.assertEqual(summary['standing']['2026-W46'], {'why': 'mix_plan_not_reported', 'ask': 'raised'}, summary)
        # Nothing in Buffer, nothing handed off, nothing written by a model, no standing drafts.
        self.assertEqual((self.creates(), summary['mutations'], self.words.calls), ([], 0, []))
        self.assertFalse([k for k in self.cc.reports if ':review:' in k or ':derived:' in k or ':standing:' in k])
        self.assertEqual([k for k, _ in self.asks()], ['makeyourmindup:mixask:2026-W46'])
        lines = maker.step_summary(summary)
        self.assertIn('- 2026-W46: nothing drafted, no approved weekly mix (mix_plan_not_reported). The ask: raised.',
                      lines)

    def test_a_dry_run_with_no_mix_raises_nothing(self):
        summary, code = self.make(deliver=False)
        self.assertEqual((code, summary['standing']['2026-W46']['ask']), (0, 'would_raise'), summary)
        self.assertEqual([c for c in self.cc.calls if c['method'] == 'POST' and c['path'].endswith('/reports')], [])
        self.assertEqual((self.cc.reports, self.creates()), ({}, []))

    def test_a_past_week_whose_slots_record_is_missing_is_skipped_and_noted(self):
        # W45's plan was reported with no slots record (6 to 8 November). On Sunday's run its only day is the rest day
        # that ends it: nothing of it can be made, so its hold is noted and never fails the run.
        past = mix.plan(inventory_of(0), '2026-11-02', IDEAS,
                        {NEWS: {'claim': CLAIM, 'mock_sha256': [sha(d) for d in DRIVE.values()]}}, urgency=4)
        summary, code = self.handoff(dispatch_of(past), now='2026-11-02T12:00:00Z')
        self.assertEqual(code, 0, summary)
        for key in [k for k in self.cc.reports if ':mixslots:2026-W45:' in k]:
            del self.cc.reports[key]
        summary, code = self.make(now='2026-11-08T12:00:00Z')  # Sunday 07:00 in New York: Sunday and Monday
        self.assertEqual((summary['days'], summary['weeks']), (['2026-11-08', '2026-11-09'], ['2026-W45', '2026-W46']))
        self.assertEqual((code, summary['loud'], summary['holds']), (0, [], {}), summary)
        self.assertEqual(summary['skipped_weeks'], {'2026-W45': 'slots_record_missing'})
        self.assertEqual(summary['drafted_from'], {'2026-W46': 'no_approved_mix'})
        self.assertIn('- 2026-W45: skipped, nothing of it can be made in this run (slots_record_missing).',
                      maker.step_summary(summary))

    def test_the_week_raises_one_ask_and_every_other_run_that_week_is_silent(self):
        runs = ['2026-11-09T12:00:00Z', '2026-11-09T18:00:00Z', '2026-11-10T12:00:00Z', '2026-11-11T12:00:00Z',
                '2026-11-12T12:00:00Z', '2026-11-13T12:00:00Z', '2026-11-14T12:00:00Z']  # seven runs, all in W46
        asks = []
        for now in runs:
            summary, code = self.make(now=now)
            self.assertEqual((code, summary['loud']), (0, []), summary)
            asks.append(summary['standing']['2026-W46']['ask'])
        self.assertEqual(asks, ['raised'] + ['already_raised'] * 6)
        self.assertEqual(len(self.ask_posts()), 1, 'the second to the seventh run raise nothing')
        summary, code = self.make(now='2026-11-16T12:00:00Z')
        self.assertEqual((code, summary['standing']['2026-W47']['ask']), (0, 'raised'), summary)
        summary, code = self.make(now='2026-11-17T12:00:00Z')
        self.assertEqual((code, summary['standing']['2026-W47']['ask']), (0, 'already_raised'), summary)
        self.assertEqual([k for k, _ in self.asks()], ['makeyourmindup:mixask:2026-W46', 'makeyourmindup:mixask:2026-W47'])

    def test_the_ask_says_nothing_goes_out_and_ends_with_the_week(self):
        self.make()
        (key, item), = self.asks()
        report = self.cc.reports[key]
        self.assertEqual((item['proposal_id'], item['wall'], item['kind'], item['close_condition']['event']),
                         ('makeyourmindup:mixask:2026-W46', 'strategy', 'advice', 'mix_approved'))
        self.assertEqual(item['expires_at'], '2026-11-16T05:00:00Z', 'it ends with the week, New York time')
        self.assertTrue(item['exact_payload'].startswith(maker.ASK_TITLE + ': the week of Monday 9 November 2026'))
        for needle in ('nothing from this week is put in Buffer, scheduled or posted', 'Content-engine makes every post',
                       "approve this week's mix on the publish board", 'once a week'):
            self.assertIn(needle, item['exact_payload'])
        self.assertEqual(item['evidence'][0]['url'], 'https://controlcenter.krishraja.com/#/content?week=2026-11-09')
        self.assertEqual((report['status'], report['holds']),
                         ('held', [{'reason': 'week_mix_not_approved', 'detail': '2026-W46: mix_plan_not_reported'}]))
        self.assertNotIn('\u2014', item['exact_payload'])
        self.assertNotIn('standing plan', item['exact_payload'].lower())

    def test_once_his_mix_is_approved_the_next_run_makes_his_plan(self):
        summary, _ = self.make(now='2026-11-10T04:30:00Z')
        self.assertEqual(summary['drafted_from'], {'2026-W46': 'no_approved_mix'})
        self.propose()  # reported, not yet approved on the board: still nothing, and no second ask
        summary, code = self.make(now='2026-11-10T04:40:00Z')
        self.assertEqual((code, summary['standing']['2026-W46']), (0, {'why': 'mix_not_approved',
                                                                      'ask': 'already_raised'}), summary)
        self.board.press(self.plan)  # his yes on the week's mix
        summary, code = self.make(now='2026-11-10T04:50:00Z')
        self.assertEqual((code, summary['drafted_from'], summary['standing']), (0, {'2026-W46': 'his_mix'}, {}), summary)
        self.assertEqual((summary['slots'].get('made'), summary['handoff']['recorded'], len(self.creates())), (4, 4, 4))
        self.assertEqual(len(self.ask_posts()), 1)

    def test_the_ask_report_carries_the_engine_state_when_served(self):
        # Control Center shows the newest live report's priorities, obsessions and next steps on every place, so a
        # maker report without them blanked the engine's state there (the W46 ask, 12 November 2026).
        self.make()  # not served: the report goes as before, at 1.0.0 with no state
        plain = self.cc.reports['makeyourmindup:mixask:2026-W46']
        self.assertEqual((plain['schema_version'], 'priorities' in plain), ('1.0.0', False))
        self.cc.reports, self.cc.calls = {}, []
        saved = (self.cc.versions, self.cc.capabilities, self.cc.directive_extra)
        self.addCleanup(lambda: setattr(self.cc, 'versions', saved[0]) or setattr(self.cc, 'capabilities', saved[1])
                        or setattr(self.cc, 'directive_extra', saved[2]))
        self.cc.versions = None  # the base stand-in then serves these capabilities
        self.cc.capabilities = {'schema_versions': ['1.0.0', '1.1.0', '1.17.0', '1.20.0'],
                                'features': {'engine_state': True}}
        self.cc.directive_extra = {'features': {'engine_state': True, 'krish_instruction': True}}
        summary, code = self.make()
        self.assertEqual((code, summary['loud'], summary['error']), (0, [], None), summary)
        report = self.cc.reports['makeyourmindup:mixask:2026-W46']
        self.assertEqual(report['schema_version'], '1.20.0')
        self.assertTrue(report['priorities'] and report['next_steps'])
        self.assertNotIn('instruction_acks', report, 'the maker acks nothing')
        directives = [c for c in self.cc.calls if c['method'] == 'GET' and c['path'].endswith('/directive')]
        self.assertEqual(len(directives), 1, 'the directive is read once a run')

    def test_his_no_on_the_standing_plan_means_no_ask(self):
        self.cc.decisions.append({'proposal_id': 'makeyourmindup:plan:w45-w52', 'decision': 'declined',
                                  'decided_at': DECIDED, 'payload_sha256': 'a' * 64, 'stage': 'plan', 'amended': False})
        summary, code = self.make()
        self.assertEqual((code, summary['holds'], summary['drafted_from']), (1, {'mix_plan_not_reported': 1}, {}),
                         'with no plan at all the week holds loudly, as before')
        self.assertEqual((self.asks(), self.words.calls), ([], []))

    # Which day, which channels -------------------------------------------------------------------

    def test_by_hand_only_today_or_tomorrow_is_made(self):
        self.approved()
        summary, _ = self.make(now='2026-11-08T04:30:00Z')  # Saturday 23:30: makes Sunday, nothing of the concept
        self.assertEqual((summary['days'], summary.get('slots', {}).get('made')), (['2026-11-08'], None), summary)
        self.assertEqual(self.creates(), [])
        self.assertEqual(self.make(day='2026-11-12')[0]['error'], 'day_out_of_range', 'by hand: today or tomorrow only')
        summary, code = self.make(now='2026-11-10T11:00:00Z', day='2026-11-10')  # Tuesday 06:00, by hand
        self.assertEqual((code, summary['days'], summary['slots'].get('made')), (0, ['2026-11-10'], 4), summary)

    def test_a_late_run_makes_the_rest_of_today_as_well_as_tomorrow(self):
        # Review finding 4: the remaining slots of today (New York) plus all of tomorrow's, so a late scheduled
        # run never skips a day; what an earlier run made is already_made.
        self.assertEqual(maker.make_days(maker.instant('2026-11-09T04:30:00Z')), [maker.dt.date(2026, 11, 9)],
                         'Sunday 23:30 in winter: nothing of Sunday can still be released')
        self.assertEqual(maker.make_days(maker.instant('2026-07-15T04:30:00Z')),
                         [maker.dt.date(2026, 7, 15), maker.dt.date(2026, 7, 16)], '00:30 in summer: today and tomorrow')
        self.approved()
        summary, code = self.make(now='2026-11-09T11:00:00Z')  # Monday 06:00 New York, a late run
        self.assertEqual((code, summary['days'], summary['slots'].get('made')),
                         (0, ['2026-11-09', '2026-11-10'], 4), summary)
        summary, code = self.make(now='2026-11-09T11:05:00Z')
        self.assertEqual((code, outcomes(summary), len(self.creates())), (0, {'already_made': 4}, 4), summary)

    def test_the_draft_save_refuses_linkedin_and_any_channel_not_pinned(self):
        buffer = self.buffer()
        linkedin = next(cid for cid, ch in buffer_channels.HANDED_OFF_CHANNELS.items() if ch == 'linkedin')
        for channel, channel_id in (('linkedin', linkedin), ('x', linkedin), ('threads', BUFFER_CHANNEL_ID['threads']),
                                    ('x', BUFFER_CHANNEL_ID['instagram'])):
            with self.assertRaises(BufferError) as caught:
                buffer.create_draft(channel, channel_id, 'Synthetic words.', [])
            self.assertEqual(caught.exception.code, 'draft_channel_refused')
        with self.assertRaises(BufferError):
            buffer.create_draft('x', BUFFER_CHANNEL_ID['x'], 'Synthetic words.', [{'image': {'url': 'http://example.org/a'}}])
        self.assertEqual(self.buf.calls, [])
        text = (ROOT / 'engine' / 'run' / 'buffer_drafts.py').read_text(encoding='utf-8')
        for word in ('shareNow', 'shareNext', 'deletePost', 'customScheduled', "'dueAt'", 'editPost'):
            self.assertNotIn(word, text)
        self.assertEqual(re.findall(r'mutation (\w+)', buffer_drafts.CREATE_MUTATION), ['CreateDraft'])

    def test_placements_take_only_the_files_their_format_takes(self):
        mocks = [('a' * 64, 'png'), ('b' * 64, 'png'), ('c' * 64, 'mp4')]
        self.assertEqual(maker.placement_files(mocks, 'carousel', 'instagram'), mocks[:2])
        self.assertEqual(maker.placement_files(mocks, 'short-video', 'youtube'), mocks[2:])
        self.assertEqual(maker.placement_files(mocks, 'single-image', 'x'), mocks[:1])
        self.assertEqual(maker.placement_files(mocks, 'meme', 'youtube'), mocks[2:])
        self.assertEqual(maker.placement_files(mocks, 'meme', 'instagram'), mocks[:1])
        self.assertEqual(maker.placement_files(mocks, 'text', 'x'), [])
        with self.assertRaises(maker.Held):
            maker.placement_files(mocks[:1], 'carousel', 'tiktok')


    # His words on the option (Ruling, Krish, 2026-11-02) --------------------------------------------

    def noted(self, note):
        """The plan approved per option on the board, every option carrying his words."""
        self.propose()
        for row in self.board.approve(self.plan):
            row['note'] = note
        return self.board.approved

    def test_his_direction_and_quotes_reach_the_share_declaration_and_never_change_the_caption(self):
        self.noted('Make it drier. Caption:\n"WHEN YOUR AI MEETS\nYOUR CUSTOMER\'S AI"')
        summary, code = self.make()
        self.assertEqual(code, 0, summary)
        briefs = [c['user'] for c in self.words.calls if c['schema'] is maker.SHARE_SCHEMA]
        self.assertTrue(briefs)
        for brief in briefs:
            self.assertIn("Editor's direction (context only, never quote it): Make it drier. Caption", brief)
            self.assertIn('Already on the picture or video, exactly: ' + json.dumps("WHEN YOUR AI MEETS\nYOUR CUSTOMER'S AI"), brief)
        # The words are content-engine's caption; the maker adds only the subscribe route.
        for post in self.buf.posts.values():
            self.assertEqual(post['text'].split('\nSubscribe: ')[0], WORDS)

    def test_a_quote_that_reads_as_what_not_to_say_holds_for_him(self):
        self.noted('don\'t say "game changer"')
        summary, code = self.make()
        self.assertEqual(self.creates(), [])
        self.assertEqual((summary['holds'], summary['loud'], code), ({'note_needs_krish': 4}, ['note_needs_krish'], 1), summary)

    def test_without_his_words_the_brief_is_unchanged(self):
        self.noted(None)
        summary, code = self.make()
        self.assertEqual(code, 0, summary)
        for c in self.words.calls:
            if c['schema'] is maker.SHARE_SCHEMA:
                self.assertNotIn("Editor's direction", c['user'])
                self.assertNotIn('Already on the picture', c['user'])


class AnthropicClientTests(unittest.TestCase):
    """The stdlib client against a local stand-in: its headers, its body, codes and never the key."""

    def setUp(self):
        seen = self.seen = []
        self.reply = {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '{"words": "Synthetic."}'}]}
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                seen.append({'headers': {k.lower(): v for k, v in self.headers.items()}, 'body': body})
                status, reply = (401, {}) if self.headers.get('x-api-key') != 'synthetic-key' else (200, test.reply)
                data = json.dumps(reply).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1]) + '/v1/messages'

    def test_one_json_answer_on_the_named_model_with_a_schema(self):
        client = anthropic_api.Anthropic('synthetic-key', self.url, 5, loopback_for_tests=True)
        got = client.json_message('Synthetic system.', 'Synthetic user.', {'type': 'object'})
        self.assertEqual(got, {'words': 'Synthetic.'})
        sent = self.seen[0]
        self.assertEqual((sent['body']['model'], sent['headers'].get('anthropic-version')),
                         ('claude-sonnet-5-5', anthropic_api.VERSION))
        self.assertEqual(sent['body']['output_config']['format'], {'type': 'json_schema', 'schema': {'type': 'object'}})
        self.assertNotIn('temperature', sent['body'])
        self.reply = {'stop_reason': 'refusal', 'content': []}
        with self.assertRaises(anthropic_api.AnthropicError) as caught:
            client.json_message('s', 'u', {'type': 'object'})
        self.assertEqual(caught.exception.code, 'anthropic_refused')

    def test_usage_is_counted_for_the_meter_and_posted_once_as_tokens(self):
        # ai-cost-4 (audit, 14 Nov 2026): the maker's paid calls reach Control Center's meter, tokens only.
        client = anthropic_api.Anthropic('synthetic-key', self.url, 5, loopback_for_tests=True)
        self.assertIsNone(anthropic_api.meter_body(client, 'makeyourmindup-maker-gh1.1', 'maker'))
        self.reply = dict(self.reply, usage={'input_tokens': 1200, 'output_tokens': 300,
                                             'cache_read_input_tokens': 50, 'cache_creation_input_tokens': 7})
        client.json_message('s', 'u', {'type': 'object'})
        self.reply = {'stop_reason': 'refusal', 'content': [], 'usage': {'input_tokens': 10, 'output_tokens': 1}}
        with self.assertRaises(anthropic_api.AnthropicError):
            client.json_message('s', 'u', {'type': 'object'})  # billed, so counted
        body = anthropic_api.meter_body(client, 'makeyourmindup-maker-gh1.1', 'maker')
        self.assertEqual(body, {'source': 'growth-makeyourmindup', 'run_id': 'makeyourmindup-maker-gh1.1',
                                'job': 'maker', 'calls': [{'model': 'claude-sonnet-5-5', 'calls': 2,
                                                           'input_tokens': 1210, 'output_tokens': 301,
                                                           'cache_read_tokens': 50, 'cache_write_tokens': 7}]})

        class CC:
            posted = []

            def post_meter_usage(self, body):
                self.posted.append(body)
                return {'ok': True}

        cc = CC()
        self.assertEqual(maker.post_meter(cc, client, {'GITHUB_RUN_ID': '42', 'GITHUB_RUN_ATTEMPT': '2'}), 'recorded')
        self.assertEqual(cc.posted[0]['run_id'], 'makeyourmindup-maker-gh42.2')

        class Refusing:
            def post_meter_usage(self, body):
                raise ProtocolError('not_found', 404)

        self.assertEqual(maker.post_meter(Refusing(), client, {}), 'meter_not_found')
        self.assertEqual(maker.post_meter(cc, anthropic_api.Anthropic('synthetic-key', self.url, 5,
                                                                      loopback_for_tests=True), {}), 'no_calls')
        summary = {'meter': 'recorded', 'model_usage': body['calls'][0]}
        lines = '\n'.join(maker.step_summary(summary))
        self.assertIn('- Model calls: 2 on claude-sonnet-5-5, 1210 tokens in and 301 out; meter recorded.', lines)

    def test_a_refused_key_is_its_own_error_and_never_echoed(self):
        client = anthropic_api.Anthropic('another-synthetic-key', self.url, 5, loopback_for_tests=True)
        with self.assertRaises(anthropic_api.AnthropicAuthError) as caught:
            client.json_message('s', 'u', {'type': 'object'})
        self.assertNotIn('another-synthetic-key', str(caught.exception) + repr(client))
        with self.assertRaises(anthropic_api.AnthropicError):
            anthropic_api.Anthropic('synthetic-key', 'https://elsewhere.invalid/v1/messages')


class AnthropicRetryTests(unittest.TestCase):
    """Review finding 5: 429 and 5xx (529 included) are retried, retry-after honoured, then given up loudly."""

    def setUp(self):
        self.script, self.seen = [], []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length', 0)))
                status, headers = test.script.pop(0) if test.script else (200, {})
                test.seen.append(status)
                reply = ({'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '{"ok": true}'}]}
                         if status == 200 else {'type': 'error'})
                data = json.dumps(reply).encode('utf-8')
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1]) + '/v1/messages'
        self.slept, self.now = [], [0.0]

    def client(self):
        def sleep(seconds):
            self.slept.append(seconds)
            self.now[0] += seconds
        return anthropic_api.Anthropic('synthetic-key', self.url, 5, loopback_for_tests=True, sleep=sleep,
                                       clock=lambda: self.now[0])

    def test_overloaded_and_rate_limited_are_retried_honouring_retry_after(self):
        self.script = [(529, {'retry-after': '7'}), (429, {}), (200, {})]
        self.assertEqual(self.client().json_message('s', 'u', {'type': 'object'}), {'ok': True})
        self.assertEqual((self.seen, self.slept), ([529, 429, 200], [7, anthropic_api.BACKOFF[1]]))

    def test_after_three_tries_it_gives_up_with_a_code_the_maker_fails_loudly_on(self):
        self.script = [(500, {}), (503, {}), (529, {})]
        with self.assertRaises(anthropic_api.AnthropicError) as caught:
            self.client().json_message('s', 'u', {'type': 'object'})
        self.assertEqual((caught.exception.code, len(self.seen)), ('anthropic_overloaded', 3))
        self.assertIn(caught.exception.code, anthropic_api.GAVE_UP)
        self.assertLess(sum(self.slept), 90)

    def test_a_retry_after_past_the_wait_budget_is_not_waited_for(self):
        self.script = [(429, {'retry-after': '120'})]
        with self.assertRaises(anthropic_api.AnthropicError) as caught:
            self.client().json_message('s', 'u', {'type': 'object'})
        self.assertEqual((caught.exception.code, self.seen, self.slept), ('anthropic_rate_limited', [429], []))

    def test_no_call_reaches_past_the_run_deadline(self):
        client = self.client()
        client.set_deadline(100.0)
        self.now[0] = 95.0
        with self.assertRaises(anthropic_api.AnthropicError) as caught:
            client.json_message('s', 'u', {'type': 'object'})
        self.assertEqual((caught.exception.code, self.seen), ('anthropic_out_of_time', []))
        self.now[0], self.script = 60.0, [(529, {'retry-after': '35'})]
        with self.assertRaises(anthropic_api.AnthropicError) as caught:
            client.json_message('s', 'u', {'type': 'object'})
        self.assertEqual((caught.exception.code, self.slept), ('anthropic_overloaded', []), 'no wait past it')


class MakerWorkflowTests(unittest.TestCase):
    def test_the_workflow_runs_daily_with_deliver_and_by_hand_as_a_dry_run(self):
        text = (ROOT / '.github' / 'workflows' / 'maker.yml').read_text(encoding='utf-8')
        # GROWTH_WRITEBACK_TOKEN reads the board's mix press only (Ruling, Krish, 2026-10-30); the maker never
        # writes to the board.
        self.assertEqual(set(re.findall(r'secrets\.([A-Z_]+)', text)),
                         {'CONTROL_CENTER_ENGINE_TOKEN', 'BUFFER_API_KEY', 'ANTHROPIC_API_KEY', 'GROWTH_WRITEBACK_TOKEN'})
        self.assertNotIn('.posted(', (ROOT / 'engine' / 'run' / 'maker.py').read_text(encoding='utf-8'))
        for needle in ("cron: '33 4 * * *'", 'types: [growth-mymu-maker]', 'workflow_dispatch', 'contents: read', 'group: maker',
                       'cancel-in-progress: false', 'timeout-minutes:', "python-version: '3.12'",
                       'persist-credentials: false', 'set -- run maker', 'set -- "$@" --deliver', 'python growth.py "$@"',
                       "MAKER_DELIVER: ${{ github.event_name == 'schedule' || github.event_name == 'repository_dispatch' || "
                       "inputs.trigger == 'control-center-clock' || inputs.deliver }}", 'default: false'):
            self.assertIn(needle, text)
        for banned in ('upload-artifact', 'GITHUB_TOKEN', 'contents: write', 'set -x', 'client_payload'):
            self.assertNotIn(banned, text)
        lanes = json.loads((ROOT / 'lanes.json').read_text(encoding='utf-8'))
        job = next(j for j in lanes['jobs'] if j['id'] == 'maker')
        self.assertEqual((job['lane'], job['workflow']), ('L0_code', 'maker.yml'))
        self.assertIn('ANTHROPIC_API_KEY', job['secrets'])
        self.assertIn('docs/MAKER.md', (ROOT / 'docs' / 'LANES.md').read_text(encoding='utf-8'))


    def test_the_maker_doc_says_what_it_trusts(self):
        # Review finding 7.
        text = (ROOT / 'docs' / 'MAKER.md').read_text(encoding='utf-8')
        self.assertIn('## What it trusts', text)
        section = ' '.join(text.split('## What it trusts', 1)[1].split('\n## ', 1)[0].split())
        for needle in ('the idea, the channel and the week', 'planning, not approval', 'repository dispatch', 'write access',
                       'hash', 'release', "Krish's own Drive"):
            self.assertIn(needle, section)
        self.assertNotIn('\u2014', text, 'no em dashes')
        self.assertIn('first live run', text)

    def test_the_maker_doc_says_what_it_does_with_no_approved_mix(self):
        # Ruling (Krish, 2026-11-12): with no approved weekly mix, draft from the standing plan and ask once a week.
        text = (ROOT / 'docs' / 'MAKER.md').read_text(encoding='utf-8')
        self.assertIn('## With no approved mix', text)
        section = ' '.join(text.split('## With no approved mix', 1)[1].split('\n## ', 1)[0].split())
        for needle in ('Ruling (Krish, 2026-11-12)', 'specs/standing-plan.json', 'never saved in Buffer',
                       'never handed off', 'makeyourmindup:standing:<day>', 'makeyourmindup:mixask:<ISO week>',
                       "This week's mix isn't approved", 'every other run that week says nothing', 'skipped_weeks',
                       'the next run makes his plan', 'no_approved_edition'):
            self.assertIn(needle, section)
        self.assertIn('draft-from-standing-plan', json.dumps(json.loads((ROOT / 'lanes.json').read_text(encoding='utf-8'))))


if __name__ == '__main__':
    unittest.main()
