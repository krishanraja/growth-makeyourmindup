"""Offline social operating contracts. No credentials, network or posting."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .buffer_channels import channel_id_errors
from .copy_lint import copy_lint_errors
from .share import (StaleSendTest, compare_send_test, cta_applies, cta_errors, load_rules as load_share_rules,
                    send_test_request, share_errors, stage_send_test)


ROOT = Path(__file__).resolve().parents[1]
# Built to be sent (Ruling, Krish, 2026-10-28): every snackable format names its
# share mechanic in its delivery checks and carries this lesson.
SHARE_MECHANIC = 'Share mechanic: '
SHARE_LESSON = 'built-to-be-sent'
# Personal accounts Krish has scoped for delegated cadence of approved content:
# X and TikTok (ruling of 26 Oct 2026) and Threads (ruling of 27 Oct 2026,
# CHANGES.md). Every other personal account stays human_publish_only.
DELEGATED_PERSONAL = ('x', 'tiktok', 'threads', 'substack-notes')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def validate(value, schema, at='$'):
    """Validate the deliberately small JSON Schema subset used here.

    Fail closed on unsupported keywords rather than silently skipping checks.
    The checked-in schemas are also usable by a full Draft 2020-12 validator.
    """
    supported = {'$schema', 'title', 'description', 'type', 'const', 'enum',
                 'properties', 'required', 'additionalProperties', 'items',
                 'minItems', 'uniqueItems', 'minLength', 'pattern', 'minimum',
                 'maximum', 'format'}
    if set(schema) - supported:
        raise ValueError(at + ': unsupported schema keyword')
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
               'string': isinstance(value, str), 'integer': type(value) is int,
               'boolean': type(value) is bool, 'null': value is None}
    if types and not any(matches.get(t, False) for t in types):
        raise ValueError(at + ': wrong type')
    if 'const' in schema and value != schema['const']:
        raise ValueError(at + ': wrong constant')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(at + ': unsupported value')
    if value is None:
        return
    if isinstance(value, dict):
        props = schema.get('properties', {})
        missing = set(schema.get('required', [])) - set(value)
        if missing:
            raise ValueError(at + ': missing ' + ', '.join(sorted(missing)))
        if schema.get('additionalProperties') is False and set(value) - set(props):
            raise ValueError(at + ': unknown fields ' + ', '.join(sorted(set(value) - set(props))))
        for key in value.keys() & props.keys():
            validate(value[key], props[key], at + '.' + key)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            raise ValueError(at + ': too few items')
        if schema.get('uniqueItems') and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            raise ValueError(at + ': duplicate items')
        for i, item in enumerate(value):
            validate(item, schema.get('items', {}), at + '[' + str(i) + ']')
    if isinstance(value, str):
        if len(value.strip()) < schema.get('minLength', 0):
            raise ValueError(at + ': empty/short string')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(at + ': invalid pattern')
        if schema.get('format') == 'date':
            date.fromisoformat(value)
        if schema.get('format') == 'date-time':
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError(at + ': timestamp needs timezone')
    if type(value) is int:
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            raise ValueError(at + ': integer outside bounds')


def local_ref(root, ref):
    path = (root / ref).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise ValueError('operating reference escapes repository')
    if not path.is_file():
        raise ValueError('missing operating reference: ' + ref)
    return path


def inventory(root=ROOT):
    result = {}
    for kind, folder in [('channel', 'channels'), ('format', 'formats'),
                         ('tool', 'tools'), ('lesson', 'lessons')]:
        schema = read(root / 'social' / 'schemas' / (kind + '.schema.json'))
        records = {}
        for path in sorted((root / 'social' / folder).glob('*.json')):
            obj = read(path)
            validate(obj, schema)
            if obj['id'] in records or path.stem != obj['id']:
                raise ValueError('duplicate or mismatched record identity: ' + path.name)
            records[obj['id']] = obj
        if not records:
            raise ValueError('empty operating layer: ' + kind)
        result[kind] = records
    for obj in result['channel'].values():
        local_ref(root, obj['guide'])
        local_ref(root, obj['voice_policy'])
        local_ref(root, obj['authority_ref'])
        personal = obj['account_context'] == 'personal'
        if obj['id'] in DELEGATED_PERSONAL and not personal:
            raise ValueError('account context cannot expand publication authority')
        expected_mode = ('approved_content_cadence' if personal and obj['id'] in DELEGATED_PERSONAL
                         else 'human_publish_only' if personal
                         else 'approved_brand_content')
        if obj['publication_mode'] != expected_mode:
            raise ValueError('account context cannot expand publication authority')
        if expected_mode == 'human_publish_only' and obj['daily_posts_target'] is not None:
            raise ValueError('human-only accounts have no automatic posting quota')
        # Notes post from Krish's own Substack profile at up to two a day as he
        # signs (27 Oct); every other account stays at one a day.
        if (obj['daily_posts_target'] or 0) > 1 and obj['id'] != 'substack-notes':
            raise ValueError('only Substack Notes has a two-a-day target')
        for name in obj['formats']:
            if name not in result['format'] or obj['id'] not in result['format'][name]['channels']:
                raise ValueError('channel/format mismatch: ' + name)
        for lesson in obj['lessons']:
            if lesson not in result['lesson']:
                raise ValueError('unknown channel lesson: ' + lesson)
    for obj in result['format'].values():
        local_ref(root, obj['guide'])
        if obj['production_owner'] == 'growth-canva':
            local_ref(root, obj['production_reference'])
        if obj['max_assets'] is not None and obj['min_assets'] > obj['max_assets']:
            raise ValueError('inconsistent format asset bounds')
        mechanics = [c for c in obj['delivery_checks'] if c.startswith(SHARE_MECHANIC)]
        if obj['snackable'] and (len(mechanics) != 1 or SHARE_LESSON not in obj['lessons']):
            raise ValueError('a snackable format names one share mechanic and the built-to-be-sent lesson: ' + obj['id'])
        if not obj['snackable'] and mechanics:
            raise ValueError('only a snackable format carries a share mechanic: ' + obj['id'])
        for name in obj['channels']:
            if name not in result['channel'] or obj['id'] not in result['channel'][name]['formats']:
                raise ValueError('format/channel mismatch: ' + name)
    for obj in result['tool'].values():
        local_ref(root, obj['guide'])
        keys = set()
        for cap in obj['capabilities']:
            key = (cap['channel'], cap['format'])
            if key in keys or cap['format'] not in result['channel'].get(cap['channel'], {}).get('formats', []):
                raise ValueError('duplicate or unknown tool capability')
            keys.add(key)
            if cap['status'] == 'verified' and not cap['verified_at']:
                raise ValueError('verified capability requires observation date')
            if cap['status'] == 'verified' and not cap['verified_operations']:
                raise ValueError('verified capability requires its specific tested operation')
    for obj in result['lesson'].values():
        if obj['status'] == 'accepted' and obj['evidence']['kind'] != 'user_ruling':
            raise ValueError('accepted rule needs a user ruling, not a performance inference')
        if obj['supersedes'] and obj['supersedes'] not in result['lesson']:
            raise ValueError('superseded lesson not found')
    for kind in ('channel', 'format', 'tool'):
        for obj in result[kind].values():
            if any(name not in result['lesson'] for name in obj['lessons']):
                raise ValueError('unknown operating lesson reference')
    load_share_rules(root / 'social' / 'share.json')
    return result


def route(channel, format_id, tool='buffer', as_of=None, root=ROOT):
    records = inventory(root)
    c = records['channel'][channel]
    f = records['format'][format_id]
    t = records['tool'][tool]
    if format_id not in c['formats']:
        raise ValueError('format is not routed for this channel')
    now = date.fromisoformat(as_of) if as_of else datetime.now(timezone.utc).date()
    caps = [x for x in t['capabilities'] if x['channel'] == channel and x['format'] == format_id]
    holds = []
    if not caps or caps[0]['status'] != 'verified':
        holds.append('capability_not_verified_for_selected_channel_and_format')
    else:
        age = (now - date.fromisoformat(caps[0]['verified_at'])).days
        if age < 0 or age > t['recheck_after_days']:
            holds.append('capability_observation_requires_recheck')
    lesson_ids = list(dict.fromkeys(c['lessons'] + f['lessons'] + t['lessons']))
    return {'local_only': True, 'publication_authorized': False,
            'channel': c, 'format': f, 'tool': t['id'],
            'read': ['social/README.md', c['guide'], c['voice_policy'], c['authority_ref'], f['guide'], t['guide']],
            'known_capability': caps[0] if caps else None,
            'live_checks': c['live_checks'] + t['always_live_checks'],
            'holds': holds, 'lessons': [records['lesson'][x] for x in lesson_ids
                                      if records['lesson'][x]['status'] != 'superseded']}


def package_digest(package):
    body = {k: v for k, v in package.items() if k != 'publication_approval'}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def draft_target_errors(package, target):
    """Why a get_post readback is not a Buffer draft this package may overwrite with edit_post.

    edit_post names only a postId, never a channelId, and the Buffer organisation
    is shared with other ventures, so a reused draft is read with get_post first:
    it must sit on the package's pinned channel (never another venture's), be a
    draft and not be a post imported from the network. The same checks release
    runs on its own edit targets (engine/run/release.py:target_errors).
    """
    from .run.release import BUFFER_ID, CHANNELS, _post, target_errors  # local: release imports route from here
    if package.get('tool') != 'buffer':
        return ['a get_post edit target applies only to a Buffer package']
    if package.get('channel') not in CHANNELS:
        return ['Buffer has no route for ' + str(package.get('channel')) + ' in this engine']
    post = _post(target)
    if not isinstance(post, dict) or not (isinstance(post.get('id'), str) and BUFFER_ID.match(post['id'])):
        return ['edit target was not read back with get_post']
    errors = channel_id_errors(package['channel'], post.get('channelId'))
    errors += [e for e in target_errors({'buffer_draft_id': post['id'], 'channel': package['channel']}, post,
                                        package['buffer_channel_id']) if e not in errors]
    return errors


def preflight(package, as_of=None, root=ROOT, send_test=None, target=None):
    """Structural package checks. send_test is the blind reader's answer, when one has run.

    target is a get_post readback of an existing draft the package would be
    saved over with edit_post; it must pass draft_target_errors first.
    """
    validate(package, read(root / 'social' / 'schemas' / 'package.schema.json'))
    decision = route(package['channel'], package['format'], package['tool'], as_of, root)
    profile = decision['channel']
    if package['account_url'] != profile['account_url'] or package['account_context'] != profile['account_context']:
        raise ValueError('wrong account identity or speaking context')
    if package['tool'] == 'buffer':
        # The Buffer organisation is shared with other ventures: a draft saved
        # through the connector names this engine's pinned channelId, the same
        # table release reads (engine/buffer_channels.py), or nothing is saved.
        pinned = channel_id_errors(package['channel'], package['buffer_channel_id'])
        if pinned:
            raise ValueError(pinned[0])
    if target is not None:
        wrong = draft_target_errors(package, target)
        if wrong:
            raise ValueError('edit_post target refused: ' + '; '.join(wrong))
    if profile['publication_mode'] == 'human_publish_only' and package['proposed_due_at'] is not None:
        raise ValueError('personal account packages must remain unscheduled for human publication')
    if re.search(r'(?:illustrations?|artwork|scenes?|scorecard)\s+(?:(?:was|were|are|is)\s+)?(?:generated\s+(?:with|by)\s+AI|AI[- ]generated)|AI[- ]generated\s+(?:editorial\s+)?illustrations?', package['caption'], re.I):
        raise ValueError('public illustration-disclaimer boilerplate is prohibited; retain private provenance and native metadata')
    lint = copy_lint_errors(package['caption'], 'channel_copy')
    if lint:
        # Krish, 28 Oct 2026: no eyebrows, asterisks, AI notes or take labels.
        raise ValueError('the caption fails the copy lint: ' + '; '.join(lint))
    if not package['voice_review_passed'] or not package['production']['approved']:
        raise ValueError('voice review and accepted production package are required')
    f = decision['format']
    share_rules = load_share_rules(root / 'social' / 'share.json')
    asks = cta_errors(package['caption'], share_rules) if cta_applies(f['snackable'], share_rules) else []
    if asks:
        raise ValueError('generic share call to action in the copy (' + asks[0] + '); the share must come from'
                         ' the content, not a request (social/share.json)')
    problems = share_errors(package['share'], f['snackable'], share_rules)
    if problems:
        raise ValueError('share block: ' + '; '.join(problems))
    if package['production']['owner'] != f['production_owner']:
        raise ValueError('production owner does not match the selected format')
    count = len(package['assets'])
    if count < f['min_assets'] or (f['max_assets'] is not None and count > f['max_assets']):
        raise ValueError('wrong asset count for selected format')
    for asset in package['assets']:
        path = Path(asset['path'])
        path = path if path.is_absolute() else root / path
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('missing or changed production asset')
    digest = package_digest(package)
    approval = package['publication_approval']
    if approval['approved'] and (approval['payload_sha256'] != digest or not approval['evidence_ref']):
        raise ValueError('publication approval does not bind this exact package')
    holds = list(decision['holds'])
    if profile['publication_mode'] == 'human_publish_only':
        holds.append('personal_account_human_final_publication_required')
    if not approval['approved'] and profile['publication_mode'] == 'human_publish_only':
        holds.append('exact_publication_approval_missing')
    # The blind answer counts only for this exact revision: its request_sha256 must be this request's.
    request = send_test_request(package, share_rules) if f['snackable'] or package['share'] is not None else None
    tested = None
    if send_test is not None and package['share'] is not None:
        try:
            tested = compare_send_test(package['share'], send_test, request, share_rules)
        except StaleSendTest as exc:
            tested = {'local_only': True, 'verdict': 'stale', 'reasons': [str(exc)],
                      'request_sha256': request['request_sha256']}
    if f['snackable'] and (tested is None or tested['verdict'] == 'stale'):
        holds.append('blind_send_test_required_before_krish_sees_it')
    elif tested is not None and tested['verdict'] == 'revise':
        holds.append('blind_send_test_revise')
    # Even a matching stored approval is not authenticated go-live permission.
    holds.append('live_identity_schema_and_authority_readback_required_before_external_action')
    return {'local_only': True, 'structurally_valid': True, 'publication_authorized': False,
            'publication_mode': profile['publication_mode'],
            'package_id': package['id'], 'payload_sha256': digest, 'assets_checked': count,
            'send_test_request_sha256': request['request_sha256'] if request else None,
            'send_test': tested, 'edit_target_checked': target is not None, 'holds': holds}


def command(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    p = sub.add_parser('route')
    p.add_argument('channel'); p.add_argument('format'); p.add_argument('--tool', default='buffer')
    p.add_argument('--as-of')
    p = sub.add_parser('preflight'); p.add_argument('file'); p.add_argument('--as-of')
    p.add_argument('--send-test', help="the blind reader's JSON answer for this package")
    p.add_argument('--target', help='a get_post readback of the draft edit_post would overwrite; required before'
                                    ' any edit_post of a reused draft')
    p = sub.add_parser('send-test', help='print the blind request for a fresh reader, stage it, or compare its answer')
    p.add_argument('file'); p.add_argument('--answer', help="the reader's JSON answer to compare")
    p.add_argument('--stage', help='a new or empty folder: the assets under blind names and request.json,'
                                   ' the only things the reader is given')
    args = parser.parse_args(argv)
    try:
        if args.action == 'check':
            result = {'local_only': True, 'valid': True,
                      'records': {k: len(v) for k, v in inventory().items()}}
        elif args.action == 'route':
            result = route(args.channel, args.format, args.tool, args.as_of)
        elif args.action == 'send-test':
            package = read(args.file)
            validate(package, read(ROOT / 'social' / 'schemas' / 'package.schema.json'))
            if args.answer and args.stage:
                raise ValueError('stage the request or compare an answer, not both')
            if args.answer:
                if package['share'] is None:
                    raise ValueError('this package declares no share block to compare against')
                result = compare_send_test(package['share'], read(args.answer), send_test_request(package))
            elif args.stage:
                result = dict(stage_send_test(package, args.stage), staged=str(args.stage))
            else:
                result = send_test_request(package)
        else:
            result = preflight(read(args.file), args.as_of, send_test=read(args.send_test) if args.send_test else None,
                               target=read(args.target) if args.target else None)
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0
