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

Ruling (Krish, 2026-11-13): AEO's win kits reach him through each venture's own
growth engine. Where Control Center serves the standing's detail (proposed
protocol 1.23.0, `features.ai_answers_detail`), and only then:

- the standing's `kits` are read loosely (read_kits), highest priority first
  as AEO ranks them (a higher number matters more): a missing or malformed
  field means no kit, never an error. They stay in memory and in the ignored
  .scratch/cc/ai-answers.txt that `cc start` writes for the answer job (block),
  never in a committed file; a report carries their count only;
- a kit's site fix or off-site move that would put author, Person or E-E-A-T
  work under his name is dropped and counted (R100: no public word names him);
- misses_and_moves puts the kits first (each kit's title, else its question);
- a request says `mode: replace`;
- an answer piece a session marked shipped on its question in
  config/ai-answer-questions.json (`shipped: {url, shipped_at}`, never set by
  the engine) goes with every request, and on its own (`mode: append`) once
  each time the shipped list changes, recorded in that file as `shipped_sent`.

Wherever the request on file carries a `digest` (flag or none, as Heartside's
and Mindmake's engines read it), it is compared with request_digest of the
file's own valid questions, and a different one asks again, once per list: the
ask's record keeps the digest asked for, so a request on file that still reads
otherwise never asks every day. Without a digest, the rule above stands: ask
when none is on file, or when his approved questions are pending. A directive
that serves AI answers but carries no readable standing (the protocol leaves
the block out when Control Center could not read it) asks nothing and records
nothing: a request on file is never replaced on a guess.
"""
import hashlib
import json
import math
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
# Whitespace exactly as JavaScript's trim() and \s read it (ECMAScript WhiteSpace and LineTerminator), so
# request_digest matches Control Center's: Python's str.split() also splits on U+001C to U+001F and U+0085, and
# never on U+FEFF.
JS_SPACE = re.compile('[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+')
SURROGATE = re.compile('[\ud800-\udfff]')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
KITS_MAX = 5
# The largest whole number read from a kit: past it a number is malformed (a float of it would overflow).
NUMBER_MAX = 10 ** 15
# A kit's site fix or off-site move that would put author, Person or E-E-A-T work on the publication: none is
# done under Krish's name (R100), so the consumer drops it and counts it. Whole words only, so "personal",
# "authority" and "authoritative" stay; AEO's own host and page fixes (AEO-Engine src/pipeline/62-kits.ts) match none.
AUTHOR_WORK = re.compile(
    r'(?<![a-z])(?:person|author(?:s|ed|ing|ship)?|byline|e-?e-?a-?t|e-a-t|profile ?page|bios?|biography|writers?'
    r'|credentials?|expertise|sameas|founders?|headshots?)(?![a-z])', re.I)
SETTLED = ("AEO-Engine's request on file still reads otherwise than the file's questions, which were already asked for, "
           'so they were not asked again.')
SHIPPED_AT = re.compile(r'^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2}))?$')
HOST = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$')


def configured(root):
    """The real reader questions on file and the hosts the publication is cited by."""
    try:
        data = json.loads((Path(root) / QUESTIONS).read_text())
    except (OSError, ValueError):
        return [], []
    if not isinstance(data, dict):
        return [], []
    qs = []
    for q in data.get('questions') or []:
        text = ' '.join(str(q.get('question') if isinstance(q, dict) else q).split())
        if valid(text) and text not in qs:
            qs.append(text)
    hosts = [h for h in data.get('domains') or [] if isinstance(h, str)][:5]
    return qs[:MAX_QUESTIONS], hosts


def _body(directive):
    """The served directive's body, or {} when it is not an object: a malformed directive is read as none."""
    body = directive.get('directive') if isinstance(directive, dict) else None
    return body if isinstance(body, dict) else {}


def standing(directive):
    block = _body(directive).get('ai_answers')
    return block.get('standing') if isinstance(block, dict) else None


def served(directive):
    """Whether the directive serves AI answers (features.ai_answers, or an `ai_answers` block). A `features` that is
    not an object is read as no features, never an error, as every other feature reader here reads it."""
    body = _body(directive)
    features = body.get('features')
    return (isinstance(features, dict) and bool(features.get('ai_answers'))) or isinstance(body.get('ai_answers'), dict)


def readable(directive):
    """Whether the directive carries a standing to read: an `ai_answers` block whose `standing` is null or an object.
    The protocol leaves the block out when Control Center could not read the standing (1.22.0), never a guess; the
    same test as Heartside's readable and Mindmake's aiAnswersReadable."""
    block = _body(directive).get('ai_answers')
    return isinstance(block, dict) and 'standing' in block and (block['standing'] is None or isinstance(block['standing'], dict))


def detail_served(directive):
    """Whether Control Center serves the standing's detail (proposed 1.23.0): kits, and `mode` and `shipped` on
    `POST answers`. None of these is read or sent before. (The request's digest decides whenever it is present.)"""
    features = _body(directive).get('features')
    return isinstance(features, dict) and features.get('ai_answers_detail') is True


def request_digest(questions):
    """Control Center's `request.digest` of a list of questions (proposed 1.23.0), exactly.

    Each question trimmed, each run of internal whitespace one space (JavaScript's whitespace, JS_SPACE),
    sorted by code point, serialised as compact JSON with non-ASCII left unescaped (JSON.stringify;
    json.dumps(..., separators=(',', ':'), ensure_ascii=False)), UTF-8 encoded, then the lowercase hex
    SHA-256. A lone surrogate, which JSON.stringify writes as a \\u escape, is escaped the same way, so the
    digest never fails."""
    forms = sorted(JS_SPACE.sub(' ', q).strip(' ') for q in questions or () if isinstance(q, str))
    text = json.dumps(forms, separators=(',', ':'), ensure_ascii=False)
    text = SURROGATE.sub(lambda m: '\\u{:04x}'.format(ord(m.group(0))), text)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def digest_on_file(s):
    """The request on file's `digest`, or None when there is none (before 1.23.0) or it is not a lowercase SHA-256."""
    request = s.get('request') if isinstance(s, dict) else None
    value = request.get('digest') if isinstance(request, dict) else None
    return value if isinstance(value, str) and DIGEST.match(value) else None


# AEO's win kits (proposed 1.23.0; Ruling, Krish, 2026-11-13) --------------------------------------

def _text(value, limit=300):
    """A string field with its whitespace collapsed, cut to limit, or None."""
    if not isinstance(value, str):
        return None
    text = ' '.join(value.split())
    return text[:limit] if text else None


def _texts(value, limit=300, most=20):
    return [t for t in (_text(v, limit) for v in (value if isinstance(value, list) else ())) if t][:most]


def _number(value):
    """A finite number, or None. A whole number past NUMBER_MAX is malformed, never an error: math.isfinite and a
    float format both overflow on one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if abs(value) <= NUMBER_MAX else None
    return value if isinstance(value, float) and math.isfinite(value) else None


def _names_him(text):
    """Whether text names Krish, by content-engine's no_name pattern (R100). An unreadable lint names him."""
    from .copy_lint import copy_lint
    try:
        return any(hit['id'] == 'no_name' for hit in copy_lint(text, 'article_body'))
    except ValueError:
        return True


def _site_fix(value):
    """(fix or None, dropped): a fix under Krish's name or for author or Person markup is dropped (R100)."""
    if not isinstance(value, dict) or not _text(value.get('fix'), 600):
        return None, False
    fix = {'gate': _text(value.get('gate'), 100), 'host': _text(value.get('host'), 253),
           'url': _text(value.get('url'), 2000), 'fix': _text(value.get('fix'), 600),
           'owner_repo': _text(value.get('owner_repo'), 200)}
    # The owner repository is a GitHub owner, never words on a page, so it is not read.
    words = ' '.join(v for k, v in fix.items() if v and k != 'owner_repo')
    if AUTHOR_WORK.search(words) or _names_him(words):
        return None, True
    return fix, False


def _off_site(value):
    """(move or None, dropped): a move that names Krish, or whose words ask for author, Person or E-E-A-T work, is
    dropped (R100). Its host and address are where, never what is asked, so only they skip the author-work test."""
    if not isinstance(value, dict) or not _text(value.get('host'), 253):
        return None, False
    move = {'host': _text(value.get('host'), 253), 'url': _text(value.get('url'), 2000),
            'source_type': _text(value.get('source_type'), 100), 'engines': _texts(value.get('engines'), 40, 8),
            'why': _text(value.get('why'), 600)}
    asks = ' '.join(v for v in (move['source_type'], move['why']) if v)
    if AUTHOR_WORK.search(asks) or _names_him(' '.join(v for v in (move['host'], move['url'], asks) if v)):
        return None, True
    return move, False


def _kit(value):
    """(kit or None, dropped): one kit as AEO serves it, read loosely; None without a question or a title."""
    if not isinstance(value, dict):
        return None, 0
    question, title = _text(value.get('question')), _text(value.get('title'))
    if not (question or title):
        return None, 0
    target = value.get('target') if isinstance(value.get('target'), dict) else {}
    capsule = value.get('capsule') if isinstance(value.get('capsule'), dict) else {}
    verify = value.get('verify') if isinstance(value.get('verify'), dict) else {}
    dropped, fixes, moves = 0, [], []
    for raw in value.get('site_fixes') if isinstance(value.get('site_fixes'), list) else ():
        fix, drop = _site_fix(raw)
        dropped += drop
        if fix:
            fixes.append(fix)
    for raw in value.get('off_site') if isinstance(value.get('off_site'), list) else ():
        move, drop = _off_site(raw)
        dropped += drop
        if move:
            moves.append(move)
    beat = [{'host': _text(b.get('host'), 253), 'url': _text(b.get('url'), 2000), 'engine': _text(b.get('engine'), 40),
             'position': _number(b.get('position'))}
            for b in (value.get('beat') if isinstance(value.get('beat'), list) else ())
            if isinstance(b, dict) and (_text(b.get('host'), 253) or _text(b.get('url'), 2000))]
    baseline = verify.get('baseline')
    kit = {
        'kit_id': _text(value.get('kit_id'), 200), 'v': _number(value.get('v')), 'query_id': _text(value.get('query_id'), 200),
        'question': question, 'title': title, 'gap_class': _text(value.get('gap_class'), 100),
        'priority': _number(value.get('priority')),
        'target': {'kind': _text(target.get('kind'), 40), 'url': _text(target.get('url'), 2000),
                   'host': _text(target.get('host'), 253), 'suggested_path': _text(target.get('suggested_path'), 300)},
        'capsule': {'rules': _texts(capsule.get('rules'), 400), 'must_cover': _texts(capsule.get('must_cover'), 300)},
        'h2s': _texts(value.get('h2s'), 200), 'beat': beat[:10], 'site_fixes': fixes[:10], 'off_site': moves[:10],
        'verify': {'engines': _texts(verify.get('engines'), 40, 8), 'samples': _number(verify.get('samples')),
                   'success': _text(verify.get('success'), 400), 'recheck': _text(verify.get('recheck'), 100),
                   'baseline': baseline if isinstance(baseline, str) or _number(baseline) is not None else None},
        'evidence': _texts(value.get('evidence'), 2000, 10),
    }
    return kit, dropped


def read_kits(s):
    """(kits, counts): AEO's win kits in a standing, highest priority first, as AEO ranks them (AEO-Engine
    src/pipeline/62-kits.ts sorts b.priority - a.priority: a higher number matters more), a kit with none last and
    served order breaking ties, each once, at most five, so a cut keeps the best. counts says how many were served,
    how many could not be read, and how many site fixes or off-site moves were dropped for putting work under his
    name (R100). A missing or malformed `kits` reads as none, never an error."""
    counts = {'served': 0, 'unreadable': 0, 'dropped': 0}
    raw = s.get('kits') if isinstance(s, dict) else None
    if not isinstance(raw, list):
        return [], counts
    found, seen = [], set()
    for i, value in enumerate(raw[:KITS_MAX * 4]):
        kit, dropped = _kit(value)
        if kit is None:
            counts['unreadable'] += 1
            continue
        key = kit['kit_id'] or _key(kit['question'] or kit['title'])
        if key in seen:
            continue
        seen.add(key)
        counts['dropped'] += dropped
        priority = kit['priority']
        found.append(((0, -priority, i) if priority is not None else (1, 0, i), kit))
    found.sort(key=lambda item: item[0])
    kits = [kit for _, kit in found][:KITS_MAX]
    counts['served'] = len(kits)
    return kits, counts


def kits(s):
    """AEO's win kits for the publication, highest priority first; none when the standing serves none."""
    return read_kits(s)[0]


def kit_lines(s):
    """The report's kit line, counts only: kit words never leave the run's memory and the ignored local file."""
    found, counts = read_kits(s)
    n = len(found)
    lines = [f'AEO-Engine serves {n} win kit{"" if n == 1 else "s"} for the publication; the answer job reads them first.'
             if n else 'AEO-Engine serves no win kit for the publication today.']
    if counts['dropped']:
        d = counts['dropped']
        lines.append(f'Left out {d} kit fix{"" if d == 1 else "es"} that would put author or Person work under '
                     f'Krish\'s name (R100).')
    if counts['unreadable']:
        u = counts['unreadable']
        lines.append(f'{u} kit{"" if u == 1 else "s"} could not be read and {"was" if u == 1 else "were"} left out.')
    return lines


def _day(ymd):
    months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    try:
        y, m, d = (int(x) for x in str(ymd)[:10].split('-'))
        return f'{d} {months[m - 1]}'
    except (ValueError, IndexError):
        return str(ymd)


def line(s):
    """The publication's AI answers in one line, the words Control Center's tile uses."""
    if not s or not isinstance(s, dict):
        return 'AI answers: not tracked yet.'
    latest = s.get('latest')
    if latest and isinstance(latest, dict):
        n = latest.get('asked')
        return f'AI answers: cited first on {latest.get("cited_first")} of {n} question{"" if n == 1 else "s"}, {_day(latest.get("as_of"))}.'
    request = s.get('request') if isinstance(s.get('request'), dict) else {}
    if request.get('state') == 'open':
        n = request.get('questions')
        return f'AI answers: AEO tracks {n} question{"" if n == 1 else "s"} from its next research run.'
    return 'AI answers: tracked, not asked yet.' if s.get('tracked') else 'AI answers: not tracked yet.'


def misses_and_moves(s):
    """What the weekly answer piece reads first: AEO's win kits (each kit's title, else its question), then the
    questions another site is cited first on, then AEO's moves."""
    if not isinstance(s, dict):
        return []
    misses = s.get('misses') if isinstance(s.get('misses'), list) else []
    moves = s.get('moves') if isinstance(s.get('moves'), list) else []
    out = [k['title'] or k['question'] for k in kits(s)]
    out += [m['question'] for m in misses if isinstance(m, dict) and isinstance(m.get('question'), str) and m['question']]
    out += [m.get('target_query') or m.get('title') for m in moves if isinstance(m, dict)
            and isinstance(m.get('target_query') or m.get('title'), str) and (m.get('target_query') or m.get('title'))]
    return list(dict.fromkeys(out))


def _on_domains(url, hosts):
    """Whether url is an https page on one of the publication's hosts (or a subdomain of one)."""
    match = re.match(r'^https://([^/?#:@]+)(?:[/?#]|$)', url or '')
    host = match.group(1).lower() if match else ''
    return bool(host) and any(host == h or host.endswith('.' + h) for h in hosts)


def _shipped_entry(row, hosts):
    """{question, url, shipped_at} for a question an answer-piece session marked shipped, or None.

    The mark is `shipped: {url, shipped_at}` on the question's entry in the file: the https address of the
    published answer piece, on one of the publication's hosts, and the day (or moment) it went out. The engine
    never writes one."""
    if not isinstance(row, dict) or not isinstance(row.get('shipped'), dict):
        return None
    question = ' '.join(str(row.get('question') or '').split())
    url = row['shipped'].get('url')
    shipped_at = row['shipped'].get('shipped_at')
    if not valid(question) or not isinstance(url, str) or len(url) > 2000 or not _on_domains(url, hosts):
        return None
    if not isinstance(shipped_at, str) or not SHIPPED_AT.match(shipped_at):
        return None
    return {'question': question, 'url': url, 'shipped_at': shipped_at}


def shipped(root):
    """The answer pieces marked shipped in config/ai-answer-questions.json, each question once, at most 25."""
    data = _read(root)
    hosts = [h for h in data.get('domains') or [] if isinstance(h, str)]
    out, seen = [], set()
    for row in data.get('questions') if isinstance(data.get('questions'), list) else ():
        entry = _shipped_entry(row, hosts)
        if entry and _key(entry['question']) not in seen:
            seen.add(_key(entry['question']))
            out.append(entry)
    return out[:MAX_QUESTIONS]


def shipped_digest(entries):
    """One digest per shipped list, so the same list is told to AEO once."""
    rows = sorted((e['question'], e['url'], e['shipped_at']) for e in entries)
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode('utf-8')).hexdigest()


def problems(data):
    """What is wrong with the questions file's shape, one line each; none when it is sound.

    The optional `shipped: {url, shipped_at}` on a question's entry is set only by an answer-piece session, once
    the piece answering that question is published (jobs/answer.md); never invented, never by the engine."""
    if not isinstance(data, dict):
        return ['the file must be one JSON object']
    out = []
    hosts = data.get('domains')
    if not isinstance(hosts, list) or not 1 <= len(hosts) <= 5 or not all(isinstance(h, str) and HOST.match(h) for h in hosts):
        out.append('domains must be 1 to 5 bare lowercase hosts')
        hosts = []
    rows = data.get('questions')
    if not isinstance(rows, list):
        return out + ['questions must be a list']
    seen = set()
    for i, row in enumerate(rows, 1):
        text = row.get('question') if isinstance(row, dict) else row
        if not isinstance(text, str) or not valid(' '.join(text.split())):
            out.append(f'question {i} is not one AEO takes (8 to 300 characters, never an address, a link or a number)')
            continue
        if _key(' '.join(text.split())) in seen:
            out.append(f'question {i} repeats an earlier one')
        seen.add(_key(' '.join(text.split())))
        if not isinstance(row, dict):
            continue
        if 'from' in row and not isinstance(row['from'], str):
            out.append(f'question {i}: from must be a string')
        if 'shipped' in row and _shipped_entry(row, hosts) is None:
            out.append(f'question {i}: shipped must be {{url, shipped_at}}, the https address of the published answer '
                       'piece on one of the domains and an ISO date or time')
    ask = data.get('ask')
    if ask is not None and ask != 'pending' and not isinstance(ask, dict):
        out.append('ask must be pending or the record of the ask')
    if isinstance(ask, dict) and 'digest' in ask and not (isinstance(ask['digest'], str) and DIGEST.match(ask['digest'])):
        out.append('ask.digest must be the request_digest of the questions asked')
    sent = data.get('shipped_sent')
    if sent is not None and not (isinstance(sent, dict) and isinstance(sent.get('sha256'), str) and DIGEST.match(sent['sha256'])):
        out.append('shipped_sent must record the sha256 of the shipped list last told to AEO')
    return out


def _record(root, **fields):
    """Write the ask's record into the questions file, which the workflow commits. True when written."""
    data = _read(root)
    data.update(fields)
    try:
        write_json(Path(root) / QUESTIONS, data)
    except OSError:
        return False
    return True


def _tell_shipped(client, root, entries, hosts, now):
    """Tell AEO of the shipped answer pieces once per change (`mode: append`): their questions and addresses."""
    if not entries:
        return []
    digest = shipped_digest(entries)
    sent = _read(root).get('shipped_sent')
    if isinstance(sent, dict) and sent.get('sha256') == digest:
        return []
    n = len(entries)
    pieces = f'{n} shipped answer piece{"" if n == 1 else "s"}'
    body = {'questions': [e['question'] for e in entries], 'domains': hosts, 'mode': 'append', 'shipped': entries}
    try:
        out = client.answers_request(body)
    except Exception as error:  # noqa: BLE001 - one line, never a failed run
        return [f'Could not tell AEO-Engine of {pieces} ({getattr(error, "code", "answers_request_failed")}); the next run tells it again.']
    out = out if isinstance(out, dict) else {}
    if not _record(root, shipped_sent={'sha256': digest, 'at': iso(now), 'request_id': out.get('request_id'), 'answers': n}):
        return [f'Told AEO-Engine of {pieces}; could not record it, so the next run tells it again.']
    return [f'Told AEO-Engine of {pieces}, to check each is cited, from its next research run.']


def sync(client, directive, root, now=None):
    """The publication's AI answers in a few lines, asking AEO when none is on file, again when Krish's approved
    questions were written since the last ask, and again when the request on file carries a digest that differs from
    the file's own questions. With the detail served, the kits are counted, the request says `mode: replace`, and the
    shipped answer pieces go with every request, and on their own once per change. A standing that could not be read
    asks nothing and records nothing. Never raises."""
    if not served(directive):
        return []
    if not readable(directive):
        # Served, but no standing to read (the protocol leaves the block out when Control Center could not read it):
        # never "no request on file". A request on file is never replaced on a guess, and nothing is recorded, so the
        # questions file is not rewritten, and committed, while the standing stays unread.
        return ["AI answers: the publication's standing could not be read today, so nothing was asked."]
    s = standing(directive)
    lines = [line(s)]
    detail = detail_served(directive)
    if detail:
        lines += kit_lines(s)
    ask = _read(root).get('ask')
    pending = ask == 'pending'
    filed = bool(s and s.get('request'))
    questions, hosts = configured(root)
    # The request on file's digest decides wherever it is present, flag or none, as Heartside's on_record and
    # Mindmake's askFor read it; only what the POST carries (mode, shipped) waits for the detail.
    recorded = digest_on_file(s)
    mine = request_digest(questions) if questions else None
    keep = detail or recorded is not None  # The ask's record keeps the digest asked for, so a differing one settles.
    changed = bool(filed and mine and recorded and mine != recorded)
    if changed and not pending and isinstance(ask, dict) and ask.get('digest') == mine:
        # These exact questions were asked for already and the request on file still reads otherwise (Control
        # Center kept fewer, say): asking again would change nothing, so never every day.
        lines.append(SETTLED)
        changed = False
    ship = shipped(root) if detail else []
    if filed and not pending and not changed:
        return lines + _tell_shipped(client, root, ship, hosts, now)
    if not questions:
        return lines + ['No real reader question is on file to ask AEO-Engine about yet; jobs/answer.md adds one when it finds one.']
    body = {'questions': questions, 'domains': hosts}
    if detail:
        # Sent only once Control Center serves the detail: an older route would refuse fields it does not know.
        body['mode'] = 'replace'
        if ship:
            body['shipped'] = ship
    try:
        out = client.answers_request(body)
    except Exception as error:  # noqa: BLE001 - one line, never a failed run
        return lines + [f'Could not ask AEO-Engine to track the publication\'s reader questions ({getattr(error, "code", "answers_request_failed")}); the next run asks again.']
    out = out if isinstance(out, dict) else {}
    n = out.get('questions', len(questions))
    record = {}
    if pending or keep:
        # The ask is done: recorded in the file, which the workflow commits, so the next run does not ask again.
        # Wherever a digest decides, it also keeps the digest of what was asked, so a digest on file that still
        # differs from these same questions never asks every day.
        record['ask'] = {'request_id': out.get('request_id'), 'asked_at': iso(now), 'questions': n,
                         **({'digest': mine} if keep else {})}
    if ship:
        record['shipped_sent'] = {'sha256': shipped_digest(ship), 'at': iso(now), 'request_id': out.get('request_id'),
                                  'answers': len(ship)}
    if record and not _record(root, **record):
        if pending:
            return lines + [f'Asked AEO-Engine to track {n} question{"" if n == 1 else "s"} Krish approved; could not record the ask, so the next run asks again.']
        return lines + [f'Asked AEO-Engine to track {n} reader question{"" if n == 1 else "s"}; could not record the ask, '
                        'so the next run may ask again.']
    told = f', with {len(ship)} shipped answer piece{"" if len(ship) == 1 else "s"}' if ship else ''
    if pending:
        return lines + [f'Asked AEO-Engine to track the {n} question{"" if n == 1 else "s"} Krish approved{told}, from its next research run.']
    if changed:
        return lines + [f'Asked AEO-Engine again to track {n} reader question{"" if n == 1 else "s"}{told}, replacing the request '
                        'on file, whose questions differ from the file\'s, from its next research run.']
    return lines + [f'Asked AEO-Engine to track {n} reader question{"" if n == 1 else "s"}{told} from its next research run.']


def block(directive):
    """The answer job's local reading of AEO's work for the publication, kits first: the ignored
    .scratch/cc/ai-answers.txt that `cc start` writes. It holds kit and question words, so it never goes to a
    public log, a report or a committed file."""
    head = "AEO-ENGINE'S AI-ANSWER WORK FOR THE PUBLICATION (local only: never commit, post or report these words)"
    if not served(directive):
        return [head, "Not served by today's directive."]
    if not readable(directive):
        return [head, "Control Center could not read the publication's standing today, so there is no kit, miss or move."]
    s = standing(directive)
    lines = [head, line(s)]
    found, counts = read_kits(s) if detail_served(directive) else ([], None)
    if counts is None:
        lines.append("Win kits: not served by today's directive yet (features.ai_answers_detail).")
    elif not found:
        lines.append('Win kits: none today.')
    else:
        lines.append("Win kits, highest priority first (AEO's priority: a higher number matters more):")
    for i, kit in enumerate(found, 1):
        priority = kit['priority']
        lines += ['', f'Kit {i}' + (f', priority {priority:g}' if priority is not None else '') + f': {kit["title"] or kit["question"]}']
        if kit['question']:
            lines.append(f'  Question: {kit["question"]}')
        target = kit['target']
        if target['kind'] or target['url'] or target['host']:
            where = target['url'] or ' '.join(x for x in (target['host'], target['suggested_path']) if x)
            lines.append(f'  Target: {target["kind"] or "page"}' + (f', {where}' if where else ''))
        if kit['gap_class']:
            lines.append(f'  Gap: {kit["gap_class"]}')
        lines += [f'  Capsule rule: {r}' for r in kit['capsule']['rules']]
        lines += [f'  Must cover: {c}' for c in kit['capsule']['must_cover']]
        lines += [f'  H2: {h}' for h in kit['h2s']]
        hosts = list(dict.fromkeys(b['host'] for b in kit['beat'] if b['host']))
        if hosts:
            lines.append('  Pages to beat (hosts): ' + ', '.join(hosts))
        lines += [f'  Site fix for the host checklist (Krish applies; the engine never changes a host): '
                  + ': '.join(x for x in (f['gate'], f['fix']) if x) + (f' ({f["url"]})' if f['url'] else '')
                  for f in kit['site_fixes']]
        lines += [f'  Off site: {m["host"]}' + (f' ({m["source_type"]})' if m['source_type'] else '')
                  + (f': {m["why"]}' if m['why'] else '') for m in kit['off_site']]
        verify = kit['verify']
        if verify['success'] or verify['engines']:
            lines.append('  Verify: ' + '; '.join(x for x in (verify['success'], ', '.join(verify['engines']),
                                                               verify['recheck'] and 'recheck ' + verify['recheck']) if x))
    if counts and counts['dropped']:
        lines.append(f'Left out {counts["dropped"]} kit fix(es) that would put author or Person work under Krish\'s name (R100).')
    misses = misses_and_moves({'misses': s.get('misses')}) if isinstance(s, dict) and isinstance(s.get('misses'), list) else []
    moves = misses_and_moves({'moves': s.get('moves')}) if isinstance(s, dict) and isinstance(s.get('moves'), list) else []
    lines += ['', 'Misses (another site is cited first):'] + [f'  {q}' for q in misses] if misses else []
    lines += ['', "AEO's moves:"] + [f'  {q}' for q in moves] if moves else []
    return lines


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
    # A shipped mark an answer-piece session set on the same question stays with it; the engine never sets one.
    marks = {_key(_clean(q.get('question'))): q['shipped'] for q in data.get('questions') or []
             if isinstance(q, dict) and isinstance(q.get('shipped'), dict)}
    data['questions'] = [dict({'question': q, 'from': 'krish_approved'},
                              **({'shipped': marks[_key(q)]} if _key(q) in marks else {})) for q in approved] + kept
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
