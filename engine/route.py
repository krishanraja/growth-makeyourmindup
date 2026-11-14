"""One subscribe route, built one way and checked one way, so every gate and GA4 agree (13 November 2026).

Before this, three places disagreed about what a tracked subscribe link is: the subscribe gate needed two
tags (utm_source and utm_content, engine/intensity.py), the GA4 join needed four (engine/run/ga4.py
own_links: utm_source, utm_medium, utm_campaign and utm_content), and the gate's own hint suggested
utm_medium=organic while the profile links Krish approved use utm_medium=social (jobs/channel-audit.md). A link
could pass the gate and still never be credited by GA4, so its post could only ever read "insufficient".

subscribe_url builds the one route: the subscribe page with all four tags, utm_medium=social (his approved
scheme), utm_campaign=growth and a unique utm_content per post or slot. intensity.subscribe_errors, the
subscribe gate and GA4 all read links by the same four tags. line_errors checks a go-live line (its words and
its first comment) the way the Buffer hook checks a hand-made call, so the engine's own path carries the same
gate as a session's (engine/run/handoff.py and engine/run/autorelease.py).

The route's shape is also written down once, for every repository that builds a subscribe link
(content-engine's kit, krishraja.com): specs/subscribe-route.json (mymu-subscribe-route/1, audit 2026-11-14,
I-09). tests/test_subscribe_route_spec.py fails when this module, engine/intensity.py, the gate or GA4's reader
stops equalling it, so change the spec and the code in one pull request.

Offline only: no network, no credentials. Nothing here posts, sends, publishes or spends.
"""
import re
from urllib.parse import urlencode

from . import intensity, subscribe_gate

UTMS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
MEDIUM = 'social'
CAMPAIGN = 'growth'
CONTENT = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')


def subscribe_url(channel, content, campaign=CAMPAIGN, root=intensity.ROOT):
    """The tagged subscribe page for one post on one channel: all four UTMs, utm_content unique to the post."""
    if channel not in subscribe_gate.CHANNEL_BY_ID.values():
        raise ValueError('not one of this engine\'s pinned channels: ' + str(channel))
    content = str(content).strip().lower()
    if not CONTENT.match(content):
        raise ValueError('utm_content must be a post or slot id: lower case letters, digits, - and _, at most 64')
    if not CONTENT.match(campaign):
        raise ValueError('utm_campaign must be lower case letters, digits, - and _')
    page = intensity.bounds(root)['conversion']['subscribe_url']
    return page + '?' + urlencode([('utm_source', channel), ('utm_medium', MEDIUM), ('utm_campaign', campaign),
                                   ('utm_content', content)])


def content_of(post_id):
    """A slot or post id as a utm_content subscribe_url takes: lower case, each run of other characters made one -,
    no leading - or _, at most 64. ValueError when nothing is left."""
    content = re.sub(r'[^a-z0-9_-]+', '-', str(post_id).strip().lower()).lstrip('-_')[:64]
    if not CONTENT.match(content):
        raise ValueError('utm_content needs a slot or post id with a letter or digit')
    return content


def item_content(item, channel):
    """utm_content for a post that is a board item: content_of(<board item id>-<channel>), the rule agreed with
    Control Center (audit 2026-11-14, I-09; its buffer_sent sweep binds a post whose utm_content equals this, or the
    bare content_of(item), never a prefix). Unique per post, since one item goes out on several channels. ValueError
    for a channel that is not pinned or an id that leaves nothing."""
    if channel not in subscribe_gate.CHANNEL_BY_ID.values():
        raise ValueError('not one of this engine\'s pinned channels: ' + str(channel))
    content = content_of(str(item) + '-' + channel)
    if not content.endswith('-' + channel):
        raise ValueError('a board item id that long would lose its channel: at most 64 characters in all')
    return content


def line_errors(line, urgency=None, root=intensity.ROOT):
    """Why a go-live line (engine/run/autorelease.py LINE_KEYS) would send a post with no subscribe route, or [].

    The same check the Buffer hook makes on a hand-made call (engine/subscribe_gate.py), on the line's words
    and its first comment. Below the conversion urgency nothing is required; another venture's channel is
    never this engine's and passes."""
    if not isinstance(line, dict):
        return ['subscribe_route_missing: the go-live line is unreadable']
    meta = line.get('meta') if isinstance(line.get('meta'), dict) else {}
    call = {'channelId': line.get('buffer_channel_id'), 'text': line.get('words') or '',
            'metadata': meta.get('metadata') if isinstance(meta.get('metadata'), dict) else {}}
    return subscribe_gate.errors('create_post', call, urgency, root)
