"""Growth's assets never wear a series' colour or name (R125).

Krish, 4 Nov 2026: "Post random memes on a Monday but that doesn't mean it's Monday's colour and brand. Then follow
the money. There is only one "follow the money" piece, one "mind the gap" piece, and one "mind the gap" piece every
week. Other stuff can be fluid, maybe changeable." and "I should be allowed to post random stuff on any day but it
doesn't take on the brand colours of Follow the Money, Mind the Gap, or Under the Hood. Which are only once a week,
omni-channel, and a completely different distribution format". Asked whether a post Growth makes from a series piece
wears its colour, he chose the series piece's own hero assets only.

The series pieces and their hero assets (article, both cuts, thumbnails, covers) are content-engine's; its
docs/CAROUSEL-STANDARD.md and scripts/pages/brand.py `series_look` hold them. Everything Growth makes, on any day
(memes, off-day carousels, Notes, derived posts), wears none of butter, lilac or coral and names no subchannel:
the house tones and mint carry it. The hex values are the kit's own (render/templates.json "kit" "colours").
"""
import re

# subchannel: (kit tone, hex)
SERIES = {'follow.the.money': ('butter', '#FFD84D'),
          'under.the.hood': ('lilac', '#B7A6FF'),
          'mind.the.gap': ('coral', '#FF6A4D')}
SERIES_COLOURS = {hexval for _, hexval in SERIES.values()}
SERIES_TONES = {tone for tone, _ in SERIES.values()}
HOUSE_TONE = ('mint', '#7EF0C0')
NAMED = re.compile(r'\b(' + '|'.join(re.escape(n) for n in SERIES) + r')\b', re.IGNORECASE)


def asset_rule():
    """The rule in one line, for a brief or a prompt."""
    return ('No series colour or name: Growth\'s assets belong to no series on any day. Neutral ink, cream or green, '
            'with the house mint (' + HOUSE_TONE[1] + ') at most as the one accent; never butter, lilac or coral, and '
            'never follow.the.money, under.the.hood or mind.the.gap.')


def colour_errors(painted):
    """The series colours among the colours an asset paints (hex strings, any case)."""
    wrong = sorted({str(c).upper() for c in painted} & SERIES_COLOURS)
    if not wrong:
        return []
    return ['wears a series colour (' + ', '.join(wrong) + '); only a series piece\'s own hero assets do, and Growth makes none']


def name_errors(texts):
    """The subchannel names among an asset's words."""
    found = sorted({m.group(1).lower() for t in texts if isinstance(t, str) for m in NAMED.finditer(t)})
    if not found:
        return []
    return ['names a series (' + ', '.join(found) + '); only a series piece\'s own hero assets do']
