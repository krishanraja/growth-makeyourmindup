"""Channels this engine no longer owns, and the engine that owns each now. Standard library only, no I/O.

Ruling (Krish, 2026-11-13), asked "Which engine should own your personal LinkedIn posts (you still click
every post)?" and answered "growth-mindmake owns it": growth-mindmake (krishanraja/growth-mindmake) owns
Krish's personal LinkedIn posts (Mindmake's published thinking, about three a week) and the replies to
everyone who engages with them. He still clicks every post (LinkedIn stays human_publish_only). His X and
the publication's own accounts stay with this engine.

So this engine drafts, queues, taps, schedules and pins nothing on his personal LinkedIn: no post, no
comment, no engagement tap and no go-live. Reading LinkedIn (research, the radar's trend reading, measuring
what others post, and judging this engine's own posts there from before the handover: before_handover) is
not owning the channel, and stays. The channel record says the same (social/channels/linkedin.json,
owned_by), and engine/social.py:inventory checks that the two agree. A page is the channel's by the host a
browser opens (page_host), whatever label an item carries (page_refusal).
"""
import datetime as dt
import re
import unicodedata
from urllib.parse import unquote

# Channel id -> the engine that owns it now.
HANDED_OFF = {'linkedin': 'growth-mindmake'}
# Channel id -> the day the ruling handed it over.
SINCE = {'linkedin': '2026-11-13'}
# Channel id -> the web hosts that open it, so a page on it is known whatever label a draft carries
# (a host matches itself and any subdomain: www.linkedin.com, uk.linkedin.com; lnkd.in is its short link).
HOSTS = {'linkedin': ('linkedin.com', 'lnkd.in')}
# The hold code every refusal carries, so Control Center and the reports name one reason.
HOLD = 'channel_owned_by_another_engine'


def owner(channel):
    """The engine that owns channel now, when it is no longer this engine's; None when it is.

    A platform label that starts with the channel id ("LinkedIn", "linkedin-comment") counts, the same
    way engine/control_center.py reads a go-live's channel."""
    if not isinstance(channel, str):
        return None
    key = channel.strip().lower()
    for name, engine in HANDED_OFF.items():
        if key.startswith(name):
            return engine
    return None


def handed_off_channel(channel):
    """The channel id channel names when it is no longer this engine's, else None."""
    if not isinstance(channel, str):
        return None
    key = channel.strip().lower()
    return next((name for name in HANDED_OFF if key.startswith(name)), None)


def page_host(url):
    """The host a browser opens for url, as Control Center's URL parser reads it, lower case, or ''.

    The host is read the way a browser reads it, so a page cannot pass as another site by its spelling:
    a backslash counts as a slash, the user name and port are dropped, the host is percent-decoded and put
    in its plain form (full-width letters and dots become ASCII), an internationalised (xn--) label is
    decoded, and a trailing dot is dropped."""
    if not isinstance(url, str):
        return ''
    text = url.strip().replace('\\', '/')
    match = re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', text)
    rest = text[match.end():] if match else text
    authority = re.split(r'[/?#]', rest.lstrip('/'), maxsplit=1)[0]
    host = unquote(authority.rpartition('@')[2])
    host = unicodedata.normalize('NFKC', host).replace('\u3002', '.').lower()
    if not host.startswith('['):
        host = re.sub(r':\d*$', '', host)
    labels = []
    for label in host.split('.'):
        if label.startswith('xn--'):
            try:
                label = label.encode('ascii').decode('idna')
            except (UnicodeError, ValueError):
                pass
        labels.append(unicodedata.normalize('NFKC', label).lower())
    return '.'.join(labels).rstrip('.')


def url_channel(url):
    """The handed-off channel id whose page url opens, else None: read from the host, never the label."""
    host = page_host(url)
    for name, hosts in HOSTS.items():
        if any(host == h or host.endswith('.' + h) for h in hosts):
            return name
    return None


def page_refusal(label, *urls):
    """Why an item on this label that opens these pages is another engine's, or '': by its label, or by any
    page it opens (url_channel), whatever label it carries. The one check the engagement tap queue
    (engine/engage.py) and the Engagement engine's queue (engine/engines/engagement.py) both make."""
    if owner(label):
        return refusal(label)
    for url in urls:
        opens = url_channel(url)
        if opens:
            return refusal(opens)
    return ''


def before_handover(channel, when):
    """True when when (an ISO 8601 time or date, or a datetime) falls before the day channel was handed over, in UTC.

    A post made then was this engine's, so its readers still read and judge it as history; a post from the
    day of the handover on is the new owner's. False for a channel still this engine's, and for a time that
    cannot be read."""
    name = handed_off_channel(channel)
    if name is None:
        return False
    if isinstance(when, dt.datetime):
        when = when.isoformat()
    if not isinstance(when, str) or not when.strip():
        return False
    try:
        if len(when.strip()) == 10:
            at = dt.datetime.combine(dt.date.fromisoformat(when.strip()), dt.time(0), dt.timezone.utc)
        else:
            at = dt.datetime.fromisoformat(when.strip().replace('Z', '+00:00'))
            if at.tzinfo is None:
                return False
    except ValueError:
        return False
    since = dt.datetime.combine(dt.date.fromisoformat(SINCE[name]), dt.time(0), dt.timezone.utc)
    return at < since


def refusal(channel):
    """One plain line saying where the channel went, for a hold, a finding or an error."""
    name = handed_off_channel(channel)
    if name is None:
        return ''
    label = {'linkedin': "Krish's personal LinkedIn"}.get(name, name)
    return (label + ' is ' + HANDED_OFF[name] + "'s since " + SINCE[name] + ' (Ruling, Krish, ' + SINCE[name]
            + '): this engine drafts, queues, taps and pins nothing there')
