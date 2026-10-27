"""The session pack: docs/RUN.md, the spec slice, crew cards in play, findings and status.

One text block of at most 36 KB, so a run session can skip the standing docs.
Offline: it reads local files and writes only where --out points.
"""
import argparse
import json
from pathlib import Path
import sys

from ..core import calendar_date, ny_time, read_json
from ..social import validate
from .spec import ROOT, SCHEMA, lint, monday, status

MAX_BYTES = 36 * 1024
MAX_CARD = 3 * 1024
# Plan section 4: RUN.md 8 KB, the spec slice 10 KB, the cards 12 KB, findings and status 6 KB.
BUDGETS = (('docs/RUN.md', 8 * 1024), ('the spec slice', 10 * 1024), ('the crew cards', 12 * 1024),
           ('findings and status', 6 * 1024))


def spec_slice(spec, day=None, channel=None):
    """The spec with only the slots (and experiments) of this day and channel.

    With --day, a slot with no due_at (a krish_click draft) has no day and is left out.
    """
    if day is not None:
        calendar_date(day)
    part = json.loads(json.dumps(spec))
    part['slots'] = [s for s in spec['slots']
                     if (channel is None or s['channel'] == channel)
                     and (day is None or (s['due_at'] is not None and ny_time(s['due_at']).date().isoformat() == day))]
    if channel is not None:
        part['experiments'] = [x for x in spec['experiments'] if x['channel'] == channel]
    return part


def _entries(registry):
    entries = registry.get('crew') if isinstance(registry, dict) else registry
    if isinstance(entries, dict):
        entries = [dict(value, id=key) for key, value in sorted(entries.items()) if isinstance(value, dict)]
    if not isinstance(entries, list):
        raise ValueError('crew/registry.json has no crew list')
    return [entry for entry in entries if isinstance(entry, dict) and isinstance(entry.get('id'), str)]


def week_flag(spec):
    """The registry flag for this run's week, such as "w45" for the week of 2 November 2026."""
    return 'w%02d' % monday(spec['window']['start']).isocalendar()[1]


def in_play(entry, channels, flag=None, narrowed=False):
    """A crew member is in play when the registry flags it for this week, else by channel.

    A week flag (true or false) overrides the channel match; --channel still narrows it.
    """
    overlap = bool(set(entry.get('channels') or []) & set(channels))
    if flag and flag in entry:
        return entry[flag] is True and (overlap or not narrowed)
    return bool(entry.get('always')) or overlap


def crew_cards(channels, root=ROOT, flag=None, narrowed=False):
    """(cards, findings) for the crew in play (see in_play)."""
    root = Path(root)
    path = root / 'crew' / 'registry.json'
    if not path.is_file():
        return [], ['crew/registry.json is not built yet; no crew cards loaded']
    try:
        entries = _entries(read_json(path))
    except (ValueError, OSError) as exc:
        return [], ['crew/registry.json is unreadable: ' + str(exc)]
    cards, findings = [], []
    for entry in entries:
        if not in_play(entry, channels, flag, narrowed):
            continue
        ref = entry.get('card') or 'crew/' + entry['id'] + '/card.md'
        card = (root / ref).resolve()
        try:
            card.relative_to((root / 'crew').resolve())
        except ValueError:
            findings.append('card for ' + entry['id'] + ' is outside crew/; not loaded')
            continue
        if not card.is_file():
            findings.append('card for ' + entry['id'] + ' is missing: ' + ref)
        elif card.stat().st_size > MAX_CARD:
            findings.append('card for ' + entry['id'] + ' is over 3 KB; not loaded')
        else:
            cards.append((ref, card.read_text(encoding='utf-8-sig').strip()))
    return cards, findings


def compile_pack(spec, day=None, channel=None, runs=None, root=ROOT, records=None):
    validate(spec, read_json(SCHEMA))
    part = spec_slice(spec, day, channel)
    ids = {s['slot_id'] for s in part['slots']}
    found = lint(spec, records, root)
    keep = [f for f in found['errors'] + found['warnings'] if f['slot_id'] is None or f['slot_id'] in ids]
    findings = []
    try:
        rows = [r for r in status(spec, runs, root)['slots'] if r['slot_id'] in ids]
    except (ValueError, OSError) as exc:
        rows, findings = [], ['status unavailable: ' + str(exc)]
    cards, more = crew_cards(sorted({s['channel'] for s in part['slots']}), root, week_flag(spec),
                             day is not None or channel is not None)
    findings += more
    run_doc = (Path(root) / 'docs' / 'RUN.md').read_text(encoding='utf-8-sig').strip()
    parts = ['## docs/RUN.md\n\n' + run_doc,
             '## Spec slice\n\n' + json.dumps(part, ensure_ascii=False, indent=1),
             '## Crew cards in play\n\n' + ('\n\n'.join('### ' + ref + '\n\n' + text for ref, text in cards) or 'none loaded'),
             '\n\n'.join(['## Lint findings for this slice\n\n' + (json.dumps(keep, ensure_ascii=False, indent=1) if keep else 'none'),
                          '## Status (computed from evidence)\n\n' + (json.dumps(rows, indent=1) if rows else 'no slots'),
                          '## Pack findings\n\n' + ('\n'.join('- ' + f for f in findings) or 'none')])]
    blocks = ['# Run pack: ' + spec['run_id'] + ' (day ' + (day or 'all') + ', channel ' + (channel or 'all') + ')',
              'Lint: ' + str(len(found['errors'])) + ' errors, ' + str(len(found['warnings'])) + ' warnings in the whole spec.']
    text = '\n\n'.join(blocks + parts) + '\n'
    size = len(text.encode('utf-8'))
    if size > MAX_BYTES:
        raise ValueError('pack is ' + str(size) + ' bytes; the limit is ' + str(MAX_BYTES) + '. Narrow it with --day or --channel')
    for (name, budget), block in zip(BUDGETS, parts):
        size = len(block.split('\n\n', 1)[1].encode('utf-8'))  # the body, without its heading
        if size > budget:
            raise ValueError(name + ' is ' + str(size) + ' bytes; its budget is ' + str(budget)
                             + '. Narrow it with --day or --channel')
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run', description='Compile a session pack of at most 36 KB. Offline.')
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('pack')
    p.add_argument('spec')
    p.add_argument('--day', help='YYYY-MM-DD in New York')
    p.add_argument('--channel')
    p.add_argument('--runs-dir', help='evidence root (default .scratch/runs)')
    p.add_argument('--out')
    args = parser.parse_args(argv)
    try:
        text = compile_pack(read_json(args.spec), args.day, args.channel, args.runs_dir)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding='utf-8')
        print('pack written locally: ' + args.out + ' (' + str(len(text.encode('utf-8'))) + ' bytes)')
    elif hasattr(sys.stdout, 'buffer'):
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode('utf-8'))  # Windows consoles need not be UTF-8.
        sys.stdout.buffer.flush()
    else:
        print(text, end='')
    return 0
