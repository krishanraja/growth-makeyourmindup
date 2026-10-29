"""A tiny Anthropic Messages API client for the maker (L0). Standard library only.

This repository runs on Python 3.9 with no dependencies, so it calls the
Messages API over HTTPS directly rather than through the SDK. One call shape:
a system prompt, one user message and a JSON schema the answer must follow
(output_config.format, structured outputs), on one model, answered as a dict.

It never logs or raises with words, the key or a response body: errors carry
a lower_snake code only. A refused key (401 or 403) is AnthropicAuthError, so
the maker stops at once instead of trying every slot.
"""
import http.client
import json
import re
import socket
import urllib.error
import urllib.request

ENDPOINT = 'https://api.anthropic.com/v1/messages'
VERSION = '2026-10-21'
MODEL = 'claude-sonnet-5-5'
EFFORT = 'medium'
TIMEOUT = 120
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

    def __init__(self, key, endpoint=ENDPOINT, timeout=TIMEOUT, loopback_for_tests=False, model=MODEL):
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
        self.calls = 0

    def __repr__(self):
        return '<Anthropic client>'

    def _send(self, body):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self._endpoint, data=data, method='POST', headers={
            'x-api-key': self._key, 'anthropic-version': VERSION, 'content-type': 'application/json',
            'accept': 'application/json'})
        self.calls += 1
        with self._opener.open(request, timeout=self._timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise AnthropicError('response_too_large')
        return raw

    def json_message(self, system, user, schema, max_tokens=MAX_TOKENS):
        """The model's answer to one user message under system, as the dict schema describes.

        Tried twice on a 5xx, a timeout or a dropped connection (a read: nothing is written by it)."""
        body = {'model': self.model, 'max_tokens': max_tokens, 'system': system,
                'messages': [{'role': 'user', 'content': user}],
                'output_config': {'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': schema}}}
        raw = None
        for attempt in (1, 2):
            try:
                raw = self._send(body)
                break
            except AnthropicError:
                raise
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
                if status in (401, 403):
                    raise AnthropicAuthError(status) from None
                if attempt == 1 and status >= 500:
                    continue
                if status == 429:
                    raise AnthropicError('anthropic_rate_limited', status) from None
                raise AnthropicError('anthropic_server_error' if status >= 500 else 'anthropic_rejected',
                                     status) from None
            except (urllib.error.URLError, OSError, http.client.HTTPException) as error:
                if attempt == 1:
                    continue
                reason = getattr(error, 'reason', error)
                raise AnthropicError('anthropic_timeout' if isinstance(reason, socket.timeout)
                                     else 'anthropic_unreachable') from None
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
