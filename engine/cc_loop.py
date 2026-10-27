"""The daily Control Center loop for this engine.

Two entry points share one client (engine.control_center):
- the publication workspace, where the Codex automations in automations.json run: each
  job starts with `growth.py cc start --job KIND --deliver` and ends with
  `growth.py cc finish --job KIND ... --deliver`;
- the GitHub runner, woken by Control Center's `cc-growth-directive`
  dispatch: `growth.py cc runner --deliver` checks the engine offline and
  reports honestly what a clean runner can and cannot see.

Order every run: attempt started, directive, the work, report and readback,
decisions, attempt terminal. Nothing here posts, sends, publishes or spends.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from .control_center import (ENGINE_ID, SLUG, ProtocolError, action_key, build_report, golive_review, iso,
                             match_decisions, objective, proposal)
from .core import KINDS, UTC, http_url, instant, locked, ny_time, read_json, today, write_json
from .operations import aggregate, daily_queue, validate_observation

SECRET_ENV = ('CONTROL_CENTER_ENGINE_TOKEN', 'GROWTH_ENGINE_TOKEN')
STATE_DIR = Path('.scratch') / 'cc'
WORKSPACE_ONLY = 'Measured only in the publication workspace'
NO_SPEND = 'this engine has no spend authority, bought no boosts and does not read platform ad spend'
# Which wall each pack kind sits behind, and the event that closes it.
WALLS = {'daily': ('post', 'published'), 'radar': ('post', 'published'), 'conversion': ('post', 'applied'),
         'pitches': ('send', 'sent'), 'swaps': ('send', 'sent'), 'partners': ('send', 'sent'),
         'report': ('strategy', 'reviewed'), 'numbers': ('none', 'verified')}
# Outreach to shows, guests, swaps and partners is Control Center's: People and Visibility
# find, draft and track it (Ruling, Krish, 2026-10-21). That work is held, never proposed.
CONTROL_CENTER_OWNS = frozenset({'pitches', 'swaps', 'partners'})
OWNED_REASON = "Control Center's People and Visibility own outreach to shows and guests"
COMPLETIONS = {'Published': 'published', 'Sent': 'sent', 'Applied': 'applied',
               'Verified': 'verified', 'Reviewed': 'reviewed'}
NAMES = {'linkedin': 'LinkedIn', 'x': 'X', 'youtube': 'YouTube', 'tiktok': 'TikTok', 'seo': 'search',
         'substack': 'Substack', 'instagram': 'Instagram', 'spotify': 'Spotify', 'reddit': 'Reddit'}


def count(number, noun):
    return str(number) + ' ' + noun + ('' if number == 1 else 's')


def run_id_for(command, now=None):
    return SLUG + ':' + today(now) + ':' + command


def revision(root):
    value = os.environ.get('GITHUB_SHA', '').strip()
    if value:
        return value
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(root), capture_output=True,
                                text=True, timeout=10)
        if result.returncode == 0 and re.match(r'^[0-9a-f]{40}$', result.stdout.strip()):
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return 'unknown'


def week_start(now):
    """Monday 00:00 in New York, as a UTC instant."""
    local = ny_time(now)
    monday = local.date() - dt.timedelta(days=local.weekday())
    # Clock changes happen on Sundays, so Monday noon has Monday midnight's offset.
    offset = ny_time(dt.datetime(monday.year, monday.month, monday.day, 17, tzinfo=UTC)).utcoffset()
    return dt.datetime(monday.year, monday.month, monday.day, tzinfo=dt.timezone(offset)).astimezone(UTC)


# The loop -----------------------------------------------------------------

class Loop:
    def __init__(self, client, command, run_id, clock=None):
        self.client = client
        self.command = command
        self.run_id = run_id
        self.clock = clock or (lambda: instant())
        self.attempt_id = None
        self.started_at = None
        self.directive = None
        self.phase = 'start'
        self.journaled = False

    def state(self):
        return {'attempt_id': self.attempt_id, 'run_id': self.run_id, 'command': self.command,
                'started_at': self.started_at, 'directive': self.directive}

    @classmethod
    def resume(cls, client, state, clock=None):
        loop = cls(client, state['command'], state['run_id'], clock)
        loop.attempt_id, loop.started_at = state['attempt_id'], state['started_at']
        loop.directive, loop.journaled, loop.phase = state.get('directive'), True, 'work'
        return loop

    def start(self):
        """Journal the start before any source is read, then pull the directive."""
        now = self.clock()
        self.started_at = iso(now)
        self.attempt_id = self.run_id + ':' + instant(now).strftime('%Y%m%dT%H%M%SZ')
        self.client.attempt({'attempt_id': self.attempt_id, 'command': self.command, 'run_id': self.run_id,
                             'status': 'started', 'phase': 'start', 'error_code': None,
                             'started_at': self.started_at})
        self.journaled = True
        self.phase = 'directive'
        self.directive = self.client.directive()
        self.phase = 'work'
        return self.state()

    def end(self, status, error_code=None):
        result = {'status': status, 'error_code': error_code, 'phase': self.phase, 'attempt_journaled': False}
        if not self.journaled:
            return result
        record = {'attempt_id': self.attempt_id, 'command': self.command, 'run_id': self.run_id,
                  'status': status, 'phase': self.phase, 'error_code': error_code,
                  'started_at': self.started_at, 'finished_at': iso(self.clock())}
        try:
            self.client.attempt(record)
            result['attempt_journaled'] = True
        except ProtocolError as error:
            result['attempt_error'] = error.code
        return result

    def finish(self, build, since):
        """build(directive) returns (report, error_code or None)."""
        outcome = {}
        try:
            self.phase = 'work'
            report, work_error = build(self.directive)
            outcome['report'] = report
            self.phase = 'report'
            posted = self.client.post_report(report)
            outcome['posted'] = posted
            if posted['conflict']:
                # The same run_id already holds a different payload. Never
                # resend: the stored report stands, and the attempt says so.
                outcome.update(self.end('failed', 'report_conflict'))
                return outcome
            self.phase = 'decisions'
            outcome['decisions'] = self.client.decisions(since)
            self.phase = 'done'
            outcome.update(self.end('failed', work_error) if work_error else self.end('succeeded'))
        except ProtocolError as error:
            outcome.update(self.end('failed', error.code))
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            outcome.update(self.end('failed', 'work_failed' if self.phase == 'work' else 'internal_error'))
        return outcome


def run(client, command, run_id, build, since, clock=None):
    loop = Loop(client, command, run_id, clock)
    try:
        loop.start()
    except ProtocolError as error:
        result = loop.end('failed', error.code)
        return result
    return loop.finish(build, since)


# The GitHub runner --------------------------------------------------------

def clean_env():
    return {key: value for key, value in os.environ.items() if key not in SECRET_ENV}


def runner_checks(root):
    """Run the engine's own offline checks in child processes that never see a key."""
    results = []
    with tempfile.TemporaryDirectory() as folder:
        for name, args in (('self_test', ['--self-test']), ('doctor_offline', ['doctor', '--offline']),
                           ('dry_run', ['dry-run', '--out', folder])):
            try:
                done = subprocess.run([sys.executable, str(Path(root) / 'growth.py')] + args, cwd=str(root),
                                      env=clean_env(), capture_output=True, text=True, timeout=900)
                results.append({'name': name, 'ok': done.returncode == 0, 'stdout': done.stdout, 'stderr': done.stderr})
            except (OSError, subprocess.SubprocessError):
                results.append({'name': name, 'ok': False, 'stdout': '', 'stderr': 'could not run'})
    return results


def _tests_ran(check):
    found = re.search(r'Ran (\d+) tests?', check.get('stderr', '') + check.get('stdout', ''))
    return int(found.group(1)) if found else None


def experiment_proposals(root):
    out = []
    for exp in read_json(Path(root) / 'experiments.json')['experiments']:
        if exp.get('status') != 'planned':
            continue
        out.append(proposal(
            SLUG + ':experiment:' + exp['experiment_id'],
            'Decide whether to start the ' + exp['experiment_id'] + ' experiment',
            exp['hypothesis'] + ' Rule: ' + exp['decision_rule'], 'advice', 'strategy', 'experiment_started',
            objective_key='new_subscribers', reference=exp['experiment_id'], payload=exp))
    return out


def automation_count(root):
    """How many automations automations.json defines, or None when it cannot be read."""
    try:
        entries = read_json(Path(root) / 'automations.json')['automations']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return len(entries) if isinstance(entries, list) else None


def runner_report(root, run_id, now, checks, mode='live', directive_pulled=False, rev=None):
    root = Path(root)
    automations = automation_count(root)
    defined = 'the ' + str(automations) + ' ' if automations is not None else 'the '
    by_name = {c['name']: c for c in checks}
    failed = [c['name'] for c in checks if not c['ok']]
    activity = []
    if directive_pulled:
        activity.append({'line': "Pulled today's directive on the GitHub runner"})
    tests = by_name.get('self_test')
    if tests:
        count = _tests_ran(tests)
        activity.append({'line': 'Ran the unit tests on Python ' + '.'.join(map(str, sys.version_info[:2])) + ': '
                         + ('passed' if tests['ok'] else 'failed') + (' (' + str(count) + ' tests)' if count else '')})
    doctor = by_name.get('doctor_offline')
    if doctor:
        activity.append({'line': 'Checked ' + defined + 'automation definitions, job files and config offline: '
                         + ('ready' if doctor['ok'] else 'not ready')})
    dry = by_name.get('dry_run')
    if dry:
        line = 'Ran the offline fixture dry run: ' + ('passed' if dry['ok'] else 'failed')
        try:
            result = json.loads(dry['stdout'])
            line += (', ' + str(result['pieces_seen']) + ' fixture pieces, replay added '
                     + str(result['replay_new_tasks']) + ' tasks, ' + str(result['external_writes']) + ' external writes')
        except (ValueError, KeyError, TypeError):
            pass
        activity.append({'line': line})
    experiments = read_json(root / 'experiments.json')['experiments']
    channels = read_json(root / 'channels.json')['channels']
    journeys = read_json(root / 'journeys.json')['journeys']
    activity.append({'line': 'Read the committed plan: ' + str(len(channels)) + ' channels, ' + str(len(journeys))
                     + ' reader journeys, ' + str(len(experiments)) + ' experiment templates, '
                     + str(sum(e.get('status') == 'running' for e in experiments)) + ' running'})
    activity.append({'line': 'Posted, sent, published and spent nothing'})
    holds = [{'reason': 'Drafts and dashboard numbers are made only in the publication workspace',
              'detail': 'The automations defined in automations.json' + (' (' + str(automations) + ')' if automations is not None else '')
                        + ' draft and read dashboards there and report as their own runs; this runner checks the engine offline.'}]
    if failed:
        holds.append({'reason': 'Offline checks failed on the runner', 'detail': ', '.join(failed)})
    objectives = [
        objective('new_subscribers', reason=WORKSPACE_ONLY + '; a GitHub runner cannot read the Substack dashboard'),
        objective('paid_boosts_usd', reason=WORKSPACE_ONLY + '; ' + NO_SPEND)]
    report = build_report(run_id, mode, now, rev or revision(root), now, 'degraded' if failed else 'held',
                          objectives, activity, experiment_proposals(root), [], holds)
    return report, ('offline_checks_failed' if failed else None)


# The publication workspace ------------------------------------------------

ALL_SOURCES = 'publication'
SOURCE_PREFIX = 'source:'


def _in_week(row, start, now):
    """True inside this New York week, False outside it, None when the window is unreadable."""
    try:
        return instant(row['start']) >= start and instant(row['end']) <= instant(now)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _substack_week(observations, now):
    """All Substack new-free rows, this week's, the unreadable ones and the week's start."""
    rows = [r for r in observations or [] if isinstance(r, dict)
            and r.get('platform') == 'substack' and r.get('metric') == 'new_free']
    start = week_start(now)
    placed = [(r, _in_week(r, start, now)) for r in rows]
    return rows, [r for r, inside in placed if inside], [r for r, inside in placed if inside is None], start


def new_subscribers(observations, now):
    """This New York week's all-source new free subscribers (Krish owns the metric).

    Scope 'publication' is the all-source reading; 'source:<name>' is one
    source. Without an all-source row, per-source rows are added within each
    source and the sources summed, which means the same. Both together would
    count people twice, so the all-source reading wins. Any other scope (a post,
    say) is not a part of the sum, so the week is missing, never guessed."""
    rows, current, unreadable, start = _substack_week(observations, now)
    if not rows:
        return objective('new_subscribers', reason='No Substack new-subscriber reading was supplied to this run; '
                                                   'the numbers job reads it from the dashboard')
    if unreadable:
        return objective('new_subscribers', reason='A Substack new-subscriber reading has no readable window')
    if not current:
        return objective('new_subscribers', reason='No Substack new-subscriber window inside this New York week yet')
    sources, other = {}, set()
    for row in current:
        scope = row.get('scope')
        if scope == ALL_SOURCES or (isinstance(scope, str) and scope.startswith(SOURCE_PREFIX)
                                    and scope[len(SOURCE_PREFIX):].strip()):
            sources.setdefault(scope, []).append(row)
        else:
            other.add(scope if isinstance(scope, str) else repr(scope))
    if other:
        return objective('new_subscribers', reason='Substack rows this week have a scope that is neither the '
                                                   'publication nor a source: ' + ', '.join(sorted(other)))
    parts = [sources[ALL_SOURCES]] if ALL_SOURCES in sources else [sources[k] for k in sorted(sources, key=str)]
    totals = []
    for part in parts:
        try:
            total = aggregate(part)
        except ValueError as error:
            return objective('new_subscribers', reason='Substack windows this week cannot be added: ' + str(error))
        if total.get('value') is None:
            return objective('new_subscribers', reason='Substack this week: ' + total.get('reason', 'not shown'))
        if instant(total['start']) != start:
            return objective('new_subscribers', reason='Substack windows this week do not start on Monday in New York')
        totals.append(total)
    if len({instant(t['end']) for t in totals}) != 1:
        return objective('new_subscribers', reason='Substack sources this week end at different times, so they cannot be added')
    return objective('new_subscribers', sum(t['value'] for t in totals), 'measured',
                     window_start=totals[0]['start'], window_end=totals[0]['end'])


def observation_line(observations, now):
    """Exactly what this report validated: only this week's Substack new-subscriber readings."""
    observations = list(observations or [])
    _, current, unreadable, _ = _substack_week(observations, now)
    valid = 0
    for row in current:
        try:
            validate_observation(row)
            valid += 1
        except (ValueError, TypeError, AttributeError):
            pass
    failed = len(current) - valid + len(unreadable)
    rest = len(observations) - len(current) - len(unreadable)
    line = 'Validated ' + count(valid, 'Substack new-subscriber reading') + ' inside this New York week'
    if failed:
        line += ', ' + str(failed) + ' failed validation'
    if rest:
        line += '; ' + count(rest, 'other supplied observation') + ' not checked'
    return line


def _items(envelopes, queue, now, job):
    """The selected and deferred work, with metadata, from the job's own files."""
    index = {}
    for envelope in envelopes:
        for item, meta in zip(envelope['pack'].get('items', []), envelope['metadata']):
            index[meta['item_id']] = {**item, **meta, 'pack_kind': envelope['pack']['kind']}
    if queue is None:
        queue = daily_queue(list(index.values()), now)
    # The day's queue merges every job; this report carries only this job's work.
    mine = lambda item: item.get('pack_kind') in (None, job)
    selected = [row for row in ({**index.get(i['item_id'], {}), **i} for i in queue.get('items', [])) if mine(row)]
    deferred = [row for row in ({**index.get(i['item_id'], {}), **i} for i in queue.get('deferred', [])) if mine(row)]
    return selected, deferred, queue


def item_proposal(item, job, evidence):
    kind = item.get('pack_kind') or job
    wall, event = WALLS[kind]
    name = NAMES.get(item['platform'], item['platform'])
    title = {'post': 'Post the ' + name + ' draft: ' + item.get('placement', kind),
             'send': 'Send the ' + name + ' ' + kind + ' draft: ' + item.get('placement', kind),
             'strategy': 'Review the ' + kind + ' recommendation: ' + item.get('placement', kind),
             'none': 'Check the ' + kind + ' card: ' + item.get('placement', kind)}[wall]
    why = (item.get('why_now') or 'Prepared by the ' + kind + ' job.') + ' About ' + str(item.get('minutes', 1)) + ' minutes of Krish time.'
    sources = []
    for ref in item.get('evidence_ids', []):
        source = evidence.get(ref)
        if source and isinstance(source.get('url'), str) and source['url'].startswith('https://') and http_url(source['url']):
            sources.append({'label': source['kind'].replace('_', ' '), 'url': source['url']})
    return proposal(SLUG + ':' + item['item_id'], title, why, 'advice' if wall == 'strategy' else 'prepared',
                    wall, event, channel=item['platform'], exact_payload=item['text'],
                    target=item.get('target_url') or item.get('target_name'), evidence=sources,
                    reference=item.get('success_check'), expires_at=item.get('expires_at'))


def completion_events(rows, now):
    """Completion labels Krish confirmed, with public or private evidence links."""
    events = []
    for row in rows or []:
        event = COMPLETIONS.get(row.get('label'))
        if not event or row.get('confirmed_by') != 'Krish':
            raise ValueError('a completion needs a known label and confirmed_by Krish')
        url = row.get('evidence_url')
        if not (isinstance(url, str) and url.startswith('https://') and http_url(url)):
            raise ValueError('a completion needs an https evidence_url')
        if instant(row['at']) > instant(now):
            raise ValueError('a completion cannot be in the future')
        pid = row.get('proposal_id') or SLUG + ':' + row['item_id']
        events.append({'event': event, 'proposal_id': pid, 'at': iso(row['at']), 'evidence_url': url})
    return events[:40]


def workspace_report(job, run_id, now, envelopes=(), queue=None, observations=None, completions=None,
                     mode='live', directive_pulled=False, rev=None, root='.'):
    if job not in KINDS:
        raise ValueError('unknown job ' + str(job))
    evidence = {e['evidence_id']: e for env in envelopes for e in env.get('evidence', [])}
    selected, deferred, queue = _items(envelopes, queue, now, job)
    proposals, holds, minutes = [], [], 0
    for item in selected:
        if len(proposals) == 10:
            holds.append({'reason': 'Over the ten proposals one report carries', 'detail': item['item_id']})
            continue
        if (item.get('pack_kind') or job) in CONTROL_CENTER_OWNS:
            holds.append({'reason': OWNED_REASON, 'detail': item.get('item_id', '?') + ': open People in Control Center'})
            continue
        try:
            proposals.append(item_proposal(item, job, evidence))
            minutes += item.get('minutes', 0)
        except (KeyError, ValueError) as error:
            holds.append({'reason': 'Draft could not become a proposal', 'detail': item.get('item_id', '?') + ': ' + str(error)})
    for item in deferred:
        detail = item['item_id']
        if item.get('blocked_by'):
            detail += ': ' + '; '.join(str(b) for b in item['blocked_by'])
        holds.append({'reason': 'Deferred: ' + item.get('reason', 'not selected'), 'detail': detail})
    if len(holds) > 40:
        extra = len(holds) - 39
        holds = holds[:39] + [{'reason': str(extra) + ' more holds', 'detail': 'Full list in the local queue'}]
    goal = new_subscribers(observations, now)
    objectives = [goal, objective('paid_boosts_usd', reason=NO_SPEND[0].upper() + NO_SPEND[1:])]
    events = completion_events(completions, now)
    activity = []
    if directive_pulled:
        activity.append({'line': "Pulled today's directive before reading any source"})
    activity.append({'line': 'Ran the ' + job + ' job and prepared ' + count(len(proposals), 'proposal') + ' for Krish, about '
                     + str(minutes) + ' minutes of the '
                     + str(queue.get('budget_minutes', 20)) + ' minute daily budget'})
    if deferred:
        activity.append({'line': 'Deferred ' + count(len(deferred), 'draft') + ' for the budget, expiry or an unverified prerequisite'})
    if observations:
        activity.append({'line': observation_line(observations, now)})
    if events:
        activity.append({'line': 'Recorded ' + count(len(events), 'completion') + ' Krish confirmed'})
    activity.append({'line': 'Posted, sent, published and spent nothing; Krish acts on each proposal himself'})
    if job == 'numbers' and goal['availability'] != 'measured':
        status = 'degraded'
    elif proposals or events or goal['availability'] == 'measured':
        status = 'ready'
    else:
        status = 'held'
        if not holds:
            holds.append({'reason': 'Nothing was prepared this run', 'detail': None})
    report = build_report(run_id, mode, now, rev or revision(root), now, status, objectives,
                          activity, proposals, events, holds)
    return report, None


# Local state in the workspace ---------------------------------------------

def state_path(root, name):
    return Path(root) / STATE_DIR / name


def remember(root, report, decisions, read_at):
    """Keep a local ledger so a later decision can be matched to its exact payload."""
    path = state_path(root, 'proposals.json')
    ledger = read_json(path) if path.exists() else {}
    for item in report['proposals']:
        ledger[item['proposal_id']] = {'payload_sha256': item['payload_sha256'], 'title': item['title'],
                                       'wall': item['wall'], 'channel': item['channel'],
                                       'exact_payload': item['exact_payload'], 'reported_in': report['run_id']}
        for key in ('stage', 'parent_proposal_id'):
            if key in item:  # 1.1.0: the go-live step needs each stage and its plan.
                ledger[item['proposal_id']][key] = item[key]
        if 'stage' in item:
            ledger[item['proposal_id']].update(amount_usd=item['amount_usd'], expires_at=item['expires_at'])
    write_json(path, ledger)
    known = [{'proposal_id': pid, 'payload_sha256': row['payload_sha256']} for pid, row in ledger.items()]
    matched = match_decisions(decisions or [], known)
    write_json(state_path(root, 'decisions.json'), {'read_at': iso(read_at), 'decisions': matched})
    return matched


GOLIVE_LEDGER = 'golive-ledger.json'


def golive_ledger(root):
    """The local idempotency ledger: go-lives already claimed, plans Krish stopped,
    and declined check-ins whose plan is not known yet."""
    path = state_path(root, GOLIVE_LEDGER)
    ledger = read_json(path) if path.exists() else {}
    return {key: dict(ledger.get(key) or {}) for key in ('acted', 'stopped', 'unresolved')}


def remembered_proposals(root):
    """The staged proposals this workspace reported before, from remember()."""
    path = state_path(root, 'proposals.json')
    rows = read_json(path) if path.exists() else {}
    return [dict(row, proposal_id=pid) for pid, row in sorted(rows.items())
            if isinstance(row, dict) and 'stage' in row]


def claim_golives(root, proposals, decisions, now=None):
    """Claim each approved go-live once, under the lock, and return the review.

    The returned actions are claimed before anything acts on them, so a lost or
    uncertain outcome is never repeated: the release layer reads back instead.
    Stops are recorded too, so a purged plan stays stopped, and the proposals
    reported before are read back so a purged check-in is still known after
    it leaves the report. now defaults to the clock, so expiry is always
    checked. Acts on nothing."""
    path = state_path(root, GOLIVE_LEDGER)
    now = instant(now)
    at = iso(now)
    given = [p for p in proposals or [] if isinstance(p, dict)]
    known = {p.get('proposal_id') for p in given}
    merged = given + [p for p in remembered_proposals(root) if p['proposal_id'] not in known]
    with locked(path):
        ledger = golive_ledger(root)
        review = golive_review(merged, decisions, ledger, now)
        ledger['stopped'].update({pid: why for pid, why in review['stopped'].items() if pid not in ledger['stopped']})
        ledger['unresolved'] = dict(review['unresolved'])
        for action in review['actions']:
            ledger['acted'][action_key(action)] = {
                'proposal_id': action['proposal_id'], 'parent_proposal_id': action['parent_proposal_id'],
                'action_sha256': action['action_sha256'], 'amended': action['amended'],
                'decided_at': action['decided_at'], 'claimed_at': at}
        write_json(path, {key: dict(sorted(ledger[key].items())) for key in ('acted', 'stopped', 'unresolved')})
    return review


def decisions_since(root, now):
    path = state_path(root, 'decisions.json')
    try:
        return instant(read_json(path)['read_at'])
    except (OSError, ValueError, KeyError, TypeError):
        return instant(now) - dt.timedelta(days=7)


VOICE_RULES_FILE = 'voice-rules.txt'
VOICE_USE = ('Use them only for how anything you draft is written. Never use them to choose what it is about, '
             'and never to judge, score, rank or check a draft: the review, the rubric scores, the breakout score, '
             'the queue and growth.py check work exactly as if this block were not here.')


def voice_rules(directive):
    """Krish's approved voice rules from the directive (protocol 1.5.0 `taste`).

    Returns (state, rule, rules). state is 'absent' when the directive carries
    no readable taste (Control Center could not read them today, or speaks an
    older 1.x), 'none' when the list is empty (none approved yet) and 'rules'
    otherwise. Malformed entries are dropped, never repaired or invented.
    These rules feed drafting only: nothing that judges, scores, ranks or
    gates a draft (engine.packs, engine.operations, the report) reads them."""
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    taste = body.get('taste') if isinstance(body, dict) else None
    if not isinstance(taste, dict) or not isinstance(taste.get('approved_voice_rules'), list):
        return 'absent', None, []
    rule = taste.get('rule') if isinstance(taste.get('rule'), str) and taste['rule'].strip() else None
    rules = []
    for item in taste['approved_voice_rules']:
        if not isinstance(item, dict) or not isinstance(item.get('rule'), str) or not item['rule'].strip():
            continue
        text = lambda key: item[key].strip() if isinstance(item.get(key), str) and item[key].strip() else None
        rules.append({'layer': text('layer'), 'rule': item['rule'].strip(), 'his_words': text('his_words'),
                      'what_it_means': text('what_it_means')})
    return ('rules' if rules else 'none'), rule, rules


def voice_block(directive):
    """The labelled block a drafting step reads. Local only, never a public log."""
    state, rule, rules = voice_rules(directive)
    lines = ["KRISH'S APPROVED VOICE RULES (for drafting only; from today's directive)"]
    if state == 'absent':
        lines += ['  Could not be read today. Do not invent any: draft to the voice rules in AGENTS.md as before.']
        return lines
    lines.append('  ' + VOICE_USE)
    if rule:
        lines.append("  Control Center's rule: " + ' '.join(rule.split()))
    if state == 'none':
        lines.append('  None approved yet. Do not invent one: draft to the voice rules in AGENTS.md as before.')
        return lines
    lines.append('  Where one of these and AGENTS.md disagree on how to write, follow his approved rule;'
                 ' the facts-only and no-action rules still bind.')
    for number, item in enumerate(rules, 1):
        lines.append('  ' + str(number) + '. ' + ('[' + item['layer'] + '] ' if item['layer'] else '') + ' '.join(item['rule'].split()))
        if item['his_words']:
            lines.append('     his words: "' + ' '.join(item['his_words'].split()) + '"')
        if item['what_it_means']:
            lines.append('     what it means: ' + ' '.join(item['what_it_means'].split()))
    lines.append('END OF VOICE RULES')
    return lines


def describe(directive):
    """A short local summary of the directive. Never used on a public runner log."""
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    action = body.get('next_action') or {}
    lines = ['directive ' + str(body.get('directive_id')) + ' (chosen by ' + str(directive.get('chosen_by')) + ')',
             'next action: ' + str(action.get('instruction')), 'why: ' + str(action.get('why'))]
    if action.get('proposal_id'):
        lines.append('proposal: ' + str(action['proposal_id']))
    for item in body.get('objectives', []):
        lines.append('objective ' + str(item.get('key')) + ': latest ' + str(item.get('latest')) + ' '
                     + str(item.get('unit')) + ', target ' + str(item.get('target')) + ', ' + str(item.get('availability')))
    return lines + voice_block(directive)


def summary(outcome, public=False, matched=None):
    lines = []
    posted = outcome.get('posted') or {}
    if outcome.get('report'):
        lines.append('report ' + outcome['report']['run_id'] + ' ' + outcome['report']['status']
                     + ', payload_sha256 ' + outcome['report']['payload_sha256'])
    if posted:
        if posted.get('conflict'):
            lines.append('report conflict: Control Center already holds a different payload for this run_id; not resent'
                         + ('; the stored digest matches ours' if posted.get('readback_matches') else ''))
        else:
            lines.append('report accepted' + (' (replayed)' if posted.get('replayed') else '') + '; readback digest matches')
    if 'decisions' in outcome:
        if matched is None:
            matched = match_decisions(outcome['decisions'], (outcome.get('report') or {}).get('proposals', []))
        usable = [m for m in matched if m['usable_approval']]
        lines.append('decisions read: ' + str(len(matched)) + ', approvals on the exact payload reported: ' + str(len(usable)))
        if not public:
            lines += ['approved exactly: ' + str(m['proposal_id']) + ' (Krish acts; this engine posts nothing)' for m in usable]
    lines.append('attempt ' + outcome['status'] + (' ' + outcome['error_code'] if outcome.get('error_code') else '')
                 + ('' if outcome.get('attempt_journaled') else ' (not journaled in Control Center)'))
    return lines


def _load_many(paths):
    return [read_json(p) for p in paths or []]


def cli(args, root, make_client, out=print, checks=None):
    """growth.py cc start|finish|run|runner. Returns the exit code."""
    checks = checks or runner_checks
    root = Path(root)
    now_value = getattr(args, 'now', None)
    clock = (lambda: instant(now_value)) if now_value else (lambda: instant())
    now = clock()
    if args.cc_cmd == 'runner':
        dispatched = os.environ.get('CC_DISPATCH_ENGINE_ID', '').strip()
        if dispatched and dispatched != ENGINE_ID:
            out('Not ready: the dispatch named another engine; nothing was run')
            return 1
        run_id = args.run_id or run_id_for('runner', now)
        if not args.deliver:
            report, error = runner_report(root, run_id, now, checks(root), args.mode)
            out('Dry run: no Control Center call. Report ' + report['status'] + ', payload_sha256 ' + report['payload_sha256'])
            return int(bool(error))
        client = make_client()
        outcome = run(client, 'runner', run_id,
                      lambda d: runner_report(root, run_id, clock(), checks(root), args.mode, True),
                      now - dt.timedelta(days=7), clock)
        for line in summary(outcome, public=True):
            out(line)
        return int(outcome['status'] != 'succeeded')

    job = args.job
    run_id = args.run_id or run_id_for(job, now)
    saved = state_path(root, job + '.state.json')
    voice_file = state_path(root, VOICE_RULES_FILE)
    if args.cc_cmd in ('start', 'run') and voice_file.exists():
        voice_file.unlink()  # Never let yesterday's rules stand in for today's, even on a dry run.

    def build(directive):
        return workspace_report(job, run_id, clock(), _load_many(args.envelope),
                                read_json(args.queue) if args.queue else None,
                                [o for rows in _load_many(args.observations) for o in rows],
                                read_json(args.completions) if args.completions else None,
                                args.mode, directive is not None, root=root)

    if not args.deliver:
        if args.cc_cmd == 'start':
            out('Dry run: no Control Center call. A scheduled run adds --deliver to journal the start and pull the directive.')
            return 0
        report, _ = build(None)
        write_json(state_path(root, 'report-' + job + '.json'), report)
        out('Dry run: report ' + report['status'] + ' with ' + count(len(report['proposals']), 'proposal') + ', payload_sha256 '
            + report['payload_sha256'] + '; written to ' + str(STATE_DIR / ('report-' + job + '.json')) + '; no Control Center call')
        return 0
    client = make_client()
    loop = None
    if args.cc_cmd == 'finish' and saved.exists():
        state = read_json(saved)
        if state.get('run_id') == run_id and state.get('attempt_id'):
            loop = Loop.resume(client, state, clock)
    if loop is None:
        loop = Loop(client, job, run_id, clock)
        if voice_file.exists():
            voice_file.unlink()  # A fresh start pulls today's rules.
        try:
            write_json(saved, loop.start())
        except ProtocolError as error:
            outcome = loop.end('failed', error.code)
            out(summary(outcome)[-1])
            return 1
        # The drafting steps read this local, ignored file; nothing that checks,
        # scores or queues a draft does.
        voice_file.write_text('\n'.join(voice_block(loop.directive)) + '\n', encoding='utf-8')
        for line in describe(loop.directive):
            out(line)
        if args.cc_cmd == 'start':
            out('attempt started: finish this job with growth.py cc finish --job ' + job + ' --deliver')
            return 0
    since = decisions_since(root, now)
    outcome = loop.finish(build, since)
    if outcome.get('report'):
        write_json(state_path(root, 'report-' + job + '.json'), outcome['report'])
    matched = None
    if 'decisions' in outcome:
        matched = remember(root, outcome['report'], outcome['decisions'], now)
    if outcome.get('attempt_journaled') and saved.exists():
        saved.unlink()
    for line in summary(outcome, matched=matched):
        out(line)
    return int(outcome['status'] != 'succeeded')
