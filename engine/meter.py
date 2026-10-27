"""The run's own cost: seconds since the run started and HTTP calls made.

One counter in one place. install() wraps urllib's OpenerDirector.open once,
so every HTTP call this process makes through urllib (the Control Center
client, the GA4 transport, the packs call, a Buffer client built on urllib,
the GitHub API read) is counted without touching a call site. It counts
calls, never URLs, bodies or keys.

The clock starts at GROWTH_RUN_STARTED (Unix seconds, set by the workflow's
first step, so setup time counts too) or, without it, when this module loads.
"""
import os
import time
import urllib.request

START_ENV = 'GROWTH_RUN_STARTED'
_LOADED = time.time()
_state = {'calls': 0, 'original': None}


def install():
    """Count every urllib open from now on. Idempotent."""
    if _state['original'] is not None:
        return
    original = urllib.request.OpenerDirector.open

    def counted(self, *args, **kwargs):
        _state['calls'] += 1
        return original(self, *args, **kwargs)

    _state['original'] = original
    urllib.request.OpenerDirector.open = counted


def uninstall():
    if _state['original'] is not None:
        urllib.request.OpenerDirector.open = _state['original']
        _state['original'] = None


def reset():
    _state['calls'] = 0


def calls():
    return _state['calls']


def started(environ=None):
    environ = os.environ if environ is None else environ
    raw = (environ.get(START_ENV) or '').strip()
    if raw.isdigit():
        return float(raw)
    return _LOADED


def seconds(now=None, environ=None):
    now = time.time() if now is None else now
    return max(0, int(round(now - started(environ))))


def cost_line(when='so far', now=None, environ=None):
    """The aggregate cost line a report, journal or log carries: two counts, nothing else."""
    s, n = seconds(now, environ), calls()
    return ('Cost ' + when + ': ' + str(s) + ' second' + ('' if s == 1 else 's') + ' of Actions run time and '
            + str(n) + ' HTTP call' + ('' if n == 1 else 's'))
