"""Lane L0, the maker: tomorrow's Buffer drafts from the ideas and mocks Krish approved, handed off for release.

`growth.py run maker [--deliver]` runs in GitHub Actions (.github/workflows/maker.yml) at
04:30 UTC, just before or after New York midnight. Without --deliver it is a dry run: it
reads Control Center and Buffer, writes and reviews the words, and creates no draft and
writes nothing to Control Center.

For the next New York day (tomorrow, or today when its midnight passed under two hours
ago; by hand, --day names today or tomorrow in New York and nothing else), in order:

1. His authority, read back from Control Center by digest, never a file:
   engine/run/autorelease.py week_state (decision.cc_readback and concept_part, the same
   rules release applies). A no on the week makes nothing; a hold makes nothing.
2. The week's slots, from the slots record the handoff wrote beside the plan
   (cc_records.SLOTS, keyed by the plan's part digests). They are checked twice before
   use: rebuilt with the handoff's own validate_mix_plan against the concepts each part
   carries (so every concept's channels are exactly its slots), and the plan lines of
   part 1, the words he approved, must be the lines these slots make (mix._sections).
   Anything else holds loudly as slots_differ_from_plan.
3. For each slot due that day on Instagram, YouTube, TikTok or X (never LinkedIn) whose
   concept is approved and not stopped: one draft per concept, channel and week. A
   concept already in the week's derived index, or a post on that channel in Buffer
   that carries its claim, is already_made.
4. The mock files, by the week's mock manifest (cc_records.MOCKS, sha256 to Drive file
   id): each file downloaded from its Drive download link and hashed; a file not in the
   manifest holds as mock_file_missing, one whose bytes differ as mock_hash_mismatch.
   A placement takes the files its format takes (release.format_shape): every picture
   for a carousel, the video for YouTube, the first picture (the cover) for one image,
   none for text. Buffer gets the same Drive link, so release rebuilds the post from
   exactly those bytes.
5. The words, from the Anthropic API (ANTHROPIC_API_KEY, model claude-sonnet-5-5), from
   the concept's idea and claim only, in the account's voice (docs/ACCOUNT-VOICE.md). They
   must carry the claim word for word (concepts.carries), pass content-engine's copy lint
   (release.copy_errors) and the share rule (release.share_ask_errors), and declare a share
   block (share.share_errors). One rewrite with the reasons, then it holds.
6. The review: a separate Anthropic call that sees only the post's format, its words and
   its files' blind names, under the blind send-test lens (social/share.json). Its answer
   is compared with the declared share block (share.compare_send_test) and judged again,
   at the draft's own payload_sha256, by spec.review_reason, the one judge release uses.
   It is maker-attested, not an independent judge (docs/CONCEPT-MANIFEST.md).
7. With --deliver: the draft is saved in Buffer with saveToDraft true and no due time
   (buffer_drafts.DraftBuffer.create_draft), read back, rebuilt with
   autorelease.draft_line, and handed off in-process through engine/run/handoff.py
   (growth-go-live-manifest, each slot with its concept_id and review), which records the
   review and the day's index that release reads. Nothing here schedules, publishes or
   deletes; release.yml schedules each post, later, only while every gate still passes.

Without ANTHROPIC_API_KEY it holds loudly (anthropic_key_missing) and reads nothing.
Output is one JSON line of counts and reason codes: never words, URLs, ids or keys.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from engine import concepts as concept_rules, mix as mix_rules
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.cc_loop import decisions_paged
from engine.control_center import SLUG, ProtocolError
from engine.core import instant, ny_time
from engine.run import autorelease, buffer_api, cc_records, handoff, release
from engine.run.anthropic_api import KEY_ENV, Anthropic, AnthropicAuthError, AnthropicError
from engine.run.buffer_api import BufferAuthError, BufferError, CarryHold
from engine.run.buffer_drafts import DraftBuffer
from engine.run.spec import ny_midnight, review_reason
from engine.share import JOBS, StaleSendTest, compare_send_test, share_errors, slot_send_test_request
from engine.social import inventory

ROOT = Path(__file__).resolve().parents[2]
DRIVE_URL = 'https://drive.usercontent.google.com/download?id={}&export=download'
LEAD_BACK = dt.timedelta(hours=2)  # the 04:30 UTC run lands just before or just after New York midnight
MIN_LEAD = dt.timedelta(minutes=60)  # a slot due sooner is not made: release needs time to read it
MAX_WRITES = 2  # the first words, then one rewrite with the reasons
WORDS_MAX = {'x': 270, 'instagram': 600, 'tiktok': 600, 'youtube': 600}
TITLE_MAX = 90
YOUTUBE_CATEGORY = '28'  # Science and Technology
NAMES = {'x': 'X', 'instagram': 'Instagram', 'tiktok': 'TikTok', 'youtube': 'YouTube Shorts'}
LIVE = ['scheduled', 'sending', 'sent']
STATE_DIR = Path('.scratch') / 'cc'

WRITER_SYSTEM = '\n'.join([
    'You write the words of one social post for makeyourmindup, a publication that takes one AI story apart'
    ' three times a week: who gets paid, what is real and where it leads.',
    'The post carries an idea and a claim the editor approved. The claim is fixed: put it in the words exactly as'
    ' given, character for character, as one whole sentence. Never change, split, shorten or reword it.',
    'Write only from the idea and the claim. Add no fact, number, name, quote, result or source that is not in'
    ' them. If you are unsure, leave it out.',
    'Plain English a busy senior leader reads in five seconds. Human and humble: no hype, no lecture, no showing'
    ' off, no launch language.',
    'Never name the person behind the accounts, his handle or his initials. No em dashes. No hashtags, no emojis,'
    ' no links, no @ mentions.',
    'Never ask the reader to share, send, forward, tag, repost, like, comment or follow.',
    'Then declare the share: the one specific person who would send this post to one other specific person.'
    ' sender and receiver each name one person by role and relationship (for example: a head of operations at a'
    ' mid-size insurer; her CFO, who signs off the pilot budget), never a crowd. job is the one job sending it'
    ' does for the sender. dm_line is the short message the sender would type with it, in their own words.'
    ' moment is the everyday situation that brings the post to mind.',
    'title: for YouTube, a plain title of at most 90 characters that carries the idea, with no clickbait;'
    ' for every other channel, an empty string.',
    'Answer only with the JSON the schema asks for.'])
VOICE = {'personal': 'a personal account. Write as a person quietly pleased to share something useful: sincere,'
                     ' warm and humble. First person is fine; never invent a feeling, an experience or a result.',
         'publication': "the publication's account. Speak as makeyourmindup, as we where needed: clear, useful and"
                        ' visually specific, dryly funny only where it is earned.'}
WRITE_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['words', 'title', 'share'],
    'properties': {
        'words': {'type': 'string'}, 'title': {'type': 'string'},
        'share': {'type': 'object', 'additionalProperties': False,
                  'required': ['sender', 'receiver', 'job', 'dm_line', 'moment'],
                  'properties': {'sender': {'type': 'string'}, 'receiver': {'type': 'string'},
                                 'job': {'type': 'string', 'enum': list(JOBS)}, 'dm_line': {'type': 'string'},
                                 'moment': {'type': 'string'}}}}}
NULLABLE = lambda schema: {'anyOf': [schema, {'type': 'null'}]}
REVIEW_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['would_send', 'receiver', 'job', 'dm_line', 'why'],
    'properties': {'would_send': {'type': 'boolean'}, 'receiver': NULLABLE({'type': 'string'}),
                   'job': NULLABLE({'type': 'string', 'enum': list(JOBS)}), 'dm_line': NULLABLE({'type': 'string'}),
                   'why': {'type': 'string'}}}


class Held(Exception):
    """One slot holds, with a code; loud ones fail the run so GitHub emails Krish."""

    def __init__(self, code, loud=False):
        self.code, self.loud = code, loud
        super().__init__(code)


class Tally:
    def __init__(self):
        self.counts, self.holds, self.loud = {}, {}, []

    def count(self, outcome, n=1):
        self.counts[outcome] = self.counts.get(outcome, 0) + n

    def hold(self, code, loud=False, n=1):
        self.count('held', n)
        self.holds[code] = self.holds.get(code, 0) + n
        if loud:
            self.loud.append(code)


def drive_url(file_id):
    return DRIVE_URL.format(file_id)


def target_day(now):
    """The New York day the run makes: tomorrow, or today when its midnight passed under LEAD_BACK ago."""
    return ny_time(instant(now) - LEAD_BACK).date() + dt.timedelta(days=1)


# The week's plan, slots and mock manifest, read back from Control Center ------------------------

def read_plan(cc, monday):
    """(parts, [(proposal, part record)]) of the plan in force, read by digest, or Held."""
    label = autorelease._week_label(monday)
    versions = cc_records.probe(cc, lambda n: cc_records.version_run_id(label, n), cc_records.VERSION,
                                autorelease.MAX_NUMBERED)
    if not versions:
        raise Held('mix_plan_not_reported' if versions == [] else 'mix_versions_unbounded', loud=True)
    parts = versions[-1].get('parts')
    if not isinstance(parts, list) or not parts:
        raise Held('mix_version_malformed', loud=True)
    read = []
    for part in parts:
        item, record = autorelease.read_part(cc, part.get('proposal_id'), part.get('payload_sha256'))
        if item is None or not isinstance(record, dict) or not isinstance(item.get('exact_payload'), str):
            raise Held('mix_part_missing', loud=True)
        read.append((item, record))
    return parts, read


def week_slots(cc, monday, parts, read, cfg, root):
    """The week's slots as the plan he approved lays them out, or Held (loud).

    The record is rebuilt into the plan file's own shape and put through the handoff's
    validate_mix_plan with the concepts each part carries, then part 1's plan lines must be
    the lines these slots make: the slots record never adds a slot the words he read do not."""
    label, key = autorelease._week_label(monday), cc_records.plan_key(parts)
    try:
        chunks = cc_records.read_chunked(cc, lambda n: cc_records.slots_run_id(label, key, n), cc_records.SLOTS)
    except ValueError:
        raise Held('slots_record_unreadable', loud=True) from None
    if chunks is None:
        raise Held('slots_record_missing', loud=True)
    first = chunks[0]
    terms = ('week_of', 'plan', 'weights', 'moved', 'shortfalls')
    if any(c.get(t) != first.get(t) for c in chunks for t in terms) or first.get('plan') != parts \
            or first.get('week_of') != monday or type(first.get('shortfalls')) is not int \
            or not all(isinstance(c.get('slots'), list) for c in chunks):
        raise Held('slots_record_unreadable', loud=True)
    filler = {'channel': 'none', 'day': 'none', 'lane': 'none', 'needs': 'none'}
    payload = {'week_of': monday, 'targets': read[0][1].get('targets'), 'weights': first['weights'],
               'moved': first['moved'], 'slots': [s for c in chunks for s in c['slots']],
               'concepts': [c for _, record in read for c in record.get('concepts') or []],
               'shortfalls': [dict(filler) for _ in range(first['shortfalls'])]}
    try:
        mix, _, _ = handoff.validate_mix_plan(payload, root)
    except handoff.PayloadRejected:
        raise Held('slots_differ_from_plan', loud=True) from None
    head, _, tail = mix_rules._sections(mix, cfg)
    words = read[0][0]['exact_payload']
    if not words.startswith('\n'.join(head) + '\n') or not words.endswith('\n' + '\n'.join(tail)):
        raise Held('slots_differ_from_plan', loud=True)
    return mix['slots']


def mock_manifest(cc, monday, parts):
    """{sha256: Drive file id} for the week, or None when none is reported. Held (loud) when unreadable."""
    label, key = autorelease._week_label(monday), cc_records.plan_key(parts)
    try:
        chunks = cc_records.read_chunked(cc, lambda n: cc_records.mocks_run_id(label, key, n), cc_records.MOCKS)
    except ValueError:
        raise Held('mock_manifest_unreadable', loud=True) from None
    if chunks is None:
        return None
    files = {}
    for chunk in chunks:
        got = chunk.get('files')
        if chunk.get('plan') != parts or not isinstance(got, dict) or not all(
                isinstance(k, str) and release.HEX64.match(k) and isinstance(v, str) and handoff.DRIVE_ID.match(v)
                for k, v in got.items()):
            raise Held('mock_manifest_unreadable', loud=True)
        files.update(got)
    return files


# One placement's files ---------------------------------------------------------------------

def placement_files(mocks, fmt, channel):
    """The (sha256, extension) files a placement carries, from its concept's mocks in order, or Held.

    The format's shape decides (release.format_shape): its kinds and how many. YouTube takes video,
    never a still; elsewhere, when a concept has both, a post takes its pictures. Past the format's
    most, the first files are taken (the cover first): one image is the cover of the carousel."""
    shape = release.format_shape(fmt)
    if shape is None:
        raise Held('format_shape_unknown')
    if shape['max'] == 0:
        return []
    kinds = [(sha, ext, release.MEDIA.get('.' + ext)) for sha, ext in mocks]
    picked = [(sha, ext, kind) for sha, ext, kind in kinds if kind in shape['kinds']]
    if channel == 'youtube':
        picked = [p for p in picked if p[2] == 'video']
    elif {'image', 'video'} <= {p[2] for p in picked}:
        picked = [p for p in picked if p[2] == 'image']
    if shape['max'] is not None:
        picked = picked[:shape['max']]
    if not picked or len(picked) < (shape['min'] or 0):
        raise Held('mock_files_do_not_fit_format')
    return [(sha, ext) for sha, ext, _ in picked]


# The words and their review ------------------------------------------------------------------

def write_words(anthropic, slot, concept, voice, files):
    """(words, title, share) that carry the claim and pass every check, or Held. One rewrite with the reasons."""
    channel, fmt = slot['channel'], slot['format']
    media = ('text only, no picture' if not files else
             str(len(files)) + (' pictures' if len(files) > 1 else ' picture' if release.MEDIA.get(
                 '.' + files[0][1]) == 'image' else ' video'))
    brief = ('Channel: ' + NAMES[channel] + ', ' + VOICE[voice] + '\nFormat: ' + fmt + ', ' + media
             + '.\nAt most ' + str(WORDS_MAX[channel]) + ' characters of words, the claim included.'
             + '\nIdea: ' + concept['idea'] + '\nClaim: ' + concept['claim'])
    reasons, code = [], None
    for _ in range(MAX_WRITES):
        user = brief + ('\nYour last draft was held. Write it again so none of these applies: ' + '; '.join(reasons)
                        if reasons else '')
        got = anthropic.json_message(WRITER_SYSTEM, user, WRITE_SCHEMA)
        words, title, share = got.get('words'), got.get('title'), got.get('share')
        code, reasons = None, []
        if not isinstance(words, str) or not words.strip() or not isinstance(title, str) \
                or not isinstance(share, dict):
            code, reasons = 'words_unreadable', ['answer with words, a title and a share block']
            continue
        words = words.strip()
        share = dict({k: share.get(k) for k in ('sender', 'receiver', 'job', 'dm_line', 'moment')}, standalone=True)
        checks = [
            ('words_missing_claim', [] if concept_rules.carries(concept['claim'], words)
             else ['the claim is not in the words exactly as given']),
            ('words_too_long', [] if len(words) <= WORDS_MAX[channel]
             else ['the words are longer than ' + str(WORDS_MAX[channel]) + ' characters']),
            ('copy_lint_refused', release.copy_errors(words)),
            ('share_ask_refused', release.share_ask_errors({'format': fmt}, words)),
            ('share_block_refused', share_errors(share, True)),
            ('title_refused', ([] if channel != 'youtube' else
                               ['a YouTube post needs a plain title'] if not title.strip() or len(title) > TITLE_MAX
                               else release.copy_errors(title, 'titles')))]
        for name, found in checks:
            if found and code is None:
                code = name
            reasons += found
        if code is None:
            return words, title.strip(), share
    raise Held(code)


def review_words(anthropic, slot, words, share, assets):
    """The blind reader's answer to the post's exact words, compared with its share block, or Held."""
    request = slot_send_test_request({'format': slot['format'], 'words': words, 'assets': assets})
    user = ('The post, as JSON. Its pictures or video are not shown; judge it from its format, its file names and'
            ' its words.\n' + json.dumps(request['post'], ensure_ascii=False, sort_keys=True))
    answer = anthropic.json_message(request['prompt'], user, REVIEW_SCHEMA)
    answer = {k: answer.get(k) for k in ('would_send', 'receiver', 'job', 'dm_line', 'why')}
    answer['request_sha256'] = request['request_sha256']  # the request this call was given, and no other
    try:
        result = compare_send_test(share, answer, request)
    except (StaleSendTest, ValueError, KeyError, TypeError):
        raise Held('review_unreadable') from None
    if result['verdict'] != 'pass':
        raise Held('review_not_passed')
    return answer


# Buffer --------------------------------------------------------------------------------------

def draft_metadata(channel, files, title):
    video = any(release.MEDIA.get('.' + ext) == 'video' for _, ext in files)
    if channel == 'instagram':
        return {'instagram': {'type': 'reel' if video else 'post', 'shouldShareToFeed': True}}
    if channel == 'youtube':
        return {'youtube': {'title': title, 'categoryId': YOUTUBE_CATEGORY, 'privacy': 'public',
                            'madeForKids': False}}
    return None


class Maker:
    def __init__(self, cc, buffer, anthropic, now, deliver, fetch, root):
        self.cc, self.buffer, self.anthropic = cc, buffer, anthropic
        self.now, self.deliver, self.fetch, self.root = now, deliver, fetch, root
        self.tally = Tally()
        self.organizations, self.listed, self.downloads = [], {}, {}

    def in_buffer(self, channel, claim, since):
        """True when a post on this engine's channel already carries the claim: any draft, or a post scheduled
        or gone out since the week began (since), so the read never grows with the channel's history."""
        if channel not in self.listed:
            pinned, posts = BUFFER_CHANNEL_ID[channel], []
            for organization in self.organizations:
                posts += self.buffer.list_posts(organization, ['draft'], [pinned])
                posts += self.buffer.list_posts(organization, LIVE, [pinned], since)
            self.listed[channel] = [p for p in posts if isinstance(p, dict) and p.get('channelId') == pinned]
        return any(concept_rules.carries(claim, p.get('text') or '') for p in self.listed[channel])

    def mocks_of(self, concept, manifest):
        """[(sha256, extension)] of every mock file of the concept, downloaded and hashed now, or Held."""
        if concept['mock_sha256'] and manifest is None:
            raise Held('mock_manifest_missing', loud=True)
        out = []
        for sha in concept['mock_sha256']:
            if sha not in manifest:
                raise Held('mock_file_missing')
            if sha not in self.downloads:
                try:
                    self.downloads[sha] = self.fetch(drive_url(manifest[sha]))
                except BufferError:
                    raise Held('mock_download_failed') from None
            digest, _, ext = self.downloads[sha]
            if digest != sha:
                raise Held('mock_hash_mismatch')
            if release.MEDIA.get('.' + str(ext)) not in ('image', 'video'):
                raise Held('mock_kind_unknown')
            out.append((sha, ext))
        return out

    def make(self, slot, concept, voice, manifest):
        """The handoff slot for one made draft (or None in a dry run), or Held."""
        due = autorelease.due_instant(slot['due_at'])
        if due is None or due - self.now < MIN_LEAD:
            raise Held('due_too_soon')
        files = placement_files(self.mocks_of(concept, manifest), slot['format'], slot['channel'])
        assets = [{'name': 'mock-' + str(n) + '.' + ext, 'sha256': sha} for n, (sha, ext) in enumerate(files, 1)]
        words, title, share = write_words(self.anthropic, slot, concept, voice, files)
        answer = review_words(self.anthropic, slot, words, share, assets)
        if not self.deliver:
            return None
        channel = slot['channel']
        body = [{release.MEDIA['.' + ext]: {'url': drive_url(manifest[sha])}} for sha, ext in files]
        try:
            post = self.buffer.create_draft(channel, BUFFER_CHANNEL_ID[channel], words, body,
                                            draft_metadata(channel, files, title))
            post = self.buffer.get_post(post.get('id'))
        except BufferAuthError:
            raise
        except BufferError:
            raise Held('draft_not_saved', loud=True) from None
        self.tally.count('drafts_saved')
        if post.get('status') != 'draft' or post.get('dueAt') or post.get('channelId') != BUFFER_CHANNEL_ID[channel] \
                or post.get('text') != words or len(post.get('assets') or []) != len(files):
            raise Held('draft_readback_differs', loud=True)
        fields = {'slot_id': slot['slot_id'], 'format': slot['format'], 'due_at': slot['due_at'],
                  'link_placement': None, 'publish_mode': 'engine', 'buffer_draft_id': post['id']}
        try:
            line = autorelease.draft_line(post, fields, lambda url: self.fetch(url)[:2])
        except CarryHold as hold:
            raise Held(hold.code, loud=True) from None
        except BufferError:
            raise Held('draft_asset_unreadable', loud=True) from None
        if line['assets'] != [sha for sha, _ in files]:
            raise Held('draft_assets_differ_from_mock', loud=True)
        payload = autorelease.spec_digest(line)
        review = {'slot_id': slot['slot_id'], 'verdict': 'pass', 'lens': 'send-test', 'payload_sha256': payload,
                  'send_test': {'reader_answer': answer}}
        judged = {'slot_id': slot['slot_id'], 'format': slot['format'], 'words': line['words'], 'assets': assets,
                  'payload_sha256': payload, 'share': share}
        if review_reason(judged, review, snack=True):
            raise Held('review_failed_after_draft', loud=True)
        return {'slot': slot['slot_id'], 'channel': channel, 'buffer_draft_id': post['id'], 'payload_sha256': payload,
                'per_item_review': False, 'format': slot['format'], 'due_at': slot['due_at'], 'link_placement': None,
                'publish_mode': 'engine', 'concept_id': concept['concept_id'],
                'review': {'slot_id': slot['slot_id'], 'verdict': 'pass', 'lens': 'send-test',
                           'payload_sha256': payload, 'reader_answer': answer, 'share': share,
                           'asset_names': [a['name'] for a in assets]}}


def maker(cc, buffer, anthropic, now=None, deliver=False, fetch=None, root=None, out_path=None, day=None):
    """Returns (summary, exit_code). summary holds counts and codes only.

    day (YYYY-MM-DD) names the New York day to make by hand; only today or tomorrow there is accepted,
    so a yes given after the night's run can still be made that morning (day_out_of_range otherwise)."""
    now = instant(now)
    root = Path(root or ROOT)
    if day is None:
        day = target_day(now)
    else:
        try:
            day = dt.date.fromisoformat(day)
        except (TypeError, ValueError):
            day = None
        local = ny_time(now).date()
        if day not in (local, local + dt.timedelta(days=1)):
            summary = {'lane': 'L0', 'command': 'maker', 'deliver': bool(deliver), 'error': 'day_out_of_range',
                       'exit': 1}
            return summary, 1
    monday = (day - dt.timedelta(days=day.weekday())).isoformat()
    summary = {'lane': 'L0', 'command': 'maker', 'deliver': bool(deliver), 'day': day.isoformat(),
               'week': autorelease._week_label(monday), 'slots': {}, 'holds': {}, 'mutations': 0,
               'handoff': None, 'taste': 'taste_unavailable', 'loud': [], 'error': None}
    work = Maker(cc, buffer, anthropic, now, deliver, fetch or buffer_api.download_facts, root)
    tally = work.tally
    if anthropic is None:
        # No words without the key: nothing is read, nothing is made, and the run fails so GitHub emails him.
        tally.hold('anthropic_key_missing', loud=True)
        return _finish(summary, tally, buffer)
    folder = tempfile.TemporaryDirectory()
    made = []
    try:
        work.organizations = buffer.account_check().get('organization_ids') or []
        decisions = decisions_paged(cc, now - autorelease.LOOKBACK)
        if decisions is None:
            raise autorelease.Unpaged()
        proposals = autorelease.signed_golives(cc, decisions, {}, now)
        state = autorelease.week_state(cc, monday, decisions, folder.name, now, root, proposals)
        if state.get('stopped'):
            tally.count('week_stopped')
            return _finish(summary, tally, buffer)
        if state.get('hold'):
            tally.hold(state['why'] if state['hold'] == 'concept_hold' and state.get('why') else state['hold'],
                       loud=state.get('loud', False))
            return _finish(summary, tally, buffer)
        approved, stops = state['decision']['concepts'], set(state['decision']['stopped_concepts'] or [])
        known = {c['concept_id']: c for c in state['spec']['concepts']}
        cfg = mix_rules.load(root)
        voices = {c: (inventory(root)['channel'].get(c) or {}).get('account_context') for c in concept_rules.CONCEPT_CHANNELS}
        parts, read = read_plan(cc, monday)
        slots = [s for s in week_slots(cc, monday, parts, read, cfg, root)
                 if ny_time(s['due_at']).date() == day]
        manifest = mock_manifest(cc, monday, parts)
        week = autorelease.week_entries(cc, monday, tally.holds)
        if week is None:
            raise Held('derived_index_unreadable', loud=True)
        done = {(e['concept_id'], e['channel']) for e in week}
        since = ny_midnight(dt.date.fromisoformat(monday)).isoformat()
        for slot in sorted(slots, key=lambda s: (instant(s['due_at']), s['slot_id'])):
            channel, cid = slot['channel'], slot['concept_id']
            if channel not in concept_rules.CONCEPT_CHANNELS or channel in release.KRISH_CLICK_ONLY:
                tally.count('not_a_concept_channel')
                continue
            if cid is None:
                tally.count('empty_slot')
                continue
            try:
                if cid in stops:
                    raise Held(concept_rules.STOPPED)
                concept = known.get(cid)
                if concept is None or approved.get(cid) != concept.get('concept_sha256'):
                    raise Held('concept_not_approved')
                if {'channel': channel, 'format': slot['format']} not in concept['placements']:
                    raise Held(concept_rules.DEPARTS)
                if voices.get(channel) not in VOICE:
                    raise Held('account_voice_unknown')
                if (cid, channel) in done:
                    tally.count('already_made')
                    continue
                if work.in_buffer(channel, concept['claim'], since):
                    # A draft carrying its claim is in Buffer but not in the week's index: never made twice.
                    tally.count('already_made')
                    tally.loud.append('made_not_handed_off')
                    continue
                one = work.make(slot, concept, voices[channel], manifest)
                done.add((cid, channel))
                if one is None:
                    tally.count('would_make')
                else:
                    made.append(one)
                    tally.count('made')
            except Held as hold:
                tally.hold(hold.code, hold.loud)
            except AnthropicAuthError:
                raise
            except AnthropicError as error:
                tally.hold(error.code)
        if made:
            run_id = SLUG + ':' + autorelease._week_label(monday) + ':week'
            result, code = handoff.handoff(handoff.GO_LIVE, {'run_id': run_id, 'slots': made}, cc, buffer, now, True,
                                           lambda url: work.fetch(url)[:2], root, out_path)
            summary['handoff'] = {'recorded': result['slots'].get('derived_recorded', 0), 'holds': result['holds'],
                                  'error': result['error']}
            if code or result['slots'].get('derived_recorded', 0) != len(made):
                tally.loud.append('handoff_incomplete')  # a draft exists that release cannot read yet
    except Held as hold:
        tally.hold(hold.code, hold.loud)
    except AnthropicAuthError as error:
        summary['error'] = error.code
    except BufferAuthError as error:
        summary['error'] = error.code
    except BufferError as error:
        summary['error'] = error.code
    except ProtocolError as error:
        summary['error'] = 'control_center_' + error.code
    except autorelease.Unpaged:
        summary['error'] = 'decisions_unpaged'
    except ValueError as error:
        summary['error'] = str(error) if re.match(r'^[a-z_]{1,40}$', str(error)) else 'record_unreadable'
    finally:
        folder.cleanup()
    return _finish(summary, tally, buffer)


def _finish(summary, tally, buffer):
    summary['slots'] = dict(sorted(tally.counts.items()))
    summary['holds'] = dict(sorted(tally.holds.items()))
    summary['mutations'] = getattr(buffer, 'mutations', 0)
    summary['loud'] = sorted(set(tally.loud))
    code = 1 if summary['error'] or summary['loud'] else 0
    summary['exit'] = code
    return summary, code


def _buffer_client():
    return DraftBuffer(os.environ.get(autorelease.BUFFER_KEY_ENV, '').strip())


def _anthropic_client():
    key = os.environ.get(KEY_ENV, '').strip()
    return Anthropic(key) if key else None


def main(argv=None, make_cc=None, make_buffer=None, make_anthropic=None, fetch=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['maker']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run maker', description=__doc__.split('\n')[0])
    parser.add_argument('--deliver', action='store_true',
                        help='save the drafts in Buffer and hand them off; without it, a dry run')
    parser.add_argument('--now', help='a fixed clock, for tests')
    parser.add_argument('--day', help='by hand: the New York day to make, today or tomorrow only (default: the next'
                        ' New York day)')
    args = parser.parse_args(argv)
    summary = {'lane': 'L0', 'command': 'maker', 'deliver': args.deliver}
    try:
        anthropic = (make_anthropic or _anthropic_client)()
    except AnthropicError as error:
        summary.update(error=error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    if anthropic is None:
        # anthropic_key_missing: held loudly before any client is built or anything is read.
        result, code = maker(None, None, None, args.now, args.deliver, fetch, day=args.day)
        out(json.dumps(result, sort_keys=True))
        return code
    try:
        buffer = (make_buffer or _buffer_client)()
        cc = (make_cc or autorelease._cc_client)()
    except BufferError as error:
        summary.update(error=error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    except ProtocolError as error:
        summary.update(error='control_center_' + error.code, exit=1)
        out(json.dumps(summary, sort_keys=True))
        return 1
    result, code = maker(cc, buffer, anthropic, args.now, args.deliver, fetch, day=args.day)
    out(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
