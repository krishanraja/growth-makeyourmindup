"""Google Analytics 4, read directly: the Measurement Specialist's per-post attribution.

Krish, 27 Oct 2026: "Happy to let you read Google Analytics directly." The
engine reads property G-VC5V9LDE17 on home.makeyourmindup.ai through the GA4
Data API (runReport) with a read-only service account (Viewer on that one
property). Credentials come from GA4_SERVICE_ACCOUNT_JSON (raw JSON or base64
of it) and GA4_PROPERTY_ID (digits only).

Standard library only. The access token is a JWT signed RS256 in pure Python
(minimal DER parsing of the PKCS#8 key, EMSA-PKCS1-v1_5 over SHA-256) and
exchanged at Google's token endpoint. The transport talks to exactly two
https origins, follows no redirect, has a timeout and a size cap, and never
prints, logs or raises with the token, the key or an error body.

Read-only, and network only when a command is given --live. Without it the
command prints what it would request and exits 0. Event names are confirmed
from the live GA4 Events report and recorded in invariants/ga4.json, never
guessed: a report or join that relies on an unverified event name is refused.
Numbers go to .scratch/ and the Control Center report, never into this
public repository, and a dated reading is never overwritten.

    python -m engine.run.ga4 ga4 events --days 28 --live
    python -m engine.run.ga4 ga4 report --start YYYY-MM-DD --end YYYY-MM-DD --live
    python -m engine.run.ga4 ga4 join CAPTURE SPEC
"""
import argparse
import base64
import binascii
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlsplit

from ..core import calendar_date, instant, ny_time, read_json, write_json
from ..packs import EM_DASH, URL

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path('invariants') / 'ga4.json'
SCRATCH = Path('.scratch') / 'ga4'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
DATA_ORIGIN = 'https://analyticsdata.googleapis.com'
ORIGINS = ('https://oauth2.googleapis.com', DATA_ORIGIN)
SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
GRANT = 'urn:ietf:params:oauth:grant-type:jwt-bearer'
CREDENTIALS_ENV = 'GA4_SERVICE_ACCOUNT_JSON'
PROPERTY_ENV = 'GA4_PROPERTY_ID'
DIMENSIONS = ('date', 'sessionSource', 'sessionMedium', 'sessionCampaignName', 'sessionManualAdContent',
              'landingPage', 'eventName')
METRICS = ('sessions', 'engagedSessions', 'eventCount', 'keyEvents')
ROW_KEYS = ('date', 'session_source', 'session_medium', 'campaign', 'content', 'landing_page', 'event_name',
            'sessions', 'engaged_sessions', 'event_count', 'key_events')
TEXT_KEYS = ROW_KEYS[1:7]
COUNT_KEYS = ROW_KEYS[7:]
CAPTURE_KEYS = {'kind', 'measurement_id', 'property_id', 'captured_at', 'date_range', 'rows'}
EVENT_KEYS = ('sign_up', 'paid_subscription')
CONFIG_KEYS = {'measurement_id', 'property_id_env', 'credentials_env', 'events', 'verified_at', 'note'}
OWN_HOST = 'home.makeyourmindup.ai'
UTMS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
MAX_DAYS = 90
MAX_ROWS = 1000
TIMEOUT = 20
MAX_RESPONSE = 4000000
TOKEN_SECONDS = 3600
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
PROPERTY = re.compile(r'^[0-9]{1,20}$')
MEASUREMENT = re.compile(r'^G-[A-Z0-9]{4,20}$')
DATA_PATH = re.compile(r'^/v1beta/properties/[0-9]{1,20}:runReport$')
EVENT_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')
PEM = re.compile(r'-----BEGIN (RSA )?PRIVATE KEY-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END (RSA )?PRIVATE KEY-----')
RSA_OID = '1.2.840.113549.1.1.1'
# DER of DigestInfo { AlgorithmIdentifier { id-sha256, NULL }, OCTET STRING (32) }: RFC 8017, 9.2 note 1.
SHA256_DIGEST_INFO = bytes.fromhex('3031300d060960864801650304020105000420')
STATUS_CODES = {400: 'bad_request', 401: 'unauthorized', 403: 'forbidden', 404: 'not_found', 429: 'rate_limited'}
EVENTS_COMMAND = 'python -m engine.run.ga4 ga4 events --days 28 --live'
UNVERIFIED = ('refused: the {} event name is not verified; confirm it from the live GA4 Events report '
              '(' + EVENTS_COMMAND + ') and record it in invariants/ga4.json, never guessed')


class GA4Error(ValueError):
    """A failure named by a lower_snake code. Never carries a body, token or key."""

    def __init__(self, code, status=None):
        if not CODE.match(code):
            code = 'internal_error'
        self.code = code
        self.status = status
        super().__init__('GA4: ' + code + (' (HTTP ' + str(status) + ')' if status else ''))


def plain(text, field):
    """Text a person reads: no em dash, no percentages."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(field + ' must be a non-empty string')
    if EM_DASH.search(text) or '%' in text or re.search(r'\bper ?cent\b', text, re.I):
        raise ValueError(field + ' must have no em dash or percentage')
    return text


def count(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(field + ' must be a non-negative whole number')
    return value


# Configuration: invariants/ga4.json ---------------------------------------

def load_config(root=ROOT, path=None):
    """The measurement id, the env names and the event names with their verified flags."""
    path = Path(path) if path else Path(root) / CONFIG
    data = read_json(path)
    if not isinstance(data, dict) or set(data) != CONFIG_KEYS:
        raise ValueError('ga4.json fields must be exactly ' + ', '.join(sorted(CONFIG_KEYS)))
    if not isinstance(data['measurement_id'], str) or not MEASUREMENT.match(data['measurement_id']):
        raise ValueError('ga4.json measurement_id must look like G-XXXXXXXXXX')
    if data['property_id_env'] != PROPERTY_ENV or data['credentials_env'] != CREDENTIALS_ENV:
        raise ValueError('ga4.json names ' + PROPERTY_ENV + ' and ' + CREDENTIALS_ENV)
    plain(data['note'], 'ga4.json note')
    events = data['events']
    if not isinstance(events, dict) or set(events) != set(EVENT_KEYS):
        raise ValueError('ga4.json events are exactly ' + ' and '.join(EVENT_KEYS))
    for key in EVENT_KEYS:
        event = events[key]
        if not isinstance(event, dict) or set(event) != {'name', 'verified'} or not isinstance(event['verified'], bool):
            raise ValueError('ga4.json event ' + key + ' needs name and verified (true or false)')
        name = event['name']
        if name is not None and (not isinstance(name, str) or not EVENT_NAME.match(name)):
            raise ValueError('ga4.json event ' + key + ' name must be a GA4 event name or null')
        if event['verified'] and name is None:
            raise ValueError('ga4.json event ' + key + ' cannot be verified without a name')
    names = [events[k]['name'] for k in EVENT_KEYS if events[k]['name'] is not None]
    if len(names) != len(set(names)):
        raise ValueError('ga4.json sign_up and paid_subscription cannot share an event name')
    verified = any(events[k]['verified'] for k in EVENT_KEYS)
    if verified != (data['verified_at'] is not None):
        raise ValueError('ga4.json verified_at is the date a verified name was read, and null before')
    if data['verified_at'] is not None:
        calendar_date(data['verified_at'])
    return data


def verified_event(config, key):
    """The confirmed GA4 event name for sign_up or paid_subscription; refused while unverified."""
    if key not in EVENT_KEYS:
        raise ValueError('event key must be ' + ' or '.join(EVENT_KEYS))
    event = config['events'][key]
    if event['verified'] is not True or not event['name']:
        raise ValueError(UNVERIFIED.format(key))
    return event['name']


# Credentials ---------------------------------------------------------------

class Credentials:
    """A service account's email, RSA key and the property id. The key never prints."""

    def __init__(self, client_email, modulus, exponent, property_id):
        self.client_email = client_email
        self._n = modulus
        self._d = exponent
        self.property_id = property_id

    def __repr__(self):
        return '<GA4 credentials for property ' + self.property_id + '>'

    def sign(self, message):
        return rs256(message, self._n, self._d)


def _service_account(raw):
    text = raw.lstrip('\ufeff').strip()  # a key file saved by Notepad starts with a byte order mark
    if not text.startswith('{'):
        compact = re.sub(r'\s+', '', text)
        compact += '=' * (-len(compact) % 4)
        try:
            decoded = (base64.b64decode(compact, validate=True) if re.fullmatch(r'[A-Za-z0-9+/=]*', compact)
                       else base64.urlsafe_b64decode(compact))
            text = decoded.decode('utf-8').lstrip('\ufeff').strip()
        except (binascii.Error, ValueError, UnicodeDecodeError):
            raise GA4Error('bad_credentials') from None
    try:
        info = json.loads(text)
    except ValueError:
        raise GA4Error('bad_credentials') from None
    if not isinstance(info, dict) or info.get('type') != 'service_account':
        raise GA4Error('bad_credentials')
    email = info.get('client_email')
    if not isinstance(email, str) or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[A-Za-z]{2,}', email):
        raise GA4Error('bad_credentials')
    if info.get('token_uri', TOKEN_URL) != TOKEN_URL:
        raise GA4Error('token_uri_refused')  # a key file may not point the assertion anywhere else
    key = info.get('private_key')
    if not isinstance(key, str):
        raise GA4Error('bad_credentials')
    return email, key


def credentials(environ=None):
    """Read the two environment variables; accept the key file as raw JSON or base64 of it."""
    environ = os.environ if environ is None else environ
    raw = environ.get(CREDENTIALS_ENV)
    if not isinstance(raw, str) or not raw.strip():
        raise GA4Error('missing_credentials')
    property_id = (environ.get(PROPERTY_ENV) or '').strip()
    if not PROPERTY.match(property_id):
        raise GA4Error('bad_property_id')
    email, key = _service_account(raw)
    n, d = private_key(key)
    return Credentials(email, n, d, property_id)


# Minimal DER and RS256 -----------------------------------------------------

def _tlv(data, pos):
    """One DER element at pos: (tag, start of value, end of value)."""
    if pos + 2 > len(data):
        raise GA4Error('bad_private_key')
    tag, first = data[pos], data[pos + 1]
    pos += 2
    if first < 0x80:
        length = first
    else:
        size = first & 0x7f
        if size == 0 or size > 4 or pos + size > len(data):
            raise GA4Error('bad_private_key')  # indefinite or absurd lengths are not DER
        length = int.from_bytes(data[pos:pos + size], 'big')
        pos += size
    if pos + length > len(data):
        raise GA4Error('bad_private_key')
    return tag, pos, pos + length


def _children(data, start, end):
    out = []
    while start < end:
        tag, a, b = _tlv(data, start)
        out.append((tag, a, b))
        start = b
    if start != end:
        raise GA4Error('bad_private_key')
    return out


def _integer(data, part):
    tag, a, b = part
    if tag != 0x02 or a == b:
        raise GA4Error('bad_private_key')
    return int.from_bytes(data[a:b], 'big', signed=True)


def _oid(raw):
    if not raw or raw[-1] & 0x80:
        raise GA4Error('bad_private_key')  # empty, or the last arc never ends
    parts, value = [], 0
    for byte in raw:
        value = (value << 7) | (byte & 0x7f)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    first = min(parts[0] // 40, 2)
    return '.'.join(str(x) for x in [first, parts[0] - 40 * first] + parts[1:])


def _rsa_private_key(der):
    """RSAPrivateKey (PKCS#1): version, n, e, d, p, q, ... -> (n, d)."""
    tag, a, b = _tlv(der, 0)
    if tag != 0x30 or b != len(der):
        raise GA4Error('bad_private_key')
    parts = _children(der, a, b)
    if len(parts) < 9 or _integer(der, parts[0]) != 0:
        raise GA4Error('bad_private_key')
    n, d = _integer(der, parts[1]), _integer(der, parts[3])
    if n <= 0 or d <= 0 or n.bit_length() < 512:
        raise GA4Error('bad_private_key')
    return n, d


def private_key(pem):
    """(n, d) from a PKCS#8 'PRIVATE KEY' PEM (or a PKCS#1 'RSA PRIVATE KEY')."""
    match = PEM.search(pem.replace('\\n', '\n')) if isinstance(pem, str) else None
    if not match or bool(match.group(1)) != bool(match.group(3)):
        raise GA4Error('bad_private_key')
    try:
        der = base64.b64decode(re.sub(r'\s+', '', match.group(2)), validate=True)
    except (binascii.Error, ValueError):
        raise GA4Error('bad_private_key') from None
    if match.group(1):
        return _rsa_private_key(der)
    tag, a, b = _tlv(der, 0)
    if tag != 0x30 or b != len(der):
        raise GA4Error('bad_private_key')
    parts = _children(der, a, b)
    if len(parts) < 3 or _integer(der, parts[0]) != 0 or parts[1][0] != 0x30 or parts[2][0] != 0x04:
        raise GA4Error('bad_private_key')
    algorithm = _children(der, parts[1][1], parts[1][2])
    if not algorithm or algorithm[0][0] != 0x06 or _oid(der[algorithm[0][1]:algorithm[0][2]]) != RSA_OID:
        raise GA4Error('key_not_rsa')
    return _rsa_private_key(der[parts[2][1]:parts[2][2]])


def rs256(message, n, d):
    """RSASSA-PKCS1-v1_5 with SHA-256 (RFC 8017, 8.2.1): EMSA encoding, then m^d mod n."""
    if isinstance(message, str):
        message = message.encode('utf-8')
    k = (n.bit_length() + 7) // 8
    t = SHA256_DIGEST_INFO + hashlib.sha256(message).digest()
    if k < len(t) + 11:
        raise GA4Error('key_too_short')
    encoded = b'\x00\x01' + b'\xff' * (k - len(t) - 3) + b'\x00' + t
    return pow(int.from_bytes(encoded, 'big'), d, n).to_bytes(k, 'big')


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def assertion(creds, now=None):
    """The signed JWT a service account trades for a read-only access token."""
    issued = int(instant(now).timestamp())
    header = {'alg': 'RS256', 'typ': 'JWT'}
    claims = {'iss': creds.client_email, 'scope': SCOPE, 'aud': TOKEN_URL, 'iat': issued,
              'exp': issued + TOKEN_SECONDS}
    signing_input = '.'.join(b64url(json.dumps(x, separators=(',', ':'), sort_keys=True).encode('utf-8'))
                             for x in (header, claims))
    return signing_input + '.' + b64url(creds.sign(signing_input.encode('ascii')))


# Transport: two Google origins, no redirects, bounded ----------------------

class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could carry the bearer elsewhere, so none is followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            if fp is not None:
                fp.close()  # unread: the redirect body is never looked at
        except (OSError, AttributeError):
            pass
        raise GA4Error('redirect_refused', code)


def opener():
    return urllib.request.build_opener(NoRedirect())


def allowed(url):
    """True only for the token endpoint or a property's runReport: the transport itself is read-only."""
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return False
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        return False
    origin = u.scheme + '://' + u.netloc
    if (u.scheme != 'https' or origin not in ORIGINS or port is not None or u.username or u.password
            or u.query or u.fragment):
        return False
    return url == TOKEN_URL or (origin == DATA_ORIGIN and bool(DATA_PATH.match(u.path)))


class Transport:
    """POST JSON or a form to Google, read-only routes only; an opener can be injected for tests."""

    def __init__(self, open_fn=None, timeout=TIMEOUT):
        self._open = open_fn or opener().open
        self._timeout = timeout

    def __repr__(self):
        return '<GA4 transport for ' + ' and '.join(ORIGINS) + '>'

    def post(self, url, body, headers):
        if not allowed(url):
            raise GA4Error('origin_refused')
        request = urllib.request.Request(url, data=body, method='POST', headers=dict(headers))
        try:
            with self._open(request, timeout=self._timeout) as response:
                final = getattr(response, 'geturl', lambda: url)()
                raw = response.read(MAX_RESPONSE + 1)
                status = getattr(response, 'status', 200)
        except GA4Error:
            raise
        except urllib.error.HTTPError as error:
            try:
                error.close()  # the body is never read: it could echo a token or key
            except (OSError, AttributeError):
                pass
            code = STATUS_CODES.get(error.code, 'server_error' if error.code >= 500 else 'http_error')
            raise GA4Error(code, error.code) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
            reason = getattr(error, 'reason', error)
            raise GA4Error('timeout' if isinstance(reason, socket.timeout) else 'unreachable') from None
        if final != url:
            raise GA4Error('redirect_refused', status)
        if not 200 <= status < 300:
            raise GA4Error('http_error', status)
        if len(raw) > MAX_RESPONSE:
            raise GA4Error('response_too_large', status)
        try:
            result = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise GA4Error('bad_response', status) from None
        if not isinstance(result, dict):
            raise GA4Error('bad_response', status)
        return result


def access_token(creds, transport, now=None):
    """Trade the signed assertion for a bearer held in memory only."""
    body = urlencode({'grant_type': GRANT, 'assertion': assertion(creds, now)}).encode('ascii')
    result = transport.post(TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded',
                                              'Accept': 'application/json'})
    token = result.get('access_token')
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise GA4Error('bad_token_response')
    if str(result.get('token_type', 'Bearer')).lower() != 'bearer':
        raise GA4Error('bad_token_response')
    return token


def report_url(property_id):
    if not isinstance(property_id, str) or not PROPERTY.match(property_id):
        raise GA4Error('bad_property_id')
    return DATA_ORIGIN + '/v1beta/properties/' + property_id + ':runReport'


def run_report(creds, transport, body, now=None):
    token = access_token(creds, transport, now)
    return transport.post(report_url(creds.property_id), json.dumps(body, sort_keys=True).encode('utf-8'),
                          {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                           'Accept': 'application/json'})


# Requests -------------------------------------------------------------------

def date_range(start, end, today):
    """At most 90 days, inclusive, ending before today in New York: today is still being processed."""
    start, end = calendar_date(start), calendar_date(end)
    today = calendar_date(today)
    if end < start:
        raise ValueError('the date range ends before it starts')
    if end >= today:
        raise ValueError('the date range must end before today; GA4 is still processing today')
    if (end - start).days + 1 > MAX_DAYS:
        raise ValueError('the date range is longer than ' + str(MAX_DAYS) + ' days')
    return start.isoformat(), end.isoformat()


def report_request(start, end, today):
    """Every event row for the range, unfiltered, so per-slot sessions are never narrowed by an event."""
    start, end = date_range(start, end, today)
    return {'dateRanges': [{'startDate': start, 'endDate': end}],
            'dimensions': [{'name': d} for d in DIMENSIONS],
            'metrics': [{'name': m} for m in METRICS],
            'limit': MAX_ROWS, 'keepEmptyRows': False}


def events_request(days, today):
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
        raise ValueError('--days must be from 1 to ' + str(MAX_DAYS))
    end = calendar_date(today) - dt.timedelta(days=1)  # today is still being processed
    start = end - dt.timedelta(days=days - 1)
    return {'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
            'dimensions': [{'name': 'eventName'}], 'metrics': [{'name': 'eventCount'}],
            'orderBys': [{'metric': {'metricName': 'eventCount'}, 'desc': True}],
            'limit': MAX_ROWS, 'keepEmptyRows': False}


def _metric(text):
    if not isinstance(text, str) or not re.fullmatch(r'[0-9]{1,15}(?:\.0+)?', text):
        raise GA4Error('bad_response')
    return int(text.split('.')[0])


def _table(response, dimensions, metrics):
    """(dimension values, metric values) per row, refusing anything partial or reordered."""
    if not isinstance(response, dict):
        raise GA4Error('bad_response')
    metadata = response.get('metadata') or {}
    if not isinstance(metadata, dict):
        raise GA4Error('bad_response')
    if metadata.get('dataLossFromOtherRow') or metadata.get('samplingMetadatas'):
        raise ValueError('GA4 rolled rows into (other) or sampled this report, so its counts are not whole; '
                         'narrow the date range and read again')
    heads = [h.get('name') if isinstance(h, dict) else None for h in response.get('dimensionHeaders') or []]
    measures = [h.get('name') if isinstance(h, dict) else None for h in response.get('metricHeaders') or []]
    rows = response.get('rows') or []
    if not isinstance(rows, list):
        raise GA4Error('bad_response')
    if rows and (heads != list(dimensions) or measures != list(metrics)):
        raise GA4Error('bad_response')
    total = response.get('rowCount', len(rows))
    if isinstance(total, bool) or not isinstance(total, int) or total < len(rows):
        raise GA4Error('bad_response')
    if total > len(rows) or len(rows) > MAX_ROWS:
        raise ValueError('the report has more than ' + '{:,}'.format(MAX_ROWS)
                         + ' rows; narrow the date range so nothing is cut off')
    out = []
    for row in rows:
        dims = [v.get('value') if isinstance(v, dict) else None for v in (row.get('dimensionValues') or [])]
        mets = [v.get('value') if isinstance(v, dict) else None for v in (row.get('metricValues') or [])]
        if len(dims) != len(dimensions) or len(mets) != len(metrics) or not all(isinstance(x, str) for x in dims):
            raise GA4Error('bad_response')
        out.append((dims, [_metric(x) for x in mets]))
    return out


def events_from_response(response):
    return [{'event_name': dims[0], 'event_count': mets[0]}
            for dims, mets in _table(response, ('eventName',), ('eventCount',))]


def capture_from_response(response, config, property_id, captured_at, start, end):
    rows = []
    for dims, mets in _table(response, DIMENSIONS, METRICS):
        day = dims[0]
        if not re.fullmatch(r'[0-9]{8}', day):
            raise GA4Error('bad_response')
        values = [day[:4] + '-' + day[4:6] + '-' + day[6:]] + dims[1:] + mets
        rows.append(dict(zip(ROW_KEYS, values)))
    capture = {'kind': 'ga4_report', 'measurement_id': config['measurement_id'], 'property_id': property_id,
               'captured_at': captured_at, 'date_range': {'start': start, 'end': end}, 'rows': rows}
    return validate_capture(capture, config, captured_at)


# The ga4_report capture ------------------------------------------------------

def validate_capture(capture, config=None, now=None):
    """A GA4 report saved for the join: whole counts, no future capture, inside its range."""
    if not isinstance(capture, dict) or capture.get('kind') != 'ga4_report':
        raise ValueError('capture must be a ga4_report object')
    if set(capture) != CAPTURE_KEYS:
        raise ValueError('capture fields must be exactly ' + ', '.join(sorted(CAPTURE_KEYS)))
    if not isinstance(capture['measurement_id'], str) or not MEASUREMENT.match(capture['measurement_id']):
        raise ValueError('measurement_id must look like G-XXXXXXXXXX')
    if config is not None and capture['measurement_id'] != config['measurement_id']:
        raise ValueError('the capture is for another GA4 measurement id than invariants/ga4.json names')
    if not isinstance(capture['property_id'], str) or not PROPERTY.match(capture['property_id']):
        raise ValueError('property_id must be digits only')
    if not isinstance(capture['captured_at'], str):
        raise ValueError('captured_at must be a timestamp with an offset')
    captured = instant(capture['captured_at'])
    if captured > instant(now):
        raise ValueError('captured_at is in the future')
    window = capture['date_range']
    if not isinstance(window, dict) or set(window) != {'start', 'end'}:
        raise ValueError('date_range needs exactly start and end')
    start, end = calendar_date(window['start']), calendar_date(window['end'])
    date_range(window['start'], window['end'], ny_time(captured).date().isoformat())
    rows = capture['rows']
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError('rows must be a list of at most ' + '{:,}'.format(MAX_ROWS))
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(ROW_KEYS):
            raise ValueError('each row needs exactly ' + ', '.join(ROW_KEYS))
        day = calendar_date(row['date'])
        if not start <= day <= end:
            raise ValueError('a row date falls outside the date range')
        for key in TEXT_KEYS:
            if not isinstance(row[key], str):
                raise ValueError(key + ' must be the text GA4 showed')
        for key in COUNT_KEYS:
            count(row[key], key)
        key = tuple(row[k] for k in ROW_KEYS[:7])
        if key in seen:
            raise ValueError('duplicate GA4 row for one date, source, campaign, content, page and event')
        seen.add(key)
    return capture


# Join to slots by utm_content --------------------------------------------------

def own_links(words):
    """Own links in a slot's words: (utm_content or None, tracked with all four UTMs)."""
    out = []
    for match in URL.finditer(words if isinstance(words, str) else ''):
        url = match.group().rstrip('.,;!?)')
        try:
            parts = urlsplit(url)
            host = (parts.hostname or '').lower()
        except ValueError:
            continue
        if host != OWN_HOST:
            continue
        tags = {}
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key.lower() in UTMS:
                tags.setdefault(key.lower(), value)
        tracked = all(tags.get(k) for k in UTMS)
        out.append({'utm_content': tags.get('utm_content') if tracked else None, 'tracked': tracked,
                    'utm_source': tags.get('utm_source'), 'utm_campaign': tags.get('utm_campaign')})
    return out


def _sessions(rows):
    """Sessions without double counting across event rows: the largest per date, source,
    medium, campaign, content and landing page. A lower bound, never a guess."""
    groups = {}
    for row in rows:
        key = tuple(row[k] for k in ROW_KEYS[:6])
        groups[key] = max(groups.get(key, 0), row['sessions'])
    return sum(groups.values())


def _outcome(rows, config, key):
    try:
        name = verified_event(config, key)
    except ValueError as exc:
        return {'value': None, 'event_name': None, 'reason': str(exc)}
    return {'value': sum(r['event_count'] for r in rows if r['event_name'] == name), 'event_name': name,
            'reason': None}


def join(capture, spec, config=None, now=None):
    """Per slot: sessions, sign-ups and paid subscriptions by the slot's own utm_content.

    Sign-ups and paid subscriptions come only through verified event names. A
    capture content value no slot claims is listed, never assigned.
    """
    config = load_config() if config is None else config
    validate_capture(capture, config, now)
    if not isinstance(spec, dict) or not isinstance(spec.get('slots'), list):
        raise ValueError('spec needs a slots list')
    slots = []
    for slot in spec['slots']:
        if not isinstance(slot, dict) or not isinstance(slot.get('slot_id'), str) or not slot['slot_id']:
            raise ValueError('each slot needs a slot_id')
        links = own_links(slot.get('words'))
        slots.append((slot['slot_id'], links))
    owners = {}
    for slot_id, links in slots:
        for content in {link['utm_content'] for link in links if link['tracked']}:
            owners.setdefault(content, []).append(slot_id)
    out = []
    for slot_id, links in slots:
        contents = sorted({link['utm_content'] for link in links if link['tracked']})
        entry = {'slot_id': slot_id, 'utm_content': contents, 'own_links': len(links),
                 'untracked_own_links': len([x for x in links if not x['tracked']])}
        shared = sorted(c for c in contents if len(owners[c]) > 1)
        if not contents or shared:
            reason = ('utm_content shared with another slot: ' + ', '.join(shared) if shared
                      else 'no own link with all four UTMs in the slot words')
            entry.update(sessions=None, rows=0, sign_ups={'value': None, 'event_name': None, 'reason': reason},
                         paid_subscriptions={'value': None, 'event_name': None, 'reason': reason}, reason=reason)
            out.append(entry)
            continue
        rows = [r for r in capture['rows'] if r['content'] in contents]
        entry.update(sessions=_sessions(rows), rows=len(rows), sign_ups=_outcome(rows, config, 'sign_up'),
                     paid_subscriptions=_outcome(rows, config, 'paid_subscription'), reason=None)
        out.append(entry)
    unmatched = sorted({r['content'] for r in capture['rows']} - set(owners))
    return {'local_only': True, 'measurement_id': capture['measurement_id'], 'date_range': capture['date_range'],
            'join_key': 'utm_content', 'sessions_basis': 'largest per date, source, medium, campaign, content and '
            'landing page across event rows, so a lower bound', 'slots': out, 'unmatched_content': unmatched}


def weekly_signups(capture, config=None, now=None):
    """The GA4 sign-ups for one seven-day capture, through the verified event name only.

    Returns {value, event_name, reason}, the shape reconcile() accepts; value is
    None with the refusal while the sign_up name is unverified.
    """
    config = load_config() if config is None else config
    validate_capture(capture, config, now)
    window = capture['date_range']
    days = (calendar_date(window['end']) - calendar_date(window['start'])).days + 1
    if days != 7:
        raise ValueError('a weekly sign-up reading needs a seven-day capture, not ' + str(days) + ' days')
    return _outcome(capture['rows'], config, 'sign_up')


def reconcile(ga4_weekly_signups, substack_all_source):
    """Both readings and the gap; the more conservative one is labelled as the one to use."""
    readings = {}
    for name, value in (('ga4', ga4_weekly_signups), ('substack', substack_all_source)):
        if isinstance(value, dict):
            value = value.get('value')
        readings[name] = None if value is None else count(value, name + ' reading')
    ga4, substack = readings['ga4'], readings['substack']
    out = {'ga4': ga4, 'substack': substack, 'gap': None, 'use': None, 'value': None}
    if substack is None:
        out['reason'] = 'Substack Growth sources were not read, so there is nothing to reconcile against'
        return out
    if ga4 is None:
        out.update(use='substack', value=substack,
                   reason='GA4 was not read; Substack alone, unreconciled, and the gap is unknown')
        return out
    out['gap'] = ga4 - substack
    if ga4 < substack:
        out.update(use='ga4', value=ga4, reason='GA4 reads lower, so it is the more conservative reading; '
                   'the gap is reported')
    else:
        out.update(use='substack', value=substack,
                   reason='Substack reads lower or the same, so it is the more conservative reading'
                   + ('; the gap is reported' if ga4 != substack else ''))
    return out


# Command line ------------------------------------------------------------------

def _private_path(path, root, default):
    """Numbers stay out of git: inside --root or this repository only under .scratch/, and never overwritten."""
    path = Path(path) if path else Path(root) / default
    path = path if path.is_absolute() else Path.cwd() / path
    resolved = path.resolve()
    for base in {Path(root).resolve(), ROOT.resolve()}:
        scratch = (base / '.scratch').resolve()
        if (resolved == base or base in resolved.parents) and scratch not in resolved.parents:
            raise ValueError('GA4 numbers stay out of the public repository; write under .scratch/')
    if path.exists():
        raise ValueError(str(path) + ' exists; GA4 readings are never overwritten, choose another --out')
    return path


def _stamp(now):
    """The capture instant in UTC for a file name, so a later reading never replaces an earlier one."""
    return instant(now).astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _would(body):
    return {'live': False, 'network': 'none; pass --live to read',
            'would_request': [{'method': 'POST', 'url': TOKEN_URL, 'body': 'a signed JWT assertion (never shown)'},
                              {'method': 'POST', 'url': DATA_ORIGIN + '/v1beta/properties/{' + PROPERTY_ENV
                               + '}:runReport', 'body': body}]}


def main(argv=None, transport=None, environ=None):
    parser = argparse.ArgumentParser(prog='python -m engine.run.ga4', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    top = sub.add_parser('ga4')
    what = top.add_subparsers(dest='what', required=True)
    e = what.add_parser('events')
    e.add_argument('--days', type=int, default=28)
    r = what.add_parser('report')
    r.add_argument('--start', required=True); r.add_argument('--end', required=True); r.add_argument('--out')
    for command in (e, r):
        command.add_argument('--live', action='store_true')
        command.add_argument('--now')
    j = what.add_parser('join')
    j.add_argument('capture'); j.add_argument('spec'); j.add_argument('--now')
    for command in (e, r, j):
        command.add_argument('--root', default=str(ROOT))
    args = parser.parse_args(argv)
    try:
        root = Path(args.root)
        config = load_config(root)
        today = ny_time(args.now).date().isoformat()
        if args.what == 'join':
            result = join(read_json(args.capture), read_json(args.spec), config, args.now)
        elif args.what == 'events':
            body = events_request(args.days, today)
            if not args.live:
                result = _would(body)
            else:
                path = _private_path(None, root, SCRATCH / ('events-' + _stamp(args.now) + '.json'))
                creds = credentials(environ)
                names = events_from_response(run_report(creds, transport or Transport(), body, args.now))
                _private_path(path, root, None)  # still new after the read
                write_json(path, {'kind': 'ga4_events', 'measurement_id': config['measurement_id'],
                                  'captured_at': instant(args.now).isoformat(), 'date_range': body['dateRanges'][0],
                                  'events': names,
                                  'next': 'Krish or a session confirms which names are sign_up and '
                                          'paid_subscription, then records them in invariants/ga4.json'})
                result = {'live': True, 'written': str(path), 'event_names': len(names)}
        else:
            body = report_request(args.start, args.end, today)
            if not args.live:
                result = _would(body)
            else:
                path = _private_path(args.out, root, SCRATCH / ('report-' + args.start + '-' + args.end + '-'
                                                                + _stamp(args.now) + '.json'))
                creds = credentials(environ)
                captured_at = instant(args.now).isoformat()
                capture = capture_from_response(run_report(creds, transport or Transport(), body, args.now),
                                                config, creds.property_id, captured_at, *date_range(
                                                    args.start, args.end, today))
                _private_path(path, root, None)  # still new after the read
                write_json(path, capture)
                result = {'live': True, 'written': str(path), 'rows': len(capture['rows'])}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
