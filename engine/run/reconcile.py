"""Reconciliation: every post on this engine's pinned channels carries a tracked route, whoever made it.

The subscribe gate holds a Buffer call a session makes (engine/subscribe_gate.py) and the go-live path holds a
line with no route (engine/route.py), but a post made natively in an app, or by a session without the hook,
passes neither. From 2 to 11 November 58 posts went out with no subscribe ask, and nothing said so for days.
The measure job now reads every sent post on the eight pinned channels, Buffer-made and native, and counts
those with no tracked route: an own link with all four UTM tags GA4 credits it by (engine/run/ga4.py
own_links) to the subscribe page, in its words, link card or first comment, or, on Instagram and TikTok, words
that point to the profile link. Any such post sent since the go-live check landed raises the alarm: a hold in
the measure report, which Control Center shows on this engine every day. It does not fail the run, because a
post already sent stays sent and a failed run three times a day would only repeat the same email.

What is not checked here yet: whether each post matches a go-live he approved. That needs the go-live claim
ledger (growth-golive-claim/1) read in the measure run, and is said as "approval not reconciled" rather than
guessed. Counts and codes only: the log and the report carry no words, ids or URLs.
"""
import datetime as dt
import re
from urllib.parse import urlsplit

from .. import intensity
from ..core import instant
from .ga4 import OWN_HOST, own_links

# The go-live route check landed on 13 November 2026; earlier posts are history, counted but never alarmed.
CHECKED_FROM = '2026-11-13T00:00:00+00:00'
WINDOW = dt.timedelta(days=7)
PROFILE = re.compile(r'\b(?:link in (?:my |the )?(?:bio|profile)|profile link|subscribe)\b', re.I)


def routed(post, root=intensity.ROOT):
    """True when the post's words (and link card) carry a tracked own link, or point to the profile link on a
    channel whose posts carry no clickable link."""
    page = urlsplit(intensity.bounds(root)['conversion']['subscribe_url']).path.rstrip('/')
    for url in intensity.URL_IN_TEXT.findall(post.get('words') or ''):
        url = url.rstrip('.,;:!?)')
        if urlsplit(url).path.rstrip('/') == page and any(link['tracked'] for link in own_links(url)):
            return True
    profile = intensity.bounds(root)['conversion']['profile_link_channels']
    return post.get('channel') in profile and bool(PROFILE.search(post.get('words') or ''))


def check(posts_read, now, root=intensity.ROOT):
    """{'checked', 'routeless': {'buffer', 'native'}, 'alarm', 'line'} over the last seven days' sent posts."""
    now = instant(now)
    since, gate = now - WINDOW, instant(CHECKED_FROM)
    made = [('buffer', p) for p in posts_read.get('posts') or []] + [('native', p) for p in posts_read.get('native') or []]
    routeless = {'buffer': 0, 'native': 0}
    alarm = {'buffer': 0, 'native': 0}
    checked = 0
    for how, post in made:
        sent = post.get('sent_at')
        if sent is None or not since <= instant(sent) <= now:
            continue
        checked += 1
        if routed(post, root):
            continue
        routeless[how] += 1
        if instant(sent) >= gate:
            alarm[how] += 1
    line = ('Reconciliation over the last 7 days: ' + str(checked) + ' sent posts on the pinned channels; with no '
            'tracked route ' + str(routeless['buffer']) + ' made in Buffer and ' + str(routeless['native'])
            + ' made natively; approval not reconciled yet (go-live claim ledger)')
    return {'checked': checked, 'routeless': routeless, 'alarm': sum(alarm.values()), 'alarm_by': alarm, 'line': line,
            'host': OWN_HOST}
