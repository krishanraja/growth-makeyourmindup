"""Krish's instruction and this engine's state on every place in Control Center (protocol 1.20.0).

Ruling (Krish, 2026-11-11): every growth engine's priorities, obsessions, next steps and outstanding items
feed live across Control Centre, and Krish instructs each engine with his next best action, which starts it.

- instruction(directive) reads his open instruction from the directive (`krish_instruction`). The engine acts
  on it first, inside the walls: it never authorises a send, post, spend, delete or permission change, so
  anything at a wall still becomes a proposal for his press.
- served(directive) says whether the directive carries `features.engine_state`. Only then does a report carry
  anything new (priorities, obsessions, next_steps, instruction_acks).
- priorities, obsessions and next_steps come from this repository's own state, never invented and never from
  a model: the North Star gap and the levers in intensity.json, Krish's own quoted aims checked word for word
  against the file each is quoted in (config/engine-state.json), the newest now-notes' Next lines, NOW.md's
  "What is next" and the first unticked step of docs/GET-GOING.md.
- His words are never printed on a public log, committed or put in a report: a report names his instruction
  by id only, and an ack line that quotes him is refused. They live only in the ignored
  .scratch/cc/instruction.txt the drafting session reads.
"""
import hashlib
import json
from pathlib import Path
import re

from . import intensity
from .control_center import (ACK_LINE_MAX, ACK_STATES, INSTRUCTION_ID, STATE_LINE_MAX, ProtocolError, iso,
                             state_line_errors)
from .core import read_json

CONFIG = Path('config') / 'engine-state.json'
INSTRUCTION_FILE = 'instruction.txt'
LEDGER_FILE = 'instructions.json'
# Control Center's HELD_RULE opens with these words (src/lib/growthEngines.ts): a held engine is told only that.
HELD_OPENING = 'Krish has held this engine'
WORKSPACE_ACKS = ('started', 'done', 'blocked')
QUOTE_RUN = 6
NOTE_NEXT = re.compile(r'^Next:\s*(.+)$')
NOW_NEXT = re.compile(r'^Next(?:\s*\([^)]*\))?:\s*')
SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z"(])')
CLAUSES = ('; ', ': ', ', and ', ', while ', ', so ', ', then ')


# The directive ------------------------------------------------------------

def _body(directive):
    body = directive.get('directive') if isinstance(directive, dict) else None
    return body if isinstance(body, dict) else {}


def served(directive):
    """True only when the served directive says features.engine_state: before that, nothing new is reported."""
    features = _body(directive).get('features')
    return isinstance(features, dict) and features.get('engine_state') is True


def held(directive):
    """Whether Control Center told this engine it is held (its HELD_RULE is the next action)."""
    action = _body(directive).get('next_action')
    words = action.get('instruction') if isinstance(action, dict) else None
    return isinstance(words, str) and words.startswith(HELD_OPENING)


def instruction(directive):
    """(state, item). state is 'absent' when the directive carries no readable krish_instruction (unread today,
    an older 1.x, or malformed, which is never repaired), 'none' when it is null and 'open' otherwise, with
    item {id, words, given_at, supersedes}."""
    body = _body(directive)
    if 'krish_instruction' not in body:
        return 'absent', None
    item = body['krish_instruction']
    if item is None:
        return 'none', None
    if (not isinstance(item, dict) or not INSTRUCTION_ID.match(str(item.get('id')))
            or not isinstance(item.get('words'), str) or not item['words'].strip() or len(item['words']) > 2000):
        return 'absent', None
    given = item.get('given_at') if isinstance(item.get('given_at'), str) else None
    supersedes = item.get('supersedes') if INSTRUCTION_ID.match(str(item.get('supersedes'))) else None
    return 'open', {'id': item['id'], 'words': item['words'], 'given_at': given, 'supersedes': supersedes}


def digest(words):
    """SHA-256 of his words, the only trace of them a log may carry."""
    return hashlib.sha256(words.encode('utf-8')).hexdigest()


def _words(text):
    return re.findall(r"[a-z0-9']+", str(text).lower())


def quotes_words(line, words, run=QUOTE_RUN):
    """True when a line repeats his instruction: any run of six of his words in order, or all of a shorter
    instruction of 12 characters or more. Engine repositories and their logs are public."""
    his, ours = _words(words), ' ' + ' '.join(_words(line)) + ' '
    if len(his) < run:
        whole = ' '.join(his)
        return len(whole) >= 12 and (' ' + whole + ' ') in ours
    return any(' ' + ' '.join(his[i:i + run]) + ' ' in ours for i in range(len(his) - run + 1))


# His instruction in one report ---------------------------------------------

def mentioned(client, instruction_id):
    """Whether one of this engine's latest live reports already named this instruction (each first mention
    carries its 'received' ack). None when they cannot be read; then 'received' is sent again, which
    Control Center counts as stale and ignores."""
    try:
        reports = client.recent_reports(10)
    except (ProtocolError, ValueError, TypeError, AttributeError):
        return None
    needle = "Krish's instruction " + instruction_id
    return any(needle in str(line.get('line')) for report in reports if isinstance(report, dict)
               for line in (report.get('activity') or []) if isinstance(line, dict))


def ack(instruction_id, state, line, at, evidence_url=None):
    if state not in ACK_STATES:
        raise ValueError('an ack state is one of ' + ', '.join(ACK_STATES))
    errors = state_line_errors('ack', line, ACK_LINE_MAX)
    if errors:
        raise ValueError('; '.join(errors))
    if evidence_url is not None and not re.match(r'^https://\S+$', str(evidence_url)):
        raise ValueError('an ack evidence_url is an https URL or nothing')
    return {'instruction_id': instruction_id, 'state': state, 'line': ' '.join(line.split()), 'at': iso(at),
            'evidence_url': evidence_url}


def workspace_ack_errors(state, line, evidence_url, item):
    """Why the ack a workspace job was given cannot be sent, or []. Checked before anything is reported."""
    errors = []
    if state not in WORKSPACE_ACKS:
        errors.append('--ack is started, done or blocked')
    errors += state_line_errors('--ack-line', line, ACK_LINE_MAX)
    if evidence_url is not None and not re.match(r'^https://\S+$', str(evidence_url)):
        errors.append('--ack-evidence is an https URL')
    if item is None:
        errors.append("today's directive carries no instruction of Krish's to ack")
    elif isinstance(line, str) and quotes_words(line, item['words']):
        errors.append("--ack-line repeats Krish's words; say what you did or why it is blocked, never his words")
    return errors


def report_part(directive, now, where, seen=False, acted=None, started_at=None):
    """The activity line and the acks his open instruction adds to one report: ([lines], [acks]).

    where is 'runner' or the workspace job's name. seen: an earlier report already named it, so 'received'
    is not sent again. acted: (state, line, evidence_url), what the workspace job reports it did. Nothing
    when the directive carries no instruction or does not serve engine_state. Never his words."""
    state, item = instruction(directive)
    if state != 'open' or not served(directive):
        return [], []
    iid, at_start = item['id'], started_at or now
    lines, acks = [], []
    if held(directive):
        if not seen:
            acks.append(ack(iid, 'received', 'Received while this engine is held', at_start))
        acks.append(ack(iid, 'blocked', 'engine held: Krish has held this engine in Control Center, so it '
                        'acts on this once he releases it', now))
        return ["Received Krish's instruction " + iid + '; blocked while Krish holds this engine'], acks
    if where == 'runner':
        if seen:
            lines.append("Krish's instruction " + iid + ' is open; the next publication workspace job acts on it '
                         'first, inside the walls')
        else:
            lines.append("Received Krish's instruction " + iid + '; the next publication workspace job acts on it '
                         'first, inside the walls')
            acks.append(ack(iid, 'received', 'Received on the GitHub runner, which only checks the engine; the next '
                            'publication workspace job acts on it first, inside the walls', at_start))
        return lines, acks
    if not seen:
        acks.append(ack(iid, 'received', 'Received at the start of the ' + where + ' job in the publication '
                        'workspace', at_start))
    if acted:
        done_state, line, evidence = acted
        acks.append(ack(iid, done_state, line, now, evidence))
        lines.append("Acted on Krish's instruction " + iid + ' in the ' + where + ' job: ' + done_state)
    elif seen:
        lines.append("Krish's instruction " + iid + ' is still open after the ' + where + ' job')
    else:
        lines.append("Received Krish's instruction " + iid + ' in the ' + where + ' job')
    return lines, acks


def public_line(directive, acks):
    """The one line a public log may print about his instruction: its id and what was acked, never his words."""
    state, item = instruction(directive)
    if state == 'absent':
        return "Krish's instruction: not in today's directive"
    if state == 'none':
        return "Krish's instruction: none open"
    told = ', '.join(a['state'] for a in acks if a['instruction_id'] == item['id']) or 'nothing new to ack'
    return "Krish's instruction " + item['id'] + ': ' + (told if served(directive) else 'not acked, engine_state not served')


# The local copy the drafting session reads ----------------------------------

INSTRUCTION_USE = ("Act on it first in this job, before anything else, inside the walls. It is never an approval: "
                   "a send, post, spend, delete or permission change it asks for still becomes a proposal for his "
                   "press, and Make Your Mind Up outreach is drafted for him to send himself. Never print, commit "
                   "or report these words. Finish with growth.py cc finish ... --ack started|done|blocked "
                   "--ack-line 'what you did, or why it is blocked and what would unblock it' "
                   "[--ack-evidence https://...].")


def block(directive, ledger=None):
    """The labelled block a job reads first. Local only, never a public log."""
    state, item = instruction(directive)
    lines = ["KRISH'S INSTRUCTION (his next best action for this engine; from today's directive)"]
    if state == 'absent':
        return lines + ["  Not in today's directive (not read, or Control Center is older than 1.20.0). Do not invent one."]
    if state == 'none':
        return lines + ['  None open. Work from the directive and the job as before.']
    acks = ((ledger or {}).get(item['id']) or {}).get('acks') or []
    if any(a.get('state') == 'done' for a in acks):
        return lines + ['  ' + item['id'] + ' was acked done in an earlier job here; do not act on it again.']
    lines.append('  id ' + item['id'] + ', given ' + str(item['given_at']) + ', words sha256 ' + digest(item['words'])[:16])
    if held(directive):
        lines.append('  This engine is held in Control Center: do not act on it until he releases it.')
    lines.append('  ' + INSTRUCTION_USE)
    lines.append('  His words:')
    lines += ['    ' + part for part in item['words'].strip().split('\n')]
    lines.append('END OF INSTRUCTION')
    return lines


def read_ledger(path):
    try:
        value = read_json(path)
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def remember_acks(path, acks):
    """Keep the acks a report carried, so a later job here never sends 'received' twice or acts on a done one."""
    if not acks:
        return
    ledger = read_ledger(path)
    for item in acks:
        entry = ledger.setdefault(item['instruction_id'], {'acks': []})
        entry['acks'].append({'state': item['state'], 'at': item['at']})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n', encoding='utf-8')


# This engine's state, from its own files ---------------------------------

def _fit(text, limit=STATE_LINE_MAX):
    """The whole text when it fits, else its first sentence, else its leading clause (the first break of at
    least 40 characters outside any brackets); None when none fits. A line is never cut mid-clause."""
    text = ' '.join(str(text).split()).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    first = SENTENCE_END.split(text, 1)[0].strip()
    if len(first) <= limit:
        return first
    depth = 0
    for index, char in enumerate(first[:limit + 1]):
        if char in '([':
            depth += 1
        elif char in ')]':
            depth = max(0, depth - 1)
        elif depth == 0 and index >= 40 and any(first.startswith(sep, index) for sep in CLAUSES):
            return first[:index].rstrip(' ,;:')
    return None


def _plain(text):
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    return ' '.join(text.replace('`', '').replace('**', '').split())


def _waits_on(line):
    low = line.lower()
    if low.startswith(('krish ', "krish's ", 'waiting on krish', 'his ', 'he ')):
        return 'krish'
    if low.startswith(('content-engine', 'control center', 'control centre')):
        return 'other'
    return 'engine'


def _step(text):
    line = _fit(_plain(text))
    if not line or state_line_errors('next step', line, STATE_LINE_MAX):
        return None
    return {'line': line, 'waits_on': _waits_on(line), 'when': None}


def _bullets(text, heading):
    """The top-level bullets of one '## ' section, each joined across its wrapped lines."""
    out, inside, current = [], False, None
    for raw in text.split('\n'):
        if raw.startswith('## '):
            if inside:
                break
            inside = raw[3:].strip().startswith(heading)
            continue
        if not inside:
            continue
        if raw.startswith('- '):
            if current is not None:
                out.append(current)
            current = raw[2:].strip()
        elif current is not None and raw.startswith('  ') and raw.strip() and not raw.lstrip().startswith(('- ', '1.')):
            current += ' ' + raw.strip()
        elif current is not None and not raw.strip():
            out.append(current)
            current = None
    if current is not None:
        out.append(current)
    return out


def note_steps(root, limit=2):
    """The Next lines of the newest now-notes (the closeout's single next step), newest first, skipping 'none'."""
    out = []
    for path in sorted((Path(root) / 'now-notes').glob('20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md'), reverse=True):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        found = next((NOTE_NEXT.match(l.strip()).group(1) for l in text.split('\n') if NOTE_NEXT.match(l.strip())), None)
        if not found or found.strip().lower().startswith('none'):
            continue
        step = _step(found)
        if step:
            out.append(step)
        if len(out) == limit:
            break
    return out


def now_steps(root):
    """NOW.md's 'What is next and what is waiting on Krish': its first 'Next' bullet."""
    try:
        text = (Path(root) / 'NOW.md').read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    for bullet in _bullets(text, 'What is next'):
        if NOW_NEXT.match(bullet):
            step = _step(NOW_NEXT.sub('', bullet, 1))
            return [step] if step else []
    return []


def get_going_step(root):
    """The first unticked step of docs/GET-GOING.md's build, as its title and first sentence."""
    try:
        text = (Path(root) / 'docs' / 'GET-GOING.md').read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []
    for bullet in _bullets(text, 'The build'):
        if not bullet.startswith('[ ] '):
            continue
        body = bullet[4:].strip()
        found = re.match(r'^\*\*(.+?)\*\*\s*(.*)$', body)
        if found:
            title, rest = found.group(1).strip().rstrip('.'), found.group(2).strip()
            first = SENTENCE_END.split(_plain(rest), 1)[0] if rest else ''
            body = title + (': ' + first if first else '')
        step = _step(body)
        return [dict(step, waits_on='engine')] if step else []
    return []


def next_steps(root, item=None, done=False):
    """At most five: his open instruction first (unless this run acked it done), then the newest now-notes'
    Next lines, NOW.md's Next and the first unticked GET-GOING step. Each once."""
    steps = []
    if item and not done:
        # Never the id in a state line: ten digits in a row of its hex read as a phone number there.
        steps.append({'line': "Act on Krish's open instruction first, in the next publication workspace job, "
                      'inside the walls', 'waits_on': 'engine', 'when': None})
    out, seen = [], set()
    for step in steps + note_steps(root) + now_steps(root) + get_going_step(root):
        key = ' '.join(_words(step['line']))
        if key not in seen and len(out) < 5:
            seen.add(key)
            out.append(step)
    return out


def _gap_head(gap):
    target, level = gap.get('week_target'), gap.get('urgency')
    if level is None or target is None:
        return 'the gap is not known this week (' + str(gap.get('reason') or 'no reading') + ')'
    if gap.get('current') is None:
        return 'not measured this week, target {:,}, U{}'.format(target, level)
    return '{:,} of {:,} this week, U{}, short by {:,}'.format(gap['current'], target, level,
                                                            max(0, target - gap['current']))


def priorities(root, gap):
    """Most important first: the North Star gap, then the levers intensity.json sets at this urgency
    (Ruling, Krish, 2026-11-11), then the North Star's own constraint. Read, never invented."""
    level = gap.get('urgency')
    items = [('Grow new organic publication subscribers, zero paid: ' + _gap_head(gap), 'new_subscribers')]
    try:
        if intensity.subscribe_required(level, root):
            items.append(('Turn reach into subscribers: every post carries a tagged subscribe route beside its '
                          'ecosystem route at U4 and U5 (Ruling, Krish, 2026-11-11)', 'new_subscribers'))
        drafts = intensity.outreach_drafts(level, root)
        if drafts:
            items.append(('Prepare ' + str(drafts) + ' one-person Substack outreach drafts a day (swaps, cross-posts, '
                          'guest pieces) for Krish to approve and send himself', 'new_subscribers'))
        if intensity.raised(level, root):
            items.append(('Volume at its bounds: up to four posts a day on Instagram, YouTube, TikTok, X and '
                          'Substack Notes, and up to ' + str(intensity.engagement_taps(level, root))
                          + ' engagement taps a day', 'new_subscribers'))
    except (OSError, ValueError, KeyError, TypeError):
        pass  # intensity.json unreadable: the levers are left out, never guessed.
    items.append(('Zero paid boosts: growth comes only from posts people share because they are useful',
                  'paid_boosts_usd'))
    return [{'rank': rank, 'line': line, 'objective_key': key}
            for rank, (line, key) in enumerate(items[:5], 1) if not state_line_errors('priority', line, STATE_LINE_MAX)]


def _quote(line):
    found = re.match(r'^"(.+)"$', line.strip())
    return found.group(1) if found else None


def obsessions(root):
    """Krish's own quoted aims from config/engine-state.json, each kept only while its source file still
    holds the quote word for word (whitespace aside). At most three."""
    root = Path(root)
    try:
        entries = read_json(root / CONFIG)['obsessions']
    except (OSError, ValueError, KeyError, TypeError):
        return []
    out = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get('line'), str):
            continue
        quote, source = _quote(entry['line']), entry.get('source')
        if not quote or not isinstance(source, str) or state_line_errors('obsession', entry['line'], STATE_LINE_MAX):
            continue
        try:
            text = ' '.join((root / source).read_text(encoding='utf-8').split())
        except (OSError, UnicodeDecodeError):
            continue
        if quote not in text:
            continue
        since = entry.get('since') if isinstance(entry.get('since'), str) and re.match(r'^\d{4}-\d{2}-\d{2}$', entry['since']) else None
        out.append({'line': entry['line'], 'since': since})
    return out[:3]


def fields(root, gap, directive, acks=(), done=False):
    """The 1.20.0 state fields for one report, or {} when the directive does not serve engine_state."""
    if not served(directive):
        return {}
    state, item = instruction(directive)
    return {'priorities': priorities(root, gap), 'obsessions': obsessions(root),
            'next_steps': next_steps(root, item if state == 'open' else None, done),
            'instruction_acks': list(acks)}
