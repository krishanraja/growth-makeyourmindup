"""`growth.py run keys`: key health on the GitHub runner, read-only.

- Control Center: GET capabilities with the engine's gen1_ token.
- Buffer: account_check, when engine/run/buffer_api.py is installed and
  BUFFER_API_KEY is set; otherwise it says "buffer_api not installed" or
  "Buffer not configured" and carries on.

A refused key exits non-zero with cc_token_refused or buffer_key_refused, so
GitHub emails Krish about the failed run. A missing engine token is
cc_token_missing. It prints codes only, never a key or a response body.
"""
import os
import sys

from .. import meter
from ..control_center import ProtocolError
from . import buffer_reads

REFUSED = ('unauthorized', 'forbidden', 'missing_token')


def check_cc(make_client):
    """None when Control Center answered, else a failure code."""
    try:
        client = make_client()
    except ValueError as exc:
        return 'cc_token_missing' if 'No Control Center engine key' in str(exc) else 'cc_token_refused'
    try:
        client.capabilities()
    except ProtocolError as exc:
        return 'cc_token_refused' if exc.code in REFUSED else 'cc_' + exc.code
    return None


def check_buffer(environ=None):
    """(failure code or None, note)."""
    environ = os.environ if environ is None else environ
    if buffer_reads.buffer_module() is None:
        return None, buffer_reads.NOT_INSTALLED
    client, note = buffer_reads.buffer_client(environ)
    if client is None:
        return None, note
    try:
        buffer_reads.account_check(client)
    except Exception as exc:  # an outside module: keep only whether the key was refused
        return ('buffer_key_refused' if buffer_reads.refused(exc) else 'buffer_unreachable'), None
    return None, 'Buffer account check: ok'


def main(argv=None, make_client=None, environ=None, out=print):
    environ = os.environ if environ is None else environ
    if make_client is None:
        import growth
        make_client = growth.engine_client
    failures = []
    cc = check_cc(make_client)
    out('keys: Control Center capabilities: ' + ('ok' if cc is None else 'FAILED ' + cc))
    if cc:
        failures.append(cc)
    code, note = check_buffer(environ)
    out('keys: Buffer: ' + (note if code is None else 'FAILED ' + code))
    if code:
        failures.append(code)
    out(meter.cost_line('in all'))
    for failure in failures:
        if environ.get('GITHUB_ACTIONS') == 'true':
            out('::error::key check failed: ' + failure)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
