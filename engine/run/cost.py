"""Phase 0 cost baseline and meter from local agent session logs.

Reads Codex CLI rollout files and Claude Code transcripts, read-only. The
result carries aggregates only: token counts, call counts and minutes per
session and per job kind, the repository name and model names. No message
text and no paths, so it is safe to commit. The formats drift, so unknown or
unparseable lines are counted and reported; a value is never guessed.
"""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys

from ..core import calendar_date, ny_time, read_json, write_json

SCHEMA = 'growth-cost-baseline/1'
JOB = re.compile(r'\bRun jobs/([A-Za-z0-9_-]+)\.md\b')
STAMP = re.compile(r'^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})$')
CODEX_TYPES = {'session_meta', 'turn_context', 'event_msg', 'response_item', 'compacted'}
CODEX_USAGE = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens')
CODEX_KINDS = {'input_tokens': 'input', 'cached_input_tokens': 'cached_input', 'output_tokens': 'output',
               'reasoning_output_tokens': 'reasoning_output', 'total_tokens': 'total'}
CLAUDE_TYPES = {'user', 'assistant', 'system', 'summary', 'file-history-snapshot', 'queue-operation'}
CLAUDE_USAGE = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')
CLAUDE_KINDS = {'input_tokens': 'input', 'cache_creation_input_tokens': 'cache_creation_input',
                'cache_read_input_tokens': 'cache_read_input', 'output_tokens': 'output'}
TOOL_CALLS = {'function_call', 'custom_tool_call'}
TOOL_OUTPUTS = {'function_call_output', 'custom_tool_call_output'}


def stamp(value):
    """Offset-bearing ISO timestamp, any fraction length; None when it is not one."""
    if not isinstance(value, str):
        return None
    match = STAMP.match(value.strip())
    if not match:
        return None
    day, clock, fraction, zone = match.groups()
    zone = '+00:00' if zone == 'Z' else zone if ':' in zone else zone[:3] + ':' + zone[3:]
    try:
        value = dt.datetime.fromisoformat(day + 'T' + clock + '.' + (fraction or '')[:6].ljust(6, '0') + zone)
    except ValueError:
        return None
    return value.astimezone(dt.timezone.utc)


def usage(value, keys):
    """Every present key a non-negative whole number, or None (counted unknown)."""
    if not isinstance(value, dict):
        return None
    out = {}
    for key in keys:
        if key not in value or value[key] is None:
            continue
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            return None
        out[key] = item
    return out if out else None


def minutes(seconds):
    return round(seconds / 60, 2)


def lines(path):
    """Yield (parsed, ok) per line; undecodable or non-JSON lines are not ok."""
    with open(path, 'rb') as handle:
        for raw in handle:
            if not raw.strip():
                continue
            try:
                yield json.loads(raw.decode('utf-8-sig')), True
            except (UnicodeDecodeError, ValueError):
                yield None, False


class Session:
    def __init__(self, tool):
        self.tool = tool
        self.cwd = None
        self.models = set()
        self.first_prompt = None
        self.tokens = {}
        self.calls = 0
        self.context = 0
        self.lines = self.unparseable = self.unknown = 0
        self.engine = self.wait = self.tool_seconds = 0.0
        self.started = None
        self.allowance = None
        self.events = []  # (time, 'prompt' | 'activity' | 'start' | 'complete')
        self.tool_open = {}

    def seen(self, when):
        if when and (self.started is None or when < self.started):
            self.started = when

    def prompt(self, text, when):
        if self.first_prompt is None and isinstance(text, str):
            match = JOB.search(text)
            self.first_prompt = match.group(1) if match else 'interactive'
        if when:
            self.events.append((when, 'prompt'))

    def tool_start(self, call_id, when):
        if call_id and when:
            self.tool_open[call_id] = when

    def tool_end(self, call_id, when):
        start = self.tool_open.pop(call_id, None) if call_id else None
        if start and when and when >= start:
            self.tool_seconds += (when - start).total_seconds()

    def clocks(self):
        """Engine and wait-for-human time, kept as separate clocks."""
        events = sorted(self.events, key=lambda e: e[0])
        if any(kind == 'start' for _, kind in events):
            opened = done = None
            for when, kind in events:
                if kind == 'start':
                    opened = when
                elif kind == 'complete' and opened:
                    self.engine += (when - opened).total_seconds()
                    opened, done = None, when
                elif kind == 'prompt' and done:
                    self.wait += (when - done).total_seconds()
                    done = None
            return
        # No task markers: each turn runs from its prompt (or first activity)
        # to its last activity; the wait runs from there to the next prompt.
        begun = last = None
        for when, kind in events:
            if kind == 'prompt':
                if begun and last:
                    self.engine += (last - begun).total_seconds()
                    self.wait += (when - last).total_seconds()
                begun, last = when, None
            elif kind == 'activity':
                begun = begun or when
                last = when
        if begun and last:
            self.engine += (last - begun).total_seconds()

    def report(self):
        tokens = {kind: self.tokens.get(key) for key, kind in
                  (CODEX_KINDS if self.tool == 'codex' else CLAUDE_KINDS).items() if key in self.tokens}
        if self.tool == 'claude' and tokens:
            tokens['total'] = sum(tokens.values())
        return {'tool': self.tool, 'started_at': self.started.isoformat() if self.started else None,
                'job_kind': self.first_prompt or 'interactive', 'models': sorted(self.models),
                'model_calls': self.calls, 'tokens': tokens or None,
                'mean_context': round(self.context / self.calls) if self.calls else None,
                'context_tokens': self.context,
                'engine_minutes': minutes(self.engine), 'wait_for_human_minutes': minutes(self.wait),
                'tool_minutes': minutes(self.tool_seconds),
                'lines': self.lines, 'unparseable_lines': self.unparseable, 'unknown_lines': self.unknown}


def codex_session(path):
    s = Session('codex')
    total = None
    summed = {}
    for row, ok in lines(path):
        s.lines += 1
        if not ok:
            s.unparseable += 1
            continue
        kind = row.get('type') if isinstance(row, dict) else None
        payload = row.get('payload') if isinstance(row, dict) else None
        if kind not in CODEX_TYPES or not isinstance(payload, dict):
            s.unknown += 1
            continue
        when = stamp(row.get('timestamp'))
        s.seen(when)
        if kind in ('session_meta', 'turn_context'):
            if isinstance(payload.get('cwd'), str) and s.cwd is None:
                s.cwd = payload['cwd']
            if isinstance(payload.get('model'), str):
                s.models.add(payload['model'])
            continue
        if kind == 'compacted':
            continue
        sub = payload.get('type')
        if kind == 'response_item':
            if sub in TOOL_CALLS:
                s.tool_start(payload.get('call_id'), when)
                if when:
                    s.events.append((when, 'activity'))
            elif sub in TOOL_OUTPUTS:
                s.tool_end(payload.get('call_id'), when)
            continue
        if sub == 'token_count':
            info = payload.get('info')
            if info is not None:
                last = usage(info.get('last_token_usage') if isinstance(info, dict) else None, CODEX_USAGE)
                whole = usage(info.get('total_token_usage') if isinstance(info, dict) else None, CODEX_USAGE)
                if last is None and whole is None:
                    s.unknown += 1
                    continue
                if last is not None:
                    s.calls += 1
                    s.context += last.get('input_tokens', 0)
                    for key, value in last.items():
                        summed[key] = summed.get(key, 0) + value
                if whole is not None and (total is None or whole.get('total_tokens', 0) >= total.get('total_tokens', 0)):
                    total = whole
            limits = payload.get('rate_limits')
            if limits is not None:
                s.allowance = allowance(limits, when) or s.allowance
            if when:
                s.events.append((when, 'activity'))
        elif sub == 'user_message':
            s.prompt(payload.get('message'), when)
        elif sub == 'agent_message':
            if when:
                s.events.append((when, 'activity'))
        elif sub in ('task_started', 'task_complete'):
            if when:
                s.events.append((when, 'start' if sub == 'task_started' else 'complete'))
        elif not isinstance(sub, str):
            s.unknown += 1
    # The cumulative total is the authority; summed last usages only fill a gap.
    s.tokens = total or summed
    s.clocks()
    return s


def allowance(limits, when):
    if not isinstance(limits, dict) or not when:
        return None
    out = {'read_at': when.isoformat(), 'source': 'codex rollout rate_limits'}
    for name in ('primary', 'secondary'):
        part = limits.get(name)
        if not isinstance(part, dict):
            continue
        used = part.get('used_percent')
        if isinstance(used, bool) or not isinstance(used, (int, float)) or not math.isfinite(used) or not 0 <= used <= 100:
            continue
        out[name + '_used_percent'] = used
        window = part.get('window_minutes')
        out[name + '_window_minutes'] = window if type(window) is int and window > 0 else None
        reset = part.get('resets_in_seconds')
        epoch = part.get('resets_at')
        if type(reset) is int and reset >= 0:
            out[name + '_resets_at'] = (when + dt.timedelta(seconds=reset)).isoformat()
        elif type(epoch) is int and epoch > 0:
            out[name + '_resets_at'] = dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat()
        else:
            out[name + '_resets_at'] = None
    return out if 'primary_used_percent' in out else None


def claude_text(message):
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, str):
        return content, []
    if not isinstance(content, list):
        return None, []
    texts = [b.get('text') for b in content if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str)]
    results = [b.get('tool_use_id') for b in content if isinstance(b, dict) and b.get('type') == 'tool_result']
    return ('\n'.join(texts) if texts else None), results


def claude_session(path):
    s = Session('claude')
    usages = {}
    anonymous = []
    for row, ok in lines(path):
        s.lines += 1
        if not ok:
            s.unparseable += 1
            continue
        kind = row.get('type') if isinstance(row, dict) else None
        if kind not in CLAUDE_TYPES:
            s.unknown += 1
            continue
        if isinstance(row.get('cwd'), str) and s.cwd is None:
            s.cwd = row['cwd']
        when = stamp(row.get('timestamp'))
        s.seen(when)
        message = row.get('message')
        sidechain = row.get('isSidechain') is True
        if kind == 'user':
            text, results = claude_text(message)
            for call_id in results:
                s.tool_end(call_id, when)
            if text is not None and not results and not sidechain and row.get('isMeta') is not True:
                s.prompt(text, when)
        elif kind == 'assistant':
            if not isinstance(message, dict):
                s.unknown += 1
                continue
            if isinstance(message.get('model'), str) and not message['model'].startswith('<'):
                s.models.add(message['model'])
            if 'usage' in message:
                found = usage(message['usage'], CLAUDE_USAGE)
                if found is None:
                    s.unknown += 1
                elif isinstance(message.get('id'), str):
                    usages[message['id']] = found  # one response is split over lines; keep its last
                else:
                    anonymous.append(found)
            content = message.get('content')
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    s.tool_start(block.get('id'), when)
            if when and not sidechain:
                s.events.append((when, 'activity'))
    for found in list(usages.values()) + anonymous:
        s.calls += 1
        s.context += sum(found.get(k, 0) for k in CLAUDE_USAGE if k != 'output_tokens')
        for key, value in found.items():
            s.tokens[key] = s.tokens.get(key, 0) + value
    s.clocks()
    return s


def default_dirs():
    home = os.path.expanduser('~')
    if os.name == 'nt' and os.environ.get('USERPROFILE'):
        home = os.environ['USERPROFILE']
    codex = os.environ.get('CODEX_HOME') or os.path.join(home, '.codex')
    claude = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(home, '.claude')
    return os.path.join(codex, 'sessions'), os.path.join(claude, 'projects')


def in_repo(cwd, repo):
    return repo.casefold() in cwd.replace('\\', '/').casefold()


def baseline(codex_dir=None, claude_dir=None, repo='growth-makeyourmindup', since=None, verified_posts=None):
    if not isinstance(repo, str) or not repo.strip() or '/' in repo or '\\' in repo:
        raise ValueError('repo must be a bare repository name')
    since = calendar_date(since) if since else None
    default_codex, default_claude = default_dirs()
    sources = [('codex', Path(codex_dir or default_codex), 'rollout-*.jsonl', codex_session),
               ('claude', Path(claude_dir or default_claude), '*.jsonl', claude_session)]
    totals = {'lines': 0, 'unparseable': 0, 'unknown': 0}
    files, outside, no_cwd, earlier = {}, 0, 0, 0
    found = {}
    sessions, latest = [], None
    for tool, folder, pattern, read in sources:
        paths = sorted(folder.rglob(pattern)) if folder.is_dir() else []
        files[tool] = len(paths)
        found[tool] = folder.is_dir()
        for path in paths:
            try:
                s = read(path)
            except OSError:
                totals['unparseable'] += 1
                continue
            totals['lines'] += s.lines
            totals['unparseable'] += s.unparseable
            totals['unknown'] += s.unknown
            reading = s.allowance
            if reading and (latest is None or reading['read_at'] > latest['read_at']):
                latest = reading  # account-wide, so read from every session
            if s.cwd is None:
                no_cwd += 1
            elif not in_repo(s.cwd, repo):
                outside += 1
            elif since and (s.started is None or ny_time(s.started).date() < since):
                earlier += 1
            else:
                sessions.append(s.report())
    sessions.sort(key=lambda r: (r['started_at'] or '', r['tool']))
    kinds = {}
    for row in sessions:
        agg = kinds.setdefault(row['job_kind'], {'sessions': 0, 'tools': {}, 'model_calls': 0, 'tokens': {},
                                                 'context_tokens': 0, 'engine_minutes': 0.0,
                                                 'wait_for_human_minutes': 0.0, 'tool_minutes': 0.0})
        agg['sessions'] += 1
        agg['tools'][row['tool']] = agg['tools'].get(row['tool'], 0) + 1
        agg['model_calls'] += row['model_calls']
        agg['context_tokens'] += row['context_tokens']
        for key, value in (row['tokens'] or {}).items():
            agg['tokens'][key] = agg['tokens'].get(key, 0) + value
        for key in ('engine_minutes', 'wait_for_human_minutes', 'tool_minutes'):
            agg[key] = round(agg[key] + row[key], 2)
    for agg in kinds.values():
        agg['mean_context'] = round(agg.pop('context_tokens') / agg['model_calls']) if agg['model_calls'] else None
    per_post = None
    if verified_posts is not None:
        per_post = {}
        for kind, posts in sorted(verified_posts.items()):
            agg = kinds.get(kind)
            entry = {'verified_posts': posts, 'tokens_per_post': None, 'engine_minutes_per_post': None}
            if not agg:
                entry['reason'] = 'no sessions of this job kind'
            elif not posts:
                entry['reason'] = 'no verified posts'
            else:
                if 'total' in agg['tokens']:
                    entry['tokens_per_post'] = round(agg['tokens']['total'] / posts)
                entry['engine_minutes_per_post'] = round(agg['engine_minutes'] / posts, 2)
                entry['reason'] = None
            per_post[kind] = entry
    return {'schema': SCHEMA, 'repo': repo, 'since': since.isoformat() if since else None,
            'logs_found': found, 'files_read': files, 'lines': totals,
            'sessions_counted': len(sessions), 'sessions_outside_repo': outside,
            'sessions_without_cwd': no_cwd, 'sessions_before_since': earlier,
            'by_job_kind': dict(sorted(kinds.items())), 'sessions': sessions,
            'allowance': latest, 'per_verified_post': per_post,
            'note': ('Aggregates only: no message text and no paths. Codex input includes cached input; '
                     'Claude input, cache creation and cache reads are separate. Unknown lines are counted, '
                     'never estimated.')}


def verified(path):
    value = read_json(path)
    if not isinstance(value, dict) or any(not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int)
                                          or v < 0 for k, v in value.items()):
        raise ValueError('verified posts must map job kind to a non-negative whole number')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    cost = sub.add_parser('cost').add_subparsers(dest='action', required=True)
    b = cost.add_parser('baseline')
    b.add_argument('--codex-dir'); b.add_argument('--claude-dir')
    b.add_argument('--repo', default='growth-makeyourmindup'); b.add_argument('--since')
    b.add_argument('--verified-posts'); b.add_argument('--out')
    args = parser.parse_args(argv)
    try:
        result = baseline(args.codex_dir, args.claude_dir, args.repo, args.since,
                          verified(args.verified_posts) if args.verified_posts else None)
    except (ValueError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
    if args.out:
        write_json(args.out, result)
        print('cost baseline written locally: ' + args.out + '; aggregates only')
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
