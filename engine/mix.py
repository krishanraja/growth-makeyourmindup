"""The weekly mix: past pieces as carousels, interleaved with memes, positive news and level-up posts.

Ruling (Krish, 2026-10-29): "For Make Your Mind Up I think the engine needs to
strategize how to repurpose all the previous posts into carousels and
intertwine them with the memes, positive news pieces, and the other filler
pieces that we decided on." Three or four posts a day on Instagram, YouTube,
TikTok and X, and Krish approves each idea and its mock once.

Deterministic and offline. From the backlog inventory (engine/backlog.py,
oldest unamplified first), the lanes in mix.json and this week's ideas, it
lays out every day of the week on each of the four channels: the channel's
daily target (four, three beside the series piece on Monday, Wednesday and
Friday), never under its floor of three, split across the lanes by their
weights with largest remainders and interleaved by smooth weighted round
robin. A piece or idea runs at most once per channel in a week. Each slot
names its concept; the concepts Krish has to approve, idea and mock, go to
him as one plan proposal behind strategy whose exact payload is the mix and
every concept_sha256, so one press approves them all (engine/concepts.py).

Learning: `mix learn` reads the What-Works verdicts the week's posts earned
(verdict/<slot>.json under the run folder, engine/run/measure.py) and joins
each to its concept and lane; `mix plan --learn` moves a lane's weight one
step inside its bounds (mix.json, learning). Nothing is invented: a lane
with too few judged posts keeps its weight.

Nothing here posts, schedules, sends or writes outside where --out points.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from . import concepts as concept_rules
from . import intensity
from .control_center import proposal
from .core import TIMEZONE, calendar_date, http_url, ny_time, read_json, write_json
from .social import inventory as social_inventory, max_daily_posts

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'mix.json'
SLUG = 'makeyourmindup'
DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
VERDICTS = ('works', 'neutral', 'fails', 'insufficient')
CHANNEL_NAMES = {'instagram': 'Instagram', 'youtube': 'YouTube Shorts', 'tiktok': 'TikTok', 'x': 'X'}
LANE_NAMES = {'repurposed_carousel': 'repurposed carousels', 'meme': 'memes', 'positive_news': 'positive news',
              'level_up': 'level-up advice'}


# Configuration --------------------------------------------------------------

def load(root=ROOT):
    """mix.json, checked against the social records: every lane placement a format its channel takes."""
    path = Path(root) / CONFIG
    cfg = read_json(path if path.is_file() else ROOT / CONFIG)
    channels = cfg['channels']
    if sorted(channels) != sorted(concept_rules.CONCEPT_CHANNELS):
        raise ValueError('mix.json channels are the concept channels: ' + ', '.join(concept_rules.CONCEPT_CHANNELS))
    times = cfg['slot_times']
    for t in times:
        dt.time.fromisoformat(t)
    if len(set(times)) != len(times):
        raise ValueError('mix.json slot_times repeat')
    if cfg['reserved']['time'] not in times:
        raise ValueError('mix.json reserved time must be one of slot_times')
    if any(day not in DAYS or not isinstance(n, int) or n < 0 for day, n in cfg['reserved']['days'].items()):
        raise ValueError('mix.json reserved days are weekday names with whole numbers')
    try:
        records = social_inventory(Path(root))['channel']
    except (ValueError, OSError):
        records = social_inventory(ROOT)['channel']
    sources = 0
    for name, lane in cfg['lanes'].items():
        w, lo, hi = lane['weight'], lane['min'], lane['max']
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (w, lo, hi)) or not 0 <= lo <= w <= hi:
            raise ValueError('lane ' + name + ': weight must be a whole number inside its min and max')
        if lane['source'] not in ('backlog', 'ideas'):
            raise ValueError('lane ' + name + ': source is backlog or ideas')
        sources += lane['source'] == 'backlog'
        if sorted(lane['placements']) != sorted(channels):
            raise ValueError('lane ' + name + ' needs one placement on each mix channel')
        for channel, fmt in lane['placements'].items():
            if fmt not in records[channel]['formats']:
                raise ValueError('lane ' + name + ': ' + fmt + ' is not a format of ' + channel)
    if sources != 1:
        raise ValueError('exactly one lane repurposes the backlog')
    learn = cfg['learning']
    if not (isinstance(learn['min_judged'], int) and learn['min_judged'] >= 1 and 0 < learn['band'] <= 1
            and isinstance(learn['step'], int) and learn['step'] >= 1):
        raise ValueError('mix.json learning needs min_judged, band and step')
    return cfg


def lanes(root=ROOT):
    return load(root)['lanes']


def targets(root=ROOT, urgency=None):
    """{channel: (daily target, floor)} from the social records, at this urgency's caps."""
    records = social_inventory(Path(root))['channel']
    out = {}
    for channel in load(root)['channels']:
        record = records[channel]
        cap = intensity.daily_cap(record, urgency, root)
        floor = record.get('daily_posts_floor') or cap
        if cap is None or floor is None or floor > cap:
            raise ValueError(channel + ' needs a daily target and a floor no higher than it')
        out[channel] = (cap, floor)
    return out


# Layout ---------------------------------------------------------------------

def week_days(week_of):
    day = calendar_date(week_of)
    if day.weekday() != 0:
        raise ValueError('a mix week starts on a Monday')
    return [day + dt.timedelta(days=i) for i in range(7)]


def due_at(day, hhmm):
    """New York wall time on that day, with its own offset (DST changes at 02:00, before any slot)."""
    offset = ny_time(dt.datetime(day.year, day.month, day.day, 12, tzinfo=dt.timezone.utc)).utcoffset()
    clock = dt.time.fromisoformat(hhmm)
    return dt.datetime.combine(day, clock, tzinfo=dt.timezone(offset)).isoformat()


def day_times(day, cfg, target, floor):
    """The slot times the mix fills on one channel and day: its target less the series slot, never under the floor."""
    reserved = cfg['reserved']['days'].get(DAYS[day.weekday()], 0)
    count = min(len(cfg['slot_times']), max(floor, target - reserved))
    times = [t for t in cfg['slot_times'] if not (reserved and t == cfg['reserved']['time'])]
    if count > len(times):
        times = list(cfg['slot_times'])
    return times[:count]


def weights(cfg, learned=None):
    """Each lane's weight, moved one step by last week's verdicts where enough were judged."""
    out, moved = {}, {}
    rule = cfg['learning']
    tallies = (learned or {}).get('lanes') or {}
    for name, lane in cfg['lanes'].items():
        w = lane['weight']
        row = tallies.get(name) or {}
        judged = sum(int(row.get(v) or 0) for v in ('works', 'neutral', 'fails'))
        if judged >= rule['min_judged']:
            score = (int(row.get('works') or 0) - int(row.get('fails') or 0)) / judged
            step = rule['step'] if score >= rule['band'] else -rule['step'] if score <= -rule['band'] else 0
            new = min(lane['max'], max(lane['min'], w + step))
            if new != w:
                moved[name] = {'from': w, 'to': new, 'judged': judged, 'score': round(score, 2)}
            w = new
        out[name] = w
    return out, moved


def quotas(total, lane_weights):
    """Largest remainder: whole slots per lane for this many, in lane order on a tie."""
    names = list(lane_weights)
    whole = sum(lane_weights.values())
    if total <= 0 or whole <= 0:
        return {n: 0 for n in names}
    exact = {n: total * lane_weights[n] / whole for n in names}
    out = {n: int(exact[n]) for n in names}
    rest = sorted(names, key=lambda n: (-(exact[n] - out[n]), names.index(n)))
    for n in rest[:total - sum(out.values())]:
        out[n] += 1
    return out


def interleave(counts):
    """Smooth weighted round robin: each lane spread evenly through the week, deterministic."""
    names = [n for n in counts if counts[n] > 0]
    total = sum(counts[n] for n in names)
    current = {n: 0 for n in names}
    order = []
    for _ in range(total):
        for n in names:
            current[n] += counts[n]
        best = max(names, key=lambda n: (current[n], -names.index(n)))
        current[best] -= total
        order.append(best)
    return order


# Concepts -------------------------------------------------------------------

def _slug(text):
    out = ''.join(c if c.isalnum() else '-' for c in str(text).lower()).strip('-')
    while '--' in out:
        out = out.replace('--', '-')
    return out[:48].strip('-')


def backlog_pool(inventory, lane_name, lane):
    """Past pieces as carousel concepts, in the inventory's order: oldest unamplified first, then partial."""
    pool = []
    for piece in inventory.get('pieces') or []:
        if piece.get('status') == 'covered':
            continue
        open_pairs = {(f['channel'], f['format']) for f in piece.get('formats_open') or []}
        channels = [c for c, fmt in lane['placements'].items() if (c, fmt) in open_pairs]
        if not channels:
            continue
        pool.append({'concept_id': 'carousel-' + piece['piece_id'][len('piece_'):], 'lane': lane_name,
                     'idea': 'A carousel of "' + piece['title'] + '" (published ' + piece['published_at'][:10] + ')',
                     'claim': None, 'source_url': piece['url'], 'piece_id': piece['piece_id'],
                     'open': set(channels)})
    return pool


def idea_pool(ideas, lane_name, lane, week):
    """This week's ideas for one filler lane, and the ones refused with why."""
    pool, refused = [], []
    for item in ideas:
        if item.get('lane') != lane_name:
            continue
        iid = _slug(item.get('idea_id') or '')
        why = None
        if not iid:
            why = 'needs an idea_id'
        elif not isinstance(item.get('idea'), str) or not item['idea'].strip():
            why = 'needs the idea in words'
        elif item.get('source_url') is not None and not (http_url(item['source_url'])
                                                          and item['source_url'].startswith('https://')):
            why = 'source_url must be https'
        elif lane.get('needs_source'):
            if not item.get('source_url') or not item.get('source_date'):
                why = 'positive news names its primary source and its date'
            else:
                try:
                    dated = calendar_date(item['source_date'])
                    if not week[0] - dt.timedelta(days=lane['fresh_days']) <= dated <= week[-1]:
                        why = 'the source is not dated within ' + str(lane['fresh_days']) + ' days of the week'
                except ValueError:
                    why = 'source_date must be YYYY-MM-DD'
        if why:
            refused.append({'idea_id': item.get('idea_id'), 'lane': lane_name, 'why': why})
            continue
        pool.append({'concept_id': _slug(lane_name.replace('_', '-') + '-' + iid), 'lane': lane_name,
                     'idea': item['idea'].strip(), 'claim': item.get('claim'), 'source_url': item.get('source_url'),
                     'piece_id': None, 'open': set(lane['placements'])})
    return pool, refused


def ready(concept):
    """A concept Krish can approve: a claim, and mock files for every placement that carries media."""
    return bool(concept['claim']) and (bool(concept['mock_sha256']) or concept['text_only'])


# The plan -------------------------------------------------------------------

def plan(inventory, week_of, ideas=(), mocks=None, learned=None, root=ROOT, urgency=None):
    """The week's mix, its concepts and the one plan proposal for Krish."""
    cfg = load(root)
    week = week_days(week_of)
    caps = targets(root, urgency)
    lane_weights, moved = weights(cfg, learned)
    formats = social_inventory(Path(root))['format']
    pools, refused = {}, []
    for name, lane in cfg['lanes'].items():
        if lane['source'] == 'backlog':
            pools[name] = backlog_pool(inventory, name, lane)
        else:
            pools[name], bad = idea_pool(list(ideas or ()), name, lane, week)
            refused += bad
    slots, shortfalls, used = [], [], {}
    for channel in cfg['channels']:
        target, floor = caps[channel]
        times = [(day, t) for day in week for t in day_times(day, cfg, target, floor)]
        order = interleave(quotas(len(times), lane_weights))
        seen = set()
        for (day, t), lane_name in zip(times, order):
            fmt = cfg['lanes'][lane_name]['placements'][channel]
            pick = next((c for c in pools[lane_name] if channel in c['open'] and c['concept_id'] not in seen), None)
            slot = {'slot_id': (channel + '-' + day.isoformat() + '-' + t.replace(':', '')),
                    'channel': channel, 'format': fmt, 'lane': lane_name, 'day': DAYS[day.weekday()],
                    'due_at': due_at(day, t), 'concept_id': pick['concept_id'] if pick else None}
            slots.append(slot)
            if pick is None:
                shortfalls.append({'channel': channel, 'day': day.isoformat(), 'lane': lane_name,
                                   'needs': 'a past piece with this format open' if cfg['lanes'][lane_name]['source']
                                   == 'backlog' else 'an idea for this lane'})
                continue
            seen.add(pick['concept_id'])
            used.setdefault(pick['concept_id'], (pick, []))[1].append({'channel': channel, 'format': fmt})
    mocks = mocks or {}
    concepts = []
    for cid, (pick, placements) in sorted(used.items(), key=lambda kv: (list(cfg['lanes']).index(kv[1][0]['lane']),
                                                                         kv[0])):
        given = mocks.get(cid) or {}
        concept = {'concept_id': cid, 'lane': pick['lane'], 'idea': pick['idea'],
                   'claim': given.get('claim') or pick['claim'], 'source_url': pick['source_url'],
                   'piece_id': pick['piece_id'], 'mock_sha256': list(given.get('mock_sha256') or []),
                   'placements': placements}
        concept['text_only'] = all(formats[p['format']]['min_assets'] == 0 for p in placements)
        concept['ready'] = ready(concept)
        concept['concept_sha256'] = concept_rules.concept_sha256(concept) if concept['ready'] else None
        concepts.append(concept)
    summary = {c: {} for c in cfg['channels']}
    for slot in slots:
        summary[slot['channel']][slot['lane']] = summary[slot['channel']].get(slot['lane'], 0) + 1
    mix = {'schema': 'growth-mix/1', 'week_of': week[0].isoformat(), 'tz': TIMEZONE,
           'targets': {c: {'target': caps[c][0], 'floor': caps[c][1]} for c in cfg['channels']},
           'weights': lane_weights, 'moved': moved, 'per_channel': summary, 'slots': slots,
           'concepts': concepts, 'shortfalls': shortfalls, 'refused_ideas': refused,
           'local_only': True, 'external_writes': 0}
    mix['proposal'], mix['proposal_hold'] = None, None
    try:
        mix['proposal'] = plan_proposal(mix, cfg)
    except ValueError as exc:
        mix['proposal_hold'] = str(exc)
    return mix


def proposal_id(week_of):
    year, week = calendar_date(week_of).isocalendar()[:2]
    return SLUG + ':mix:%d-W%02d' % (year, week)


def week_part(pid, week_of):
    """True when pid is any part of the week's plan, in any version: the plan id itself or it with :p<n>.

    His no on any of them stops the week for good, whatever later versions carry (R111)."""
    base = proposal_id(week_of)
    return isinstance(pid, str) and (pid == base or (pid.startswith(base + ':p') and pid[len(base) + 2:].isdigit()))


def _channels(names):
    names = list(names)
    if sorted(names) == sorted(CHANNEL_NAMES):
        return 'all four channels'
    return ', '.join(CHANNEL_NAMES[c] for c in names)


def concept_line(c):
    """One concept's line in the plan Krish reads; his yes binds exactly this line, his edit of it stops it."""
    head = '- ' + c['concept_id'] + ' (' + LANE_NAMES.get(c['lane'], c['lane']) + '): ' + c['idea']
    if not c['ready']:
        return head + '. Not ready, so not approved: ' + ('needs its claim and mock' if not c['claim'] else 'needs its mock')
    files = len(c['mock_sha256'])
    return (head + '. Claim: "' + c['claim'] + '" On ' + _channels(p['channel'] for p in c['placements'])
            + ', ' + (str(files) + ' mock file' + ('' if files == 1 else 's') if files else 'text only, no files')
            + '. Hash ' + c['concept_sha256'])


def _days(days):
    return ', '.join(d[:3] for d in days)


def ceiling(mix, channel):
    """The most posts a day release can allow on a channel this week: its planned target, or its policy
    bound if urgency rises (engine/intensity.py daily_cap never goes above either)."""
    return max(mix['targets'][channel]['target'], max_daily_posts(channel))


def _caps_line(mix, channels):
    return ', '.join(CHANNEL_NAMES[c] + ' ' + str(ceiling(mix, c)) for c in channels)


def _sections(mix, cfg):
    """(head, concept lines, tail) of the plan text Krish reads: the plan lines, one line per concept, the walls."""
    channels = cfg['channels']
    ready = {c['concept_id'] for c in mix['concepts'] if c['ready']}
    waiting = {c['concept_id'] for c in mix['concepts'] if not c['ready']}
    per_day = {}
    for slot in mix['slots']:
        row = per_day.setdefault(slot['channel'], {})
        row[slot['day']] = row.get(slot['day'], 0) + 1
    shapes = {}
    for channel in channels:
        counts = {}
        for day in DAYS:
            counts.setdefault(per_day.get(channel, {}).get(day, 0), []).append(day)
        shape = '; '.join(str(n) + ' on ' + _days(ds) for n, ds in sorted(counts.items(), reverse=True))
        shapes.setdefault(shape, []).append(channel)
    reserved = sorted({d for d, n in cfg['reserved']['days'].items() if n}, key=DAYS.index)
    lines = ['Mix for the week of ' + mix['week_of'] + ' (New York) on '
             + ', '.join(CHANNEL_NAMES[c] for c in channels) + '.']
    for shape, names in shapes.items():
        lines.append('Planned slots a day on ' + _channels(names) + ': ' + shape
                     + (' (the piece\'s own post on ' + _days(reserved) + ' is signed separately)' if reserved else '')
                     + '.')
    lines.append('Ratio (weights): ' + ', '.join(LANE_NAMES.get(n, n) + ' ' + str(w) for n, w in mix['weights'].items()) + '.')
    formats = {}
    for n, lane in cfg['lanes'].items():
        formats.setdefault(', '.join(CHANNEL_NAMES[c] + ' ' + lane['placements'][c] for c in channels), []).append(
            LANE_NAMES.get(n, n))
    lines.append('Formats: ' + '; '.join(' and '.join(names) + ' as ' + where for where, names in formats.items()) + '.')
    if mix['moved']:
        lines.append('Learned from last week: ' + '; '.join(
            LANE_NAMES.get(n, n) + ' ' + str(m['from']) + ' to ' + str(m['to']) + ' on ' + str(m['judged']) + ' judged posts'
            for n, m in mix['moved'].items()) + '.')
    for channel in channels:
        rows = [s for s in mix['slots'] if s['channel'] == channel]
        lanes_row = {}
        for s in rows:
            lanes_row[s['lane']] = lanes_row.get(s['lane'], 0) + 1
        filled = sum(1 for s in rows if s['concept_id'] in ready)
        wait = sum(1 for s in rows if s['concept_id'] in waiting)
        lines.append(CHANNEL_NAMES[channel] + ': ' + str(len(rows)) + ' slots, ' + ', '.join(
            str(lanes_row.get(n, 0)) + ' ' + LANE_NAMES.get(n, n) for n in cfg['lanes']) + '; ' + str(filled)
            + ' with a ready concept, ' + str(wait) + ' waiting for a mock, ' + str(len(rows) - filled - wait) + ' empty.')
    order = {}
    for slot in mix['slots']:
        if slot['channel'] == channels[0]:
            order.setdefault(slot['day'], []).append(LANE_NAMES.get(slot['lane'], slot['lane']).split()[-1])
    lines.append('Day by day on ' + CHANNEL_NAMES[channels[0]] + ': '
                 + '; '.join(d[:3] + ' ' + ', '.join(v) for d, v in order.items()) + '.')
    lines.append('')
    lines.append(_terms(mix, channels))
    tail = []
    if mix['shortfalls']:
        tail.append('Empty slots: ' + str(len(mix['shortfalls'])) + ' (missing ideas or open past pieces), never filled'
                    ' with unapproved creative.')
    tail.append(WALLS_LINE)
    return lines, [(c, concept_line(c)) for c in mix['concepts']], tail


WALLS_LINE = 'Walls: spend 0; no comments, follows or messages.'


def _terms(mix, channels):
    return ('Concepts. Your yes approves each ready concept below at its hash: its idea, its claim, the channels'
            ' named and its mock files. A post made from it may then go out on those channels, once on each a week,'
            ' with no further ask, only in its format above, with only its mock files and its claim word for word. Each post'
            ' still needs a passing review of its own exact words and room under its channel\'s daily cap when it'
            ' goes out (at most ' + _caps_line(mix, channels) + ' a day), and must pass copy lint, the share rule, the channel lock and, on a route not yet'
            ' verified, the one capability check; a post that fails any of these is held, never posted. Delete'
            ' or change a concept\'s line and that concept and every post from it stop. Change or add any other'
            ' line and no concept is approved until a plan carrying your change is approved. Your no stops them all.'
            ' LinkedIn stays your click.')


def payload_text(mix, cfg):
    """The exact words Krish approves. Every sentence in it is what release does, no more (R101, R103)."""
    head, items, tail = _sections(mix, cfg)
    return '\n'.join(head + [line for _, line in items] + tail)


# A week too long for one approval -------------------------------------------------

PAYLOAD_CAP = 8000  # engine/control_center.py proposal: an exact_payload over it is held, never cut
EVIDENCE_CAP = 12  # the report schema's evidence items a proposal carries: one mock view link per concept


def part_id(week_of, number):
    """Part 1 is the week's plan proposal itself; later parts add :p<n>, so a stop on part 1 stops them all."""
    return proposal_id(week_of) + ('' if number == 1 else ':p' + str(number))


def _part_head(mix, number, parts):
    return ['Part ' + str(number) + ' of ' + str(parts) + ' of the mix for the week of ' + mix['week_of']
            + ' (New York): more concepts under the plan in part 1, on its terms as written there.']


def _part_note(parts):
    return ('This week comes in ' + str(parts) + ' parts, one ask at a time, in order. A concept is approved only'
            ' once part 1 and its own part are; your no on any part stops every concept of the week.')


def payload_parts(mix, cfg, fits=None):
    """[(exact words, concepts)] for each part of the week, in order, each at most PAYLOAD_CAP characters.

    One part when the whole plan fits (then its words are payload_text exactly);
    otherwise part 1 carries every plan line and the concepts that fit, and each
    later part repeats the terms and carries more concept lines, so one press never
    reads past 8,000 characters (docs/MIX.md). fits(concepts) is the caller's own
    bound on a part (the record that carries its concepts, its evidence). Raises
    ValueError when one concept cannot fit a part on its own."""
    fits = fits or (lambda group: True)
    head, items, tail = _sections(mix, cfg)
    whole = '\n'.join(head + [line for _, line in items] + tail)
    concepts = [c for c, _ in items]
    if len(whole) <= PAYLOAD_CAP and fits(concepts):
        return [(whole, concepts)]
    terms = _terms(mix, cfg['channels'])
    # Worst-case numbering, so a part that fits here still fits once numbered.
    first = head + [_part_note(99)]
    later = _part_head(mix, 99, 99) + ['', terms]
    groups, current = [], []
    for concept, line in items:
        frame = first if not groups else later
        ends = tail if not groups else [WALLS_LINE]
        if len('\n'.join(frame + [line] + ends)) > PAYLOAD_CAP or not fits([concept]):
            raise ValueError('concept ' + concept['concept_id'] + ' does not fit a part of its own')
        trial = current + [(concept, line)]
        if current and (len('\n'.join(frame + [x for _, x in trial] + ends)) > PAYLOAD_CAP
                        or not fits([c for c, _ in trial])):
            groups.append(current)
            current = [(concept, line)]
        else:
            current = trial
    groups.append(current)
    parts, total = [], len(groups)
    for number, group in enumerate(groups, 1):
        frame = head + [_part_note(total)] if number == 1 else _part_head(mix, number, total) + ['', terms]
        ends = tail if number == 1 else [WALLS_LINE]
        parts.append(('\n'.join(frame + [line for _, line in group] + ends), [c for c, _ in group]))
    return parts


def plan_proposal(mix, cfg):
    text = payload_text(mix, cfg)
    ready_count = sum(c['ready'] for c in mix['concepts'])
    return proposal(proposal_id(mix['week_of']),
                    'Approve the week of ' + mix['week_of'] + ': ' + str(ready_count) + ' ideas and their mocks',
                    'One press approves the ideas and mocks for the week; posts made exactly from them may then go'
                    ' out on Instagram, YouTube, TikTok and X, each still reviewed, at most '
                    + _caps_line(mix, cfg['channels']) + ' a day.',
                    'advice', 'strategy', 'plan_approved', exact_payload=text, reference='docs/MIX.md',
                    stage='plan')


def part_proposals(mix, cfg, fits=None, links=None):
    """([proposal], [concepts]) for each part of the week in order (payload_parts), each behind strategy at stage plan.

    One part is plan_proposal's own words. links maps concept_id to its mock view
    links (https); a part's evidence carries the first link of each of its concepts,
    at most EVIDENCE_CAP, so he can open every mock he approves from the ask."""
    links = links or {}
    linked = lambda group: sum(1 for c in group if links.get(c['concept_id'])) <= EVIDENCE_CAP
    parts = payload_parts(mix, cfg, lambda group: linked(group) and (fits is None or fits(group)))
    out = []
    for number, (text, group) in enumerate(parts, 1):
        ready_count = sum(1 for c in group if c['ready'])
        suffix = '' if len(parts) == 1 else ' (part ' + str(number) + ' of ' + str(len(parts)) + ')'
        evidence = [{'label': 'Mock for ' + c['concept_id'], 'url': links[c['concept_id']][0]}
                    for c in group if links.get(c['concept_id'])]
        out.append(proposal(part_id(mix['week_of'], number),
                            'Approve the week of ' + mix['week_of'] + ': ' + str(ready_count) + ' ideas and their mocks'
                            + suffix,
                            'One press approves the ideas and mocks for the week; posts made exactly from them may then go'
                            ' out on Instagram, YouTube, TikTok and X, each still reviewed, at most '
                            + _caps_line(mix, cfg['channels']) + ' a day.'
                            + (' This week comes in ' + str(len(parts)) + ' parts, one at a time.' if len(parts) > 1
                               else ''),
                            'advice', 'strategy', 'plan_approved', exact_payload=text, reference='docs/MIX.md',
                            stage='plan', evidence=evidence))
    return out, [group for _, group in parts]


def spec_concepts(mix):
    """The ready concepts as the run spec carries them (run new --mix); the rest wait for their mock."""
    keep = ('concept_id', 'lane', 'idea', 'claim', 'source_url', 'piece_id', 'mock_sha256', 'placements')
    out = []
    for c in mix['concepts']:
        if c.get('ready'):
            item = {k: c[k] for k in keep}
            item['concept_sha256'] = concept_rules.concept_sha256(item)
            out.append(item)
    return out


def _line(text):
    return ' '.join(str(text).split())


def approved_map(mix, approved_text=None):
    """{concept_id: concept_sha256} as decision.json carries it once Krish approves the plan.

    approved_text is the payload he approved, his amended version when he
    changed it: a concept is approved only while its line stands in it exactly
    as the engine wrote it (spaces aside). A line he deleted or changed is not
    approved; amended_out says which.
    """
    out = {c['concept_id']: c['concept_sha256'] for c in spec_concepts(mix)}
    if approved_text is None:
        return out
    kept = {_line(line) for line in str(approved_text).split('\n')}
    lines = {c['concept_id']: _line(concept_line(c)) for c in mix['concepts'] if c.get('ready')}
    return {cid: sha for cid, sha in out.items() if lines.get(cid) in kept}


def amended_out(mix, approved_text):
    """(deleted, changed): ready concepts whose line is gone from his version, and those whose line he edited.

    Both stop: the engine never posts his edited words in place of the mock it
    hashed. changed is told apart by its hash still standing in his text, so the
    next plan can carry his words."""
    kept = {_line(line) for line in str(approved_text).split('\n')}
    text = str(approved_text)
    deleted, changed = [], []
    for c in mix['concepts']:
        if not c.get('ready') or _line(concept_line(c)) in kept:
            continue
        (changed if c['concept_sha256'] in text else deleted).append(c['concept_id'])
    return sorted(deleted), sorted(changed)


def plan_lines_changed(mix, cfg, approved_text):
    """How many of the plan's own lines (not concept lines) his version changed or dropped."""
    return lines_changed(payload_text(mix, cfg), approved_text)


def lines_changed(engine_text, approved_text):
    """How many plan lines his version changed, dropped or added (any part's words).

    The engine's own non-concept lines he changed or dropped count, and so does every
    line he added that is not his edit of a concept's own line (amended_out stops that
    concept): a term he writes in ("nothing on X this week") is his, and the engine
    cannot enforce it, so it holds the week like any other changed term (R112)."""
    kept = {_line(line) for line in str(approved_text).split('\n')}
    engine_lines = [line for line in str(engine_text).split('\n') if line.strip()]
    ours = {_line(line) for line in engine_lines}
    dropped = sum(1 for line in engine_lines if not line.startswith('- ') and _line(line) not in kept)
    concept_ids = {line[2:].split(' (', 1)[0] for line in engine_lines if line.startswith('- ')}
    added = sum(1 for line in str(approved_text).split('\n') if line.strip() and _line(line) not in ours
                and not (line.startswith('- ') and line[2:].split(' (', 1)[0] in concept_ids))
    return max(dropped, added)


# Learning -------------------------------------------------------------------

def learn(specs, runs_dir=None, root=ROOT):
    """Last week's verdicts by lane and by channel, joined through each slot's concept. Local only."""
    from .run.spec import run_dir
    lanes_out, channels_out, rows = {}, {}, []
    for spec in specs:
        known = concept_rules.by_id(spec)
        folder = run_dir(spec, runs_dir, root)
        for slot in spec.get('slots') or []:
            concept = known.get(slot.get('concept_id'))
            if concept is None:
                continue
            path = folder / 'verdict' / (slot['slot_id'] + '.json')
            if not path.is_file():
                continue
            try:
                value = read_json(path).get('verdict')
            except (ValueError, OSError, AttributeError):
                continue
            if value not in VERDICTS:
                continue
            for table, key in ((lanes_out, concept['lane']), (channels_out, slot['channel'])):
                row = table.setdefault(key, {v: 0 for v in VERDICTS})
                row[value] += 1
            rows.append({'slot_id': slot['slot_id'], 'channel': slot['channel'], 'concept_id': concept['concept_id'],
                         'lane': concept['lane'], 'verdict': value})
    return {'schema': 'growth-mix-learn/1', 'lanes': lanes_out, 'channels': channels_out, 'posts': rows,
            'local_only': True}


# Command line ---------------------------------------------------------------

def command(argv, root=ROOT):
    parser = argparse.ArgumentParser(prog='growth.py mix', description='The weekly mix and its learning. Offline.')
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan', help="lay out the week and the one plan proposal of Krish's ideas and mocks")
    p.add_argument('--week-of', required=True, help='the Monday, YYYY-MM-DD')
    p.add_argument('--inventory', default=str(Path('.scratch') / 'backlog' / 'inventory.json'))
    p.add_argument('--ideas', help='JSON list of filler ideas: idea_id, lane, idea, claim, source_url, source_date')
    p.add_argument('--mocks', help='JSON map concept_id to {claim, mock_sha256}')
    p.add_argument('--learn', help='a mix learn file from last week')
    p.add_argument('--urgency', type=int, choices=range(1, 6))
    p.add_argument('--out')
    lp = sub.add_parser('learn', help="last week's verdicts by concept, lane and channel")
    lp.add_argument('specs', nargs='+'); lp.add_argument('--runs-dir'); lp.add_argument('--out')
    args = parser.parse_args(argv)
    if args.action == 'plan':
        mix = plan(read_json(args.inventory), args.week_of, read_json(args.ideas) if args.ideas else (),
                   read_json(args.mocks) if args.mocks else None, read_json(args.learn) if args.learn else None,
                   root, args.urgency if args.urgency else intensity.state(root)['urgency'])
    else:
        mix = learn([read_json(s) for s in args.specs], args.runs_dir, root)
    if args.out:
        write_json(args.out, mix)
        print('written locally to ' + args.out + '; no external write')
    else:
        print(json.dumps(mix, indent=2, ensure_ascii=False))
    return 0
