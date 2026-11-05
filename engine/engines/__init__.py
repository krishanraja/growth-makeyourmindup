"""Four independently runnable growth engines sharing one history (docs/reviews/2026-11-05-growth-engine-review.md).

Each engine has a contract (engines/<engine>.json), a queue of records (engines/records/<engine>.jsonl) and a
module here naming its record kinds, states, detail checks and what a fresh run recovers first. They prepare,
record and decide. Nothing here posts, sends, schedules, spends or writes to Control Center: Krish acts.
"""
import importlib

ENGINES = ('acquisition', 'engagement', 'publishing', 'measurement')


def module(name):
    """The engine module for one of ENGINES."""
    if name not in ENGINES:
        raise ValueError('unknown engine: ' + str(name) + '; choose one of ' + ', '.join(ENGINES))
    return importlib.import_module('engine.engines.' + name)
