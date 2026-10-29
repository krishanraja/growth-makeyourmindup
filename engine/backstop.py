"""Post the chat backstop's kept lines to Control Center's taste_reports (W3.3).

The SessionEnd hook (scripts/taste_backstop.py) keeps Krish's flagged,
scrubbed lines in the ignored .scratch/taste/backstop.jsonl. No session holds
the engine key, so the runner that does (the numbers job on his PC, Krish's
choice of 29 October 2026: "Local file, runner posts") files them here, once
each: Control Center keys each row by its line_sha256, so a repost answers
duplicate, and a line it filed or already holds is marked posted locally.

    python growth.py cc backstop            # dry run: counts only, no call
    python growth.py cc backstop --deliver  # file them

The log carries counts only, never a line.
"""
import json
from pathlib import Path
import re

from .control_center import ProtocolError

OUTBOX = Path('.scratch') / 'taste' / 'backstop.jsonl'
BATCH = 50
ROUTE, FEATURE = 'taste', 'taste_backstop'  # control-center PR #627: POST .../engines/<slug>/taste
REJECTION = re.compile(r"\b(?:reject|nope|hate|doesn'?t fly|ugly|cringe|no[,.!])", re.I)


def kind(line):
    """Control Center takes correction or rejection; a plain no or a dislike is a rejection."""
    return 'rejection' if REJECTION.search(line or '') else 'correction'


def _rows(path):
    rows = []
    for raw in path.read_text(encoding='utf-8', errors='replace').splitlines() if path.is_file() else []:
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get('line'), str) and isinstance(row.get('line_sha256'), str):
            rows.append(row)
    return rows


def wire(row):
    return {'venture': row.get('venture'), 'repository': row.get('repository'), 'kind': kind(row['line']),
            'line': row['line'], 'line_sha256': row['line_sha256'], 'session': row.get('session'),
            'noted_at': row.get('noted_at'), 'posted': False}


def post(client, root, deliver=False):
    """Returns a summary of counts. Marks rows posted only on Control Center's filed or duplicate."""
    path = Path(root) / OUTBOX
    rows = _rows(path)
    waiting = [r for r in rows if r.get('posted') is not True]
    summary = {'waiting': len(waiting), 'filed': 0, 'duplicate': 0, 'refused': 0, 'deliver': bool(deliver),
               'error': None}
    if not deliver or not waiting:
        return summary
    done = set()
    try:
        for start in range(0, len(waiting), BATCH):
            result = client.post_flagged_lines(ROUTE, FEATURE, [wire(r) for r in waiting[start:start + BATCH]])
            for item in result['results']:
                outcome = item.get('result') if isinstance(item, dict) else None
                if outcome in ('filed', 'duplicate', 'refused'):
                    summary[outcome] += 1
                if outcome in ('filed', 'duplicate'):
                    done.add(item.get('line_sha256'))
    except ProtocolError as error:
        summary['error'] = error.code
    if done:
        for row in rows:
            if row.get('line_sha256') in done:
                row['posted'] = True
        tmp = path.with_suffix('.tmp')
        tmp.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows),
                       encoding='utf-8')
        tmp.replace(path)
    return summary
