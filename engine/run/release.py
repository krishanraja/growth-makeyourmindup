"""Release Gate: a signed run-spec slot becomes exact Buffer MCP call
arguments, and a Buffer readback becomes local evidence. Offline only.

This code never calls Buffer, Control Center or any network, and it never
schedules, sends or posts. A session passes the emitted arguments verbatim to
the named Buffer MCP tool, then feeds the get_post readback to `release check`.
Uncertain outcomes are held for a readback, never retried blindly.

Buffer schema facts relied on, read on 27 October 2026 with the read-only
introspect_schema and the create_post/edit_post/get_post tool definitions.
Recheck them before trusting this after a provider change:
- create_post requires channelId and schedulingType; edit_post requires postId.
  Both take text, assets, metadata, mode, dueAt and saveToDraft. GraphQL:
  createPost(input: CreatePostInput!) and editPost(input: EditPostInput!),
  both returning PostActionPayload.
- ShareMode: addToQueue, customScheduled, shareNext, shareNow. dueAt is ISO
  8601 with an offset, only valid with customScheduled, and must be in the
  future. SchedulingType: automatic, notification.
- Every edit_post is revalidated as a whole post, not merged with the stored
  one, and sending a mode reschedules it.
- An asset is exactly one of {image: {url, metadata: {altText}}},
  {video: {url}} or {document: {url, title, thumbnailUrl}} (LinkedIn only).
- Metadata: instagram {type story|reel|post, shouldShareToFeed (required),
  isAiGenerated, link (the Story link sticker)}; facebook {type post|reel|
  story}; tiktok {isAiGenerated (video only), title}; threads {type post|
  ghost_post}; youtube requires title and categoryId. The domain tool offers
  no null linkedin linkAttachment; GraphQL EditPostInput is the inspected
  clear route.
- PostStatus: draft, error, needs_approval, scheduled, sending, sent.
  PostVia: api, buffer, network. A Post carries externalLink and sentAt.
- Services used: substack, threads, twitter, instagram, facebook, tiktok,
  youtube, linkedin.

The decision file is Krish's recorded go-live decision for one run:
{"run_id", "proposal_id", "decision": "approved", "decided_at",
 "slots": {slot_id: payload_sha256}}. An amended slot carries his amended
digest, so the amended version is the one that releases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from engine.control_center import sha256_hex
from engine.core import instant, read_json, write_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_CHECKED = '2026-10-27'
SERVER = 'Buffer'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
BUFFER_ID = re.compile(r'^[a-f0-9]{24}$')
DUE_AT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$')
PLAY = re.compile(r'^P[1-9]$')
SAFE = re.compile(r'[^A-Za-z0-9._-]+')
SLOT_KEYS = {'slot_id', 'channel', 'format', 'play', 'due_at', 'words', 'assets', 'link_placement',
             'cta', 'forward_line', 'experiment_arm', 'publish_mode', 'buffer_draft_id', 'payload_sha256'}
ASSET_KEYS = {'name', 'sha256', 'url', 'bytes'}
DIGEST_KEYS = ('channel', 'format', 'words', 'link_placement', 'due_at', 'publish_mode')
# Channel id -> (Buffer service, native hosts). A leading dot allows subdomains.
CHANNELS = {
    'substack-notes': ('substack', ('substack.com', '.substack.com')),
    'threads': ('threads', ('threads.net', 'www.threads.net', 'threads.com', 'www.threads.com')),
    'x': ('twitter', ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com')),
    'instagram': ('instagram', ('instagram.com', 'www.instagram.com')),
    'facebook': ('facebook', ('facebook.com', 'www.facebook.com', 'm.facebook.com')),
    'tiktok': ('tiktok', ('tiktok.com', 'www.tiktok.com')),
    'youtube': ('youtube', ('youtube.com', 'www.youtube.com', 'm.youtube.com')),
    'linkedin': ('linkedin', ('linkedin.com', 'www.linkedin.com')),
}
KRISH_CLICK_ONLY = ('linkedin',)
MEDIA = {'.png': 'image', '.jpg': 'image', '.jpeg': 'image', '.gif': 'image', '.webp': 'image',
         '.mp4': 'video', '.mov': 'video', '.webm': 'video', '.pdf': 'document'}
NEEDS_MEDIA = ('instagram', 'tiktok', 'youtube')
PREVIEW_CLEAR_ROUTE = {
    'tool': 'execute_mutation', 'server': SERVER,
    'mutation': 'editPost(input: $input)', 'input_type': 'EditPostInput!',
    'returns': 'PostActionPayload: PostActionSuccess { post { id status dueAt } } or MutationError { message }',
}


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


def check_slot(slot):
    """Refuse a malformed slot or one whose stored digest is not its own."""
    if not isinstance(slot, dict) or set(slot) != SLOT_KEYS:
        raise ValueError('slot must carry exactly the run-spec slot fields')
    sid = slot['slot_id']
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError('slot_id is required')
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
        if not isinstance(asset['name'], str) or not asset['name'].strip() or Path(asset['name']).name != asset['name']:
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
    if slot['channel'] == 'instagram' and (slot['link_placement'] or '').replace('-', '_') == 'link_sticker':
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


def native_host(channel, url):
    if not https_url(url):
        return False
    host = urlsplit(url).hostname.lower()
    for allowed in CHANNELS[channel][1]:
        if host == allowed or (allowed.startswith('.') and host.endswith(allowed)):
            return True
    return False


def verify_asset_bytes(slot, paths):
    """Refuse unless every file, in order, has the signed bytes and sha256.

    The Drive 4 Growth library is editable by anyone with its link, so the
    bytes are checked at release and never trusted for where they live.
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


# Exact call arguments ------------------------------------------------------

def _asset_input(asset):
    kind = media_kind(asset)
    if kind == 'document':
        raise ValueError('document assets are held: Buffer lost a saved PDF preview (buffer-document-preview-hold)')
    return {kind: {'url': asset['url']}}


def _metadata(slot):
    channel, fmt = slot['channel'], slot['format']
    video = any(media_kind(a) == 'video' for a in slot['assets'])
    if channel == 'instagram':
        kind = 'story' if fmt == 'story' else 'reel' if video else 'post'
        # Never `link` (F09) and never an AI flag the slot does not sign.
        return {'instagram': {'type': kind, 'shouldShareToFeed': kind != 'story'}}
    if channel == 'facebook':
        return {'facebook': {'type': 'story' if fmt == 'story' else 'reel' if video else 'post'}}
    if channel == 'threads':
        return {'threads': {'type': 'post'}}
    # TikTok photo posts never carry isAiGenerated (F02); X, Notes and
    # LinkedIn need no metadata, and a link preview is never attached.
    return None


def call_arguments(slot, channel_id=None, now=None):
    """The one exact Buffer call for a checked slot, or a ValueError hold."""
    sid = slot['slot_id']
    if slot['channel'] == 'youtube':
        raise ValueError('youtube needs a signed title and categoryId, which the slot does not carry')
    for asset in slot['assets']:
        if asset['url'] is None:
            raise ValueError('asset has no public url yet: ' + asset['name'])
    draft = slot['publish_mode'] == 'krish_click' or slot['due_at'] is None
    if not draft and instant(slot['due_at']) <= instant(now):
        raise ValueError('due_at is not in the future')
    args = {}
    if slot['buffer_draft_id']:
        tool = 'edit_post'
        args['postId'] = slot['buffer_draft_id']
    else:
        tool = 'create_post'
        if not (isinstance(channel_id, str) and BUFFER_ID.match(channel_id)):
            raise ValueError('Buffer channelId unknown: read list_channels live; never guess')
        args['channelId'] = channel_id
    # F01: an edit always carries the complete payload, never scheduling alone.
    args['text'] = slot['words']
    args['assets'] = [_asset_input(a) for a in slot['assets']]
    meta = _metadata(slot)
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
    call = {'server': SERVER, 'tool': tool, 'slot_id': sid,
            'payload_sha256': slot['payload_sha256'], 'arguments': args}
    errors = argument_errors(call, slot)
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


def argument_errors(call, slot):
    """Guards on any Buffer call, however it was built."""
    args = call.get('arguments', {})
    meta = args.get('metadata') or {}
    out = []
    if call.get('tool') not in ('create_post', 'edit_post'):
        out.append('only create_post or edit_post is emitted')
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
    if _has_null_link_attachment(args):
        out.append('a link preview is never cleared with linkAttachment null; use preview_clear_hold')
    if 'link' in (meta.get('instagram') or {}) or 'stickerFields' in (meta.get('instagram') or {}):
        out.append('an Instagram Story link sticker is never set or claimed automatic')
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


# Plan ----------------------------------------------------------------------

def _signed_digests(spec, decision):
    if not isinstance(decision, dict) or decision.get('decision') != 'approved':
        raise ValueError('no approved go-live decision: nothing releases')
    if decision.get('run_id') != spec.get('run_id'):
        raise ValueError('decision belongs to another run')
    signature = spec.get('signature') or {}
    if signature.get('go_live_proposal_id') and signature['go_live_proposal_id'] != decision.get('proposal_id'):
        raise ValueError('decision is for another go-live proposal')
    slots = decision.get('slots')
    if not isinstance(slots, dict):
        raise ValueError('decision must map each signed slot_id to its payload_sha256')
    return slots


def release_plan(spec, decision, ledger=None, asset_paths=None, channel_ids=None, now=None):
    """Arguments for signed, unreleased slots only, once per slot.

    asset_paths maps slot_id to its ordered local files; without them a slot
    with assets is held, because its bytes cannot be checked. Returns calls,
    holds and the updated ledger; the caller saves the ledger.
    """
    if not isinstance(spec, dict) or not isinstance(spec.get('slots'), list):
        raise ValueError('run spec needs a slots list')
    signed = _signed_digests(spec, decision)
    ledger = json.loads(json.dumps(ledger)) if ledger else {'run_id': spec['run_id'], 'released': {}}
    if ledger.get('run_id') != spec['run_id']:
        raise ValueError('ledger belongs to another run')
    asset_paths = asset_paths or {}
    channel_ids = channel_ids or {}
    seen, calls, holds = set(), [], []
    for slot in spec['slots']:
        check_slot(slot)
        sid = slot['slot_id']
        if sid in seen:
            raise ValueError('duplicate slot_id: ' + sid)
        seen.add(sid)

        def hold(reason):
            holds.append({'slot_id': sid, 'hold': reason})

        if signed.get(sid) != slot['payload_sha256']:
            hold('unsigned_or_changed_since_signing' if sid not in signed else 'payload_does_not_match_signed_digest')
            continue
        done = ledger['released'].get(sid)
        if done:
            hold('already_released_once' if done.get('payload_sha256') == slot['payload_sha256']
                 else 'released_earlier_with_another_payload')
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
        try:
            call = call_arguments(slot, channel_ids.get(slot['channel']), now)
        except ValueError as exc:
            hold(str(exc))
            continue
        calls.append(call)
        ledger['released'][sid] = {'payload_sha256': slot['payload_sha256'], 'tool': call['tool'],
                                   'post_id': slot['buffer_draft_id'], 'planned_at': instant(now).isoformat()}
    return {'calls': calls, 'holds': holds, 'ledger': ledger}


# Readback ------------------------------------------------------------------

def _post(value):
    if isinstance(value, dict) and 'status' not in value and isinstance(value.get('post'), dict):
        return value['post']
    return value


def check_readback(slot, post, stage, ledger=None):
    """Evidence from one get_post readback. queued proves only a queue state;
    live needs status sent and an https native URL on the expected host."""
    check_slot(slot)
    post = _post(post)
    sid = slot['slot_id']
    if stage not in ('queued', 'live'):
        raise ValueError('stage must be queued or live')
    if not isinstance(post, dict) or not isinstance(post.get('id'), str):
        raise ValueError(sid + ': readback is not a Buffer post')
    if post.get('via') == 'network':
        # F17: imported "sent via network" posts are not engine publications.
        raise ValueError(sid + ': post was imported from the network; not an engine publication')
    if ledger is not None:
        entry = (ledger.get('released') or {}).get(sid)
        if not entry:
            raise ValueError(sid + ': slot absent from the release ledger; not an engine publication')
        if entry.get('post_id') and entry['post_id'] != post['id']:
            raise ValueError(sid + ': readback post is not the one the engine released')
    if slot['buffer_draft_id'] and slot['buffer_draft_id'] != post['id']:
        raise ValueError(sid + ': readback post is not the signed draft')
    if post.get('channelService') and post['channelService'] != CHANNELS[slot['channel']][0]:
        raise ValueError(sid + ': readback is on another service')
    if post.get('text') != slot['words']:
        raise ValueError(sid + ': readback text differs from the signed words')
    if len(post.get('assets') or []) != len(slot['assets']) and slot['format'] != 'story':
        raise ValueError(sid + ': readback asset count differs from the signed slot')
    if slot['format'] == 'story':
        story_frame(post, sid)
    status = post.get('status')
    if status == 'error':
        raise ValueError(sid + ': Buffer reports an error; hold and diagnose, never retry blindly')
    if status == 'sending':
        raise ValueError(sid + ': still sending; uncertain, read back again later')
    draft = slot['publish_mode'] == 'krish_click' or slot['due_at'] is None
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
        if not native_host(slot['channel'], native):
            raise ValueError(sid + ': live needs an https native URL on the ' + slot['channel'] + ' host')
    evidence = {'slot_id': sid, 'stage': stage, 'channel': slot['channel'], 'post_id': post['id'],
                'payload_sha256': slot['payload_sha256'], 'status': status, 'due_at': post.get('dueAt'),
                'sent_at': post.get('sentAt'), 'native_url': native, 'via': post.get('via'),
                'published': stage == 'live', 'readback_sha256': hashlib.sha256(json.dumps(
                    post, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()}
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


def engine_publications(posts, ledger):
    """Only posts the engine released count; imports and others never do."""
    ids = {entry.get('post_id') for entry in (ledger.get('released') or {}).values() if entry.get('post_id')}
    return [p for p in map(_post, posts)
            if p.get('id') in ids and p.get('via') != 'network' and p.get('status') == 'sent']


# Command line --------------------------------------------------------------

def safe_name(value):
    name = SAFE.sub('_', str(value)).strip('._')
    if not name:
        raise ValueError('cannot make a safe file name from ' + repr(value))
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


def main(argv=None, root=None):
    root = Path(root) if root else ROOT
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['release']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='release', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan')
    p.add_argument('spec'); p.add_argument('--decision', required=True); p.add_argument('--ledger')
    p.add_argument('--assets', help='folder holding each signed asset by name')
    p.add_argument('--channels', help='channel id to Buffer channelId, read live from list_channels')
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
        ledger_path = scratch_path(root, args.ledger or run_dir / 'ledger.json')
        ledger = read_json(ledger_path) if ledger_path.exists() else None
        if args.action == 'check' and ledger is None:
            raise ValueError('no release ledger for this run: nothing here was released by the engine')
        if args.action == 'plan':
            result = release_plan(spec, read_json(args.decision), ledger, _ordered_assets(spec, args.assets),
                                  read_json(args.channels) if args.channels else None, args.now)
            if result['calls']:
                write_json(ledger_path, result['ledger'])
            if result['holds']:
                print(json.dumps({'holds': result['holds']}, indent=2), file=sys.stderr)
            print(json.dumps(result['calls'], ensure_ascii=False, indent=2))
            return 0
        slots = {s['slot_id']: s for s in spec.get('slots', []) if isinstance(s, dict) and 'slot_id' in s}
        readback = read_json(args.readback)
        if not isinstance(readback, dict) or not readback:
            raise ValueError('readback must map slot_id to its get_post result')
        written = []
        for sid, post in sorted(readback.items()):
            if sid not in slots:
                raise ValueError('readback names an unknown slot: ' + sid)
            evidence = check_readback(slots[sid], post, args.stage, ledger)
            evidence['run_id'] = spec['run_id']
            evidence['checked_at'] = instant(args.now).isoformat()
            if args.stage == 'queued' and not ledger['released'][sid].get('post_id'):
                ledger['released'][sid]['post_id'] = evidence['post_id']
            out = scratch_path(root, run_dir / args.stage / (safe_name(sid) + '.json'))
            write_json(out, evidence)
            written.append(str(out))
        if args.stage == 'queued':
            write_json(ledger_path, ledger)
        print(json.dumps({'valid': True, 'stage': args.stage, 'written': written}, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
