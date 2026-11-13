"""This engine's pinned Buffer channels, and the other ventures' and engines' channels it never touches.

The Buffer organisation is shared with other ventures, so a service or a name
alone never identifies this engine's account. Release (engine/run/release.py)
and social preflight (engine/social.py) both read this one table, so a draft
prepared by the daily job and a post scheduled by release are held to the same
ids. Offline only: no network, no credentials.
"""
from . import owners

# Channel id -> the one Buffer channelId this engine may act on, read with a
# read-only list_channels of "My organization" on 2026-10-28. A channel is
# pinned by service, name and this id together; a new id under the same name
# holds until a reviewed change updates this table. The Substack entry is
# Krish's profile, which carries Notes (R81).
# Threads branded pin verified with list_channels and get_channel on 13 Nov 2026:
# makeyourmind.up, https://www.threads.net/@makeyourmind.up, connected and unlocked.
# The old personal channel ID cannot pass this pin or the release name check.
# Krish's LinkedIn is no longer pinned here: it is growth-mindmake's (HANDED_OFF_CHANNELS below).
BUFFER_CHANNEL_ID = {'substack-notes': '6ae09edc2f1f5ed648e9e48c', 'threads': '6af6cf0f62b70b94b017c3b0',
                     'x': '6adccbf5778b240e2fafc457', 'instagram': '6adccb3a778b240e2fafbb63',
                     'facebook': '6adccc1e778b240e2fafc615', 'tiktok': '6adccbdd778b240e2fafc32e',
                     'youtube': '6adccf83778b240e2fafe7af'}
# The Buffer channels this engine pinned once and handed to another engine (engine/owners.py), by
# channelId. Never this engine's again: Ruling (Krish, 2026-11-13), growth-mindmake owns Krish's
# personal LinkedIn, so its Buffer channel (read with list_channels on 2026-10-28) is refused here.
HANDED_OFF_CHANNELS = {'6adccba0778b240e2fafc06d': 'linkedin'}
# The other ventures' channels in the same Buffer organisation. Never this
# engine's, whatever a readback, a slot, a package or a hand-built call says
# (plan of 28 Oct 2026, W5: never the Full Time or Heartside channels).
DENIED_CHANNELS = {'6ae09bba2f1f5ed648e9cbfc': 'fulltime.fm TikTok',
                   '6ae096d32f1f5ed648e99e98': 'Heartside Facebook',
                   '6ae0973f2f1f5ed648e9a327': 'yourdoghasnotes TikTok',
                   '6ae096872f1f5ed648e99b6d': 'yourdoghasnotes Instagram'}


def channel_id_errors(channel, channel_id):
    """Why channel_id is not this engine's pinned Buffer channel for channel, if it is not."""
    if not isinstance(channel_id, str):
        return ['Buffer channelId must be text, not ' + type(channel_id).__name__]
    if channel_id in HANDED_OFF_CHANNELS or owners.owner(channel):
        return ['Buffer channel ' + channel_id + ': '
                + owners.refusal(HANDED_OFF_CHANNELS.get(channel_id) or channel)]
    if channel_id in DENIED_CHANNELS:
        return ['Buffer channel ' + channel_id + ' is ' + DENIED_CHANNELS[channel_id]
                + ', another venture\'s; this engine never acts on it']
    if channel_id != BUFFER_CHANNEL_ID.get(channel):
        return ['Buffer channel ' + str(channel_id) + ' is not this engine\'s pinned ' + str(channel) + ' channel']
    return []


def report_field():
    """This engine's channels for Control Center (protocol 1.17.0 buffer_channels): a go-live of posts is
    approved only when each post names exactly the id listed here for its channel."""
    return {'allowed': dict(sorted(BUFFER_CHANNEL_ID.items())),
            'denied': sorted(set(DENIED_CHANNELS) | set(HANDED_OFF_CHANNELS))}
