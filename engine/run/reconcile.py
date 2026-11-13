"""Reconciliation: every post on this engine's pinned channels carries a tracked route, whoever made it.

The subscribe gate holds a Buffer call a session makes (engine/subscribe_gate.py) and the go-live path holds a
line with no route (engine/route.py), but a post made natively in an app, or by a session without the hook,
passes neither. From 2 to 11 November 58 posts went out with no subscribe ask, and nothing said so for days.
The measure job now reads every sent post on the eight pinned channels, Buffer-made and native, and counts
those with no subscribe route: a link to the subscribe page on this engine's own host, in its words, link card,
story link sticker or first comment, or, on Instagram and TikTok, words that point to the profile link. A route
is tracked when its link carries all four UTM tags GA4 credits a post by (engine/run/ga4.py own_links). A link
with only utm_source and utm_content (the test the gate made before 13 November) is untracked by GA4: on a post
sent before UNTRACKED_FROM it still counts as a route, counted apart and never alarmed; on a post sent from then
on GA4 can never credit it, so it raises the alarm as a missing route does.

A thread's later items are not read yet. The Buffer listing selects an X or Threads thread's count, never its
items, so a route in item two or later cannot be seen here. A thread whose first item carries no route is
therefore counted as not verifiable and never alarmed, whether it is routed further down or not at all: until
the items are read, a routeless thread raises no alarm.

Any other post with no route sent since the go-live check landed raises the alarm: a hold in the measure report,
which Control Center shows on this engine every day. It does not fail the run, because a post already sent stays
sent and a failed run three times a day would only repeat the same email.

What is not checked here yet: whether each post matches a go-live he approved. That needs the go-live claim
ledger (growth-golive-claim/1) read in the measure run, and is said as "approval not reconciled" rather than
guessed. Counts and codes only: the log and the report carry no words, ids or URLs.
"""
import datetime as dt
import re
from urllib.parse import parse_qsl, urlsplit

from .. import intensity
from ..core import instant
from .ga4 import OWN_HOST, own_links

# The go-live route check landed on 13 November 2026; earlier posts are history, counted but never alarmed.
CHECKED_FROM = '2026-11-13T00:00:00+00:00'
# A two-tag subscribe link (utm_source and utm_content, the gate's test before the four-tag check of 13 November) is a
# route only on a post sent before this; from then on GA4 can never credit it, so it is alarmed as a missing route.
UNTRACKED_FROM = '2026-11-14T00:00:00+00:00'
WINDOW = dt.timedelta(days=7)
PROFILE = re.compile(r'\b(?:link in (?:my |the )?(?:bio|profile)|profile link|subscribe)\b', re.I)


def route_of(post, root=intensity.ROOT):
    """The post's subscribe route: 'tracked' (a link to the subscribe page with all four UTM tags GA4 credits it
    by), 'untracked' (only utm_source and utm_content: a route, which GA4 cannot credit), 'profile_link' (words
    pointing to the profile link, on a channel whose posts carry no clickable link), or None."""
    page = urlsplit(intensity.bounds(root)['conversion']['subscribe_url']).path.rstrip('/')
    untracked = False
    for url in intensity.URL_IN_TEXT.findall(post.get('words') or ''):
        url = url.rstrip('.,;:!?)')
        if urlsplit(url).path.rstrip('/') != page:
            continue
        for link in own_links(url):  # a link on this engine's own host only
            if link['tracked']:
                return 'tracked'
            tags = {}
            for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
                tags.setdefault(key.lower(), value.strip())
            untracked = untracked or bool(tags.get('utm_source') and tags.get('utm_content'))
    profile = intensity.bounds(root)['conversion']['profile_link_channels']
    if post.get('channel') in profile and PROFILE.search(post.get('words') or ''):
        return 'profile_link'  # the gate passes it on a profile-link channel, whatever else the words carry
    if untracked:
        return 'untracked'
    return None


def routed(post, root=intensity.ROOT):
    """True when the post carries a subscribe route (route_of), tracked by GA4 or not."""
    return route_of(post, root) is not None


def check(posts_read, now, root=intensity.ROOT):
    """{'checked', 'routeless': {'buffer', 'native'}, 'untracked', 'untracked_alarmed', 'unverified', 'alarm',
    'alarm_by', 'line'} over the last seven days' sent posts.

    untracked: posts whose only route is a two-tag link GA4 cannot credit; those sent before UNTRACKED_FROM count as
    routed, and those sent since (untracked_alarmed) raise the alarm as a missing route does. unverified: threads
    whose first item carries no route, never alarmed, because a thread's later items are not read yet."""
    now = instant(now)
    since, gate, late_from = now - WINDOW, instant(CHECKED_FROM), instant(UNTRACKED_FROM)
    made = [('buffer', p) for p in posts_read.get('posts') or []] + [('native', p) for p in posts_read.get('native') or []]
    routeless = {'buffer': 0, 'native': 0}
    alarm = {'buffer': 0, 'native': 0}
    checked = untracked = untracked_alarmed = unverified = 0
    for how, post in made:
        sent = post.get('sent_at')
        if sent is None or not since <= instant(sent) <= now:
            continue
        checked += 1
        kind = route_of(post, root)
        late = kind == 'untracked' and instant(sent) >= late_from  # from then on, no route
        if kind and not late:
            if kind == 'untracked':
                untracked += 1  # a route then, which GA4 cannot credit
            continue
        if post.get('thread_count'):
            unverified += 1  # its later items are not read yet, so a route there is not seen
            continue
        if late:
            untracked += 1
            untracked_alarmed += 1
            alarm[how] += 1
            continue
        routeless[how] += 1
        if instant(sent) >= gate:
            alarm[how] += 1
    line = ('Reconciliation over the last 7 days: ' + str(checked) + ' sent posts on the pinned channels; with no '
            'subscribe route ' + str(routeless['buffer']) + ' made in Buffer and ' + str(routeless['native'])
            + ' made natively; untracked by GA4 ' + str(untracked) + ' (a subscribe link without all four tags: '
            + str(untracked_alarmed) + ' sent from 14 November raise the alarm, as a missing route does); not '
            'verifiable ' + str(unverified) + ' (threads whose first item carries no route: a thread\'s later items '
            'are not read yet); approval not reconciled yet (go-live claim ledger)')
    return {'checked': checked, 'routeless': routeless, 'untracked': untracked, 'untracked_alarmed': untracked_alarmed,
            'unverified': unverified, 'alarm': sum(alarm.values()), 'alarm_by': alarm, 'line': line, 'host': OWN_HOST}
