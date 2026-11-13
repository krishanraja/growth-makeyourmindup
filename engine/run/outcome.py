"""One outcome row per run (Engines rule 3: every hold files its way out; a run that says nothing is a defect).

Each runner ends with exactly one of:

- advanced: it moved something (measured posts, scheduled a line, made a draft), with what;
- nothing_to_do: it looked and there was nothing to act on, with what it looked at;
- held_below_bar: it held work on purpose, with the reason code;
- blocked: it could not run its job, with the lookup it filed or the ask it queued (its way out).

A blocked row with no way out, or a run with no row, fails the run (exit 1), so GitHub emails Krish and
Control Center's engine health sees it. Codes and counts only: this repository is public.
"""
import re

KINDS = ('advanced', 'nothing_to_do', 'held_below_bar', 'blocked')
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


def row(kind, what, way_out=None):
    """The row, or ValueError when it cannot stand (an unknown kind, or blocked with no way out)."""
    if kind not in KINDS:
        raise ValueError('outcome must be one of ' + ', '.join(KINDS))
    if not isinstance(what, str) or not what.strip():
        raise ValueError('an outcome says what it saw')
    if kind == 'blocked' and not (isinstance(way_out, str) and way_out.strip()):
        raise ValueError('a blocked run names its way out: the lookup it filed or the ask it queued')
    return {'outcome': kind, 'what': ' '.join(what.split()), 'way_out': way_out}


def line(value):
    text = 'Outcome: ' + value['outcome'] + ' (' + value['what'] + ')'
    return text + ('; way out: ' + value['way_out'] if value.get('way_out') else '')


def failed(value):
    """True when the row means the run failed: missing, or blocked."""
    return not isinstance(value, dict) or value.get('outcome') not in KINDS or value['outcome'] == 'blocked'
