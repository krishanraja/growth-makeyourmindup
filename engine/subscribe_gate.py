"""The subscribe gate on every Buffer post this engine's channels send (Ruling, Krish, 2026-11-12).

From 2 to 11 November the eight pinned makeyourmindup channels sent 58 posts through Buffer and none of them
asked anyone to subscribe: hand-run sessions drafted straight into Buffer with the connector, so the subscribe
route that release and social preflight require (subscribe_cta, intensity.json conversion) never ran. This
module is the one check on the path every post takes, the Buffer connector's create_post and edit_post; the
Claude Code hook in .claude/hooks/buffer-subscribe-gate.py calls it before the connector runs.

A post on one of this engine's pinned channels (engine/buffer_channels.py) needs the tagged subscribe page
(intensity.json conversion.subscribe_url, with all four UTM tags GA4 credits it by, engine/route.py, and
utm_source naming the channel):

- in the post's own words, on a channel whose posts carry a clickable link;
- or in the first comment (Buffer's firstComment), the first reply;
- or, on Instagram and TikTok, where a post's words carry no clickable link, in the first comment, or words
  that point to the profile link (whose link is the tagged subscribe page, engine/channel_audit.py).

Below the conversion urgency nothing is required, as everywhere else. Other ventures' channels in the shared
Buffer organisation are never this engine's and pass untouched. Offline only: no network, no credentials.
"""
from urllib.parse import parse_qs, urlsplit

from . import intensity
from .buffer_channels import BUFFER_CHANNEL_ID

HOLD = 'subscribe_route_missing'
CHANNEL_BY_ID = {v: k for k, v in BUFFER_CHANNEL_ID.items()}
# Buffer's metadata key for each channel, where it differs from the channel name: Buffer keeps an X post's
# metadata (its thread among it) under twitter, as its create_post schema names it.
SERVICE = {'substack-notes': 'substack', 'x': 'twitter'}
# The channel each of Buffer's metadata keys belongs to, the inverse of SERVICE (an edit names no channel).
CHANNEL_BY_SERVICE = {SERVICE.get(channel, channel): channel for channel in BUFFER_CHANNEL_ID}
TOOLS = ('create_post', 'edit_post')


def _texts(tool_input, channel):
    """(words, first_comment, other_links): the post's own words (thread items included), its first comment
    and any link Buffer attaches outside the words (link card, story link sticker)."""
    meta = (tool_input.get('metadata') or {})
    key = SERVICE.get(channel, channel)
    service = meta.get(key) or {}
    thread = list(service.get('thread') or [])
    words = [tool_input.get('text') or '']
    for item in thread:
        words.append(item.get('text') or '')
    links = []
    # A link card sits on the post or on a thread item, on the item itself or in Buffer's documented shape for a
    # thread item (thread[i].metadata.<service>.linkAttachment).
    for holder in [service] + thread + [(item.get('metadata') or {}).get(key) or {} for item in thread]:
        card = (holder.get('linkAttachment') or {}) if isinstance(holder, dict) else {}
        if card.get('url'):
            links.append(card['url'])
    if service.get('link'):
        links.append(service['link'])
    return '\n'.join(words), service.get('firstComment') or '', links


def _source_errors(url, channel):
    tag = (parse_qs(urlsplit(url).query).get('utm_source') or [''])[0].strip().lower()
    names = {channel, SERVICE.get(channel, channel)}
    return [] if tag in names else ['utm_source=' + (tag or '(none)') + ' does not name the channel ' + channel]


def _edit_channel(tool_input, root):
    """(channel, problems) for an edit_post, which names its post and never its channel (Buffer's edit_post takes a
    postId). Offline, so it never reads the post.

    The post is this engine's when the words the edit sends (its text, thread and first comment) speak for the
    publication, as its subscribe page does. Any other post passes untouched, so another venture's post is never
    blocked, and an edit that changes no words (a reschedule, an asset swap) keeps what was checked. This engine's
    post is judged on its own channel: the one Buffer's metadata key names (twitter is X), else the one the
    utm_source of a subscribe URL in its words names; never a default. When neither names one channel it holds."""
    if 'text' not in tool_input:
        return None, []
    meta = tool_input.get('metadata') or {}
    services = {k: v for k, v in meta.items() if isinstance(v, dict)}
    said = [str(tool_input.get('text') or '')]
    for service in services.values():
        said.append(str(service.get('firstComment') or ''))
        said += [str(item.get('text') or '') for item in service.get('thread') or [] if isinstance(item, dict)]
    said = '\n'.join(said)
    if 'makeyourmindup' not in said.lower():
        return None, []
    named = {CHANNEL_BY_SERVICE[k] for k in services if k in CHANNEL_BY_SERVICE}
    if services and not named:
        return None, []  # a service none of this engine's channels is on
    if not named:
        page = urlsplit(intensity.bounds(root)['conversion']['subscribe_url']).path.rstrip('/')
        for url in intensity.URL_IN_TEXT.findall(said):
            parts = urlsplit(url.rstrip('.,;:!?)'))
            if parts.path.rstrip('/') == page:
                tag = (parse_qs(parts.query).get('utm_source') or [''])[0].strip().lower()
                if CHANNEL_BY_SERVICE.get(tag, tag) in BUFFER_CHANNEL_ID:
                    named.add(CHANNEL_BY_SERVICE.get(tag, tag))
    if len(named) == 1:
        return named.pop(), []
    return None, [HOLD + ': this edit changes the words of a makeyourmindup post but names ' + ('no' if not named else
                  'more than one') + ' channel, so its subscribe route cannot be checked. Carry the post\'s metadata '
                  'forward (get_post) or put the tagged subscribe URL for its channel in the words']


def _tagged(text, channel, root):
    """The first tagged subscribe URL in text that names this channel, and why each other one fails."""
    page = intensity.bounds(root)['conversion']['subscribe_url']
    why = []
    for url in intensity.URL_IN_TEXT.findall(text or ''):
        url = url.rstrip('.,;:!?)')
        if urlsplit(url).path.rstrip('/') != urlsplit(page).path.rstrip('/'):
            continue
        problems = intensity.subscribe_errors({'url': url, 'placement': 'in_post'}, channel, url, None, 5, root)
        problems = problems or _source_errors(url, channel)
        if not problems:
            return url, []
        why += problems
    return None, why


def errors(tool_name, tool_input, urgency=None, root=intensity.ROOT):
    """Why this Buffer call would send a post with no subscribe route, or [].

    tool_name is the connector tool's name (anything ending create_post or edit_post); tool_input its input.
    urgency is the North Star urgency (intensity.state); None reads it."""
    if not str(tool_name).endswith(TOOLS) or not isinstance(tool_input, dict):
        return []
    channel = CHANNEL_BY_ID.get(tool_input.get('channelId'))
    unnamed = []
    if str(tool_name).endswith('edit_post') and not tool_input.get('channelId'):  # absent, null or empty
        # An edit that sends no channelId, or one present but null, names no channel: it is resolved the same way.
        channel, unnamed = _edit_channel(tool_input, root)
    if channel is None and not unnamed:
        return []
    if urgency is None:
        urgency = intensity.state(root)['urgency']
    if not intensity.subscribe_required(urgency, root):
        return []
    if unnamed:
        return unnamed
    words, first, links = _texts(tool_input, channel)
    url, why = _tagged(words + '\n' + '\n'.join(links), channel, root)
    if url:
        return []
    url, why_first = _tagged(first, channel, root)
    if url:
        return []
    conversion = intensity.bounds(root)['conversion']
    if channel in conversion['profile_link_channels']:
        if not intensity.subscribe_errors({'url': conversion['subscribe_url'] + '?utm_source=' + channel
                                           + '&utm_medium=social&utm_content=bio',
                                           'placement': 'profile_link'},
                                          channel, words, None, urgency, root):
            return []
    page = conversion['subscribe_url']
    where = ('in the first comment, or words that point to the profile link'
             if channel in conversion['profile_link_channels'] else 'in the words or the first comment')
    return [HOLD + ': this ' + channel + ' post carries no subscribe route at U' + str(urgency) + '. Put '
            + page + '?utm_source=' + channel + '&utm_medium=social&utm_campaign=growth&utm_content=<post or slot id> '
            + where + ' (intensity.json conversion; Ruling, Krish, 2026-11-12)'] + why + why_first
