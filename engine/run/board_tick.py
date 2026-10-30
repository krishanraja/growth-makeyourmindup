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

    def posted(self, monday, row):
        return self._request('POST', '/api/board/' + monday + '/posted', row)

    def mix(self, monday):
        """His one press on the week's mix (picks/mix), or None until he presses. Raises BoardError."""
        return board_mix(self.pieces(monday))


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
    parser.add_argument('action', choices=('tick',))
    parser.add_argument('--deliver', action='store_true')
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    token = (os.environ.get(TOKEN_ENV) or '').strip()
    if make_board is None and not token:
        out(NOT_CONFIGURED + ': set the ' + TOKEN_ENV + ' secret to tick the publish board')
        return 0
    client, why = (make_buffer() if make_buffer else buffer_client(links=True))
    if client is None:
        out('board tick: ' + why)
        return 0
    board = make_board() if make_board else Board(token)
    summary = tick(board, client, now=now, deliver=args.deliver, accounts=load_accounts())
    out('board tick: ' + json.dumps(summary, sort_keys=True))
    return 1 if summary['error'] else 0
