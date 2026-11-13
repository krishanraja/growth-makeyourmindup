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
# Buffer's metadata key for each channel, where it differs from the channel name.
SERVICE = {'substack-notes': 'substack'}
TOOLS = ('create_post', 'edit_post')


def _texts(tool_input, channel):
    """(words, first_comment, other_links): the post's own words (thread items included), its first comment
    and any link Buffer attaches outside the words (link card, story link sticker)."""
    meta = (tool_input.get('metadata') or {})
    service = meta.get(SERVICE.get(channel, channel)) or {}
    words = [tool_input.get('text') or '']
    for item in service.get('thread') or []:
        words.append(item.get('text') or '')
    links = []
    for holder in [service] + list(service.get('thread') or []):
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
    if str(tool_name).endswith('edit_post') and channel is None:
        # An edit names only its post. It is this engine's when its words or first comment speak for the
        # publication; an edit that changes no words (a reschedule, an asset swap) keeps what was checked.
        meta = tool_input.get('metadata') or {}
        service = next((k for k, v in meta.items() if isinstance(v, dict) and ('firstComment' in v or 'thread' in v)), None)
        said = (tool_input.get('text') or '') + ' ' + str((meta.get(service) or {}).get('firstComment') or '')
        if 'text' not in tool_input or 'makeyourmindup' not in said.lower():
            return []
        channel = {'substack': 'substack-notes'}.get(service, service) or 'threads'
    if channel is None:
        return []
    if urgency is None:
        urgency = intensity.state(root)['urgency']
    if not intensity.subscribe_required(urgency, root):
        return []
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
