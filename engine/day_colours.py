"""The colour each day's asset wears, Monday to Saturday (R125).

Krish, 4 Nov 2026: "lightly colour-code the thumbnail and cover asset templates for Monday, Wednesday, and Friday?
When they go on Facebook and Instagram they're slightly differently coloured based on the colour theme of each day.
The off days are neutral colours or the colours we have planned, but not under the Monday, Wednesday, or Friday
panels or colours. Just subtle brand recognition would be nice as a hard rule across Monday to Saturday assets."

A series day wears its subchannel's colour; every other day wears the house mint and no subchannel's colour. The
same table is content-engine's docs/CAROUSEL-STANDARD.md and its scripts/pages/brand.py `day_look`; the hex values
are the kit's own (render/templates.json "kit" "colours").
"""
import datetime as dt

# weekday (Monday is 0): (subchannel, kit tone, hex)
SERIES_DAYS = {0: ('follow.the.money', 'butter', '#FFD84D'),
               2: ('under.the.hood', 'lilac', '#B7A6FF'),
               4: ('mind.the.gap', 'coral', '#FF6A4D')}
OFF_DAY = ('house', 'mint', '#7EF0C0')
SERIES_COLOURS = {hexval for _, _, hexval in SERIES_DAYS.values()}
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


def day_look(date):
    """{'day', 'series_day', 'owner', 'tone', 'colour'} for a publishing date (YYYY-MM-DD or a date)."""
    day = date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date)[:10])
    owner, tone, colour = SERIES_DAYS.get(day.weekday(), OFF_DAY)
    return {'day': WEEKDAYS[day.weekday()], 'series_day': day.weekday() in SERIES_DAYS, 'owner': owner,
            'tone': tone, 'colour': colour}


def day_rule(date):
    """The rule in one line, for a brief or a prompt."""
    look = day_look(date)
    if look['series_day']:
        return (look['day'] + ': ' + look['owner'] + "'s day. Its colour, " + look['tone'] + ' (' + look['colour']
                + '), is the accent; no other subchannel colour (butter, lilac or coral) appears.')
    return (look['day'] + ': an off day. The accent is the house mint (' + look['colour'] + ') on neutral ink, '
            'cream or green; no subchannel colour (butter, lilac or coral) appears anywhere.')


def colour_errors(painted, date):
    """What breaks the day's rule among the colours an asset paints (hex strings, any case). With no date the asset
    is held as an off day, so it can never wear a subchannel's colour by accident."""
    look = day_look(date) if date else {'day': 'An undated asset', 'series_day': False, 'owner': OFF_DAY[0],
                                        'tone': OFF_DAY[1], 'colour': OFF_DAY[2]}
    found = {str(c).upper() for c in painted}
    wrong = sorted(found & (SERIES_COLOURS - ({look['colour']} if look['series_day'] else set())))
    if not wrong:
        return []
    if look['series_day']:
        return [look['day'] + ' wears ' + look['owner'] + "'s colour only; it paints another day's " + ', '.join(wrong)]
    return [look['day'] + (' is an off day' if date else ' is held as an off day') + ' and wears no subchannel colour; it paints ' + ', '.join(wrong)]
