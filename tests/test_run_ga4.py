"""The direct GA4 reader on synthetic data: credentials, RS256, transport, join and reconcile.

No test touches the network: every live path runs through an injected opener.
The RSA key is built at runtime from two fixed primes and DER-encoded here;
no private key text is committed.
"""
import base64
import contextlib
import copy
import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request

from engine.core import tracked
from engine.run import ga4
from engine.run.ga4 import (GA4Error, Transport, assertion, capture_from_response, credentials, join, load_config,
                            main, own_links, private_key, reconcile, rs256, validate_capture, verified_event,
                            weekly_signups)

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'ga4'
ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-05T17:00:00Z'
# Two fixed primes (synthetic, test only). n has 641 bits: enough room for the SHA-256 DigestInfo.
P = 2135987035920910082395021706169552114602704522356652769947041607822219725780640550022962086949023
Q = 3203980553881365123592532559254328171904056783534979154920562411733329588670960825034443130411861
E = 65537
TOKEN = 'ya29.SYNTHETIC-access-token-never-printed'
EMAIL = 'synthetic-reader@synthetic-project.iam.gserviceaccount.com'
PROPERTY_ID = '100000001'
THREADS = 'placement_bdc6f7e80a42d61ec2b6'
NOTES = 'placement_0a24e3f622234d0f452c'


def der(tag, body):
    size = len(body)
    if size < 0x80:
        head = bytes([size])
    else:
        raw = size.to_bytes((size.bit_length() + 7) // 8, 'big')
        head = bytes([0x80 | len(raw)]) + raw
    return bytes([tag]) + head + body


def der_int(value):
    return der(0x02, value.to_bytes(value.bit_length() // 8 + 1, 'big'))


def synthetic_key():
    """(PKCS#8 PEM, PKCS#1 PEM, n, d), built now from the fixed primes."""
    n, d = P * Q, pow(E, -1, (P - 1) * (Q - 1))
    pkcs1 = der(0x30, b''.join(der_int(x) for x in (0, n, E, d, P, Q, d % (P - 1), d % (Q - 1), pow(Q, -1, P))))
    rsa_oid = der(0x06, bytes.fromhex('2a864886f70d010101'))
    pkcs8 = der(0x30, der_int(0) + der(0x30, rsa_oid + der(0x05, b'')) + der(0x04, pkcs1))

    def pem(label, raw):
        text = base64.b64encode(raw).decode('ascii')
        lines = [text[i:i + 64] for i in range(0, len(text), 64)]
        return '\n'.join(['-----BEGIN ' + label + '-----'] + lines + ['-----END ' + label + '-----']) + '\n'
    return pem('PRIVATE' + ' KEY', pkcs8), pem('RSA PRIVATE' + ' KEY', pkcs1), n, d


PEM8, PEM1, N, D = synthetic_key()


def account(pem=PEM8, **extra):
    info = {'type': 'service_account', 'project_id': 'synthetic-project', 'private_key_id': 'synthetic',
            'private_key': pem, 'client_email': EMAIL, 'token_uri': 'https://oauth2.googleapis.com/token'}
    info.update(extra)
    return json.dumps(info)


def environ(raw=None, property_id=PROPERTY_ID):
    return {'GA4_SERVICE_ACCOUNT_JSON': account() if raw is None else raw, 'GA4_PROPERTY_ID': property_id}


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def unb64(text):
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def api_response(capture):
    """The runReport JSON that would produce this capture's rows."""
    rows = [{'dimensionValues': [{'value': r['date'].replace('-', '')}]
             + [{'value': r[k]} for k in ga4.ROW_KEYS[1:7]],
             'metricValues': [{'value': str(r[k])} for k in ga4.ROW_KEYS[7:]]} for r in capture['rows']]
    return {'dimensionHeaders': [{'name': x} for x in ga4.DIMENSIONS],
            'metricHeaders': [{'name': x, 'type': 'TYPE_INTEGER'} for x in ga4.METRICS],
            'rows': rows, 'rowCount': len(rows), 'kind': 'analyticsData#runReport'}


class Response:
    def __init__(self, body, url, status=200, final=None):
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
        self.status = status
        self._final = final or url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, limit=-1):
        return self._body if limit < 0 else self._body[:limit]

    def geturl(self):
        return self._final


class FakeGoogle:
    """Stands in for the opener: answers the token and runReport routes, records each request."""

    def __init__(self, report=None, fail=None):
        self.requests = []
        self.report = report if report is not None else api_response(load('capture.json'))
        self.fail = fail

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.fail:
            raise self.fail(request)
        if request.full_url == ga4.TOKEN_URL:
            return Response({'access_token': TOKEN, 'token_type': 'Bearer', 'expires_in': 3600}, request.full_url)
        return Response(self.report, request.full_url)


def run(argv, transport=None, env=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv, transport=transport, environ=env)
    return code, out.getvalue() + err.getvalue()


def unverified_config():
    """The committed ga4.json with nothing verified, whatever the committed file says today."""
    config = copy.deepcopy(load_config(ROOT))
    config['events'] = {k: {'name': None, 'verified': False} for k in ga4.EVENT_KEYS}
    config['verified_at'] = None
    return config


def verified_root(tmp):
    (Path(tmp) / 'invariants').mkdir()
    (Path(tmp) / 'invariants' / 'ga4.json').write_text(json.dumps(load('config-verified.json')), encoding='utf-8')
    return Path(tmp)


class CredentialTests(unittest.TestCase):
    def test_ga4_credentials_accept_raw_or_base64_json(self):
        raw = account()
        encoded = base64.b64encode(raw.encode('utf-8')).decode('ascii')
        wrapped = '\n'.join(encoded[i:i + 76] for i in range(0, len(encoded), 76))
        urlsafe = base64.urlsafe_b64encode(raw.encode('utf-8')).decode('ascii').rstrip('=')
        escaped = account(PEM8.replace('\n', '\\n'))
        bom = base64.b64encode(('\ufeff' + raw).encode('utf-8')).decode('ascii')
        for value in (raw, '  ' + raw + '\n', encoded, wrapped, urlsafe, escaped, account(PEM1), '\ufeff' + raw, bom):
            creds = credentials(environ(value))
            self.assertEqual((creds.client_email, creds.property_id), (EMAIL, PROPERTY_ID))
            self.assertEqual(creds.sign(b'x'), rs256(b'x', N, D))
            shown = repr(creds) + str(vars(creds).keys())
            self.assertNotIn(str(D), repr(creds))
            self.assertNotIn(EMAIL, repr(creds))
            self.assertIn('property', shown)
        refused = [(environ(property_id='12a'), 'bad_property_id'),
                   (environ(property_id=''), 'bad_property_id'),
                   (environ(property_id='properties/1'), 'bad_property_id'),
                   ({'GA4_PROPERTY_ID': PROPERTY_ID}, 'missing_credentials'),
                   (environ(' '), 'missing_credentials'),
                   (environ('not json and not base64!'), 'bad_credentials'),
                   (environ(base64.b64encode(b'[1, 2]').decode('ascii')), 'bad_credentials'),
                   (environ(account(type='authorized_user')), 'bad_credentials'),
                   (environ(account(client_email='nobody')), 'bad_credentials'),
                   (environ(account(token_uri='https://evil.example/token')), 'token_uri_refused'),
                   (environ(account('-----BEGIN PRIVATE' + ' KEY-----\nAAAA\n-----END PRIVATE' + ' KEY-----')),
                    'bad_private_key')]
        for env, code in refused:
            with self.assertRaises(GA4Error) as caught:
                credentials(env)
            self.assertEqual(caught.exception.code, code, env.get('GA4_SERVICE_ACCOUNT_JSON', '')[:30])
            self.assertNotIn('MII', str(caught.exception))

    def test_rs256_signature_verifies_with_public_key(self):
        self.assertEqual(private_key(PEM8), (N, D))
        self.assertEqual(private_key(PEM1), (N, D))
        message = b'synthetic signing input'
        signature = rs256(message, N, D)
        k = (N.bit_length() + 7) // 8
        self.assertEqual(len(signature), k)
        # Verify with the public key alone: s^e mod n is the EMSA-PKCS1-v1_5 block (RFC 8017, 9.2).
        digest_info = (bytes.fromhex('3031300d060960864801650304020105000420')
                       + hashlib.sha256(message).digest())
        block = b'\x00\x01' + b'\xff' * (k - len(digest_info) - 3) + b'\x00' + digest_info
        self.assertEqual(pow(int.from_bytes(signature, 'big'), E, N).to_bytes(k, 'big'), block)
        other = pow(int.from_bytes(rs256(b'another input', N, D), 'big'), E, N).to_bytes(k, 'big')
        self.assertNotEqual(other, block)
        # The JWT a service account trades for a token verifies the same way.
        creds = credentials(environ())
        jwt = assertion(creds, NOW)
        head, claims, sig = jwt.split('.')
        self.assertEqual(json.loads(unb64(head)), {'alg': 'RS256', 'typ': 'JWT'})
        body = json.loads(unb64(claims))
        self.assertEqual((body['iss'], body['aud'], body['scope']),
                         (EMAIL, 'https://oauth2.googleapis.com/token',
                          'https://www.googleapis.com/auth/analytics.readonly'))
        self.assertEqual(body['exp'] - body['iat'], 3600)
        signed = (head + '.' + claims).encode('ascii')
        expected = (b'\x00\x01' + b'\xff' * (k - 54) + b'\x00' + bytes.fromhex('3031300d060960864801650304020105000420')
                    + hashlib.sha256(signed).digest())
        self.assertEqual(pow(int.from_bytes(unb64(sig), 'big'), E, N).to_bytes(k, 'big'), expected)
        # A key that is not RSA, or too short for the DigestInfo, is refused.
        ec_oid = der(0x06, bytes.fromhex('2a8648ce3d0201'))
        inner = PEM8.split('-----')[2]
        pkcs1 = base64.b64decode(''.join(PEM1.split('-----')[2].split()))
        not_rsa = der(0x30, der_int(0) + der(0x30, ec_oid + der(0x05, b'')) + der(0x04, pkcs1))
        swapped = PEM8.replace(inner, '\n' + base64.b64encode(not_rsa).decode('ascii') + '\n')
        with self.assertRaises(GA4Error) as caught:
            private_key(swapped)
        self.assertEqual(caught.exception.code, 'key_not_rsa')
        # An object identifier whose last arc never ends is a refused key, not a crash.
        broken = der(0x30, der_int(0) + der(0x30, der(0x06, b'\x81') + der(0x05, b'')) + der(0x04, pkcs1))
        with self.assertRaises(GA4Error) as caught:
            private_key(PEM8.replace(inner, '\n' + base64.b64encode(broken).decode('ascii') + '\n'))
        self.assertEqual(caught.exception.code, 'bad_private_key')
        with self.assertRaises(GA4Error) as caught:
            rs256(message, 3233, 2753)
        self.assertEqual(caught.exception.code, 'key_too_short')


class TransportTests(unittest.TestCase):
    def test_ga4_transport_only_allows_google_origins_and_never_logs_secrets(self):
        fake = FakeGoogle()
        transport = Transport(fake, timeout=7)
        for url in ('http://oauth2.googleapis.com/token', 'https://evil.example/token',
                    'https://oauth2.googleapis.com.evil.example/token', 'https://user@oauth2.googleapis.com/token',
                    'https://oauth2.googleapis.com:8443/token', 'https://www.googleapis.com/token',
                    'https://analyticsdata.googleapis.com', 'https://analyticsdata.googleapis.com/x y',
                    'https://analyticsdata.googleapis.com/v1beta/properties/1/audienceExports',
                    'https://analyticsdata.googleapis.com/v1beta/properties/1:runReport?alt=media',
                    'https://oauth2.googleapis.com/revoke', None):
            with self.assertRaises(GA4Error) as caught:
                transport.post(url, b'{}', {})
            self.assertEqual(caught.exception.code, 'origin_refused', url)
        self.assertEqual(fake.requests, [])  # refused before anything is opened
        self.assertEqual(transport.post(ga4.TOKEN_URL, b'x', {})['access_token'], TOKEN)
        self.assertEqual(fake.requests[0][1], 7)
        # No redirect is followed, whether the handler sees it or the final URL moved.
        redirect_body = io.BytesIO(b'moved')
        with self.assertRaises(GA4Error) as caught:
            ga4.NoRedirect().redirect_request(None, redirect_body, 302, 'Found', {}, 'https://evil.example/')
        self.assertEqual(caught.exception.code, 'redirect_refused')
        self.assertTrue(redirect_body.closed)
        self.assertTrue(any(isinstance(h, ga4.NoRedirect) for h in ga4.opener().handlers))
        moved = Transport(lambda request, timeout=None: Response({}, request.full_url, final='https://evil.example/'))
        with self.assertRaises(GA4Error) as caught:
            moved.post(ga4.TOKEN_URL, b'x', {})
        self.assertEqual(caught.exception.code, 'redirect_refused')
        big = Transport(lambda request, timeout=None: Response(b' ' * (ga4.MAX_RESPONSE + 2), request.full_url))
        with self.assertRaises(GA4Error) as caught:
            big.post(ga4.TOKEN_URL, b'x', {})
        self.assertEqual(caught.exception.code, 'response_too_large')

        class Body(io.BytesIO):
            reads = 0

            def read(self, *args):
                Body.reads += 1
                return super().read(*args)
        secret_body = Body(('{"error": "echo ' + TOKEN + ' ' + PEM8 + '"}').encode('utf-8'))

        def forbidden(request):
            return urllib.error.HTTPError(request.full_url, 403, 'Forbidden', {}, secret_body)

        def slow(request):
            return urllib.error.URLError(socket.timeout('timed out'))

        def cut(request):
            return http.client.IncompleteRead(b'partial ' + TOKEN.encode('ascii'))
        for fail, code in ((forbidden, 'forbidden'), (slow, 'timeout'), (cut, 'unreachable')):
            with self.assertRaises(GA4Error) as caught:
                Transport(FakeGoogle(fail=fail)).post(ga4.TOKEN_URL, b'x', {})
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn(TOKEN, str(caught.exception))
        self.assertEqual(Body.reads, 0)  # the error body is never read

        # A whole live run: the token goes only to the data API, and nothing secret is printed.
        with tempfile.TemporaryDirectory() as tmp:
            root = verified_root(tmp)
            fake = FakeGoogle()
            env = environ()
            code, text = run(['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04', '--live',
                              '--root', str(root), '--now', NOW], Transport(fake), env)
            self.assertEqual(code, 0, text)
            token_request, report_request = [r for r, _ in fake.requests]
            self.assertEqual(token_request.full_url, 'https://oauth2.googleapis.com/token')
            self.assertIsNone(token_request.get_header('Authorization'))
            form = dict(x.split('=', 1) for x in token_request.data.decode('ascii').split('&'))
            self.assertEqual(form['grant_type'], 'urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer')
            self.assertEqual(report_request.full_url,
                             'https://analyticsdata.googleapis.com/v1beta/properties/' + PROPERTY_ID + ':runReport')
            self.assertEqual(report_request.get_header('Authorization'), 'Bearer ' + TOKEN)
            body = json.loads(report_request.data.decode('utf-8'))
            self.assertEqual([d['name'] for d in body['dimensions']], list(ga4.DIMENSIONS))
            self.assertEqual(body['limit'], 1000)
            written = json.loads(text)['written']
            self.assertIn(str(Path('.scratch') / 'ga4'), written)
            saved = validate_capture(json.loads(Path(written).read_text(encoding='utf-8')), now=NOW)
            self.assertEqual(saved['rows'], load('capture.json')['rows'])
            for secret in (TOKEN, str(D), PEM8.split('\n')[1], env['GA4_SERVICE_ACCOUNT_JSON'][:40], EMAIL):
                self.assertNotIn(secret, text)
                self.assertNotIn(secret, Path(written).read_text(encoding='utf-8'))
            # An error mid-run prints only its code.
            code, text = run(['ga4', 'events', '--live', '--root', str(root), '--now', NOW],
                             Transport(FakeGoogle(fail=forbidden)), env)
            self.assertEqual(code, 1)
            self.assertIn('forbidden', text)
            for secret in (TOKEN, 'echo', PEM8.split('\n')[1], EMAIL):
                self.assertNotIn(secret, text)
            # GA4 numbers never land in the repository outside .scratch/.
            code, text = run(['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04', '--live',
                              '--root', str(root), '--now', NOW, '--out', str(root / 'lists' / 'ga4.json')],
                             Transport(FakeGoogle()), env)
            self.assertEqual(code, 1)
            self.assertIn('.scratch', text)
            # Nor in this repository, whatever --root says.
            code, text = run(['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04', '--live',
                              '--root', str(root), '--now', NOW, '--out', str(ROOT / 'lists' / 'ga4-synthetic.json')],
                             Transport(FakeGoogle()), env)
            self.assertEqual(code, 1)
            self.assertIn('.scratch', text)
            self.assertFalse((ROOT / 'lists' / 'ga4-synthetic.json').exists())
            # The events listing goes to .scratch/ga4/ only and prints a count, not the names.
            fake = FakeGoogle(report={'dimensionHeaders': [{'name': 'eventName'}],
                                      'metricHeaders': [{'name': 'eventCount'}], 'rowCount': 2,
                                      'rows': [{'dimensionValues': [{'value': 'page_view'}],
                                                'metricValues': [{'value': '40'}]},
                                               {'dimensionValues': [{'value': 'synthetic_event'}],
                                                'metricValues': [{'value': '3'}]}]})
            code, text = run(['ga4', 'events', '--days', '28', '--live', '--root', str(root), '--now', NOW],
                             Transport(fake), env)
            self.assertEqual(code, 0, text)
            self.assertNotIn('synthetic_event', text)
            listing = json.loads(Path(json.loads(text)['written']).read_text(encoding='utf-8'))
            self.assertEqual(listing['events'], [{'event_name': 'page_view', 'event_count': 40},
                                                 {'event_name': 'synthetic_event', 'event_count': 3}])
            self.assertEqual(Path(json.loads(text)['written']).parent, root / '.scratch' / 'ga4')


class EvidenceTests(unittest.TestCase):
    def test_ga4_live_readings_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = verified_root(tmp)
            argv = ['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04', '--live', '--root', str(root),
                    '--now', NOW]
            code, text = run(argv, Transport(FakeGoogle()), environ())
            self.assertEqual(code, 0, text)
            first = Path(json.loads(text)['written'])
            self.assertIn('20261105T170000Z', first.name)  # the capture instant names the file
            before = first.read_bytes()
            fake = FakeGoogle(report=api_response(dict(load('capture.json'), rows=[])))
            code, text = run(argv, Transport(fake), environ())
            self.assertEqual(code, 1)
            self.assertIn('never overwritten', text)
            self.assertEqual(fake.requests, [])  # refused before any request
            self.assertEqual(first.read_bytes(), before)
            # A later reading of the same range lands beside it.
            code, text = run(argv[:-1] + ['2026-11-05T18:00:00Z'], Transport(fake), environ())
            self.assertEqual(code, 0, text)
            self.assertNotEqual(Path(json.loads(text)['written']), first)
            self.assertEqual(first.read_bytes(), before)
            # An explicit --out that exists is refused the same way.
            code, text = run(argv + ['--out', str(first)], Transport(FakeGoogle()), environ())
            self.assertEqual(code, 1)
            self.assertEqual(first.read_bytes(), before)


class EventTests(unittest.TestCase):
    def test_ga4_unverified_event_name_is_refused(self):
        committed = load_config(ROOT)
        self.assertEqual(committed['measurement_id'], 'G-VC5V9LDE17')
        for key in ('sign_up', 'paid_subscription'):
            if committed['events'][key]['verified'] is not True:
                with self.assertRaisesRegex(ValueError, 'not verified'):
                    verified_event(committed, key)
        config = unverified_config()
        for key in ('sign_up', 'paid_subscription'):
            with self.assertRaisesRegex(ValueError, 'not verified'):
                verified_event(config, key)
        self.assertIn('python -m engine.run.ga4 ga4 events', ga4.UNVERIFIED)
        named = copy.deepcopy(config)
        named['events']['sign_up']['name'] = 'sign_up'  # a plausible name is still a guess until verified
        with self.assertRaisesRegex(ValueError, 'never guessed'):
            verified_event(named, 'sign_up')
        # The join gives sessions but refuses sign-ups, even with a row literally named sign_up.
        result = join(load('capture.json'), load('spec.json'), config, NOW)
        slot = result['slots'][0]
        self.assertEqual(slot['sessions'], 8)
        for name in ('sign_ups', 'paid_subscriptions'):
            self.assertIsNone(slot[name]['value'])
            self.assertTrue(slot[name]['reason'].startswith('refused'))
        # With no config given, the join reads the committed file and still counts sessions.
        self.assertEqual(join(load('capture.json'), load('spec.json'), now=NOW)['slots'][0]['sessions'], 8)
        # The config itself: verified needs a name and a date; a name alone is not verified.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ga4.json'
            for change, message in (
                    (lambda c: c['events']['sign_up'].update(verified=True), 'without a name'),
                    (lambda c: c['events']['sign_up'].update(name='synthetic_sign_up', verified=True), 'verified_at'),
                    (lambda c: c.update(verified_at='2026-10-27'), 'verified_at'),
                    (lambda c: c['events'].update(other={'name': None, 'verified': False}), 'exactly'),
                    (lambda c: c.update(note='ten per cent'), 'percentage'),
                    (lambda c: c.update(measurement_id='UA-1'), 'measurement_id')):
                data = json.loads((ROOT / 'invariants' / 'ga4.json').read_text(encoding='utf-8'))
                change(data)
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, message):
                    load_config(path=path)
        verified = load_config(path=FIXTURES / 'config-verified.json')
        self.assertEqual(verified_event(verified, 'sign_up'), 'synthetic_sign_up')
        # The report is never filtered by event, so per-slot sessions are never narrowed.
        self.assertNotIn('dimensionFilter', ga4.report_request('2026-11-02', '2026-11-04', '2026-11-05'))


class JoinTests(unittest.TestCase):
    def test_ga4_report_joins_slots_by_utm_content(self):
        config = load_config(path=FIXTURES / 'config-verified.json')
        spec = load('spec.json')
        link = tracked('https://home.makeyourmindup.ai/p/synthetic-piece', 'threads', 'daily', '2026-11-02',
                       'synthetic-asset-1', 'w45-mon-threads-1')
        self.assertIn(link, spec['slots'][0]['words'])  # the join key is the one tracked() writes
        self.assertEqual([x['utm_content'] for x in own_links(spec['slots'][0]['words'])], [THREADS])
        result = join(load('capture.json'), spec, config, NOW)
        slots = {s['slot_id']: s for s in result['slots']}
        threads, note = slots['w45-mon-threads-1'], slots['w45-mon-note-1']
        # Sessions count once per date and placement, however many event rows share them.
        self.assertEqual((threads['sessions'], threads['sign_ups']['value'], threads['paid_subscriptions']['value']),
                         (8, 2, 0))
        self.assertEqual(threads['sign_ups']['event_name'], 'synthetic_sign_up')  # the unverified "sign_up" row is not counted
        self.assertEqual((note['sessions'], note['sign_ups']['value'], note['paid_subscriptions']['value']), (4, 2, 1))
        self.assertEqual(note['utm_content'], [NOTES])
        quiet, untracked = slots['w45-tue-note-1'], slots['w45-wed-threads-1']
        for slot in (quiet, untracked):
            self.assertIsNone(slot['sessions'])
            self.assertIsNone(slot['sign_ups']['value'])
        self.assertEqual((untracked['own_links'], untracked['untracked_own_links']), (1, 1))
        # Content no slot claims is listed, never assigned; an outside link's utm_content claims nothing.
        self.assertEqual(result['unmatched_content'], ['(not set)', 'placement_ffffffffffffffffffff'])
        # Two slots sharing one utm_content are ambiguous: neither gets the numbers.
        shared = copy.deepcopy(spec)
        shared['slots'][2]['words'] = spec['slots'][0]['words']
        result = join(load('capture.json'), shared, config, NOW)
        for slot in result['slots'][:3:2]:
            self.assertIsNone(slot['sessions'])
            self.assertIn('shared', slot['reason'])
        # The capture is validated like measure.py captures.
        for change in (lambda c: c['rows'][0].update(sessions=-1),
                       lambda c: c['rows'][0].update(event_count=True),
                       lambda c: c['rows'][0].update(key_events=1.5),
                       lambda c: c['rows'][0].update(date='2026-11-05'),
                       lambda c: c['rows'][0].update(extra=1),
                       lambda c: c.update(captured_at='2026-11-06T00:00:00Z'),
                       lambda c: c.update(property_id='G-1'),
                       lambda c: c.update(measurement_id='G-OTHER1'),
                       lambda c: c['date_range'].update(start='2026-08-01'),
                       lambda c: c['date_range'].update(end='2026-11-06'),
                       lambda c: c['rows'].append(dict(c['rows'][0])),
                       lambda c: c.update(rows=[c['rows'][0]] * 1001)):
            capture = load('capture.json')
            change(capture)
            with self.assertRaises(ValueError):
                join(capture, spec, config, NOW)
        # A runReport response becomes the same capture; a truncated one is refused.
        response = api_response(load('capture.json'))
        built = capture_from_response(response, config, '100000001', '2026-11-05T09:00:00-05:00',
                                      '2026-11-02', '2026-11-04')
        self.assertEqual(built, load('capture.json'))
        with self.assertRaisesRegex(ValueError, 'more than 1,000 rows'):
            capture_from_response(dict(response, rowCount=1500), config, '100000001', NOW, '2026-11-02', '2026-11-04')
        with self.assertRaises(GA4Error):
            capture_from_response(dict(response, metricHeaders=response['metricHeaders'][::-1]), config, '100000001',
                                  NOW, '2026-11-02', '2026-11-04')
        for metadata in ({'dataLossFromOtherRow': True}, {'samplingMetadatas': [{'samplesReadCount': '1'}]}):
            with self.assertRaisesRegex(ValueError, 'sampled'):
                capture_from_response(dict(response, metadata=metadata), config, '100000001', NOW,
                                      '2026-11-02', '2026-11-04')
        with self.assertRaisesRegex(ValueError, '90 days'):
            ga4.report_request('2026-08-01', '2026-11-04', '2026-11-05')
        with self.assertRaisesRegex(ValueError, 'still processing today'):
            ga4.report_request('2026-11-02', '2026-11-05', '2026-11-05')
        self.assertEqual(ga4.events_request(28, '2026-11-05')['dateRanges'],
                         [{'startDate': '2026-10-08', 'endDate': '2026-11-04'}])
        # The command line join reads the same files.
        with tempfile.TemporaryDirectory() as tmp:
            code, text = run(['ga4', 'join', str(FIXTURES / 'capture.json'), str(FIXTURES / 'spec.json'),
                              '--root', str(verified_root(tmp)), '--now', NOW])
        self.assertEqual(code, 0, text)
        self.assertEqual(json.loads(text)['slots'][1]['paid_subscriptions']['value'], 1)

    def test_ga4_reconcile_prefers_the_conservative_reading(self):
        lower_ga4 = reconcile(5, 9)
        self.assertEqual((lower_ga4['ga4'], lower_ga4['substack'], lower_ga4['gap']), (5, 9, -4))
        self.assertEqual((lower_ga4['use'], lower_ga4['value']), ('ga4', 5))
        lower_substack = reconcile(12, 9)
        self.assertEqual((lower_substack['use'], lower_substack['value'], lower_substack['gap']), ('substack', 9, 3))
        same = reconcile(7, 7)
        self.assertEqual((same['use'], same['value'], same['gap']), ('substack', 7, 0))
        # A measure.py all_source reading is accepted as it comes.
        self.assertEqual(reconcile(3, {'value': 4, 'reason': None})['value'], 3)
        no_ga4 = reconcile(None, 4)
        self.assertEqual((no_ga4['use'], no_ga4['value'], no_ga4['gap']), ('substack', 4, None))
        no_substack = reconcile(4, {'value': None, 'reason': 'not shown'})
        self.assertEqual((no_substack['use'], no_substack['value']), (None, None))
        for result in (lower_ga4, lower_substack, same, no_ga4, no_substack):
            self.assertNotIn('%', result['reason'])
            self.assertNotIn('\u2014', result['reason'])
        for bad in ((-1, 3), (True, 3), (2.5, 3), (3, '4')):
            with self.assertRaises(ValueError):
                reconcile(*bad)
        # The GA4 weekly figure comes from a seven-day capture through the verified name only.
        week = load('capture.json')
        week['date_range'] = {'start': '2026-10-29', 'end': '2026-11-04'}
        verified = load_config(path=FIXTURES / 'config-verified.json')
        expected = sum(r['event_count'] for r in week['rows'] if r['event_name'] == 'synthetic_sign_up')
        reading = weekly_signups(week, verified, NOW)
        self.assertEqual((reading['value'], reading['event_name']), (expected, 'synthetic_sign_up'))
        self.assertEqual(reconcile(reading, expected + 3)['use'], 'ga4')
        unverified = weekly_signups(week, unverified_config(), NOW)
        self.assertIsNone(unverified['value'])
        self.assertTrue(unverified['reason'].startswith('refused'))
        self.assertEqual((reconcile(unverified, 9)['use'], reconcile(unverified, 9)['gap']), ('substack', None))
        with self.assertRaisesRegex(ValueError, 'seven-day'):
            weekly_signups(load('capture.json'), verified, NOW)


class OfflineTests(unittest.TestCase):
    def test_ga4_never_calls_network_without_live(self):
        def refuse(*args, **kwargs):
            raise AssertionError('network touched without --live')
        fake = FakeGoogle()
        with mock.patch.object(socket, 'create_connection', refuse), \
                mock.patch.object(socket.socket, 'connect', refuse), \
                mock.patch.object(urllib.request, 'urlopen', refuse), \
                mock.patch.object(urllib.request.OpenerDirector, 'open', refuse):
            for argv in (['ga4', 'events'], ['ga4', 'events', '--days', '90'],
                         ['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04']):
                code, text = run(argv + ['--now', NOW], Transport(fake), environ())
                self.assertEqual(code, 0, text)
                plan = json.loads(text)
                self.assertFalse(plan['live'])
                self.assertEqual([x['url'] for x in plan['would_request']],
                                 ['https://oauth2.googleapis.com/token',
                                  'https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY_ID}:runReport'])
                self.assertNotIn(PROPERTY_ID, text)
            code, text = run(['ga4', 'join', str(FIXTURES / 'capture.json'), str(FIXTURES / 'spec.json'),
                              '--now', NOW], Transport(fake), environ())
            self.assertEqual(code, 0, text)
            # --live with no credentials stops before any request.
            code, text = run(['ga4', 'events', '--live', '--now', NOW], Transport(fake), {})
            self.assertEqual(code, 1)
            self.assertIn('missing_credentials', text)
            code, text = run(['ga4', 'events', '--days', '91', '--now', NOW], Transport(fake), environ())
            self.assertEqual(code, 1)
            # The default transport stays offline too.
            for argv in (['ga4', 'events'], ['ga4', 'report', '--start', '2026-11-02', '--end', '2026-11-04']):
                code, text = run(argv + ['--now', NOW], None, environ())
                self.assertEqual(code, 0, text)
                self.assertFalse(json.loads(text)['live'])
        self.assertEqual(fake.requests, [])


if __name__ == '__main__':
    unittest.main()
