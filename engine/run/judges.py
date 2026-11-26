"""content-engine's 10/10 judges: Growth binds their pass to the post it saves and reports the post live.

Ruling (Krish, 2026-11-12): "Judge them; count passes. Every Growth carousel goes through the same 10/10 judges, and
each one that passes and goes live counts." Since 26 Nov 2026 content-engine makes every asset and its make flow asks
the judges itself (Ruling, Krish: "I believe that growth should move all asset production to Content Engine"), so
Growth never asks a judge. It keeps the two board write-backs that need a Buffer post, on its own board key
(GROWTH_WRITEBACK_TOKEN), through the one board route content-engine keeps for it:

    POST https://content.krishraja.com/api/board/<Monday>/judge
    {"op": "bind", "artifact_sha256", "buffer_post_id", "payload_sha256", "item"}   once the maker saves the draft
    {"op": "live", "posts": [{"buffer_post_id", "url", "at"}]}                       board tick, from Buffer's sent posts

The artifact the pass binds is the format, the channel, the exact words and each picture's sha256, in order
(artifact_sha256), so the maker names it from the draft it saved. The North Star's number then counts each judged
derived post that passed and went live (content-engine's reader in Control Center). Content-engine keeps every verdict,
reasons included, on the item.
"""
import hashlib
import json

from .board_tick import BoardError

# The derived posts the North Star names ("essays, Shorts, carousels"): the carousels and the Shorts are judged.
JUDGED_FORMATS = ('carousel', 'short-video')


def judged(slot):
    return slot.get('format') in JUDGED_FORMATS


def artifact_sha256(slot, words, assets):
    """What the verdict binds: the format, the channel, the exact words and each picture's sha256, in order."""
    canon = json.dumps({'format': slot.get('format'), 'channel': slot.get('channel'), 'words': words,
                        'assets': [a['sha256'] for a in assets]}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


def bind(board, monday, verdict, post_id, payload, slot_id):
    """Ties a passing verdict to the saved Buffer post, so the post counts when it goes live. True when it landed."""
    try:
        board.judge(monday, {'op': 'bind', 'artifact_sha256': verdict['artifact_sha256'], 'buffer_post_id': post_id,
                             'payload_sha256': payload, 'item': slot_id})
        return True
    except (BoardError, AttributeError):
        return False


def report_live(board, monday, posts):
    """Each post Buffer shows sent, so content-engine marks the judged ones live. Returns how many it marked."""
    if board is None or not hasattr(board, 'judge') or not posts:
        return 0
    rows = [{'buffer_post_id': p['buffer_post_id'], 'url': p['url'], 'at': p['at']} for p in posts
            if p.get('buffer_post_id') and p.get('url') and p.get('at')]
    if not rows:
        return 0
    answer = board.judge(monday, {'op': 'live', 'posts': rows[:200]})
    return int(answer.get('marked') or 0) if isinstance(answer, dict) else 0
