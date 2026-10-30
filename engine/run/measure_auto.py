"""`growth.py run measure auto [--deliver]`: the scheduled measure job.

Runs on GitHub Actions three times a day (.github/workflows/measure.yml):

1. reads this engine's sent posts on its eight pinned Buffer channels, with
   Buffer's per-post metrics where present (engine/run/buffer_reads.py);
2. reads Control Center's `web_analytics` rows: from the directive it pulls
   itself with --deliver, or from .scratch/cc/web-analytics.json (kept by the
   runner or `cc start`) on a dry run;
3. joins them on utm_content (engine/run/ga4.py join_directive);
4. gives each post a verdict against its own channel's median
   (engine/run/measure.py judge: works, neutral, fails or insufficient, at
   least six observations, association not cause), with every channel kept
   insufficient for its first 14 days;
5. reports the aggregates to Control Center by the existing report path
   (engine/cc_loop.py run: attempt, directive, report and readback,
   decisions, attempt end).

The numbers go only into the Control Center report and the ignored local
copy. The log carries counts per verdict, notes and the cost line. Without
--deliver nothing is sent to Control Center. Nothing here posts, sends,
publishes or spends.
"""
import argparse
import datetime as dt
from pathlib import Path
import sys

from .. import meter
from ..cc_loop import (STATE_DIR, count, WEB_ANALYTICS_FILE, keep_web_analytics, revision, run, summary,
                       web_analytics_activity, web_analytics_block, web_analytics_summary)
from ..control_center import SLUG, build_report, iso, objective
from ..core import instant, read_json, today, write_json
from . import buffer_reads
from .ga4 import directive_rows, join_directive, load_config
from .measure import judge, share_rates
from .release import BUFFER_NAME

ROOT = Path(__file__).resolve().parents[2]
VERDICTS = ('works', 'neutral', 'fails', 'insufficient')
# Judge windows from the crew table (docs/plans/2026-10-27-engine-architecture.md, section 3).
WINDOW_HOURS = {'substack-notes': 24, 'threads': 48, 'x': 48, 'linkedin': 48,
                'instagram': 72, 'facebook': 72, 'youtube': 72, 'tiktok': 72}
# Proposed default for Krish's approval at G-A: the channel's leading indicator is
# the first of these Buffer shows on its posts, so a channel is judged on one measure.
INDICATORS = ('impressions', 'views', 'reach')
NEW_CHANNEL_DAYS = 14
LOOKBACK_DAYS = 56
NEW_CHANNEL = 'new channel: its first 14 days are a baseline with no verdicts'
COMMAND = 'measure'
NOT_MEASURED = ('The measure job reads Buffer and the GA4 rows Control Center sends, not the Substack '
                'dashboard, so the North Star is measured by the numbers job')
NO_SPEND = 'This engine has no spend authority, bought no boosts and does not read platform ad spend'


def run_id(now):
    return SLUG + ':' + today(now) + ':' + COMMAND + '-' + instant(now).strftime('%H%MZ')


def _median(values):
    values = sorted(values)
    if not values:
        return None
    middle = len(values) // 2
    value = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return int(value) if float(value).is_integer() else value


def verdicts(posts, now):
    """One verdict per post against its own channel's median; channels with their aggregates."""
    now = instant(now)
    by_channel = {}
    for post in posts:
        by_channel.setdefault(post['channel'], []).append(post)
    results, channels = [], {}
    for cid in sorted(by_channel):
        rows = by_channel[cid]
        first = min(p['sent_at'] for p in rows)
        indicator = next((name for name in INDICATORS if any(name in (p['metrics'] or {}) for p in rows)), None)
        window = WINDOW_HOURS[cid]

        def elapsed(post):
            return (now - post['sent_at']).total_seconds() / 3600

        mature = [p for p in rows if indicator and indicator in (p['metrics'] or {}) and elapsed(p) >= window]
        new = now - first < dt.timedelta(days=NEW_CHANNEL_DAYS)
        tally = dict.fromkeys(VERDICTS, 0)
        for post in rows:
            value = (post['metrics'] or {}).get(indicator) if indicator else None
            if new:
                result = {'verdict': 'insufficient', 'reason': NEW_CHANNEL}
            elif value is None:
                result = {'verdict': 'insufficient', 'reason': 'Buffer shows no ' + (indicator or 'count metric')
                          + ' for this post'}
            else:
                row = {'channel': cid, 'format': 'all', 'indicator': indicator, 'value': value}
                history = [{'channel': cid, 'format': 'all', 'indicator': indicator, 'value': p['metrics'][indicator]}
                           for p in mature if p is not post]
                result = judge(row, history, window, elapsed(post))
            tally[result['verdict']] += 1
            results.append({'post_id': post['post_id'], 'channel': cid, 'indicator': indicator, 'value': value,
                            'verdict': result['verdict'], 'median': result.get('median'),
                            'ratio': result.get('ratio'), 'reason': result.get('reason')})
        channels[cid] = {'posts': len(rows), 'indicator': indicator, 'window_hours': window, 'new': new,
                         'median': _median([p['metrics'][indicator] for p in mature]), 'mature': len(mature),
                         'verdicts': tally}
    return results, channels


def tally(results):
    counts = dict.fromkeys(VERDICTS, 0)
    for item in results:
        counts[item['verdict']] += 1
    return counts


def post_metrics(posts, now):
    """Each post's numbers as Buffer shows them, for Control Center (protocol 1.17.0 post_metrics), at most 60,
    newest first. A number the post does not show is null, never zero. A sent post is not matched back to its
    go-live here, so proposal_id is null and slot_id is its Buffer id; url waits on the board tick's listing."""
    rows = []
    for post in sorted(posts, key=lambda p: p['sent_at'], reverse=True)[:60]:
        metrics = post.get('metrics') or {}
        try:
            rates = share_rates(post['channel'], metrics)
        except ValueError:
            rates = {}

        def whole(value):
            return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) \
                and float(value).is_integer() and 0 <= value <= 10 ** 10 else None
        rows.append({'proposal_id': None, 'slot_id': 'buffer:' + post['post_id'], 'channel': post['channel'],
                     'posted_at': iso(post['sent_at']), 'url': None, 'measured_at': iso(now),
                     'reach': whole(rates.get('reach')), 'sends': whole(rates.get('sends')),
                     'saves': whole(rates.get('saves')), 'likes': whole(metrics.get('likes')),
                     'comments': whole(metrics.get('comments'))})
    return rows


def share_part(posts):
    """Sends and saves per 1,000 reached, by channel, over the posts that show both (W2.8).

    The snackable lane's primary measure (measure.share_rates, Krish, 2026-10-28),
    labelled with its status: a house hypothesis until MYMU's own dated data
    confirms it. A channel that shows no sends, saves or reach says so, never zero.
    Returns (activity lines, {channel: aggregate})."""
    by_channel = {}
    for post in posts:
        try:
            rates = share_rates(post['channel'], post['metrics'] or {})
        except ValueError:
            continue
        by_channel.setdefault(post['channel'], []).append(rates)
    out, lines = {}, []
    status = None
    for cid in sorted(by_channel):
        rows = by_channel[cid]
        status = rows[0]['status']
        agg = {'posts': len(rows)}
        for key in ('sends', 'saves'):
            shown = [r for r in rows if r[key] is not None and r['reach']]
            reach = sum(r['reach'] for r in shown)
            agg[key + '_per_1000_reached'] = round(sum(r[key] for r in shown) * 1000 / reach, 1) if reach else None
            agg[key + '_posts_shown'] = len(shown)
        out[cid] = agg

        def say(key):
            value = agg[key + '_per_1000_reached']
            return (key + ' not shown' if value is None
                    else key + ' ' + str(value) + ' per 1,000 reached over ' + count(agg[key + '_posts_shown'], 'post'))
        lines.append('Built to be sent, ' + cid + ': ' + say('sends') + '; ' + say('saves'))
    if lines:
        lines.append('Sends and saves per reach are the snackable lane\'s measure: ' + str(status))
    return lines, out


def ga4_part(block, posts, config):
    """(activity lines, hold or None, joined result or None). Unknown is said, never zero."""
    if block is None:
        return ["GA4: today's directive carried no web_analytics block, so no post was joined"], None, None
    try:
        rows = directive_rows(block)
    except ValueError as exc:
        return [], {'reason': 'GA4 rows from Control Center could not be read', 'detail': str(exc)}, None
    lines = []
    if rows is not None:
        groups = {}
        for r in rows:
            key = (r['date'], r['source'], r['content'])
            groups[key] = max(groups.get(key, 0), r['sessions'])
        lines.append('GA4 per-post rows: ' + str(len({r['content'] for r in rows})) + ' utm_content values, about '
                     + str(sum(groups.values())) + ' sessions (a lower bound across event rows)')
    if not posts:
        return lines, None, None
    try:
        joined = join_directive(block, {'slots': [{'slot_id': p['post_id'], 'words': p['words']} for p in posts]},
                                config)
    except ValueError as exc:
        return lines, {'reason': 'GA4 rows could not be joined to the posts', 'detail': str(exc)}, None
    slots = joined['slots']
    tracked = [s for s in slots if s['utm_content']]
    measured = [s for s in tracked if s['sessions'] is not None]

    def outcome(key):
        values = [s[key]['value'] for s in measured]
        if not measured:
            return 'not joined'
        if any(v is None for v in values):
            reason = next(s[key]['reason'] for s in measured if s[key]['value'] is None)
            return 'not counted (' + str(reason)[:160] + ')'
        return str(sum(values))

    lines.append('GA4 joined on utm_content: ' + str(len(tracked)) + ' of ' + str(len(slots)) + ' posts carry a tracked own link; '
                 + str(sum(s['sessions'] for s in measured)) + ' sessions on them; sign-ups ' + outcome('sign_ups')
                 + '; paid subscriptions ' + outcome('paid_subscriptions') + '; coverage '
                 + ('complete' if joined['coverage']['complete'] else 'incomplete'))
    return lines, None, joined


def build(posts_read, block, now, root, mode, config, directive_pulled):
    """The report and its work error. posts_read is buffer_reads.sent_posts output, or a {'note'} or {'error'}."""
    activity, holds, work_error = [], [], None
    if directive_pulled:
        activity.append({'line': "Pulled today's directive before reading any source"})
    posts = posts_read.get('posts') or []
    if 'note' in posts_read:
        holds.append({'reason': posts_read['note'], 'detail': 'Measured the GA4 part only; set BUFFER_API_KEY for posts'})
    if 'error' in posts_read:
        holds.append({'reason': 'Buffer could not be read', 'detail': posts_read['error']})
        work_error = 'buffer_read_failed'
    for item in posts_read.get('held', []):
        holds.append({'reason': 'Buffer channel not pinned', 'detail': item['channel'] + ': ' + item['reason']})
    results, channels = verdicts(posts, now)
    counts = tally(results)
    if 'listed' in posts_read:
        activity.append({'line': 'Read ' + str(len(posts)) + ' sent posts from Buffer on ' + str(len(channels)) + ' of '
                         + str(len(BUFFER_NAME)) + ' pinned channels over the last ' + str(LOOKBACK_DAYS) + ' days ('
                         + str(posts_read['imported']) + ' imported posts left unjudged, '
                         + str(posts_read['get_post_reads']) + ' per-post reads)'})
        quiet = [m['channel'] for m in posts_read.get('missing', [])]
        if quiet:
            activity.append({'line': 'No sent posts seen on: ' + ', '.join(quiet)})
    for cid, info in sorted(channels.items()):
        activity.append({'line': cid + ': ' + count(info['posts'], 'post') + ', judged on ' + str(info['indicator'] or 'no metric')
                         + ' at ' + str(info['window_hours']) + ' hours, channel median '
                         + ('not available' if info['median'] is None else str(info['median'])) + ' over '
                         + count(info['mature'], 'settled post') + ('; baseline, new channel' if info['new'] else '')
                         + '; ' + ', '.join(k + ' ' + str(v) for k, v in info['verdicts'].items())})
    activity.append({'line': 'Verdicts against each post\'s own channel median: '
                     + ', '.join(k + ' ' + str(v) for k, v in counts.items())
                     + '. Association, not cause; bands are proposed defaults for Krish at G-A'})
    activity += [{'line': line} for line in share_part(posts)[0]]
    lines, hold, joined = ga4_part(block, posts, config)
    activity += [{'line': line} for line in lines]
    if hold:
        holds.append(hold)
    activity.append({'line': web_analytics_activity(web_analytics_summary(block))})
    activity.append({'line': meter.cost_line('before this report')})
    activity.append({'line': 'Posted, sent, published and spent nothing'})
    objectives = [objective('new_subscribers', reason=NOT_MEASURED), objective('paid_boosts_usd', reason=NO_SPEND)]
    status = 'degraded' if work_error or hold else ('ready' if posts or joined else 'held')
    if status == 'held' and not holds:
        holds.append({'reason': 'Nothing to measure this run', 'detail': None})
    report = build_report(run_id(now), mode, now, revision(root), now, status, objectives, activity, [], [], holds,
                          post_metrics=post_metrics(posts, now) or None)
    return report, work_error, counts


def read_buffer(client, note, now):
    if client is None:
        return {'note': note}
    try:
        return buffer_reads.sent_posts(client, instant(now) - dt.timedelta(days=LOOKBACK_DAYS), now)
    except Exception as exc:  # an outside module: keep only its name or code, never its words
        code = getattr(exc, 'code', None)
        return {'error': (code if isinstance(code, str) and code.isidentifier() else type(exc).__name__)}


def main(argv=None, make_client=None, buffer=None, out=print, root=ROOT, environ=None):
    parser = argparse.ArgumentParser(prog='growth.py run measure auto', description=__doc__.split('\n')[0])
    parser.add_argument('--deliver', action='store_true')
    parser.add_argument('--mode', choices=('live', 'synthetic'), default='live')
    parser.add_argument('--now')
    args = parser.parse_args(argv)
    root = Path(root)
    clock = (lambda: instant(args.now)) if args.now else (lambda: instant())
    now = clock()
    client, note = buffer if buffer is not None else buffer_reads.buffer_client(environ)
    if note == buffer_reads.NOT_CONFIGURED:
        out('Buffer not configured: measuring the GA4 part only')
    elif note:
        out(note + ': measuring the GA4 part only')
    config = load_config(root)
    seen = {}

    def work(directive, pulled):
        block = web_analytics_block(directive) if pulled else _local_block(root)
        if pulled:
            keep_web_analytics(root, directive)
        report, error, counts = build(read_buffer(client, note, clock()), block, clock(), root, args.mode, config, pulled)
        seen['counts'] = counts
        return report, error

    if not args.deliver:
        report, error = work(None, False)
        write_json(root / STATE_DIR / 'report-measure.json', report)
        out(_counts_line(seen['counts']))
        out('Dry run: report ' + report['status'] + ', payload_sha256 ' + report['payload_sha256'] + '; written to '
            + str(STATE_DIR / 'report-measure.json') + '; no Control Center call')
        out(meter.cost_line('in all'))
        return int(bool(error))
    if make_client is None:
        import growth
        make_client = growth.engine_client
    cc = make_client()
    outcome = run(cc, COMMAND, run_id(now), lambda d: work(d, True), now - dt.timedelta(days=7), clock)
    if outcome.get('report'):
        write_json(root / STATE_DIR / 'report-measure.json', outcome['report'])
    if 'counts' in seen:
        out(_counts_line(seen['counts']))
    for line in summary(outcome, public=True):
        out(line)
    out(meter.cost_line('in all'))
    return int(outcome['status'] != 'succeeded')


def _local_block(root):
    path = Path(root) / STATE_DIR / WEB_ANALYTICS_FILE
    return read_json(path) if path.is_file() else None


def _counts_line(counts):
    return 'measure: ' + ' '.join(k + '=' + str(counts[k]) for k in VERDICTS)


if __name__ == '__main__':
    sys.exit(main())
