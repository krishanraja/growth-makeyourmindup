"""The content backlog: every published piece against the channels and formats it could run on.

Discovery reads the public feed in a 21-day window for the day's work. The
backlog reads it as far back as the feed reaches (up to 366 days) and merges
the local catalog state (`growth.py discover`), so older pieces stay visible
after they leave the feed. Each piece is matched against the native editions
already made of it: the committed pilot records (lists/pilots.json) and the
local amplification ledger (.scratch/backlog/amplified.json, written by
`growth.py backlog record`). The inventory is ordered oldest unamplified
first, then partly amplified, then covered.

Published pieces and Krish's own native post URLs are public, but the live
inventory and ledger are working state, so they stay in ignored .scratch/.
Only the schemas and a synthetic fixture are committed (backlog/).
Nothing here posts, sends or writes outside .scratch/.
"""
import argparse
import json
from pathlib import Path

from .catalog import discover, parse_feed, pieces as read_feed
from .core import canonical, http_url, instant, locked, read_json, write_json
from .social import inventory as social_inventory, validate

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SCHEMA = ROOT / 'backlog' / 'inventory.schema.json'
LEDGER_SCHEMA = ROOT / 'backlog' / 'amplified.schema.json'
LOCAL = Path('.scratch') / 'backlog'
LEDGER = LOCAL / 'amplified.json'
INVENTORY = LOCAL / 'inventory.json'
CATALOG = Path('.scratch') / 'catalog.json'
PILOTS = Path('lists') / 'pilots.json'
# The piece's own home is where it was published, so it is never an open edition.
HOME_CHANNELS = ('substack',)
STATUSES = ('unamplified', 'partial', 'covered')
FEED_DAYS = 366


def channel_matrix(root=ROOT):
    """{channel: [formats]} for every channel a piece can be amplified on, from the social records."""
    records = social_inventory(Path(root))['channel']
    return {cid: list(rec['formats']) for cid, rec in sorted(records.items()) if cid not in HOME_CHANNELS}


def _edition(entry, matrix, source, at):
    if not isinstance(entry, dict):
        raise ValueError(at + ' must be an object')
    channel, fmt = entry.get('channel'), entry.get('format')
    if channel not in matrix:
        raise ValueError(at + ': unknown amplification channel ' + repr(channel))
    if fmt is not None and fmt not in matrix[channel]:
        raise ValueError(at + ': ' + repr(fmt) + ' is not a format of ' + channel)
    native = entry.get('native_url')
    if native is not None and not (http_url(native) and native.startswith('https://')):
        raise ValueError(at + ': native_url must be an https URL')
    return {'channel': channel, 'format': fmt, 'source': source, 'native_url': native}


def pilot_editions(root=ROOT, matrix=None):
    """{piece url: [editions]} from the committed pilot records that name their piece."""
    matrix = matrix or channel_matrix(root)
    path = Path(root) / PILOTS
    out = {}
    if not path.exists():
        return out
    for i, pilot in enumerate(read_json(path).get('pilots') or []):
        url = pilot.get('piece_url') if isinstance(pilot, dict) else None
        if not url:
            continue
        at = str(PILOTS) + ' pilots[' + str(i) + ']'
        listed = pilot.get('editions') or [{'channel': c, 'format': None} for c in pilot.get('channels') or []]
        out.setdefault(canonical(url), []).extend(
            _edition(e, matrix, 'pilot', at + '.editions[' + str(j) + ']') for j, e in enumerate(listed))
    return out


def read_ledger(path, matrix):
    """{piece url: [editions]} from the local amplification ledger; absent means empty."""
    path = Path(path)
    if not path.exists():
        return {}
    value = read_json(path)
    validate(value, read_json(LEDGER_SCHEMA))
    out = {}
    for i, entry in enumerate(value['editions']):
        at = str(path) + ' editions[' + str(i) + ']'
        if not http_url(entry['piece_url']):
            raise ValueError(at + ': piece_url must be an http(s) URL')
        instant(entry['at'])
        out.setdefault(canonical(entry['piece_url']), []).append(_edition(entry, matrix, 'ledger', at))
    return out


def record(path, piece_url, channel, fmt, native_url, at, root=ROOT):
    """Add one live native edition to the local ledger. Local only; idempotent on the same edition."""
    matrix = channel_matrix(root)
    entry = {'piece_url': canonical(piece_url), 'channel': channel, 'format': fmt,
             'native_url': native_url, 'at': instant(at).isoformat()}
    _edition(entry, matrix, 'ledger', 'the edition')
    path = Path(path)
    with locked(path):
        value = read_json(path) if path.exists() else {'schema_version': 1, 'editions': []}
        validate(value, read_json(LEDGER_SCHEMA))
        same = [e for e in value['editions'] if (e['piece_url'], e['channel'], e['format'], e['native_url'])
                == (entry['piece_url'], channel, fmt, native_url)]
        if not same:
            value['editions'].append(entry)
            validate(value, read_json(LEDGER_SCHEMA))
            write_json(path, value)
    return not same


def build(rows, catalog=None, editions=None, root=ROOT, now=None, feed_days=FEED_DAYS, sources=None):
    """The inventory: each piece, its editions and the channels still open, oldest unamplified first.

    A video post with an explicit published link to its article is folded into
    that article (catalog.discover's verified pairs); similar titles never pair."""
    matrix = channel_matrix(root)
    editions = editions if editions is not None else {}
    state = discover(rows, catalog, now)
    entries = state['pieces']
    folded = {p['video_id']: p['article_id'] for p in state['verified_pairs']}
    out = []
    for pid, row in entries.items():
        if pid in folded:
            continue
        urls = [row['url']] + sorted(entries[v]['url'] for v, a in folded.items() if a == pid)
        made = [e for url in urls for e in editions.get(canonical(url), [])]
        done = {e['channel'] for e in made}
        open_channels = [c for c in matrix if c not in done]
        status = 'unamplified' if not made else ('partial' if open_channels else 'covered')
        out.append({'piece_id': pid, 'url': row['url'], 'title': row['title'], 'kind': row['kind'],
                    'published_at': instant(row['published_at']).isoformat(),
                    'video_post_url': urls[1] if len(urls) > 1 else None,
                    'status': status, 'editions': made, 'channels_open': open_channels})
    out.sort(key=lambda p: (STATUSES.index(p['status']), p['published_at'], p['piece_id']))
    summary = {'pieces': len(out), 'remaining': sum(p['status'] == 'unamplified' for p in out),
               'partial': sum(p['status'] == 'partial' for p in out),
               'covered': sum(p['status'] == 'covered' for p in out),
               'editions_open': sum(len(p['channels_open']) for p in out)}
    result = {'schema_version': 1, 'kind': 'backlog_inventory', 'observed_at': instant(now).isoformat(),
              'feed_days': feed_days, 'sources': list(sources or []),
              'channels': [{'channel': c, 'formats': f} for c, f in matrix.items()],
              'summary': summary, 'pieces': out}
    validate(result, read_json(INVENTORY_SCHEMA))
    return result


def oldest_unamplified(inventory, limit=3):
    return [p for p in inventory['pieces'] if p['status'] == 'unamplified'][:limit]


def summary_line(inventory, where=None):
    """One plain report line: 'Backlog remaining N ...', oldest unamplified first."""
    s = inventory['summary']
    line = ('Backlog remaining ' + str(s['remaining']) + ': ' + str(s['remaining']) + ' of ' + str(s['pieces'])
            + ' published pieces have no native edition yet, ' + str(s['partial']) + ' partly amplified, '
            + str(s['editions_open']) + ' channel editions open')
    first = oldest_unamplified(inventory, 1)
    if first:
        line += '. Oldest unamplified: ' + first[0]['title'] + ' (' + first[0]['published_at'][:10] + ')'
    if where:
        line += '. ' + where
    return line


def for_runner(root=ROOT, now=None, fetch=None):
    """(inventory, None) or (None, reason) on a clean runner: the public feed and the committed
    pilot records only, since the workspace ledger never leaves .scratch/."""
    try:
        rows = (fetch or read_feed)(FEED_DAYS, now)
        return build(rows, None, pilot_editions(root), root, now, FEED_DAYS, ['public feed', str(PILOTS)]), None
    except (ValueError, KeyError, TypeError, OSError):
        return None, 'the public feed or the pilot records could not be read on this run'


def command(argv, root=ROOT):
    parser = argparse.ArgumentParser(prog='growth.py backlog',
                                     description='Every published piece against channel and format, oldest unamplified first. Local only.')
    parser.add_argument('action', nargs='?', choices=('list', 'record'), default='list')
    parser.add_argument('--days', type=int, default=FEED_DAYS)
    parser.add_argument('--feed-file')
    parser.add_argument('--catalog', default=str(CATALOG))
    parser.add_argument('--ledger', default=str(LEDGER))
    parser.add_argument('--out', default=str(INVENTORY))
    parser.add_argument('--now')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--piece'); parser.add_argument('--channel'); parser.add_argument('--format')
    parser.add_argument('--native-url'); parser.add_argument('--at')
    args = parser.parse_args(argv)
    if args.action == 'record':
        missing = [n for n in ('piece', 'channel', 'native_url', 'at') if not getattr(args, n)]
        if missing:
            raise ValueError('backlog record needs --' + ', --'.join(m.replace('_', '-') for m in missing))
        added = record(args.ledger, args.piece, args.channel, args.format, args.native_url, args.at, root)
        print(('recorded locally in ' if added else 'already recorded in ') + args.ledger + '; no external write')
        return 0
    rows = parse_feed(Path(args.feed_file).read_bytes(), args.days, args.now) if args.feed_file else read_feed(args.days, args.now)
    catalog = read_json(args.catalog) if Path(args.catalog).exists() else None
    matrix = channel_matrix(root)
    editions = pilot_editions(root, matrix)
    for url, made in read_ledger(args.ledger, matrix).items():
        editions.setdefault(url, []).extend(made)
    sources = ['public feed' if not args.feed_file else 'feed file', str(PILOTS)]
    sources += [args.catalog] if catalog else []
    sources += [args.ledger] if Path(args.ledger).exists() else []
    result = build(rows, catalog, editions, root, args.now, args.days, sources)
    write_json(args.out, result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    for piece in result['pieces']:
        print(piece['status'].ljust(12) + piece['published_at'][:10] + '  ' + piece['title'] + '\n  ' + piece['url']
              + ('\n  open: ' + ', '.join(piece['channels_open']) if piece['channels_open'] else ''))
    print(summary_line(result) + '. Written locally to ' + args.out + '; no external write.')
    return 0
