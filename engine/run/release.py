"""Release Gate: a signed run-spec slot becomes exact Buffer MCP call
arguments, and a Buffer readback becomes local evidence. Offline only.

This code never calls Buffer, Control Center or any network, and it never
schedules, sends or posts. A session passes the emitted `arguments` verbatim
to the named Buffer MCP tool, then feeds the get_post readback to `release
check`. Uncertain outcomes are held for a readback, never retried blindly.

Buffer schema facts relied on, read on 27 October 2026 with the read-only
introspect_schema and the create_post/edit_post/get_post tool definitions.
Recheck them before trusting this after a provider change:
- GraphQL createPost(input: CreatePostInput!) and editPost(input:
  EditPostInput!) both return PostActionPayload. CreatePostInput needs
  channelId, schedulingType and mode (ShareMode!, required), while the
  create_post domain tool defaults mode to addToQueue; a draft create_post
  therefore relies on saveToDraft true overriding that default, and every
  scheduled call names customScheduled. EditPostInput needs only id.
- ShareMode: addToQueue, customScheduled, shareNext, shareNow. dueAt is ISO
  8601 with an offset, only valid with customScheduled, and must be in the
  future. SchedulingType: automatic, notification.
- Every edit_post is revalidated as a whole post, not merged with the stored
  one, and sending a mode reschedules it. Stored alt text and AI labels are
  therefore read from the target draft and carried forward, or the edit holds.
- AssetInput is exactly one of {image: {url, metadata: {altText}}},
  {video: {url}} or {document: {url, title, thumbnailUrl}}. A returned
  ImageAsset carries source and image.altText.
- Metadata: instagram {type, shouldShareToFeed (required), isAiGenerated,
  link (the Story link sticker), stickerFields}; facebook {type post|reel|
  story}; tiktok {isAiGenerated, title}; twitter {isAiGenerated}; threads
  {type}; youtube needs title and categoryId; linkedin, facebook, threads and
  substack readbacks carry linkAttachment. The domain tool refuses a null
  linkedin linkAttachment; GraphQL EditPostInput is the inspected clear route.
- Post carries channelId, channelService, schedulingType, status, via,
  externalLink and sentAt. PostStatus: draft, error, needs_approval,
  scheduled, sending, sent. PostVia: api, buffer, network.

The decision file is Krish's recorded go-live decision for one run:
{"run_id", "proposal_id", "decision": "approved", "decided_at",
 "slots": {slot_id: payload_sha256}}. An amended slot carries his amended
digest, so the amended version is the one that releases. The spec's
signature names that proposal and records decision_digest, the sha256 of the
canonical JSON of the decision's slots map; both are required.

A malformed or hand-edited slot refuses the whole run on purpose: the spec is
signed as one document, so a bad line means the signing cannot be trusted.

Asset bytes: --assets must be a folder of fresh downloads of each asset url,
made into .scratch immediately before release. Buffer fetches the url, and
the Drive 4 Growth library is editable by link, so older copies prove nothing.

Channel lock (28 October 2026): the Buffer organisation is shared with other
ventures, so a channel acts only when its service, name and channelId all
match this engine's pinned entry, and an id on the denylist is refused
wherever it appears: list_channels, a built call, an edit target or a
readback. Copy lint (Krish, 28 October 2026): a slot whose words, or the alt
text and titles its call carries, hit content-engine's copy lint
(engine/copy_lint.py) is held and never emitted; his name is one of its
patterns ("no content refers to Krish, ever").
Capability checks (28 October 2026): on a channel and format that
social.route does not show as verified and fresh, only the run's earliest
signed post releases, as the route's capability check; the rest hold until
the route is recorded as passed in social/tools/buffer.json. A check already
released, in this run's ledger or any other run's under .scratch/runs, is the
route's one check: nothing else on the route releases, in any run, until the
route is recorded as passed. Share asks (Krish, 28 October 2026, R99): a
snackable slot whose words ask for the share is held, as the copy lint holds.
Concept approval (Ruling, Krish, 2026-10-29; engine/concepts.py, R101): on
Instagram, YouTube, TikTok and X a slot with no digest of its own releases when
decision.json approves its concept at the concept_sha256 the signature's
concepts_digest binds, and only while it matches the concept's placements, mock
files and claim; a slot that departs holds as departs_from_approved_mock. A
stopped concept, or a stopped mix plan proposal, holds every post made from it,
and so does any decline not yet matched to its plan. Such a post also needs a
passing review at its payload_sha256 and room under its channel's daily cap,
counted across every run's ledger. Every other check above still runs on each
post. With no go-live for the week, decision.json is concept-only (proposal_id
and decision null, slots {}; engine/run/decision.py writes it): the approved
mix plan is then the go-live for posts made from its concepts and nothing else
releases (docs/CONCEPT-MANIFEST.md).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from engine import concepts as concept_rules
from engine.buffer_channels import BUFFER_CHANNEL_ID, DENIED_CHANNELS, channel_id_errors
from engine.control_center import sha256_hex
from engine.copy_lint import copy_lint_errors, version as copy_lint_version
from engine.core import instant, locked, ny_time, read_json, write_json
from engine.share import cta_applies, cta_errors
from engine.social import inventory, route
from engine import intensity

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_CHECKED = '2026-10-27'
SERVER = 'Buffer'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
BUFFER_ID = re.compile(r'^[a-f0-9]{24}$')
DUE_AT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3}|\.\d{6})?(?:Z|[+-]\d{2}:\d{2})$')
PLAY = re.compile(r'^P[1-9]$')
ASSET_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._-]*$')
SAFE = re.compile(r'[^A-Za-z0-9._-]+')
SLOT_KEYS = {'slot_id', 'channel', 'format', 'play', 'due_at', 'words', 'assets', 'link_placement',
             'cta', 'forward_line', 'experiment_arm', 'publish_mode', 'buffer_draft_id', 'payload_sha256'}
# Optional on a slot and outside its digest: share (built to be sent), ecosystem_cta (lint's route) and
# concept_id (the approved concept it is made from, R101).
OPTIONAL_SLOT_KEYS = {'share', 'ecosystem_cta', 'concept_id'}
ASSET_KEYS = {'name', 'sha256', 'url', 'bytes'}
DIGEST_KEYS = ('channel', 'format', 'words', 'link_placement', 'due_at', 'publish_mode')
# Channel id -> (Buffer service, native hosts). Hosts match exactly.
CHANNELS = {
    'substack-notes': ('substack', ('substack.com', 'www.substack.com')),
    'threads': ('threads', ('threads.net', 'www.threads.net', 'threads.com', 'www.threads.com')),
    'x': ('twitter', ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com')),
    'instagram': ('instagram', ('instagram.com', 'www.instagram.com')),
    'facebook': ('facebook', ('facebook.com', 'www.facebook.com', 'm.facebook.com')),
    'tiktok': ('tiktok', ('tiktok.com', 'www.tiktok.com')),
    'youtube': ('youtube', ('youtube.com', 'www.youtube.com', 'm.youtube.com')),
    'linkedin': ('linkedin', ('linkedin.com', 'www.linkedin.com')),
}
# Channel id -> social/channels profile id.
CHANNEL_PROFILE = {'substack-notes': 'substack-notes', 'threads': 'threads', 'x': 'x', 'instagram': 'instagram',
                   'facebook': 'facebook', 'tiktok': 'tiktok', 'youtube': 'youtube', 'linkedin': 'linkedin'}
# Channel id -> the one Buffer channel name this engine may use (read from
# list_channels on 2026-10-27). The Buffer organisation is shared with other
# ventures, so a service alone never identifies this engine's account; a renamed
# or missing channel holds instead of guessing.
BUFFER_NAME = {'substack-notes': 'Krish', 'threads': 'krishraja1', 'x': 'TheRealKrisho',
               'instagram': 'makeyourmind.up', 'facebook': 'Makeyourmind/up', 'tiktok': 'therealkrisho',
               'youtube': 'makeyourmindup', 'linkedin': 'krish-raja'}
# BUFFER_CHANNEL_ID and DENIED_CHANNELS live in engine/buffer_channels.py, the
# one table release and social preflight both read.
# Native post URLs that carry the account handle as their first path segment.
HANDLE_IN_PATH = ('x', 'tiktok', 'threads', 'substack-notes')
KRISH_CLICK_ONLY = ('linkedin',)
# A placement that lives entirely in `words`, so one Buffer call carries it.
EXPRESSIBLE_LINK_PLACEMENTS = (None, 'none', 'in_post')
MEDIA = {'.png': 'image', '.jpg': 'image', '.jpeg': 'image', '.gif': 'image', '.webp': 'image',
         '.mp4': 'video', '.mov': 'video', '.webm': 'video', '.pdf': 'document'}
NEEDS_MEDIA = ('instagram', 'tiktok', 'youtube')
NO_MIXED_MEDIA = ('instagram', 'facebook', 'tiktok')
STORY_TYPED = ('instagram', 'facebook')
PREVIEW_CLEAR_ROUTE = {
    'tool': 'execute_mutation', 'server': SERVER,
    'mutation': 'editPost(input: $input)', 'input_type': 'EditPostInput!',
    'returns': 'PostActionPayload: PostActionSuccess { post { id status dueAt } } or MutationError { message }',
}
DROP_HOLD = 'edit_would_drop_alt_text_or_ai_label'


# Slot identity -------------------------------------------------------------

def slot_digest(slot):
    """sha256 of the canonical JSON of exactly what would act."""
    body = {key: slot[key] for key in DIGEST_KEYS}
    body['assets'] = [asset['sha256'] for asset in slot['assets']]
    return sha256_hex(body)


def media_kind(asset):
    kind = MEDIA.get(Path(asset['name']).suffix.lower())
    if kind is None:
        raise ValueError('unsupported asset type: ' + asset['name'])
    return kind


def _squash(value):
    return re.sub(r'[^a-z0-9]', '', (value or '').lower())


def is_draft(slot):
    return slot['publish_mode'] == 'krish_click' or slot['due_at'] is None


def check_slot(slot):
    """Refuse a malformed slot or one whose stored digest is not its own."""
    if not isinstance(slot, dict) or set(slot) - OPTIONAL_SLOT_KEYS != SLOT_KEYS:
        raise ValueError('slot must carry exactly the run-spec slot fields (share, ecosystem_cta and concept_id'
                         ' are optional)')
    sid = slot['slot_id']
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError('slot_id is required')
    if slot.get('concept_id') is not None and not (isinstance(slot['concept_id'], str) and slot['concept_id'].strip()):
        raise ValueError(sid + ': concept_id must be text or null')
    if slot['channel'] not in CHANNELS:
        raise ValueError(sid + ': unknown channel ' + str(slot['channel']))
    if not isinstance(slot['format'], str) or not slot['format'].strip():
        raise ValueError(sid + ': format is required')
    if slot['play'] is not None and not (isinstance(slot['play'], str) and PLAY.match(slot['play'])):
        raise ValueError(sid + ': play must be P1 to P9 or null')
    if slot['due_at'] is not None:
        if not isinstance(slot['due_at'], str) or not DUE_AT.match(slot['due_at']):
            raise ValueError(sid + ': due_at must be ISO 8601 with seconds and an offset')
        instant(slot['due_at'])
    for key in ('words', 'forward_line'):
        if not isinstance(slot[key], str):
            raise ValueError(sid + ': ' + key + ' must be text')
    if not slot['words'].strip():
        raise ValueError(sid + ': words are required')
    if type(slot['cta']) is not bool:
        raise ValueError(sid + ': cta must be true or false')
    for key in ('link_placement', 'experiment_arm'):
        if slot[key] is not None and not isinstance(slot[key], str):
            raise ValueError(sid + ': ' + key + ' must be text or null')
    if slot['publish_mode'] not in ('engine', 'krish_click'):
        raise ValueError(sid + ': publish_mode must be engine or krish_click')
    if slot['channel'] in KRISH_CLICK_ONLY and slot['publish_mode'] != 'krish_click':
        raise ValueError(sid + ': ' + slot['channel'] + ' is Krish\'s own click; it is never released by the engine')
    if slot['buffer_draft_id'] is not None and not (isinstance(slot['buffer_draft_id'], str)
                                                    and BUFFER_ID.match(slot['buffer_draft_id'])):
        raise ValueError(sid + ': buffer_draft_id must be a Buffer post id or null')
    if not isinstance(slot['assets'], list):
        raise ValueError(sid + ': assets must be a list')
    for asset in slot['assets']:
        if not isinstance(asset, dict) or set(asset) != ASSET_KEYS:
            raise ValueError(sid + ': each asset carries exactly name, sha256, url and bytes')
        if not isinstance(asset['name'], str) or not ASSET_NAME.match(asset['name']):
            raise ValueError(sid + ': asset name must be a plain file name')
        if not isinstance(asset['sha256'], str) or not HEX64.match(asset['sha256']):
            raise ValueError(sid + ': asset sha256 must be 64 lower-case hex characters')
        if type(asset['bytes']) is not int or asset['bytes'] < 1:
            raise ValueError(sid + ': asset bytes must be a positive whole number')
        if asset['url'] is not None and not https_url(asset['url']):
            raise ValueError(sid + ': asset url must be https or null')
        media_kind(asset)
    if slot['format'] == 'story' and len(slot['assets']) != 1:
        # F14: Stories are one frame per post; a sequence is several slots.
        raise ValueError(sid + ': a Story is one frame per post')
    if slot['channel'] in ('instagram', 'facebook') and 'sticker' in _squash(slot['link_placement']):
        # F09: the sticker switched Automatic to Notify Me in the composer.
        raise ValueError(sid + ': an Instagram Story link sticker is never set or claimed automatic')
    if slot['channel'] in NEEDS_MEDIA and not slot['assets']:
        raise ValueError(sid + ': ' + slot['channel'] + ' needs an image or video asset')
    if not isinstance(slot['payload_sha256'], str) or not HEX64.match(slot['payload_sha256']):
        raise ValueError(sid + ': payload_sha256 must be 64 lower-case hex characters')
    if slot['payload_sha256'] != slot_digest(slot):
        raise ValueError(sid + ': payload_sha256 is not this slot\'s computed digest')
    return slot


def https_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        u = urlsplit(value)
    except ValueError:
        return False
    return u.scheme == 'https' and bool(u.hostname) and not (u.username or u.password)


def _first_segment(url):
    parts = [p for p in urlsplit(url).path.split('/') if p]
    return parts[0].lower() if parts else ''


def native_host(channel, url, account_url=None):
    """An https native URL on the channel's host and, where the native URL
    carries the handle, on the expected account."""
    if not https_url(url):
        return False
    if urlsplit(url).hostname.lower() not in CHANNELS[channel][1]:
        return False
    if account_url and channel in HANDLE_IN_PATH:
        handle = _first_segment(account_url)
        return bool(handle) and _first_segment(url) == handle
    return True


def load_accounts(root=None):
    """Channel id -> account_url for channels whose native URLs carry the handle."""
    folder = Path(root or ROOT) / 'social' / 'channels'
    out = {}
    for channel in HANDLE_IN_PATH:
        path = folder / (CHANNEL_PROFILE[channel] + '.json')
        if path.is_file():
            out[channel] = read_json(path)['account_url']
    return out


def verify_asset_bytes(slot, paths):
    """Refuse unless every file, in order, has the signed bytes and sha256.

    The Drive 4 Growth library is editable by anyone with its link, so the
    bytes are checked at release and never trusted for where they live. The
    files must be fresh downloads of each asset url made just before release.
    """
    paths = [Path(p) for p in paths]
    if len(paths) != len(slot['assets']):
        raise ValueError(slot['slot_id'] + ': expected ' + str(len(slot['assets'])) + ' asset files')
    for asset, path in zip(slot['assets'], paths):
        if not path.is_file():
            raise ValueError(slot['slot_id'] + ': missing asset file ' + asset['name'])
        data = path.read_bytes()
        if len(data) != asset['bytes'] or hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError(slot['slot_id'] + ': asset bytes differ from the signed slot: ' + asset['name'])
    return True


# Live Buffer state ---------------------------------------------------------

def _post(value):
    if isinstance(value, dict) and 'status' not in value and isinstance(value.get('post'), dict):
        return value['post']
    return value


def service_meta(post, service):
    """The post's metadata for one service, keyed or flat as the readback gives it."""
    meta = post.get('metadata') or {}
    if not isinstance(meta, dict):
        return {}
    keyed = meta.get(service)
    return keyed if isinstance(keyed, dict) else meta


def resolve_channel(slot, channels):
    """This engine's one Buffer channel for the slot, pinned by service, name and channelId."""
    if isinstance(channels, dict):
        channels = channels.get('channels')
    service = CHANNELS[slot['channel']][0]
    name = BUFFER_NAME[slot['channel']]
    found = [c for c in (channels or []) if isinstance(c, dict) and c.get('service') == service
             and c.get('name') == name]
    if not found:
        raise ValueError('no Buffer channel ' + service + '/' + name + ' in the list_channels readback; never guess')
    if len(found) > 1:
        raise ValueError('more than one Buffer channel for ' + service + '; name the one intended')
    channel = found[0]
    if not (isinstance(channel.get('id'), str) and BUFFER_ID.match(channel['id'])):
        raise ValueError('Buffer channelId is malformed in the list_channels readback')
    errors = channel_id_errors(slot['channel'], channel['id'])
    if errors:
        raise ValueError(errors[0] + '; never guess')
    if channel.get('isDisconnected') or channel.get('isLocked'):
        raise ValueError('Buffer channel for ' + service + ' is disconnected or locked')
    return channel


def target_errors(slot, target, channel_id):
    """F01 groundwork: an edit acts only on the intended, still-draft post."""
    target = _post(target)
    if not isinstance(target, dict):
        return ['edit target was not read back with get_post']
    out = []
    if target.get('id') != slot['buffer_draft_id']:
        out.append('edit target is not the signed draft')
    if target.get('channelService') != CHANNELS[slot['channel']][0]:
        out.append('edit target is on another service')
    if target.get('channelId') != channel_id:
        out.append('edit target is on another Buffer channel')
    if target.get('status') != 'draft':
        out.append('edit target is not a draft')
    if target.get('via') == 'network':
        out.append('edit target was imported from the network')
    return out


def _carried(slot, target):
    """Alt text per signed asset url and the AI label stored on the target
    draft, which a whole-post edit would otherwise drop. Raises a hold."""
    alts, unmatched = {}, False
    urls = [a['url'] for a in slot['assets']]
    for asset in (target or {}).get('assets') or []:
        alt = ((asset or {}).get('image') or {}).get('altText') if isinstance(asset, dict) else None
        if not alt:
            continue
        if asset.get('source') in urls:
            alts[asset['source']] = alt
        else:
            unmatched = True
    if unmatched:
        raise ValueError(DROP_HOLD)
    service = CHANNELS[slot['channel']][0]
    ai = target is not None and service_meta(target, service).get('isAiGenerated') is True
    video = any(media_kind(a) == 'video' for a in slot['assets'])
    if ai and not (service in ('instagram', 'twitter') or (service == 'tiktok' and video)):
        # F02: a TikTok photo post can never carry it, so the edit holds.
        raise ValueError(DROP_HOLD)
    return alts, ai


# Exact call arguments ------------------------------------------------------

def _asset_input(asset, alts):
    kind = media_kind(asset)
    if kind == 'document':
        raise ValueError('document assets are held: Buffer lost a saved PDF preview (buffer-document-preview-hold)')
    body = {'url': asset['url']}
    if kind == 'image' and alts.get(asset['url']):
        body['metadata'] = {'altText': alts[asset['url']]}
    return {kind: body}


def _metadata(slot, ai=False):
    channel, fmt = slot['channel'], slot['format']
    video = any(media_kind(a) == 'video' for a in slot['assets'])
    if channel == 'instagram':
        kind = 'story' if fmt == 'story' else 'reel' if video else 'post'
        # Never `link` (F09). An AI label is only ever the stored one carried forward.
        meta = {'type': kind, 'shouldShareToFeed': kind != 'story'}
        if ai:
            meta['isAiGenerated'] = True
        return {'instagram': meta}
    if channel == 'facebook':
        return {'facebook': {'type': 'story' if fmt == 'story' else 'reel' if video else 'post'}}
    if channel == 'threads':
        return {'threads': {'type': 'post'}}
    if ai and channel == 'x':
        return {'twitter': {'isAiGenerated': True}}
    if ai and channel == 'tiktok' and video:
        return {'tiktok': {'isAiGenerated': True}}
    # TikTok photo posts never carry isAiGenerated (F02); Notes and LinkedIn
    # need no metadata, and a link preview is never attached.
    return None


def call_arguments(slot, channel, now=None, target=None, formats=None):
    """The one exact Buffer call for a checked slot, or a ValueError hold.

    channel is this slot's entry from a live list_channels readback; target
    is a fresh get_post of buffer_draft_id, required for every edit.
    """
    sid = slot['slot_id']
    service = CHANNELS[slot['channel']][0]
    if slot['channel'] == 'youtube':
        raise ValueError('youtube needs a signed title and categoryId, which the slot does not carry')
    if slot['link_placement'] not in EXPRESSIBLE_LINK_PLACEMENTS:
        raise ValueError('link_placement not expressible as one Buffer call: ' + slot['link_placement'])
    kinds = {media_kind(a) for a in slot['assets']}
    if slot['channel'] in NO_MIXED_MEDIA and {'image', 'video'} <= kinds:
        raise ValueError('mixed images and video are held for ' + slot['channel'])
    for asset in slot['assets']:
        if asset['url'] is None:
            raise ValueError('asset has no public url yet: ' + asset['name'])
    if not isinstance(channel, dict) or channel.get('service') != service \
            or not (isinstance(channel.get('id'), str) and BUFFER_ID.match(channel['id'])):
        raise ValueError('Buffer channel must be the live ' + service + ' entry from list_channels')
    pinned = channel_id_errors(slot['channel'], channel['id'])
    if pinned:
        raise ValueError(pinned[0])
    draft = is_draft(slot)
    if not draft and instant(slot['due_at']) <= instant(now):
        raise ValueError('due_at is not in the future')
    args, alts, ai = {}, {}, False
    if slot['buffer_draft_id']:
        tool = 'edit_post'
        errors = target_errors(slot, target, channel['id'])
        if errors:
            raise ValueError('; '.join(errors))
        alts, ai = _carried(slot, _post(target))
        args['postId'] = slot['buffer_draft_id']
    else:
        tool = 'create_post'
        args['channelId'] = channel['id']
    # F01: an edit always carries the complete payload, never scheduling alone.
    args['text'] = slot['words']
    args['assets'] = [_asset_input(a, alts) for a in slot['assets']]
    meta = _metadata(slot, ai)
    if meta:
        args['metadata'] = meta
    if draft:
        # F13: a draft sets saveToDraft and carries no dueAt and no mode.
        args['saveToDraft'] = True
        if tool == 'create_post':
            args['schedulingType'] = 'automatic'
    else:
        args.update({'mode': 'customScheduled', 'schedulingType': 'automatic',
                     'saveToDraft': False, 'dueAt': slot['due_at']})
    call = {'server': SERVER, 'tool': tool, 'slot_id': sid, 'payload_sha256': slot['payload_sha256'],
            'service': service, 'channel_id': channel['id'], 'arguments': args}
    errors = argument_errors(call, slot, formats)
    if errors:
        raise ValueError('; '.join(errors))
    return call


def _has_null_link_attachment(value):
    if isinstance(value, dict):
        if 'linkAttachment' in value and value['linkAttachment'] is None:
            return True
        return any(_has_null_link_attachment(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_null_link_attachment(v) for v in value)
    return False


def copy_errors(text, applies_to='channel_copy'):
    """The copy lint on one post's words, as refusals; an unreadable lint refuses too."""
    try:
        return copy_lint_errors(text, applies_to)
    except ValueError as exc:
        return ['copy lint could not run, so nothing releases: ' + str(exc)]


def media_copy_errors(args):
    """The copy lint on the public words a call's assets and metadata carry, besides its text.

    An image's alt text carries the picture's words, so it is read as carousel_text; a
    document or metadata title is read as titles. Alt text carried forward from a stored
    draft is public too, so a name in it holds the slot like a name in the text
    (Krish, 2026-10-28: "no content refers to Krish, ever").
    """
    out = []
    for asset in args.get('assets') or []:
        for kind, body in (asset.items() if isinstance(asset, dict) else ()):
            if not isinstance(body, dict):
                continue
            alt = (body.get('metadata') or {}).get('altText') if isinstance(body.get('metadata'), dict) else None
            if isinstance(alt, str):
                out += ['alt text ' + e for e in copy_errors(alt, 'carousel_text')]
            if isinstance(body.get('title'), str):
                out += [kind + ' title ' + e for e in copy_errors(body['title'], 'titles')]
    for service, meta in (args.get('metadata') or {}).items():
        if isinstance(meta, dict) and isinstance(meta.get('title'), str):
            out += [service + ' title ' + e for e in copy_errors(meta['title'], 'titles')]
    return out


def snackable_formats():
    """format id -> snackable, from the social records; None when they cannot be read."""
    try:
        return {fid: record.get('snackable') is True for fid, record in inventory()['format'].items()}
    except (ValueError, KeyError, OSError, TypeError):
        return None


def share_ask_errors(slot, text, formats=None):
    """Share asks in a snackable slot's words, as refusals (R99); a check that cannot run refuses too.

    Run lint and social preflight refuse them first; release checks the signed
    words again, as it does the copy lint, because it never reads lint.json.
    """
    formats = snackable_formats() if formats is None else formats
    if formats is None or slot['format'] not in formats:
        return ['share asks could not be checked, so nothing releases: no social format record for '
                + str(slot['format'])]
    try:
        if not cta_applies(formats[slot['format']]):
            return []
        return ['share call to action ' + e for e in cta_errors(text)]
    except ValueError as exc:
        return ['share asks could not be checked, so nothing releases: ' + str(exc)]


def argument_errors(call, slot, formats=None):
    """Guards on any Buffer call, however it was built. formats: snackable_formats(), read once by a plan."""
    args = call.get('arguments', {})
    meta = args.get('metadata') or {}
    service = call.get('service', CHANNELS[slot['channel']][0])
    out = []
    if call.get('tool') not in ('create_post', 'edit_post'):
        out.append('only create_post or edit_post is emitted')
    named = [c for c in (call.get('channel_id'), args.get('channelId')) if c is not None]
    if call.get('tool') == 'create_post' and 'channelId' not in args:
        out.append('a create_post names its pinned Buffer channelId')
    if not named:
        out.append('the call names no Buffer channel; release only acts on a pinned channel')
    for i, channel_id in enumerate(named):
        if channel_id not in named[:i]:
            out += channel_id_errors(slot['channel'], channel_id)
    if 'text' in args:
        out += copy_errors(args['text'])
        out += share_ask_errors(slot, args['text'], formats)
    out += media_copy_errors(args)
    if service != CHANNELS[slot['channel']][0]:
        out.append('the call is for another service than the slot')
    if args.get('mode') not in (None, 'customScheduled'):
        out.append('release uses an exact customScheduled time, never a queue or immediate mode')
    if call.get('tool') == 'edit_post' and ('text' not in args or 'assets' not in args
                                            or (_metadata(slot) and 'metadata' not in args)):
        out.append('an edit must send the complete payload, never a scheduling-only edit')
    if args.get('saveToDraft') is True and ('dueAt' in args or 'mode' in args):
        out.append('a draft save carries no dueAt and no mode')
    if args.get('saveToDraft') is not True and ('dueAt' not in args or args.get('mode') != 'customScheduled'):
        out.append('a scheduled release needs customScheduled and an exact dueAt; never rely on the default queue')
    if slot['publish_mode'] == 'krish_click' and (args.get('saveToDraft') is not True or 'dueAt' in args):
        out.append('a krish_click slot only ever gets an unscheduled draft')
    if (service == 'linkedin' or slot['channel'] in KRISH_CLICK_ONLY) and args.get('saveToDraft') is not True:
        out.append('LinkedIn is only ever an unscheduled draft; Krish makes the final click')
    if _has_null_link_attachment(args):
        out.append('a link preview is never cleared with linkAttachment null; use preview_clear_hold')
    if 'link' in (meta.get('instagram') or {}) or 'stickerFields' in (meta.get('instagram') or {}):
        out.append('an Instagram Story link sticker is never set or claimed automatic')
    if args.get('schedulingType') not in (None, 'automatic'):
        out.append('an engine release is automatic, never a notification post')
    tiktok_photo = slot['channel'] == 'tiktok' and not any(media_kind(a) == 'video' for a in slot['assets'])
    if tiktok_photo and 'isAiGenerated' in (meta.get('tiktok') or {}):
        out.append('TikTok photo posts never set the AI-generated flag')
    if slot['format'] == 'story' and len(args.get('assets', [])) != 1:
        out.append('a Story is one frame per post')
    return out


def preview_clear_hold(slot):
    """F03: clearing a saved link preview is never linkAttachment null through
    the domain tool. Hold, naming the introspected mutation route."""
    return {'slot_id': slot['slot_id'], 'hold': 'preview_clear_needs_introspected_mutation',
            'post_id': slot['buffer_draft_id'], 'route': dict(PREVIEW_CLEAR_ROUTE),
            'schema_checked': SCHEMA_CHECKED,
            'before': 'inspect the live schema and read back get_post first; one bounded attempt, never a blind retry'}


def stored_link_preview(slot, post):
    return bool(service_meta(post, CHANNELS[slot['channel']][0]).get('linkAttachment'))


# Plan ----------------------------------------------------------------------

def decision_digest(decision):
    return sha256_hex(decision.get('slots'))


def concept_only(spec, decision):
    """Whether this run's authority is the week's approved mix plan alone, with no go-live decision.

    decision.json then has proposal_id and decision null and slots {}, and the
    signature names no go-live (docs/CONCEPT-MANIFEST.md). Only posts made from
    an approved concept can release; nothing else is signed."""
    signature = spec.get('signature') or {}
    return (isinstance(decision, dict) and decision.get('proposal_id') is None and decision.get('decision') is None
            and 'go_live_proposal_id' in signature and signature['go_live_proposal_id'] is None)


def _signed_digests(spec, decision):
    if concept_only(spec, decision):
        if decision.get('run_id') != spec.get('run_id'):
            raise ValueError('decision belongs to another run')
        if decision.get('slots') != {} or decision.get('amended'):
            raise ValueError('a concept-only decision signs no slot of its own')
        if (spec.get('signature') or {}).get('decision_digest') != decision_digest(decision):
            raise ValueError('decision does not match the signed decision_digest')
        if not decision.get('concepts'):
            raise ValueError('no approved go-live decision and no approved concept: nothing releases')
        concept_problem = concept_rules.decision_errors(spec, decision)
        if concept_problem:
            raise ValueError(concept_problem)
        return {}
    if not isinstance(decision, dict) or decision.get('decision') != 'approved':
        raise ValueError('no approved go-live decision: nothing releases')
    if decision.get('run_id') != spec.get('run_id'):
        raise ValueError('decision belongs to another run')
    slots = decision.get('slots')
    if not isinstance(slots, dict):
        raise ValueError('decision must map each signed slot_id to its payload_sha256')
    signature = spec.get('signature') or {}
    if not signature.get('go_live_proposal_id') or not signature.get('decision_digest'):
        raise ValueError('run spec is not signed: it needs go_live_proposal_id and decision_digest')
    if signature['go_live_proposal_id'] != decision.get('proposal_id'):
        raise ValueError('decision is for another go-live proposal')
    if signature['decision_digest'] != decision_digest(decision):
        raise ValueError('decision does not match the signed decision_digest')
    concept_problem = concept_rules.decision_errors(spec, decision)
    if concept_problem:
        raise ValueError(concept_problem)
    return slots


STOP_UNRESOLVED = 'concept_stop_unresolved'


def authorised_digests(spec, decision, signed, stopped_proposals=(), unresolved_stops=(), formats=None):
    """(slot_id -> digest that may release, slot_id -> hold reason) from signed digests and approved concepts.

    A slot signed one by one keeps its digest unless Krish stopped its concept; a
    slot with no digest of its own is covered by its approved concept only while
    it matches the concept's mock and claim (engine/concepts.py, R101). While a
    decline in the loop's go-live ledger is not yet matched to its plan
    (unresolved_stops), it may be a stop on the mix plan, so every post made from
    a concept holds: unknown never releases.
    """
    out, reasons = {}, {}
    for slot in spec['slots']:
        sid = slot['slot_id']
        cid = slot.get('concept_id')
        if cid and concept_rules.stopped(decision, cid, stopped_proposals, spec.get('signature')):
            reasons[sid] = concept_rules.STOPPED + ': Krish stopped concept ' + cid + ', so none of its posts go out'
            continue
        if cid and unresolved_stops:
            reasons[sid] = (STOP_UNRESOLVED + ': ' + str(len(unresolved_stops)) + ' decline(s) in the go-live ledger'
                            ' are not yet matched to their plan, so any of them may stop concept ' + cid)
            continue
        if sid in signed:
            out[sid] = signed[sid]
            continue
        if cid:
            digest, reason = concept_rules.authority(spec, slot, decision, stopped_proposals, formats)
            if digest:
                out[sid] = digest
            else:
                reasons[sid] = reason
    return out, reasons


def approved_creative(spec):
    """Asset hashes in the manifest of an input that names its creative approval.

    New creative needs Krish's approval before use (docs/PUBLISHING-AUTHORITY.md),
    so a manifest without a creative_approval_ref approves nothing.
    """
    approved = set()
    for item in spec.get('inputs') or []:
        if not isinstance(item, dict) or not item.get('creative_approval_ref'):
            continue
        manifest = item.get('manifest')
        for entry in (manifest.get('files') if isinstance(manifest, dict) else None) or []:
            if isinstance(entry, dict) and isinstance(entry.get('sha256'), str) and HEX64.match(entry['sha256']):
                approved.add(entry['sha256'])
    return approved


def route_holds(slot, as_of):
    """(holds, known, since): social.route's capability holds for the slot's channel and format.

    known is False when the route cannot be read at all (a format the channel
    does not carry, or a broken social/ record); such a slot always holds.
    since is the date its capability record was last verified, or None.
    """
    try:
        decision = route(CHANNEL_PROFILE[slot['channel']], slot['format'], as_of=as_of)
    except (ValueError, KeyError) as exc:
        return ['route_unknown: ' + str(exc)], False, None
    record = decision.get('known_capability') or {}
    return decision['holds'], True, record.get('verified_at')


def capability_checks(spec, signed, ledger=None):
    """(channel, format) -> slot_id of the route's capability check in this run.

    On a route not yet verified in social/tools/buffer.json, that one post is
    the route's capability check (docs/PUBLISHING-AUTHORITY.md, 28 October):
    the check this run's ledger already released, else the earliest signed,
    scheduled slot on the route, so a slot signed later never becomes a second check.
    """
    scheduled = [s for s in spec['slots'] if not is_draft(s) and signed.get(s['slot_id']) == s['payload_sha256']]
    first = {}
    slots = {s['slot_id']: s for s in spec['slots']}
    for sid, entry in sorted(((ledger or {}).get('released') or {}).items()):
        if isinstance(entry, dict) and entry.get('capability_check') is True:
            slot = slots.get(sid) or entry
            if isinstance(slot.get('channel'), str) and isinstance(slot.get('format'), str):
                first.setdefault((slot['channel'], slot['format']), sid)
    for slot in sorted(scheduled, key=lambda s: instant(s['due_at'])):
        first.setdefault((slot['channel'], slot['format']), slot['slot_id'])
    return first


def other_capability_checks(root, run_id):
    """Capability checks released in other runs' ledgers under .scratch/runs, as dicts.

    A ledger that cannot be read refuses the plan: without it no route can say
    whether its check is still waiting to be recorded as passed.
    """
    base = Path(root) / '.scratch' / 'runs'
    own = safe_name(run_id)
    found = []
    for path in sorted(base.glob('*/ledger.json')) if base.is_dir() else []:
        if path.parent.name == own:
            continue
        try:
            ledger = read_json(path)
            released = ledger['released']
            if not isinstance(released, dict):
                raise TypeError('released is not a map')
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise ValueError('another run\'s release ledger cannot be read, so no route can tell whether its'
                             ' capability check is pending: ' + path.parent.name + ' (' + str(exc) + ')') from None
        if ledger.get('run_id') == run_id:
            continue  # this run's own ledger, which release_plan reads as its ledger
        for sid, entry in sorted(released.items()):
            if isinstance(entry, dict) and entry.get('capability_check') is True:
                found.append({'run_id': ledger.get('run_id'), 'slot_id': sid, 'channel': entry.get('channel'),
                              'format': entry.get('format'), 'planned_at': entry.get('planned_at')})
    return found


def pending_check(key, other_checks, since):
    """Another run's capability check on this route that the route's record has not caught up with.

    A check planned on or before the record's last verified date is what that
    record already settled. A check whose format or date was not recorded
    counts as pending: unknown never releases.
    """
    for check in other_checks or []:
        if check.get('channel') != key[0] or check.get('format') not in (key[1], None):
            continue
        try:
            planned = instant(check['planned_at']).date().isoformat()
        except (KeyError, TypeError, ValueError):
            planned = None
        if since and planned and planned <= since:
            continue
        return check
    return None


def day_of(entry):
    """The New York day a scheduled release lands on, from its due_at (planned_at for an older entry)."""
    when = entry.get('due_at') or entry.get('planned_at')
    try:
        return ny_time(when).date().isoformat() if when else None
    except (ValueError, TypeError):
        return None


def concept_caps(urgency=None, root=ROOT):
    """channel -> scheduled posts a New York day may carry (engine/intensity.py), None when unknown."""
    try:
        records = inventory(root)['channel']
    except (ValueError, KeyError, OSError, TypeError):
        return {}
    return {c: intensity.daily_cap(records.get(c), urgency, root) for c in concept_rules.CONCEPT_CHANNELS}


def release_plan(spec, decision, ledger=None, asset_paths=None, channels=None, now=None, targets=None,
                 other_checks=None, stopped_proposals=(), unresolved_stops=(), reviews=None, caps=None,
                 other_scheduled=None):
    """Arguments for signed, unreleased slots only, once per slot.

    asset_paths maps slot_id to its ordered local files; without them a slot
    with assets is held, because its bytes cannot be checked. channels is the
    live list_channels readback; targets maps slot_id to a fresh get_post of
    its buffer_draft_id. other_checks lists the capability checks other runs
    released (other_capability_checks). Returns calls, holds and the updated
    ledger; the caller saves the ledger.

    A post its concept authorises (no digest of Krish's own) also needs, in
    reviews (slot_id -> review/<slot>.json), a passing review at its
    payload_sha256, the creative bar, and room under its channel's daily cap
    (caps, channel -> posts a New York day; default concept_caps()), counted
    over this run's ledger, other runs' scheduled releases (other_scheduled,
    a list of {channel, due_at}) and the posts Krish signed one by one in this
    spec. Either missing holds the post: his signature is no longer the cap.
    """
    if not isinstance(spec, dict) or not isinstance(spec.get('slots'), list):
        raise ValueError('run spec needs a slots list')
    signed = _signed_digests(spec, decision)
    ledger = json.loads(json.dumps(ledger)) if ledger else {'run_id': spec['run_id'], 'released': {}}
    if ledger.get('run_id') != spec['run_id']:
        raise ValueError('ledger belongs to another run')
    asset_paths = asset_paths or {}
    targets = targets or {}
    approved = approved_creative(spec)
    seen = set()
    for slot in spec['slots']:
        check_slot(slot)
        if slot['slot_id'] in seen:
            raise ValueError('duplicate slot_id: ' + slot['slot_id'])
        seen.add(slot['slot_id'])
    by_krish = dict(signed)
    try:
        format_records = inventory()['format']
    except (ValueError, KeyError, OSError, TypeError):
        format_records = None
    signed, concept_holds = authorised_digests(spec, decision, signed, stopped_proposals, unresolved_stops,
                                               format_records)
    concepts = concept_rules.by_id(spec)
    reviews = reviews or {}
    caps = concept_caps() if caps is None else caps
    # Scheduled posts per (channel, New York day): other runs, this run's ledger, and every post Krish
    # signed one by one in this spec, reserved first so a concept post never takes his place.
    per_day = {}
    released_here = ledger['released']
    scheduled = list(other_scheduled or []) + [e for e in released_here.values() if isinstance(e, dict)
                                                and e.get('scheduled') is not False]
    for slot in spec['slots']:
        if by_krish.get(slot['slot_id']) == slot['payload_sha256'] and slot['slot_id'] not in released_here \
                and not is_draft(slot) and slot['due_at']:
            scheduled.append({'channel': slot['channel'], 'due_at': slot['due_at']})
    for entry in scheduled:
        day = day_of(entry)
        if day and entry.get('channel'):
            per_day[(entry['channel'], day)] = per_day.get((entry['channel'], day), 0) + 1
    as_of = instant(now).date().isoformat()
    first_post, routes = capability_checks(spec, signed, ledger), {}
    formats = snackable_formats()
    calls, holds = [], []
    for slot in spec['slots']:
        sid = slot['slot_id']

        def hold(reason):
            holds.append({'slot_id': sid, 'hold': reason})

        if sid in concept_holds:
            hold(concept_holds[sid])
            continue
        if signed.get(sid) != slot['payload_sha256']:
            hold('unsigned_or_changed_since_signing' if sid not in signed else 'payload_does_not_match_signed_digest')
            continue
        done = ledger['released'].get(sid)
        if done:
            hold('already_released_once' if done.get('payload_sha256') == slot['payload_sha256']
                 else 'released_earlier_with_another_payload')
            continue
        lint = copy_errors(slot['words'])
        if lint:
            # Krish, 28 Oct 2026: no eyebrows, asterisks, AI notes or take labels.
            hold('copy_lint_refused: ' + '; '.join(lint))
            continue
        asks = share_ask_errors(slot, slot['words'], formats)
        if asks:
            # Krish, 28 Oct 2026: a snackable post is shared for a reason, never asked for the share.
            hold('share_cta_refused: ' + '; '.join(asks))
            continue
        capability_check = False
        if not is_draft(slot):
            key = (slot['channel'], slot['format'])
            if key not in routes:
                routes[key] = route_holds(slot, as_of)
            unchecked, known, since = routes[key]
            if not known:
                hold(unchecked[0])
                continue
            pending = pending_check(key, other_checks, since) if unchecked else None
            if pending:
                # "until a route has passed it, the route holds": across runs, not only within one.
                hold('route_capability_check_pending: ' + str(pending.get('run_id')) + ' released '
                     + str(pending.get('slot_id')) + " as this route's capability check; nothing else on the route"
                     ' releases until social/tools/buffer.json records the route as passed')
                continue
            if unchecked and first_post.get(key) != sid:
                # Krish, 28 Oct 2026: each route's first real post is its capability
                # check; until the route has passed it, the rest of the route holds.
                hold('route_not_verified: ' + '; '.join(unchecked) + '; its capability check is '
                     + first_post[key] + ', and the rest wait until the route is recorded as passed')
                continue
            capability_check = bool(unchecked)
        mocks = set()
        if slot.get('concept_id') in concepts and (decision.get('concepts') or {}).get(slot['concept_id']) \
                == concepts[slot['concept_id']].get('concept_sha256'):
            mocks = set(concepts[slot['concept_id']]['mock_sha256'])  # his concept approval approved its mock
        if slot['publish_mode'] == 'engine' and any(a['sha256'] not in approved | mocks for a in slot['assets']):
            hold('creative_not_approved')
            continue
        by_concept = sid not in by_krish
        if by_concept:
            # The creative bar on a post with no digest of his own: a passing review at this payload.
            from engine.run.spec import review_reason
            reason = review_reason(slot, reviews.get(sid), snack=bool((formats or {}).get(slot['format'])))
            if reason:
                hold('concept_post_not_reviewed: ' + reason)
                continue
            if not is_draft(slot):
                cap = caps.get(slot['channel'])
                # The plan he approved states the most a day per channel; release keeps under it too.
                stated = (decision.get('concept_daily_caps') or {}).get(slot['channel'], cap)
                if isinstance(cap, int) and not isinstance(cap, bool):
                    cap = min(cap, stated) if isinstance(stated, int) and not isinstance(stated, bool) else None
                key = (slot['channel'], day_of({'due_at': slot['due_at']}))
                if not isinstance(cap, int) or isinstance(cap, bool) or key[1] is None:
                    hold('concept_daily_cap_unknown: ' + slot['channel'] + ' has no readable daily cap')
                    continue
                if per_day.get(key, 0) >= cap:
                    hold('concept_daily_cap_reached: ' + slot['channel'] + ' already has ' + str(per_day[key])
                         + ' scheduled on ' + key[1] + ' (New York), at most ' + str(cap) + ' a day')
                    continue
        if slot['assets']:
            if sid not in asset_paths:
                hold('asset_bytes_not_checked')
                continue
            try:
                verify_asset_bytes(slot, asset_paths[sid])
            except ValueError as exc:
                hold(str(exc))
                continue
        target = _post(targets.get(sid)) if slot['buffer_draft_id'] else None
        try:
            channel = resolve_channel(slot, channels)
            if slot['buffer_draft_id'] and not target_errors(slot, target, channel['id']) \
                    and stored_link_preview(slot, target):
                # F03: the saved preview is cleared only through the mutation route.
                if slot['assets'] or slot['link_placement'] in (None, 'none'):
                    holds.append(preview_clear_hold(slot))
                else:
                    hold('edit_would_drop_link_preview')
                continue
            call = call_arguments(slot, channel, now, target, formats)
        except ValueError as exc:
            hold(str(exc))
            continue
        calls.append(call)
        entry = {'payload_sha256': slot['payload_sha256'], 'tool': call['tool'], 'channel': slot['channel'],
                 'format': slot['format'], 'service': call['service'], 'channel_id': call['channel_id'],
                 'post_id': slot['buffer_draft_id'], 'planned_at': instant(now).isoformat(),
                 'copy_lint_version': copy_lint_version()}
        if not is_draft(slot):
            # The day it lands on, so the daily cap counts it in every later plan (R102).
            entry['due_at'] = slot['due_at']
            if by_concept:
                key = (slot['channel'], day_of(entry))
                per_day[key] = per_day.get(key, 0) + 1
        else:
            entry['scheduled'] = False
        if slot.get('concept_id'):
            # Outcomes are learned per concept and lane (engine/mix.py learn).
            entry['concept_id'] = slot['concept_id']
            entry['concept_sha256'] = concepts.get(slot['concept_id'], {}).get('concept_sha256')
        if capability_check:
            # The route's first real post: its readback is the capability check.
            call['capability_check'] = entry['capability_check'] = True
        if target is not None:
            # The before-state, journalled ahead of the mutation.
            entry['target_sha256'] = _readback_digest(target)
        ledger['released'][sid] = entry
    return {'calls': calls, 'holds': holds, 'ledger': ledger}


# Readback ------------------------------------------------------------------

def _readback_digest(post):
    return hashlib.sha256(json.dumps(post, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def check_readback(slot, post, stage, ledger, accounts=None):
    """Evidence from one get_post readback of a post in the release ledger.
    queued proves only a queue state; live needs status sent and an https
    native URL on the expected host and account."""
    check_slot(slot)
    post = _post(post)
    sid = slot['slot_id']
    service = CHANNELS[slot['channel']][0]
    if stage not in ('queued', 'live'):
        raise ValueError('stage must be queued or live')
    if not isinstance(post, dict) or not isinstance(post.get('id'), str):
        raise ValueError(sid + ': readback is not a Buffer post')
    if post.get('via') == 'network':
        # F17: imported "sent via network" posts are not engine publications.
        raise ValueError(sid + ': post was imported from the network; not an engine publication')
    entry = ((ledger or {}).get('released') or {}).get(sid)
    if not entry:
        raise ValueError(sid + ': slot absent from the release ledger; not an engine publication')
    if entry.get('payload_sha256') != slot['payload_sha256']:
        raise ValueError(sid + ': ledger released another payload for this slot')
    if entry.get('post_id'):
        if entry['post_id'] != post['id']:
            raise ValueError(sid + ': readback post is not the one the engine released')
    elif stage == 'live':
        raise ValueError(sid + ': no queued readback bound this slot to a Buffer post; check queued first')
    elif post.get('via') != 'api':
        raise ValueError(sid + ': a created post is bound only when Buffer says it came via the api')
    if slot['buffer_draft_id'] and slot['buffer_draft_id'] != post['id']:
        raise ValueError(sid + ': readback post is not the signed draft')
    if not post.get('channelService'):
        raise ValueError(sid + ': readback has no channelService; read it back in full')
    if post['channelService'] != service:
        raise ValueError(sid + ': readback is on another service')
    if not post.get('channelId') or post['channelId'] != entry.get('channel_id'):
        raise ValueError(sid + ': readback is on another Buffer channel than the one released')
    pinned = channel_id_errors(slot['channel'], post['channelId'])
    if pinned:
        raise ValueError(sid + ': ' + pinned[0])
    if post.get('text') != slot['words']:
        raise ValueError(sid + ': readback text differs from the signed words')
    if len(post.get('assets') or []) != len(slot['assets']) and slot['format'] != 'story':
        raise ValueError(sid + ': readback asset count differs from the signed slot')
    meta = service_meta(post, service)
    if slot['format'] == 'story':
        story_frame(post, sid)
        if slot['channel'] in STORY_TYPED and meta.get('type') != 'story':
            raise ValueError(sid + ': readback is not stored as a Story')
    if slot['channel'] == 'instagram':
        stickers = meta.get('stickerFields') or {}
        if meta.get('link') or (isinstance(stickers, dict) and any(stickers.values())):
            # F09: a stored link sticker is never claimed automatic.
            raise ValueError(sid + ': an Instagram Story link sticker is never set or claimed automatic')
    if stored_link_preview(slot, post) and (slot['assets'] or slot['link_placement'] in (None, 'none')):
        raise ValueError(sid + ': the stored post still carries a link preview; clear it through '
                         + PREVIEW_CLEAR_ROUTE['mutation'] + ', never linkAttachment null')
    draft = is_draft(slot)
    if draft:
        if post.get('schedulingType') not in (None, 'automatic'):
            raise ValueError(sid + ': draft is stored as a notification post')
    elif post.get('schedulingType') != 'automatic':
        raise ValueError(sid + ': an engine release must be automatic, found '
                         + str(post.get('schedulingType')) + '; a notification post is never automatic')
    status = post.get('status')
    if status == 'error':
        raise ValueError(sid + ': Buffer reports an error; hold and diagnose, never retry blindly')
    if status == 'sending':
        raise ValueError(sid + ': still sending; uncertain, read back again later')
    native = None
    if stage == 'queued':
        if draft:
            if status != 'draft' or post.get('dueAt') is not None:
                raise ValueError(sid + ': expected an unscheduled draft')
        else:
            if status != 'scheduled':
                raise ValueError(sid + ': expected scheduled, found ' + str(status))
            if not post.get('dueAt') or instant(post['dueAt']) != instant(slot['due_at']):
                raise ValueError(sid + ': scheduled time differs from the signed due_at')
    else:
        # F08: scheduled is never sent.
        if status != 'sent':
            raise ValueError(sid + ': not live; status is ' + str(status) + ', and scheduled is never sent')
        native = post.get('externalLink')
        if not native_host(slot['channel'], native, (accounts or {}).get(slot['channel'])):
            raise ValueError(sid + ': live needs an https native URL on the ' + slot['channel'] + ' host and account')
    evidence = {'slot_id': sid, 'stage': stage, 'channel': slot['channel'], 'post_id': post['id'],
                'channel_id': post['channelId'], 'payload_sha256': slot['payload_sha256'], 'status': status,
                'due_at': post.get('dueAt'), 'sent_at': post.get('sentAt'), 'native_url': native,
                'via': post.get('via'), 'published': stage == 'live',
                'media_sources': [a.get('source') for a in post.get('assets') or [] if isinstance(a, dict)],
                'readback_sha256': _readback_digest(post)}
    if slot['channel'] == 'instagram' and slot['format'] == 'story':
        evidence['link_sticker'] = 'not_set_not_claimed'
    return evidence


def story_frame(post, sid='story'):
    """F14: one frame per Story post. Duplicate DOM or thumbnail copies are
    deduplicated by returned media URL, never by source file or frame."""
    urls = []
    for asset in post.get('assets') or []:
        url = (asset.get('source') or asset.get('url')) if isinstance(asset, dict) else None
        if not url:
            raise ValueError(sid + ': Story asset has no returned media URL')
        if url not in urls:
            urls.append(url)
    if len(urls) != 1:
        raise ValueError(sid + ': a Story post must hold exactly one frame, found ' + str(len(urls)))
    return urls[0]


def story_sequence(posts):
    """Ordered distinct frames of a Story sequence; a repeated frame is refused."""
    frames = []
    for i, post in enumerate(posts):
        url = story_frame(_post(post), 'story ' + str(i + 1))
        if url in frames:
            raise ValueError('story ' + str(i + 1) + ' repeats an earlier frame')
        frames.append(url)
    return frames


def engine_publications(posts, ledger, accounts=None):
    """Only posts the engine released count, and only once live with a
    native URL on their channel; imports and others never do."""
    entries = {e.get('post_id'): e for e in (ledger.get('released') or {}).values()
               if isinstance(e, dict) and e.get('post_id')}
    out = []
    for p in map(_post, posts):
        entry = entries.get(p.get('id')) if isinstance(p, dict) else None
        if not entry or p.get('via') == 'network' or p.get('status') != 'sent':
            continue
        channel = entry.get('channel')
        if channel not in CHANNELS or p.get('channelService') != CHANNELS[channel][0]:
            continue
        if channel_id_errors(channel, p.get('channelId')):
            continue
        if native_host(channel, p.get('externalLink'), (accounts or {}).get(channel)):
            out.append(p)
    return out


# Command line --------------------------------------------------------------

def _golive_ledger_part(root, key):
    path = Path(root) / '.scratch' / 'cc' / 'golive-ledger.json'  # engine/cc_loop.py GOLIVE_LEDGER
    if not path.exists():
        return ()
    try:
        part = read_json(path).get(key) or {}
        if not isinstance(part, dict):
            raise TypeError(key + ' is not a map')
    except (ValueError, TypeError, OSError, AttributeError) as exc:
        raise ValueError('the go-live ledger cannot be read, so no concept can tell whether Krish stopped it: '
                         + str(exc)) from None
    return tuple(sorted(part))


def stopped_plans(root):
    """Plan proposals Krish stopped, from the Control Center loop's local go-live ledger.

    A stop on the mix plan proposal stops every concept it carried (R101). A
    ledger that cannot be read refuses the plan: unknown never releases.
    """
    return _golive_ledger_part(root, 'stopped')


def unresolved_stops(root):
    """Declines in the go-live ledger not yet matched to their plan (control_center.golive_review).

    Any of them may be a stop on the mix plan, so while one is listed every
    post made from a concept holds."""
    return _golive_ledger_part(root, 'unresolved')


def other_scheduled(root, run_id):
    """Scheduled releases in other runs' ledgers, as {channel, due_at, planned_at}, for the daily cap.

    A ledger that cannot be read refuses the plan: without it no channel can
    say how many posts its day already carries."""
    base = Path(root) / '.scratch' / 'runs'
    found = []
    for path in sorted(base.glob('*/ledger.json')) if base.is_dir() else []:
        try:
            ledger = read_json(path)
            released = ledger['released']
            if not isinstance(released, dict):
                raise TypeError('released is not a map')
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise ValueError("another run's release ledger cannot be read, so no channel can count its day: "
                             + path.parent.name + ' (' + str(exc) + ')') from None
        if ledger.get('run_id') == run_id:
            continue
        for entry in released.values():
            if isinstance(entry, dict) and entry.get('scheduled') is not False:
                found.append({'channel': entry.get('channel'), 'due_at': entry.get('due_at'),
                              'planned_at': entry.get('planned_at')})
    return found


def run_reviews(spec, root):
    """slot_id -> its review/<slot>.json under the run's evidence folder (engine/run/spec.py run_dir)."""
    from engine.run.spec import run_dir
    folder = run_dir(spec, None, root) / 'review'
    out = {}
    for slot in spec['slots']:
        path = folder / (str(slot['slot_id']) + '.json')
        if path.is_file():
            try:
                out[slot['slot_id']] = read_json(path)
            except (ValueError, OSError):
                continue
    return out


def safe_name(value):
    """A file name; a changed name gains a short digest so names never collide."""
    raw = str(value)
    name = SAFE.sub('_', raw).strip('._')
    if not name:
        raise ValueError('cannot make a safe file name from ' + repr(value))
    if name != raw:
        name = name[:111] + '-' + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:8]
    return name[:120]


def scratch_path(root, path):
    base = (Path(root) / '.scratch').resolve()
    path = Path(path)
    path = (path if path.is_absolute() else Path(root) / path).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ValueError('release writes only under .scratch')
    return path


def _ordered_assets(spec, folder):
    if folder is None:
        return {}
    folder = Path(folder)
    return {s['slot_id']: [folder / a['name'] for a in s['assets']]
            for s in spec['slots'] if isinstance(s, dict) and isinstance(s.get('assets'), list)}


def _check_all(spec, readback, stage, ledger, accounts, now):
    slots = {s['slot_id']: s for s in spec.get('slots', []) if isinstance(s, dict) and 'slot_id' in s}
    if not isinstance(readback, dict) or not readback:
        raise ValueError('readback must map slot_id to its get_post result')
    results = []
    for sid, post in sorted(readback.items()):
        if sid not in slots:
            raise ValueError('readback names an unknown slot: ' + sid)
        evidence = check_readback(slots[sid], post, stage, ledger, accounts)
        evidence['run_id'] = spec['run_id']
        evidence['checked_at'] = instant(now).isoformat()
        results.append((sid, evidence))
    return results


def main(argv=None, root=None):
    root = Path(root) if root else ROOT
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['release']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='release', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan')
    p.add_argument('spec'); p.add_argument('--decision', required=True); p.add_argument('--ledger')
    p.add_argument('--assets', help='folder of fresh downloads of each asset url, made under .scratch just before release')
    p.add_argument('--channels', help='the live list_channels readback: a list of {id, service}')
    p.add_argument('--targets', help='slot_id to a fresh get_post of its buffer_draft_id')
    p.add_argument('--now')
    c = sub.add_parser('check')
    c.add_argument('spec'); c.add_argument('--readback', required=True)
    c.add_argument('--stage', required=True, choices=('queued', 'live'))
    c.add_argument('--ledger'); c.add_argument('--now')
    args = parser.parse_args(argv)
    try:
        spec = read_json(args.spec)
        if not isinstance(spec, dict) or not isinstance(spec.get('run_id'), str):
            raise ValueError('run spec needs a run_id')
        run_dir = Path('.scratch') / 'runs' / safe_name(spec['run_id'])
        ledger_path = scratch_path(root, run_dir / 'ledger.json')
        if args.ledger and scratch_path(root, args.ledger) != ledger_path:
            raise ValueError('the release ledger lives only at ' + str(run_dir / 'ledger.json'))
        with locked(ledger_path):
            ledger = read_json(ledger_path) if ledger_path.exists() else None
            if ledger is not None and ledger.get('run_id') != spec['run_id']:
                raise ValueError('ledger belongs to another run')
            if args.action == 'plan':
                result = release_plan(spec, read_json(args.decision), ledger, _ordered_assets(spec, args.assets),
                                      read_json(args.channels) if args.channels else None, args.now,
                                      read_json(args.targets) if args.targets else None,
                                      other_capability_checks(root, spec['run_id']), stopped_plans(root),
                                      unresolved_stops(root), run_reviews(spec, root),
                                      concept_caps(intensity.state(root)['urgency'], root),
                                      other_scheduled(root, spec['run_id']))
                if result['calls']:
                    write_json(ledger_path, result['ledger'])
                if result['holds']:
                    print(json.dumps({'holds': result['holds']}, indent=2), file=sys.stderr)
                print(json.dumps(result['calls'], ensure_ascii=False, indent=2))
                return 0
            if ledger is None:
                raise ValueError('no release ledger for this run: nothing here was released by the engine')
            results = _check_all(spec, read_json(args.readback), args.stage, ledger, load_accounts(), args.now)
            written = []
            for sid, evidence in results:
                entry = ledger['released'][sid]
                if not entry.get('post_id'):
                    entry['post_id'] = evidence['post_id']
                entry[args.stage + '_checked_at'] = evidence['checked_at']
                out = scratch_path(root, run_dir / args.stage / (safe_name(sid) + '.json'))
                write_json(out, evidence)
                written.append(str(out))
            write_json(ledger_path, ledger)
        print(json.dumps({'valid': True, 'stage': args.stage, 'written': written}, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
