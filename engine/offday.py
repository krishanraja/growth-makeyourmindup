"""The off-day lane's three jobs on top of the week's mix (W2.9).

Krish, 29 October 2026, in the Wave 2 session, choosing between his two
rulings: "Mix wins: every day". The meme, positive news and level-up lanes
(mix.json lanes whose source is ideas) run every day under the flood ruling,
so there is no weekday ban here; the Monday, Wednesday and Friday series slot
stays reserved for the piece's own cut (mix.json reserved) and no day goes
over its channel's cap.

1. The Sunday Off-days section (`growth.py mix offdays`): for each day of the
   week, two or three options from the plan's filler concepts, each with its
   format, its source, its draft copy and its share line, as data for
   content-engine's Sunday board (week_board.py). It never makes a board of
   its own, and a day with fewer than two options says so.
2. The mid-week top-up (`growth.py mix topup`): the next free filler slot for
   one post on a channel, from a fresh Buffer readback of what is already
   scheduled: never the reserved series slot, never a day already at the lower
   of the plan's cap and the live cap, never a slot already taken, and never
   closer than release's 90-minute window.
3. The clock facts Control Center keeps (W2.2): offday_stocked (every filler
   slot of the week has a ready concept by the Sunday before it, 20:00 New
   York) and offday_slots_filled (filler slots filled against available).

4. The week's mix (`proposed_mix`): the formats Growth proposes for each day,
   and the sha256 Krish's one press on the board is bound to (Ruling, Krish,
   2026-10-30: "approve the week's mix once, let Growth fill it"), computed
   exactly as content-engine's week_board.py does.

Deterministic and offline. Nothing here posts, schedules or writes outside
where --out points.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from . import intensity, mix as mix_rules
from .buffer_channels import BUFFER_CHANNEL_ID
from .core import calendar_date, instant, ny_time, read_json, write_json
from .share import share_line
from .social import inventory as social_inventory

ROOT = Path(__file__).resolve().parents[1]
STOCKED_BY = dt.time(20, 0)  # Sunday 20:00 New York, before the week
LEAD = dt.timedelta(minutes=90)  # release schedules a post 5 to 90 minutes before it is due
MIN_OPTIONS, MAX_OPTIONS = 2, 6  # Ruling (Krish, 2026-11-01): up to six options a day, each judged on its own
LIVE = ('scheduled', 'sending', 'sent')
CHANNEL_OF_ID = {cid: channel for channel, cid in BUFFER_CHANNEL_ID.items()}


def filler_lanes(cfg):
    return [name for name, lane in cfg['lanes'].items() if lane['source'] == 'ideas']


def _share(idea):
    """The share line for an idea's share block, or None with why it is missing."""
    block = idea.get('share') if isinstance(idea, dict) else None
    if not isinstance(block, dict):
        return None, 'needs its share block'
    try:
        return share_line(block), None
    except (ValueError, KeyError, TypeError):
        return None, 'its share block is incomplete'


def options(mix, ideas=(), root=ROOT):
    """The Off-days section: {day: [option, ...]} for content-engine's Sunday board."""
    cfg = mix_rules.load(root)
    fillers = filler_lanes(cfg)
    concepts = {c['concept_id']: c for c in mix['concepts']}
    by_idea = {}
    for idea in ideas or ():
        if isinstance(idea, dict) and idea.get('lane') in fillers and idea.get('idea_id'):
            cid = mix_rules._slug(idea['lane'].replace('_', '-') + '-' + mix_rules._slug(idea['idea_id']))
            by_idea[cid] = idea
    days, short = {}, []
    for day in mix_rules.week_days(mix['week_of']):
        name = mix_rules.DAYS[day.weekday()]
        seen, out = [], []
        for slot in sorted(mix['slots'], key=lambda s: (fillers.index(s['lane']) if s['lane'] in fillers else 99,
                                                         s['due_at'], s['channel'])):
            cid = slot['concept_id']
            if slot['day'] != name or slot['lane'] not in fillers or not cid or cid in seen:
                continue
            seen.append(cid)
            concept = concepts[cid]
            line, missing = _share(by_idea.get(cid))
            out.append({'concept_id': cid, 'lane': concept['lane'],
                        'formats': sorted({p['channel'] + ':' + p['format'] for p in concept['placements']}),
                        'source_url': concept['source_url'], 'draft': concept['claim'] or concept['idea'],
                        'share_line': line, 'needs': [n for n in (missing, None if concept['ready']
                                                                    else 'needs its claim and mock') if n],
                        'ready': bool(concept['ready'])})
            if len(out) == MAX_OPTIONS:
                break
        days[day.isoformat()] = out
        if len(out) < MIN_OPTIONS:
            short.append({'day': day.isoformat(), 'options': len(out), 'needs': MIN_OPTIONS - len(out)})
    return {'schema': 'growth-offdays/1', 'week_of': mix['week_of'], 'days': days, 'short': short,
            'local_only': True, 'external_writes': 0}


DAY_KEYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
OFFDAYS_SCHEMA = 'growth-offdays/1'


def option_format(option):
    """The one format line the board shows for an option: its formats joined, or its lane (week_board.py)."""
    fmt = ', '.join(option.get('formats') or []) or option.get('lane')
    fmt = str(fmt or '').strip()
    if not fmt:
        raise ValueError('an off-day option has no format and no lane, so the board cannot show it')
    return fmt


def board_options(offdays_doc, monday):
    """{day key: [option, ...]} as the board keeps them from a growth-offdays/1 file. Pure; raises ValueError.

    Mirrors content-engine scripts/post-pack/week_board.py read_growth_offdays: each date maps to its
    day key of the week, the first six options are kept, and a date with fewer than two is left off."""
    monday = calendar_date(monday)
    if not isinstance(offdays_doc, dict) or offdays_doc.get('schema') != OFFDAYS_SCHEMA \
            or not isinstance(offdays_doc.get('days'), dict):
        raise ValueError('not a ' + OFFDAYS_SCHEMA + ' file')
    if str(offdays_doc.get('week_of')) != monday.isoformat():
        raise ValueError('the off-days file is for another week')
    out = {}
    for day, opts in sorted(offdays_doc['days'].items()):
        try:
            offset = (dt.date.fromisoformat(day) - monday).days
        except (TypeError, ValueError):
            offset = None
        if offset not in range(7):
            raise ValueError('an off-days date is not a day of the week of ' + monday.isoformat())
        opts = [o for o in opts or [] if isinstance(o, dict)][:MAX_OPTIONS]
        if len(opts) >= MIN_OPTIONS:
            out[DAY_KEYS[offset]] = opts
    return out


def proposed_mix(offdays_doc, monday):
    """(days, mix_sha256): the week's mix Growth proposes, exactly as the board computes the hash Krish presses.

    Ruling (Krish, 2026-10-30): "approve the week's mix once, let Growth fill it". Mirrors week_board.py
    week_mix on read_growth_offdays: days[key] is the sorted set of each kept option's format line, a
    recorded option left out, and the hash is sha256 of the compact sorted JSON of days."""
    days = {}
    for key, opts in board_options(offdays_doc, monday).items():
        kinds = sorted({option_format(o) for o in opts if o.get('kind') != 'recorded'})
        if kinds:
            days[key] = kinds
    return days, mix_sha256(days)


def mix_sha256(days):
    return hashlib.sha256(json.dumps(days, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def counts(scheduled):
    """{channel: {New York date: posts}} from a Buffer readback of the pinned channels."""
    if not isinstance(scheduled, list):
        raise ValueError('the scheduled readback is a list of posts')
    out = {}
    for post in scheduled:
        if not isinstance(post, dict) or not isinstance(post.get('id'), str) or post.get('status') not in LIVE + (
                'draft', 'error'):
            raise ValueError('each post needs id, status, channelId and dueAt')
        channel = CHANNEL_OF_ID.get(post.get('channelId'))
        if channel is None or post['status'] not in LIVE or not post.get('dueAt'):
            continue
        day = ny_time(instant(post['dueAt'])).date().isoformat()
        out.setdefault(channel, {})
        out[channel][day] = out[channel].get(day, 0) + 1
    return out


def reserved(slot, cfg):
    return cfg['reserved']['days'].get(slot['day'], 0) and slot['due_at'][11:16] == cfg['reserved']['time']


def day_cap(mix, channel, root=ROOT, urgency=None):
    """The lower of the plan's cap and the live cap (engine/intensity.py), as release enforces."""
    record = social_inventory(Path(root))['channel'][channel]
    live = intensity.daily_cap(record, urgency, root)
    plan = mix_rules.ceiling(mix, channel)
    return min(c for c in (live, plan) if c is not None)


def next_free_slot(mix, channel, scheduled, now, taken=(), root=ROOT, urgency=None):
    """(slot, None) for the next free filler slot on channel, or (None, why)."""
    cfg = mix_rules.load(root)
    if channel not in cfg['channels']:
        return None, 'not_a_mix_channel'
    fillers = filler_lanes(cfg)
    filled = counts(scheduled).get(channel, {})
    cap = day_cap(mix, channel, root, urgency)
    earliest = instant(now) + LEAD
    for slot in sorted(mix['slots'], key=lambda s: s['due_at']):
        if slot['channel'] != channel or slot['lane'] not in fillers or slot['slot_id'] in taken:
            continue
        if reserved(slot, cfg) or instant(slot['due_at']) <= earliest:
            continue
        day = ny_time(instant(slot['due_at'])).date().isoformat()
        if filled.get(day, 0) >= cap:
            continue
        return slot, None
    return None, 'no_free_slot_this_week'


def clock(mix, now, filled_slot_ids=(), root=ROOT):
    """The clock facts Control Center keeps for the off-day lane (W2.2)."""
    cfg = mix_rules.load(root)
    fillers = filler_lanes(cfg)
    ready = {c['concept_id'] for c in mix['concepts'] if c.get('ready')}
    slots = [s for s in mix['slots'] if s['lane'] in fillers]
    stocked = [s for s in slots if s['concept_id'] in ready]
    sunday = calendar_date(mix['week_of']) - dt.timedelta(days=1)
    deadline = dt.datetime.fromisoformat(mix_rules.due_at(sunday, STOCKED_BY.strftime('%H:%M')))
    ids = set(filled_slot_ids)
    return {'offday_stocked': bool(slots) and len(stocked) == len(slots),
            'stocked_slots': len(stocked), 'filler_slots': len(slots), 'stocked_by': deadline.isoformat(),
            'past_deadline': instant(now) > deadline,
            'offday_slots_filled': sum(1 for s in slots if s['slot_id'] in ids), 'offday_slots_available': len(slots)}


def command(argv, root=ROOT):
    parser = argparse.ArgumentParser(prog='growth.py mix', description='The off-day lane on top of the mix. Offline.')
    sub = parser.add_subparsers(dest='action', required=True)
    o = sub.add_parser('offdays', help="the Sunday board's Off-days section: two or three options a day")
    o.add_argument('--plan', required=True, help='a mix plan file (growth.py mix plan --out)')
    o.add_argument('--ideas', help='the same ideas file the plan read, for each idea share block')
    o.add_argument('--out')
    t = sub.add_parser('topup', help='the next free filler slot for one post on a channel')
    t.add_argument('--plan', required=True)
    t.add_argument('--channel', required=True)
    t.add_argument('--scheduled', required=True, help="a fresh Buffer list_posts readback: posts with id, status, "
                                                      'channelId and dueAt')
    t.add_argument('--taken', help='JSON list of slot_ids already given a post')
    t.add_argument('--now')
    t.add_argument('--out')
    c = sub.add_parser('clock', help='offday_stocked and offday_slots_filled for Control Center')
    c.add_argument('--plan', required=True)
    c.add_argument('--filled', help='JSON list of filled slot_ids')
    c.add_argument('--now')
    c.add_argument('--out')
    args = parser.parse_args(argv)
    mix = read_json(args.plan)
    now = args.now or instant().isoformat()
    if args.action == 'offdays':
        value = options(mix, read_json(args.ideas) if args.ideas else (), root)
    elif args.action == 'topup':
        slot, why = next_free_slot(mix, args.channel, read_json(args.scheduled), now,
                                   read_json(args.taken) if args.taken else (), root)
        value = {'schema': 'growth-topup/1', 'slot': slot, 'why': why, 'local_only': True}
    else:
        value = clock(mix, now, read_json(args.filled) if args.filled else (), root)
    if args.out:
        write_json(args.out, value)
        print('written locally to ' + args.out + '; no external write')
    else:
        print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0
