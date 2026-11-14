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

from . import meter
from .control_center import (ENGAGE_CHANNEL, ENGINE_ID, SLUG, STATE_FIELDS, ProtocolError, _decided_at, action_key,
                             action_errors, build_report, canonical_json, copy_open, engage_action, golive_review, iso,
                             match_decisions, objective, proposal, without_state, _stops)
from . import engage, engine_state, intensity, owners, stale_asks
from .credits import credits_block, credits_lines
from .copy_lint import copy_lint_errors
from .core import KINDS, UTC, http_url, instant, locked, ny_time, read_json, today, write_json
from .operations import aggregate, daily_queue, validate_observation
# What this engine took back once its week or window was over, carried forward (engine/stale_asks.py).
from .stale_asks import WITHDREW, WITHDRAWN
# Its go-lives that still carried a LinkedIn line could not be read back (engine/run/handoff.py handed_off_golives).
UNREAD_GOLIVES = 'Could not read its own go-lives, so none with a LinkedIn post was taken back or proposed again today'

SECRET_ENV = ('CONTROL_CENTER_ENGINE_TOKEN', 'GROWTH_ENGINE_TOKEN', 'BUFFER_API_KEY', 'GITHUB_TOKEN')
STATE_DIR = Path('.scratch') / 'cc'
WORKSPACE_ONLY = 'Measured only in the publication workspace'
NO_SPEND = 'this engine has no spend authority, bought no boosts and does not read platform ad spend'
# Which wall each pack kind sits behind, and the event that closes it.
WALLS = {'daily': ('post', 'published'), 'radar': ('post', 'published'), 'conversion': ('post', 'applied'),
         'pitches': ('send', 'sent'), 'swaps': ('send', 'sent'), 'partners': ('send', 'sent'),
         'report': ('strategy', 'reviewed'), 'numbers': ('none', 'verified')}
# Make Your Mind Up outreach (shows, guests, swaps and partners) belongs to this engine, and
# Krish enacts it himself in Codex sessions (Ruling, Krish, 2026-11-05). Only Mindmake's own
# outreach is Control Center's. So this work never becomes a Control Center proposal.
CONTROL_CENTER_OWNS = frozenset({'pitches', 'swaps', 'partners'})
OWNED_REASON = "Make Your Mind Up outreach is this engine's own, enacted in Krish's Codex sessions; it never goes to Control Center"
COMPLETIONS = {'Published': 'published', 'Sent': 'sent', 'Applied': 'applied',
               'Verified': 'verified', 'Reviewed': 'reviewed'}
NAMES = {'linkedin': 'LinkedIn', 'x': 'X', 'youtube': 'YouTube', 'tiktok': 'TikTok', 'seo': 'search',
         'substack': 'Substack', 'instagram': 'Instagram', 'spotify': 'Spotify', 'reddit': 'Reddit',
         'facebook': 'Facebook', 'threads': 'Threads', 'notes': 'Substack Notes'}


def count(number, noun):
    return str(number) + ' ' + noun + ('' if number == 1 else 's')


def run_id_for(command, now=None):
    return SLUG + ':' + today(now) + ':' + command


WAKE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$')


def runner_run_id(now, backup=False, wake=None):
    """The runner's run_id: one a day, and one more for each extra wake. Krish's instruction can wake the runner a
    second time the same day (protocol 1.20.0), so that wake reports under its own discriminator (the GitHub run
    id and attempt) and never conflicts with the morning's report."""
    base = run_id_for('runner-backup' if backup else 'runner', now)
    if wake is None:
        return base
    if not WAKE.match(str(wake)):
        raise ValueError('--wake is up to 40 letters, digits, dots, dashes or underscores')
    return base + ':wake-' + wake


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

    def finish(self, build, since, degrade=None):
        """build(directive) returns (report, error_code or None). degrade(directive) rebuilds it with the
        engagement task as one plain proposal, used once when Control Center cannot take the task."""
        outcome = {}
        try:
            self.phase = 'work'
            report, work_error = build(self.directive)
            outcome['report'] = report
            self.phase = 'report'
            tried = set()
            while True:
                try:
                    posted = self.client.post_report(report)
                    break
                except ProtocolError as error:
                    # A refused or unconfirmed report was not stored, so the next one is not a resend.
                    if 'state' not in tried and error.code in STATE_DEGRADE and any(k in report for k in STATE_FIELDS):
                        # Control Center could not take 1.20.0 today: report the run without its new fields.
                        tried.add('state')
                        report = without_state(report)
                        outcome.update(report=report, state_dropped=error.code)
                        continue
                    if not ('engage' not in tried and degrade and error.code in ENGAGE_DEGRADE
                            and any(copy_open(p) for p in report['proposals'])):
                        raise
                    tried.add('engage')
                    self.phase = 'work'
                    report, work_error = degrade(self.directive)
                    if 'state' in tried:
                        report = without_state(report)
                    outcome.update(report=report, degraded=error.code)
                    self.phase = 'report'
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


PLAN_FILE = Path('specs') / 'standing-plan.json'
PILOTS_FILE = Path('lists') / 'pilots.json'
# This engine adopted protocol 1.1.0 on 2026-10-19; none of its decisions is older.
DECISIONS_SINCE = '2026-10-19T00:00:00Z'
LOOKBACK_DAYS = 14
# Control Center serves at most 100 decisions a read, the oldest first.
DECISIONS_PAGE = 100
DECISIONS_PAGES = 50
HOLD_DETAIL_MAX = 1000
WAITING = 'Waiting on Krish, not sent again'
ANSWERED = 'Answered by Krish, not sent again'
UNREAD = 'Could not read what Krish was already sent, so nothing was proposed'
VERDICTS = ('works', 'neutral', 'fails', 'insufficient')


def standing_plan(root):
    """The standing W45 to W52 plan as a stage plan proposal behind strategy, or None without its file."""
    path = Path(root) / PLAN_FILE
    if not path.exists():
        return None
    plan = read_json(path)
    return proposal(plan['proposal_id'], plan['title'], plan['why'], 'advice', 'strategy', 'plan_approved',
                    exact_payload=plan['exact_payload'], reference='docs/RUN.md, Gates', stage='plan')


MIX_DIR = Path('.scratch') / 'mix'


def next_monday(now):
    local = ny_time(now).date()
    return local + dt.timedelta(days=7 - local.weekday())


def mix_proposal(root, now):
    """(proposal, hold): next week's mix plan, Krish's one press on its ideas and mocks (R101, R103).

    `growth.py mix plan --out .scratch/mix/plan-<Monday>.json` writes it in the
    Sunday report's run; the report carries its plan proposal behind strategy.
    No file means no ask; a file whose proposal could not be built is a hold.
    The plan itself is judged by plan_proposals, which the L0 handoff calls too
    with a plan it was sent (engine/run/handoff.py, growth-mix-plan)."""
    path = Path(root) / MIX_DIR / ('plan-' + next_monday(now).isoformat() + '.json')
    if not path.exists():
        return None, None
    try:
        items, hold = plan_proposals(read_json(path))
        return (items[0] if items else None), hold
    except (ValueError, OSError, AttributeError) as exc:
        return None, {'reason': "Next week's mix could not be read", 'detail': str(exc)[:900]}


BACKSTOP_FILE = Path('.scratch') / 'taste' / 'backstop.jsonl'


def clock_lines(root, now, taps=0):
    """Wave 2 clock facts for Control Center's DONE_CHECKS (W2.2), as activity lines until it names their fields.

    engage: the taps prepared today (engage_done itself is Krish's marks); offday:
    this week's mix plan file, if there is one (engine/offday.py clock); backstop:
    the flagged lines the SessionEnd hook kept locally (scripts/taste_backstop.py),
    waiting on Control Center's taste_reports route. Unknown is said, never zero."""
    from . import offday
    lines = []
    if taps:
        lines.append('Clock engage: ' + count(taps, 'engagement tap') + " ready for Krish today; engage_done is his marks")
    monday = next_monday(now) - dt.timedelta(days=7)
    for day in (monday, monday + dt.timedelta(days=7)):
        path = Path(root) / MIX_DIR / ('plan-' + day.isoformat() + '.json')
        if not path.is_file():
            continue
        try:
            facts = offday.clock(read_json(path), now, root=root)
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            lines.append('Clock offday for the week of ' + day.isoformat() + ': the plan file could not be read')
            continue
        lines.append('Clock offday for the week of ' + day.isoformat() + ': offday_stocked '
                     + ('yes' if facts['offday_stocked'] else 'no') + ', ' + str(facts['stocked_slots']) + ' of '
                     + str(facts['filler_slots']) + ' filler slots ready, due ' + facts['stocked_by'][:16])
    path = Path(root) / BACKSTOP_FILE
    if path.is_file():
        try:
            waiting = sum(1 for raw in path.read_text(encoding='utf-8').splitlines()
                          if raw.strip() and json.loads(raw).get('posted') is False)
            lines.append('Chat backstop: ' + count(waiting, 'flagged line') + " of Krish's kept locally, waiting on "
                         "Control Center's taste_reports route; none sent")
        except (ValueError, OSError, AttributeError):
            lines.append('Chat backstop: its local file could not be read')
    return lines


def offdays_field(root, now):
    """This week's off-day options for Control Center (protocol 1.17.0 offdays, growth-offdays/1), from the
    mix plan file of the week that holds today, else next week's; None when neither is kept. His list counts
    the ready ones from today on. Only the three keys Control Center reads go out per option."""
    from . import offday
    monday = next_monday(now) - dt.timedelta(days=7)
    for day in (monday, monday + dt.timedelta(days=7)):
        path = Path(root) / MIX_DIR / ('plan-' + day.isoformat() + '.json')
        if not path.is_file():
            continue
        try:
            value = offday.options(read_json(path), root=root)
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            return None
        days = {date: [{'concept_id': o['concept_id'], 'lane': o['lane'], 'ready': bool(o['ready'])}
                       for o in options[:6]] for date, options in sorted(value['days'].items())[:7]}
        return {'schema': value['schema'], 'week_of': value['week_of'], 'days': days}
    return None


def plan_proposals(mix):
    """([proposal], hold) for one week's mix doc: its plan proposal, then any later parts in order.

    Each must be a plan behind strategy, or nothing is asked and the hold says why.
    The local loop reads a plan file and asks its one proposal; the L0 handoff
    rebuilds the parts of a plan it was sent (mix['parts'], engine/mix.py
    part_proposals) and asks them all, one at a time in order."""
    items = list(mix.get('parts') or []) or [mix.get('proposal')]
    if not items or any(not isinstance(item, dict) or item.get('stage') != 'plan' or item.get('wall') != 'strategy'
                        for item in items):
        return [], {'reason': "Next week's mix has no plan proposal", 'detail': str(mix.get('proposal_hold'))[:900]}
    return items, None


def experiment_proposals(root, now=None):
    """Each planned experiment as an ask behind strategy. One whose window has closed is never asked
    (engine/stale_asks.py: nothing is asked about a window that is over)."""
    out = []
    for exp in read_json(Path(root) / 'experiments.json')['experiments']:
        if exp.get('status') != 'planned' or (now is not None and stale_asks.experiment_over(exp, now)):
            continue
        out.append(proposal(
            SLUG + ':experiment:' + exp['experiment_id'],
            'Decide whether to start the ' + exp['experiment_id'] + ' experiment',
            exp['hypothesis'] + ' Rule: ' + exp['decision_rule'], 'advice', 'strategy', 'experiment_started',
            objective_key='new_subscribers', reference=exp['experiment_id'], payload=exp))
    return out


def id_holds(reason, entries):
    """Holds naming each entry whole, as many to a hold as fit its 1000-character detail: never clipped."""
    out, line = [], ''
    for entry in entries:
        if line and len(line) + 2 + len(entry) > HOLD_DETAIL_MAX:
            out.append({'reason': reason, 'detail': line})
            line = ''
        line = line + ', ' + entry if line else entry
    return out + ([{'reason': reason, 'detail': line}] if line else [])


def _decision_key(item):
    """A decision's identity: its whole record. The route gives no id, and two reads of
    one decision are the same record."""
    return json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def decisions_paged(client, since):
    """Every decision after since, oldest first, each once, read page by page; None when
    the pages do not end (the caller fails closed: decisions_unpaged).

    Control Center serves at most DECISIONS_PAGE decisions a read, the oldest first,
    after since to the second. A page that is short is the last. The next page starts
    one second before the last decided_at seen, so a decision sharing that time (a tie
    at the page boundary) is read again rather than dropped, and a decision read twice
    counts once. A full page that moves since no further (more than a page of decisions
    inside one second), or more than DECISIONS_PAGES pages, is None: never a guess.
    Shared by the runner's ledger read and both L0 lanes (engine.run.autorelease and
    engine.run.handoff)."""
    since, out, seen = instant(since), [], set()
    for _ in range(DECISIONS_PAGES):
        page = client.decisions(since)
        for item in page:
            key = _decision_key(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        if len(page) < DECISIONS_PAGE:
            return out
        times = [_decided_at(d) for d in page if isinstance(d, dict)]
        last = max((t for t in times if t is not None), default=None)
        if last is None:
            return None
        following = last - dt.timedelta(seconds=1)
        if following <= since:
            return None
        since = following
    return None


def _decisions_until(client, cutoff):
    """Every decision since this engine began and decided by cutoff, read page by page, or None."""
    out = decisions_paged(client, DECISIONS_SINCE)
    return None if out is None else [d for d in out if not _after(d, cutoff)]


def _after(item, cutoff):
    try:
        return isinstance(item, dict) and bool(item.get('decided_at')) and instant(item['decided_at']) > cutoff
    except (ValueError, TypeError):
        return False


def already_sent(client, now, directive=None, mode='live', include_today=False):
    """What Krish already has from this engine: {proposal_id: decision or 'pending'}, or None.

    A clean runner keeps no state, so Control Center is the ledger. Every
    decision since this engine began and decided by now counts, whatever
    payload it was made on, read page by page: an answered ask is never sent
    again. The latest earlier runner report of this run's mode that read its
    ledger carries forward what it knew: its proposals and waiting hold as
    pending, its answered hold as answered, its taken-back hold as
    'withdrawn' (engine/stale_asks.py), so a decision past the route's
    reach still counts. A report that could not read its ledger, or of the
    other mode, is passed over. Today's own report is never read, and a
    decision after now is not counted, so a rerun with the same --now makes
    the same report. A second wake the same day (include_today) reads that
    morning's report first, so it never proposes again what the morning did.
    None when any read fails: then nothing is proposed."""
    known, answered, withdrawn = {}, {}, {}
    cutoff = instant(now)
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    try:
        decisions = _decisions_until(client, cutoff)
        if decisions is None:
            return None
        decisions = [d for d in body.get('decisions_since') or [] if not _after(d, cutoff)] + decisions
        for day in range(0 if include_today else 1, LOOKBACK_DAYS + 1):
            run_id = run_id_for('runner', cutoff - dt.timedelta(days=day))
            try:
                found = client.read_report(run_id).get('report')
            except ProtocolError as error:
                if error.code == 'not_found':
                    continue
                raise
            if not isinstance(found, dict):
                return None
            reasons = [h.get('reason') for h in found.get('holds') or [] if isinstance(h, dict)]
            if found.get('mode') != mode or UNREAD in reasons:
                continue
            for item in found.get('proposals') or []:
                if isinstance(item, dict) and isinstance(item.get('proposal_id'), str):
                    known[item['proposal_id']] = 'pending'
            for hold in found.get('holds') or []:
                if not isinstance(hold, dict) or not isinstance(hold.get('detail'), str):
                    continue
                entries = [e.strip() for e in hold['detail'].split(',') if e.strip()]
                if hold.get('reason') == WAITING:
                    known.update({pid: 'pending' for pid in entries})
                elif hold.get('reason') == ANSWERED:
                    answered.update(e.split('=', 1) for e in entries if '=' in e)
                elif hold.get('reason') == WITHDREW:
                    # Taken back by this engine once its week or window was over (engine/stale_asks.py).
                    withdrawn.update({pid: WITHDRAWN for pid in entries})
            break
    except ProtocolError:
        return None
    known.update(answered)
    known.update(withdrawn)
    for item in decisions:
        if isinstance(item, dict) and isinstance(item.get('proposal_id'), str):
            known[item['proposal_id']] = str(item.get('decision') or 'decided')
    return known


def pilot_lines(root, now):
    """Each pilot's verdict as an activity line, or a hold saying what it waits for. Never a proposal."""
    path = Path(root) / PILOTS_FILE
    if not path.exists():
        return [], []
    activity, holds = [], []
    try:
        pilots = read_json(path)['pilots']
        for pilot in pilots:
            pid, verdict = pilot['pilot_id'], pilot.get('verdict')
            if verdict is not None:
                if verdict not in VERDICTS or not pilot.get('verdict_recorded_at'):
                    raise ValueError(pid)
                activity.append({'line': 'Pilot ' + pid + ' verdict: ' + verdict + ' (recorded '
                                 + iso(pilot['verdict_recorded_at'])[:10] + ' by the What-Works Analyst)'})
                continue
            windows = [m['window'] for m in pilot.get('measured') or [] if m.get('captured_at')]
            due = instant(pilot['published_at']) + dt.timedelta(hours=pilot['judge_window_hours'])
            when = ('its judge window ended ' if due <= instant(now) else 'its judge window ends ') + iso(due)[:10]
            if windows:
                holds.append({'reason': 'Pilot measured, verdict not recorded yet',
                              'detail': pid + ': measured at ' + ', '.join(windows) + '; ' + when
                                        + '; closed by ' + pilot['closes_on']})
            else:
                holds.append({'reason': 'Pilot awaiting measurement',
                              'detail': pid + ': published ' + iso(pilot['published_at'])[:10] + ' on '
                                        + ', '.join(pilot['channels']) + '; ' + when + '; closed by ' + pilot['closes_on']})
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return [], [{'reason': 'Pilot record unreadable', 'detail': str(PILOTS_FILE)}]
    return activity, holds


def automation_count(root):
    """How many automations automations.json defines, or None when it cannot be read."""
    try:
        entries = read_json(Path(root) / 'automations.json')['automations']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return len(entries) if isinstance(entries, list) else None


RUNNER_BACKLOG = ('counted from the public feed and the committed pilot records; editions recorded only '
                  'in the publication workspace ledger are not visible to the runner')


def backlog_line(backlog):
    """The report's 'Backlog remaining N' line from (inventory, reason), or None when not read."""
    from .backlog import summary_line
    inventory, reason = backlog if backlog else (None, 'not read on this run')
    if inventory is None:
        return 'Backlog remaining: not counted, ' + reason
    return summary_line(inventory, RUNNER_BACKLOG[0].upper() + RUNNER_BACKLOG[1:])


def runner_report(root, run_id, now, checks, mode='live', directive_pulled=False, rev=None, sent=None,
                  backlog=None, gap=None, extra_activity=(), directive=None, seen=False, events=(), weeks=None,
                  golives=None):
    """The runner's held report. sent is already_sent(): asks Krish has, answered or pending, are
    never sent again, and None (not read) proposes nothing. backlog is backlog.for_runner():
    (inventory, None) or (None, reason); None means it was not read. extra_activity: lines
    the runner adds (the web_analytics shape it kept, its own cost so far). directive: today's, for
    Krish's instruction and the 1.20.0 state (engine/engine_state.py); seen: an earlier report already
    named his open instruction, so 'received' is not sent again. events: what this run closed (the
    proposed AI-answer questions, once written on his yes; engine/ai_answers.py). weeks is
    stale_asks.week_candidates(): (the ended weeks' own asks, None) or ([], why it could not read them); None
    means they were not read (a dry run). Every undecided ask of its own whose week or window is over is taken
    back (withdrawn), and none is asked again (Ruling, Krish, 2026-11-12: nothing on his list is stale).
    golives is engine/run/handoff.py handed_off_golives()'s (withdraw, code): its undecided go-lives that
    carried only a LinkedIn post, taken back the same way (Ruling, Krish, 2026-11-13: LinkedIn is
    growth-mindmake's), or why they could not be read; None means not read (a dry run)."""
    root = Path(root)
    automations = automation_count(root)
    defined = 'the ' + str(automations) + ' ' if automations is not None else 'the '
    by_name = {c['name']: c for c in checks}
    failed = [c['name'] for c in checks if not c['ok']]
    gap = gap or intensity.state(root, now)
    # Every report leads with the gap (Ruling, Krish, 2026-10-29; engine/intensity.py); his instruction is next.
    told, acks = engine_state.report_part(directive, now, 'runner', seen)
    activity = [{'line': intensity.gap_line(gap)}] + [{'line': line} for line in told]
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
    activity += [{'line': line} for line in extra_activity]
    activity.append({'line': backlog_line(backlog)})
    holds = [{'reason': 'Drafts and dashboard numbers are made only in the publication workspace',
              'detail': 'The automations defined in automations.json' + (' (' + str(automations) + ')' if automations is not None else '')
                        + ' draft and read dashboards there and report as their own runs; this runner checks the engine offline.'}]
    if failed:
        holds.append({'reason': 'Offline checks failed on the runner', 'detail': ', '.join(failed)})
    proposals, plan, asks = [], standing_plan(root), experiment_proposals(root, now)
    # An ask whose week or window is over is never asked again, and taken back when it still waits on him.
    candidates = stale_asks.local_candidates(root, now)
    if plan and plan['proposal_id'] in {pid for pid, _ in candidates}:
        plan = None
    week_asks, week_error = weeks if weeks is not None else ([], None)
    if week_error:
        holds.append({'reason': stale_asks.UNREAD_WEEKS, 'detail': week_error})
    handed_asks, golive_error = golives if golives is not None else ([], None)
    if golive_error:
        holds.append({'reason': UNREAD_GOLIVES, 'detail': golive_error})
    # The publication's AI-answer questions, proposed for his approval (Ruling, Krish, 2026-11-13).
    from . import ai_answers
    questions, questions_hold = ai_answers.proposal_or_hold(root)
    if questions_hold:
        holds.append(questions_hold)
    withdrawn = []
    if sent is None:
        holds.append({'reason': UNREAD, 'detail': 'decisions or earlier runner reports could not be read'})
    else:
        waiting, answered = [], []
        for item in ([plan] if plan else []) + asks + ([questions] if questions else []):
            pid = item['proposal_id']
            if pid not in sent:
                proposals.append(item)
            elif sent[pid] == 'pending':
                waiting.append(pid)
            else:
                answered.append(pid + '=' + sent[pid])
                if plan and pid == plan['proposal_id']:
                    activity.append({'line': 'The standing W45 to W52 plan is answered (' + sent[pid] + '); not proposed again'})
        count_answered = sum(1 for item in asks if sent.get(item['proposal_id'], 'pending') != 'pending')
        if count_answered:
            activity.append({'line': 'Experiment asks Krish has answered: ' + str(count_answered) + '; none sent again'})
        withdrawn, carried = stale_asks.withdrawals(candidates + list(week_asks) + list(handed_asks), sent,
                                                    [p['proposal_id'] for p in proposals])
        handed_ids = {pid for pid, _ in handed_asks}
        line = stale_asks.activity_line([w for w in withdrawn if w['proposal_id'] not in handed_ids])
        if line:
            activity.append({'line': line})
        handed_out = [w['proposal_id'] for w in withdrawn if w['proposal_id'] in handed_ids]
        if handed_out:
            activity.append({'line': 'Withdrew ' + str(len(handed_out)) + ' of its own go-live'
                             + ('' if len(handed_out) == 1 else 's') + " that held only a LinkedIn post, which is "
                             "growth-mindmake's since 13 November 2026: " + ', '.join(handed_out)})
        # Each id whole, so tomorrow's runner reads every one back (already_sent).
        holds += id_holds(WAITING, waiting) + id_holds(ANSWERED, answered) + id_holds(WITHDREW, carried)
    pilot_activity, pilot_holds = pilot_lines(root, now)
    activity += pilot_activity + [{'line': 'Posted, sent, published and spent nothing'}]
    holds += pilot_holds
    objectives = [
        objective('new_subscribers', reason=WORKSPACE_ONLY + '; a GitHub runner cannot read the Substack dashboard'),
        objective('paid_boosts_usd', reason=WORKSPACE_ONLY + '; ' + NO_SPEND)]
    report = build_report(run_id, mode, now, rev or revision(root), now, 'degraded' if failed else 'held',
                          objectives, activity, proposals, list(events), holds,
                          state=engine_state.fields(root, gap, directive, acks), withdrawn=withdrawn)
    return report, ('offline_checks_failed' if failed else None)


# The publication workspace ------------------------------------------------

ALL_SOURCES = 'publication'
SOURCE_PREFIX = 'source:'
# jobs/numbers.md records attributed sources separately and leaves Direct unattributed, so
# per-source rows cover every subscriber only when Direct is among them.
DIRECT_SOURCE = 'direct'


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
    source and the sources summed, which means the same only when a
    'source:direct' row (any case) is among them; without it the attributed
    sources alone would undercount, so the week is missing. Both together would
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
    if ALL_SOURCES not in sources and not any(k[len(SOURCE_PREFIX):].strip().lower() == DIRECT_SOURCE
                                              for k in sources):
        return objective('new_subscribers', reason='per-source rows without the all-source or direct row would undercount')
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
    if wall in ('post', 'send'):
        # The exact words reach the public once he presses, and the envelope may not have been sealed
        # here, so the copy lint reads them again: no eyebrows, asterisks, AI notes or take labels
        # (Krish, 2026-10-28), and "no content refers to Krish, ever" (Krish, 2026-10-28). A hit, or a
        # lint that cannot run, raises, and the draft is held, never proposed.
        lint = copy_lint_errors(item['text'], 'channel_copy')
        if lint:
            raise ValueError('the draft fails the copy lint: ' + '; '.join(lint))
    sources = []
    for ref in item.get('evidence_ids', []):
        source = evidence.get(ref)
        if source and isinstance(source.get('url'), str) and source['url'].startswith('https://') and http_url(source['url']):
            sources.append({'label': source['kind'].replace('_', ' '), 'url': source['url']})
    return proposal(SLUG + ':' + item['item_id'], title, why, 'advice' if wall == 'strategy' else 'prepared',
                    wall, event, channel=item['platform'], exact_payload=item['text'],
                    target=item.get('target_url') or item.get('target_name'), evidence=sources,
                    reference=item.get('success_check'), expires_at=item.get('expires_at'))


ENGAGE_JOBS = ('radar',)
# Control Center refuses or cannot take the engagement task: the same taps then go as one plain proposal.
ENGAGE_DEGRADE = ('schema_version_unsupported', 'schema_version_unconfirmed', 'copy_open_unsupported', 'bad_request')
# When Control Center cannot take the 1.20.0 state fields, the run still reports, once, without them.
STATE_DEGRADE = ('schema_version_unsupported', 'schema_version_unconfirmed', 'engine_state_unsupported', 'bad_request')


def _tap(item):
    name = NAMES.get(item['platform'], item['platform'])
    who = item.get('target_name') or item.get('placement') or 'the thread'
    return {'label': name + ': ' + str(who), 'text': item['text'], 'url': item.get('target_url')}


def engagement_task(items, now, evidence, cap, plain=False):
    """The day's engagement taps as one ask (Control Center's copy_open, protocol 1.14.0).

    Returns (proposal or None, holds, minutes). Each tap is the exact words to
    copy and the public page to open; Krish pastes and posts them himself and
    marks them carried out. Nothing here or in Control Center posts. A tap past
    today's cap, or one that cannot be a tap, is held with its reason. plain
    degrades the same taps to one plain-text proposal for a Control Center
    that cannot take the task."""
    taps, chosen, holds = [], [], []
    for item in items:
        tap = _tap(item)
        problems = action_errors({'body': 'x', 'taps': [tap]}) or engage.tap_errors(item['platform'], tap['url'], tap['text'])
        if problems:
            holds.append({'reason': 'Engagement draft cannot be a tap', 'detail': item['item_id'] + ': ' + problems[0]})
        elif len(taps) >= cap:
            holds.append({'reason': "Over today's engagement cap of " + str(cap), 'detail': item['item_id']})
        else:
            taps.append(tap)
            chosen.append(item)
    if not taps:
        return None, holds, 0
    minutes = sum(item.get('minutes', 1) for item in chosen)
    over = ('; over the ' + str(engage.QUEUE_MINUTES) + ' minute queue, the cap is from intensity.json'
            if minutes > engage.QUEUE_MINUTES else '')
    body = ("Today's " + str(len(taps)) + (' reply or comment' if len(taps) == 1 else ' replies or comments')
            + ' for Krish to post himself: each tap copies the exact words and opens the public page. About '
            + str(minutes) + ' minutes' + over + '.')
    sources = []
    for item in chosen:
        for ref in item.get('evidence_ids', []):
            source = evidence.get(ref)
            if source and isinstance(source.get('url'), str) and source['url'].startswith('https://') and http_url(source['url']):
                sources.append({'label': source['kind'].replace('_', ' '), 'url': source['url']})
    expiries = [instant(i['expires_at']) for i in chosen if i.get('expires_at')]
    if plain:
        words = '\n\n'.join(str(n) + '. ' + t['label'] + '\nOpen: ' + t['url'] + '\nCopy: ' + t['text']
                              for n, t in enumerate(taps, 1))
        payload = body + '\n\n' + words
    else:
        payload = canonical_json(engage_action(body, taps))
    item = proposal(SLUG + ':engage:' + today(now), "Post today's " + count(len(taps), 'engagement tap'),
                    'As many as cleared the bar today, batched as one ask. ' + body, 'advice' if plain else 'prepared',
                    'post', 'tapped', channel=ENGAGE_CHANNEL, exact_payload=payload, evidence=sources[:12],
                    reference='Krish marks them carried out after posting each one himself',
                    expires_at=min(expiries) if expiries else None)
    return item, holds, minutes


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
                     mode='live', directive_pulled=False, rev=None, root='.', gap=None, plain_taps=False,
                     directive=None, seen=False, acted=None, started_at=None):
    """One workspace job's report. directive, seen, acted and started_at carry Krish's instruction (protocol
    1.20.0, engine/engine_state.py): acted is (state, line, evidence_url), what this job did with it."""
    if job not in KINDS:
        raise ValueError('unknown job ' + str(job))
    evidence = {e['evidence_id']: e for env in envelopes for e in env.get('evidence', [])}
    selected, deferred, queue = _items(envelopes, queue, now, job)
    gap = gap or intensity.state(root, now)
    proposals, holds, minutes = [], [], 0
    # A draft for a channel another engine owns is held, never proposed or tapped (Ruling, Krish, 2026-11-13:
    # growth-mindmake owns his personal LinkedIn, posts and replies). A report's reading about it stays.
    for item in [i for i in selected if owners.owner(i.get('platform'))
                 and (i.get('pack_kind') or job) not in ('report', 'numbers')]:
        selected.remove(item)
        holds.append({'reason': 'Not this engine\'s channel', 'detail': item.get('item_id', '?') + ': '
                      + owners.refusal(item['platform'])})
    if job == 'report':
        mixed, held = mix_proposal(root, now)
        proposals += [mixed] if mixed else []
        holds += [held] if held else []
    taps = [i for i in selected if (i.get('pack_kind') or job) in ENGAGE_JOBS]
    if taps:
        task, more, used = engagement_task(taps, now, evidence, intensity.engagement_taps(gap['urgency'], root), plain_taps)
        proposals += [task] if task else []
        holds += more
        minutes += used
    for item in selected:
        if item in taps:
            continue
        if len(proposals) == 10:
            holds.append({'reason': 'Over the ten proposals one report carries', 'detail': item['item_id']})
            continue
        if (item.get('pack_kind') or job) in CONTROL_CENTER_OWNS:
            holds.append({'reason': OWNED_REASON, 'detail': item.get('item_id', '?') + ': in the Acquisition queue (jobs/acquisition.md); Krish sends it from his Codex session'})
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
    told, acks = engine_state.report_part(directive, now, job, seen, acted, started_at)
    activity = [{'line': intensity.gap_line(gap)}] + [{'line': line} for line in told]
    if intensity.raised(gap['urgency']):
        activity.append({'line': 'At U' + str(gap['urgency']) + ' the volume caps rise to their bounds in intensity.json: '
                         + str(intensity.engagement_taps(gap['urgency'], root)) + ' engagement taps a day; each channel'
                         + "'s posts stay at its own policy bound (Instagram, YouTube, TikTok and X four a day, Substack Notes four,"
                         + ' every other one); walls, spend and approvals unchanged'})
    if directive_pulled:
        activity.append({'line': "Pulled today's directive before reading any source"})
    if taps and proposals and copy_open(proposals[0]) is not None:
        activity.append({'line': 'Batched ' + count(len(json.loads(proposals[0]['exact_payload'])['taps']), 'engagement tap')
                         + " into one copy and open ask on Krish's list; he posts each himself"})
    elif taps and proposals and proposals[0]['channel'] == ENGAGE_CHANNEL:
        activity.append({'line': 'Control Center could not take the copy and open task, so the same taps went as one plain ask'})
    activity.append({'line': 'Ran the ' + job + ' job and prepared ' + count(len(proposals), 'proposal') + ' for Krish, about '
                     + str(minutes) + ' minutes of the '
                     + str(queue.get('budget_minutes', 20)) + ' minute daily budget'})
    if deferred:
        activity.append({'line': 'Deferred ' + count(len(deferred), 'draft') + ' for the budget, expiry or an unverified prerequisite'})
    if observations:
        activity.append({'line': observation_line(observations, now)})
    if events:
        activity.append({'line': 'Recorded ' + count(len(events), 'completion') + ' Krish confirmed'})
    tapped = len(json.loads(proposals[0]['exact_payload'])['taps']) if taps and proposals \
        and copy_open(proposals[0]) is not None else 0
    activity += [{'line': line} for line in clock_lines(root, now, tapped)]
    activity.append({'line': 'Posted, sent, published and spent nothing; Krish acts on each proposal himself'})
    if job == 'numbers' and goal['availability'] != 'measured':
        status = 'degraded'
    elif proposals or events or goal['availability'] == 'measured':
        status = 'ready'
    else:
        status = 'held'
        if not holds:
            holds.append({'reason': 'Nothing was prepared this run', 'detail': None})
    # 1.17.0, only when a mix plan is kept: the week's off-day options his list counts. The channels a
    # go-live may name ride on each go-live's own report (engine/run/handoff.py reports_for).
    # 1.21.0, only when the directive serves it: the cards he ticked as a style that a concept's mocks used.
    used = inspiration_used_field(root, now, directive)
    if used:
        activity.append({'line': 'Used ' + count(len(used), 'style') + ' Krish ticked as an instruction in this week\'s mocks; reported as inspiration_used'})
    report = build_report(run_id, mode, now, rev or revision(root), now, status, objectives,
                          activity, proposals, events, holds, offdays=offdays_field(root, now),
                          state=engine_state.fields(root, gap, directive, acks,
                                                    done=bool(acted) and acted[0] == 'done'),
                          inspiration_used=used)
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


def older_golives_line(count):
    """The runner's line when its newest page of reports was full: go-lives older than those were not looked at."""
    return ('Looked for its go-lives with a LinkedIn post in its ' + str(count) + ' newest reports only, the most'
            ' Control Center serves: any older go-live was not looked at')


def handed_off_golives(client, sent, now, root):
    """([activity line], (withdraw, code)) for the runner: its pending go-lives that still carry a line on a
    channel another engine owns (engine/run/handoff.py handed_off_golives). Each that keeps other posts is
    proposed again now, the same proposal_id without that line, in its own go-live report, so Control Center
    shows his list that version; each that held nothing else is returned for the runner's withdrawn[]. Only its
    handoff.RECENT newest reports are looked at (Control Center serves no older page); when that page was full,
    one line says older go-lives were not. It is a line, not a hold."""
    from .run import handoff
    reports, withdraw, code, full = handoff.handed_off_golives(client, sent, now, root)
    lines = [older_golives_line(handoff.RECENT)] if full else []
    if not reports:
        return lines, (withdraw, code)
    done = {'reports': {'posted': 0, 'readback_matches': 0, 'already_reported': 0}, 'loud': []}
    try:
        handoff.deliver_reports(client, reports, done)
    except ProtocolError as error:
        return lines, (withdraw, code or 'golive_report_' + error.code)
    if done['loud']:
        return lines, (withdraw, code or done['loud'][0])
    ids = [item['proposal_id'] for report in reports for item in report['proposals']]
    return ['Proposed again without its LinkedIn post, which is growth-mindmake\'s since 13 November 2026: '
            + str(len(ids)) + ' go-live' + ('' if len(ids) == 1 else 's') + ' (' + ', '.join(ids) + ')'] + lines, \
        (withdraw, code)


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


def record_stops(root, proposals, decisions):
    """Record Krish's stops in the go-live ledger and return it: plans he stopped stay stopped,
    and declined check-ins whose plan is not known yet are listed as unresolved.

    The same rule claim_golives applies (control_center._stops), run in every loop
    run, so release (engine/run/release.py stopped_plans, unresolved_stops) and the
    mix plan readback read stops that were really written. Claims nothing and
    acts on nothing."""
    path = state_path(root, GOLIVE_LEDGER)
    given = [p for p in proposals or [] if isinstance(p, dict)]
    known = {p.get('proposal_id') for p in given}
    merged = given + [p for p in remembered_proposals(root) if p['proposal_id'] not in known]
    with locked(path):
        ledger = golive_ledger(root)
        stopped, unresolved = _stops(merged, decisions, ledger)
        ledger['stopped'].update({pid: why for pid, why in stopped.items() if pid not in ledger['stopped']})
        ledger['unresolved'] = dict(unresolved)
        write_json(path, {key: dict(sorted(ledger[key].items())) for key in ('acted', 'stopped', 'unresolved')})
    return ledger


def decisions_since(root, now):
    path = state_path(root, 'decisions.json')
    try:
        return instant(read_json(path)['read_at'])
    except (OSError, ValueError, KeyError, TypeError):
        return instant(now) - dt.timedelta(days=7)


VOICE_RULES_FILE = 'voice-rules.txt'
INSPIRATION_FILE = 'inspiration.txt'
# AEO-Engine's win kits and misses for the answer job (proposed 1.23.0); local and ignored, never a public log.
AI_ANSWERS_FILE = 'ai-answers.txt'
WEB_ANALYTICS_FILE = 'web-analytics.json'


def web_analytics_block(directive):
    """The `web_analytics` block (protocol 1.10.0) beside the directive or inside it, else None."""
    if not isinstance(directive, dict):
        return None
    block = directive.get('web_analytics')
    if not isinstance(block, dict) and isinstance(directive.get('directive'), dict):
        block = directive['directive'].get('web_analytics')
    return block if isinstance(block, dict) else None


def keep_web_analytics(root, directive):
    """Keep today's `web_analytics` (protocol 1.10.0) for the Measurement Specialist.

    The local, ignored file is replaced at every fresh start, and removed when
    the directive carries no block, so yesterday's readings never stand in for
    today's. The numbers stay private: they go back in the report, never into
    this public repository.
    """
    path = state_path(root, WEB_ANALYTICS_FILE)
    block = web_analytics_block(directive)
    if isinstance(block, dict):
        write_json(path, block)
    elif path.exists():
        path.unlink()
    return path if isinstance(block, dict) else None


SUBSCRIBERS_FILE = 'subscribers.json'
SUBSCRIBERS_FEATURE = 'subscriber_sources'
SUBSCRIBER_COUNTS = ('total', 'organic', 'paid', 'this_week_so_far')


def _count(value):
    """A whole count of zero or more, else None: a missing figure stays missing, never 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def subscribers_block(directive):
    """New subscribers by source, as Control Center counts them from Substack's own notices (audit 2026-11-14,
    I-09), or None.

    Served only behind features.subscriber_sources, as `subscribers { rule, week_of, total, organic, paid,
    by_source, unclassified[], this_week_so_far, read_on }`: counts and Substack's own source labels only,
    absent when unread, never 0. Read tolerantly: a malformed field is left out, never repaired or invented;
    by_source may be {label: count} or [{source, count}]. Nothing here moves a weight in the mix: Krish rules
    on that first."""
    if not isinstance(directive, dict):
        return None
    body = directive.get('directive') if isinstance(directive.get('directive'), dict) else directive
    features = body.get('features') if isinstance(body.get('features'), dict) else {}
    block = body.get('subscribers')
    if features.get(SUBSCRIBERS_FEATURE) is not True or not isinstance(block, dict):
        return None
    week = block.get('week_of')
    if not isinstance(week, str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', week):
        return None
    raw = block.get('by_source')
    pairs = raw.items() if isinstance(raw, dict) else [
        (r.get('source'), r.get('count')) for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    by_source = {}
    for label, count in pairs:
        label = _wa_text(label, 80)
        if label and _count(count) is not None:
            by_source[label] = by_source.get(label, 0) + count
    unclassified = [u for u in (block.get('unclassified') or []) if isinstance(block.get('unclassified'), list)
                    and isinstance(u, (str, dict))]
    out = {'week_of': week, 'by_source': dict(sorted(by_source.items())), 'unclassified_n': len(unclassified),
           'rule': _wa_text(block.get('rule'), 300),
           'read_on': block.get('read_on') if isinstance(block.get('read_on'), str) else None}
    out.update({key: _count(block.get(key)) for key in SUBSCRIBER_COUNTS})
    return out


def keep_subscribers(root, directive):
    """Keep today's subscribers block in the ignored .scratch/cc/, as keep_web_analytics keeps its block: replaced at
    every fresh start and removed when the directive carries none, so last week's reading never stands in."""
    path = state_path(root, SUBSCRIBERS_FILE)
    block = subscribers_block(directive)
    if block is not None:
        write_json(path, block)
    elif path.exists():
        path.unlink()
    return path if block is not None else None


def subscribers_line(block):
    """What a public log may say: whether the block was read and its shape, never a count."""
    if block is None:
        return 'subscribers by source: not served (the weekly Substack read in jobs/subscribers.md stands)'
    return ('subscribers by source: read for the week of ' + block['week_of'] + ', ' + str(len(block['by_source']))
            + ' sources, ' + str(block['unclassified_n']) + ' unclassified')


WA_DIMS = ('source_medium', 'landing_page', 'utm_content')
_WA_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')
_WA_TEXT = re.compile(r'[^A-Za-z0-9 ,.:;()/_-]+')


def _wa_text(value, limit=160):
    """Control Center's words, one line, plain characters only, for a public log."""
    if not isinstance(value, str) or not value.strip():
        return None
    return ' '.join(_WA_TEXT.sub(' ', value).split())[:limit] or None


def web_analytics_summary(block):
    """What the runner may say about the block: shape only, never a value or a per-page count.

    property, through and days; how many rows of each dim_type; whether coverage
    is complete and why not; and the event names with their key_event flags.
    """
    if not isinstance(block, dict):
        return {'present': False}
    rows = block.get('rows')
    counts = None
    if isinstance(rows, list):
        counts = {dim: sum(1 for r in rows if isinstance(r, dict) and r.get('dim_type') == dim) for dim in WA_DIMS}
    coverage = block.get('coverage') if isinstance(block.get('coverage'), dict) else {}
    events = block.get('events')
    names = None
    if isinstance(events, list):
        names = [{'name': e['name'] if _WA_NAME.match(e['name']) else '(unreadable name)', 'key': e.get('key_event') is True}
                 for e in events if isinstance(e, dict) and isinstance(e.get('name'), str)]
    days = block.get('days')
    through = block.get('through')
    return {'present': True, 'property': _wa_text(block.get('property'), 40),
            'through': through if isinstance(through, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', through) else None,
            'days': days if isinstance(days, int) and not isinstance(days, bool) else None,
            'rows': counts, 'complete': coverage.get('complete') is True,
            'reason': _wa_text(coverage.get('reason')), 'events': names}


def web_analytics_line(summary):
    """The one public log line: counts of rows per dim_type, coverage, event names. No values."""
    if not summary.get('present'):
        return "web_analytics: not in today's directive"
    rows = summary['rows']
    part = ('rows ' + ' '.join(dim + '=' + str(rows[dim]) for dim in WA_DIMS)) if rows is not None else 'rows not read'
    coverage = 'complete' if summary['complete'] else 'incomplete' + (' (' + summary['reason'] + ')' if summary['reason'] else '')
    events = summary['events']
    names = ('none' if not events else ','.join(e['name'] + ('(key)' if e['key'] else '') for e in events)) \
        if events is not None else 'not read'
    return 'web_analytics: ' + part + '; coverage=' + coverage + '; events=' + names


def web_analytics_activity(summary):
    """The report's line: the same shape, with the property, end date and window."""
    if not summary.get('present'):
        return "Today's directive carried no web_analytics block, so nothing from GA4 was kept"
    head = ('web_analytics for property ' + str(summary['property'] or 'unnamed') + ' through '
            + str(summary['through'] or 'an unstated date') + ' over ' + (str(summary['days']) + ' days' if summary['days'] else 'an unstated window'))
    return head + ': ' + web_analytics_line(summary)[len('web_analytics: '):]


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


INSPIRATION_USE = ('These are Krish\'s own suggestions. Treat them as the baseline standard for every week, piece and '
                   'express idea you plan: schedule a trial of each one he tagged, or say in the spec why it waits. '
                   'Rebuild a source in the publication\'s own voice and look; never copy it. Quote his_words as his; '
                   'agreed_reasons are guesses he tapped, never his words. Nothing that checks, scores, ranks or '
                   'queues a draft reads this block.')
# Protocol 1.21.0 (Ruling, Krish, 2026-11-12: an inspiration card he ticks is an instruction that jumps the queue:
# Production means use the style within a week). A card he ticked is not a suggestion.
INSTRUCTION_USE = ('MUST USE: Krish ticked these as instructions, not inspiration. Use each style in your next fitting '
                   'asset (a carousel, a meme or an off-day post) before its date, rebuilt in our voice and look, '
                   'never copied. Name the card as the concept\'s style_card in the mocks file, so the report says it '
                   'was used (inspiration_used) and his tick closes.')


def inspiration_suggestions(directive):
    """Krish's suggestions from his inspiration board (protocol 1.15.0 `inspiration`).

    Returns (state, rule, suggestions). state is 'absent' when the directive
    carries no readable block (Control Center could not read the board today,
    or speaks an older 1.x), 'none' when he has suggested nothing yet and
    'suggestions' otherwise. Malformed entries are dropped, never repaired or
    invented. Like the voice rules, they feed planning and drafting only."""
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    block = body.get('inspiration') if isinstance(body, dict) else None
    if not isinstance(block, dict) or not isinstance(block.get('suggestions'), list):
        return 'absent', None, []
    rule = block.get('rule') if isinstance(block.get('rule'), str) and block['rule'].strip() else None
    text = lambda item, key: item[key].strip() if isinstance(item.get(key), str) and item[key].strip() else None
    strings = lambda item, key: [w.strip() for w in item.get(key) or [] if isinstance(w, str) and w.strip()]
    out = []
    for item in block['suggestions']:
        if not isinstance(item, dict) or not text(item, 'card_id'):
            continue
        trials = [{'trial': t['trial'], 'label': text(t, 'label') or t['trial'], 'means': text(t, 'means')}
                  for t in item.get('trials') or [] if isinstance(t, dict) and isinstance(t.get('trial'), str)]
        raw = item.get('instruction')
        instruction = ({'action_id': text(raw, 'action_id'), 'kind': 'copy_style', 'due_at': text(raw, 'due_at'),
                        'overdue': raw.get('overdue') is True, 'words': text(raw, 'words')}
                       if isinstance(raw, dict) and raw.get('kind') == 'copy_style' and text(raw, 'due_at') else None)
        out.append({'instruction': instruction, 'card_id': text(item, 'card_id'), 'name': text(item, 'name'), 'kind': text(item, 'kind'),
                    'lane': text(item, 'lane'), 'trials': trials, 'his_words': strings(item, 'his_words'),
                    'agreed_reasons': strings(item, 'agreed_reasons'), 'note_for_claude': text(item, 'note_for_claude'),
                    'read_as': text(item, 'read_as'), 'post_url': text(item, 'post_url'),
                    'drive_url': text(item, 'drive_url'), 'saved_at': text(item, 'saved_at')})
    # His instructions first, the soonest due first (Control Center sends them so; kept so here too).
    out.sort(key=lambda i: (i['instruction'] is None, (i['instruction'] or {}).get('due_at') or ''))
    return ('suggestions' if out else 'none'), rule, out


def instruction_cards(directive):
    """The card ids Krish ticked as a style to use (protocol 1.21.0), from today's directive."""
    return [i['card_id'] for i in inspiration_suggestions(directive)[2] if i['instruction']]


def used_served(directive):
    """True only when the served directive says features.inspiration_used."""
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    features = body.get('features') if isinstance(body, dict) else None
    return isinstance(features, dict) and features.get('inspiration_used') is True


def inspiration_used_field(root, now, directive):
    """The cards Krish ticked as a style to use that a concept with its mocks made in that style names
    (style_card, the mocks file), from this week's and next week's mix plan, as protocol 1.21.0 inspiration_used;
    None when the directive does not serve it or nothing used one. What was made is said in words: the lane and
    the idea, never an address or a link."""
    if not used_served(directive):
        return None
    wanted = set(instruction_cards(directive))
    if not wanted:
        return None
    used, monday = {}, next_monday(now) - dt.timedelta(days=7)
    for day in (monday, monday + dt.timedelta(days=7)):
        path = Path(root) / MIX_DIR / ('plan-' + day.isoformat() + '.json')
        if not path.is_file():
            continue
        try:
            concepts = read_json(path).get('concepts') or []
        except (ValueError, OSError, AttributeError):
            continue
        for c in concepts:
            card = str(c.get('style_card') or '').lower() if isinstance(c, dict) else ''
            if card not in wanted or card in used or not c.get('ready'):
                continue
            words = ' '.join(str(c.get('idea') or '').split())
            words = re.sub(r'https?://\S+|\S+@\S+', '', words).strip()
            asset = (str(c.get('lane') or 'post').replace('_', ' ') + ' for the week of ' + day.isoformat()
                     + (': ' + words if words else ''))[:200]
            used[card] = {'card_id': card, 'asset': asset, 'made_at': None}
    return list(used.values()) or None


def inspiration_block(directive):
    """The labelled block a planning or drafting step reads. Local only, never a public log."""
    state, rule, items = inspiration_suggestions(directive)
    lines = ["KRISH'S INSPIRATION BOARD (the baseline for what you plan; from today's directive)"]
    if state == 'absent':
        lines += ['  Could not be read today. Do not invent his suggestions: plan from AGENTS.md and the playbook as before.']
        return lines
    lines.append('  ' + INSPIRATION_USE)
    if rule:
        lines.append("  Control Center's rule: " + ' '.join(rule.split()))
    if state == 'none':
        lines.append('  He has suggested nothing yet. Do not invent any.')
        return lines
    tried = [i for i in items if i['trials']]
    told = [i for i in items if i['instruction']]
    if told:
        lines.append('  ' + INSTRUCTION_USE)
    lines.append('  ' + str(len(told)) + ' he ticked as an instruction, ' + str(len(tried)) + ' with a trial he tagged, '
                 + str(len(items)) + ' in all; his instructions first, then newest first.')
    for number, item in enumerate(items, 1):
        head = str(number) + '. ' + (item['name'] or item['card_id'])
        head += ' (' + ', '.join(x for x in (item['kind'], item['lane'], item['saved_at']) if x) + ')'
        if item['instruction']:
            due = (item['instruction']['due_at'] or '')[:10]
            head = ('PAST DUE ' if item['instruction']['overdue'] else '') + 'MUST USE BY ' + due + ': ' + head
        lines.append('  ' + head)
        if item['instruction']:
            lines.append('     card id (name it as the concept\'s style_card): ' + item['card_id'])
            if item['instruction']['words']:
                lines.append('     his instruction: "' + ' '.join(item['instruction']['words'].split()) + '"')
        if item['trials']:
            lines.append('     try: ' + '; '.join(t['label'] + (' (' + t['means'] + ')' if t['means'] else '') for t in item['trials']))
        for words in item['his_words']:
            lines.append('     his words: "' + ' '.join(words.split()) + '"')
        if item['agreed_reasons']:
            lines.append('     reasons he agreed with: ' + '; '.join(item['agreed_reasons']))
        if item['read_as'] or item['note_for_claude']:
            lines.append('     how to read it: ' + ' '.join(x for x in (item['read_as'], item['note_for_claude']) if x))
        for key, label in (('post_url', 'post'), ('drive_url', 'file')):
            if item[key]:
                lines.append('     ' + label + ': ' + item[key])
    lines.append('END OF INSPIRATION BOARD')
    return lines


def describe(directive, ledger=None):
    """A short local summary of the directive, Krish's instruction first. Never used on a public runner log."""
    body = directive.get('directive', {}) if isinstance(directive, dict) else {}
    action = body.get('next_action') or {}
    lines = engine_state.block(directive, ledger)
    lines += ['directive ' + str(body.get('directive_id')) + ' (chosen by ' + str(directive.get('chosen_by')) + ')',
             'next action: ' + str(action.get('instruction')), 'why: ' + str(action.get('why'))]
    if action.get('proposal_id'):
        lines.append('proposal: ' + str(action['proposal_id']))
    for item in body.get('objectives', []):
        lines.append('objective ' + str(item.get('key')) + ': latest ' + str(item.get('latest')) + ' '
                     + str(item.get('unit')) + ', target ' + str(item.get('target')) + ', ' + str(item.get('availability')))
    state, _, items = inspiration_suggestions(directive)
    lines.append('inspiration board: ' + ('could not be read today' if state == 'absent' else
                 str(sum(1 for i in items if i['trials'])) + ' tagged trials, ' + str(len(items)) + ' suggestions in '
                 + state_label(INSPIRATION_FILE)))
    from . import ai_answers
    if ai_answers.detail_served(directive):
        n = len(ai_answers.kits(ai_answers.standing(directive)))
        lines.append('AI-answer kits: ' + str(n) + ' from AEO-Engine in ' + state_label(AI_ANSWERS_FILE))
    lines.append(subscribers_line(subscribers_block(directive)))
    return lines + voice_block(directive)


def state_label(name):
    return str(Path(STATE_DIR) / name)


def summary(outcome, public=False, matched=None):
    lines = []
    if outcome.get('state_dropped'):
        lines.append('engine state not taken (' + outcome['state_dropped'] + '); reported without it')
    if outcome.get('degraded'):
        lines.append('engagement task not taken (' + outcome['degraded'] + '); the same taps went as one plain ask')
    posted = outcome.get('posted') or {}
    if outcome.get('report'):
        lines.append('report ' + outcome['report']['run_id'] + ' ' + outcome['report']['status']
                     + ', payload_sha256 ' + outcome['report']['payload_sha256'])
        if outcome['report'].get('withdrawn'):
            lines.append('asks taken back, their week or window over: ' + str(len(outcome['report']['withdrawn'])))
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
    if args.cc_cmd == 'backstop':
        from . import backstop
        counts = backstop.post(make_client() if args.deliver else None, root, args.deliver)
        out('backstop: ' + ' '.join(k + '=' + str(counts[k]) for k in ('waiting', 'filed', 'duplicate', 'refused'))
            + ('' if args.deliver else ' (dry run: no Control Center call)')
            + (' error=' + counts['error'] if counts['error'] else ''))
        return int(bool(counts['error']))
    if args.cc_cmd == 'runner':
        dispatched = os.environ.get('CC_DISPATCH_ENGINE_ID', '').strip()
        if dispatched and dispatched != ENGINE_ID:
            out('Not ready: the dispatch named another engine; nothing was run')
            return 1
        # The 05:40 UTC backup reports under its own run_id, so it never conflicts with the dispatch's report, and
        # a second wake the same day (Krish's instruction, protocol 1.20.0) under its own discriminator.
        wake = getattr(args, 'wake', None)
        run_id = args.run_id or runner_run_id(now, getattr(args, 'backup', False), wake)
        if not args.deliver:
            report, error = runner_report(root, run_id, now, checks(root), args.mode, sent={})
            out('Dry run: no Control Center call. Report ' + report['status'] + ', payload_sha256 ' + report['payload_sha256'])
            return int(bool(error))
        client = make_client()
        from .backlog import for_runner
        seen = {}

        def build(directive):
            # Keep the block for the measure job, and say what it holds, shape only.
            keep_web_analytics(root, directive)
            keep_subscribers(root, directive)
            seen['web'] = web_analytics_summary(web_analytics_block(directive))
            lines = ['Kept for the measure job: ' + web_analytics_activity(seen['web']),
                     subscribers_line(subscribers_block(directive))]
            # The share of each prepaid pool (1.16.0); the runner spends none of it (docs/CREDITS.md is how a session does).
            lines += credits_lines(credits_block(directive)) + [meter.cost_line('before this report')]
            # AI answers are AEO-Engine's (protocol 1.22.0; Ruling, Krish, 2026-11-12): one line, and real reader questions to AEO.
            # His yes on the proposed questions is written first, so the same run asks AEO for them (Ruling, Krish, 2026-11-13).
            from . import ai_answers
            try:
                decided = _decisions_until(client, clock())
            except ProtocolError:
                decided = None
            written, event = ai_answers.approved_write(root, decided, clock())
            lines += written
            lines += ai_answers.sync(client, directive, root, clock())
            # Krish's instruction (1.20.0): 'received' once, so an earlier report naming it counts.
            state, item = engine_state.instruction(directive)
            told = bool(state == 'open' and engine_state.served(directive) and engine_state.mentioned(client, item['id']))
            sent = already_sent(client, clock(), directive, args.mode, include_today=bool(wake))
            # Its go-lives still waiting from before LinkedIn went to growth-mindmake (Ruling, Krish, 2026-11-13):
            # each is proposed again without its LinkedIn line, or taken back when that was all it held.
            golives = None
            if args.mode == 'live':
                lines_again, golives = handed_off_golives(client, sent, clock(), root)
                lines += lines_again
            # Its own asks for weeks that are over, read from its own records (engine/stale_asks.py).
            return runner_report(root, run_id, clock(), checks(root), args.mode, True,
                                 sent=sent, backlog=for_runner(root, clock()),
                                 gap=intensity.state(root, clock(), directive), extra_activity=lines,
                                 directive=directive, seen=told, events=[event] if event else [],
                                 weeks=stale_asks.week_candidates(client, clock()), golives=golives)

        loop = Loop(client, 'runner', run_id, clock)
        try:
            loop.start()
            outcome = loop.finish(build, now - dt.timedelta(days=7))
        except ProtocolError as error:
            outcome = loop.end('failed', error.code)
        if 'web' in seen:
            out(web_analytics_line(seen['web']))
        if loop.directive is not None:
            # His instruction by id and what was acked, never his words: this log is public.
            out(engine_state.public_line(loop.directive, (outcome.get('report') or {}).get('instruction_acks') or []))
        for line in summary(outcome, public=True):
            out(line)
        out(meter.cost_line('in all'))
        return int(outcome['status'] != 'succeeded')

    job = args.job
    run_id = args.run_id or run_id_for(job, now)
    saved = state_path(root, job + '.state.json')
    voice_file = state_path(root, VOICE_RULES_FILE)
    instruction_file = state_path(root, engine_state.INSTRUCTION_FILE)
    instruction_json = state_path(root, engine_state.INSTRUCTION_JSON)
    ledger_file = state_path(root, engine_state.LEDGER_FILE)
    if args.cc_cmd in ('start', 'run'):
        # Never let yesterday's rules or instruction stand in for today's, even on a dry run.
        for stale in (voice_file, instruction_file, instruction_json):
            if stale.exists():
                stale.unlink()
    acted = None
    if getattr(args, 'ack', None) or getattr(args, 'ack_line', None):
        acted = (args.ack, args.ack_line, getattr(args, 'ack_evidence', None))
    told, started = {'seen': False}, {'at': None}

    def build(directive, plain_taps=False):
        return workspace_report(job, run_id, clock(), _load_many(args.envelope),
                                read_json(args.queue) if args.queue else None,
                                [o for rows in _load_many(args.observations) for o in rows],
                                read_json(args.completions) if args.completions else None,
                                args.mode, directive is not None, root=root,
                                gap=intensity.state(root, clock(), directive), plain_taps=plain_taps,
                                directive=directive, seen=told['seen'], acted=acted,
                                started_at=started['at'])

    if not args.deliver:
        if args.cc_cmd == 'start':
            out('Dry run: no Control Center call. A scheduled run adds --deliver to journal the start and pull the directive.')
            return 0
        if acted:
            out("Not reported: a dry run has no directive, so there is no instruction of Krish's to ack")
            return 1
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
        inspiration_file = state_path(root, INSPIRATION_FILE)
        if inspiration_file.exists():
            inspiration_file.unlink()  # And today's board.
        answers_file = state_path(root, AI_ANSWERS_FILE)
        if answers_file.exists():
            answers_file.unlink()  # And today's AI-answer kits.
        try:
            write_json(saved, loop.start())
        except ProtocolError as error:
            outcome = loop.end('failed', error.code)
            out(summary(outcome)[-1])
            return 1
        # The drafting steps read this local, ignored file; nothing that checks,
        # scores or queues a draft does.
        voice_file.write_text('\n'.join(voice_block(loop.directive)) + '\n', encoding='utf-8')
        # His inspiration board (1.15.0), the baseline for what the plan schedules; local and ignored like the rules.
        inspiration_file.write_text('\n'.join(inspiration_block(loop.directive)) + '\n', encoding='utf-8')
        # AEO-Engine's win kits and misses (Ruling, Krish, 2026-11-13), which the answer job reads first; local and
        # ignored like the rules, since they hold question and kit words.
        from . import ai_answers
        answers_file.write_text('\n'.join(ai_answers.block(loop.directive)) + '\n', encoding='utf-8')
        # His instruction (1.20.0), which the job acts on first; local and ignored, never a public log.
        ledger = engine_state.read_ledger(ledger_file)
        instruction_file.write_text('\n'.join(engine_state.block(loop.directive, ledger)) + '\n', encoding='utf-8')
        # The same, structured, for the four engine sessions' engine start (local and ignored).
        engine_state.keep_local(instruction_json, loop.directive, clock())
        keep_web_analytics(root, loop.directive)
        keep_subscribers(root, loop.directive)
        for line in describe(loop.directive, ledger):
            out(line)
        if args.cc_cmd == 'start':
            out('attempt started: finish this job with growth.py cc finish --job ' + job + ' --deliver')
            return 0
    state, item = engine_state.instruction(loop.directive)
    if not acted and state == 'open':
        # What an engine session did with it (engine close), carried by this report: the one write path.
        pending = engine_state.pending_ack(engine_state.read_ledger(ledger_file), item['id'])
        if pending:
            errors = engine_state.workspace_ack_errors(pending['state'], pending['line'], pending.get('evidence_url'),
                                                       item)
            if errors:
                out("Not carried: the engine session's ack on Krish's instruction (" + '; '.join(errors) + ')')
            else:
                acted = (pending['state'], pending['line'], pending.get('evidence_url'))
                out("Carrying the " + str(pending.get('engine')) + " engine session's ack on Krish's instruction: "
                    + pending['state'])
    if acted:
        errors = engine_state.workspace_ack_errors(acted[0], acted[1], acted[2], item if state == 'open' else None)
        if errors:
            # Nothing is reported yet: the attempt stays started, so this finish can be run again, fixed.
            out('Not reported: ' + '; '.join(errors))
            return 1
        if not engine_state.served(loop.directive):
            out("Not acked: today's directive does not serve engine_state yet, so the report goes without the ack")
    started['at'] = loop.started_at
    if state == 'open' and engine_state.served(loop.directive):
        acked = (engine_state.read_ledger(ledger_file).get(item['id']) or {}).get('acks')
        told['seen'] = bool(acked) or bool(engine_state.mentioned(client, item['id']))
    since = decisions_since(root, now)
    outcome = loop.finish(build, since, degrade=lambda d: build(d, plain_taps=True))
    if outcome.get('report'):
        write_json(state_path(root, 'report-' + job + '.json'), outcome['report'])
    posted = outcome.get('posted') or {}
    if posted.get('accepted') and not posted.get('conflict'):
        engine_state.remember_acks(ledger_file, outcome['report'].get('instruction_acks') or [])
    matched = None
    if 'decisions' in outcome:
        matched = remember(root, outcome['report'], outcome['decisions'], now)
        # His decision on the week's mix plan reaches decision.json here, in this run, before the next read
        # replaces decisions.json (engine/run/decision.py, R101). Local writes only.
        from .run.decision import after_readback
        for line in after_readback(root, matched, now):
            out(line)
    if outcome.get('attempt_journaled') and saved.exists():
        saved.unlink()
    for line in summary(outcome, matched=matched):
        out(line)
    return int(outcome['status'] != 'succeeded')
