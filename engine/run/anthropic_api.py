"""A tiny Anthropic Messages API client for the maker (L0). Standard library only.

This repository runs on Python 3.9 with no dependencies, so it calls the
Messages API over HTTPS directly rather than through the SDK. One call shape:
a system prompt, one user message and a JSON schema the answer must follow
(output_config.format, structured outputs), on one model, answered as a dict.

It never logs or raises with words, the key or a response body: errors carry
a lower_snake code only. A refused key (401 or 403) is AnthropicAuthError, so
the maker stops at once instead of trying every slot.

A busy or failing API (429, 5xx including 529 overloaded, a timeout or a
dropped connection) is tried at most MAX_ATTEMPTS times, waiting between
tries as its retry-after header asks (or BACKOFF when it names none), never
more than MAX_WAIT seconds in all for one call: a call takes at most
CALL_WORST seconds. A wait that would pass MAX_WAIT or the run's deadline is
not taken; the call fails at once with its code, one of GAVE_UP, and the
maker fails the run loudly on it. With a deadline (set_deadline, a
time.monotonic() instant) no attempt's timeout reaches past it, and a call
that starts too close to it fails as anthropic_out_of_time, so the time a run
spends on this API is bounded by its deadline whatever the slot count.
"""
import http.client
import json
import re
import socket
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://api.anthropic.com/v1/messages'
VERSION = '2026-10-21'
MODEL = 'claude-sonnet-5-5'
EFFORT = 'medium'
TIMEOUT = 60  # seconds, one attempt
MAX_ATTEMPTS = 3
BACKOFF = (5, 15)  # seconds before the second and the third attempt, when the reply names no retry-after
MAX_WAIT = 60  # seconds of waiting in all for one call (under 90)
MIN_ATTEMPT = 10  # seconds: an attempt with less time than this before the deadline is not started
CALL_WORST = MAX_ATTEMPTS * TIMEOUT + MAX_WAIT  # the longest one call can take, in seconds
# The codes a call ends with once its tries are spent or its time is up: the API is busy or down.
GAVE_UP = frozenset({'anthropic_rate_limited', 'anthropic_overloaded', 'anthropic_server_error', 'anthropic_timeout',
                     'anthropic_unreachable', 'anthropic_out_of_time'})
MAX_TOKENS = 16000
MAX_RESPONSE = 2000000
KEY_ENV = 'ANTHROPIC_API_KEY'
LOOPBACK = re.compile(r'^http://127\.0\.0\.1:[0-9]{1,5}(/|$)')
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


class AnthropicError(Exception):
    """An Anthropic failure named by a lower_snake code. Never carries a body or the key."""

    def __init__(self, code, status=None):
        self.code = code if isinstance(code, str) and CODE.match(code) else 'anthropic_error'
        self.status = status
        super().__init__('Anthropic: ' + self.code + (' (HTTP ' + str(status) + ')' if status else ''))


class AnthropicAuthError(AnthropicError):
    def __init__(self, status=None):
        super().__init__('anthropic_key_refused', status)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AnthropicError('redirect_refused', code)


class Anthropic:
    """One JSON answer per call, on MODEL. Nothing else."""

    def __init__(self, key, endpoint=ENDPOINT, timeout=TIMEOUT, loopback_for_tests=False, model=MODEL,
                 sleep=time.sleep, clock=time.monotonic):
        if loopback_for_tests:
            if not LOOPBACK.match(endpoint or ''):
                raise AnthropicError('endpoint_refused')
        elif endpoint != ENDPOINT:
            raise AnthropicError('endpoint_refused')
        if not isinstance(key, str) or not key or any(c.isspace() for c in key):
            raise AnthropicError('anthropic_key_missing')
        self._endpoint, self._key, self._timeout, self.model = endpoint, key, timeout, model
        handlers = [_NoRedirect()]
        if loopback_for_tests:
            handlers.append(urllib.request.ProxyHandler({}))
        self._opener = urllib.request.build_opener(*handlers)
        self._sleep, self._clock, self.deadline = sleep, clock, None
        self.calls = 0
        self.waited = 0.0

    def set_deadline(self, deadline):
        """No attempt reaches past deadline (a clock() instant); a call too close to it is anthropic_out_of_time."""
        self.deadline = deadline

    def _attempt_timeout(self):
        if self.deadline is None:
            return self._timeout
        left = self.deadline - self._clock()
        if left < MIN_ATTEMPT:
            raise AnthropicError('anthropic_out_of_time')
        return min(self._timeout, left)

    def __repr__(self):
        return '<Anthropic client>'

    def _send(self, body, timeout):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self._endpoint, data=data, method='POST', headers={
            'x-api-key': self._key, 'anthropic-version': VERSION, 'content-type': 'application/json',
            'accept': 'application/json'})
        self.calls += 1
        with self._opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise AnthropicError('response_too_large')
        return raw

    def json_message(self, system, user, schema, max_tokens=MAX_TOKENS):
        """The model's answer to one user message under system, as the dict schema describes.

        A 429, a 5xx (529 included), a timeout or a dropped connection is tried again, at most
        MAX_ATTEMPTS times in all, waiting as retry-after asks and never more than MAX_WAIT seconds
        in all (a read: nothing is written by it). Then it raises with one of GAVE_UP."""
        body = {'model': self.model, 'max_tokens': max_tokens, 'system': system,
                'messages': [{'role': 'user', 'content': user}],
                'output_config': {'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': schema}}}
        raw, waited = None, 0.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            retry_after = None
            try:
                raw = self._send(body, self._attempt_timeout())
                break
            except AnthropicError:
                raise
            except urllib.error.HTTPError as error:
                status = error.code
                retry_after = _retry_after(error.headers)
                error.close()
                if status in (401, 403):
                    raise AnthropicAuthError(status) from None
                if status == 429:
                    failure = AnthropicError('anthropic_rate_limited', status)
                elif status == 529:
                    failure = AnthropicError('anthropic_overloaded', status)
                elif status >= 500:
                    failure = AnthropicError('anthropic_server_error', status)
                else:
                    raise AnthropicError('anthropic_rejected', status) from None
            except (urllib.error.URLError, OSError, http.client.HTTPException) as error:
                reason = getattr(error, 'reason', error)
                failure = AnthropicError('anthropic_timeout' if isinstance(reason, socket.timeout)
                                         else 'anthropic_unreachable')
            if attempt == MAX_ATTEMPTS:
                raise failure from None
            wait = BACKOFF[attempt - 1] if retry_after is None else retry_after
            if waited + wait > MAX_WAIT or (self.deadline is not None
                                            and self._clock() + wait + MIN_ATTEMPT > self.deadline):
                raise failure from None  # waiting that long would pass the call's or the run's bound
            self._sleep(wait)
            waited += wait
            self.waited += wait
        try:
            result = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise AnthropicError('anthropic_bad_response') from None
        if not isinstance(result, dict):
            raise AnthropicError('anthropic_bad_response')
        if result.get('stop_reason') == 'refusal':
            raise AnthropicError('anthropic_refused')
        if result.get('stop_reason') == 'max_tokens':
            raise AnthropicError('anthropic_truncated')
        text = next((b.get('text') for b in result.get('content') or []
                     if isinstance(b, dict) and b.get('type') == 'text'), None)
        try:
            value = json.loads(text) if isinstance(text, str) else None
        except ValueError:
            value = None
        if not isinstance(value, dict):
            raise AnthropicError('anthropic_bad_response')
        return value


def _retry_after(headers):
    """Seconds a retry-after header asks for (a whole number, as the API sends it), or None."""
    value = headers.get('retry-after') if headers is not None else None
    if isinstance(value, str) and re.match(r'^[0-9]{1,6}$', value.strip()):
        return int(value.strip())
    return None
