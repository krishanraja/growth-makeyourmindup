"""Browser-audit selection, authority and repair receipts. No browser or HTTP writes.

The browser operator supplies observations from the live page. These guards
check consistency, not whether an observation was actually made in a browser.
"""
import datetime as dt
import hashlib
import json
from urllib.parse import urlsplit

from engine.core import canonical, http_url, identity, instant

ACCOUNTS = {
    'youtube': 'https://www.youtube.com/@makeyourmind-up',
    'instagram': 'https://www.instagram.com/makeyourmind.up',
    'tiktok': 'https://www.tiktok.com/@therealkrisho',
    'x': 'https://x.com/therealkrisho',
    'linkedin': 'https://www.linkedin.com/in/krish-raja/',
    'substack': 'https://home.makeyourmindup.ai',
}
AUTO = {'post': {'title', 'caption', 'description', 'link'},
        'profile': {'link'}}
PROTECTED = {'bio', 'positioning', 'pin', 'pinned_content', 'thumbnail',
             'overlay', 'video', 'image', 'audio', 'reupload', 'delete'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def https(value):
    return http_url(value) and urlsplit(value).scheme == 'https'


def same_target(left, right):
    """Match an observed YouTube Studio editor to its public native video ID."""
    if canonical(left) == canonical(right):
        return True
    from urllib.parse import parse_qs
    def video_id(url):
        parsed = urlsplit(url)
        parts = parsed.path.strip('/').split('/')
        if parsed.scheme != 'https':
            return None
        if parsed.hostname == 'studio.youtube.com' and len(parts) == 3 and parts[0] == 'video' and parts[2] == 'edit':
            return parts[1]
        if parsed.hostname == 'www.youtube.com':
            if len(parts) == 2 and parts[0] == 'shorts':
                return parts[1]
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [None])[0]
        return None
    native_id = video_id(left)
    return bool(native_id and native_id == video_id(right))


def scope_start(last_complete=None, now=None):
    end = instant(now)
    start = instant(last_complete) if last_complete else end - dt.timedelta(days=30)
    require(start <= end, 'coverage checkpoint cannot be in the future')
    return start.isoformat()


def in_scope(item, last_complete=None, now=None):
    """Profiles, pins, open repairs and evidenced attention always return.

    Unknown publication dates are included for inspection, never silently lost.
    Only a complete channel checkpoint advances that channel's post window.
    """
    if item.get('surface') == 'profile' or item.get('pinned') is True or item.get('open_repair') is True:
        return True
    if item.get('attention_evidence'):
        return True
    published = item.get('published_at')
    return published is None or instant(scope_start(last_complete, now)) <= instant(published) <= instant(now)


def evidence(value, now=None):
    require(isinstance(value, dict), 'browser evidence required')
    require(value.get('method') == 'browser' and https(value.get('url')), 'live browser URL required')
    require(isinstance(value.get('excerpt'), str) and bool(value['excerpt'].strip()), 'literal page excerpt required')
    require(isinstance(value.get('observed_at'), str), 'explicit browser observation timestamp required')
    age = instant(now) - instant(value.get('observed_at'))
    require(dt.timedelta(0) <= age <= dt.timedelta(hours=2), 'browser evidence must be fresh within two hours')


def repair_plan(change, now=None):
    """Fail closed. Protected/unknown actions never become autonomous via input flags."""
    channel = change.get('channel')
    require(channel in ACCOUNTS, 'unconfigured account; verify and configure it first')
    require(change.get('account_url') == ACCOUNTS[channel], 'account does not match configured owner')
    require(https(change.get('target_url')), 'exact target HTTPS URL required')
    target_host = urlsplit(change['target_url']).hostname
    require(target_host == urlsplit(ACCOUNTS[channel]).hostname, 'target is on another platform')
    evidence(change.get('evidence'), now)
    require(canonical(change['evidence']['url']) == canonical(change['target_url']), 'evidence is for another target')
    require(isinstance(change.get('before'), str) and isinstance(change.get('after'), str), 'exact before/after strings required')
    require(change['before'] != change['after'], 'no change to apply')
    require(change['before'] in change['evidence']['excerpt'], 'before value missing from page evidence')
    require(bool(change.get('reason')) and bool(change.get('success_check')), 'reason and falsifiable success check required')
    payload = {key: change.get(key) for key in ('channel', 'account_url', 'target_url', 'surface', 'field', 'before', 'after')}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    result = {'repair_id': identity('repair', payload), 'payload_sha256': digest, **payload}
    field, surface = change.get('field'), change.get('surface')
    if (channel == 'youtube' and field == 'title') or (channel == 'x' and surface == 'profile' and field == 'link'):
        require(len(change['after']) <= 100, 'proposed value exceeds the observed platform field limit')
    if field in PROTECTED or field not in AUTO.get(surface, set()):
        return {**result, 'disposition': 'approval_required', 'reason': 'outside standing edit authority'}
    for key in ('owner_verified', 'meaning_preserved', 'voice_checked', 'claims_checked', 'field_editable'):
        if change.get(key) is not True:
            return {**result, 'disposition': 'held', 'reason': key + ' not verified'}
    if field == 'link':
        destination = change.get('destination')
        evidence(destination, now)
        require(destination.get('usable') is True, 'destination must be usable, not merely HTTP 200')
        require(destination.get('requested_url') == change['after'], 'destination evidence must name the exact proposed link')
        require(destination.get('purpose_match') is True, 'destination must match the CTA')
        if surface == 'profile':
            require(change.get('link_purpose') in ('repair_broken', 'align_subscription'), 'profile link authority is limited')
            require(urlsplit(change['after']).hostname == 'home.makeyourmindup.ai', 'subscription destination must be owned')
            require(urlsplit(change['after']).path.rstrip('/') == '/subscribe', 'profile alignment must use the verified subscription route')
    return {**result, 'disposition': 'autonomous', 'reason': change['reason']}


def begin(journal, change, current, now=None):
    """Persist intent before using Save. Never retry an unresolved write blindly."""
    plan = repair_plan(change, now)
    require(plan['disposition'] == 'autonomous', 'repair is not autonomously authorised')
    evidence(current, now)
    require(same_target(current['url'], plan['target_url']), 'current page is another target')
    require(current.get('account_url') == plan['account_url'] and current.get('owner_verified') is True,
            'current browser owner must match')
    require(current.get('field') == plan['field'], 'current field does not match')
    require(isinstance(current.get('value'), str) and current['value'] in current['excerpt'],
            'current value must appear in literal browser evidence')
    previous = journal.get(plan['repair_id'])
    if previous:
        if previous['status'] == 'verified' and current.get('value') == plan['after']:
            return {**previous, 'replayed': True}
        # A proved no-op may retry once. An uncertain write or a human edit
        # never retries, and the attempt budget survives process restarts.
        require(previous['status'] == 'held' and previous.get('readback', {}).get('value') == plan['before']
                and current.get('value') == plan['before'] and previous.get('attempts', 1) < 2,
                'existing repair needs readback/reconciliation or has exhausted its attempt budget')
    require(current.get('value') == plan['before'], 'live value changed; re-audit rather than overwrite')
    return {**plan, 'status': 'pending_readback', 'started_at': instant(now).isoformat(),
            'attempts': previous.get('attempts', 1) + 1 if previous else 1,
            'prior_readback': previous.get('readback') if previous else None}


def reconcile(record, readback, now=None):
    evidence(readback, now)
    require(same_target(readback['url'], record['target_url']), 'readback is for another target')
    require(readback.get('field') == record['field'], 'readback is for another field')
    require(instant(readback['observed_at']) >= instant(record['started_at']), 'readback predates edit intent')
    require(readback.get('reopened') is True, 'reopen or reload the saved page before readback')
    require(isinstance(readback.get('value'), str) and readback['value'] in readback['excerpt'],
            'readback value must appear in literal browser evidence')
    status = 'verified' if readback.get('value') == record['after'] else 'held'
    return {**record, 'status': status, 'readback': readback, 'verified_at': instant(now).isoformat() if status == 'verified' else None}


def checkpoint(previous, coverage, now=None):
    """Advance only fully paginated, unblocked channel coverage."""
    require(coverage.get('channel') in ACCOUNTS, 'unknown coverage channel')
    require(coverage.get('account_url') == ACCOUNTS[coverage['channel']], 'coverage owner mismatch')
    require(coverage.get('complete') is True and coverage.get('pagination_complete') is True,
            'partial coverage cannot advance checkpoint')
    require(not coverage.get('blockers'), 'blocked coverage cannot advance checkpoint')
    require(coverage.get('profiles_checked') is True and coverage.get('pins_checked') is True,
            'profiles and pins must be checked')
    require(coverage.get('window_start') == scope_start(previous, now), 'coverage window has a gap')
    require(isinstance(coverage.get('window_end'), str), 'coverage end timestamp required')
    require(instant(coverage.get('window_end')) == instant(now), 'coverage end must match run start')
    return instant(now).isoformat()


def command(action, input_path, state_path, out_path, root, now=None):
    """Local CLI used by the browser operator; it cannot edit a platform."""
    from pathlib import Path
    from engine.core import locked, read_json, write_json
    private = Path(root).resolve() / '.scratch'
    for path in (state_path, out_path):
        require(private in Path(path).resolve().parents, 'audit state and outputs must stay in ignored .scratch')
    value = read_json(input_path)
    with locked(state_path):
        state = read_json(state_path) if Path(state_path).exists() else {'repairs': {}, 'coverage': {}}
        if action == 'plan':
            result = repair_plan(value, now)
        elif action == 'begin':
            result = begin(state['repairs'], value['change'], value['current'], now)
            state['repairs'][result['repair_id']] = result
        elif action == 'reconcile':
            record = state['repairs'][value['repair_id']]
            result = reconcile(record, value['readback'], now)
            state['repairs'][result['repair_id']] = result
        elif action == 'checkpoint':
            channel = value['channel']
            at = checkpoint(state['coverage'].get(channel), value, now)
            state['coverage'][channel] = at
            result = {'channel': channel, 'last_complete': at}
        else:
            raise ValueError('unknown audit action')
        if action != 'plan':
            write_json(state_path, state)
        write_json(out_path, result)
    print('audit ' + action + ': ' + result.get('status', result.get('disposition', 'checkpoint saved')))
    return 0
