"""Asks whose week or window is over are taken back by this engine itself.

Ruling (Krish, 2026-11-12): nothing on his list is stale; an engine withdraws
its own asks once their week or window has passed ("not only up to date but
impossible to sprawl over time").

Krish's list in Control Center shows one of this engine's asks at a time
(oneTurnEach: a plan first, then the oldest), so an ask about a week that is
over holds every live ask behind it. Each runner report (engine/cc_loop.py)
takes back, through the protocol's own route (1.10.0 `withdrawn[]`), each of
its own undecided asks whose subject has passed, with a one-line reason.
Control Center marks such an ask expired, keeps the reason beside it
(`done_evidence.kind: withdrawn`) and takes it off his list; one he decided is
left as it is. The asks it takes back:

- a week's mix plan, every part (`makeyourmindup:mix:<week>`, then `:p2`,
  ...), as that week's own version records name them
  (`makeyourmindup:mixplan:<week>:<n>`, engine/run/handoff.py), once the week
  has ended in New York;
- that week's "This week's mix isn't approved" ask
  (`makeyourmindup:mixask:<week>`, engine/run/maker.py), once the week has
  ended;
- the standing plan (specs/standing-plan.json), once the last of its weeks
  has ended;
- an experiment's ask (`makeyourmindup:experiment:<id>`), once its window has
  closed: the `end` day experiments.json gives it has passed.

It never deletes a row, never answers for Krish and never touches an ask that
is still live. What it took back rides forward in a hold (WITHDREW), so the
next runner, which keeps no state, does not take it back again.

Nothing new is asked about a week that is over either: the runner proposes
neither an ended plan nor a closed experiment, the handoff refuses a mix plan
for an ended week (`week_over`), the maker raises no mix ask for one, and a
week's mix plan carries `expires_at` at the end of its week (the mix ask
already did), so Control Center drops it on its own even on a day this engine
does not run.
"""
import datetime as dt
from pathlib import Path

from .control_center import SLUG, ProtocolError
from .core import UTC, calendar_date, instant, ny_time, read_json

WITHDREW = 'Taken back by this engine: its week or window is over'
UNREAD_WEEKS = 'Could not read its own week records, so no week ask was taken back today'
WITHDRAWN = 'withdrawn'
# Control Center takes at most 40 a report (WITHDRAWN_MAX); the rest go on the next run.
WITHDRAWN_MAX = 40
REASON_MAX = 300
# The first week a mix plan was ever asked for (R101, 29 October 2026): no week before it has one to read.
FIRST_MIX_WEEK = dt.date(2026, 11, 2)
# How many ended weeks each run reads back. A week's mix plan also expires at its week's end, so a run
# that misses this window still leaves nothing on his list.
LOOKBACK_WEEKS = 8
MAX_VERSIONS = 24  # engine/run/handoff.py MAX_INDEX_PARTS: plan versions read before a lane holds
PLAN_FILE = Path('specs') / 'standing-plan.json'
EXPERIMENTS_FILE = 'experiments.json'


# Weeks and days, in New York ----------------------------------------------------------------

def _midnight(day):
    from .run.spec import ny_midnight
    return ny_midnight(day).astimezone(UTC)


def week_ends(monday):
    """When the week that starts on monday (a date or YYYY-MM-DD) ends: midnight in New York the Monday after."""
    if isinstance(monday, str):
        monday = calendar_date(monday)
    return _midnight(monday + dt.timedelta(days=7))


def week_over(monday, now):
    return week_ends(monday) <= instant(now)


def week_label(monday):
    year, week = monday.isocalendar()[:2]
    return '%d-W%02d' % (year, week)


def mixask_id(label):
    """The week's "This week's mix isn't approved" ask (engine/run/maker.py raise_ask)."""
    return SLUG + ':mixask:' + label


def window_over(end, now):
    """True once an experiment's window has closed: its end day (YYYY-MM-DD, the last day of the window, in
    New York) is over, or its end time has passed. No end, or one that cannot be read, is never over."""
    if not end or not isinstance(end, str):
        return False
    try:
        if len(end) == 10:
            return _midnight(calendar_date(end) + dt.timedelta(days=1)) <= instant(now)
        return instant(end) <= instant(now)
    except (ValueError, TypeError):
        return False


def standing_over(plan, now):
    """True once the last week of the standing plan has ended."""
    weeks = [w for w in (plan or {}).get('weeks') or [] if isinstance(w, str)]
    return bool(weeks) and week_over(max(weeks), now)


def experiment_over(experiment, now):
    return window_over((experiment or {}).get('end'), now)


def _sunday(monday):
    return (monday + dt.timedelta(days=6)).isoformat()


# What has passed ------------------------------------------------------------------------------

def local_candidates(root, now):
    """[(proposal_id, reason)] for the runner's own standing asks whose subject has passed: the standing plan once
    its last week has ended, and each planned experiment whose window has closed. Reads only committed files."""
    root, out = Path(root), []
    path = root / PLAN_FILE
    if path.exists():
        plan = read_json(path)
        if standing_over(plan, now):
            last = calendar_date(max(plan['weeks']))
            out.append((plan['proposal_id'], 'The standing plan it asks about ended with the week of '
                        + last.isoformat() + ' (' + week_label(last) + '), so it can no longer be approved.'))
    for exp in read_json(root / EXPERIMENTS_FILE)['experiments']:
        if exp.get('status') == 'planned' and experiment_over(exp, now):
            out.append((SLUG + ':experiment:' + exp['experiment_id'],
                        'The ' + exp['experiment_id'] + ' experiment window closed on ' + str(exp['end'])[:10]
                        + ', so there is nothing left to start.'))
    return out


def week_candidates(cc, now, lookback=LOOKBACK_WEEKS):
    """([(proposal_id, reason)], None) for the ended weeks in the lookback: every part any version of a week's mix
    plan named, and the week's mix ask when the maker raised one. ([], code) when its own records cannot be read:
    nothing is taken back on a guess."""
    from .run import cc_records
    local = ny_time(now).date()
    this_monday = local - dt.timedelta(days=local.weekday())
    out = []
    try:
        for back in range(lookback, 0, -1):
            monday = this_monday - dt.timedelta(weeks=back)
            if monday < FIRST_MIX_WEEK or not week_over(monday, now):
                continue
            label = week_label(monday)
            reason = ('Its week, ' + label + ' (' + monday.isoformat() + ' to ' + _sunday(monday)
                      + '), is over, so it can no longer be approved.')
            versions = cc_records.probe(cc, lambda n, label=label: cc_records.version_run_id(label, n),
                                        cc_records.VERSION, MAX_VERSIONS)
            if versions is None:
                return [], 'mix_versions_full'
            part = SLUG + ':mix:' + label
            named = {p['proposal_id'] for v in versions for p in v.get('parts') or []
                     if isinstance(p, dict) and isinstance(p.get('proposal_id'), str)
                     and (p['proposal_id'] == part or p['proposal_id'].startswith(part + ':p'))}
            out += [(pid, reason) for pid in sorted(named, key=_part_order)]
            if cc_records.read_report(cc, mixask_id(label)) is not None:
                out.append((mixask_id(label), reason))
    except ProtocolError as error:
        return [], 'week_records_' + error.code
    except (ValueError, TypeError, KeyError, AttributeError):
        return [], 'week_records_unreadable'
    return out, None


def _part_order(pid):
    tail = pid.rsplit(':p', 1)
    return int(tail[1]) if len(tail) == 2 and tail[1].isdigit() else 1


def withdrawals(candidates, sent, proposed=()):
    """([{proposal_id, reason}], [carried proposal_id]) for one report.

    sent is engine/cc_loop.py already_sent(): {proposal_id: 'pending', a decision, or WITHDRAWN}. A candidate
    Krish decided is left as it is. One this engine already took back (an earlier runner report's WITHDREW hold)
    is carried forward and not taken back again. The rest are taken back now, at most WITHDRAWN_MAX (the rest on
    the next run), and carried forward too. Never one this report also proposes: the protocol refuses both."""
    out, carried, seen = [], [], set(proposed)
    for pid, reason in candidates:
        if pid in seen:
            continue
        seen.add(pid)
        state = sent.get(pid)
        if state == WITHDRAWN:
            carried.append(pid)
        elif state in (None, 'pending') and len(out) < WITHDRAWN_MAX:
            out.append({'proposal_id': pid, 'reason': ' '.join(reason.split())[:REASON_MAX]})
            carried.append(pid)
    return out, carried


def activity_line(withdrawn):
    """One plain line naming what this report took back, by id: never an address, never his words."""
    if not withdrawn:
        return None
    ids = ', '.join(w['proposal_id'] for w in withdrawn)
    head = ('Withdrew ' + str(len(withdrawn)) + ' of its own ask' + ('' if len(withdrawn) == 1 else 's')
            + " whose week or window is over, so none waits on Krish's list; any he had decided stays as it is: ")
    line = head + ids
    return line if len(line) <= 500 else head + str(len(withdrawn)) + ' asks, each named in the report'
