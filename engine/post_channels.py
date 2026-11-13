"""Which Buffer channel each Buffer post is on, by post id: so an edit, which names only its post, is gated by
its channel (engine/subscribe_gate.py). Standard library only. Offline: it reads and writes local files only.

Buffer's edit_post carries a postId and no channelId, so the gate cannot see from the call alone whether an
edit lands on one of this engine's channels, another venture's, or Krish's personal LinkedIn, which is
growth-mindmake's since 13 November 2026 (Ruling, Krish, 2026-11-13). The channel is known once the post has
been read, so the map comes from two places:

- the Claude Code hook .claude/hooks/buffer-post-channels.py, after every Buffer get_post, list_posts and
  create_post, records each post id with its channel id from the call's answer;
- the one ledger of this engine's own that records a Buffer post id with its channel id as fields: each release
  run's ledger (.scratch/runs/<run>/ledger.json, `post_id` with `channel_id`, as engine/run/release.py writes it).

The L0 handoff's output is not a seed: it carries a draft's channel id only inside each go-live's exact payload
text, and the gate fails closed without it, refusing an edit of a post it cannot map until the post is read.

The map is working state, kept in the ignored .scratch/buffer/post-channels.json and never committed. It holds
ids only: no words, no addresses, no URLs.
"""
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAP = Path('.scratch') / 'buffer' / 'post-channels.json'
SCHEMA = 'growth-buffer-post-channels/1'
BUFFER_ID = re.compile(r'^[a-f\d]{24}$')
# The newest this many posts are kept; an older post's edit is read again first.
MAX_POSTS = 20000
# The ledgers that record a Buffer post id with its channel id as fields: (folder, glob, post id key, channel id key).
SEEDS = ((Path('.scratch') / 'runs', '*/ledger.json', 'post_id', 'channel_id'),)
TOOLS = ('get_post', 'list_posts', 'create_post')


def _id(value):
    return value if isinstance(value, str) and BUFFER_ID.match(value) else None


def _parsed(value, key=None):
    """value with any JSON text inside it parsed, as an MCP answer may carry its post as text (a content block's
    text, or the whole answer)."""
    if isinstance(value, str):
        text = value.strip()
        if key in (None, 'text', 'content', 'result') and text[:1] in '{[':
            try:
                return _parsed(json.loads(text))
            except ValueError:
                return value
        return value
    if isinstance(value, list):
        return [_parsed(v) for v in value]
    if isinstance(value, dict):
        return {k: _parsed(v, k) for k, v in value.items()}
    return value


def _channel_id(post):
    channel = post.get('channel') if isinstance(post.get('channel'), dict) else {}
    return _id(post.get('channelId')) or _id(channel.get('id'))


def pairs(value):
    """[(post id, channel id)] for every post in value that names both: a Buffer post as get_post, list_posts and
    create_post answer it ({id, channelId} or {id, channel: {id}}), however deeply the answer nests it."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            pid, cid = _id(node.get('id')), _channel_id(node)
            if pid and cid and pid != cid:
                out.append((pid, cid))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(_parsed(value))
    return out


def from_call(tool_name, tool_input, tool_response):
    """[(post id, channel id)] one Buffer call's answer shows: get_post, list_posts or create_post.

    A get_post answer that gives its channel but not its own id is the post the call asked for; a create_post
    answer that gives the new post's id but not its channel is on the channel the call named."""
    name = str(tool_name or '')
    if not name.endswith(TOOLS):
        return []
    found = pairs(tool_response)
    asked = tool_input if isinstance(tool_input, dict) else {}
    answer = _parsed(tool_response)
    top = answer if isinstance(answer, dict) else {}
    if not found and name.endswith('get_post') and _id(asked.get('postId')):
        inner = next((v for v in top.values() if isinstance(v, dict) and _channel_id(v)), top)
        if _channel_id(inner):
            found.append((asked['postId'], _channel_id(inner)))
    if not found and name.endswith('create_post') and _id(asked.get('channelId')):
        inner = next((v for v in top.values() if isinstance(v, dict) and _id(v.get('id'))), top)
        if _id(inner.get('id')) and _id(inner.get('id')) != asked['channelId']:
            found.append((inner['id'], asked['channelId']))
    return found


def _read(path):
    try:
        with open(path, encoding='utf-8') as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return {}
    posts = value.get('posts') if isinstance(value, dict) else None
    return {k: v for k, v in (posts or {}).items() if _id(k) and _id(v)} if isinstance(posts, dict) else {}


def recorded(root=ROOT):
    """{post id: channel id} the hook recorded."""
    return _read(Path(root) / MAP)


def record(root, found):
    """Add found ([(post id, channel id)]) to the map and return how many were new or changed."""
    found = [(p, c) for p, c in found if _id(p) and _id(c)]
    if not found:
        return 0
    path = Path(root) / MAP
    posts = _read(path)
    changed = 0
    for pid, cid in found:
        if posts.get(pid) != cid:
            changed += 1
        posts.pop(pid, None)
        posts[pid] = cid  # newest last, so the oldest go first
    if not changed:
        return 0
    posts = dict(list(posts.items())[-MAX_POSTS:])
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.post-channels-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump({'schema': SCHEMA, 'posts': posts}, handle, separators=(',', ':'))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return changed


def seeded(root=ROOT):
    """{post id: channel id} from this engine's release ledgers (SEEDS). A file that cannot be read adds nothing."""
    out = {}

    def walk(node, post_key, channel_key):
        if isinstance(node, dict):
            pid, cid = _id(node.get(post_key)), _id(node.get(channel_key))
            if pid and cid:
                out[pid] = cid
            for child in node.values():
                walk(child, post_key, channel_key)
        elif isinstance(node, list):
            for child in node:
                walk(child, post_key, channel_key)

    for folder, pattern, post_key, channel_key in SEEDS:
        base = Path(root) / folder
        for path in sorted(base.glob(pattern)) if base.is_dir() else []:
            try:
                with open(path, encoding='utf-8') as handle:
                    walk(json.load(handle), post_key, channel_key)
            except (OSError, ValueError):
                continue
    return out


def known(root=ROOT):
    """{post id: channel id}: the ledgers' seeds, with what the hook recorded on top (the newest reading)."""
    return {**seeded(root), **recorded(root)}
