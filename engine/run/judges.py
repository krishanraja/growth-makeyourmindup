"""content-engine's 10/10 judges on every Growth carousel and Short before it is made.

Ruling (Krish, 2026-11-12): "Judge them; count passes. Every Growth carousel goes through the same 10/10 judges, and
each one that passes and goes live counts." Content-engine owns the judges and production standards
(docs/ENGINE-BOUNDARY.md); this engine asks them, on its own board key (GROWTH_WRITEBACK_TOKEN), through the one board
route content-engine keeps for it:

    POST https://content.krishraja.com/api/board/<Monday>/judge
    {"op": "judge", "item", "format", "channel", "concept_id", "claim", "words", "assets": [{"name", "sha256"}]}
        -> {"verdict": "pass" | "fail", "score", "band", "reasons": [{"judge", "score", "fix"}], "artifact_sha256"}
    {"op": "bind", "artifact_sha256", "buffer_post_id", "payload_sha256", "item"}   once the draft is saved
    {"op": "live", "posts": [{"buffer_post_id", "url", "at"}]}                       board tick, from Buffer's sent posts

The maker asks before a draft is saved (make) or handed off (adopt). A pass is made and handed off, and its verdict is
bound to the Buffer post, so the post counts once it goes live. A fail is never made: the slot holds loudly as
judges_failed, and the judges' reasons are kept in the ignored .scratch/judges/ for the session that rewrites it (this
repository is public, so the log carries codes only). Content-engine keeps every verdict, reasons included, on the item.
The North Star's number then counts each judged derived post that passed and went live (content-engine's reader in
Control Center). No judge is ever skipped for a judged format: with no board key the slot holds as judges_unavailable.
"""
import hashlib
import json
from pathlib import Path

from .board_tick import BoardError

# The derived posts the North Star names ("essays, Shorts, carousels"): Growth makes the carousels and the Shorts.
JUDGED_FORMATS = ('carousel', 'short-video')
SCRATCH = Path('.scratch') / 'judges'


class JudgesHeld(Exception):
    """The judges said no, or could not be asked: a code, and the reasons when they gave them."""

    def __init__(self, code, reasons=None):
        self.code, self.reasons = code, list(reasons or [])
        super().__init__(code)


def judged(slot):
    return slot.get('format') in JUDGED_FORMATS


def artifact_sha256(slot, words, assets):
    """What the verdict binds: the format, the channel, the exact words and each picture's sha256, in order."""
    canon = json.dumps({'format': slot.get('format'), 'channel': slot.get('channel'), 'words': words,
                        'assets': [a['sha256'] for a in assets]}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


def judge(board, monday, slot, concept, words, assets, root=None):
    """The judges' verdict on one derived post, or JudgesHeld. Only a judged format is asked."""
    if board is None or not hasattr(board, 'judge'):
        raise JudgesHeld('judges_unavailable')
    body = {'op': 'judge', 'item': slot['slot_id'], 'format': slot['format'], 'channel': slot['channel'],
            'concept_id': (concept or {}).get('concept_id'), 'claim': (concept or {}).get('claim') or '', 'words': words,
            'assets': [{'name': a['name'], 'sha256': a['sha256']} for a in assets]}
    try:
        answer = board.judge(monday, body)
    except BoardError as error:
        raise JudgesHeld('judges_unavailable' if error.code != 'judge_cap_reached' else 'judges_cap_reached') from None
    verdict = answer.get('verdict') if isinstance(answer, dict) else None
    if verdict not in ('pass', 'fail') or answer.get('artifact_sha256') != artifact_sha256(slot, words, assets):
        raise JudgesHeld('judges_bad_answer')
    if verdict == 'fail':
        keep(root, slot['slot_id'], answer)
        raise JudgesHeld('judges_failed', answer.get('reasons'))
    return answer


def keep(root, slot_id, answer):
    """The judges' reasons, kept privately for the session that rewrites the post (never committed, never logged)."""
    folder = Path(root or '.') / SCRATCH
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (str(slot_id) + '.json')).write_text(json.dumps(answer, indent=1, sort_keys=True), encoding='utf-8')
    except OSError:
        pass


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
