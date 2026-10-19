"""The Control Center growth engine protocol, version 1.0.0: one transport.

This module is the only place that talks to Control Center. It holds the
bounded HTTPS transport (also used by the legacy packs call in growth.py),
the canonical digest, a validator for the published report schema, the
report builder and the client for the protocol routes. Nothing here can
send, post, publish or spend: a report only describes and proposes.

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
from urllib.parse import quote

from .core import instant

SLUG = 'makeyourmindup'
ENGINE_ID = 'growth-makeyourmindup'
PRODUCT_SLUG = 'publication'
APPROVED_ORIGIN = 'https://controlcenter.krishraja.com'
SCHEMA_VERSION = '1.0.0'
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
    if isinstance(value, dict):
        props = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append(path + '.' + key + ' is required')
        for key, item in value.items():
            if key not in props:
                errors.append(path + '.' + key + ' is not a protocol field')
            else:
                errors += schema_errors(item, props[key], path + '.' + key)
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


def proposal(proposal_id, title, why, kind, wall, close_event, channel=None, exact_payload=None,
             target=None, amount_usd=None, objective_key='new_subscribers', evidence=(),
             reference=None, expires_at=None, payload=None):
    if wall in ('send', 'post') and not exact_payload:
        raise ValueError('a send or post proposal needs its exact words')
    if wall == 'spend' and amount_usd is None:
        raise ValueError('a spend proposal needs amount_usd')
    if kind == 'autonomous' and wall != 'none':
        raise ValueError('an autonomous proposal cannot be behind a wall')
    if exact_payload is not None and len(exact_payload) > 8000:
        raise ValueError('exact_payload is over 8000 characters; hold it instead of cutting the words')
    return {'proposal_id': proposal_id, 'title': clip(title, 160), 'why': clip(why, 1000),
            'kind': kind, 'wall': wall, 'amount_usd': amount_usd, 'channel': channel,
            'objective_key': objective_key, 'exact_payload': exact_payload,
            'payload_sha256': payload_digest(wall, channel, exact_payload, target, amount_usd, payload),
            'evidence': [{'label': clip(e['label'], 500), 'url': e['url']} for e in list(evidence)[:12]],
            'close_condition': {'event': close_event, 'reference': clip(reference, 500) if reference else None},
            'expires_at': iso(expires_at) if expires_at else None}


def validate_report(report):
    errors = schema_errors(report, load_schema())
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
    if report.get('payload_sha256') != report_digest(report):
        errors.append('payload_sha256 does not match the canonical report')
    if errors:
        raise ValueError('report refused locally: ' + '; '.join(errors))
    return report


def build_report(run_id, mode, observed_at, revision, captured_at, status, objectives=(),
                 activity=(), proposals=(), events=(), holds=()):
    report = whole({
        'schema_version': SCHEMA_VERSION, 'engine_id': ENGINE_ID, 'product_slug': PRODUCT_SLUG,
        'run_id': run_id, 'mode': mode, 'observed_at': iso(observed_at),
        'source': {'revision': clip(revision, 128), 'captured_at': iso(captured_at)},
        'status': status, 'objectives': list(objectives),
        'activity': [{'line': clip(a['line'], 500), 'evidence_url': a.get('evidence_url')} for a in activity],
        'proposals': list(proposals), 'events': list(events),
        'holds': [{'reason': clip(h['reason'], 200), 'detail': clip(h['detail'], 1000) if h.get('detail') else None}
                  for h in holds]})
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

    def decisions(self, since):
        result = self._request('GET', 'decisions?since=' + quote(iso(since), safe=''))
        if not isinstance(result.get('decisions'), list):
            raise ProtocolError('bad_decisions')
        return result['decisions']


def match_decisions(decisions, proposals):
    """Bind each decision to the payload it was made on. A yes on another
    payload is a stale yes and is never acted on. Even an exact yes only
    means Krish said yes to those words; Krish still posts and sends."""
    current = {p['proposal_id']: p['payload_sha256'] for p in proposals}
    out = []
    for item in decisions:
        if not isinstance(item, dict):
            continue
        pid = item.get('proposal_id')
        exact = pid in current and item.get('payload_sha256') == current[pid]
        out.append({'proposal_id': pid, 'decision': item.get('decision'), 'decided_at': item.get('decided_at'),
                    'payload_sha256': item.get('payload_sha256'), 'known': pid in current,
                    'matches_payload': exact,
                    'usable_approval': exact and item.get('decision') == 'approved'})
    return out
