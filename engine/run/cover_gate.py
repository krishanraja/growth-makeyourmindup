"""The release gate for a video's cover frame: every video goes out pointing at its designed cover (F133).

His words, on the Counting rat tails reel Buffer posted to Instagram on 14 Nov 2026 (Buffer post 6af7980e81e1228421cd5b7b,
F133): "the thumbnail is ridiculously poor, and that must never be the case." That post carried the raw cut with
thumbnailOffset null, so Instagram showed frame 0.

Buffer takes a video as {url, metadata {title, thumbnailOffset}} (engine/run/buffer_api.py): there is no field for a cover
image, so Buffer can only ever show a frame of the cut. Content-engine makes the cover and the cut with the cover baked in
(Ruling, Krish, 2026-11-26: content-engine makes every asset; covers and thumbnails come only from the v5 Library's
`python scripts/covers/make_covers.py <piece> --out <folder>`), and names the frame the cover sits at. Growth only checks
that frame is named before anything is saved or scheduled: release refuses any video call on a cover channel with no
thumbnailOffset (engine/run/release.py), the L0 carry refuses a stored draft with none (buffer_api.carried), and the maker
never saves a video draft without one. Never a null offset. Nothing here draws, composes or encodes a picture.
"""

# The channels whose grid tile or player shows a video's cover: Instagram, TikTok, YouTube, Facebook, Threads and X
# (the five vertical channels, AGENTS.md "Vertical content goes to all five", and YouTube Shorts).
COVER_CHANNELS = ('instagram', 'tiktok', 'youtube', 'facebook', 'threads', 'x')
# The same channels by Buffer service name (a readback carries channelService).
COVER_SERVICES = ('instagram', 'tiktok', 'youtube', 'facebook', 'threads', 'twitter')


def needs_cover(channel, kinds):
    """True when a post on this channel (engine id or Buffer service) carries a video."""
    return (channel in COVER_CHANNELS or channel in COVER_SERVICES) and 'video' in set(kinds or ())


def offset_ok(value):
    """A thumbnailOffset Buffer can be given: a whole number of milliseconds, never null, never negative."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
