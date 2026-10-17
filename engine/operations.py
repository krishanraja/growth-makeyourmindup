"""Global work budget, honest observations, experiments and relationship events."""
import datetime as dt
import math

from .core import http_url, identity, instant, ny_time

METRICS = {
    'followers': ('accounts', 'snapshot'), 'subscribers': ('people', 'snapshot'),
    'reach': ('accounts', 'interval'), 'impressions': ('impressions', 'interval'),
    'views': ('views', 'interval'), 'plays': ('plays', 'interval'),
    'visits': ('sessions', 'interval'), 'link_clicks': ('clicks', 'interval'),
    'new_free': ('people', 'interval'), 'new_paid': ('people', 'interval'),
    'unsubscribes': ('people', 'interval'), 'retained_30d': ('people', 'cohort'),
    'effort': ('minutes', 'interval'), 'saves': ('saves', 'interval'), 'shares': ('shares', 'interval')}
AVAILABILITY = ('available', 'signed_out', 'not_connected', 'not_shown', 'not_supported', 'delayed')


def validate_observation(row):
    if not isinstance(row, dict):
        raise ValueError('observation must be an object')
    expected = METRICS.get(row.get('metric'))
    if not expected or (row.get('unit'), row.get('window_kind')) != expected:
        raise ValueError('metric, unit and window_kind do not match the metric registry')
    for field in ('platform', 'source', 'scope'):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError('observation needs ' + field)
    if not http_url(row.get('source')) or row.get('timezone') != 'America/New_York':
        raise ValueError('source URL and New York reporting timezone are required')
    start, end, captured = (instant(row.get(k)) if row.get(k) else None for k in ('start', 'end', 'captured_at'))
    if None in (start, end, captured) or end < start or captured < end:
        raise ValueError('invalid or future measurement window')
    if row['window_kind'] == 'snapshot' and start != end:
        raise ValueError('snapshot start and end must match')
    if row['window_kind'] != 'snapshot' and start == end:
        raise ValueError('interval/cohort window must have positive duration')
    if row['metric'] == 'retained_30d' and captured < end + dt.timedelta(days=30):
        raise ValueError('30-day retention needs a fully matured acquisition cohort')
    if row.get('availability') not in AVAILABILITY:
        raise ValueError('unknown availability')
    value = row.get('value')
    if row['availability'] == 'available':
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('available observations need a finite non-negative value')
    elif value is not None or not row.get('reason'):
        raise ValueError('unavailable observations need null value and an explicit reason')
    return row


def measurement_key(row):
    return tuple(row.get(k) for k in ('platform', 'metric', 'unit', 'scope', 'asset_id', 'source', 'start', 'end', 'window_kind'))


def aggregate(rows):
    """Add disjoint intervals only. Repeated captures replace an identical window."""
    unique = {}
    for row in rows:
        validate_observation(row)
        key = measurement_key(row)
        old = unique.get(key)
        if not old or instant(row['captured_at']) > instant(old['captured_at']):
            unique[key] = row
        elif instant(row['captured_at']) == instant(old['captured_at']) and row != old:
            raise ValueError('conflicting observations at the same capture time')
    values = sorted(unique.values(), key=lambda r: instant(r['start']))
    if not values:
        return {'value': None, 'reason': 'not shown'}
    signature = lambda r: tuple(r.get(k) for k in ('platform', 'metric', 'unit', 'scope', 'asset_id', 'source', 'window_kind'))
    if len({signature(r) for r in values}) != 1 or values[0]['window_kind'] != 'interval':
        raise ValueError('only comparable intervals can be summed; snapshots and cohorts cannot')
    if any(instant(a['end']) > instant(b['start']) for a, b in zip(values, values[1:])):
        raise ValueError('overlapping windows cannot be summed')
    if any(instant(a['end']) < instant(b['start']) for a, b in zip(values, values[1:])):
        return {'value': None, 'reason': 'measurement windows have gaps'}
    if any(r['value'] is None for r in values):
        return {'value': None, 'reason': 'one or more windows not shown'}
    return {'value': sum(r['value'] for r in values), 'windows': len(values),
            'start': values[0]['start'], 'end': values[-1]['end']}


def yield_per_thousand(subscribers, reach):
    for row in (subscribers, reach):
        validate_observation(row)
    match = all(subscribers.get(k) == reach.get(k) for k in ('platform', 'scope', 'asset_id', 'start', 'end', 'timezone'))
    if (not match or subscribers['metric'] != 'new_free' or reach['metric'] != 'reach'
            or not subscribers.get('attribution_basis') or subscribers.get('attribution_basis') == 'temporal'
            or subscribers['value'] is None or reach['value'] in (None, 0)):
        return {'value': None, 'reason': 'attributed new free subscribers and matching unique reach required'}
    return {'value': round(subscribers['value'] * 1000 / reach['value'], 2), 'unit': 'new free subscribers per 1000 accounts reached'}


def daily_queue(items, now=None):
    now = instant(now)
    budget = 30 if ny_time(now).weekday() == 6 else 20
    selected, deferred, used = [], [], 0
    seen = set()
    for item in items:
        uid = item.get('item_id')
        if not uid:
            raise ValueError('queue items need stable item_id')
        if uid in seen:
            raise ValueError('duplicate item_id in global queue')
        seen.add(uid)
        minutes = item.get('minutes')
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 30:
            raise ValueError('minutes must be an estimate from 1 to 30')
        if isinstance(item.get('priority'), bool) or item.get('priority') not in (1, 2, 3, 4, 5):
            raise ValueError('priority must be from 1 to 5; 1 is highest')
    for item in sorted(items, key=lambda r: (r['priority'], r.get('expires_at') or '9999', r['item_id'])):
        reason = None
        if item.get('status', 'draft') != 'draft':
            reason = 'already handled'
        elif item.get('expires_at') and instant(item['expires_at']) <= now:
            reason = 'expired; re-read source before replacing'
        elif item.get('blocked_by'):
            reason = 'prerequisite is not verified'
        elif used + item['minutes'] > budget:
            reason = 'daily budget'
        if reason:
            deferred.append({'item_id': item['item_id'], 'reason': reason})
        else:
            selected.append(item)
            used += item['minutes']
    return {'date': ny_time(now).date().isoformat(), 'budget_minutes': budget, 'estimated_minutes': used,
            'items': selected, 'deferred': deferred, 'note': 'Time estimates, not measured effort. Merge every job before choosing.'}


RELATIONSHIP_EVENTS = ('drafted', 'sent', 'replied', 'declined', 'booked', 'published')


def relationship(events, person_id, now=None, cooldown_days=60):
    now = instant(now)
    events = [e for e in events if e.get('person_id') == person_id]
    ids = set()
    for event in events:
        if event.get('type') not in RELATIONSHIP_EVENTS or instant(event['at']) > now:
            raise ValueError('invalid relationship event or future date')
        if not event.get('event_id') or event['event_id'] in ids:
            raise ValueError('relationship events need unique event_id')
        ids.add(event['event_id'])
        if event['type'] != 'drafted' and (event.get('confirmed_by') != 'Krish' or not http_url(event.get('evidence_url'))):
            raise ValueError('real interaction needs Krish confirmation and evidence URL')
    events.sort(key=lambda e: instant(e['at']))
    real = [e for e in events if e['type'] != 'drafted']
    last = real[-1] if real else None
    sent = [e for e in real if e['type'] == 'sent']
    due = instant(sent[-1]['at']) + dt.timedelta(days=cooldown_days) if sent else None
    declined = bool(last and last['type'] == 'declined')
    inbound = bool(last and last['type'] == 'replied')
    return {'person_id': person_id, 'state': last['type'] if last else 'uncontacted',
            'eligible': not declined and (inbound or due is None or due <= now),
            'next_due_at': due.isoformat() if due else None,
            'note': 'Drafting never means contact. A real inbound reply can justify the next relevant step.'}


def experiment_decision(experiment, observations, now=None):
    now = instant(now)
    if experiment.get('status') not in ('planned', 'running', 'completed'):
        raise ValueError('invalid experiment status')
    for field in ('hypothesis', 'primary_metric', 'guardrail', 'decision_rule', 'owner'):
        if not isinstance(experiment.get(field), str) or not experiment[field].strip():
            raise ValueError('experiment needs ' + field)
    minimum = experiment.get('minimum_observations')
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError('experiment needs a positive minimum_observations')
    start, end = instant(experiment['start']), instant(experiment['end'])
    if end <= start:
        raise ValueError('invalid experiment duration')
    qualified = [r for r in observations if r.get('experiment_id') == experiment['experiment_id']
                 and r.get('metric') == experiment['primary_metric']]
    for row in qualified:
        validate_observation(row)
    if now < end or experiment['status'] != 'completed':
        return 'collect: planned window is not completed'
    if len({measurement_key(r) for r in qualified if r['value'] is not None and
            start <= instant(r['start']) < instant(r['end']) <= end}) < minimum:
        return 'collect: too few comparable observations; no kill or scale decision'
    return 'review: Krish applies the predeclared rule and guardrail; association alone does not establish cause'
