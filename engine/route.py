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

The weekly edition (Krish, 2026-11-25: one email a week, Saturday 08:00 New York) has its own tags, the spec's
`edition` block: utm_source=newsletter, utm_medium=email, utm_campaign=weekly and
utm_content=edition-<the Saturday>-<place>. edition_url builds one of its links; edition_tags reads one back.
The subscribe gate and GA4's reader credit such a link to the source newsletter, never to a social channel, so
the social sources and the pinned Buffer channels stay exactly as they were.

Offline only: no network, no credentials. Nothing here posts, sends, publishes or spends.
"""
import datetime as dt
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from . import intensity, subscribe_gate

UTMS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
MEDIUM = 'social'
CAMPAIGN = 'growth'
CONTENT = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')
# The weekly edition's own links (specs/subscribe-route.json, edition; the contract with content-engine, 25 Nov 2026).
EDITION_SOURCE = 'newsletter'
EDITION_MEDIUM = 'email'
EDITION_CAMPAIGN = 'weekly'
EDITION_CONTENT = re.compile(r'^edition-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{1,40}$')
EDITION_PLACES = ('forward', 'subscribe', 'piece-mon', 'piece-wed', 'piece-fri', 'video-mon', 'video-wed',
                  'video-fri', 'note')
# A subscribe place goes to the one page; a piece or video place goes to the piece's own address.
EDITION_PAGE_PLACES = ('forward', 'subscribe')
EDITION_TARGET_PLACES = ('piece-mon', 'piece-wed', 'piece-fri', 'video-mon', 'video-wed', 'video-fri')


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


def edition_content(edition_date, place):
    """utm_content for one link in the weekly edition: edition-<the Saturday, YYYY-MM-DD>-<place>.

    edition_date is the Saturday the edition goes out (a date or YYYY-MM-DD); place is one of EDITION_PLACES.
    ValueError for any other date or place, so a link the spec does not describe is never built."""
    text = edition_date.isoformat()[:10] if isinstance(edition_date, dt.date) else str(edition_date)
    if not re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', text):
        raise ValueError('the edition date is YYYY-MM-DD, not ' + text)
    try:
        day = dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError('the edition date is not a real date: ' + text) from None
    if day.weekday() != 5:
        raise ValueError('the edition date is the Saturday it goes out, not ' + day.strftime('%A ') + text)
    if place not in EDITION_PLACES:
        raise ValueError('not one of the edition places (' + ', '.join(EDITION_PLACES) + '): ' + str(place))
    content = 'edition-' + text + '-' + place
    if not EDITION_CONTENT.match(content):
        raise ValueError('not an edition utm_content: ' + content)
    return content


def edition_url(edition_date, place, target=None, root=intensity.ROOT):
    """One link in the weekly edition, with all four of its tags (specs/subscribe-route.json, edition).

    A subscribe place (forward, subscribe) goes to the one subscribe page and takes no target. A piece or video
    place goes to target, the piece's own https address on the publication, with the same four tags after any
    query it already has. note goes to either. ValueError for a target on another host, one that already carries a
    utm_ tag, or a place sent to the wrong address."""
    content = edition_content(edition_date, place)
    page = intensity.bounds(root)['conversion']['subscribe_url']
    tags = [('utm_source', EDITION_SOURCE), ('utm_medium', EDITION_MEDIUM), ('utm_campaign', EDITION_CAMPAIGN),
            ('utm_content', content)]
    if target is None:
        if place in EDITION_TARGET_PLACES:
            raise ValueError('a ' + place + ' link goes to the piece\'s own address: pass it as target')
        return page + '?' + urlencode(tags)
    if place in EDITION_PAGE_PLACES:
        raise ValueError('a ' + place + ' link goes to the one subscribe page, never to another address')
    host = urlsplit(page).hostname
    try:
        parts = urlsplit(str(target))
        port = parts.port
    except ValueError:
        raise ValueError('the piece address is not a URL: ' + str(target)) from None
    if (parts.scheme != 'https' or (parts.hostname or '').lower() != host or parts.username or parts.password
            or port is not None or not parts.path.strip('/')):
        raise ValueError('a piece link goes to the piece\'s own https address on ' + host + ', not ' + str(target))
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(key.lower().startswith('utm_') for key, _ in query):
        raise ValueError('the piece address already carries a utm_ tag; pass it without one')
    link = 'https://' + parts.netloc + parts.path + '?' + urlencode(query + tags)
    return link + ('#' + parts.fragment if parts.fragment else '')


def edition_tags(url, root=intensity.ROOT):
    """The weekly edition's tags read back from url, or None when url is not one of the edition's links.

    It is one when it is on the publication's own host and carries the edition's three fixed tags exactly
    (utm_source=newsletter, utm_medium=email, utm_campaign=weekly) and an edition utm_content. Returns
    {source, content, edition_date, place}: source is what the link is credited to, always newsletter."""
    try:
        parts = urlsplit(str(url))
        host = (parts.hostname or '').lower()
    except ValueError:
        return None
    if host != urlsplit(intensity.bounds(root)['conversion']['subscribe_url']).hostname:
        return None
    tags = {}
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        tags.setdefault(key.lower(), value)
    fixed = (tags.get('utm_source'), tags.get('utm_medium'), tags.get('utm_campaign'))
    content = tags.get('utm_content') or ''
    if fixed != (EDITION_SOURCE, EDITION_MEDIUM, EDITION_CAMPAIGN) or not EDITION_CONTENT.match(content):
        return None
    return {'source': EDITION_SOURCE, 'content': content, 'edition_date': content[8:18], 'place': content[19:]}


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
