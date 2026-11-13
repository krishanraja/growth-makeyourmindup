"""The source clock: which post brought a subscriber, from the counts Buffer already shows (growth-source-clock/1).

Buffer shows each Substack Note's `freeSubscriptions` and `reposts`, and each post's reach, views, clicks,
follows, shares and saves (engine/run/buffer_reads.py metric_values). Until 13 November the measure job read
them and dropped every count but reach, sends, saves, likes and comments, because Control Center's
`post_metrics` schema is closed (protocol 1.17.0). So the one subscriber a Note brought on 4 November was in
Buffer and nowhere in this engine's record.

The measure job now keeps those counts as a record of their own, riding a live report at
`makeyourmindup:sourceclock:<YYYY-MM-DD>-<HHMMZ>` (engine/run/cc_records.py record_report): no protocol
change, and `post_metrics` stays schema-valid. Each run's record is the whole lookback (56 days), so the first
run is the backfill of every post Buffer still lists.

Counts only. A record holds Buffer post ids, this engine's channel names, sent times and whole counts; any
entry with anything else (an id that is not a plain id, a field not listed here, a count that is not a whole
number) is left out, and the record is refused if any string in it could be an address. Nothing here reads
subscribers, emails or Substack notices. Read-only: nothing posts, sends, publishes or spends.
"""
import re

from ..control_center import SLUG, canonical_json, iso
from ..core import instant, today
from . import cc_records

SCHEMA = 'growth-source-clock/1'
# The counts kept, in the order a reader sees them. Substack Notes show the first five.
COUNTS = ('freeSubscriptions', 'paidSubscriptions', 'reposts', 'impressions', 'reach', 'views', 'clicks',
          'follows', 'shares', 'saves')
MAX_POSTS = 60  # newest first; older posts drop off before the record outgrows one report
POST_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
ADDRESS = re.compile(r'@|%40|mailto:', re.IGNORECASE)
NOTES = 'substack-notes'


def run_id(now):
    return SLUG + ':sourceclock:' + today(now) + '-' + instant(now).strftime('%H%MZ')


def _whole(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or value > 10 ** 10 or not float(value).is_integer():
        return None
    return int(value)


def entry(post):
    """One post's counts, or None when it cannot be kept as counts only."""
    pid, channel = post.get('post_id'), post.get('channel')
    if not isinstance(pid, str) or not POST_ID.match(pid) or not isinstance(channel, str) or not POST_ID.match(channel):
        return None
    metrics = post.get('metrics')
    if not isinstance(metrics, dict):
        return None
    counts = {}
    for key in COUNTS:
        value = _whole(metrics.get(key))
        if value is not None:
            counts[key] = value
    if not counts:
        return None
    try:
        sent_at = iso(instant(post['sent_at']))
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return {'post_id': pid, 'channel': channel, 'sent_at': sent_at, 'counts': counts}


def totals(entries):
    """Sums per channel over the posts that show each count; a count no post shows is absent, never zero."""
    out = {}
    for item in entries:
        row = out.setdefault(item['channel'], {'posts': 0})
        row['posts'] += 1
        for key, value in item['counts'].items():
            row[key] = row.get(key, 0) + value
    return dict(sorted(out.items()))


def record(posts, now):
    """The source clock record for these posts (buffer_reads.sent_posts' `posts`), newest first.

    Older posts are dropped until the record fits one report; `dropped` says how many."""
    kept = [e for e in (entry(p) for p in posts or []) if e]
    kept.sort(key=lambda e: e['sent_at'], reverse=True)
    left_out = len(posts or []) - len(kept)
    kept, dropped = kept[:MAX_POSTS], max(0, len(kept) - MAX_POSTS)
    while True:
        value = {'schema': SCHEMA, 'measured_at': iso(instant(now)), 'posts': kept, 'totals': totals(kept),
                 'dropped_oldest': dropped, 'left_out': left_out}
        if cc_records.fits(SCHEMA, value) or not kept:
            break
        kept, dropped = kept[:-1], dropped + 1
    if ADDRESS.search(canonical_json(value)):
        raise ValueError('source_clock_identity')  # never reached by Buffer ids and counts; a guard, not a filter
    return value


def line(value):
    """One counts-only line for the measure report and log."""
    notes = value['totals'].get(NOTES)
    if not notes:
        return 'Source clock: no Substack Note with counts in the lookback; ' + str(len(value['posts'])) \
            + ' posts kept with their counts (' + SCHEMA + ')'
    return ('Source clock (Buffer per-post counts, ' + SCHEMA + '): ' + str(notes['posts']) + ' Notes, '
            + str(notes.get('impressions', 'not shown')) + ' impressions, '
            + str(notes.get('freeSubscriptions', 'not shown')) + ' free subscriptions, '
            + str(notes.get('reposts', 'not shown')) + ' reposts; ' + str(len(value['posts']))
            + ' posts kept in all')


def report(posts, now, revision):
    """The live report carrying this run's record, ready for cc.post_report, or None with no post to keep."""
    value = record(posts, now)
    if not value['posts']:
        return None
    return cc_records.record_report(run_id(now), SCHEMA, value,
                                    ['Source clock: per-post counts Buffer shows, kept as counts only',
                                     'Read Buffer only; posted, sent, published and spent nothing'],
                                    now, revision)
