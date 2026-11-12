"""`growth.py run learn [--now TIME]`: last judged week's posts, judged by subscribers, for `mix learn`.

Ruling (Krish, 2026-11-12): the engine reads subscribers every week and judges posts by subscribers, not
engagement. The learn workflow (.github/workflows/learn.yml, Sundays 10:30 UTC, before next week's mix
plan is made that day) runs this, then `growth.py mix learn --verdicts`, and commits the learn file
lists/mix-learn/for-<next Monday>.json, which `growth.py mix plan` reads for that week (engine/mix.py).

The judged week is the latest New York week whose posts have all had their seven days: on a Sunday, the
week that ended a week ago. For each post this engine sent that week on its pinned Buffer channels:

1. its verdict by subscribers, exactly as the measure job gives it (measure_auto.subscriber_verdicts: the
   GA4 sign-ups on its own utm_content over its first seven days, from Control Center's web_analytics);
2. its concept, by its Buffer id in that week's derived index in Control Center (the maker's
   `growth-derived-index/1` records, autorelease.week_entries), and so its lane (mix.lane_of).

A post that is not in the index was not made from the week's mix, so it is counted and left out of the
lanes. Reads only: Buffer's sent posts, today's directive and Control Center's records. It writes one
local file under .scratch/learn/ and prints counts and codes only, never a word, URL, id or figure: this
repository and its Actions logs are public. Nothing here posts, sends, publishes or spends.
"""
import argparse
import datetime as dt
from pathlib import Path
import sys

from ..cc_loop import web_analytics_block
from ..core import instant, ny_time, write_json
from .. import mix
from . import buffer_reads
from .ga4 import load_config
from .measure import monday
from .measure_auto import VERDICTS, subscriber_verdicts

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = Path('.scratch') / 'learn'


def weeks(now):
    """(judged Monday, plan Monday): the latest week whose every post has had its seven days, and the week
    whose plan the learning feeds (the next Monday)."""
    day = ny_time(now).date()
    judged = monday(day - dt.timedelta(days=13))
    return judged, monday(day) + dt.timedelta(days=7)


def verdict_rows(posts, block, config, entries, judged, now):
    """The judged week's posts with their subscriber verdict and, where the index has it, their concept."""
    end = judged + dt.timedelta(days=6)
    week = [p for p in posts if judged <= ny_time(p['sent_at']).date() <= end]
    results = subscriber_verdicts(week, now, block, config)
    by_draft = {e['buffer_draft_id']: e for e in entries or []}
    rows = []
    for post in week:
        entry = by_draft.get(post['post_id'])
        result = results[post['post_id']]
        rows.append({'post_id': post['post_id'], 'channel': post['channel'],
                     'concept_id': entry['concept_id'] if entry else None, 'verdict': result['verdict'],
                     'code': result['code']})
    return rows


def build(posts_read, directive, entries, now, root=ROOT):
    """The growth-learn-verdicts/1 document, or ValueError naming what could not be read."""
    if 'error' in posts_read:
        raise ValueError('buffer_read_failed: ' + str(posts_read['error']))
    if 'note' in posts_read:
        raise ValueError('buffer_not_configured: ' + str(posts_read['note']))
    if entries is None:
        raise ValueError('derived_index_unreadable')
    judged, plan_week = weeks(now)
    rows = verdict_rows(posts_read.get('posts') or [], web_analytics_block(directive), load_config(root), entries,
                        judged, now)
    channels = mix.load(root)['channels']
    mixed = [r for r in rows if r['concept_id'] is not None and r['channel'] in channels]
    return {'schema': mix.VERDICTS_SCHEMA, 'basis': 'subscribers', 'for_week_of': plan_week.isoformat(),
            'judged_week_of': judged.isoformat(), 'made_at': instant(now).isoformat(), 'rows': mixed,
            'counts': {'posts_in_week': len(rows), 'from_the_mix': len(mixed),
                       'not_from_the_mix': len(rows) - len(mixed)},
            'local_only': True}


def read_entries(cc, judged):
    from .autorelease import week_entries
    holds = {}
    entries = week_entries(cc, judged.isoformat(), holds)
    return entries, holds


def main(argv=None, buffer=None, make_client=None, out=print, root=ROOT, environ=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog='growth.py run learn', description=__doc__.split('\n')[0])
    parser.add_argument('--now'); parser.add_argument('--out')
    args = parser.parse_args(argv[1:] if argv and argv[0] == 'learn' else argv)
    now = instant(args.now)
    judged, plan_week = weeks(now)
    root = Path(root)
    client, note = buffer if buffer is not None else buffer_reads.buffer_client(environ)
    if client is None:
        posts_read = {'note': note}
    else:
        start = dt.datetime.combine(judged, dt.time(0), ny_time(now).tzinfo)
        try:
            posts_read = buffer_reads.sent_posts(client, start - dt.timedelta(days=1), now)
        except Exception as exc:  # an outside module: keep only its name or code, never its words
            code = getattr(exc, 'code', None)
            posts_read = {'error': code if isinstance(code, str) and code.isidentifier() else type(exc).__name__}
    if make_client is None:
        import growth
        make_client = growth.engine_client
    try:
        cc = make_client()
    except ValueError:  # its message names where the key goes; the log names the code only
        out('learn: not written; engine_key_missing')
        return 1
    try:
        directive = cc.directive()
        entries, holds = read_entries(cc, judged)
        doc = build(posts_read, directive, entries, now, root)
    except Exception as exc:  # the log stays counts and codes: a code or a class name, never a message body
        code = getattr(exc, 'code', None)
        head = str(exc).split(':')[0] if isinstance(exc, ValueError) else ''
        why = (code if isinstance(code, str) and code.isidentifier()
               else head if head.isidentifier() and head.islower() else type(exc).__name__)
        out('learn: not written; ' + why)
        return 1
    path = Path(args.out) if args.out else root / SCRATCH / ('verdicts-for-' + doc['for_week_of'] + '.json')
    write_json(path, doc)
    tally = dict.fromkeys(VERDICTS, 0)
    for row in doc['rows']:
        tally[row['verdict']] += 1
    out('learn: week of ' + doc['judged_week_of'] + ' for the plan of ' + doc['for_week_of'] + '; '
        + str(doc['counts']['posts_in_week']) + ' posts, ' + str(doc['counts']['from_the_mix'])
        + ' from the mix; by subscribers ' + ' '.join(k + '=' + str(v) for k, v in tally.items())
        + ('; index holds ' + ','.join(sorted(holds)) if holds else ''))
    out('written locally to ' + str(path.relative_to(root) if path.is_relative_to(root) else path)
        + '; next: growth.py mix learn --verdicts')
    return 0


if __name__ == '__main__':
    sys.exit(main())
