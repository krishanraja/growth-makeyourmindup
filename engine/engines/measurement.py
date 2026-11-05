"""The Measurement & Allocation engine: dated readings, weekly scorecards, funnels and allocation memos.

Review section "What Measurement & Allocation should produce" (docs/reviews/2026-11-05-growth-engine-review.md).
It builds on the Measurement Specialist (crew/attribution-ladder/card.md) and the What-Works Analyst
(crew/what-works/card.md): a missing reading is unavailable with its reason, never zero; direct stays
unattributed; paid never counts toward the North Star; a performance claim waits for its judge window and goes
through engine.operations.experiment_decision with at least 6 observations. A source attribution (Substack >
Notes) never implies an activity attribution (the specific Note, an outreach link): those stay unknown until
evidence names them. Verified operational failures and explicit owner corrections apply at once. Each run
answers one question for Krish. Nothing here posts, sends, schedules, spends or writes to Control Center.
"""
import datetime as dt
import re

from engine.engines import ENGINES
from engine.operations import AVAILABILITY, METRICS, experiment_decision
from engine.run.measure import north_star, week_target

KINDS = ('observation', 'scorecard', 'allocation', 'funnel')
STATES = {'observation': ('recorded',), 'scorecard': ('open',), 'allocation': ('proposed', 'accepted'),
          'funnel': ('recorded',)}
CLOSED_STATES = ('final', 'superseded', 'reversed')
QUESTION = 'Where should the next five hours go, and what evidence would change that decision?'
ACTIONS = ('increase', 'reduce', 'stop', 'continue', 'test')
BASES = ('operational_failure', 'owner_correction', 'standing_rule', 'performance')
SPEND_CASES = ('observed_placement', 'conversion_route', 'costed_bottleneck')
MONEY_KINDS = ('tools', 'production', 'paid_boost')
ATTRIBUTION = ('source', 'activity', 'unknown')
UNKNOWN = 'unknown'
UNAVAILABLE = tuple(a for a in AVAILABILITY if a != 'available') + (UNKNOWN,)
SUBSCRIBER_METRICS = ('new_subscribers',)
MIN_OBSERVATIONS = 6
STALE_DAYS = 7
# Where people drop out, per engine (review "Where people drop out").
STAGES = {'acquisition': ('access', 'acceptance', 'placement', 'observed_exposure', 'visits_or_follows',
                          'subscriptions'),
          'engagement': ('substantive_responses', 'repeat_participants', 'useful_questions'),
          'publishing': ('delivered', 'reader_defects', 'hours_to_repair', 'broken_links')}
# What-Works judge windows, in hours. Subscriber impact is read at 7 days, never earlier.
JUDGE_HOURS = {'note': 24, 'linkedin': 48, 'x': 48, 'threads': 48, 'reel': 72, 'short': 72, 'tiktok': 72,
               'short-video': 72, 'subscriber_impact': 168}
DATE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
SPENDING = re.compile(r'\b(spend\w*|paid|budget|money|costs?)\b', re.IGNORECASE)
CHANGES = ('increase', 'reduce', 'stop')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _day(value):
    try:
        return dt.date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        return None


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


# Attribution --------------------------------------------------------------------------------------------


def attribute(source_rows):
    """Platform source rows to attribution rows, each subscriber counted once.

    A platform shows a subscriber under a parent and its child category (Substack and Substack > Notes): the
    parent's count includes its children. Each subscriber goes to the deepest path that holds it; the post
    and any outreach link stay unknown, because a source attribution never implies an activity attribution.
    """
    paths = {}
    for row in source_rows:
        path = tuple(row.get('path') or ())
        if not path or not all(_text(p) for p in path) or not _count(row.get('count')):
            raise ValueError('a source row needs a path of names and a whole count')
        if path in paths:
            raise ValueError('source path listed twice: ' + ' > '.join(path))
        paths[path] = row['count']
    rows = []
    for path, count in sorted(paths.items()):
        children = sum(c for p, c in paths.items() if len(p) == len(path) + 1 and p[:len(path)] == path)
        if children > count:
            raise ValueError(' > '.join(path) + ' shows fewer than its child categories')
        if count - children:
            rows.append({'class': 'source', 'count': count - children, 'source_path': list(path),
                         'post': UNKNOWN, 'outreach': UNKNOWN})
    return rows


def counted(attribution):
    """Subscribers in attribution rows, paid excluded: paid never counts toward the North Star."""
    return sum(r['count'] for r in attribution if not r.get('paid'))


def _by_path(rows):
    out = {}
    for r in rows:
        if r['class'] in ('source', 'activity') and not r.get('paid'):
            out[tuple(r['source_path'])] = out.get(tuple(r['source_path']), 0) + r['count']
    return out


def _attribution_errors(rows, value, source_rows):
    if not isinstance(rows, list):
        return ['detail.attribution must be a list']
    if not isinstance(source_rows, list):
        return ['detail.source_rows must list the platform rows as shown: [{path, count}]']
    try:
        raw = attribute(source_rows)
    except (ValueError, AttributeError, TypeError) as error:
        return ['detail.source_rows: ' + str(error)]
    errors = []
    for i, r in enumerate(rows):
        where = 'detail.attribution.' + str(i) + ': '
        if not isinstance(r, dict) or r.get('class') not in ATTRIBUTION or not _count(r.get('count')):
            errors.append(where + 'needs class ' + '|'.join(ATTRIBUTION) + ' and a whole count')
            continue
        path = r.get('source_path')
        if r['class'] == 'unknown' and path:
            errors.append(where + 'an unknown row carries no source path')
        if r['class'] in ('source', 'activity') and not (isinstance(path, list) and path and all(map(_text, path))):
            errors.append(where + 'needs its source_path')
        if r['class'] == 'source' and (r.get('post') != UNKNOWN or r.get('outreach') != UNKNOWN):
            errors.append(where + 'a source attribution never implies an activity: post and outreach stay unknown')
        if r['class'] == 'activity' and not (_text(r.get('activity_evidence_ref'))
                                             and (r.get('post') != UNKNOWN or r.get('outreach') != UNKNOWN)):
            errors.append(where + 'an activity attribution names the post or outreach and its evidence ref')
    if not errors and value is not None and sum(r['count'] for r in rows) != value:
        errors.append('detail.attribution must count each subscriber once: rows sum to the value')
    if not errors and _by_path(rows) != _by_path(raw):
        errors.append('detail.attribution must count each subscriber once: it must match attribute(source_rows)')
    return errors


# Freshness, windows and the ladder ----------------------------------------------------------------------


def freshness(observation, now):
    """How old a reading is on a date. Older than 7 days is stale."""
    read = _day(observation['detail'].get('read_at'))
    age = (_day(now) - read).days
    return {'read_at': read.isoformat(), 'age_days': age, 'stale': age > STALE_DAYS}


def comparable(da, db):
    """Two readings (details) are comparable when metric, data source and a known window length all match."""
    if da['metric'] != db['metric'] or da['data_source'] != db['data_source']:
        return False, 'different metric or data source'
    if da.get('window_days') is None or db.get('window_days') is None:
        return False, 'a window length is unknown'
    if da['window_days'] != db['window_days']:
        return False, 'different window lengths'
    return True, 'same metric, data source and window length'


def ladder_target(week_of, metric=None):
    """This week's target from the ladder in docs/NORTH_STAR.md, or None with no row for that week."""
    try:
        return week_target(week_of, metric or north_star())
    except (OSError, ValueError):
        return None


def judge_window_open(fmt, published_on, read_on):
    """True once a read is at or past the What-Works judge window. An earlier read is recorded, not judged."""
    hours = JUDGE_HOURS.get(fmt, JUDGE_HOURS['subscriber_impact'])
    return (_day(read_on) - _day(published_on)).days * 24 >= hours


def performance_decision(experiment, observations, now):
    """The What-Works decision on a performance claim: experiment_decision, never under 6 observations."""
    minimum = experiment.get('minimum_observations')
    if not _count(minimum) or minimum < MIN_OBSERVATIONS:
        raise ValueError('a performance claim needs minimum_observations of at least ' + str(MIN_OBSERVATIONS))
    return experiment_decision(experiment, observations, now)


def scorecard(observation, now, metric=None):
    """The weekly scorecard detail from one subscriber reading: count against the ladder, source, window,
    freshness and attribution. A missing reading is unavailable, never zero."""
    d = observation['detail']
    if d.get('metric') not in SUBSCRIBER_METRICS or not _day(d.get('week_of')):
        raise ValueError('a scorecard is built from a subscriber reading with its week_of')
    target = ladder_target(d['week_of'], metric)
    if target is None:
        raise ValueError('no ladder row for the week of ' + d['week_of'])
    value = None if d.get('value') is None else counted(d.get('attribution') or [])
    classes = {c: sum(r['count'] for r in d.get('attribution') or [] if r['class'] == c) for c in ATTRIBUTION}
    unavailable = {} if value is not None else {d['metric']: d.get('unavailable_reason') or UNKNOWN}
    return {'week_of': d['week_of'], 'week_target': target, 'organic_subscribers': value,
            'observation': observation['id'], 'data_source': d['data_source'],
            'window': {k: d.get(k) for k in ('window_start', 'window_end', 'window_days')},
            'freshness': freshness(observation, now), 'attribution': classes,
            'activity_attribution': {'post': UNKNOWN if not classes['activity'] else 'see observation',
                                     'outreach': UNKNOWN if not classes['activity'] else 'see observation'},
            'unavailable': unavailable, 'paid_counted': False}


# Allocation ---------------------------------------------------------------------------------------------


def _recommendation_errors(i, rec, memo_day, evidence_ok):
    where = 'recommendation ' + str(i) + ': '
    if not isinstance(rec, dict):
        return [where + 'must be an object']
    errors = []
    if rec.get('action') not in ACTIONS:
        errors.append(where + 'action must be one of ' + ', '.join(ACTIONS))
    for name in ('what', 'from', 'to', 'duration', 'uncertainty', 'reversal_condition'):
        if not _text(rec.get(name)):
            errors.append(where + name + ' is required')
    hours, cost = rec.get('hours'), rec.get('cost')
    if 'hours' not in rec and 'cost' not in rec:
        errors.append(where + 'hours or cost is required')
    elif not all(v is None or _number(v) for v in (hours, cost)):
        errors.append(where + 'hours and cost are non-negative numbers or null')
    elif hours is None and cost is None and not _text(rec.get('sizing')):
        errors.append(where + 'unsized hours and cost need a sizing note saying who sizes them')
    evidence = rec.get('evidence')
    if not isinstance(evidence, list) or not evidence or not all(_text(e) for e in evidence):
        errors.append(where + 'evidence must list record ids')
    elif not evidence_ok(evidence):
        errors.append(where + 'evidence must be among the record links')
    if rec.get('owner') not in ENGINES + ('krish',):
        errors.append(where + 'owner must be an engine or krish')
    review = _day(rec.get('review_date'))
    if review is None or (memo_day and review < memo_day):
        errors.append(where + 'review_date must be YYYY-MM-DD, not before the memo')
    if rec.get('basis') not in BASES:
        errors.append(where + 'basis must be one of ' + ', '.join(BASES))
    if rec.get('basis') == 'standing_rule' and rec.get('action') != 'continue':
        errors.append(where + 'a standing rule only continues; a change needs its owner correction, operational '
                      'failure or performance decision')
    if rec.get('basis') == 'performance' and rec.get('action') in CHANGES \
            and not (_text(rec.get('experiment')) and evidence_ok([rec['experiment']])):
        errors.append(where + 'a performance claim needs its judge window and at least ' + str(MIN_OBSERVATIONS)
                      + ' observations through experiment_decision on a linked experiment; test or continue '
                        'until then')
    if spends(rec) and rec.get('spend_case') not in SPEND_CASES:
        errors.append(where + 'a spend increase is refused without an observed placement, a conversion route '
                      'or a costed bottleneck (spend_case) in its evidence')
    return errors


def spends(rec):
    """True when a recommendation increases or tests spending: a cost, or spending named in what, from or to."""
    if rec.get('action') not in ('increase', 'test'):
        return False
    cost = rec.get('cost')
    named = any(SPENDING.search(str(rec.get(k) or '')) for k in ('what', 'from', 'to'))
    return (_number(cost) and cost > 0) or named


def _money_errors(money, evidence_ok):
    if not isinstance(money, dict) or not isinstance(money.get('proposed'), list) \
            or not isinstance(money.get('approved'), list):
        return ['money must hold proposed and approved lists, kept apart']
    errors = []
    for side in ('proposed', 'approved'):
        for i, item in enumerate(money[side]):
            where = 'money.' + side + '.' + str(i) + ': '
            if not isinstance(item, dict) or item.get('category') not in MONEY_KINDS \
                    or not _text(item.get('what')) or not _number(item.get('amount')):
                errors.append(where + 'needs category ' + '|'.join(MONEY_KINDS) + ', what and amount')
                continue
            if item['category'] == 'paid_boost' and item.get('counts_toward_north_star') is not False:
                errors.append(where + 'a paid boost stays outside the organic target: counts_toward_north_star false')
            if side == 'approved' and (item.get('approved_by') != 'krish' or not _day(item.get('approved_at'))):
                errors.append(where + 'approved spending names approved_by krish and approved_at')
            if side == 'proposed' and (item.get('spend_case') not in SPEND_CASES
                                       or not isinstance(item.get('evidence'), list) or not item['evidence']
                                       or not evidence_ok(item['evidence'])):
                errors.append(where + 'proposed spending names its spend_case and evidence among the record links')
    whats = [i.get('what') for i in money['proposed'] if isinstance(i, dict)]
    if any(isinstance(i, dict) and i.get('what') in whats for i in money['approved']):
        errors.append('money: one item is either proposed or approved, never both')
    return errors


def allocation_errors(memo, links=None, memo_day=None):
    """Why an allocation memo cannot stand. It answers the weekly question; each recommendation names action,
    what moves, from, to, hours or cost, duration, evidence, uncertainty, owner, review date and reversal."""
    if not isinstance(memo, dict):
        return ['memo must be an object']
    errors = []
    if memo.get('question') != QUESTION:
        errors.append('question must be: ' + QUESTION)
    if not _text(memo.get('answer')):
        errors.append('answer is required')
    recs = memo.get('recommendations')
    if not isinstance(recs, list) or not recs:
        errors.append('recommendations must list at least one')
        recs = []
    evidence_ok = (lambda ids: True) if links is None else (lambda ids: set(ids) <= set(links))
    for i, rec in enumerate(recs):
        errors += _recommendation_errors(i, rec, memo_day, evidence_ok)
    return errors + _money_errors(memo.get('money'), evidence_ok)


# Detail rules -------------------------------------------------------------------------------------------


def _observation_errors(d):
    errors = []
    for name in ('metric', 'unit', 'data_source'):
        if not _text(d.get(name)):
            errors.append('detail.' + name + ' is required')
    if d.get('metric') in METRICS and d.get('unit') != METRICS[d['metric']][0]:
        errors.append('detail.unit for ' + d['metric'] + ' is ' + METRICS[d['metric']][0])
    if not _day(d.get('read_at')):
        errors.append('detail.read_at must be YYYY-MM-DD')
    for name in ('window_start', 'window_end'):
        if d.get(name) is not None and not _day(d[name]):
            errors.append('detail.' + name + ' must be YYYY-MM-DD or null when unknown')
    if d.get('window_days') is not None and not (_count(d['window_days']) and d['window_days'] > 0):
        errors.append('detail.window_days must be a positive whole number or null when unknown')
    value = d.get('value')
    if value is None:
        if d.get('unavailable_reason') not in UNAVAILABLE:
            errors.append('an unavailable reading names unavailable_reason: ' + ', '.join(UNAVAILABLE))
    elif not _count(value):
        errors.append('detail.value must be a whole number, or null when unavailable (never zero for missing)')
    prev = d.get('previous')
    if prev is not None and (not isinstance(prev, dict) or not _day(prev.get('read_at'))
                             or prev.get('metric') != d.get('metric') or not _text(prev.get('data_source'))
                             or (_day(d.get('read_at')) and _day(prev['read_at']) >= _day(d['read_at']))):
        errors.append('detail.previous is the earlier reading of the same metric, with read_at and data_source')
    if d.get('metric') in SUBSCRIBER_METRICS:
        week = _day(d.get('week_of'))
        if week is None or week.weekday() != 0:
            errors.append('a subscriber reading names the Monday of its week_of')
        errors += _attribution_errors(d.get('attribution'), value, d.get('source_rows'))
    return errors


def _funnel_errors(d):
    stages = STAGES.get(d.get('engine_measured'))
    if stages is None:
        return ['detail.engine_measured must be one of ' + ', '.join(STAGES)]
    counts = d.get('stages')
    if not isinstance(counts, dict) or set(counts) != set(stages):
        return ['detail.stages must hold exactly ' + ', '.join(stages)]
    errors = []
    unavailable = d.get('unavailable') if isinstance(d.get('unavailable'), dict) else {}
    for stage in stages:
        if counts[stage] is None and unavailable.get(stage) not in UNAVAILABLE:
            errors.append('stage ' + stage + ' is null: name its reason in detail.unavailable, never zero')
        elif counts[stage] is not None and not _count(counts[stage]):
            errors.append('stage ' + stage + ' must be a whole number or null')
    for loss in d.get('losses') or []:
        if not isinstance(loss, dict) or loss.get('at') not in stages or not _count(loss.get('count')) \
                or not _text(loss.get('reason')):
            errors.append('each loss names at (a stage), count and reason')
    return errors


def validate_detail(record):
    kind, d = record['kind'], record['detail']
    if kind == 'observation':
        return _observation_errors(d)
    if kind == 'funnel':
        return _funnel_errors(d)
    if kind == 'allocation':
        return allocation_errors(d, record.get('links') or [], _day(record.get('updated_at')))
    errors = []
    if not _day(d.get('week_of')) or _day(d['week_of']).weekday() != 0:
        errors.append('detail.week_of must be a Monday')
    elif ladder_target(d['week_of']) is None or d.get('week_target') != ladder_target(d['week_of']):
        errors.append('detail.week_target must be the ladder target for its week_of in docs/NORTH_STAR.md')
    if d.get('organic_subscribers') is None:
        if not d.get('unavailable'):
            errors.append('a missing weekly count is recorded as unavailable, never zero')
    elif not _count(d['organic_subscribers']):
        errors.append('detail.organic_subscribers must be a whole number or null')
    if d.get('paid_counted') is not False:
        errors.append('paid never counts toward the North Star: paid_counted false')
    if d.get('observation') not in (record.get('links') or []):
        errors.append('detail.observation must be one of the record links')
    return errors


# Shared history -----------------------------------------------------------------------------------------

# What an evidence record must show for each basis that changes something, and for each spend case.
SHOWS = {
    'owner_correction': lambda r: r['source']['kind'] == 'user_ruling',
    'operational_failure': lambda r: (r['kind'] == 'route_hold' and r['state'] == 'held')
    or r['state'] == 'discrepancy',
    'observed_placement': lambda r: r['engine'] == 'acquisition' and r['state'] in ('booked', 'live',
                                                                                    'subscriber_attributed'),
    'conversion_route': lambda r: r['kind'] == 'funnel'
    and any(r['detail']['stages'].get(s) for s in ('visits_or_follows', 'subscriptions')),
    'costed_bottleneck': lambda r: r['kind'] == 'funnel'
    and any(_number(loss.get('cost')) and loss['cost'] > 0 for loss in r['detail'].get('losses') or []),
}


def _shown(case, ids, index):
    return any(i in index and SHOWS[case](index[i]) for i in ids)


def _performance_errors(rec, memo, everything, index):
    exp = index.get(rec.get('experiment'))
    if not exp or exp['kind'] != 'experiment':
        return ['names no experiment record']
    obs = [r['detail'] for r in everything['measurement'].values() if r['kind'] == 'observation'
           and r['detail'].get('experiment_id') == exp['detail'].get('experiment_id')]
    try:
        decision = performance_decision(exp['detail'], obs, memo['updated_at'] + 'T00:00:00+00:00')
    except (ValueError, KeyError, TypeError) as error:
        return ['experiment_decision refuses it: ' + str(error)]
    return [] if decision.startswith('review') else ['experiment_decision says ' + decision]


def check_shared(everything):
    """Errors no single line shows, read against the shared history: an open allocation's changes and spending
    must rest on evidence records that show them, and an open scorecard must match its linked observation."""
    index = {rid: r for recs in everything.values() for rid, r in recs.items()}
    errors = []
    for r in sorted(everything['measurement'].values(), key=lambda r: r['id']):
        if not _open(r):
            continue
        where = r['id'] + ': '
        if r['kind'] == 'scorecard':
            obs = everything['measurement'].get(r['detail']['observation'])
            try:
                expected = scorecard(obs, r['updated_at'])
            except (ValueError, KeyError, TypeError) as error:
                errors.append(where + 'cannot rebuild the scorecard from its observation: ' + str(error))
                continue
            got = {k: v for k, v in r['detail'].items() if k != 'freshness'}
            if got != {k: v for k, v in expected.items() if k != 'freshness'}:
                errors.append(where + 'the scorecard does not match scorecard() over its linked observation')
        if r['kind'] != 'allocation':
            continue
        for i, rec in enumerate(r['detail']['recommendations']):
            at = where + 'recommendation ' + str(i) + ': '
            basis = rec['basis']
            if rec['action'] in CHANGES and basis in ('owner_correction', 'operational_failure') \
                    and not _shown(basis, rec['evidence'], index):
                errors.append(at + 'its evidence names no ' + basis.replace('_', ' ') + ' record')
            if rec['action'] in CHANGES and basis == 'performance':
                errors += [at + e for e in _performance_errors(rec, r, everything, index)]
            if spends(rec) and not _shown(rec['spend_case'], rec['evidence'], index):
                errors.append(at + 'its evidence shows no ' + rec['spend_case'].replace('_', ' '))
        for i, item in enumerate(r['detail']['money']['proposed']):
            if not _shown(item['spend_case'], item['evidence'], index):
                errors.append(where + 'money.proposed.' + str(i) + ': its evidence shows no '
                              + item['spend_case'].replace('_', ' '))
    return errors


# Recovery -----------------------------------------------------------------------------------------------


def _open(record):
    return record.get('state') not in ('closed',) + CLOSED_STATES


def _due(record):
    found = DATE.search(record.get('revisit_when') or '')
    return found.group(1) if found else None


def overdue(records, all_records, now):
    """Measurements past due: this engine's open records whose revisit date has come, and work handed to
    Measurement by another engine whose judge window has passed with no measurement linked to it."""
    linked = {link for r in records.values() for link in r.get('links') or []}
    out = [{'id': r['id'], 'due': _due(r), 'why': r.get('revisit_when')}
           for r in records.values() if _open(r) and _due(r) and _due(r) <= now]
    for engine, recs in sorted(all_records.items()):
        if engine == 'measurement':
            continue
        for r in sorted(recs.values(), key=lambda r: r['id']):
            if r.get('next_owner') != 'measurement' or r['id'] in linked or not _day(r.get('updated_at')):
                continue
            d = r.get('detail') or {}
            hours = JUDGE_HOURS.get(d.get('channel'), JUDGE_HOURS.get(d.get('format'),
                                                                      JUDGE_HOURS['subscriber_impact']))
            due = (_day(r['updated_at']) + dt.timedelta(hours=hours)).isoformat()
            if due <= now:
                out.append({'id': r['id'], 'due': due, 'why': 'handed over by ' + engine + '; judge window passed'})
    return sorted(out, key=lambda o: (o['due'], o['id']))


def largest_constraint(records):
    """The biggest observed loss across recorded funnels, or the first observed stage at zero."""
    found = []
    for r in records.values():
        if r['kind'] != 'funnel' or not _open(r):
            continue
        d = r['detail']
        for loss in d.get('losses') or []:
            found.append((loss['count'], r['id'], d['engine_measured'], loss['at'], loss['reason']))
    if not found:
        return None
    count, rid, engine, stage, reason = max(found)
    stages = records[rid]['detail']['stages']
    return {'id': rid, 'engine': engine, 'stage': stage, 'lost': count, 'reason': reason,
            'observed': {k: v for k, v in stages.items() if v is not None}}


def recover(records, all_records, now):
    """Current number and source, comparable windows, overdue measurements, the largest observed constraint
    and one resource decision."""
    subs = sorted((r for r in records.values() if r['kind'] == 'observation'
                   and r['detail'].get('metric') in SUBSCRIBER_METRICS),
                  key=lambda r: (r['detail']['read_at'], r['id']))
    current = None
    if subs:
        latest = subs[-1]
        d = latest['detail']
        cards = [r['id'] for r in records.values() if r['kind'] == 'scorecard' and latest['id'] in r['links']]
        current = {'id': latest['id'], 'value': d.get('value') if d.get('value') is not None else 'unavailable',
                   'counted': None if d.get('value') is None else counted(d['attribution']),
                   'week_of': d['week_of'], 'week_target': ladder_target(d['week_of']),
                   'data_source': d['data_source'],
                   'window': {k: d.get(k) for k in ('window_start', 'window_end', 'window_days')},
                   'freshness': freshness(latest, now), 'attribution': d['attribution'], 'scorecards': sorted(cards)}
    windows = []
    if current:
        earlier = [dict(r['detail'], id=r['id']) for r in subs[:-1]]
        if isinstance(subs[-1]['detail'].get('previous'), dict):
            earlier.append(dict(subs[-1]['detail']['previous'], id=subs[-1]['id'] + ' (previous line)'))
        for e in sorted(earlier, key=lambda e: e['read_at'], reverse=True):
            same, why = comparable(e, subs[-1]['detail'])
            windows.append({'id': e['id'], 'read_at': e['read_at'], 'value': e.get('value'),
                            'week_of': e.get('week_of'), 'window_days': e.get('window_days'),
                            'comparable_with_current': same, 'reason': why})
    memos = sorted((r for r in records.values() if r['kind'] == 'allocation' and _open(r)),
                   key=lambda r: (r['updated_at'], r['id']))
    decision = None
    if memos:
        m = memos[-1]
        decision = {'id': m['id'], 'state': m['state'], 'question': m['detail']['question'],
                    'answer': m['detail']['answer'], 'next_owner': m['next_owner'],
                    'recommendations': [{k: rec.get(k) for k in ('action', 'what', 'owner', 'review_date',
                                                                 'reversal_condition')}
                                        for rec in m['detail']['recommendations']]}
    late = overdue(records, all_records, now)
    if late:
        nxt = {'id': late[0]['id'], 'next_action': 'read and record the overdue measurement', 'due': late[0]['due']}
    elif decision and decision['state'] == 'proposed':
        nxt = {'id': decision['id'], 'next_action': 'Krish decides on the allocation memo',
               'next_owner': decision['next_owner']}
    else:
        nxt = {'id': None, 'next_action': 'read the North Star source and record this week\'s observation'}
    return {'current_number': current, 'comparable_windows': windows, 'overdue': late,
            'largest_constraint': largest_constraint(records), 'resource_decision': decision, 'next_action': nxt}
