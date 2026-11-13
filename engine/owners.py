"""Channels this engine no longer owns, and the engine that owns each now. No imports, no I/O.

Ruling (Krish, 2026-11-13), asked "Which engine should own your personal LinkedIn posts (you still click
every post)?" and answered "growth-mindmake owns it": growth-mindmake (krishanraja/growth-mindmake) owns
Krish's personal LinkedIn posts (Mindmake's published thinking, about three a week) and the replies to
everyone who engages with them. He still clicks every post (LinkedIn stays human_publish_only). His X and
the publication's own accounts stay with this engine.

So this engine drafts, queues, taps, schedules and pins nothing on his personal LinkedIn: no post, no
comment, no engagement tap and no go-live. Reading LinkedIn (research, the radar's trend reading, measuring
what others post) is not owning the channel, and stays. The channel record says the same
(social/channels/linkedin.json, owned_by), and engine/social.py:inventory checks that the two agree.
"""

# Channel id -> the engine that owns it now.
HANDED_OFF = {'linkedin': 'growth-mindmake'}
# Channel id -> the day the ruling handed it over.
SINCE = {'linkedin': '2026-11-13'}
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


def refusal(channel):
    """One plain line saying where the channel went, for a hold, a finding or an error."""
    name = handed_off_channel(channel)
    if name is None:
        return ''
    label = {'linkedin': "Krish's personal LinkedIn"}.get(name, name)
    return (label + ' is ' + HANDED_OFF[name] + "'s since " + SINCE[name] + ' (Ruling, Krish, ' + SINCE[name]
            + '): this engine drafts, queues, taps and pins nothing there')
