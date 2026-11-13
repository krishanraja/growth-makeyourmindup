"""How hard this engine pushes: the North Star gap and the volume caps it allows.

Ruling (Krish, 2026-10-29): At U3 to U5, engines and Control Center may raise
volume caps up to each repo's existing policy bounds without a signed week
spec. This is volume only: walls unchanged.

The urgency is read from NOW.md's state line (engine/run/measure.py), checked
against this week's ladder rung, and raised to Control Center's own reading
when the directive carries one (protocol 1.4.0 `north_star.intensity`). A week
nobody has measured is U4, as the harness contract says. The bounds live in
intensity.json; nothing here touches a wall, spend, approval or Krish's time.
"""
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from .core import http_url, instant, ny_time, read_json
from .run import measure
from .social import max_daily_posts

ROOT = Path(__file__).resolve().parents[1]
BOUNDS = 'intensity.json'
PLACEMENTS = ('in_post', 'first_reply', 'profile_link')
# The four tags GA4 credits a link by (engine/run/ga4.py UTMS; engine/route.py builds them): a link with fewer
# passes no gate, because its post could never be judged by the subscribers it brought.
SOURCE_TAGS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
PROFILE_TAGS = ('utm_source', 'utm_content')
OUTREACH_MAX = 10


def bounds(root=ROOT):
    path = Path(root) / BOUNDS
    value = read_json(path if path.is_file() else ROOT / BOUNDS)
    taps = value['engagement_taps']['by_urgency']
    if sorted(taps) != ['1', '2', '3', '4', '5'] or any(not isinstance(v, int) or not 1 <= v <= 25 for v in taps.values()):
        raise ValueError('intensity.json engagement_taps needs U1 to U5, each 1 to 25')
    if value['daily_posts'].get('bound') != 'social_policy':
        raise ValueError('intensity.json daily_posts bound is the channel policy in engine/social.py, never a number of its own')
    conversion = value.get('conversion')
    if (not isinstance(conversion, dict) or conversion.get('applies_from_urgency') not in (1, 2, 3, 4, 5)
            or not isinstance(conversion.get('subscribe_url'), str)
            or not conversion['subscribe_url'].startswith('https://')
            or not isinstance(conversion.get('placements'), dict) or not conversion['placements']
            or set(conversion['placements']) - set(PLACEMENTS)
            or not isinstance(conversion.get('profile_link_channels'), list)):
        raise ValueError('intensity.json conversion needs applies_from_urgency 1 to 5, an https subscribe_url, '
                         'placements from ' + ', '.join(PLACEMENTS) + ' and profile_link_channels')
    drafts = (value.get('outreach_drafts') or {}).get('by_urgency') if isinstance(value.get('outreach_drafts'), dict) else None
    if (not isinstance(drafts, dict) or sorted(drafts) != ['1', '2', '3', '4', '5']
            or any(type(v) is not int or not 0 <= v <= OUTREACH_MAX for v in drafts.values())):
        raise ValueError('intensity.json outreach_drafts needs U1 to U5, each 0 to ' + str(OUTREACH_MAX)
                         + ' (one named person each, never bulk: AGENTS.md rule 5)')
    return value


def _directive_urgency(directive):
    body = directive.get('directive', directive) if isinstance(directive, dict) else {}
    north = body.get('north_star') if isinstance(body, dict) else None
    level = north.get('intensity', {}).get('urgency') if isinstance(north, dict) and isinstance(north.get('intensity'), dict) else None
    return level if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 5 else None


def state(root=ROOT, now=None, directive=None):
    """This week's gap: {week_of, week_target, current, as_of, urgency, reason}. Never raises.

    urgency is None only when there is no North Star target for this week (no
    ladder rung, a paused metric or an unreadable file): then nothing is raised."""
    today = ny_time(instant(now)).date()
    week = measure.monday(today)
    out = {'week_of': week.isoformat(), 'week_target': None, 'current': None, 'as_of': None,
           'urgency': None, 'reason': None}
    try:
        metric = measure.north_star(Path(root) / 'docs' / 'NORTH_STAR.md')
        if metric.get('status') == 'paused':
            out['reason'] = 'the North Star is paused'
            return out
        ladder = metric['ladder']
        if isinstance(ladder, list) and ladder and week > ladder[-1][0]:
            target = ladder[-1][1]
        else:
            target = measure.week_target(week, metric)
    except (ValueError, KeyError, TypeError, OSError):
        out['reason'] = 'no North Star target for the week of ' + measure.human_date(week)
        return out
    out['week_target'] = target
    try:
        held = measure.current_state(root)
    except (ValueError, KeyError, TypeError, OSError):
        held = {}
    level, reason = 4, 'not measured this week'
    if held.get('week_of') == week.isoformat() and held.get('current') is not None and held.get('current_as_of'):
        try:
            found = measure.urgency(held['current'], target, held['current_as_of'], today, deadline=metric.get('deadline'))
            level, reason = found['urgency'], found['urgency_reason']
            out.update(current=held['current'], as_of=held['current_as_of'])
            if isinstance(held.get('urgency'), int) and held['urgency'] > level:
                level, reason = held['urgency'], held.get('urgency_reason') or reason
        except (ValueError, TypeError):
            pass
    theirs = _directive_urgency(directive)
    if theirs and theirs > level:
        level, reason = theirs, "Control Center's reading of the North Star"
    out.update(urgency=level, reason=reason)
    return out


def gap_line(gap):
    """'X of Y, U-n, short by Z', the line every report leads with."""
    if gap['urgency'] is None:
        return 'North Star gap: ' + (gap['reason'] or 'not known') + '; volume caps stay at their defaults'
    target = gap['week_target']
    if gap['current'] is None:
        head = 'not measured of {:,}, U{}, short by unknown'.format(target, gap['urgency'])
    else:
        head = '{:,} of {:,}, U{}, short by {:,}'.format(gap['current'], target, gap['urgency'],
                                                          max(0, target - gap['current']))
    why = re.sub(r'^[0-9,]+ of [0-9,]+; ', '', str(gap['reason']))
    return head + ' (new organic subscribers, week of ' + gap['week_of'] + '; ' + why + ')'


def raised(urgency, root=ROOT):
    return urgency is not None and urgency >= bounds(root)['applies_from_urgency']


def daily_cap(record, urgency=None, root=ROOT):
    """Scheduled posts a channel takes per New York day at this urgency; None means no engine cap.

    At U3 and above the cap rises only to that channel's own policy bound
    (engine/social.py: Instagram, YouTube, TikTok and X four, Substack Notes four,
    every other channel one), never to
    the schema's maximum. A null record (a human-only channel) stays null at
    every urgency."""
    cap = record.get('daily_posts_target') if isinstance(record, dict) else None
    if not isinstance(cap, int) or isinstance(cap, bool):
        return None
    if not raised(urgency, root):
        return cap
    bounds(root)
    return max(cap, max_daily_posts(record.get('id')))


def engagement_taps(urgency=None, root=ROOT):
    """How many engagement taps one day's batch may carry at this urgency."""
    return bounds(root)['engagement_taps']['by_urgency'][str(urgency if urgency in (1, 2, 3, 4, 5) else 1)]


def _level(urgency):
    return urgency if urgency in (1, 2, 3, 4, 5) else None


def outreach_drafts(urgency=None, root=ROOT):
    """New one-person outreach drafts Acquisition prepares a day at this urgency (0 when unknown)."""
    level = _level(urgency)
    return bounds(root)['outreach_drafts']['by_urgency'][str(level)] if level else 0


def subscribe_required(urgency=None, root=ROOT):
    """Whether every post must carry a subscribe route at this urgency (Ruling, Krish, 2026-11-11)."""
    level = _level(urgency)
    return level is not None and level >= bounds(root)['conversion']['applies_from_urgency']


URL_IN_TEXT = re.compile(r'https?://[^\s<>"]+')


def subscribe_errors(cta, channel, words, link_placement=None, urgency=None, root=ROOT):
    """Why a post has no usable subscribe route, or []. Nothing is required below the conversion urgency.

    cta is {"url", "placement"}: the subscribe page with its source tags, and in_post (the URL is in the
    words), first_reply (link_placement first_reply) or profile_link (only on a channel whose posts carry no
    clickable link, and the words point to the profile). A subscribe route is a destination, never a share
    ask, and it sits beside the ecosystem route, never in place of it."""
    if not subscribe_required(urgency, root):
        return []
    conversion = bounds(root)['conversion']
    if not isinstance(cta, dict):
        return ['no subscribe route at U' + str(urgency) + ': name subscribe_cta {url, placement} '
                '(intensity.json conversion)']
    url, placement = cta.get('url'), cta.get('placement')
    if not isinstance(url, str) or not http_url(url) or not url.startswith('https://'):
        return ['the subscribe route needs an https URL']
    page, parts = urlsplit(conversion['subscribe_url']), urlsplit(url)
    if (parts.hostname or '').lower() != page.hostname or parts.path.rstrip('/') != page.path.rstrip('/'):
        return [url + ' is not the subscribe page ' + conversion['subscribe_url']]
    query = parse_qs(parts.query)
    # The profile links are the exact URLs Krish approved (jobs/channel-audit.md: source, medium and content);
    # a link in a post or a reply carries all four tags GA4 credits a post by.
    needed = PROFILE_TAGS if placement == 'profile_link' else SOURCE_TAGS
    missing = [t for t in needed if not (query.get(t) or [''])[0].strip()]
    if missing:
        return ['the subscribe URL needs its source tags (' + ', '.join(missing) + ') so Measurement can credit it']
    if placement not in conversion['placements']:
        return ['unknown subscribe placement ' + str(placement) + '; one of ' + ', '.join(conversion['placements'])]
    if placement == 'in_post':
        found = {u.rstrip('.,;:!?)') for u in URL_IN_TEXT.findall(words or '')}
        if url not in found:
            return ['an in_post subscribe route must have its URL in the words']
    if placement == 'first_reply' and link_placement != 'first_reply':
        return ['a first_reply subscribe route needs link_placement first_reply']
    if placement == 'profile_link':
        if channel not in conversion['profile_link_channels']:
            return [str(channel) + ' can carry the link itself; profile_link is only for '
                    + ', '.join(conversion['profile_link_channels'])]
        if not re.search(r'\b(?:link in (?:my |the )?(?:bio|profile)|profile link|subscribe)\b', words or '', re.I):
            return ['a profile_link subscribe route needs the words to point to the profile link']
    return []
