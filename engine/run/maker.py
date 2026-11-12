"""Lane L0, the maker: the next New York days' Buffer drafts from the ideas and mocks Krish approved, handed off.

`growth.py run maker [--deliver]` runs in GitHub Actions (.github/workflows/maker.yml) at
04:30 UTC, just before or after New York midnight. Without --deliver it is a dry run: it
reads Control Center and Buffer, writes and reviews the words, and creates no draft and
writes nothing to Control Center.

The days it makes (make_days): the slots of today in New York not yet due within release's
lead (MIN_LEAD), plus all of tomorrow's, so a late or missed scheduled run never skips a day;
what an earlier run made is already_made, so the overlap makes nothing twice. By hand, --day
names today or tomorrow in New York and nothing else. Each day is made under its own week's
plan. For each week, in order:

1. His authority: engine/run/autorelease.py week_state, the same rules release applies
   (the plan read back from Control Center by digest, his stops through decision.cc_readback,
   and his one press on the board's mix, bound to the hash of the mix Growth proposes:
   Ruling, Krish, 2026-10-30, "approve the week's mix once, let Growth fill it"). A no on the
   week makes nothing; a hold makes nothing; a slot outside the approved mix is never made.
2. The week's slots, from the slots record the handoff wrote beside the plan
   (cc_records.SLOTS, keyed by the plan's part digests). They are checked twice before
   use: rebuilt with the handoff's own validate_mix_plan against the concepts each part
   carries (so every concept's channels are exactly its slots), and the plan lines of
   part 1, the words he approved, must be the lines these slots make (mix._sections).
   Anything else holds loudly as slots_differ_from_plan.
3. For each slot due on those days on Instagram, YouTube, TikTok or X (never LinkedIn)
   whose concept is approved and not stopped: one draft per concept, channel and week,
   marked taken before any draft is saved, so one run never makes two. A concept already
   in the week's derived index is already_made. A draft in Buffer that carries its claim
   but was never indexed (a run that stopped between the save and the handoff) is
   adopted: rebuilt from Buffer, its words checked, its share declared and reviewed blind,
   and handed off, never made again. A post that is not a draft carrying the claim, or
   more than one, holds loudly as made_not_handed_off.
4. The mock files, by the week's mock manifest (cc_records.MOCKS, sha256 to Drive file
   id, its highest version): each file downloaded from its Drive download link and
   hashed; a file not in the manifest holds as mock_file_missing, one whose bytes differ
   as mock_hash_mismatch. A placement takes the files its format takes
   (release.format_shape): every picture for a carousel, the video for YouTube, the first
   picture (the cover) for one image, none for text. Buffer gets the same Drive link, so
   release rebuilds the post from exactly those bytes.
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
   (buffer_drafts.DraftBuffer.create_draft) and read back. A readback that is not a draft
   with no due time stops the whole run at once, loud (draft_not_a_draft): Buffer queued
   it, and no further draft is made. Otherwise it is rebuilt with autorelease.draft_line
   and handed off at once, that draft alone, in-process through engine/run/handoff.py
   (growth-go-live-manifest, its concept_id and review), which records the review and the
   day's index that release reads; a crash, a refused key or a timeout later in the run
   never strands it. A handoff that does not record it stops the run (handoff_incomplete).
   Nothing here schedules, publishes or deletes; release.yml schedules each post, later,
   only while every gate still passes.

With no approved weekly mix (Ruling, Krish, 2026-11-12: with no approved weekly mix, the maker
drafts from the standing plan and asks him once a week instead of failing): when week_state says
the week's plan is not reported, or reported and not yet approved on the board (NO_APPROVED_MIX),
and the standing plan (specs/standing-plan.json) covers the week and he has not declined it, the
maker drafts that week's workdays from the standing plan instead (standing_week): one text post a
day on X, the one maker channel whose standing format needs no approved edition, from a piece the
publication already published (the public feed, oldest unamplified first, a different piece each
day of the week), written and reviewed blind as above. Instagram, TikTok and YouTube need an
approved edition, so they are counted as no_approved_edition, as the standing plan says. These are
drafts only: never saved in Buffer, never handed off, so release, which reads only the handoff's
index and reviews, never sees one. With --deliver each New York day's drafts are kept in Control
Center as one live report (makeyourmindup:standing:<day>, the words in plain lines marked as
drafts, a day drafted once), and the week raises one ask on his list, "This week's mix isn't
approved" (makeyourmindup:mixask:<ISO week>), only when that address is still empty, so every
other run that week is silent about it. Once his mix is approved, the next run makes his plan.
A week whose only days in this run are rest days (the Sunday that ends a past week) has nothing
to make: it is skipped and its hold, if any, noted in skipped_weeks, never failing the run.

Anthropic calls retry a busy API (anthropic_api.MAX_ATTEMPTS, retry-after honoured, under
MAX_WAIT seconds of waiting); once a call gives up the run stops loudly. The run has a
deadline, RUN_BUDGET after it starts: no Anthropic call reaches past it and no slot is
started after it (maker_out_of_time, loud), which leaves JOB_LIMIT - RUN_BUDGET for the last
slot's Buffer and Control Center work under the job's 30-minute limit, whatever the slot count.

Without ANTHROPIC_API_KEY it holds loudly (anthropic_key_missing) and reads nothing.
Output is one JSON line of counts and reason codes: never words, URLs, ids or keys.
"""
import argparse
import datetime as dt
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

from engine import (backlog, catalog, concepts as concept_rules, engine_state, intensity, mix as mix_rules,
                    voice as voice_check)
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.cc_loop import decisions_paged, revision
from engine.control_center import SLUG, ProtocolError, build_report, proposal
from engine.core import instant, ny_time, read_json
from engine.run import autorelease, buffer_api, cc_records, handoff, release, voice_profile
from engine.run.anthropic_api import CALL_WORST, GAVE_UP, KEY_ENV, Anthropic, AnthropicAuthError, AnthropicError
from engine.run.buffer_api import BufferAuthError, BufferError, CarryHold
from engine.run.buffer_drafts import DraftBuffer
from engine.run.spec import ny_midnight, review_reason
from engine.share import JOBS, StaleSendTest, compare_send_test, share_errors, slot_send_test_request
from engine.social import inventory

ROOT = Path(__file__).resolve().parents[2]
DRIVE_URL = 'https://drive.usercontent.google.com/download?id={}&export=download'
MIN_LEAD = dt.timedelta(minutes=60)  # a slot due sooner is not made: release needs time to read it
MAX_WRITES = 2  # the first words, then one rewrite with the reasons
CALLS_PER_SLOT = MAX_WRITES + 1  # the words (and one rewrite), then the blind review
JOB_LIMIT = 30 * 60  # seconds: maker.yml timeout-minutes
RUN_BUDGET = 20 * 60  # seconds after the start: no Anthropic call reaches past it and no slot starts after it
DRAFT_LOOKBACK = dt.timedelta(days=7)  # drafts listed from the week's Monday less this, by when they were created
WORDS_MAX = {'x': 270, 'instagram': 600, 'tiktok': 600, 'youtube': 600}
TITLE_MAX = 90
YOUTUBE_CATEGORY = '28'  # Science and Technology
NAMES = {'x': 'X', 'instagram': 'Instagram', 'tiktok': 'TikTok', 'youtube': 'YouTube Shorts'}
LIVE = ['scheduled', 'sending', 'sent']
STATE_DIR = Path('.scratch') / 'cc'

# With no approved weekly mix (Ruling, Krish, 2026-11-12) ------------------------------------
STANDING_PLAN = Path('specs') / 'standing-plan.json'
# What week_state says when the week has no approved mix yet, waiting on the plan or on his press: the maker
# drafts from the standing plan. Every other hold (a record that does not match, a hash, a stop) stays as it was.
NO_APPROVED_MIX = ('mix_plan_not_reported', 'mix_not_approved', 'mix_not_proposed')
# The standing plan's format on each maker channel that needs no approved edition: X takes a text post. Instagram,
# TikTok and YouTube Shorts need a picture or a video he approved, so with no mix they get nothing (the standing
# plan: "A slot with no approved edition is recorded as missing, never filled with unapproved creative").
STANDING_FORMAT = {'x': 'text'}
STANDING_DAYS = 6  # a week's workdays (Sunday rests): the pieces needed so no piece repeats on a channel in a week
PIECE_TEXT_MAX = 6000  # characters of the piece the writer is shown
STANDING_SCHEMA = 'growth-standing-drafts/1'
ASK_TITLE = "This week's mix isn't approved"
CONTENT_BOARD = 'https://controlcenter.krishraja.com/#/content?week='

SHARE_RULE = ('Then declare the share: the one specific person who would send this post to one other specific person.'
              ' sender and receiver each name one person by role and relationship (for example: a head of operations'
              ' at a mid-size insurer; her CFO, who signs off the pilot budget), never a crowd. job is the one job'
              ' sending it does for the sender. dm_line is the short message the sender would type with it, in their'
              ' own words. moment is the everyday situation that brings the post to mind.')
WRITER_HEAD = ('You write the words of one social post for makeyourmindup, a publication that takes one AI story apart'
               ' three times a week: who gets paid, what is real and where it leads.')
WRITER_RULES = [
    'Plain English a busy senior leader reads in five seconds. Human and humble: no hype, no lecture, no showing'
    ' off, no launch language.',
    'Never name the person behind the accounts, his handle or his initials. No em dashes. No hashtags, no emojis,'
    ' no links, no @ mentions.',
    'Never ask the reader to share, send, forward, tag, repost, like, comment or follow.',
    SHARE_RULE,
    'title: for YouTube, a plain title of at most 90 characters that carries the idea, with no clickbait;'
    ' for every other channel, an empty string.',
    'Answer only with the JSON the schema asks for.']
WRITER_SYSTEM = '\n'.join([
    WRITER_HEAD,
    'The post carries an idea and a claim the editor approved. The claim is fixed: put it in the words exactly as'
    ' given, character for character, as one whole sentence. Never change, split, shorten or reword it.',
    'Write only from the idea and the claim. Add no fact, number, name, quote, result or source that is not in'
    ' them. If you are unsure, leave it out.',
    'When the editor gave direction, follow it in how you write; it is an instruction, never words to copy into'
    ' the post. Text already on the picture or video is shown for context; the words need not repeat it.'] + WRITER_RULES)
# A standing-plan draft: no approved idea or claim, so the words come only from one piece already published.
STANDING_SYSTEM = '\n'.join([
    WRITER_HEAD,
    'The post shares one useful point from one piece the publication already published, given below. Take the'
    ' point from that piece only. Add no fact, number, name, quote, result or source that is not in it. If you'
    ' are unsure, leave it out.'] + WRITER_RULES)
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
SHARE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['share'],
                'properties': {'share': WRITE_SCHEMA['properties']['share']}}
# A draft already saved but never handed off: its words are fixed, so only its share is declared.
DECLARE_SYSTEM = '\n'.join([
    'You read the words of one social post for makeyourmindup that is already written and saved. Never change or'
    ' judge the words; only declare who would share them.',
    SHARE_RULE.replace('Then declare', 'Declare'),
    'Answer only with the JSON the schema asks for.'])
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


class Stop(Exception):
    """The whole run stops at once, loudly: no further draft is made. What was made is already handed off."""

    def __init__(self, code):
        self.code = code
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


def make_days(now):
    """The New York days a scheduled run makes: today while a slot of it can still be released (its end is more
    than MIN_LEAD away), and tomorrow, whole. A late run so never skips a day; the overlap is already_made."""
    today = ny_time(now).date()
    tomorrow = today + dt.timedelta(days=1)
    return [day for day in (today, tomorrow) if day == tomorrow or ny_midnight(tomorrow) - now > MIN_LEAD]


def is_draft(post):
    """True only for a post Buffer reads back as a draft with no due time: dueAt null or absent, never set."""
    return isinstance(post, dict) and post.get('status') == 'draft' and post.get('dueAt') is None


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
    """{sha256: Drive file id} for the week, its highest version (a corrected map is the next version), or None
    when none is reported. Held (loud) when unreadable."""
    label, key = autorelease._week_label(monday), cc_records.plan_key(parts)
    try:
        found = cc_records.probe(cc, lambda n: cc_records.mocks_run_id(label, key, n), cc_records.MOCKS,
                                 cc_records.MAX_MOCK_RECORDS)
        if found is None:
            raise ValueError('record_unreadable')
        chunks = cc_records.latest_version(found)
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

def brief_of(slot, concept, voice, files, profile=None, note=None):
    """profile: voice_profile.read() for the run, or None; it adds his measured style to the account's voice.
    note: his words on the option as offday.note_parts read them (Ruling, Krish, 2026-11-02): his direction is
    followed and never printed; his quotes are on the media, shown here only so the words fit them."""
    channel, fmt = slot['channel'], slot['format']
    media = ('text only, no picture' if not files else
             str(len(files)) + (' pictures' if len(files) > 1 else ' picture' if release.MEDIA.get(
                 '.' + files[0][1]) == 'image' else ' video'))
    style = ('\n' + profile[voice]) if profile and profile.get(voice) else ''
    return ('Channel: ' + NAMES[channel] + ', ' + VOICE[voice] + style + '\nFormat: ' + fmt + ', ' + media
            + '.\nAt most ' + str(WORDS_MAX[channel]) + ' characters of words, the claim included.'
            + '\nIdea: ' + concept['idea'] + '\nClaim: ' + concept['claim'] + note_brief(note))


def note_brief(note):
    if not isinstance(note, dict):
        return ''
    out = ''
    if note.get('direction'):
        out += '\nEditor\'s direction (follow it, never quote it): ' + note['direction']
    for text in note.get('on_media') or []:
        out += '\nAlready on the picture or video, exactly: ' + json.dumps(text, ensure_ascii=False)
    return out


def voice_reasons(cc, voice, channel, words):
    """The hard voice rules these words break, for every account, personal or the publication's (engine/voice.py;
    Ruling, Krish, 2026-11-09: absolutely everything passes the one voice check). voice is kept for its callers."""
    return voice_check.voice_reasons(cc, channel, words)


def word_checks(slot, concept, words, title, voice_found=None, claim=True):
    """[(code, reasons)] the words and title fail, in order: the claim, the length, the copy lint, the share ask
    and the YouTube title. Empty when they pass. claim=False only for a standing-plan draft, which has no claim."""
    channel, fmt = slot['channel'], slot['format']
    return [(name, found) for name, found in (
        ('words_missing_claim', [] if not claim or concept_rules.carries(concept['claim'], words)
         else ['the claim is not in the words exactly as given']),
        ('words_too_long', [] if len(words) <= WORDS_MAX[channel]
         else ['the words are longer than ' + str(WORDS_MAX[channel]) + ' characters']),
        ('copy_lint_refused', release.copy_errors(words)),
        ('share_ask_refused', release.share_ask_errors({'format': fmt}, words)),
        ('voice_refused', voice_found or []),
        ('title_refused', ([] if channel != 'youtube' else
                           ['a YouTube post needs a plain title'] if not title.strip() or len(title) > TITLE_MAX
                           else release.copy_errors(title, 'titles')))) if found]


def share_block(share):
    return dict({k: share.get(k) for k in ('sender', 'receiver', 'job', 'dm_line', 'moment')}, standalone=True)


def write_words(anthropic, slot, concept, voice, files, profile=None, note=None, voice_check=None):
    """(words, title, share) that carry the claim and pass every check, or Held. One rewrite with the reasons.
    voice_check(words) gives the hard krish-voice rules the words break (voice_reasons), checked like the copy lint."""
    return _written(anthropic, WRITER_SYSTEM, brief_of(slot, concept, voice, files, profile, note), slot, concept,
                    voice_check, claim=True)


def standing_brief(channel, voice, piece, profile=None):
    """The writer's brief for a standing-plan draft: the account's voice, a text post, and one published piece."""
    style = ('\n' + profile[voice]) if profile and profile.get(voice) else ''
    return ('Channel: ' + NAMES[channel] + ', ' + VOICE[voice] + style + '\nFormat: ' + STANDING_FORMAT[channel]
            + ', text only, no picture.\nAt most ' + str(WORDS_MAX[channel]) + ' characters of words.'
            + '\nThe piece, published ' + str(piece['published_at'])[:10] + ': ' + piece['title']
            + ('\nIts subtitle: ' + piece['subtitle'] if piece.get('subtitle') else '')
            + '\nThe piece as published:\n' + piece['text'][:PIECE_TEXT_MAX])


def write_standing(anthropic, slot, voice, piece, profile=None, voice_check=None):
    """(words, title, share) of a standing-plan draft from one published piece, passing every check but the claim
    (it has none), or Held. One rewrite with the reasons."""
    return _written(anthropic, STANDING_SYSTEM, standing_brief(slot['channel'], voice, piece, profile), slot, None,
                    voice_check, claim=False)


def _written(anthropic, system, brief, slot, concept, voice_check, claim):
    reasons, code = [], None
    for _ in range(MAX_WRITES):
        user = brief + ('\nYour last draft was held. Write it again so none of these applies: ' + '; '.join(reasons)
                        if reasons else '')
        got = anthropic.json_message(system, user, WRITE_SCHEMA)
        words, title, share = got.get('words'), got.get('title'), got.get('share')
        code, reasons = None, []
        if not isinstance(words, str) or not words.strip() or not isinstance(title, str) \
                or not isinstance(share, dict):
            code, reasons = 'words_unreadable', ['answer with words, a title and a share block']
            continue
        words = words.strip()
        share = share_block(share)
        failed = word_checks(slot, concept, words, title, voice_check(words) if voice_check else None, claim)
        shared = share_errors(share, True)
        if shared:
            failed.insert(len([f for f in failed if f[0] != 'title_refused']), ('share_block_refused', shared))
        for name, found in failed:
            code = code or name
            reasons += found
        if code is None:
            return words, title.strip(), share
    raise Held(code)


def declare_share(anthropic, slot, concept, voice, files, words, profile=None, note=None):
    """The share block of words already saved (an adopted draft), or Held. The words are never rewritten."""
    user = (brief_of(slot, concept, voice, files, profile, note) + '\nThe words, exactly as saved: '
            + json.dumps(words, ensure_ascii=False))
    got = anthropic.json_message(DECLARE_SYSTEM, user, SHARE_SCHEMA)
    share = got.get('share') if isinstance(got, dict) else None
    if not isinstance(share, dict):
        raise Held('share_block_refused')
    share = share_block(share)
    if share_errors(share, True):
        raise Held('share_block_refused')
    return share


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
        # The mocks are drawn by this engine's renderer from approved templates, not generated by AI.
        return {'instagram': {'type': 'reel' if video else 'post', 'shouldShareToFeed': True, 'isAiGenerated': False}}
    if channel == 'youtube':
        return {'youtube': {'title': title, 'categoryId': YOUTUBE_CATEGORY, 'privacy': 'public',
                            'madeForKids': False}}
    return None


# With no approved weekly mix: the standing plan (Ruling, Krish, 2026-11-12) ----------------------

def standing_plan(root, decisions):
    """The standing plan (specs/standing-plan.json), or None when there is none or his latest decision on it is a no:
    then a week with no approved mix holds as it always did."""
    path = Path(root) / STANDING_PLAN
    if not path.is_file():
        return None
    try:
        plan = read_json(path)
    except (ValueError, OSError):
        return None
    if not isinstance(plan, dict) or not isinstance(plan.get('weeks'), list) \
            or not isinstance(plan.get('channels'), list) or not isinstance(plan.get('proposal_id'), str):
        return None
    on_it = sorted((d for d in decisions or [] if isinstance(d, dict) and d.get('proposal_id') == plan['proposal_id']),
                   key=lambda d: str(d.get('decided_at') or ''))
    if on_it and on_it[-1].get('decision') == 'declined':
        return None
    return plan


def no_approved_mix(state):
    """The reason code when week_state says the week has no approved mix yet (NO_APPROVED_MIX), else None."""
    if not isinstance(state, dict) or state.get('stopped'):
        return None
    why = state.get('why') if state.get('hold') == 'concept_hold' else state.get('hold')
    return why if why in NO_APPROVED_MIX else None


def week_has_ended(days):
    """True when every one of a week's days in this run is a rest day: nothing of it can be made (the Sunday
    that ends a past week)."""
    return all(mix_rules.is_rest_day(ny_midnight(d) + dt.timedelta(hours=12)) for d in days)


def published_pieces(rows, root, now, monday):
    """The articles published before the week began, with their text, oldest unamplified first (the backlog's
    order, engine/backlog.py). Published before the Monday so the list, and each day's pick, holds all week."""
    inventory = backlog.build(rows, None, backlog.pilot_editions(root), root, now, backlog.FEED_DAYS,
                              ['public feed', str(backlog.PILOTS)])
    start = ny_midnight(dt.date.fromisoformat(monday))
    by_id = {r['piece_id']: r for r in rows if isinstance(r, dict)}
    out = []
    for piece in inventory['pieces']:
        row = by_id.get(piece['piece_id'])
        if piece['kind'] == 'article' and row and row.get('text') and instant(piece['published_at']) < start:
            out.append(dict(row, published_at=piece['published_at']))
    return out


def standing_piece(pieces, day):
    """The day's piece: a different one each workday of the week, moving on week to week. None when there are too
    few for that, so a piece never repeats on a channel in a week."""
    n = len(pieces)
    if n >= STANDING_DAYS:
        return pieces[(day.isocalendar()[1] * STANDING_DAYS + day.weekday()) % n]
    return pieces[day.weekday()] if day.weekday() < n else None


def standing_run_id(day):
    return SLUG + ':standing:' + day.isoformat()


def ask_run_id(week_label):
    return SLUG + ':mixask:' + week_label


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')


def _long_day(day):
    """'Tuesday 10 November 2026', whatever the runner's locale."""
    return mix_rules.DAYS[day.weekday()] + ' ' + str(day.day) + ' ' + MONTHS[day.month - 1] + ' ' + str(day.year)


def report_state(work):
    """The engine's 1.20.0 state (engine/engine_state.py) for a live report this run posts, or None. Control Center
    shows the newest live report's priorities, obsessions and next steps on every place, so a maker report without
    them would blank the engine's state there until the next runner or measure report. Read once a run, from the
    directive pulled now; nothing when it is not served or cannot be read (the report then goes as before)."""
    if not work.state_read:
        work.state_read = True
        try:
            directive = work.cc.directive()
        except ProtocolError:
            return None
        work.state_fields = engine_state.fields(work.root, intensity.state(work.root, work.now, directive),
                                                directive) or None
    return work.state_fields


def standing_report(day, monday, why, drafts, now, root, state=None):
    """One New York day's standing-plan drafts, kept in Control Center as one live report: each draft's words in a
    plain line marked as a draft, its piece as the line's link, and the whole in a record. No proposal: nothing on
    his list, and no address release reads (cc_records). state: report_state's fields, so the engine's state rides
    on this report too."""
    label = autorelease._week_label(monday)
    lines = [{'line': 'Drafted from the standing plan (specs/standing-plan.json): no approved mix for ' + label + ' ('
              + why + '). These are drafts only: nothing is saved in Buffer, scheduled or posted, and release never'
              ' reads them.'}]
    lines += [{'line': 'Draft, ' + NAMES[d['channel']] + ', ' + _long_day(day) + ', not approved, from a piece published '
               + d['published'] + ': ' + d['words'], 'evidence_url': d['piece_url']} for d in drafts]
    lines.append({'line': 'Posted, sent, published and spent nothing'})
    record = {'schema': STANDING_SCHEMA, 'day': day.isoformat(), 'week_of': monday, 'why': why,
              'drafts': [{k: d[k] for k in ('channel', 'format', 'piece_url', 'words', 'title', 'share')} for d in drafts]}
    return build_report(standing_run_id(day), 'live', now, revision(root), now, 'ready', cc_records.objectives(),
                        lines + cc_records.record_lines(STANDING_SCHEMA, record), state=state)


def ask_report(monday, why, now, root, state=None):
    """The week's one ask on his list: a strategy proposal saying the mix is not approved and what the maker is doing
    instead. It expires when the week ends. state: report_state's fields, as on standing_report."""
    label = autorelease._week_label(monday)
    first = dt.date.fromisoformat(monday)
    ends = ny_midnight(first + dt.timedelta(days=7))
    words = '\n'.join([
        ASK_TITLE + ': the week of ' + _long_day(first) + ' (' + label + ') has no approved mix yet (' + why + ').',
        '',
        'Until it has, the maker drafts from the standing plan (specs/standing-plan.json): one post a day on X from a'
        ' piece already published, kept in Control Center as a draft. Instagram, TikTok and YouTube Shorts get'
        ' nothing, because each needs an edition you approved. Nothing is saved in Buffer, scheduled or posted.',
        '',
        "To switch to your plan, approve this week's mix on the publish board. The next maker run makes your plan's"
        ' posts instead.',
        '',
        'This ask comes once a week and expires when the week ends.'])
    item = proposal(ask_run_id(label), ASK_TITLE,
                    "Nothing from this week's mix can be made until you approve it, so the maker is drafting from the"
                    ' standing plan, and none of those drafts goes out.',
                    'advice', 'strategy', 'mix_approved', exact_payload=words,
                    evidence=[{'label': "This week's publish board", 'url': CONTENT_BOARD + monday}],
                    reference='docs/MAKER.md, With no approved mix', expires_at=ends)
    return build_report(ask_run_id(label), 'live', now, revision(root), now, 'held', cc_records.objectives(),
                        [{'line': 'Drafted from the standing plan: no approved mix for ' + label + ' (' + why + ')'},
                         {'line': 'Posted, sent, published and spent nothing'}], [item], [],
                        [{'reason': 'week_mix_not_approved', 'detail': label + ': ' + why}], state=state)


class Maker:
    def __init__(self, cc, buffer, anthropic, now, deliver, fetch, root, out_path=None, deadline=None,
                 clock=time.monotonic):
        self.cc, self.buffer, self.anthropic = cc, buffer, anthropic
        self.now, self.deliver, self.fetch, self.root, self.out_path = now, deliver, fetch, root, out_path
        self.deadline, self.clock = deadline, clock
        self.tally = Tally()
        self.organizations, self.listed, self.downloads = [], {}, {}
        self.since = self.created_since = None
        self.handed = {'recorded': 0, 'holds': {}, 'error': None}
        self.profile = None  # voice_profile.read() for the run; None drafts from the account rules alone
        self.board = None  # the board client whose mix press approves the week (autorelease.mix_binding)
        # With no approved weekly mix (Ruling, Krish, 2026-11-12): the standing plan, the published pieces (read once,
        # when a week first needs them), what each week was drafted from, each standing week's counts, and the weeks
        # skipped because nothing of them can be made in this run.
        self.standing_doc, self.feed, self.rows = None, catalog.pieces, None
        self.drafted_from, self.standing, self.skipped = {}, {}, {}
        # The engine's 1.20.0 state for the live reports this run posts (report_state): read once, on first need.
        self.state_read, self.state_fields = False, None

    def out_of_time(self):
        return self.deadline is not None and self.clock() >= self.deadline

    def carrying(self, channel, claim):
        """The posts on this engine's channel that carry the claim: drafts created since created_since (the
        week's Monday less DRAFT_LOOKBACK) and posts scheduled or gone out since the week began (since), so the
        read never grows with the channel's history."""
        if channel not in self.listed:
            pinned, posts = BUFFER_CHANNEL_ID[channel], []
            for organization in self.organizations:
                posts += self.buffer.list_drafts(organization, [pinned], self.created_since)
                posts += self.buffer.list_posts(organization, LIVE, [pinned], self.since)
            self.listed[channel] = [p for p in posts if isinstance(p, dict) and p.get('channelId') == pinned]
        return [p for p in self.listed[channel] if concept_rules.carries(claim, p.get('text') or '')]

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

    def voice_found(self, voice, channel, words):
        """voice_reasons for this run's client, with an unread verdict counted (voice_check_unread), never a hold."""
        found = voice_reasons(self.cc, voice, channel, words)
        if found is None:
            self.tally.count('voice_check_unread')
            return []
        return found

    def prepare(self, slot, concept, manifest):
        """(files, blind asset names) of one placement, or Held."""
        due = autorelease.due_instant(slot['due_at'])
        if due is None or due - self.now < MIN_LEAD:
            raise Held('due_too_soon')
        files = placement_files(self.mocks_of(concept, manifest), slot['format'], slot['channel'])
        assets = [{'name': 'mock-' + str(n) + '.' + ext, 'sha256': sha} for n, (sha, ext) in enumerate(files, 1)]
        return files, assets

    def make(self, slot, concept, voice, manifest, monday, note=None):
        """The handoff slot for one draft made and handed off (or None in a dry run), Held, or Stop."""
        files, assets = self.prepare(slot, concept, manifest)
        words, title, share = write_words(self.anthropic, slot, concept, voice, files, self.profile, note,
                                          voice_check=lambda w: self.voice_found(voice, slot['channel'], w))
        answer = review_words(self.anthropic, slot, words, share, assets)
        if not self.deliver:
            return None
        channel = slot['channel']
        pinned = BUFFER_CHANNEL_ID[channel]
        body = [{release.MEDIA['.' + ext]: {'url': drive_url(manifest[sha])}} for sha, ext in files]
        try:
            created = self.buffer.create_draft(channel, pinned, words, body, draft_metadata(channel, files, title))
        except BufferAuthError:
            raise
        except BufferError:
            raise Held('draft_not_saved', loud=True) from None
        self.tally.count('drafts_saved')
        if not is_draft(created):
            raise Stop('draft_not_a_draft')  # Buffer queued it: no further draft is made this run
        try:
            post = self.buffer.get_post(created.get('id'))
        except BufferAuthError:
            raise
        except BufferError:
            raise Held('draft_not_read_back', loud=True) from None
        if not is_draft(post):
            raise Stop('draft_not_a_draft')
        if post.get('channelId') != pinned or post.get('text') != words or len(post.get('assets') or []) != len(files):
            raise Held('draft_readback_differs', loud=True)
        return self.hand(slot, concept, post, files, assets, share, answer, monday)

    def adopt(self, slot, concept, voice, manifest, monday, found, note=None):
        """A draft saved by an earlier run but never handed off, made good: read back, its words checked, its share
        declared and reviewed blind, and handed off. Its words are never changed. Every hold is loud: a draft
        exists that release cannot read."""
        try:
            files, assets = self.prepare(slot, concept, manifest)
            try:
                post = self.buffer.get_post(found.get('id'))
            except BufferAuthError:
                raise
            except BufferError:
                raise Held('draft_not_read_back') from None
            words = post.get('text')
            if not is_draft(post) or post.get('channelId') != BUFFER_CHANNEL_ID[slot['channel']] \
                    or not isinstance(words, str) or len(post.get('assets') or []) != len(files):
                raise Held('made_not_handed_off')
            meta = post.get('metadata') if isinstance(post.get('metadata'), dict) else {}
            title = meta.get('title') if slot['channel'] == 'youtube' and isinstance(meta.get('title'), str) else ''
            failed = word_checks(slot, concept, words, title, self.voice_found(voice, slot['channel'], words))
            if failed:
                raise Held(failed[0][0])
            share = declare_share(self.anthropic, slot, concept, voice, files, words, self.profile, note)
            answer = review_words(self.anthropic, slot, words, share, assets)
            if not self.deliver:
                return None
            return self.hand(slot, concept, post, files, assets, share, answer, monday)
        except Held as hold:
            raise Held(hold.code, loud=True) from None

    def hand(self, slot, concept, post, files, assets, share, answer, monday):
        """Rebuild one saved draft as release will, judge its review at its own digest, and hand it off now."""
        channel = slot['channel']
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
        one = {'slot': slot['slot_id'], 'channel': channel, 'buffer_draft_id': post['id'], 'payload_sha256': payload,
               'per_item_review': False, 'format': slot['format'], 'due_at': slot['due_at'], 'link_placement': None,
               'publish_mode': 'engine', 'concept_id': concept['concept_id'],
               'review': {'slot_id': slot['slot_id'], 'verdict': 'pass', 'lens': 'send-test',
                          'payload_sha256': payload, 'reader_answer': answer, 'share': share,
                          'asset_names': [a['name'] for a in assets]}}
        self.hand_off(one, monday)
        return one

    def hand_off(self, one, monday):
        """Record this one draft's review and index entry now, so nothing later in the run can strand it."""
        run_id = SLUG + ':' + autorelease._week_label(monday) + ':week'
        result, code = handoff.handoff(handoff.GO_LIVE, {'run_id': run_id, 'slots': [one]}, self.cc, self.buffer,
                                       self.now, True, lambda url: self.fetch(url)[:2], self.root, self.out_path)
        recorded = result['slots'].get('derived_recorded', 0)
        self.handed['recorded'] += recorded
        for hold, n in (result.get('holds') or {}).items():
            self.handed['holds'][hold] = self.handed['holds'].get(hold, 0) + n
        self.handed['error'] = self.handed['error'] or result.get('error')
        if code or recorded != 1:
            raise Stop('handoff_incomplete')  # a draft exists that release cannot read yet: the next run adopts it


def standing_week(work, monday, days, why, voices):
    """Draft each of days (workdays of the week starting monday) from the standing plan: no approved mix, so the
    standing plan's own cadence on the maker's channels, from pieces already published. Drafts only: nothing is
    saved in Buffer or handed off. With deliver, each day's drafts are one live report in Control Center, and the
    week raises its one ask on his list when none is raised yet. Raises Stop like make_week."""
    label = autorelease._week_label(monday)
    counts = work.standing.setdefault(label, {'why': why, 'held': {}})

    def count(key, n=1):
        counts[key] = counts.get(key, 0) + n

    def hold(code, loud=False):
        counts['held'][code] = counts['held'].get(code, 0) + 1
        if loud:
            work.tally.loud.append(code)

    channels = [c for c in concept_rules.CONCEPT_CHANNELS
                if c in work.standing_doc['channels'] and c not in release.KRISH_CLICK_ONLY]
    pieces = None
    for day in days:
        try:
            if cc_records.read_report(work.cc, standing_run_id(day)) is not None:
                count('already_drafted')  # an earlier run drafted this day: a day is drafted once
                continue
        except ValueError:
            hold('standing_record_unreadable', loud=True)
            continue
        drafts = []
        for channel in channels:
            fmt = STANDING_FORMAT.get(channel)
            if fmt is None:
                count('no_approved_edition')
                continue
            if voices.get(channel) not in VOICE:
                hold('account_voice_unknown')
                continue
            if pieces is None:
                try:
                    if work.rows is None:
                        work.rows = work.feed(backlog.FEED_DAYS, work.now)
                    pieces = published_pieces(work.rows, work.root, work.now, monday)
                except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException):
                    pieces = False  # the feed could not be read: nothing is guessed, the next run tries again
            if pieces is False:
                hold('pieces_unreadable')
                continue
            piece = standing_piece(pieces, day)
            if piece is None:
                hold('no_published_piece')
                continue
            if work.out_of_time():
                raise Stop('maker_out_of_time')
            slot = {'slot_id': channel + '-' + day.isoformat() + '-standing', 'channel': channel, 'format': fmt}
            try:
                words, title, share = write_standing(
                    work.anthropic, slot, voices[channel], piece, work.profile,
                    voice_check=lambda w, c=channel: work.voice_found(voices[c], c, w))
                review_words(work.anthropic, slot, words, share, [])
            except Held as held:
                hold(held.code)
                continue
            except AnthropicAuthError:
                raise
            except AnthropicError as error:
                if error.code in GAVE_UP:
                    raise Stop(error.code) from None
                hold(error.code)
                continue
            drafts.append({'channel': channel, 'format': fmt, 'piece_url': piece['url'], 'words': words,
                           'title': title, 'share': share, 'published': str(piece['published_at'])[:10]})
        if not drafts:
            continue
        if not work.deliver:
            count('would_draft', len(drafts))
            continue
        posted = work.cc.post_report(standing_report(day, monday, why, drafts, work.now, work.root,
                                                     report_state(work)))
        if posted['accepted']:
            count('drafted', len(drafts))
        else:
            hold('standing_report_conflict', loud=True)
    counts['ask'] = raise_ask(work, monday, why)


def raise_ask(work, monday, why):
    """The week's one ask, "This week's mix isn't approved", on his list once per ISO week: raised only when its
    address is still empty, so every other run that week says nothing. Returns what happened, as a code."""
    label = autorelease._week_label(monday)
    try:
        if cc_records.read_report(work.cc, ask_run_id(label)) is not None:
            return 'already_raised'
    except ValueError:
        return 'ask_unreadable'  # never raised twice: a record that cannot be read counts as raised
    if not work.deliver:
        return 'would_raise'
    posted = work.cc.post_report(ask_report(monday, why, work.now, work.root, report_state(work)))
    return 'raised' if posted['accepted'] else 'already_raised'


def make_week(work, monday, days, decisions, proposals, folder, cfg, voices):
    """Make the slots of days (all in the week starting monday) under that week's plan, or, with no approved mix
    for the week, draft them from the standing plan (standing_week)."""
    tally = work.tally
    label = autorelease._week_label(monday)
    state = autorelease.week_state(work.cc, monday, decisions, folder, work.now, work.root, proposals, work.board)
    if week_has_ended(days):
        # Nothing of this week can be made in this run: its hold, if any, is noted and never fails the run.
        work.skipped[label] = ('week_stopped' if state.get('stopped') else
                               (state.get('why') if state.get('hold') == 'concept_hold' else state.get('hold'))
                               or 'rest_days_only')
        return
    if state.get('stopped'):
        tally.count('week_stopped')
        return
    why = no_approved_mix(state)
    if why and work.standing_doc is not None and monday in work.standing_doc['weeks']:
        work.drafted_from[label] = 'standing_plan'
        standing_week(work, monday, [d for d in days if not week_has_ended([d])], why, voices)
        return
    if state.get('hold'):
        tally.hold(state['why'] if state['hold'] == 'concept_hold' and state.get('why') else state['hold'],
                   loud=state.get('loud', False))
        return
    work.drafted_from[label] = 'his_mix'
    approved, stops = state['decision']['concepts'], set(state['decision']['stopped_concepts'] or [])
    known = {c['concept_id']: c for c in state['spec']['concepts']}
    parts, read = read_plan(work.cc, monday)
    slots = [s for s in week_slots(work.cc, monday, parts, read, cfg, work.root)
             if ny_time(s['due_at']).date() in days]
    manifest = mock_manifest(work.cc, monday, parts)
    week = autorelease.week_entries(work.cc, monday, tally.holds)
    if week is None:
        raise Held('derived_index_unreadable', loud=True)
    done = {(e['concept_id'], e['channel']) for e in week}
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
            if mix_rules.is_rest_day(slot['due_at']):
                raise Held('rest_day')  # Ruling (Krish, 2026-11-02): no publishing on Sunday, permanently
            if autorelease.outside_mix(state, cid, channel, slot['format'], slot['due_at']):
                raise Held('outside_approved_mix')
            if voices.get(channel) not in VOICE:
                raise Held('account_voice_unknown')
            # His words on the approved option (Ruling, Krish, 2026-11-02): a quote that reads as what not to say
            # holds for him to answer; his direction and his on-media quotes reach the brief.
            note = autorelease.note_for(state, cid, slot['due_at'])
            if note.get('hold'):
                raise Held('note_needs_krish', loud=True)
            if (cid, channel) in done:
                tally.count('already_made')
                continue
            if work.out_of_time():
                raise Stop('maker_out_of_time')
            found = work.carrying(channel, concept['claim'])
            done.add((cid, channel))  # taken before any draft is saved: one run never makes two
            if found:
                if len(found) != 1 or not is_draft(found[0]):
                    tally.count('already_made')
                    tally.loud.append('made_not_handed_off')
                    continue
                one = work.adopt(slot, concept, voices[channel], manifest, monday, found[0], note)
                tally.count('would_adopt' if one is None else 'adopted')
                continue
            one = work.make(slot, concept, voices[channel], manifest, monday, note)
            tally.count('would_make' if one is None else 'made')
        except Held as hold:
            tally.hold(hold.code, hold.loud)
        except AnthropicAuthError:
            raise
        except AnthropicError as error:
            if error.code in GAVE_UP:
                raise Stop(error.code) from None  # the API is busy or down: loud, and the rest waits
            tally.hold(error.code)


def maker(cc, buffer, anthropic, now=None, deliver=False, fetch=None, root=None, out_path=None, day=None,
          clock=time.monotonic, board=None, profile=None, feed=None):
    """Returns (summary, exit_code). summary holds counts and codes only.

    day (YYYY-MM-DD) names the New York day to make by hand; only today or tomorrow there is accepted,
    so a yes given after the night's run can still be made that morning (day_out_of_range otherwise).
    Without it, the days are make_days(now).
    profile is voice_profile.read() (main reads it live); None makes the drafts from the account rules alone.
    feed(days, now) reads the published pieces a standing-plan draft is written from (default: the public feed,
    engine/catalog.py). summary says, per week, what it was drafted from (drafted_from: his_mix or standing_plan),
    each standing week's counts and its ask (standing), and the weeks skipped with their hold (skipped_weeks)."""
    started = clock()
    now = instant(now)
    root = Path(root or ROOT)
    if day is None:
        days = make_days(now)
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
        days = [day]
    mondays = sorted({(d - dt.timedelta(days=d.weekday())).isoformat() for d in days})
    summary = {'lane': 'L0', 'command': 'maker', 'deliver': bool(deliver), 'days': [d.isoformat() for d in days],
               'weeks': [autorelease._week_label(m) for m in mondays], 'slots': {}, 'holds': {}, 'mutations': 0,
               'handoff': None, 'taste': 'taste_unavailable', 'loud': [], 'error': None,
               'voice_profile': 'read' if profile else 'voice_profile_unavailable', 'drafted_from': {},
               'standing': {}, 'skipped_weeks': {}}
    work = Maker(cc, buffer, anthropic, now, deliver, fetch or buffer_api.download_facts, root, out_path,
                 started + RUN_BUDGET, clock)
    work.board = board
    work.profile = profile
    if feed is not None:
        work.feed = feed
    tally = work.tally
    if anthropic is None:
        # No words without the key: nothing is read, nothing is made, and the run fails so GitHub emails him.
        tally.hold('anthropic_key_missing', loud=True)
        return _finish(summary, tally, buffer)
    if callable(getattr(anthropic, 'set_deadline', None)):
        anthropic.set_deadline(started + RUN_BUDGET)
    first = ny_midnight(dt.date.fromisoformat(mondays[0]))
    work.since, work.created_since = first.isoformat(), (first - DRAFT_LOOKBACK).isoformat()
    folder = tempfile.TemporaryDirectory()
    try:
        work.organizations = buffer.account_check().get('organization_ids') or []
        decisions = decisions_paged(cc, now - autorelease.LOOKBACK)
        if decisions is None:
            raise autorelease.Unpaged()
        proposals = autorelease.signed_golives(cc, decisions, {}, now)
        work.standing_doc = standing_plan(root, decisions)
        cfg = mix_rules.load(root)
        voices = {c: (inventory(root)['channel'].get(c) or {}).get('account_context')
                  for c in concept_rules.CONCEPT_CHANNELS}
        for monday in mondays:
            in_week = [d for d in days if (d - dt.timedelta(days=d.weekday())).isoformat() == monday]
            try:
                make_week(work, monday, in_week, decisions, proposals, folder.name, cfg, voices)
            except Held as hold:
                tally.hold(hold.code, hold.loud)
    except Stop as stop:
        tally.hold(stop.code, loud=True)
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
    if work.handed['recorded'] or work.handed['error'] or work.handed['holds']:
        summary['handoff'] = work.handed
    summary.update(drafted_from=dict(sorted(work.drafted_from.items())), skipped_weeks=dict(sorted(work.skipped.items())),
                   standing={label: dict(sorted(c.items())) for label, c in sorted(work.standing.items())})
    return _finish(summary, tally, buffer)


def step_summary(summary):
    """The run's lines for the GitHub job summary: what each week was drafted from, in counts and codes only."""
    lines = []
    for label, source in sorted((summary.get('drafted_from') or {}).items()):
        if source != 'standing_plan':
            lines.append('- ' + label + ": drafted from Krish's approved mix.")
            continue
        counts = (summary.get('standing') or {}).get(label) or {}
        made = counts.get('drafted', 0) + counts.get('would_draft', 0)
        lines.append('- ' + label + ': drafted from the standing plan, no approved weekly mix (' + str(counts.get('why'))
                     + '). Drafts ' + ('kept in Control Center' if summary.get('deliver') else 'written, dry run, saved'
                                       ' nowhere') + ': ' + str(made) + ' new, ' + str(counts.get('already_drafted', 0))
                     + ' already drafted, ' + str(sum((counts.get('held') or {}).values())) + ' held; '
                     + str(counts.get('no_approved_edition', 0)) + ' with no approved edition. The ask: '
                     + str(counts.get('ask')) + '.')
    for label, code in sorted((summary.get('skipped_weeks') or {}).items()):
        lines.append('- ' + label + ': skipped, nothing of it can be made in this run (' + str(code) + ').')
    return ['### Maker', ''] + (lines or ['- Nothing drafted.']) + ['']


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


def main(argv=None, make_cc=None, make_buffer=None, make_anthropic=None, fetch=None, out=print, make_board=None,
         read_profile=None):
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
    from engine.run.board_tick import board_from_env
    result, code = maker(cc, buffer, anthropic, args.now, args.deliver, fetch, day=args.day,
                         board=(make_board or board_from_env)(), profile=(read_profile or voice_profile.read)())
    out(json.dumps(result, sort_keys=True))
    where = os.environ.get('GITHUB_STEP_SUMMARY', '').strip()
    if where:
        try:
            with open(where, 'a', encoding='utf-8') as handle:
                handle.write('\n'.join(step_summary(result)) + '\n')
        except OSError:
            pass  # the job summary is a courtesy: the JSON line above is the record
    return code


if __name__ == '__main__':
    sys.exit(main())
