"""`growth.py run paid audit`: what earned genuine interest, and what paid reach bought. Read only, local only.

Asked by Krish on 15 Nov 2026 ("we need to understand what is generating genuine interest versus what is worth
paying boosts for"; docs/reviews/2026-11-15-interest-vs-paid.md). That review was worked by hand. This makes the
same reading repeatable, and keeps paid reach out of the organic picture the North Star is judged on
(docs/NORTH_STAR.md: zero paid boosts). Its shape follows the audit contract borrowed from Claude Ads
(docs/reviews/2026-11-15-hyperframes-and-claude-ads.md): every check ends pass, fail, unknown or not_applicable
with its evidence, unknown is a real answer and never a guess, and every recommendation is a draft that changes
no account.

Inputs, all local files; nothing here opens a network connection:

- `--posts FILE`: the raw Buffer list_posts pages a read session saved with includeMetrics true, as
  {"read_at", "posts": [...]}. A post counts when its channelId is one this engine reads
  (engine/buffer_channels.py READ_CHANNEL_ID, with the LinkedIn handover's read_channel). Unlike the measure job
  (buffer_reads.sent_posts, F17), posts made natively on those accounts (`via: network`) are read too: paid reach
  lands on the account whoever posted, and the 15 Nov review's largest suspect (TikTok, 11 Nov) was a native post.
  They are marked by `via` and never become this engine's verdicts.
- `--records FILE`: measurement records (default engines/records/measurement.jsonl). Each observation with
  `detail.paid_boost` is a boost Codex read in Krish's ads manager (Ruling, Krish, 2026-11-15), validated by
  engine/engines/measurement.py before it is used.
- `--boosts FILE`: optional, more observation records in the same shape (a JSON list), for readings not yet
  recorded.
- `--substack FILE`: optional, a Substack growth-sources capture (measure.validate_capture), for the check that
  no subscriber from a boosted platform's boost week is counted as organic without a question.

It writes one JSON report (default .scratch/paid/audit.json, ignored by git) and prints a short summary. It never
posts, sends, schedules, spends, boosts, pauses, edits a campaign or writes to Control Center, and it has no
--deliver. Thresholds marked "proposed" wait for Krish's approval and decide nothing on their own.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

from ..buffer_channels import READ_CHANNEL_ID, read_channel
from ..core import instant, read_json, write_json
from ..engines.measurement import validate_detail
from .buffer_reads import _words, metric_values
from .measure import label_key, load_sources, validate_capture
from .measure_auto import INDICATORS, LOOKBACK_DAYS, WINDOW_HOURS, _median

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path('engines') / 'records' / 'measurement.jsonl'
OUT = Path('.scratch') / 'paid' / 'audit.json'
RESULTS = ('pass', 'fail', 'unknown', 'not_applicable')
# The interactions a reader chooses to make, as Buffer names them (social/share.json, read 28 Oct 2026). Likes are
# read only where a post shows no reactions, so one tap is never counted twice.
INTERACTIONS = ('reactions', 'comments', 'shares', 'saves', 'reposts', 'replies', 'quotes')
LIKE_FALLBACK = 'likes'
# Which Buffer channels a boost on each ads platform can touch (engine/engines/measurement.py BOOST_PLATFORMS).
PLATFORM_CHANNELS = {'meta': ('facebook', 'instagram', 'threads'), 'tiktok': ('tiktok',), 'youtube': ('youtube',),
                     'x': ('x',), 'linkedin': ('linkedin',)}
# Where Codex reads each platform's boosts, read only, in Krish's signed-in browser (the 15 Nov review's reading list).
READ_WHERE = {'meta': "Meta Ads Manager and the Page's boost history", 'tiktok': 'TikTok Promote',
              'youtube': 'YouTube Studio traffic sources (Shorts feed, search, external or ads) and Google Ads',
              'x': 'X Ads', 'linkedin': 'LinkedIn Campaign Manager'}
# Substack Notes has no ads platform: a Note far above its median was lifted by Substack, never bought.
BOOSTABLE = {c for chans in PLATFORM_CHANNELS.values() for c in chans}
# Which Substack growth-source labels a boost on each ads platform could feed (invariants/sources.json keys).
PLATFORM_SOURCES = {'meta': ('facebook', 'instagram', 'threads'), 'tiktok': ('tiktok',), 'youtube': ('youtube',),
                    'x': ('x', 'twitter'), 'linkedin': ('linkedin',)}
# A boost usually promotes a post that is already live, so a post sent this many days before a boost window opens
# is inside its reach too.
LEAD_DAYS = 3
# Proposed defaults for Krish's approval. A post is far past its channel at REACH_MULTIPLE times the median of the
# channel's ordinary organic posts. On a channel an ads platform can boost, with at least MIN_PAID_EXPOSURE views or
# impressions, it is suspected paid when its interactions per 1,000 are at or under RATE_FRACTION of the channel's
# pooled organic rate (reach without interest), or at EXTREME_MULTIPLE whatever its rate (a Page whose median is 4
# does not reach 16,000 people unpaid). Under MIN_PAID_EXPOSURE a spike is too small to call bought.
REACH_MULTIPLE = 10
EXTREME_MULTIPLE = 100
RATE_FRACTION = 0.5
MIN_PAID_EXPOSURE = 1000
# A breakout needs this many interactions: one reaction on a few hundred views is noise, not people staying with it.
MIN_BREAKOUT_INTERACTIONS = 3
MIN_BASELINE = 6
# A channel median that moves by more than this once paid posts are held out says paid reach was inflating it.
INFLATION = 0.25
STATUS = "proposed defaults for Krish's approval"
DRAFT = {'mutation': 'none', 'approval': "Krish's Yes on this exact line, before anyone acts on it",
         'counts_toward_north_star': False}
# The only recommendation kinds this audit can make. None launches, buys, boosts, pauses, edits or changes a budget:
# a change to an ad account is Krish's own action, on his Yes, outside this engine.
ACTIONS = ('read_boost', 'hold_out', 'no_new_boosts', 'make_more_like')


def capture_posts(capture, since, now):
    """The sent posts in a saved list_posts capture on the channels this engine reads, sent from since to now,
    with their count metrics. {'posts': [...], 'listed', 'skipped': {why: count}}."""
    if not isinstance(capture, dict) or not isinstance(capture.get('posts'), list):
        raise ValueError('the posts capture needs a posts list (Buffer list_posts pages, includeMetrics true)')
    known = set(READ_CHANNEL_ID.values())
    posts, skipped = [], {}

    def skip(why):
        skipped[why] = skipped.get(why, 0) + 1

    for post in capture['posts']:
        if not isinstance(post, dict):
            skip('not a post')
            continue
        channel_obj = post.get('channel') if isinstance(post.get('channel'), dict) else {}
        cid = channel_obj.get('id') or post.get('channelId')
        if cid not in known:
            skip('a channel this engine does not read')
            continue
        if post.get('status') != 'sent' or not isinstance(post.get('sentAt'), str):
            skip('not sent')
            continue
        sent_at = instant(post['sentAt'])
        if not since <= sent_at <= now:
            skip('outside the window')
            continue
        channel = read_channel(cid, sent_at)
        if channel is None:
            skip("after the channel's handover")
            continue
        pid = post.get('id')
        if not isinstance(pid, str) or not pid:
            skip('no post id')
            continue
        metrics = metric_values(post['metrics']) if isinstance(post.get('metrics'), list) else None
        posts.append({'post_id': pid, 'channel': channel, 'via': post.get('via'), 'sent_at': sent_at,
                      'words': _words(post), 'metrics': metrics})
    return {'posts': posts, 'listed': len(capture['posts']), 'skipped': skipped}


def check(check_id, result, why, evidence=()):
    if result not in RESULTS:
        raise ValueError('a check ends ' + ', '.join(RESULTS))
    return {'id': check_id, 'result': result, 'why': why, 'evidence': list(evidence)}


def recommend(kind, what, why, evidence, owner):
    if kind not in ACTIONS:
        raise ValueError('recommendation kind must be one of ' + ', '.join(ACTIONS))
    return dict({'kind': kind, 'what': what, 'why': why, 'evidence': list(evidence), 'owner': owner}, **DRAFT)


def interactions(metrics):
    """(count, the metrics it came from); None when the post shows none of them, never zero for missing."""
    names = [n for n in INTERACTIONS if n in metrics]
    if 'reactions' not in metrics and LIKE_FALLBACK in metrics:
        names.append(LIKE_FALLBACK)
    if not names:
        return None, []
    return sum(metrics[n] for n in names), names


def per_thousand(count, exposure):
    if count is None or not exposure:
        return None
    return round(count * 1000.0 / exposure, 1)


def pooled_rate(rows):
    """The channel's interactions per 1,000 across these posts together, so a channel whose posts mostly show none
    still has a rate; None when they show no exposure or no interactions at all."""
    shown = [r for r in rows if r['interactions'] is not None and r['exposure']]
    exposure = sum(r['exposure'] for r in shown)
    return per_thousand(sum(r['interactions'] for r in shown), exposure) if exposure else None


def first_line(words, limit=72):
    line = (words or '').strip().splitlines()[0] if (words or '').strip() else ''
    return line if len(line) <= limit else line[:limit - 3].rstrip() + '...'


# Boost readings -------------------------------------------------------------------------------------------


def boost_readings(records):
    """The paid_boost observations among the records that pass measurement's own validation, and the ones that
    do not, with why."""
    found, refused = [], []
    for record in records:
        if not isinstance(record, dict) or record.get('kind') != 'observation':
            continue
        detail = record.get('detail') if isinstance(record.get('detail'), dict) else {}
        if detail.get('paid_boost') is None:
            continue
        errors = validate_detail(record)
        if errors:
            refused.append({'id': record.get('id'), 'errors': errors})
            continue
        boost = detail['paid_boost']
        found.append({'id': record.get('id'), 'platform': boost['platform'],
                      'window_start': dt.date.fromisoformat(boost['window_start']),
                      'window_end': dt.date.fromisoformat(boost['window_end']),
                      'spend_cents': boost.get('spend_cents'), 'piece': boost.get('piece'),
                      'metric': detail.get('metric'), 'value': detail.get('value'), 'read_at': detail.get('read_at')})
    return found, refused


def covering(post, boosts):
    """The boost readings whose platform reaches this post's channel and whose window covers its sent day (or
    opens within LEAD_DAYS after it)."""
    day = post['sent_at'].date()
    return [b for b in boosts if post['channel'] in PLATFORM_CHANNELS[b['platform']]
            and b['window_start'] - dt.timedelta(days=LEAD_DAYS) <= day <= b['window_end']]


# The reading ----------------------------------------------------------------------------------------------


def _row(post, indicator, boosts):
    metrics = post['metrics'] or {}
    exposure = metrics.get(indicator) if indicator else None
    count, names = interactions(metrics)
    paid = covering(post, boosts)
    return {'post_id': post['post_id'], 'channel': post['channel'], 'via': post['via'], 'sent_at': post['sent_at'],
            'first_line': first_line(post['words']), 'indicator': indicator, 'exposure': exposure,
            'interactions': count, 'interactions_from': names, 'shares': metrics.get('shares'),
            'free_subscriptions': metrics.get('freeSubscriptions'),
            'per_1000': per_thousand(count, exposure), 'boosts': [b['id'] for b in paid],
            'class': 'paid_window' if paid else None, 'reach_multiple': None, 'rate_vs_channel': None, 'why': None}


def channel_reading(posts, boosts, now):
    """One channel's rows and organic baseline. Paid-window posts never enter the baseline; each judged post is
    compared with the channel's other mature organic posts only."""
    channel = posts[0]['channel']
    indicator = next((n for n in INDICATORS if any(n in (p['metrics'] or {}) for p in posts)), None)
    window = dt.timedelta(hours=WINDOW_HOURS.get(channel, 72))
    rows = [_row(p, indicator, boosts) for p in posts]
    mature = [r for r in rows if r['exposure'] is not None and now - r['sent_at'] >= window]
    organic = [r for r in mature if r['class'] is None]
    # The baseline is the channel's ordinary organic posts: a post ten times past the median is the thing being
    # judged, never part of what it is judged against, so one bought spike cannot dilute the channel's rate.
    centre = _median([r['exposure'] for r in organic])
    ordinary = [r for r in organic if centre is not None and r['exposure'] < REACH_MULTIPLE * max(centre, 1)]
    for row in rows:
        if row['class'] is not None:
            continue
        others = [r for r in ordinary if r is not row]
        if row['exposure'] is None:
            row['class'] = 'not_shown'
            row['why'] = 'Buffer shows no ' + (indicator or 'exposure metric') + ' for this post'
            continue
        if len(others) < MIN_BASELINE:
            row['class'] = 'insufficient'
            row['why'] = 'fewer than {} ordinary organic posts on this channel to compare with'.format(MIN_BASELINE)
            continue
        median, rate = _median([r['exposure'] for r in others]), pooled_rate(others)
        multiple = row['exposure'] / max(median, 1)
        row['reach_multiple'] = round(multiple, 1)
        row['rate_vs_channel'] = None if not rate or row['per_1000'] is None else round(row['per_1000'] / rate, 2)
        bought = channel in BOOSTABLE and row['exposure'] >= MIN_PAID_EXPOSURE
        said = 'reach {}x the organic median of {}, {} interactions per 1,000 against the channel\'s {}'.format(
            row['reach_multiple'], median, row['per_1000'], rate)
        if multiple < REACH_MULTIPLE:
            young = now - row['sent_at'] < window
            row['class'] = 'too_early' if young else 'organic'
            row['why'] = 'its judge window has not passed' if young else None
        elif bought and multiple >= EXTREME_MULTIPLE:
            row['class'] = 'suspected_paid'
            row['why'] = said + ': reach this channel has not reached organically'
        elif bought and rate and row['per_1000'] is not None and row['per_1000'] <= rate * RATE_FRACTION:
            row['class'] = 'suspected_paid'
            row['why'] = said + ': reach without interest'
        elif (row['interactions'] or 0) >= MIN_BREAKOUT_INTERACTIONS and (not rate or row['per_1000'] >= rate):
            row['class'] = 'organic_breakout'
            row['why'] = said + ': people stayed with it'
        else:
            row['class'] = 'reach_outlier'
            row['why'] = said + (': too small to call bought' if channel in BOOSTABLE
                                 else ': no ads platform can boost this channel')
    all_mature = [r['exposure'] for r in mature]
    kept = [r for r in mature if r['class'] not in ('paid_window', 'suspected_paid')]
    baseline = {'channel': channel, 'indicator': indicator, 'posts': len(rows), 'mature': len(mature),
                'median_all': _median(all_mature), 'median_organic': _median([r['exposure'] for r in kept]),
                'held_out': len(mature) - len(kept), 'rate_organic': pooled_rate(kept)}
    return rows, baseline


def exposure_check(capture, boosts, sources_path, root):
    """Subscribers Substack credits to a platform whose boost window overlaps the capture's window are not
    provably organic. The North Star's number is not changed here: the check says how many, and why."""
    if capture is None:
        return check('north_star_exposure', 'unknown', 'no Substack growth-sources capture was given'), []
    start, end = dt.date.fromisoformat(capture['window']['start']), dt.date.fromisoformat(capture['window']['end'])
    overlapping = [b for b in boosts if b['window_start'] <= end and b['window_end'] >= start]
    if not overlapping:
        return check('north_star_exposure', 'pass' if boosts else 'not_applicable',
                     'no recorded boost overlaps the window ' + str(start) + ' to ' + str(end)), []
    mapping, approved, reason = load_sources(sources_path, root)
    exposed = []
    for boost in overlapping:
        labels = PLATFORM_SOURCES[boost['platform']]
        for row in capture['rows']:
            key = label_key(row['source'])
            if key in labels and (mapping or {}).get(key) == 'organic':
                exposed.append({'source': row['source'], 'new_free': row['new_free'], 'boost': boost['id']})
    unknown = [e for e in exposed if e['new_free'] is None]
    counted = sum(e['new_free'] for e in exposed if e['new_free'] is not None)
    evidence = [e['boost'] for e in exposed]
    if unknown:
        return check('north_star_exposure', 'unknown', 'a source a boost could feed shows no count', evidence), exposed
    if counted:
        return check('north_star_exposure', 'fail',
                     '{} new subscriber(s) from {} in a boost window are counted as organic; not provably organic'
                     .format(counted, ', '.join(sorted({e['source'] for e in exposed if e['new_free']}))),
                     evidence), exposed
    return check('north_star_exposure', 'pass', 'no subscriber came from a boosted platform in the window',
                 evidence), exposed


def audit(capture, records, now=None, since=None, substack=None, sources_path='invariants/sources.json', root=ROOT):
    """The whole reading as one JSON-ready dict."""
    now = instant(now)
    since = instant(since) if since is not None else now - dt.timedelta(days=LOOKBACK_DAYS)
    read = capture_posts(capture, since, now)
    boosts, refused = boost_readings(records)
    if substack is not None:
        substack = validate_capture(substack, now)
    by_channel = {}
    for post in read['posts']:
        by_channel.setdefault(post['channel'], []).append(post)
    rows, baselines = [], []
    for channel in sorted(by_channel):
        channel_rows, baseline = channel_reading(sorted(by_channel[channel], key=lambda p: p['sent_at']), boosts, now)
        rows += channel_rows
        baselines.append(baseline)
    suspects = [r for r in rows if r['class'] == 'suspected_paid']
    breakouts = [r for r in rows if r['class'] == 'organic_breakout']
    paid_window = [r for r in rows if r['class'] == 'paid_window']
    checks = []
    if suspects:
        checks.append(check('boosts_recorded', 'fail',
                            '{} post(s) look paid and no recorded boost covers them'
                            .format(len(suspects)), [r['post_id'] for r in suspects]))
    elif boosts or rows:
        checks.append(check('boosts_recorded', 'pass', 'every post that looks paid has a boost reading covering it',
                            [b['id'] for b in boosts]))
    else:
        checks.append(check('boosts_recorded', 'not_applicable', 'no posts and no boost readings'))
    inflated = [b for b in baselines if b['median_all'] and b['median_organic'] is not None
                and abs(b['median_all'] - b['median_organic']) / b['median_all'] > INFLATION]
    judged = [b for b in baselines if b['median_all'] is not None]
    if inflated:
        checks.append(check('organic_baseline', 'fail',
                            'paid or suspected-paid posts move the channel median by more than a quarter on '
                            + ', '.join(b['channel'] for b in inflated), [b['channel'] for b in inflated]))
    else:
        checks.append(check('organic_baseline', 'pass' if judged else 'unknown',
                            'holding paid posts out moves no channel median by more than a quarter' if judged
                            else 'no channel has a mature post with an exposure metric'))
    spends = [b for b in boosts if b['spend_cents'] is None]
    checks.append(check('spend_known', 'not_applicable' if not boosts else 'unknown' if spends else 'pass',
                        'no boost readings' if not boosts else
                        '{} boost reading(s) show no spend'.format(len(spends)) if spends else
                        'every boost reading shows its spend', [b['id'] for b in spends]))
    exposure, exposed = exposure_check(substack, boosts, sources_path, root)
    checks.append(exposure)
    checks.append(check('zero_paid_line',
                        'fail' if boosts else 'unknown' if suspects else 'pass',
                        '{} boost(s) were read in the window; the North Star is zero paid, so their results are '
                        'reported apart and never counted'.format(len(boosts)) if boosts else
                        'posts look paid but no boost has been read, so whether money was spent is unknown'
                        if suspects else 'no boost read and no post looks paid',
                        [b['id'] for b in boosts] or [r['post_id'] for r in suspects]))
    recs = []
    for row in suspects:
        platform = next(p for p, chans in sorted(PLATFORM_CHANNELS.items()) if row['channel'] in chans)
        recs.append(recommend('read_boost', 'Read {} for the {} post of {}: did a boost or promotion run, its window, '
                              'spend, reach and clicks'.format(READ_WHERE[platform], row['channel'],
                                                               row['sent_at'].date()),
                              row['why'], [row['post_id']], "Codex, in Krish's browser, read only"))
    if exposure['result'] == 'fail':
        recs.append(recommend('hold_out', 'Hold the subscribers named in north_star_exposure out of the organic count '
                              'until each boost is judged', exposure['why'], exposure['evidence'], 'Krish'))
    if boosts or suspects:
        recs.append(recommend('no_new_boosts', 'Buy no further boosts for Make Your Mind Up until subscribers per '
                              'pound is known for the ones already run',
                              'the North Star counts organic subscribers only, and no boost has a subscriber count yet',
                              [b['id'] for b in boosts] or [r['post_id'] for r in suspects], 'Krish'))
    for row in sorted(breakouts, key=lambda r: -(r['rate_vs_channel'] or 0))[:3]:
        recs.append(recommend('make_more_like', 'Make more posts like "' + row['first_line'] + '" on ' + row['channel'],
                              row['why'], [row['post_id']], 'the week\'s mix, through the learn job'))
    return {'kind': 'paid_audit', 'version': 1, 'now': now.isoformat(), 'since': since.isoformat(),
            'source': {'posts_read_at': capture.get('read_at'), 'listed': read['listed'], 'judged': len(read['posts']),
                       'native': sum(1 for p in read['posts'] if p['via'] == 'network'), 'skipped': read['skipped']},
            'thresholds': {'reach_multiple': REACH_MULTIPLE, 'extreme_multiple': EXTREME_MULTIPLE,
                           'rate_fraction': RATE_FRACTION, 'min_paid_exposure': MIN_PAID_EXPOSURE,
                           'min_breakout_interactions': MIN_BREAKOUT_INTERACTIONS,
                           'min_baseline': MIN_BASELINE, 'lead_days': LEAD_DAYS, 'inflation': INFLATION,
                           'status': STATUS},
            'boosts': [dict(b, window_start=str(b['window_start']), window_end=str(b['window_end'])) for b in boosts],
            'refused_boost_records': refused, 'baselines': baselines,
            'posts': [dict(r, sent_at=r['sent_at'].isoformat()) for r in sorted(rows, key=lambda r: r['sent_at'])],
            'suspected_paid': [r['post_id'] for r in suspects], 'organic_breakouts': [r['post_id'] for r in breakouts],
            'paid_window': [r['post_id'] for r in paid_window], 'north_star_exposed': exposed,
            'checks': checks, 'recommendations': recs,
            'boundary': 'read only: nothing was posted, sent, scheduled, spent, boosted, paused or edited, and nothing '
                        'was written to Control Center'}


def read_records(path):
    path = Path(path)
    if not path.is_file():
        return []
    if path.suffix == '.jsonl':
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    value = read_json(path)
    if not isinstance(value, list):
        raise ValueError(str(path) + ' must hold a list of observation records')
    return value


def summary(report):
    lines = ['paid audit: {} posts judged on {} channels, read {}'.format(
        report['source']['judged'], len(report['baselines']), report['source']['posts_read_at'] or 'at an unknown time')]
    for b in report['baselines']:
        lines.append('  {:<15} {:<11} median {} all, {} organic ({} held out), {} interactions per 1,000'.format(
            b['channel'], b['indicator'] or 'none', b['median_all'], b['median_organic'], b['held_out'],
            b['rate_organic']))
    for row in report['posts']:
        if row['class'] in ('suspected_paid', 'organic_breakout', 'paid_window'):
            lines.append('  {:<16} {:<15} {} {}x: {}'.format(row['class'], row['channel'], row['sent_at'][:10],
                                                             row['reach_multiple'], row['first_line']))
    for c in report['checks']:
        lines.append('  check {:<20} {:<14} {}'.format(c['id'], c['result'], c['why']))
    lines.append('  {} draft recommendation(s), none acted on; {}'.format(len(report['recommendations']),
                                                                         report['boundary']))
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:2] != ['paid', 'audit']:
        print('usage: growth.py run paid audit --posts FILE [--records FILE] [--boosts FILE] [--substack FILE] '
              '[--now ISO] [--since ISO] [--out FILE]')
        return 2
    parser = argparse.ArgumentParser(prog='growth.py run paid audit', description=__doc__.split('\n')[0])
    parser.add_argument('--posts', required=True)
    parser.add_argument('--records', default=str(ROOT / RECORDS))
    parser.add_argument('--boosts')
    parser.add_argument('--substack')
    parser.add_argument('--now')
    parser.add_argument('--since')
    parser.add_argument('--out', default=str(ROOT / OUT))
    args = parser.parse_args(argv[2:])
    records = read_records(args.records) + (read_records(args.boosts) if args.boosts else [])
    report = audit(read_json(args.posts), records, now=args.now, since=args.since,
                   substack=read_json(args.substack) if args.substack else None)
    write_json(args.out, report)
    print(summary(report))
    print('  written to ' + str(args.out))
    return 0
