"""`growth.py run board tick [--deliver]`: tick the week's publish board for each post Growth made.

Krish, 29 October 2026: "we need the growth repo to keep the publish board check
boxes update with what it has done and when". Content-engine's board takes one
write per post (content-engine PR #267):

    POST https://content.krishraja.com/api/board/<Monday>/posted
    Authorization: Bearer $GROWTH_WRITEBACK_TOKEN
    {"day", "piece_id", "channel", "post_url", "posted_at", "buffer_post_id"}

200 answers filed or duplicate (a replay of the same post is harmless, so a
clean runner needs no ledger), 409 not_this_day when the piece is not that
day's. The board says which piece sits on which day and which boxes it has
(`GET .../<Monday>/pieces`), so nothing here keeps a map by hand.

A post counts for a day's piece only when Buffer shows it sent, on this
engine's pinned channel (buffer_reads.sent_posts), at that day's reserved
series slot (mix.json `reserved`: the piece's own cut takes 12:30 New York on
Monday, Wednesday and Friday), with a native URL on the channel's own host
(release.native_host). A mix post at another time is never ticked as the
piece. Off-day boxes tick the same way once the board lists them for a day
with their own `slot` time.

Runs after release on its 30-minute schedule (.github/workflows/release.yml).
Without GROWTH_WRITEBACK_TOKEN it says the board is not configured and exits
0. Without --deliver it reads Buffer and the board and posts nothing. The log
carries counts and codes only: this repository is public.
"""
import argparse
import datetime as dt
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request

from ..core import instant, ny_time
from .. import mix as mix_rules
from .buffer_reads import buffer_client, sent_posts
from .release import load_accounts, native_host

BOARD = 'https://content.krishraja.com'
TOKEN_ENV = 'GROWTH_WRITEBACK_TOKEN'
NOT_CONFIGURED = 'board not configured'
TIMEOUT = 20
MAX_RESPONSE = 1000000
LOOKBACK = dt.timedelta(days=3)
DAY_KEYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
PIECE_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
# This engine's channel id -> the board's box names it may fill, first match wins. The piece's
# vertical cut goes out as a Short, a TikTok and a Reel; X and the rest tick only where the board has a box.
BOXES = {'youtube': ('shorts', 'youtube'), 'tiktok': ('tiktok',), 'instagram': ('reels', 'instagram'),
         'linkedin': ('linkedin',), 'x': ('x',), 'threads': ('threads',), 'facebook': ('facebook',),
         'substack-notes': ('substack-notes',)}


class BoardError(Exception):
    """A board failure named by a lower_snake code. Never carries a body, URL or token."""

    def __init__(self, code, status=None):
        super().__init__(code)
        self.code, self.status = code, status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Board:
    """The two board routes Growth uses. The token is read once and never printed."""

    def __init__(self, token, base=BOARD, opener=None, timeout=TIMEOUT):
        self._token, self._base, self._timeout = token, base.rstrip('/'), timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirect())
        self.requests = 0

    def _request(self, method, route, body=None):
        headers = {'Authorization': 'Bearer ' + self._token, 'Accept': 'application/json'}
        data = None
        if body is not None:
            data = json.dumps(body, sort_keys=True).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self._base + route, data=data, method=method, headers=headers)
        self.requests += 1
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as error:
            server_code = None
            try:
                parsed = json.loads(error.read(4096).decode('utf-8'))
                if isinstance(parsed, dict):
                    server_code = parsed.get('error') or parsed.get('code')
            except (ValueError, OSError, UnicodeDecodeError):
                pass
            finally:
                error.close()
            if isinstance(server_code, str) and CODE.match(server_code):
                raise BoardError(server_code, error.code) from None
            raise BoardError({401: 'board_token_refused', 403: 'board_token_refused', 404: 'board_not_found',
                              409: 'board_conflict', 429: 'board_rate_limited'}.get(
                                  error.code, 'board_server_error' if error.code >= 500 else 'board_rejected'),
                             error.code) from None
        except (urllib.error.URLError, OSError, ValueError) as error:
            reason = getattr(error, 'reason', error)
            raise BoardError('board_timeout' if isinstance(reason, socket.timeout) else 'board_unreachable') from None
        if len(raw) > MAX_RESPONSE:
            raise BoardError('board_response_too_large')
        try:
            result = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise BoardError('board_bad_response') from None
        if not isinstance(result, dict):
            raise BoardError('board_bad_response')
        return result

    def pieces(self, monday):
        return self._request('GET', '/api/board/' + monday + '/pieces')

    def week(self, monday):
        """The week's published build {build_id, revision, manifest}: the ledger's read, on Growth's own key
        (content-engine's /api/board/<Monday>/build; the bare week route answers only the operator)."""
        return self._request('GET', '/api/board/' + monday + '/build')

    def posted(self, monday, row):
        return self._request('POST', '/api/board/' + monday + '/posted', row)

    def mix(self, monday):
        """His one press on the week's mix (picks/mix), or None until he presses. Raises BoardError."""
        return board_mix(self.pieces(monday))

    def approvals(self, monday):
        """(mix, offdays) from one read: his old one press, and each off-day option he approved. Raises BoardError."""
        listed = self.pieces(monday)
        return board_mix(listed), board_offdays(listed)

    def offer(self, monday, doc):
        """Growth's off-day options for the week into the one place their day lives (content-engine offday_items,
        POST /api/board/<Monday>/offdays): each offered on its day; only his press approves or moves one."""
        return self._request('POST', '/api/board/' + monday + '/offdays', doc)

    def posts(self, monday, posts):
        """This engine's own record of each of the week's off-day posts (POST .../offday-posts): made, scheduled with
        its time, live with its link. Never a post it did not post."""
        return self._request('POST', '/api/board/' + monday + '/offday-posts', {'posts': posts})


HEX64 = re.compile(r'^[0-9a-f]{64}$')


def board_mix(listed):
    """The pieces route's `mix`: None until Krish presses, else {approved, days, mix_sha256, at}. Pure.

    Ruling (Krish, 2026-10-30): "approve the week's mix once, let Growth fill it" (content-engine
    docs/GROWTH-HANDOFF.md). Anything not in that shape is BoardError('board_mix_malformed'), never guessed."""
    mix = listed.get('mix') if isinstance(listed, dict) else None
    if mix is None:
        return None
    days = mix.get('days') if isinstance(mix, dict) else None
    if not isinstance(mix, dict) or not isinstance(mix.get('approved'), bool) \
            or not isinstance(mix.get('mix_sha256'), str) or not HEX64.match(mix['mix_sha256']) \
            or not isinstance(days, dict) or any(
                key not in DAY_KEYS or not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds)
                for key, kinds in days.items()) or not isinstance(mix.get('at'), (str, type(None))):
        raise BoardError('board_mix_malformed')
    return {'approved': mix['approved'], 'days': days, 'mix_sha256': mix['mix_sha256'], 'at': mix.get('at')}


OFF_OPTION = re.compile(r'^off-(mon|tue|wed|thu|fri|sat|sun)-([A-Za-z0-9][A-Za-z0-9_.:-]{0,59})$')


def board_offdays(listed):
    """The pieces route's `offdays`: each off-day option Krish approved, idea and direction, as
    [{'day', 'option_id', 'format', 'idea', 'direction', 'mock'}]. Pure; [] on a board that has none.

    Ruling (Krish, 2026-11-01), locking the off-day mock: each option is approved, improved or rejected on its own,
    idea and direction, in place of the one press on the week's mix. Anything not in that shape is
    BoardError('board_offdays_malformed'), never guessed."""
    rows = listed.get('offdays') if isinstance(listed, dict) else None
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise BoardError('board_offdays_malformed')
    out = []
    for row in rows:
        match = OFF_OPTION.match(str(row.get('id') or '')) if isinstance(row, dict) else None
        if not match or row.get('day') != match.group(1) or row.get('option_id') != match.group(2) \
                or not isinstance(row.get('format'), (str, type(None))) \
                or not isinstance(row.get('idea'), (dict, type(None))) or not isinstance(row.get('direction'), (dict, type(None))):
            raise BoardError('board_offdays_malformed')
        out.append({'day': row['day'], 'option_id': row['option_id'], 'format': row.get('format'),
                    'idea': row.get('idea'), 'direction': row.get('direction'), 'mock': row.get('mock'),
                    # His open words on the option, exactly as typed (Krish, 2026-11-02: "it would contain the exact
                    # meme text to put above the meme video"): used word for word, never paraphrased.
                    'note': row.get('note') if isinstance(row.get('note'), str) else None,
                    'approved_at': row.get('approved_at'),
                    # Where its day lives (content-engine offday_items, 2026-11-12): the date the board says it is on,
                    # the item and its version, and the day he moved it from, if he did.
                    'date': row.get('date') if isinstance(row.get('date'), str) else None,
                    'item': row.get('item') if isinstance(row.get('item'), str) else None,
                    'moved_from': row.get('moved_from') if isinstance(row.get('moved_from'), dict) else None})
    return out


OFFDAYS_SCHEMA = 'growth-offdays/1'
LIVE_STATUS = ('scheduled', 'sending')


def offer(board, doc, deliver=False):
    """Hand the week's off-day options (the growth-offdays/1 file growth.py mix offdays writes) to the board, the one
    place their day lives (Ruling, Krish, 2026-11-12: any off-day post or idea moves to any day at his press, and the move
    updates every place that names its day). Counts only. Raises BoardError; ValueError for a file in another shape."""
    if not isinstance(doc, dict) or doc.get('schema') != OFFDAYS_SCHEMA or not isinstance(doc.get('days'), dict):
        raise ValueError('not a ' + OFFDAYS_SCHEMA + ' file')
    monday = str(doc.get('week_of') or '')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', monday) or dt.date.fromisoformat(monday).weekday() != 0:
        raise ValueError('week_of is not a Monday')
    options = sum(len(v) for v in doc['days'].values() if isinstance(v, list))
    summary = {'week': monday, 'options': options, 'deliver': bool(deliver)}
    if not deliver:
        return summary
    result = board.offer(monday, {key: doc[key] for key in ('schema', 'week_of', 'days')})
    for key in ('offered', 'his', 'taken', 'withdrawn'):
        if isinstance(result.get(key), int):
            summary[key] = result[key]
    summary['left'] = len(result.get('left') or []) if isinstance(result.get('left'), list) else 0
    return summary


def placed_options(listed_by_week):
    """{concept_id: (board week, day, option doc id)} for every off-day option he approved, on the day the board says
    it is on now. listed_by_week: {Monday ISO: the pieces read}. Pure."""
    out = {}
    for monday, listed in sorted(listed_by_week.items()):
        for row in board_offdays(listed):
            out[row['option_id']] = (monday, row['day'], 'off-' + row['day'] + '-' + row['option_id'])
    return out


def piece_days(listed_by_week):
    """{date ISO: (board week, day key, piece id)} for each day of the weeks read that has its piece on the board. Pure."""
    out = {}
    for monday, listed in sorted(listed_by_week.items()):
        for day, entry in board_days(listed, dt.date.fromisoformat(monday)).items():
            out[entry['date']] = (monday, day, entry['piece_id'])
    return out


def post_rows(entries, placed, status_of, sent, accounts=None, pieces=None):
    """{board week: [post, ...]}: this engine's own record of each post it made for an option he approved, filed under
    the week the option is on now (Ruling, Krish, 2026-11-12: the move updates every place that names its day):
    made (a Buffer draft exists), scheduled (with its time), live (Buffer shows it sent, with its native link). The
    evidence is this engine's own: the derived slots indexed in Control Center tie each Buffer post to its option, and
    nothing is attributed by its date or guessed. entries: {concept_id, channel, due_at, buffer_draft_id};
    status_of(post id) -> (status, dueAt) or None; sent: {post id: buffer_reads.sent_posts post}. Pure but for status_of.

    pieces (piece_days): a post of this engine's own for a day's piece that Buffer has scheduled goes back as the
    piece's own entry, {piece_id, day, state: scheduled, channel, due_at, buffer_post_id}, kept on the day's box for its
    channel (Ruling, Krish, 2026-11-12: the board shows exactly where everything is; Fri 13 Nov was scheduled while the
    board said "Ready to post"). A post that went out is board tick's; nothing is reported for a day with no piece."""
    out = {}
    for entry in entries:
        where = placed.get(entry.get('concept_id'))
        if where is None:
            row = piece_row(entry, pieces or {}, status_of, sent)
            if row is not None:
                out.setdefault(row.pop('_week'), []).append(row)
            continue
        post_id = entry['buffer_draft_id']
        went = sent.get(post_id)
        if went is not None:
            url = went.get('external_link')
            if not native_host(entry['channel'], url, (accounts or {}).get(entry['channel'])):
                continue  # live only with the post's own link on its channel's own host
            row = {'state': 'live', 'channel': entry['channel'], 'url': url,
                   'at': instant(went['sent_at']).isoformat().replace('+00:00', 'Z')}
        else:
            read = status_of(post_id)
            if read is None:
                continue
            if read[0] in LIVE_STATUS:
                row = {'state': 'scheduled', 'channel': entry['channel'], 'due_at': read[1] or entry['due_at']}
            elif read[0] == 'draft':
                row = {'state': 'made'}
            else:
                continue
        row.update({'option': where[2], 'buffer_post_id': post_id})
        out.setdefault(where[0], []).append(row)
    return out


def piece_row(entry, pieces, status_of, sent):
    """The piece's own scheduled entry for one of this engine's posts on a day with a piece, or None. Pure but for
    status_of."""
    post_id = entry.get('buffer_draft_id')
    box = next(iter(BOXES.get(entry.get('channel'), ())), None)
    if not post_id or box is None or post_id in sent:
        return None
    read = status_of(post_id)
    if read is None or read[0] not in LIVE_STATUS:
        return None
    due = read[1] or entry.get('due_at')
    if not due:
        return None
    try:
        date = ny_time(due).date().isoformat()
    except (TypeError, ValueError):
        return None
    where = pieces.get(date)
    if where is None:
        return None
    return {'_week': where[0], 'piece_id': where[2], 'day': where[1], 'state': 'scheduled', 'channel': box,
            'due_at': instant(due).isoformat().replace('+00:00', 'Z'), 'buffer_post_id': post_id}


def record_rows(record, placed):
    """{board week: [post, ...]} from a session's own posting receipts (a JSON list, each {option or concept_id, state,
    channel, due_at, url, at}): what a Codex or Claude session made, scheduled or posted by hand for an option he
    approved. A live receipt needs its channel and the post's own https link. Pure; ValueError for anything else."""
    if not isinstance(record, list):
        raise ValueError('the record is a list of posts')
    out = {}
    for post in record:
        if not isinstance(post, dict) or post.get('state') not in ('made', 'scheduled', 'live', 'cancelled'):
            raise ValueError('each post names its state: made, scheduled, live or cancelled')
        cid = post.get('concept_id') or (OFF_OPTION.match(str(post.get('option') or '')) or [None, None, None])[2]
        where = placed.get(cid)
        if where is None:
            raise ValueError('an option he has not approved on the board: ' + str(cid))
        if post['state'] == 'live' and not (isinstance(post.get('channel'), str) and str(post.get('url') or '').startswith('https://')):
            raise ValueError('a live post needs its channel and its own https link')
        row = {k: post[k] for k in ('state', 'channel', 'due_at', 'url', 'at', 'buffer_post_id') if post.get(k) is not None}
        row['option'] = where[2]
        out.setdefault(where[0], []).append(row)
    return out


def report_posts(board, cc, buffer, sent, now=None, deliver=False, record=None, accounts=None):
    """Write back to the board what this engine made, scheduled and posted for each approved off-day option, this
    week and the next two (and, with record, a session's own receipts). Counts only."""
    from . import autorelease
    now = instant(now)
    today = ny_time(now).date()
    mondays = [(monday_of(today) + dt.timedelta(days=7 * k)).isoformat() for k in range(-1, 3)]
    summary = {'weeks': len(mondays), 'posts': 0, 'reported': 0, 'deliver': bool(deliver), 'error': None}
    listed = {}
    for monday in mondays:
        try:
            listed[monday] = board.pieces(monday)
        except BoardError as error:
            summary['error'] = error.code
            return summary
    placed = placed_options(listed)
    if record is not None:
        rows = record_rows(record, placed)
    else:
        holds, entries = {}, []
        for monday in mondays:
            entries.extend(autorelease.week_entries(cc, monday, holds) or [])

        def status_of(post_id):
            try:
                post = buffer.get_post(post_id)
            except Exception:  # noqa: BLE001 - an unreadable post is left out, never guessed
                return None
            return (post.get('status'), post.get('dueAt')) if isinstance(post, dict) else None

        rows = post_rows(entries, placed, status_of, sent, accounts, piece_days(listed))
    summary['posts'] = sum(len(v) for v in rows.values())
    if not deliver:
        return summary
    for monday, posts in sorted(rows.items()):
        try:
            result = board.posts(monday, posts)
        except BoardError as error:
            summary['error'] = error.code
            return summary
        summary['reported'] += int(result.get('items') or 0)
    return summary


def board_from_env():
    """The board client from GROWTH_WRITEBACK_TOKEN (the one secret board tick already uses), or None."""
    token = (os.environ.get(TOKEN_ENV) or '').strip()
    return Board(token) if token else None


def monday_of(day):
    return day - dt.timedelta(days=day.weekday())


def board_days(listed, monday):
    """The board's days as {day key: {'date', 'piece_id', 'boxes', 'slot'}}. Pure; a malformed day is left out."""
    days = {}
    for entry in listed.get('days') if isinstance(listed.get('days'), list) else []:
        if not isinstance(entry, dict) or entry.get('day') not in DAY_KEYS:
            continue
        date = (monday + dt.timedelta(days=DAY_KEYS.index(entry['day']))).isoformat()
        if entry.get('date') not in (None, date):
            continue
        piece = entry.get('piece_id')
        boxes = entry.get('channels')
        if not isinstance(piece, str) or not PIECE_ID.match(piece) or not isinstance(boxes, list):
            continue
        slot = entry.get('slot')
        days[entry['day']] = {'date': date, 'piece_id': piece, 'boxes': [b for b in boxes if isinstance(b, str)],
                              'slot': slot if isinstance(slot, str) and re.match(r'^\d\d:\d\d$', slot) else None}
    return days


def series_slot(day, cfg):
    """The reserved series time on that weekday, or None."""
    reserved = cfg['reserved']
    return reserved['time'] if reserved['days'].get(mix_rules.DAYS[day.weekday()], 0) else None


def rows(posts, weeks, cfg, accounts=None):
    """(rows to post, counts of what was left and why). Pure.

    posts: buffer_reads.sent_posts posts (each carries due_at and external_link).
    weeks: {Monday ISO: board_days(...)}."""
    out, left = [], {}

    def leave(code):
        left[code] = left.get(code, 0) + 1

    for post in posts:
        due = post.get('due_at')
        if due is None:
            leave('no_due_at')
            continue
        local = ny_time(due)
        monday = monday_of(local.date()).isoformat()
        day = DAY_KEYS[local.weekday()]
        entry = (weeks.get(monday) or {}).get(day)
        if entry is None:
            leave('no_board_piece_that_day')
            continue
        slot = entry['slot'] or series_slot(local.date(), cfg)
        if slot is None or local.strftime('%H:%M') != slot:
            leave('not_the_piece_slot')
            continue
        box = next((b for b in BOXES.get(post['channel'], ()) if b in entry['boxes']), None)
        if box is None:
            leave('no_box_for_channel')
            continue
        url = post.get('external_link')
        if not native_host(post['channel'], url, (accounts or {}).get(post['channel'])):
            leave('no_native_url')
            continue
        out.append((monday, {'day': day, 'piece_id': entry['piece_id'], 'channel': box, 'post_url': url,
                             'posted_at': instant(post['sent_at']).isoformat().replace('+00:00', 'Z'),
                             'buffer_post_id': post['post_id']}))
    return out, left


def tick(board, client, now=None, deliver=False, root=None, accounts=None):
    """Read sent posts and the board's days, then post one row per ticked box. Returns counts only."""
    now = instant(now)
    since = now - LOOKBACK
    cfg = mix_rules.load(root) if root else mix_rules.load()
    posts = sent_posts(client, since, now)['posts']
    weeks, summary = {}, {'sent': len(posts), 'rows': 0, 'filed': 0, 'duplicate': 0, 'refused': {}, 'left': {},
                          'deliver': bool(deliver), 'error': None}
    for monday in sorted({monday_of(ny_time(p['due_at']).date()).isoformat() for p in posts if p.get('due_at')}):
        try:
            weeks[monday] = board_days(board.pieces(monday), dt.date.fromisoformat(monday))
        except BoardError as error:
            if error.code == 'board_token_refused':
                summary['error'] = error.code
                return summary
            weeks[monday] = {}
            summary['left'][error.code] = summary['left'].get(error.code, 0) + 1
    out, left = rows(posts, weeks, cfg, accounts)
    for code, n in left.items():
        summary['left'][code] = summary['left'].get(code, 0) + n
    summary['rows'] = len(out)
    if not deliver:
        return summary
    for monday, row in out:
        try:
            result = board.posted(monday, row)
        except BoardError as error:
            if error.code == 'board_token_refused':
                summary['error'] = error.code
                return summary
            summary['refused'][error.code] = summary['refused'].get(error.code, 0) + 1
            continue
        if result.get('ok') is True and result.get('duplicate') is True:
            summary['duplicate'] += 1
        elif result.get('ok') is True:
            summary['filed'] += 1
        else:
            summary['refused']['not_confirmed'] = summary['refused'].get('not_confirmed', 0) + 1
    return summary


def main(argv=None, make_board=None, make_buffer=None, now=None, out=print):
    parser = argparse.ArgumentParser(prog='growth.py run board')
    parser.add_argument('cmd', choices=('board',))
    parser.add_argument('action', choices=('tick', 'offer', 'posts'))
    parser.add_argument('--deliver', action='store_true')
    parser.add_argument('--file', help='offer: the growth-offdays/1 file growth.py mix offdays wrote')
    parser.add_argument('--record', help="posts: a session's own posting receipts (JSON list), instead of the index")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    token = (os.environ.get(TOKEN_ENV) or '').strip()
    if make_board is None and not token:
        out(NOT_CONFIGURED + ': set the ' + TOKEN_ENV + ' secret to tick the publish board')
        return 0
    if args.action == 'offer':
        # Growth's options reach the live board through the one place their day lives, never a second file it merges.
        if not args.file:
            out('board offer: give --file, the growth-offdays/1 file growth.py mix offdays wrote')
            return 2
        board = make_board() if make_board else Board(token)
        try:
            summary = offer(board, json.loads(open(args.file, encoding='utf-8').read()), deliver=args.deliver)
        except (ValueError, OSError) as error:
            out('board offer: ' + str(error))
            return 2
        except BoardError as error:
            out('board offer: ' + error.code)
            return 1
        out('board offer: ' + json.dumps(summary, sort_keys=True))
        return 0
    if args.action == 'posts':
        # Every off-day post this engine made, scheduled or posted goes back to the board, from its own record
        # (Ruling, Krish, 2026-11-12): the index of its derived slots, or a session's receipts with --record.
        board = make_board() if make_board else Board(token)
        if args.record:
            try:
                summary = report_posts(board, None, None, {}, now=now, deliver=args.deliver,
                                       record=json.loads(open(args.record, encoding='utf-8').read()))
            except (ValueError, OSError) as error:
                out('board posts: ' + str(error))
                return 2
            out('board posts: ' + json.dumps(summary, sort_keys=True))
            return 1 if summary['error'] == 'board_token_refused' else 0
        from . import autorelease
        try:
            cc = autorelease._cc_client()
        except Exception:  # noqa: BLE001 - no engine token: say so, read nothing
            out('board posts: Control Center is not configured; nothing was read')
            return 0
        client, why = (make_buffer() if make_buffer else buffer_client(links=True))
        if client is None:
            out('board posts: ' + why)
            return 0
        sent = {p['post_id']: p for p in sent_posts(client, instant(now) - dt.timedelta(days=10), now)['posts']}
        summary = report_posts(board, cc, autorelease._buffer_client(), sent, now=now, deliver=args.deliver,
                               accounts=load_accounts())
        out('board posts: ' + json.dumps(summary, sort_keys=True))
        return 1 if summary['error'] == 'board_token_refused' else 0
    client, why = (make_buffer() if make_buffer else buffer_client(links=True))
    if client is None:
        out('board tick: ' + why)
        return 0
    board = make_board() if make_board else Board(token)
    summary = tick(board, client, now=now, deliver=args.deliver, accounts=load_accounts())
    out('board tick: ' + json.dumps(summary, sort_keys=True))
    return 1 if summary['error'] else 0
