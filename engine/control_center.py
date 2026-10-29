"""The Control Center growth engine protocol, versions 1.0.0 and 1.1.0: one transport.

This module is the only place that talks to Control Center. It holds the
bounded HTTPS transport (also used by the legacy packs call in growth.py),
the canonical digest, a validator for the published report schema, the
report builder, the client for the protocol routes and the pure go-live
step of the autonomy loop. Nothing here can send, post, publish or spend:
a report only describes and proposes, and the go-live step only says which
exact approved payloads a separate release layer may act on.

The bearer is held in memory by the client. It is never printed, logged,
written to disk or included in an exception.
"""
import hashlib
import json
from pathlib import Path
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, quote, unquote, urlsplit

from .core import instant
from .credits import spent_errors

SLUG = 'makeyourmindup'
ENGINE_ID = 'growth-makeyourmindup'
PRODUCT_SLUG = 'publication'
APPROVED_ORIGIN = 'https://controlcenter.krishraja.com'
SCHEMA_VERSION = '1.0.0'
# 1.1.0 adds a proposal's stage and parent_proposal_id. A report is raised to it
# only when a proposal uses one of them ("Raise yours only for a field you use").
AUTONOMY_VERSION = '1.1.0'
AUTONOMY_FIELDS = ('stage', 'parent_proposal_id')
# 1.14.0 adds the engagement task: a version 2 action of kind copy_open on the
# engage channel, behind post, that Krish carries out himself (docs/control-center).
ENGAGE_VERSION = '1.14.0'
# 1.16.0 adds credits_spent, the prepaid credits a run spent of the directive's
# credits share (engine/credits.py); raised only when a report carries one.
CREDITS_VERSION = '1.16.0'
CREDITS_FEATURE = 'credits'
# 1.17.0 adds buffer_channels, post_metrics and offdays, top-level report fields (W2.8, W2.9). A go-live of
# posts is approved only once a live report has said which Buffer channel id is this engine's for each
# channel; raised only when a report carries one of them.
CHANNELS_VERSION = '1.17.0'
V17_FIELDS = ('buffer_channels', 'post_metrics', 'offdays')
CHANNEL_NAME = re.compile(r'^[a-z][a-z0-9_-]{0,31}$')
BUFFER_ID_TEXT = re.compile(r'^[A-Za-z0-9]{8,64}$')
SLOT_TEXT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$')
CONCEPT_TEXT = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
METRIC_KEYS = ('reach', 'sends', 'saves', 'likes', 'comments')
ENGAGE_CHANNEL = 'engage'
ENGAGE_KIND = 'copy_open'
MAX_TAPS = 25
# A tap is checked by Control Center's own rule (src/lib/growthEngines.ts,
# parseTap and tapUrlCarriesContact), so one bad tap is held here on its own
# rather than refused there with the whole day's batch.
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[a-z]{2,}', re.I)
PHONE_RUN = re.compile(r'\+?[0-9][0-9\s().-]{8,}[0-9]')
CHAT_HOSTS = frozenset(('wa.me', 'api.whatsapp.com', 'web.whatsapp.com', 'chat.whatsapp.com', 't.me',
                        'telegram.me', 'telegram.dog', 'signal.me', 'sms.to'))
CONTACT_KEYS = re.compile(r'^(?:to|cc|bcc|phone|tel|mobile|number|recipient|recipients|email|mail)$', re.I)
TAP_URL_MAX = 2000


def has_phone(text):
    """Any run of ten digits or more, however it is spaced: Control Center's hasPhone."""
    return any(len(re.sub(r'[^0-9]', '', run)) >= 10 for run in PHONE_RUN.findall(text))


def tap_url_carries_contact(url):
    """Whether a tap's page is a private chat or carries an address or number (Control Center's rule).

    A bare run of digits in a path is a post id, never read as a number."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
    except ValueError:
        return True
    host = host[4:] if host.startswith('www.') else host
    if host in CHAT_HOSTS or (host.endswith('whatsapp.com') and re.search(r'/send\b', parts.path)):
        return True
    if any(CONTACT_KEYS.match(k) and v.strip() for k, v in parse_qsl(parts.query, keep_blank_values=True)):
        return True
    raw = parts.path + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')
    rest = unquote(raw)
    if EMAIL.search(rest):
        return True
    return any(len(re.sub(r'[^0-9]', '', run)) >= 10 and (run.startswith('+') or re.search(r'[^0-9]', run))
               for run in PHONE_RUN.findall(rest))
STAGES = ('plan', 'go_live', 'check_in')
GO_LIVE_WALLS = ('send', 'post', 'spend')
TIMEZONE = 'America/New_York'
TIMEOUT = 20
MAX_RESPONSE = 1000000
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'docs' / 'control-center' / 'engine-report.schema.json'
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
RUN_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:._-]{0,119}$')
LOOPBACK = re.compile(r'^http://127\.0\.0\.1:[0-9]{1,5}$')
STATUS_CODES = {400: 'bad_request', 401: 'unauthorized', 403: 'forbidden', 404: 'not_found',
                409: 'conflict', 413: 'payload_too_large', 429: 'rate_limited'}
OBJECTIVES = {'new_subscribers': 'people', 'paid_boosts_usd': 'USD'}
WALLED = ('spend', 'send', 'post', 'strategy')


class ProtocolError(ValueError):
    """A failure named by a lower_snake code. Never carries a body or secret."""

    def __init__(self, code, status=None, server_code=None):
        if not CODE.match(code):
            code = 'internal_error'
        self.code = code
        self.status = status
        self.server_code = server_code if isinstance(server_code, str) and CODE.match(server_code) else None
        detail = ' (HTTP ' + str(status) + ')' if status else ''
        super().__init__('Control Center: ' + code + detail)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could carry the bearer elsewhere, so none is followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProtocolError('redirect_refused', code)


def opener(loopback=False):
    handlers = [NoRedirect()]
    if loopback:
        # The local stand-in server must never be reached through a proxy.
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


# Canonical JSON and digests ------------------------------------------------

def whole(value):
    """Send whole numbers as int: JavaScript writes 1 where Python writes 1.0."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: whole(item) for key, item in value.items()}
    if isinstance(value, list):
        return [whole(item) for item in value]
    return value


def _refuse_ambiguous_numbers(value):
    if isinstance(value, float):
        text = repr(value)
        if value.is_integer() or 'e' in text or 'inf' in text or 'nan' in text:
            raise ValueError('canonical JSON refuses ' + text + '; send whole numbers as int')
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError('canonical JSON needs string keys')
            _refuse_ambiguous_numbers(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _refuse_ambiguous_numbers(item)


def canonical_json(value):
    """Keys sorted at every depth, no whitespace, arrays in order, no normalisation."""
    _refuse_ambiguous_numbers(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha256_hex(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def report_digest(report):
    body = {key: item for key, item in report.items() if key != 'payload_sha256'}
    return sha256_hex(body)


def payload_digest(wall, channel=None, exact_payload=None, target=None, amount_usd=None, payload=None):
    """The digest Krish's decision is bound to, derived only from what would act."""
    if wall in ('send', 'post'):
        value = {'channel': channel, 'exact_payload': exact_payload, 'target': target}
    elif wall == 'spend':
        value = {'amount_usd': amount_usd, 'target': target}
    else:
        value = payload if payload is not None else {'channel': channel, 'exact_payload': exact_payload, 'target': target}
    return sha256_hex(whole(value))


# The published report schema ----------------------------------------------

def load_schema():
    with open(SCHEMA_PATH, encoding='utf-8') as handle:
        return json.load(handle)


def _type_ok(value, name):
    if name == 'null':
        return value is None
    if name == 'string':
        return isinstance(value, str)
    if name == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if name == 'object':
        return isinstance(value, dict)
    if name == 'array':
        return isinstance(value, list)
    if name == 'boolean':
        return isinstance(value, bool)
    return False


def _pattern_ok(pattern, value):
    # JSON Schema patterns are JavaScript regular expressions, where $ never
    # matches before a trailing newline. Python's does, so anchor with \Z.
    if pattern.endswith('$') and not pattern.endswith('\\$'):
        pattern = pattern[:-1] + r'\Z'
    return re.search(pattern, value) is not None


def schema_errors(value, schema, path='report'):
    """Validate the keywords the protocol schemas use. Every object is closed:
    the server refuses unknown fields, so the engine never sends one."""
    errors = []
    if 'const' in schema and value != schema['const']:
        errors.append(path + ' must be ' + json.dumps(schema['const']))
    if 'enum' in schema and value not in schema['enum']:
        errors.append(path + ' must be one of ' + ', '.join(json.dumps(v) for v in schema['enum']))
    types = schema.get('type')
    if types is not None:
        types = types if isinstance(types, list) else [types]
        if not any(_type_ok(value, name) for name in types):
            return errors + [path + ' must be ' + ' or '.join(types)]
    if isinstance(value, str):
        if 'maxLength' in schema and len(value) > schema['maxLength']:
            errors.append(path + ' is longer than ' + str(schema['maxLength']))
        if 'pattern' in schema and not _pattern_ok(schema['pattern'], value):
            errors.append(path + ' does not match ' + schema['pattern'])
        if schema.get('format') == 'date-time':
            try:
                instant(value)
                if 'T' not in value:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(path + ' must be a date-time with an offset')
    if _type_ok(value, 'number') and 'minimum' in schema and value < schema['minimum']:
        errors.append(path + ' is below ' + str(schema['minimum']))
    if _type_ok(value, 'number') and 'maximum' in schema and value > schema['maximum']:
        errors.append(path + ' is above ' + str(schema['maximum']))
    if isinstance(value, dict):
        props = schema.get('properties', {})
        # A map (1.17.0 buffer_channels.allowed, offdays.days): its keys are named by propertyNames and
        # every value is checked against additionalProperties. Any other object stays closed.
        each = schema.get('additionalProperties') if isinstance(schema.get('additionalProperties'), dict) else None
        names = (schema.get('propertyNames') or {}).get('pattern')
        if 'maxProperties' in schema and len(value) > schema['maxProperties']:
            errors.append(path + ' has more than ' + str(schema['maxProperties']) + ' entries')
        for key in schema.get('required', []):
            if key not in value:
                errors.append(path + '.' + key + ' is required')
        for key, item in value.items():
            if key in props:
                errors += schema_errors(item, props[key], path + '.' + key)
            elif each is not None and (names is None or _pattern_ok(names, key)):
                errors += schema_errors(item, each, path + '.' + key)
            else:
                errors.append(path + '.' + key + ' is not a protocol field')
    if isinstance(value, list):
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            errors.append(path + ' has more than ' + str(schema['maxItems']) + ' entries')
        for index, item in enumerate(value):
            errors += schema_errors(item, schema.get('items', {}), path + '[' + str(index) + ']')
    return errors


# Building a report --------------------------------------------------------

def iso(value=None):
    return instant(value).strftime('%Y-%m-%dT%H:%M:%SZ')


def clip(text, limit):
    text = ' '.join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut or text[:limit]


def objective(key, value=None, availability='missing', reason=None, window_start=None, window_end=None):
    """Unknown is null with a reason, never zero. A measured zero is 0."""
    if key not in OBJECTIVES:
        raise ValueError('unknown objective ' + key)
    if availability == 'measured':
        if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('a measured objective needs a number')
        reason = None
    else:
        if not reason:
            raise ValueError('an objective that is not measured needs a reason')
        if availability == 'missing':
            value = None
    return {'key': key, 'value': value, 'unit': OBJECTIVES[key],
            'window_start': iso(window_start) if window_start else None,
            'window_end': iso(window_end) if window_end else None,
            'timezone': TIMEZONE, 'availability': availability,
            'reason': clip(reason, 500) if reason else None}


def stage_errors(item):
    """The autonomy rules for one proposal: a plan sits behind a wall, a go-live is
    a send, post or spend under its plan, a check-in is a strategy call on its plan."""
    pid = str(item.get('proposal_id'))
    stage, parent = item.get('stage'), item.get('parent_proposal_id')
    errors = []
    if stage is None:
        if parent is not None:
            errors.append('proposal ' + pid + ' names a parent but no stage')
        return errors
    if stage not in STAGES:
        return ['proposal ' + pid + ' has an unknown stage']
    if stage == 'plan':
        if parent is not None:
            errors.append('plan ' + pid + ' cannot name a parent')
        if item.get('wall') == 'none':
            errors.append('plan ' + pid + ' must be behind a wall')
    else:
        if not isinstance(parent, str) or not RUN_ID.match(parent) or parent == item.get('proposal_id'):
            errors.append(stage + ' ' + pid + ' needs parent_proposal_id naming its plan')
        if stage == 'go_live' and item.get('wall') not in GO_LIVE_WALLS:
            errors.append('go_live ' + pid + ' must be a send, post or spend')
        if stage == 'check_in' and item.get('wall') != 'strategy':
            errors.append('check_in ' + pid + ' must be a strategy call')
    if stage in ('plan', 'check_in') and not item.get('exact_payload'):
        errors.append(stage + ' ' + pid + ' needs its words in exact_payload')
    return errors


def engage_action(body, taps):
    """The engagement task's exact action: {version 2, engage, copy_open, body, taps}. Refuses a bad tap."""
    action = {'version': 2, 'channel': ENGAGE_CHANNEL, 'kind': ENGAGE_KIND, 'body': clip(body, 1000),
              'taps': [{'label': clip(t['label'], 80), 'text': t['text'], 'url': t['url']} for t in taps]}
    errors = action_errors(action)
    if errors:
        raise ValueError('; '.join(errors))
    return action


def action_errors(action):
    errors = []
    taps = action.get('taps') if isinstance(action, dict) else None
    if not isinstance(taps, list) or not 1 <= len(taps) <= MAX_TAPS:
        return ['an engagement task carries 1 to ' + str(MAX_TAPS) + ' taps']
    if not isinstance(action.get('body'), str) or not action['body'].strip() or len(action['body']) > 1000:
        errors.append('an engagement task needs a body of up to 1000 characters')
    for i, tap in enumerate(taps):
        at = 'tap ' + str(i + 1)
        if not isinstance(tap, dict) or set(tap) != {'label', 'text', 'url'}:
            errors.append(at + ' carries exactly label, text and url')
            continue
        if not isinstance(tap['label'], str) or not tap['label'].strip() or len(tap['label']) > 80 or '\n' in tap['label']:
            errors.append(at + ' needs a one-line label of up to 80 characters')
        if not isinstance(tap['text'], str) or not tap['text'].strip() or len(tap['text']) > 2200:
            errors.append(at + ' needs its exact words, up to 2200 characters')
        elif EMAIL.search(tap['text']) or has_phone(tap['text']):
            errors.append(at + ' words carry an email address or a phone number')
        url = tap['url']
        if not (isinstance(url, str) and len(url) <= TAP_URL_MAX and re.match(r'^https://[^\s/@]+(/\S*)?$', url)):
            errors.append(at + ' needs a public https page with no login in it, up to ' + str(TAP_URL_MAX) + ' characters')
        elif tap_url_carries_contact(url):
            errors.append(at + ' page is a private chat or carries an address or a number')
    return errors


def copy_open(item):
    """The engagement task's action when this proposal carries one, else None."""
    if not isinstance(item, dict) or item.get('channel') != ENGAGE_CHANNEL or not isinstance(item.get('exact_payload'), str):
        return None
    try:
        action = json.loads(item['exact_payload'])
    except ValueError:
        return None
    return action if isinstance(action, dict) and action.get('kind') == ENGAGE_KIND else None


def copy_open_errors(item):
    action = copy_open(item)
    if action is None:
        return []
    pid = str(item.get('proposal_id'))
    errors = ['engagement task ' + pid + ': ' + e for e in action_errors(action)]
    if action.get('version') != 2 or set(action) != {'version', 'channel', 'kind', 'body', 'taps'}:
        errors.append('engagement task ' + pid + ' is a version 2 action of version, channel, kind, body and taps')
    if item.get('wall') != 'post' or item.get('stage') is not None:
        errors.append('engagement task ' + pid + ' sits behind post with no stage')
    return errors


def report_version(proposals, credits_spent=None, v17=False):
    """1.17.0 when the report carries buffer_channels, post_metrics or offdays, 1.16.0 when it carries
    credits_spent, 1.14.0 when a proposal is an engagement task, 1.1.0 when one uses a 1.1.0 field, else 1.0.0."""
    if v17:
        return CHANNELS_VERSION
    if credits_spent:
        return CREDITS_VERSION
    proposals = [item for item in proposals or [] if isinstance(item, dict)]
    if any(copy_open(item) for item in proposals):
        return ENGAGE_VERSION
    used = any(key in item for item in proposals for key in AUTONOMY_FIELDS)
    return AUTONOMY_VERSION if used else SCHEMA_VERSION


def proposal(proposal_id, title, why, kind, wall, close_event, channel=None, exact_payload=None,
             target=None, amount_usd=None, objective_key='new_subscribers', evidence=(),
             reference=None, expires_at=None, payload=None, stage=None, parent_proposal_id=None):
    if wall in ('send', 'post') and not exact_payload:
        raise ValueError('a send or post proposal needs its exact words')
    if wall == 'spend' and amount_usd is None:
        raise ValueError('a spend proposal needs amount_usd')
    if kind == 'autonomous' and wall != 'none':
        raise ValueError('an autonomous proposal cannot be behind a wall')
    if exact_payload is not None and len(exact_payload) > 8000:
        raise ValueError('exact_payload is over 8000 characters; hold it instead of cutting the words')
    item = {'proposal_id': proposal_id, 'title': clip(title, 160), 'why': clip(why, 1000),
            'kind': kind, 'wall': wall, 'amount_usd': amount_usd, 'channel': channel,
            'objective_key': objective_key, 'exact_payload': exact_payload,
            'payload_sha256': payload_digest(wall, channel, exact_payload, target, amount_usd, payload),
            'evidence': [{'label': clip(e['label'], 500), 'url': e['url']} for e in list(evidence)[:12]],
            'close_condition': {'event': close_event, 'reference': clip(reference, 500) if reference else None},
            'expires_at': iso(expires_at) if expires_at else None}
    if stage is not None or parent_proposal_id is not None:
        # 1.1.0 fields appear only when used, so a 1.0.0 report never carries them.
        item.update(stage=stage, parent_proposal_id=parent_proposal_id)
        errors = stage_errors(item)
        if errors:
            raise ValueError('; '.join(errors))
    return item


def v17_errors(report):
    """The 1.17.0 rules the JSON schema cannot say (Control Center's parseBufferChannels, parsePostMetrics, parseOffdays)."""
    errors = []
    chans = report.get('buffer_channels')
    if isinstance(chans, dict):
        allowed = chans.get('allowed') if isinstance(chans.get('allowed'), dict) else {}
        denied = chans.get('denied') if isinstance(chans.get('denied'), list) else []
        if set(allowed.values()) & set(denied):
            errors.append('buffer_channels lists an id as both allowed and denied')
        if len(set(allowed.values())) != len(allowed):
            errors.append('buffer_channels gives two channels the same id')
    for item in report.get('post_metrics') or [] if isinstance(report.get('post_metrics'), list) else []:
        for key in METRIC_KEYS:
            value = item.get(key) if isinstance(item, dict) else None
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10 ** 10):
                errors.append('post_metrics ' + key + ' must be a whole number from 0 or null')
    offdays = report.get('offdays')
    if isinstance(offdays, dict):
        for options in (offdays.get('days') or {}).values() if isinstance(offdays.get('days'), dict) else []:
            for option in options if isinstance(options, list) else []:
                if not isinstance(option, dict) or not CONCEPT_TEXT.match(str(option.get('concept_id', ''))):
                    errors.append('offdays concept_id is not a slug Control Center takes')
    return errors


def validate_report(report):
    errors = schema_errors(report, load_schema())
    expected = report_version(report.get('proposals') if isinstance(report.get('proposals'), list) else [],
                              report.get('credits_spent'), any(k in report for k in V17_FIELDS))
    if report.get('schema_version') != expected:
        errors.append('schema_version must be ' + expected + ': raise it only for a field the report uses')
    if 'credits_spent' in report:
        errors += spent_errors(report['credits_spent'])
    errors += v17_errors(report)
    if report.get('engine_id') != ENGINE_ID or report.get('product_slug') != PRODUCT_SLUG:
        errors.append('report must name ' + ENGINE_ID + ' and ' + PRODUCT_SLUG)
    for item in report.get('objectives', []):
        if item.get('availability') != 'measured' and not item.get('reason'):
            errors.append('objective ' + str(item.get('key')) + ' needs a reason when not measured')
        if item.get('availability') == 'missing' and item.get('value') is not None:
            errors.append('objective ' + str(item.get('key')) + ' is missing, so its value must be null')
    ids = set()
    for item in report.get('proposals', []):
        if item.get('proposal_id') in ids:
            errors.append('duplicate proposal ' + str(item.get('proposal_id')))
        ids.add(item.get('proposal_id'))
        if item.get('wall') in ('send', 'post') and not item.get('exact_payload'):
            errors.append('proposal ' + str(item.get('proposal_id')) + ' needs exact_payload')
        if item.get('wall') == 'spend' and item.get('amount_usd') is None:
            errors.append('proposal ' + str(item.get('proposal_id')) + ' needs amount_usd')
        if item.get('kind') == 'autonomous' and item.get('wall') != 'none':
            errors.append('proposal ' + str(item.get('proposal_id')) + ' is autonomous behind a wall')
        if 'subject_ref' in item:
            errors.append('proposal ' + str(item.get('proposal_id')) + ' carries subject_ref, a 1.2.0 field this engine does not speak')
        errors += stage_errors(item)
        errors += copy_open_errors(item)
    if report.get('payload_sha256') != report_digest(report):
        errors.append('payload_sha256 does not match the canonical report')
    if errors:
        raise ValueError('report refused locally: ' + '; '.join(errors))
    return report


def build_report(run_id, mode, observed_at, revision, captured_at, status, objectives=(),
                 activity=(), proposals=(), events=(), holds=(), credits_spent=None, buffer_channels=None,
                 post_metrics=None, offdays=None):
    proposals = list(proposals)
    credits_spent = list(credits_spent or [])
    extra = {k: v for k, v in (('buffer_channels', buffer_channels), ('post_metrics', post_metrics or None),
                               ('offdays', offdays)) if v is not None}
    report = whole({
        'schema_version': report_version(proposals, credits_spent, bool(extra)), 'engine_id': ENGINE_ID, 'product_slug': PRODUCT_SLUG,
        'run_id': run_id, 'mode': mode, 'observed_at': iso(observed_at),
        'source': {'revision': clip(revision, 128), 'captured_at': iso(captured_at)},
        'status': status, 'objectives': list(objectives),
        'activity': [{'line': clip(a['line'], 500), 'evidence_url': a.get('evidence_url')} for a in activity],
        'proposals': proposals, 'events': list(events),
        'holds': [{'reason': clip(h['reason'], 200), 'detail': clip(h['detail'], 1000) if h.get('detail') else None}
                  for h in holds]})
    if credits_spent:
        # Only when this run spent credits, so a report without it is unchanged.
        report['credits_spent'] = whole(credits_spent)
    for key, value in extra.items():
        report[key] = whole(value)
    report['payload_sha256'] = report_digest(report)
    return validate_report(report)


# The client ---------------------------------------------------------------

class Client:
    """The six protocol calls for one engine, over HTTPS to the approved origin."""

    def __init__(self, token, base=APPROVED_ORIGIN, slug=SLUG, timeout=TIMEOUT, loopback_for_tests=False):
        base = (base or '').rstrip('/')
        if loopback_for_tests:
            if not LOOPBACK.match(base):
                raise ProtocolError('origin_refused')
        elif base != APPROVED_ORIGIN:
            raise ProtocolError('origin_refused')
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise ProtocolError('missing_token')
        self._base = base + '/api/growth/engines/' + quote(slug, safe='') + '/'
        self._token = token
        self._timeout = timeout
        self._opener = opener(loopback_for_tests)

    def __repr__(self):
        return '<Control Center client for ' + self._base + '>'

    def _request(self, method, route, body=None, idempotency_key=None):
        headers = {'Authorization': 'Bearer ' + self._token, 'Accept': 'application/json'}
        data = None
        if body is not None:
            data = canonical_json(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        request = urllib.request.Request(self._base + route, data=data, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
                status = response.status
        except ProtocolError:
            raise
        except urllib.error.HTTPError as error:
            server_code = None
            try:
                parsed = json.loads(error.read(4096).decode('utf-8'))
                if isinstance(parsed, dict):
                    server_code = parsed.get('error') or parsed.get('code')
            except (ValueError, OSError, UnicodeDecodeError):
                pass
            finally:
                error.close()
            code = STATUS_CODES.get(error.code, 'server_error' if error.code >= 500 else 'http_error')
            if error.code == 409 and isinstance(server_code, str) and CODE.match(server_code):
                code = server_code
            raise ProtocolError(code, error.code, server_code) from None
        except (urllib.error.URLError, OSError, ValueError) as error:
            # Timeouts, refused connections and TLS failures: never echo detail.
            reason = getattr(error, 'reason', error)
            raise ProtocolError('timeout' if isinstance(reason, socket.timeout) else 'unreachable') from None
        if len(raw) > MAX_RESPONSE:
            raise ProtocolError('response_too_large', status)
        try:
            result = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise ProtocolError('bad_response', status) from None
        if not isinstance(result, dict):
            raise ProtocolError('bad_response', status)
        return result

    def capabilities(self):
        return self._request('GET', 'capabilities')

    def confirm_version(self, version, feature=None):
        """A report above 1.0.0 goes only where capabilities list its version
        (and, for a feature it uses, where that flag is true). Fails closed,
        never downgrades by itself: the report is not sent."""
        try:
            served = self.capabilities()
        except ProtocolError as error:
            raise ProtocolError('schema_version_unconfirmed', error.status) from None
        offered = served.get('schema_versions')
        if not isinstance(offered, list) or version not in offered:
            raise ProtocolError('schema_version_unsupported')
        features = served.get('features') if isinstance(served.get('features'), dict) else {}
        if feature and features.get(feature) is not True:
            raise ProtocolError(feature + '_unsupported')
        return version

    def attempt(self, record):
        allowed = ('attempt_id', 'command', 'run_id', 'status', 'phase', 'error_code', 'started_at', 'finished_at')
        if set(record) - set(allowed) or record.get('status') not in ('started', 'succeeded', 'failed', 'unknown'):
            raise ProtocolError('bad_attempt')
        if record['status'] == 'failed' and not CODE.match(record.get('error_code') or ''):
            raise ProtocolError('bad_attempt')
        if (record['status'] == 'started') == ('finished_at' in record):
            raise ProtocolError('bad_attempt')
        result = self._request('POST', 'attempts', record)
        if result.get('ok') is not True:
            raise ProtocolError('attempt_not_confirmed')
        return result

    def directive(self):
        result = self._request('GET', 'directive')
        if result.get('ok') is not True or not isinstance(result.get('directive'), dict):
            raise ProtocolError('bad_directive')
        return result

    def read_report(self, run_id):
        return self._request('GET', 'reports/' + quote(run_id, safe=''))

    def post_report(self, report):
        """Report once, then read it back. A 409 is read back, never retried."""
        validate_report(report)
        if report['schema_version'] != SCHEMA_VERSION:
            feature = {ENGAGE_VERSION: ENGAGE_KIND, CREDITS_VERSION: CREDITS_FEATURE}.get(report['schema_version'])
            # 1.17.0 names no feature flag: its version in capabilities is the whole check.
            self.confirm_version(report['schema_version'], feature)
        ours = report['payload_sha256']
        try:
            result = self._request('POST', 'reports', report, idempotency_key=report['run_id'])
        except ProtocolError as error:
            if error.status != 409 or error.code == 'engine_inactive':
                raise
            stored = None
            try:
                stored = self.read_report(report['run_id']).get('payload_sha256')
            except ProtocolError:
                pass
            return {'accepted': False, 'conflict': True, 'replayed': False,
                    'stored_payload_sha256': stored, 'readback_matches': stored == ours}
        if result.get('accepted') is not True or result.get('payload_sha256') != ours:
            raise ProtocolError('report_not_confirmed')
        readback = self.read_report(report['run_id'])
        if readback.get('payload_sha256') != ours:
            raise ProtocolError('readback_mismatch')
        return {'accepted': True, 'conflict': False, 'replayed': bool(result.get('replayed')),
                'stored_payload_sha256': ours, 'readback_matches': True}

    def post_flagged_lines(self, route, feature, rows):
        """File the chat backstop's flagged lines (engine/backstop.py names the route and its feature flag).

        Idempotent on each row's line_sha256: a repost answers duplicate."""
        self.confirm_version(SCHEMA_VERSION, feature)
        if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
            raise ProtocolError('bad_backstop_batch')
        result = self._request('POST', route, {'schema': 'growth-' + route + '-backstop/1', 'rows': rows})
        if result.get('ok') is not True or not isinstance(result.get('results'), list):
            raise ProtocolError('backstop_not_confirmed')
        return result

    def decisions(self, since):
        result = self._request('GET', 'decisions?since=' + quote(iso(since), safe=''))
        if not isinstance(result.get('decisions'), list):
            raise ProtocolError('bad_decisions')
        return result['decisions']


def amended_digest(amount_usd=None, exact_payload=None):
    """SHA-256 of the canonical JSON of exactly {amount_usd, exact_payload}, null when absent."""
    return sha256_hex(whole({'amount_usd': amount_usd, 'exact_payload': exact_payload}))


def amendment_ok(decision):
    """True when an amended decision's amended_sha256 is his version's digest.
    An unreadable or mismatched amendment is refused, never repaired."""
    if decision.get('amended') is not True:
        return False
    try:
        digest = amended_digest(decision.get('amount_usd'), decision.get('exact_payload'))
    except (ValueError, TypeError):
        return False
    return decision.get('amended_sha256') == digest


def match_decisions(decisions, proposals):
    """Bind each decision to the payload it was made on. A yes on another
    payload is a stale yes and is never acted on, and an amendment whose
    digest does not recompute is refused. Even an exact yes only means
    Krish said yes to those words; Krish still posts and sends."""
    current = {p['proposal_id']: p['payload_sha256'] for p in proposals}
    out = []
    for item in decisions:
        if not isinstance(item, dict):
            continue
        pid = item.get('proposal_id')
        exact = pid in current and item.get('payload_sha256') == current[pid]
        amended = item.get('amended') is True
        sound = amendment_ok(item) if amended else True
        out.append({'proposal_id': pid, 'decision': item.get('decision'), 'decided_at': item.get('decided_at'),
                    'payload_sha256': item.get('payload_sha256'), 'known': pid in current,
                    # Kept so a declined check-in whose proposal is not at hand still counts as unresolved.
                    'stage': item.get('stage') if isinstance(item.get('stage'), str) else None,
                    'matches_payload': exact, 'amended': amended, 'amendment_matches': sound if amended else None,
                    'usable_approval': exact and sound and item.get('decision') == 'approved',
                    # His version, kept so a later step acts on his words, never the engine's.
                    'exact_payload': item.get('exact_payload') if amended else None,
                    'amount_usd': item.get('amount_usd') if amended else None,
                    'amended_sha256': item.get('amended_sha256') if amended else None})
    return out


# The go-live step of the autonomy loop ------------------------------------

def _decided_at(item):
    """A decision's time, or None when it has none that can be read."""
    if not isinstance(item.get('decided_at'), str):
        return None  # instant(None) is now, which would make an undated decision the newest.
    try:
        return instant(item['decided_at'])
    except (ValueError, TypeError, AttributeError):
        return None


def _latest(decisions):
    """Each proposal's latest dated decision (a later entry wins a tie), and the
    ids with a decision whose time cannot be read: those are held, never guessed."""
    out, undated = {}, set()
    for index, item in enumerate(decisions or []):
        if not isinstance(item, dict) or not isinstance(item.get('proposal_id'), str):
            continue
        at = _decided_at(item)
        if at is None:
            undated.add(item['proposal_id'])
            continue
        old = out.get(item['proposal_id'])
        if old is None or (at, index) >= old[0]:
            out[item['proposal_id']] = ((at, index), item)
    return {pid: pair[1] for pid, pair in out.items()}, undated


def _stops(proposals, decisions, ledger=None):
    """Plans Krish stopped, and declined check-ins whose plan cannot be told yet.

    A declined (purged) check-in stops its plan, and so does the plan itself
    declined. A stop counts whatever digest or date it was made on, because
    stopping is always safe, and once recorded in the ledger it stays (a plan
    declined once stays stopped, even under a later changed version). A
    declined check-in whose own record is not at hand is unresolved: while one
    is, every go-live is held, because the plan it stops is unknown."""
    by_id = {p.get('proposal_id'): p for p in proposals or []
             if isinstance(p, dict) and isinstance(p.get('proposal_id'), str)}
    stopped = dict((ledger or {}).get('stopped') or {})
    pending = dict((ledger or {}).get('unresolved') or {})
    for item in decisions or []:
        if not isinstance(item, dict) or item.get('decision') != 'declined':
            continue
        pid = item.get('proposal_id')
        if not isinstance(pid, str):
            continue
        found = by_id.get(pid) or {}
        stage = found.get('stage') or item.get('stage')
        if stage == 'plan':
            stopped.setdefault(pid, {'by': pid, 'decided_at': item.get('decided_at')})
        elif stage == 'check_in':
            pending.setdefault(pid, {'decided_at': item.get('decided_at')})
    for pid in sorted(pending):
        found = by_id.get(pid) or {}
        parent = found.get('parent_proposal_id')
        if found.get('stage') == 'check_in' and isinstance(parent, str):
            stopped.setdefault(parent, {'by': pid, 'decided_at': pending[pid].get('decided_at')})
        if any(isinstance(why, dict) and why.get('by') == pid for why in stopped.values()):
            del pending[pid]
    return stopped, pending


def stopped_plans(proposals, decisions, ledger=None):
    """Plans Krish stopped: a declined (purged) check-in on the plan, or the plan itself declined."""
    return _stops(proposals, decisions, ledger)[0]


def action_key(action):
    return action['proposal_id'] + '#' + action['action_sha256']


def _plan_open(plan, decision):
    if not plan or plan.get('stage') != 'plan' or not decision or decision.get('decision') != 'approved':
        return False
    if decision.get('payload_sha256') != plan.get('payload_sha256'):
        return False
    return decision.get('amended') is not True or amendment_ok(decision)


def _expiry_hold(item, now):
    """None while the go-live is in date; a hold code once it is not, or cannot be told."""
    if not item.get('expires_at'):
        return None
    if now is None:
        return 'expiry_unchecked'
    try:
        lapsed = instant(item['expires_at']) <= instant(now)
    except (ValueError, TypeError, AttributeError):
        return 'bad_expiry'
    return 'expired' if lapsed else None


def _linkedin(channel):
    return isinstance(channel, str) and channel.strip().lower().startswith('linkedin')


def golive_review(proposals, decisions, ledger=None, now=None):
    """Which approved go-lives may act, and the reason code for each one held.

    A go-live acts only when it is stage go_live; it has never been claimed;
    every decision on it and its plan is dated; no declined check-in is
    unresolved; its latest decision is an approval on the payload_sha256 its
    own fields recompute to; an amended yes recomputes to amended_sha256, and
    then his words and amount act, never the engine's; its parent plan is
    approved on its current digest and not stopped; and it is in date (with
    no now, an expiring go-live is held). Pure: no I/O."""
    ledger = ledger or {}
    acted = ledger.get('acted') or {}
    claimed = {why.get('proposal_id') for why in acted.values() if isinstance(why, dict)}
    by_id = {p.get('proposal_id'): p for p in proposals or []
             if isinstance(p, dict) and isinstance(p.get('proposal_id'), str)}
    latest, undated = _latest(decisions)
    stopped, unresolved = _stops(proposals, decisions, ledger)
    actions, holds = [], []
    for pid in sorted(by_id):
        item = by_id[pid]
        if item.get('stage') != 'go_live':
            continue
        decision = latest.get(pid)
        code = None
        try:
            own = payload_digest(item.get('wall'), item.get('channel'), item.get('exact_payload'),
                                 item.get('target'), item.get('amount_usd'))
        except (ValueError, TypeError):
            own = None
        words, amount = item.get('exact_payload'), item.get('amount_usd')
        amended = bool(decision) and decision.get('amended') is True
        parent = item.get('parent_proposal_id')
        if not isinstance(parent, str):
            parent = None
        if pid in claimed:
            code = 'already_acted'  # Each go-live acts once, whatever is approved on it later.
        elif pid in undated or parent in undated:
            code = 'undated_decision'
        elif unresolved:
            code = 'stop_unresolved'
        elif decision is None or decision.get('decision') != 'approved':
            code = 'not_approved'
        elif own is None or own != item.get('payload_sha256') or decision.get('payload_sha256') != own:
            code = 'stale_approval'
        elif amended and not amendment_ok(decision):
            code = 'amended_digest_mismatch'
        elif parent is None or parent in stopped:
            code = 'plan_stopped' if parent else 'plan_not_approved'
        elif not _plan_open(by_id.get(parent), latest.get(parent)):
            code = 'plan_not_approved'
        else:
            code = _expiry_hold(item, now)
        if code is None and amended:
            words, amount = decision.get('exact_payload'), decision.get('amount_usd')
        if code is None and (item.get('wall') == 'spend' or amount not in (None, 0)):
            code = 'no_spend_authority'
        elif code is None and item.get('wall') in ('send', 'post') and not (isinstance(words, str) and words.strip()):
            code = 'no_exact_words'
        elif code is None and _linkedin(item.get('channel')):
            code = 'linkedin_is_krish_click'
        if code is None:
            action = {'proposal_id': pid, 'parent_proposal_id': parent, 'wall': item['wall'],
                      'channel': item.get('channel'), 'target': item.get('target'), 'exact_payload': words,
                      'amount_usd': amount, 'amended': amended, 'payload_sha256': own,
                      'amended_sha256': decision.get('amended_sha256') if amended else None,
                      'decided_at': decision.get('decided_at')}
            action['action_sha256'] = sha256_hex(whole({key: action[key] for key in
                                                        ('channel', 'target', 'exact_payload', 'amount_usd')}))
            if action_key(action) in acted:
                code = 'already_acted'
            else:
                actions.append(action)
        if code:
            holds.append({'proposal_id': pid, 'reason': code})
    return {'actions': actions, 'holds': holds, 'stopped': stopped, 'unresolved': unresolved}


def golive_actions(proposals, decisions, ledger=None, now=None):
    """The exact payloads a separate release layer may act on, each once. Acts on nothing."""
    return golive_review(proposals, decisions, ledger, now)['actions']
