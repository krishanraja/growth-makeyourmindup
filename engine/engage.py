"""Where each engagement tap opens (W2.8; Krish, 2026-10-28).

"make sure everything is one click copiable and the click through goes
precisely where i need to engage." The day's queue covers X, TikTok,
Instagram and LinkedIn. A tap on one of them must open the exact post (its
reply box is on that page) or the exact profile, never a feed, a search, a
home page or a short link that hides where it goes. A tap on any other
platform keeps Control Center's general public-page check only.
"""
import re
from urllib.parse import urlsplit

QUEUE_PLATFORMS = ('x', 'tiktok', 'instagram', 'linkedin')
QUEUE_MINUTES = 10  # Krish, 2026-10-28: "10 min daily queue is fine"

_HANDLE = r'[A-Za-z0-9_]{1,15}'
_TT_USER = r'@[A-Za-z0-9_.]{2,24}'
_IG_USER = r'(?!p/|reel/|reels/|explore/|stories/|accounts/)[A-Za-z0-9_.]{1,30}'
_LI_URN = r'urn:li:(?:activity|share|ugcPost):\d{1,25}'
_RESERVED_X = {'home', 'explore', 'search', 'notifications', 'messages', 'i', 'settings', 'compose', 'hashtag'}

# platform -> [(kind, host pattern, path pattern)]; paths may end with one slash.
TARGETS = {
    'x': [('post', r'(?:x|twitter)\.com', r'/' + _HANDLE + r'/status/\d{1,25}'),
          ('profile', r'(?:x|twitter)\.com', r'/' + _HANDLE)],
    'tiktok': [('post', r'(?:www\.)?tiktok\.com', r'/' + _TT_USER + r'/(?:video|photo)/\d{1,25}'),
               ('profile', r'(?:www\.)?tiktok\.com', r'/' + _TT_USER)],
    'instagram': [('post', r'(?:www\.)?instagram\.com', r'/(?:p|reel)/[A-Za-z0-9_-]{5,40}'),
                  ('profile', r'(?:www\.)?instagram\.com', r'/' + _IG_USER)],
    'linkedin': [('post', r'(?:www\.)?linkedin\.com', r'/feed/update/' + _LI_URN),
                 ('post', r'(?:www\.)?linkedin\.com', r'/posts/[A-Za-z0-9_%-]{3,200}-(?:activity|share|ugcPost)-\d{1,25}-[A-Za-z0-9_-]{2,8}'),
                 ('profile', r'(?:www\.)?linkedin\.com', r'/in/[A-Za-z0-9_%-]{3,100}')],
}


def target_kind(platform, url):
    """'post' or 'profile' when url opens exactly that on platform, else None.

    Only the queue's four platforms have a rule; for any other this returns
    'page' (Control Center's general check still applies)."""
    if platform not in TARGETS:
        return 'page'
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != 'https' or parts.username or parts.password or parts.port or parts.fragment:
        return None
    host, path = parts.hostname or '', parts.path or ''
    for kind, host_rule, path_rule in TARGETS[platform]:
        if re.fullmatch(host_rule, host) and re.fullmatch(path_rule + r'/?', path):
            if kind == 'profile' and platform == 'x' and path.strip('/').lower() in _RESERVED_X:
                return None
            return kind
    return None


def tap_errors(platform, url, text):
    """Why a queue tap is not exact: its page, and for LinkedIn a link in the words (rule 4)."""
    errors = []
    if target_kind(platform, url) is None:
        errors.append('a ' + platform + ' tap must open the exact post or profile, not a feed, search or short link')
    if platform == 'linkedin' and isinstance(text, str) and re.search(r'https?://|www\.', text):
        errors.append('a LinkedIn reply carries no link')
    return errors
