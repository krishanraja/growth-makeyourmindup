"""`growth.py ledger`: one row per day per slot, the one place that answers "what is happening on day X".

Ruling (Krish, 2026-10-31): this repository is responsible for automatically scheduling and posting
everything, and for staying on top of what's what, where everything is, and what needs to be done every
day (docs/OPERATING_MODEL.md, sections 0, 3 and 4).

Fourteen days from today (UTC), one row a day: the hero on Monday, Wednesday and Friday, the off-day post
on Tuesday, Thursday, Saturday and Sunday. Each row says its stage (1 to 7, OPERATING_MODEL section 3),
its links, its next action, who owns it, when it is due and what has gone out.

Inputs, all read-only and each optional:

- content-engine's board: GET /api/board/<Monday>/pieces (which piece sits on which day, and Krish's
  one press on the week's mix) and GET /api/board/<Monday> (the published build's manifest), with
  GROWTH_WRITEBACK_TOKEN through the board tick's client (engine/run/board_tick.py);
- Buffer: sent and scheduled posts on this engine's eight pinned channels, through the measure job's
  reader (engine/run/buffer_reads.py) with BUFFER_API_KEY.

A missing secret never fails the build: the row is written with what was readable, and its next action
names the secret. `--fixtures DIR` (or GROWTH_LEDGER_FIXTURES) reads the same inputs from files, for tests.
Nothing here posts, schedules, ticks or writes anywhere but calendar/ (with --write).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

from .buffer_channels import BUFFER_CHANNEL_ID
from .core import calendar_date, instant, ny_time, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'growth-ledger/1'
DAYS = 14
BOARD_SITE = 'https://content.krishraja.com'
DAY_KEYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
# The publication's rhythm (content-engine api/board/_posted.ts DAY_SERIES; OPERATING_MODEL section 0).
SERIES = {0: 'follow.the.money', 2: 'under.the.hood', 4: 'mind.the.gap'}
HERO_FORMAT = 'video + article'
STAGES = {1: 'inspired', 2: 'ideate', 3: 'agree', 4: 'flesh out', 5: 'produce', 6: 'post-produce', 7: 'post'}
# The piece's own slot in New York: the series slot (mix.json reserved.time) and the board's off-day default
# (content-engine api/board/_posted.ts OFF_DAY_SLOT) until a piece names its own.
SLOT_TIME = '12:30'
# A board piece's making state, where the pieces read carries one, as a stage. Anything else stays at 4.
PIECE_STATES = {'idea': 2, 'proposed': 2, 'picked': 3, 'locked': 4, 'scripted': 4, 'recorded': 5, 'produced': 5,
                'cut': 6, 'review': 6, 'approved': 6, 'sealed': 6, 'scheduled': 7, 'published': 7, 'posted': 7}
BOARD_SECRET = 'GROWTH_WRITEBACK_TOKEN'
BUFFER_SECRET = 'BUFFER_API_KEY'
FIXTURES_ENV = 'GROWTH_LEDGER_FIXTURES'
CHANNEL_OF_ID = {cid: channel for channel, cid in BUFFER_CHANNEL_ID.items()}
HEX64 = re.compile(r'^[0-9a-f]{64}$')
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
HHMM = re.compile(r'^\d\d:\d\d$')


def monday_of(day):
    return day - dt.timedelta(days=day.weekday())


def missing(secret):
    return 'missing_secret:' + secret


# Inputs -------------------------------------------------------------------------------------------------


def _error_code(exc):
    code = getattr(exc, 'code', None)
    return code if isinstance(code, str) and re.match(r'^[a-z][a-z0-9_]{0,63}$', code) else type(exc).__name__


def read_board(board, mondays):
    """{monday: {'pieces', 'pieces_status', 'manifest', 'build_id', 'manifest_status'}} from a board client.

    board is board_tick.Board (or a stand-in with pieces() and week()), or None when its secret is unset."""
    out = {}
    for monday in mondays:
        week = {'pieces': None, 'manifest': None, 'build_id': None}
        if board is None:
            week['pieces_status'] = week['manifest_status'] = missing(BOARD_SECRET)
            out[monday] = week
            continue
        try:
            listed = board.pieces(monday)
            week['pieces'] = listed if isinstance(listed, dict) else None
            week['pieces_status'] = 'read' if week['pieces'] is not None else 'error:board_bad_response'
        except Exception as exc:  # a failed read leaves the row with what else was readable
            week['pieces_status'] = 'error:' + _error_code(exc)
        try:
            state = board.week(monday)
            manifest = state.get('manifest') if isinstance(state, dict) else None
            week['manifest'] = manifest if isinstance(manifest, dict) else None
            build = state.get('build_id') if isinstance(state, dict) else None
            week['build_id'] = build if isinstance(build, str) and HEX64.match(build) else None
            week['manifest_status'] = 'read' if week['manifest'] else 'not_published'
        except Exception as exc:
            code = _error_code(exc)
            week['manifest_status'] = 'not_published' if code in ('board_not_published', 'board_not_found') \
                else 'error:' + code
        out[monday] = week
    return out


def _channel_id(post):
    channel = post.get('channel') if isinstance(post.get('channel'), dict) else {}
    return channel.get('id') or post.get('channelId')


def normalise_posts(listed):
    """This engine's posts (pinned by channelId) as {post_id, channel, status, due_at, sent_at, url}. Pure."""
    if isinstance(listed, dict):
        listed = listed.get('posts') or [e.get('node') for e in listed.get('edges') or [] if isinstance(e, dict)]
    out = []
    for post in listed if isinstance(listed, list) else []:
        if not isinstance(post, dict) or not isinstance(post.get('id'), str):
            continue
        channel = CHANNEL_OF_ID.get(_channel_id(post))
        if channel is None or post.get('status') not in ('scheduled', 'sending', 'sent'):
            continue
        if post.get('via') == 'network':  # imported, not this engine's publication (buffer_reads F17)
            continue
        url = post.get('externalLink')
        out.append({'post_id': post['id'], 'channel': channel, 'status': post['status'],
                    'due_at': post.get('dueAt') if isinstance(post.get('dueAt'), str) else None,
                    'sent_at': post.get('sentAt') if isinstance(post.get('sentAt'), str) else None,
                    'url': url if isinstance(url, str) and url.startswith('https://') else None})
    return out


def read_buffer(client, since, why=None):
    """{'posts': [...], 'status'} from a Buffer reader with list_posts(status, since), or its reason."""
    if client is None:
        return {'posts': [], 'status': missing(BUFFER_SECRET) if why in (None, 'Buffer not configured')
                else 'error:' + re.sub(r'[^a-z0-9_]+', '_', str(why).lower()).strip('_')}
    try:
        sent = client.list_posts(status='sent', since=since)
        live = client.list_posts(status=['scheduled', 'sending'], since=since)
    except Exception as exc:
        from .run.buffer_reads import refused
        return {'posts': [], 'status': 'error:' + ('buffer_key_refused' if refused(exc) else _error_code(exc))}
    posts = {p['post_id']: p for p in normalise_posts(live)}
    posts.update({p['post_id']: p for p in normalise_posts(sent)})
    return {'posts': sorted(posts.values(), key=lambda p: (p['due_at'] or '', p['post_id'])), 'status': 'read'}


class Fixtures:
    """The same inputs from files: pieces-<Monday>.json, board-<Monday>.json, buffer-sent.json and
    buffer-scheduled.json. A file that is absent reads as its secret being unset; secrets.json may list
    which secrets to treat as set or unset ({"GROWTH_WRITEBACK_TOKEN": false})."""

    def __init__(self, folder):
        self.folder = Path(folder)
        flags = self.folder / 'secrets.json'
        self.secrets = read_json(flags) if flags.exists() else {}

    def _has(self, secret):
        return self.secrets.get(secret, True) is not False

    def _file(self, name):
        path = self.folder / name
        return read_json(path) if path.exists() else None

    def board(self):
        if not self._has(BOARD_SECRET):
            return None
        fixtures = self

        class Board:
            def pieces(self, monday):
                value = fixtures._file('pieces-' + monday + '.json')
                if value is None:
                    raise LookupError('pieces fixture missing')
                return value

            def week(self, monday):
                value = fixtures._file('board-' + monday + '.json')
                if value is None:
                    error = LookupError('board_not_published')
                    error.code = 'board_not_published'
                    raise error
                return value

        return Board()

    def buffer(self):
        if not self._has(BUFFER_SECRET):
            return None, None
        fixtures = self

        class Client:
            def list_posts(self, status=None, since=None):
                name = 'buffer-sent.json' if status == 'sent' else 'buffer-scheduled.json'
                return fixtures._file(name) or []

        return Client(), None


def live_board():
    from .run.board_tick import board_from_env
    return board_from_env()


def live_buffer():
    from .run.buffer_reads import buffer_client
    return buffer_client(links=True)


# The rows -----------------------------------------------------------------------------------------------


def _pieces_days(listed):
    """{day key: entry} from the pieces read, keeping the fields the ledger uses. Pure."""
    days = {}
    for entry in listed.get('days') if isinstance(listed, dict) and isinstance(listed.get('days'), list) else []:
        if isinstance(entry, dict) and entry.get('day') in DAY_KEYS and isinstance(entry.get('piece_id'), str) \
                and UUID.match(entry['piece_id']):
            days[entry['day']] = entry
    return days


def _mix(listed):
    mix = listed.get('mix') if isinstance(listed, dict) else None
    if not isinstance(mix, dict) or not isinstance(mix.get('days'), dict):
        return None
    return {'approved': mix.get('approved') is True, 'days': mix['days'],
            'mix_sha256': mix.get('mix_sha256') if isinstance(mix.get('mix_sha256'), str) else None}


def manifest_sha256(week):
    """The published build's id (sha256 of the canonical manifest), or the sha256 of the manifest as read."""
    if week.get('build_id'):
        return week['build_id']
    manifest = week.get('manifest')
    if not isinstance(manifest, dict):
        return None
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _text(value):
    return ' '.join(value.split()) if isinstance(value, str) and value.strip() else None


def title_of_record(entry, manifest, key):
    """The piece's title of record, else the day's board title, else None. Pure."""
    for field in ('title_of_record', 'title'):
        if _text((entry or {}).get(field)):
            return _text(entry[field])
    if _text((entry or {}).get('board_title')):
        return _text(entry['board_title'])
    days = manifest.get('days') if isinstance(manifest, dict) else None
    day = days.get(key) if isinstance(days, dict) else None
    return _text(day.get('title')) if isinstance(day, dict) else None


def _on_slot(posts, date, hhmm):
    out = []
    for post in posts:
        if not post.get('due_at'):
            continue
        local = ny_time(instant(post['due_at']))
        if local.date() == date and local.strftime('%H:%M') == hhmm:
            out.append(post)
    return out


def row(date, weeks, buffer):
    """One ledger row for one date. Pure: weeks from read_board, buffer from read_buffer."""
    weekday = date.weekday()
    key = DAY_KEYS[weekday]
    hero = weekday in SERIES
    monday = monday_of(date).isoformat()
    sunday_before = (monday_of(date) - dt.timedelta(days=1)).isoformat()
    week = weeks.get(monday) or {'pieces_status': missing(BOARD_SECRET), 'manifest_status': missing(BOARD_SECRET)}
    board_read = week.get('pieces_status') == 'read'
    entry = _pieces_days(week.get('pieces')).get(key) if board_read else None
    mix = _mix(week.get('pieces')) if board_read else None
    slot_time = SLOT_TIME
    if entry and not hero and isinstance(entry.get('slot'), str) and HHMM.match(entry['slot']):
        slot_time = entry['slot']
    posts = _on_slot(buffer['posts'], date, slot_time) if buffer['status'] == 'read' else []
    sent = [p for p in posts if p['status'] == 'sent']
    queued = [p for p in posts if p['status'] in ('scheduled', 'sending')]
    fmt = HERO_FORMAT if hero else None
    if not hero:
        if entry and _text(entry.get('format')):
            fmt = _text(entry['format'])
        elif mix and mix['days'].get(key):
            fmt = ', '.join(str(k) for k in mix['days'][key])
    stage, action, owner, due = None, None, None, date.isoformat()
    when = slot_time + ' New York'
    if sent:
        stage, owner = 7, 'growth'
        action = 'Measure it at 24h, 72h and 7d, and tick the board for each sent post'
        due = (date + dt.timedelta(days=1)).isoformat()
        if queued:
            action = 'Read back the ' + str(len(queued)) + ' still scheduled, then measure at 24h, 72h and 7d'
    elif queued:
        stage, owner = 7, 'growth'
        action = 'Goes out at ' + when + ' on ' + ', '.join(sorted({p['channel'] for p in queued})) \
            + '; read back the native URLs'
    elif not board_read:
        status = week.get('pieces_status') or missing(BOARD_SECRET)
        owner = 'krish' if status.startswith('missing_secret:') else 'growth'
        action = ('Set ' + BOARD_SECRET + ' so the ledger can read the board' if owner == 'krish'
                  else 'Board read failed (' + status[len('error:'):] + '); rerun the ledger')
    elif hero and entry:
        stage = PIECE_STATES.get(str(entry.get('state') or entry.get('stage') or '').lower(), 4)
        if stage >= 6:
            owner = 'growth'
            action = 'Schedule the sealed cut in Buffer for ' + when
        elif stage == 5:
            owner = 'content-engine'
            action = 'Make the hero assets from the recording and seal the manifest'
        else:
            owner = 'content-engine'
            action = 'make-piece: lock, scripts to Teleprompter, then Krish records'
    elif hero:
        stage, owner, due = 3, 'krish', sunday_before
        action = "Pick this day's idea on the board"
    elif entry:
        stage, owner = 5, 'growth'
        action = 'Make the off-day post from its approved mock and schedule it for ' + when
    elif mix and mix['approved'] and mix['days'].get(key):
        stage, owner = 5, 'growth'
        action = 'Make ' + fmt + ' from the approved mix and schedule it for ' + when
    elif mix and mix['approved']:
        stage, owner = 3, 'growth'
        action = 'The approved mix has nothing for this day: propose an off-day option'
    elif mix:
        stage, owner, due = 3, 'krish', sunday_before
        action = "Approve this week's mix on the board (his last press was not an approval)"
    else:
        stage, owner, due = 3, 'krish', sunday_before
        action = "Approve this week's mix on the board, or pick an off-day option"
    if buffer['status'] != 'read' and stage is not None and stage >= 5 and not sent:
        action += ' (Buffer unread: ' + (('set ' + BUFFER_SECRET) if buffer['status'].startswith('missing_secret:')
                                         else buffer['status'][len('error:'):]) + ')'
    return {
        'date': date.isoformat(), 'weekday': WEEKDAYS[weekday], 'slot': 'hero' if hero else 'off-day',
        'series': SERIES.get(weekday), 'format': fmt,
        'piece_id': entry['piece_id'] if entry else None,
        'title_of_record': title_of_record(entry, week.get('manifest'), key),
        'stage': stage, 'stage_name': STAGES.get(stage),
        'assets': {'board_url': BOARD_SITE + '/board/' + monday + '#' + key,
                   'drive_folder': _text((entry or {}).get('drive_folder')),
                   'manifest_sha256': manifest_sha256(week)},
        'next_action': action, 'owner': owner, 'due': due,
        'posted': [{'channel': p['channel'], 'url': p['url'], 'buffer_post_id': p['post_id']} for p in sent],
        'sources': {'board_pieces': week.get('pieces_status'), 'board_manifest': week.get('manifest_status'),
                    'buffer': buffer['status'],
                    'mix': ('approved' if mix and mix['approved'] else 'pressed_not_approved' if mix
                            else 'not_pressed' if board_read else week.get('pieces_status'))},
    }


def build(start, days, weeks, buffer, built_at=None):
    """The ledger document. Pure."""
    dates = [start + dt.timedelta(days=n) for n in range(days)]
    rows = [row(d, weeks, buffer) for d in dates]
    return {'schema': SCHEMA, 'built_at': instant(built_at).isoformat().replace('+00:00', 'Z'),
            'from': dates[0].isoformat(), 'days': days,
            'ruling': "Krish, 2026-10-31: Growth schedules and posts everything and keeps track of what's what",
            'stages': {str(k): v for k, v in STAGES.items()}, 'rows': rows}


def gather(start, days, fixtures=None, now=None):
    """(weeks, buffer) read live, or from fixtures."""
    mondays = sorted({monday_of(start + dt.timedelta(days=n)).isoformat() for n in range(days)})
    source = Fixtures(fixtures) if fixtures else None
    board = source.board() if source else live_board()
    client, why = source.buffer() if source else live_buffer()
    since = (dt.datetime.combine(start, dt.time(0), tzinfo=dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
    return read_board(board, mondays), read_buffer(client, since, why)


# LEDGER.md ----------------------------------------------------------------------------------------------


def _cell(value):
    return str(value).replace('|', '/').replace('\n', ' ') if value not in (None, '') else '-'


def markdown(ledger):
    lines = ['# Ledger', '',
             'Built by `python growth.py ledger --write` (`.github/workflows/ledger.yml`, daily 04:05 UTC) at '
             + ledger['built_at'] + '. One row per day per slot; the full record is `calendar/ledger.json`.',
             'Stages: ' + ', '.join(k + ' ' + v for k, v in ledger['stages'].items()) + '.', '',
             '| Date | Slot | Title | Stage | Next action | Owner |', '|---|---|---|---|---|---|']
    for r in ledger['rows']:
        date = r['weekday'][:3] + ' ' + r['date']
        slot = r['slot'] + (', ' + r['series'] if r['series'] else '')
        title = r['title_of_record'] or ('piece `' + r['piece_id'][:8] + '`, no title of record yet'
                                         if r['piece_id'] else None)
        stage = (str(r['stage']) + ' ' + r['stage_name']) if r['stage'] else 'unknown'
        lines.append('| ' + ' | '.join(_cell(v) for v in (date, slot, title, stage, r['next_action'], r['owner']))
                     + ' |')
    return '\n'.join(lines) + '\n'


# The command --------------------------------------------------------------------------------------------


def summary(ledger):
    """Counts only: this repository is public, so the log carries no titles."""
    stages, owners, sources = {}, {}, {}
    for r in ledger['rows']:
        stages[str(r['stage'])] = stages.get(str(r['stage']), 0) + 1
        owners[str(r['owner'])] = owners.get(str(r['owner']), 0) + 1
        for name, status in r['sources'].items():
            sources.setdefault(name, set()).add(status)
    return {'rows': len(ledger['rows']), 'from': ledger['from'], 'stages': stages, 'owners': owners,
            'sources': {k: sorted(v) for k, v in sorted(sources.items())}}


def command(argv, root=ROOT, now=None, out=print):
    parser = argparse.ArgumentParser(prog='growth.py ledger', description='What is happening on each day. Read-only.')
    parser.add_argument('--week', help='start on this Monday (YYYY-MM-DD) instead of today (UTC)')
    parser.add_argument('--days', type=int, default=DAYS)
    parser.add_argument('--today', help='today (UTC) as YYYY-MM-DD, for tests')
    parser.add_argument('--fixtures', help='read the inputs from this folder instead of the network')
    parser.add_argument('--write', action='store_true', help='write calendar/ledger.json and calendar/LEDGER.md')
    parser.add_argument('--json', action='store_true', help='print the whole ledger')
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 42:
        raise ValueError('--days must be 1 to 42')
    if args.week:
        start = calendar_date(args.week)
        if start.weekday() != 0:
            raise ValueError('--week must be a Monday')
    else:
        start = calendar_date(args.today) if args.today else instant(now).date()
    fixtures = args.fixtures or (os.environ.get(FIXTURES_ENV) or '').strip() or None
    weeks, buffer = gather(start, args.days, fixtures, now)
    ledger = build(start, args.days, weeks, buffer, now)
    if args.write:
        folder = Path(root) / 'calendar'
        write_json(folder / 'ledger.json', ledger)
        with open(folder / 'LEDGER.md', 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(markdown(ledger))
    if args.json:
        out(json.dumps(ledger, indent=2, ensure_ascii=False))
    else:
        out('ledger: ' + json.dumps(summary(ledger), sort_keys=True)
            + ('; written to calendar/ledger.json and calendar/LEDGER.md' if args.write else ''))
    return 0
