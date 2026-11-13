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

The weekly answer piece (jobs/answer.md) reads AEO's misses and moves for the
publication from the same block. Never fatal: a failure is one line.
"""
import json
from pathlib import Path

QUESTIONS = 'config/ai-answer-questions.json'
MAX_QUESTIONS = 25


def configured(root):
    """The real reader questions on file and the hosts the publication is cited by."""
    try:
        data = json.loads((Path(root) / QUESTIONS).read_text())
    except (OSError, ValueError):
        return [], []
    qs = []
    for q in data.get('questions') or []:
        text = ' '.join(str(q.get('question') if isinstance(q, dict) else q).split())
        if 8 <= len(text) <= 300 and text not in qs:
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


def sync(client, directive, root):
    """One line on the publication's AI answers, asking AEO first when none is on file. Never raises."""
    if not served(directive):
        return []
    s = standing(directive)
    lines = [line(s)]
    if s and s.get('request'):
        return lines
    questions, hosts = configured(root)
    if not questions:
        return lines + ['No real reader question is on file to ask AEO-Engine about yet; jobs/answer.md adds one when it finds one.']
    try:
        out = client.answers_request({'questions': questions, 'domains': hosts})
    except Exception as error:  # noqa: BLE001 - one line, never a failed run
        return lines + [f'Could not ask AEO-Engine to track the publication\'s reader questions ({getattr(error, "code", "answers_request_failed")}); the next run asks again.']
    n = out.get('questions', len(questions))
    return lines + [f'Asked AEO-Engine to track {n} reader question{"" if n == 1 else "s"} from its next research run.']
