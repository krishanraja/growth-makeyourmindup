"""AI answers through AEO-Engine, the one specialist (protocol 1.22.0).

Ruling (Krish, 2026-11-12): "AEO-Engine becomes the one specialist that every
venture's growth engine calls for its AI-answer work. Each venture's tile
shows its own AI-answer standing ..."

This engine never asks an AI assistant itself. Each runner report:

- says the publication's AI-answer standing in one line, read from the
  directive (`ai_answers`, AEO's fortnightly research);
- when no request is on file with Control Center and config/ai-answer-questions.json
  holds real reader questions (jobs/answer.md adds them, never invented),
  asks AEO once to track them (`POST answers`), naming the publication's hosts.

Ruling (Krish, 2026-11-13): Make Your Mind Up's growth engine proposes its
AI-answer questions for his approval. So the runner also:

- sends the set in config/ai-answer-questions-proposed.json once, as one
  strategy proposal whose exact words are the questions, one a line, so he can
  change any line on his list before he approves (questions_proposal);
- on his yes, on exactly those words or his amended version (its digest
  checked), writes the approved questions into config/ai-answer-questions.json,
  marks the ask pending and reports the proposal done (approved_write); a
  question he has not approved is never written;
- asks AEO for the file's questions while that ask is pending, even with an
  older request on file (a newer request replaces it), and records the ask.

The weekly answer piece (jobs/answer.md) reads AEO's misses and moves for the
publication from the same block. Never fatal: a failure is one line.
"""
import json
from pathlib import Path
import re

from .control_center import _latest, amendment_ok, iso, proposal
from .core import write_json

QUESTIONS = 'config/ai-answer-questions.json'
PROPOSED = 'config/ai-answer-questions-proposed.json'
MAX_QUESTIONS = 25
CLOSE_EVENT = 'questions_written'
FILE_URL = 'https://github.com/krishanraja/growth-makeyourmindup/blob/main/' + QUESTIONS
# Control Centre's own test for a buyer question (CONTACT in its src/lib/aiAnswers.ts): never an address,
# a link or a number, so a question it would refuse is never proposed or written.
CONTACT = re.compile(r'@|https?://|www\.|\+?\d[\d\s().-]{7,}\d', re.I)
PAYLOAD_HEAD = ('The questions our readers ask AI assistants, for AEO-Engine to track. One question a line: change, add '
                'or delete any line before you approve. Only numbered lines and lines ending in a question mark are kept.')
NUMBERED = re.compile(r'^\s*\d{1,3}\s*[.)]\s+(.*\S)\s*$')
BULLET = re.compile(r'^\s*[-*\u2022]\s+')


def configured(root):
    """The real reader questions on file and the hosts the publication is cited by."""
    try:
        data = json.loads((Path(root) / QUESTIONS).read_text())
    except (OSError, ValueError):
        return [], []
    qs = []
    for q in data.get('questions') or []:
        text = ' '.join(str(q.get('question') if isinstance(q, dict) else q).split())
        if valid(text) and text not in qs:
            qs.append(text)
    hosts = [h for h in data.get('domains') or [] if isinstance(h, str)][:5]
    return qs[:MAX_QUESTIONS], hosts


def standing(directive):
    body = (directive or {}).get('directive') or {}
    block = body.get('ai_answers')
    return block.get('standing') if isinstance(block, dict) else None


def served(directive):
    body = (directive or {}).get('directive') or {}
    return bool((body.get('features') or {}).get('ai_answers')) or isinstance(body.get('ai_answers'), dict)


def _day(ymd):
    months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    try:
        y, m, d = (int(x) for x in str(ymd)[:10].split('-'))
        return f'{d} {months[m - 1]}'
    except (ValueError, IndexError):
        return str(ymd)


def line(s):
    """The publication's AI answers in one line, the words Control Center's tile uses."""
    if not s:
        return 'AI answers: not tracked yet.'
    latest = s.get('latest')
    if latest:
        n = latest.get('asked')
        return f'AI answers: cited first on {latest.get("cited_first")} of {n} question{"" if n == 1 else "s"}, {_day(latest.get("as_of"))}.'
    request = s.get('request') or {}
    if request.get('state') == 'open':
        n = request.get('questions')
        return f'AI answers: AEO tracks {n} question{"" if n == 1 else "s"} from its next research run.'
    return 'AI answers: tracked, not asked yet.' if s.get('tracked') else 'AI answers: not tracked yet.'


def misses_and_moves(s):
    """What the weekly answer piece reads first: the questions another site is cited first on, then AEO's moves."""
    if not s:
        return []
    out = [m.get('question') for m in s.get('misses') or [] if isinstance(m, dict) and m.get('question')]
    out += [m.get('target_query') or m.get('title') for m in s.get('moves') or [] if isinstance(m, dict) and (m.get('target_query') or m.get('title'))]
    return list(dict.fromkeys(out))


def sync(client, directive, root, now=None):
    """One line on the publication's AI answers, asking AEO first when none is on file, or again when Krish's
    approved questions were written since the last ask. Never raises."""
    if not served(directive):
        return []
    s = standing(directive)
    lines = [line(s)]
    pending = _read(root).get('ask') == 'pending'
    if s and s.get('request') and not pending:
        return lines
    questions, hosts = configured(root)
    if not questions:
        return lines + ['No real reader question is on file to ask AEO-Engine about yet; jobs/answer.md adds one when it finds one.']
    try:
        out = client.answers_request({'questions': questions, 'domains': hosts})
    except Exception as error:  # noqa: BLE001 - one line, never a failed run
        return lines + [f'Could not ask AEO-Engine to track the publication\'s reader questions ({getattr(error, "code", "answers_request_failed")}); the next run asks again.']
    n = out.get('questions', len(questions))
    if pending:
        # The ask is done: recorded in the file, which the workflow commits, so the next run does not ask again.
        data = _read(root)
        data['ask'] = {'request_id': out.get('request_id'), 'asked_at': iso(now), 'questions': n}
        try:
            write_json(Path(root) / QUESTIONS, data)
        except OSError:
            return lines + [f'Asked AEO-Engine to track {n} question{"" if n == 1 else "s"} Krish approved; could not record the ask, so the next run asks again.']
        return lines + [f'Asked AEO-Engine to track the {n} question{"" if n == 1 else "s"} Krish approved, from its next research run.']
    return lines + [f'Asked AEO-Engine to track {n} reader question{"" if n == 1 else "s"} from its next research run.']


# Proposing the questions for his approval (Ruling, Krish, 2026-11-13) -----------------------------

def _clean(text):
    return ' '.join(str(text).split()).strip('"\u201c\u201d ')


def valid(text):
    """A question AEO's route takes: 8 to 300 characters, never an address, a link or a number."""
    return isinstance(text, str) and 8 <= len(text) <= 300 and not CONTACT.search(text)


def _key(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower())


def _read(root):
    try:
        data = json.loads((Path(root) / QUESTIONS).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def payload_text(questions):
    """The proposal's exact words: one line on how to change it, then one numbered question a line."""
    return PAYLOAD_HEAD + '\n\n' + '\n'.join(f'{i}. {q}' for i, q in enumerate(questions, 1))


def parse_payload(text):
    """(questions, refused): the questions in the words he approved, in order, each once.

    A numbered line is a question, and so is any line ending in a question mark (a line he added
    without a number); every other line is how-to text. A question AEO's route would refuse (too
    short, too long, an address, a link or a number) is left out and counted, never repaired."""
    out, seen, refused = [], set(), 0
    for raw in str(text or '').splitlines():
        match = NUMBERED.match(raw)
        if match:
            text_ = match.group(1)
        elif raw.strip().endswith('?'):
            text_ = BULLET.sub('', raw)
        else:
            continue
        question = _clean(text_)
        if not valid(question):
            refused += 1
            continue
        if _key(question) in seen:
            continue
        seen.add(_key(question))
        out.append(question)
    return out, refused


def questions_proposal(root):
    """The proposed set as one strategy proposal behind the wall, or None without its file.

    Raises ValueError when the file cannot be read or a question in it is one AEO would refuse:
    a set is sent whole or not at all."""
    path = Path(root) / PROPOSED
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = data.get('questions') or []
    questions = [_clean(row.get('question') if isinstance(row, dict) else row) for row in rows]
    if not questions or len(questions) > MAX_QUESTIONS or not all(valid(q) for q in questions):
        raise ValueError('the proposed questions must be 1 to ' + str(MAX_QUESTIONS) + ' questions AEO takes')
    if len({_key(q) for q in questions}) != len(questions):
        raise ValueError('the proposed questions repeat one')
    n = len(questions)
    answered = sum(1 for row in rows if isinstance(row, dict) and row.get('best_piece'))
    why = (f'Make Your Mind Up has no AI-answer questions on file, so AEO-Engine tracks nothing for the publication '
           f'and its tile says not tracked yet. These are {n} questions readers type or ask about what the three '
           f'series and Saturday\'s good news cover, each with its evidence and the piece that answers it best in the '
           f'linked page; {answered} have a published piece that answers them, fully or in part. Change any line before you approve. On '
           f'your yes the engine writes exactly your version into {QUESTIONS} and asks AEO-Engine to track them from '
           f'its next research run; on your no nothing is written and this set is never sent again.')
    return proposal(data['proposal_id'], f'Approve the {n} questions our readers ask AI assistants, for AEO-Engine to track',
                    why, 'prepared', 'strategy', CLOSE_EVENT, exact_payload=payload_text(questions),
                    evidence=data.get('evidence') or (), reference=QUESTIONS)


def proposal_or_hold(root):
    """(proposal or None, hold or None) for the runner's report."""
    try:
        return questions_proposal(root), None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return None, {'reason': 'The proposed AI-answer questions could not be read', 'detail': str(error)[:900]}


def approved_write(root, decisions, now=None):
    """(lines, event): Krish's yes on the proposed set, written into the questions file once.

    Only a yes on the exact words proposed (payload_sha256), or on his amended version whose digest
    recomputes (amended_sha256), writes, and only the questions in the words he approved. The file
    keeps any real reader question already on it after his, marks the ask pending for sync, and
    records which yes it holds, so the same yes is written once. The event closes the proposal
    (close condition questions_written), and is sent again while his yes is not yet marked done.
    decisions None means they could not be read: nothing is written. A no, or no decision yet,
    writes nothing."""
    try:
        item = questions_proposal(root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ['The proposed AI-answer questions could not be read, so none of them was written.'], None
    if item is None:
        return [], None
    if decisions is None:
        return ["Could not read Krish's decisions, so no proposed AI-answer question was written; the next run reads them again."], None
    pid = item['proposal_id']
    latest, undated = _latest(decisions)
    if pid in undated:
        return ["Krish's decision on the proposed AI-answer questions has no readable time, so nothing was written."], None
    decision = latest.get(pid)
    if decision is None:
        return [], None
    if decision.get('decision') == 'declined':
        return ['Krish said no to the proposed AI-answer questions; none was written, and the set is not sent again.'], None
    if decision.get('decision') not in ('approved', 'done'):
        return [], None
    if decision.get('payload_sha256') != item['payload_sha256']:
        return ['Krish approved another version of the proposed AI-answer questions than the one on file, so nothing was written.'], None
    amended = decision.get('amended') is True
    if amended and not amendment_ok(decision):
        return ["Krish's version of the AI-answer questions did not match its digest, so nothing was written."], None
    words = decision.get('exact_payload') if amended else item['exact_payload']
    digest = decision.get('amended_sha256') if amended else item['payload_sha256']
    approved, refused = parse_payload(words)
    if not approved:
        return ['No question could be read from the AI-answer questions Krish approved, so nothing was written.'], None
    data = _read(root)
    held = data.get('approved') or {}
    event = {'event': CLOSE_EVENT, 'proposal_id': pid, 'at': iso(now), 'evidence_url': FILE_URL}
    if held.get('proposal_id') == pid and held.get('sha256') == digest:
        # Already written. The close is sent again until Control Center has it (a replay changes nothing).
        return [], (event if decision.get('decision') == 'approved' else None)
    mine = {_key(q) for q in approved}
    kept = [q for q in data.get('questions') or []
            if _key(_clean(q.get('question') if isinstance(q, dict) else q)) not in mine]
    data['questions'] = [{'question': q, 'from': 'krish_approved'} for q in approved] + kept
    data['approved'] = {'proposal_id': pid, 'sha256': digest, 'amended': amended,
                        'decided_at': decision.get('decided_at'), 'questions': len(approved)}
    data['ask'] = 'pending'
    write_json(Path(root) / QUESTIONS, data)
    n = len(approved)
    lines = [f'Krish approved {n} AI-answer question{"" if n == 1 else "s"}' + (' in his own version' if amended else '')
             + f'; wrote them into {QUESTIONS} for AEO-Engine to track.']
    if refused:
        lines.append(f'Left out {refused} approved line{"" if refused == 1 else "s"} AEO would refuse (too short, too long, '
                     'an address, a link or a number).')
    if n + len(kept) > MAX_QUESTIONS:
        lines.append(f'The file holds {n + len(kept)} questions; AEO takes the first {MAX_QUESTIONS}.')
    return lines, event
