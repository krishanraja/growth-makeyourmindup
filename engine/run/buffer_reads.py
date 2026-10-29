"""Buffer reads for the measure job, behind one small interface.

The measure job needs only two calls from a Buffer client, so any client with
these methods works (engine/run/buffer_api.py in production, a fake in tests):

    client.list_posts(status='sent', since=ISO8601) -> posts
        a list of Post objects, or {'posts': [...]}, or a GraphQL connection
        {'edges': [{'node': Post}]}; each Post as Buffer's schema names it:
        id, status, via, sentAt, text, channelId, channelService,
        channel {id, name, service, isDisconnected, isLocked}, metadata and,
        when the list carries them, metrics [{type, value, unit}].
    client.get_post(post_id) -> Post
        read only when a listed post carries no `metrics` key.

Channel pinning reuses engine/run/release.py: a post counts for this engine
only when its channel is the one release.BUFFER_NAME names for that service
(release.resolve_channel), because the Buffer organisation is shared with
other ventures. Imported posts (via "network") are not this engine's
publications (F17) and are counted, never judged.

Read-only: nothing here creates, edits or deletes anything in Buffer.
"""
import importlib
import math
import os

from ..core import instant
from .release import BUFFER_NAME, CHANNELS, resolve_channel

KEY_ENV = 'BUFFER_API_KEY'
NOT_CONFIGURED = 'Buffer not configured'
NOT_INSTALLED = 'buffer_api not installed'
MAX_POSTS = 500


BUFFER_MODULE = 'engine.run.buffer_api'


def buffer_module():
    """engine/run/buffer_api.py when it is installed, else None."""
    try:
        return importlib.import_module(BUFFER_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != BUFFER_MODULE:
            raise
        return None


def buffer_client(environ=None, links=False):
    """(client, None) or (None, why). Degrades instead of failing when Buffer is absent.
    links=True lists sent posts with their native URL (the board tick)."""
    environ = os.environ if environ is None else environ
    key = (environ.get(KEY_ENV) or '').strip()
    if not key:
        return None, NOT_CONFIGURED
    buffer_api = buffer_module()
    if buffer_api is None:
        return None, NOT_INSTALLED
    if callable(getattr(buffer_api, 'Buffer', None)):
        return Reader(buffer_api.Buffer(key), links), None
    if callable(getattr(buffer_api, 'Client', None)):  # a stand-in with the reader's shape
        return buffer_api.Client(key), None
    return None, 'buffer_api has no client constructor this engine knows'


class Reader:
    """The measure job's view of buffer_api.Buffer: posts across the key's organisations.

    The key belongs to one person and may see several organisations; posts are
    read from each, and channel pinning (release.BUFFER_NAME) happens later.
    """

    def __init__(self, buffer, links=False):
        self.buffer, self.links = buffer, links
        self._orgs = None

    def account_check(self):
        result = self.buffer.account_check()
        self._orgs = list(result.get('organization_ids') or [])
        return result

    def list_posts(self, status=None, since=None):
        if self._orgs is None:
            self.account_check()
        posts = []
        for org in self._orgs:
            posts += (self.buffer.list_posts(org, status=status, since=since, links=True) if self.links
                      else self.buffer.list_posts(org, status=status, since=since))
        return posts

    def get_post(self, post_id):
        return self.buffer.get_post(post_id)


def _posts(listed):
    if isinstance(listed, dict):
        if isinstance(listed.get('posts'), list):
            listed = listed['posts']
        elif isinstance(listed.get('edges'), list):
            listed = [e.get('node') for e in listed['edges'] if isinstance(e, dict)]
        else:
            raise ValueError('Buffer list_posts returned no posts list')
    if not isinstance(listed, list):
        raise ValueError('Buffer list_posts returned no posts list')
    return [p for p in listed if isinstance(p, dict)]


def _channel_of(post):
    channel = post.get('channel') if isinstance(post.get('channel'), dict) else {}
    cid = channel.get('id') or post.get('channelId')
    return {'id': cid, 'name': channel.get('name'), 'service': channel.get('service') or post.get('channelService'),
            'isDisconnected': channel.get('isDisconnected', False), 'isLocked': channel.get('isLocked', False)}


def metric_values(metrics):
    """{type: value} for whole-count metrics; percentages and unreadable values are left out."""
    out = {}
    for item in metrics if isinstance(metrics, list) else []:
        if not isinstance(item, dict) or item.get('unit', 'count') != 'count' or not isinstance(item.get('type'), str):
            continue
        value = item.get('value')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            continue
        out[item['type']] = int(value) if float(value).is_integer() else value
    return out


def _words(post):
    """The post's text plus any link attachment, so a tracked link in either is joined."""
    words = post.get('text') if isinstance(post.get('text'), str) else ''
    meta = post.get('metadata') if isinstance(post.get('metadata'), dict) else {}
    link = meta.get('linkAttachment') if isinstance(meta.get('linkAttachment'), dict) else {}
    if isinstance(link.get('url'), str):
        words += ' ' + link['url']
    return words


def sent_posts(client, since, now=None):
    """This engine's sent posts on its eight pinned channels, with per-post metrics where present."""
    since, now = instant(since), instant(now)
    listed = _posts(client.list_posts(status='sent', since=since.isoformat()))[:MAX_POSTS]
    seen = {}
    for post in listed:
        channel = _channel_of(post)
        if isinstance(channel['id'], str):
            seen.setdefault(channel['id'], channel)
    pinned, missing, held = {}, [], []
    for cid in BUFFER_NAME:
        try:
            pinned[resolve_channel({'channel': cid}, list(seen.values()))['id']] = cid
        except ValueError as exc:
            (missing if str(exc).startswith('no Buffer channel') else held).append(
                {'channel': cid, 'reason': str(exc)})
    posts, imported, reads = [], 0, 0
    for post in listed:
        cid = pinned.get(_channel_of(post)['id'])
        if cid is None or post.get('status') != 'sent':
            continue
        if not isinstance(post.get('sentAt'), str):
            continue  # instant(None) would read as now
        try:
            sent_at = instant(post['sentAt'])
        except (TypeError, ValueError, AttributeError):
            continue
        if not since <= sent_at <= now:
            continue
        if post.get('via') == 'network':
            imported += 1
            continue
        pid = post.get('id')
        if not isinstance(pid, str) or not pid or len(pid) > 64:
            continue
        if 'metrics' in post:
            metrics = post['metrics']
        else:
            detail = client.get_post(pid)
            reads += 1
            metrics = detail.get('metrics') if isinstance(detail, dict) else None
        posts.append({'post_id': pid, 'channel': cid, 'service': CHANNELS[cid][0], 'sent_at': sent_at,
                      'due_at': post.get('dueAt'), 'external_link': post.get('externalLink'), 'words': _words(post), 'metrics': metric_values(metrics) if metrics is not None else None})
    return {'posts': posts, 'missing': missing, 'held': held, 'imported': imported, 'get_post_reads': reads,
            'listed': len(listed)}


def account_check(client):
    """Ask Buffer who the key belongs to. True, or raise; never returns the account."""
    check = getattr(client, 'account_check', None)
    if not callable(check):
        module_check = getattr(buffer_module(), 'account_check', None)
        if not callable(module_check):
            raise ValueError('buffer_api has no account_check')
        result = module_check(client)
    else:
        result = check()
    if result is False or result is None or (isinstance(result, dict) and result.get('ok') is False):
        raise PermissionError('buffer_key_refused')
    return True


def refused(exc):
    """True when an error says the key itself was refused (401, 403 or a named refusal)."""
    code = getattr(exc, 'code', None)
    status = getattr(exc, 'status', None) or getattr(exc, 'http_status', None)
    if isinstance(exc, PermissionError) or status in (401, 403):
        return True
    return code in (401, 403, 'unauthorized', 'forbidden', 'buffer_key_refused', 'key_refused', 'UNAUTHENTICATED')
