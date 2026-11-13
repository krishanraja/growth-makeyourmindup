"""Where each engagement tap opens (W2.8; Krish, 2026-10-28).

"make sure everything is one click copiable and the click through goes
precisely where i need to engage." The day's queue covers X, TikTok and
Instagram. A tap on one of them must open the exact post (its reply box is on
that page) or the exact profile, never a feed, a search, a home page or a
short link that hides where it goes. A tap on any other platform keeps
Control Center's general public-page check only.

LinkedIn left the queue on 13 November 2026 (Ruling, Krish, 2026-11-13):
growth-mindmake owns his personal LinkedIn posts and the replies to everyone
who engages with them, so a LinkedIn tap is refused here (engine/owners.py),
by its label or by the page it opens (linkedin.com or lnkd.in), whichever
platform it claims.
"""
import re
from urllib.parse import urlsplit

from . import owners

QUEUE_PLATFORMS = ('x', 'tiktok', 'instagram')
QUEUE_MINUTES = 10  # Krish, 2026-10-28: "10 min daily queue is fine"

_HANDLE = r'[A-Za-z0-9_]{1,15}'
_TT_USER = r'@[A-Za-z0-9_.]{2,24}'
_IG_USER = r'(?!p/|reel/|reels/|explore/|stories/|accounts/)[A-Za-z0-9_.]{1,30}'
_RESERVED_X = {'home', 'explore', 'search', 'notifications', 'messages', 'i', 'settings', 'compose', 'hashtag'}

# platform -> [(kind, host pattern, path pattern)]; paths may end with one slash.
TARGETS = {
    'x': [('post', r'(?:x|twitter)\.com', r'/' + _HANDLE + r'/status/\d{1,25}'),
          ('profile', r'(?:x|twitter)\.com', r'/' + _HANDLE)],
    'tiktok': [('post', r'(?:www\.)?tiktok\.com', r'/' + _TT_USER + r'/(?:video|photo)/\d{1,25}'),
               ('profile', r'(?:www\.)?tiktok\.com', r'/' + _TT_USER)],
    'instagram': [('post', r'(?:www\.)?instagram\.com', r'/(?:p|reel)/[A-Za-z0-9_-]{5,40}'),
                  ('profile', r'(?:www\.)?instagram\.com', r'/' + _IG_USER)],
}


def target_kind(platform, url):
    """'post' or 'profile' when url opens exactly that on platform, else None.

    Only the queue's three platforms have a rule; for any other this returns
    'page' (Control Center's general check still applies)."""
    if platform not in TARGETS:
        return 'page'
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != 'https' or parts.username or parts.password or port or parts.fragment or '\\' in url:
        return None
    host, path = parts.hostname or '', parts.path or ''
    for kind, host_rule, path_rule in TARGETS[platform]:
        if re.fullmatch(host_rule, host) and re.fullmatch(path_rule + r'/?', path):
            if kind == 'profile' and platform == 'x' and path.strip('/').lower() in _RESERVED_X:
                return None
            return kind
    return None


def tap_errors(platform, url, text):
    """Why a queue tap cannot go to Krish: a channel another engine owns, or a page that is not exact.

    The owner is read from the label and from the page the tap opens, as a browser reads its host
    (owners.page_refusal, the same check the Engagement engine's queue makes), so a LinkedIn page labelled
    threads, youtube or anything else is still LinkedIn's (Ruling, Krish, 2026-11-13)."""
    why = owners.page_refusal(platform, url)
    if why:
        return [why]
    errors = []
    if target_kind(platform, url) is None:
        errors.append('a ' + platform + ' tap must open the exact post or profile, not a feed, search or short link')
    return errors
