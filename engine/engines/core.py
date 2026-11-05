"""One shared history for the four engines: append-only JSONL records, a private overlay and read-only start.

Committed records (engines/records/<engine>.jsonl) are privacy-safe: digests, states and decisions. Exact
words, recipients, URLs and raw receipts live only in the ignored overlay (.scratch/engines/<engine>.jsonl),
whose lines merge over the committed record with the same id. The latest line for an id is current; earlier
lines are its history. Nothing here posts, sends, schedules, spends or writes to Control Center.

Every engine also accepts two shared kinds, checked here rather than in the engine modules: a "session" record
(what one session did and what it would do better next time, written by engine close) and a "handoff" record
(work one engine found that another engine owns, kept in the target engine's queue until it closes it). One
session runs one engine; anything owned by another engine becomes a handoff.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from engine import engines as package
from engine.core import calendar_date, today
from engine.engines import ENGINES

ROOT = Path(__file__).resolve().parents[2]
RECORDS_DIR = Path('engines') / 'records'
PRIVATE_DIR = Path('.scratch') / 'engines'
ROOT_ENV = 'GROWTH_ENGINES_ROOT'
CLOSED = 'closed'
SOURCE_KINDS = ('user_ruling', 'live_readback', 'published_source', 'private_file', 'review', 'session')
SHARED_KINDS = ('session', 'handoff')
SHARED_STATES = {'session': (CLOSED,), 'handoff': ('open', CLOSED)}
SESSION_KEYS = ('session_ref', 'did', 'better_next_time', 'worked', 'handoffs', 'promoted')
HANDOFF_KEYS = ('from_engine', 'to_engine', 'from_session', 'to_session_ref', 'what', 'why_not_here',
                'first_command', 'done_note', 'done_on')
LEARNING_MIN = 25
LINE_MAX = 400
FILLER = re.compile(r'^(none|nothing|nil|n a|na|nope|no changes?|no improvements?|not sure|nothing much)\b')
NO_CHANGE = re.compile(r'\b(went (quite |really |very |pretty |mostly )?(well|fine|smoothly|ok|okay)|'
                       r'(was|were|is) (all |quite |really |pretty )?(fine|good|great|smooth|ok|okay)|'
                       r'no (issues|problems)|nothing (to|i would|i d) (change|improve|add|do differently)|'
                       r'keep doing|(all|every) (the )?tasks? (were|was) (completed|done|finished))\b')
SOFTENERS = ('next time', 'in the future', 'in future', 'going forward', 'from now on', 'i would', 'i will',
             'i should', 'i d', 'we should', 'we would', 'try to', 'always', 'just', 'overall', 'generally',
             'a bit', 'a little', 'even', 'really', 'probably', 'maybe')
GENERIC = {'be more careful', 'be more thorough', 'be more efficient', 'be more organised', 'be more organized',
           'be more proactive', 'be more specific', 'be more focused', 'be faster', 'be quicker', 'be better',
           'work faster', 'work harder', 'move faster', 'do better', 'do more', 'try harder', 'pay more attention',
           'communicate better', 'plan better', 'plan ahead', 'keep going', 'keep it up', 'more of the same',
           'same as before', 'all good', 'everything went well', 'it went well', 'nothing to improve',
           'test more', 'check more', 'double check everything', 'check everything', 'read more carefully',
           'be more careful with details', 'pay attention to detail', 'pay more attention to detail'}
WHOLE_LINE_ONLY = {'do more', 'test more', 'check more', 'keep going', 'plan ahead', 'be better', 'do better'}
URL = re.compile(r'https?://|\bwww\.', re.I)
REF_KEYS = ('session_ref', 'to_session_ref')
OWNERS = ENGINES + ('krish', 'content-engine', 'none')
FIELDS = ('id', 'engine', 'kind', 'title', 'state', 'source', 'next_owner', 'next_action', 'revisit_when',
          'opportunity_id', 'links', 'updated_at', 'detail')
REQUIRED = tuple(f for f in FIELDS if f != 'opportunity_id')
CONTRACT_KEYS = ('schema_version', 'kind', 'id', 'name', 'entry_request', 'job', 'owns', 'permitted_actions',
                 'forbidden_actions', 'done', 'recover_first', 'hands_off_to')
ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
ALLOWED_EMAIL = 'hello@krishraja.com'
PRIVATE_KEYS = ('body', 'text', 'message', 'email', 'recipient_address', 'comment', 'post_url',
                'recovery_copy')
DRIVE_PATH = re.compile(r'(?<![A-Za-z])[A-Za-z]:[\\/]')
TITLE_MAX = 120


def digest(text):
    """sha256 of exact words kept private, for the committed record."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _date(value):
    try:
        calendar_date(value)
        return True
    except (ValueError, TypeError):
        return False


def is_closed(engine, state):
    mod = package.module(engine)
    return state == CLOSED or state in getattr(mod, 'CLOSED_STATES', ())


# Records ------------------------------------------------------------------------------------------------


def privacy_errors(record):
    """What makes a record unfit to commit: outside email addresses, private keys, local drive paths."""
    errors = []

    def walk(value, where, key):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in PRIVATE_KEYS:
                    errors.append(where + k + ': private key; keep it in ' + PRIVATE_DIR.as_posix())
                walk(v, where + str(k) + '.', k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, where + str(i) + '.', key)
        elif isinstance(value, str):
            for found in EMAIL.findall(value):
                if found.lower() != ALLOWED_EMAIL:
                    errors.append(where.rstrip('.') + ': email address; keep it in ' + PRIVATE_DIR.as_posix())
            is_ref = isinstance(key, str) and (key == 'ref' or key.endswith('_ref'))
            if DRIVE_PATH.search(value) and not is_ref:
                errors.append(where.rstrip('.') + ': local path outside an evidence ref')

    walk(record, '', None)
    return errors


def validate(record, private=False):
    """Errors in one record: the common schema, the engine's detail rules, and privacy unless private."""
    if not isinstance(record, dict):
        return ['record must be an object']
    errors = ['missing ' + f for f in REQUIRED if f not in record]
    errors += ['unknown field ' + f for f in record if f not in FIELDS]
    rid, engine = record.get('id'), record.get('engine')
    if not isinstance(rid, str) or not ID.match(rid):
        errors.append('id must match ' + ID.pattern)
    if engine not in ENGINES:
        return errors + ['engine must be one of ' + ', '.join(ENGINES)]
    mod = package.module(engine)
    kind, state = record.get('kind'), record.get('state')
    if kind in SHARED_KINDS:
        if state not in SHARED_STATES[kind]:
            errors.append('state ' + repr(state) + ' is not a state of ' + kind)
    elif kind not in mod.KINDS:
        errors.append('kind ' + repr(kind) + ' is not a ' + engine + ' kind')
    elif state not in tuple(mod.STATES.get(kind, ())) + (CLOSED,) + tuple(mod.CLOSED_STATES):
        errors.append('state ' + repr(state) + ' is not a state of ' + kind)
    title = record.get('title')
    if not isinstance(title, str) or not title.strip() or len(title) > TITLE_MAX:
        errors.append('title must be a short non-empty string')
    source = record.get('source')
    if not isinstance(source, dict) or source.get('kind') not in SOURCE_KINDS \
            or not isinstance(source.get('ref'), str) or not source['ref'].strip() \
            or not _date(source.get('observed_at')) or set(source) - {'kind', 'ref', 'observed_at'}:
        errors.append('source must be {kind: ' + '|'.join(SOURCE_KINDS) + ', ref, observed_at: YYYY-MM-DD}')
    if record.get('next_owner') not in OWNERS:
        errors.append('next_owner must be one of ' + ', '.join(OWNERS))
    if record.get('next_action') is not None and not isinstance(record.get('next_action'), str):
        errors.append('next_action must be a string or null')
    revisit = record.get('revisit_when')
    if not is_closed(engine, state) and (not isinstance(revisit, str) or not revisit.strip()):
        errors.append('revisit_when is required unless the record is closed')
    if revisit is not None and not isinstance(revisit, str):
        errors.append('revisit_when must be a string')
    if 'opportunity_id' in record and (not isinstance(record['opportunity_id'], str)
                                       or not ID.match(record['opportunity_id'])):
        errors.append('opportunity_id must match ' + ID.pattern)
    links = record.get('links')
    if not isinstance(links, list) or not all(isinstance(x, str) and ID.match(x) for x in links):
        errors.append('links must be a list of record ids')
    if not _date(record.get('updated_at')):
        errors.append('updated_at must be YYYY-MM-DD')
    if not isinstance(record.get('detail'), dict):
        errors.append('detail must be an object')
    elif not errors:
        errors += shared_detail_errors(record) if kind in SHARED_KINDS else mod.validate_detail(record)
    if not private:
        errors += privacy_errors(record)
    return errors


def _path(engine, root, private):
    if engine not in ENGINES:
        raise ValueError('unknown engine: ' + str(engine))
    return Path(root) / (PRIVATE_DIR if private else RECORDS_DIR) / (engine + '.jsonl')


def _lines(path):
    """[(line number, parsed value)] of a JSONL file; a missing file has none."""
    if not path.is_file():
        return []
    out = []
    with open(path, encoding='utf-8-sig') as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    out.append((number, json.loads(line)))
                except ValueError:
                    out.append((number, None))
    return out


def _merge(base, over):
    merged = {**base, **over}
    if isinstance(base.get('detail'), dict) and isinstance(over.get('detail'), dict):
        merged['detail'] = {**base['detail'], **over['detail']}
    return merged


def load(engine, root=ROOT, private=True):
    """{id: latest record} for one engine, with the private overlay merged over it unless private=False."""
    records = {}
    for _, value in _lines(_path(engine, root, False)):
        if isinstance(value, dict) and isinstance(value.get('id'), str):
            records[value['id']] = value
    if private:
        for _, value in _lines(_path(engine, root, True)):
            if isinstance(value, dict) and isinstance(value.get('id'), str):
                records[value['id']] = _merge(records.get(value['id'], {}), value)
    return records


def history(engine, record_id, root=ROOT):
    """Every committed line for one id, oldest first. The last is current."""
    return [v for _, v in _lines(_path(engine, root, False)) if isinstance(v, dict) and v.get('id') == record_id]


def all_records(root=ROOT, private=True):
    return {engine: load(engine, root, private) for engine in ENGINES}


def append(engine, record, root=ROOT, private=False):
    """Validate, then append one line. A private line may be partial: it is validated merged over the
    committed record with the same id, without the privacy rules, and goes to the ignored overlay."""
    if not isinstance(record, dict) or record.get('engine', engine) != engine:
        raise ValueError('record engine must be ' + engine)
    whole = _merge(load(engine, root, private=True).get(record.get('id'), {}), record) if private else record
    errors = validate(whole, private=private)
    if errors:
        raise ValueError('; '.join(errors))
    path = _path(engine, root, private)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')
    return whole


def load_contract(engine, root=ROOT):
    path = Path(root) / 'engines' / (engine + '.json')
    with open(path, encoding='utf-8-sig') as handle:
        contract = json.load(handle)
    missing = [k for k in CONTRACT_KEYS if k not in contract]
    if missing or contract.get('id') != engine or contract.get('kind') != 'engine':
        raise ValueError(path.as_posix() + ': contract needs ' + ', '.join(CONTRACT_KEYS) + ' and id ' + engine)
    return contract


def check(root=ROOT):
    """Errors across every committed record file and contract. Missing record files are empty queues."""
    errors, seen, kinds, links, opened = [], {}, {}, [], set()
    for engine in ENGINES:
        try:
            load_contract(engine, root)
        except (OSError, ValueError) as error:
            errors.append(engine + ' contract: ' + str(error))
        name = RECORDS_DIR.as_posix() + '/' + engine + '.jsonl'
        last = {}
        for number, value in _lines(_path(engine, root, False)):
            where = name + ':' + str(number) + ': '
            if not isinstance(value, dict):
                errors.append(where + 'not a JSON object')
                continue
            if value.get('engine') != engine:
                errors.append(where + 'engine field must be ' + engine)
            errors += [where + e for e in validate(value)]
            rid = value.get('id')
            if not isinstance(rid, str):
                continue
            if seen.setdefault(rid, engine) != engine:
                errors.append(where + 'id ' + rid + ' is already in ' + seen[rid])
            if kinds.setdefault((engine, rid), value.get('kind')) != value.get('kind'):
                errors.append(where + 'id ' + rid + ' changed kind')
            # A session is written once, and a handoff is opened once. A second opening line
            # means two checkouts took the same id the same day: say so instead of letting the
            # later line silently replace the earlier record. Renumber the later one.
            opening = value.get('kind') == 'session' or (value.get('kind') == 'handoff'
                                                         and value.get('state') == 'open')
            if opening and (engine, rid) in opened:
                errors.append(where + 'id ' + rid + ' was opened twice, likely by two checkouts on the '
                              'same day; renumber the later record')
            if opening:
                opened.add((engine, rid))
            if isinstance(last.get(rid), str) and isinstance(value.get('updated_at'), str) \
                    and value['updated_at'] < last[rid]:
                errors.append(where + 'id ' + rid + ' updated_at goes backwards')
            last[rid] = value.get('updated_at')
            links += [(where, link) for link in value.get('links') or [] if isinstance(link, str)]
    errors += [where + 'link ' + link + ' resolves to no record' for where, link in links if link not in seen]
    if not errors:  # rules across current records, once every line is valid
        whole = all_records(root, private=False)
        everything = {e: own(r) for e, r in whole.items()}
        for engine in ENGINES:
            mod = package.module(engine)
            rules, shared = getattr(mod, 'check_records', None), getattr(mod, 'check_shared', None)
            name = RECORDS_DIR.as_posix() + '/' + engine + '.jsonl: '
            errors += [name + e for e in (rules(everything[engine]) if rules else [])]
            errors += [name + e for e in (shared(everything) if shared else [])]
            errors += [name + e for e in session_errors(engine, whole)]
    return errors


# Start --------------------------------------------------------------------------------------------------


def _first_action(engine, records):
    queue = sorted((r for r in own(records).values() if r.get('next_owner') in (engine, 'krish')
                    and not is_closed(engine, r.get('state'))),
                   key=lambda r: (str(r.get('updated_at')), r.get('id')))
    if not queue:
        return None
    r = queue[0]
    return {k: r.get(k) for k in ('id', 'title', 'state', 'next_owner', 'next_action', 'revisit_when')}


def start(engine, root=ROOT, now=None, private=True):
    """What a fresh chat needs to run one engine. Reads only; writes nothing."""
    as_of = calendar_date(now).isoformat() if now else today()
    contract = load_contract(engine, root)
    whole = all_records(root, private)
    everything = {e: own(r) for e, r in whole.items()}
    recovered = package.module(engine).recover(everything[engine], everything, as_of)
    first = recovered.get('next_action') if isinstance(recovered, dict) and 'next_action' in recovered \
        else _first_action(engine, everything[engine])
    inbound = inbound_handoffs(engine, whole[engine])
    if inbound:
        first = {k: inbound[0].get(k) for k in ('id', 'title', 'state', 'next_owner', 'next_action', 'revisit_when')}
    return {'engine': engine, 'as_of': as_of, 'entry_request': contract['entry_request'], 'job': contract['job'],
            'single_job': True,
            'this_session': {'engine': engine, 'rule': SESSION_RULE.format(name=engine)},
            'inbound_handoffs': inbound, 'last_learnings': last_learnings(engine, whole[engine]),
            'recover': recovered, 'next_action': first,
            'authority': {'permitted_actions': contract['permitted_actions'],
                          'forbidden_actions': contract['forbidden_actions']}}


# Sessions and handoffs ---------------------------------------------------------------------------------

SESSION_RULE = ('One engine per session. Work owned by another engine becomes a handoff (python growth.py engine '
                'handoff); never do it here. Close with python growth.py engine close {name} --learnings FILE '
                'before your final message.')


def own(records):
    """An engine's records without the shared session and handoff kinds: what its module reasons about."""
    return {k: v for k, v in records.items() if v.get('kind') not in SHARED_KINDS}


def normal(line):
    """A learning line compared case, whitespace and punctuation insensitively."""
    return ' '.join(re.sub(r'[^\w\s]+', ' ', str(line).lower()).split())


def _one_line(value, limit=LINE_MAX):
    return isinstance(value, str) and bool(value.strip()) and '\n' not in value and len(value) <= limit


def generic(line):
    """True when a learning line says nothing specific: none, nothing, or filler such as "be more careful"."""
    words = re.sub(r'[^a-z0-9]+', ' ', str(line).lower()).strip()
    if FILLER.match(words):
        return True
    padded = ' ' + words + ' '
    for soft in SOFTENERS:
        padded = padded.replace(' ' + soft + ' ', ' ')
    rest = ' '.join(padded.split())
    if rest in GENERIC or len(rest.split()) < 4 or NO_CHANGE.search(words):
        return True
    return any((' ' + g + ' ') in (' ' + rest + ' ') for g in GENERIC - WHOLE_LINE_ONLY)


def learning_errors(lines):
    """What makes better_next_time unfit: missing, empty, too short, or generic filler."""
    if not isinstance(lines, list) or not lines:
        return ['better_next_time needs at least one specific line: what this session would do better next time']
    errors = []
    for i, line in enumerate(lines):
        where = 'better_next_time.' + str(i) + ': '
        if not _one_line(line):
            errors.append(where + 'must be one non-empty line')
        elif len(line.strip()) < LEARNING_MIN:
            errors.append(where + 'too short; say specifically what to do differently (at least '
                          + str(LEARNING_MIN) + ' characters)')
        elif generic(line):
            errors.append(where + 'too generic; name the specific step, check or tool to change')
    seen = [normal(x) for x in lines if isinstance(x, str)]
    if len(set(seen)) != len(seen):
        errors.append('better_next_time repeats a line')
    return errors


def _safe_path(value):
    return isinstance(value, str) and bool(value.strip()) and not value.startswith(('/', '\\')) \
        and not DRIVE_PATH.search(value) and '..' not in Path(value).parts


def _lines_errors(d, key, required):
    value = d.get(key, [])
    if not isinstance(value, list) or (required and not value) or not all(_one_line(x) for x in value):
        return [('detail.' + key + ' must be a list of one-line strings')
                + (', at least one' if required else '')]
    return []


def shared_detail_errors(record):
    """The detail rules of the shared session and handoff kinds."""
    d, engine, kind = record['detail'], record['engine'], record['kind']
    allowed = SESSION_KEYS if kind == 'session' else HANDOFF_KEYS
    errors = ['detail.' + k + ': unknown key' for k in d if k not in allowed]
    errors += url_errors(record)
    if kind == 'session':
        ref = d.get('session_ref')
        if ref is not None and not _one_line(ref, 500):
            errors.append('detail.session_ref must be a session link or null')
        errors += _lines_errors(d, 'did', True) + _lines_errors(d, 'worked', False)
        errors += ['detail.' + e for e in learning_errors(d.get('better_next_time'))]
        handoffs = d.get('handoffs', [])
        if not isinstance(handoffs, list) or not all(isinstance(x, str) and ID.match(x) for x in handoffs):
            errors.append('detail.handoffs must be a list of handoff record ids')
        elif not set(handoffs) <= set(record.get('links') or []):
            errors.append('detail.handoffs must also be in links')
        promoted = d.get('promoted', [])
        if not isinstance(promoted, list) or not all(
                isinstance(p, dict) and set(p) == {'learning', 'to'} and _one_line(p['learning'])
                and _safe_path(p['to']) for p in promoted):
            errors.append('detail.promoted must be a list of {learning, to: a repository path}')
        if record.get('next_owner') != 'none':
            errors.append('a session record has next_owner none')
        return errors
    frm, to = d.get('from_engine'), d.get('to_engine')
    if frm not in ENGINES or to not in ENGINES:
        errors.append('detail.from_engine and detail.to_engine must be engines')
    elif frm == to:
        errors.append('a handoff goes to another engine; from_engine and to_engine are both ' + frm)
    if to != engine:
        errors.append('a handoff lives in the target engine\'s queue: to_engine must be ' + engine)
    if d.get('from_session') is not None and not (isinstance(d['from_session'], str) and ID.match(d['from_session'])):
        errors.append('detail.from_session must be a session record id or null')
    if d.get('to_session_ref') is not None and not _one_line(d['to_session_ref'], 500):
        errors.append('detail.to_session_ref must be a session link or null')
    for key in ('what', 'why_not_here'):
        if not _one_line(d.get(key)):
            errors.append('detail.' + key + ' must be one non-empty line')
    if d.get('first_command') != 'python growth.py engine start ' + str(engine):
        errors.append('detail.first_command must be python growth.py engine start ' + str(engine))
    if record.get('state') == 'open' and record.get('next_owner') != engine:
        errors.append('an open handoff has next_owner ' + str(engine))
    if record.get('state') == CLOSED and not (_one_line(d.get('done_note')) and _date(d.get('done_on'))):
        errors.append('a closed handoff carries detail.done_note and detail.done_on')
    return errors


def url_errors(record):
    """A committed session or handoff carries no URL outside its session link: post and page URLs stay in
    the private overlay, and the record links the record id instead."""
    found = []

    def walk(value, where):
        if isinstance(value, dict):
            for k, v in value.items():
                if k not in REF_KEYS:
                    walk(v, where + '.' + str(k))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, where + '.' + str(i))
        elif isinstance(value, str) and URL.search(value):
            found.append(where)

    walk(record.get('detail'), 'detail')
    for key in ('title', 'next_action'):
        if isinstance(record.get(key), str) and URL.search(record[key]):
            found.append(key)
    return [w + ': no URL in a committed ' + str(record.get('kind')) + ' record; keep it in '
            + PRIVATE_DIR.as_posix() + ' and link the record id instead' for w in found]


def _handoffs(whole):
    return {rid: r for recs in whole.values() for rid, r in recs.items() if r.get('kind') == 'handoff'}


def session_errors(engine, whole):
    """Across engines: every handoff a session lists exists and came from that session's engine."""
    handoffs, errors = _handoffs(whole), []
    for r in sorted(whole[engine].values(), key=lambda r: r['id']):
        if r.get('kind') != 'session':
            continue
        for hid in r['detail'].get('handoffs', []):
            if hid not in handoffs:
                errors.append(r['id'] + ': handoff ' + hid + ' is not a handoff record')
            elif handoffs[hid]['detail'].get('from_engine') != engine:
                errors.append(r['id'] + ': handoff ' + hid + ' is not from ' + engine)
    return errors


def _created(record):
    return (record.get('source') or {}).get('observed_at') or record.get('updated_at') or ''


def inbound_handoffs(engine, records):
    """Open handoffs waiting in this engine's queue, oldest first."""
    return [r for r in sorted(records.values(), key=lambda r: (_created(r), r['id']))
            if r.get('kind') == 'handoff' and r.get('state') == 'open']


def _sessions(records):
    return sorted((r for r in records.values() if r.get('kind') == 'session'),
                  key=lambda r: (str(r.get('updated_at')), r['id']))


def last_learnings(engine, records, count=3):
    """better_next_time from this engine's last three session records, newest last."""
    return [{'id': r['id'], 'date': r['updated_at'], 'better_next_time': r['detail'].get('better_next_time', [])}
            for r in _sessions(records)[-count:]]


def _next_id(prefix, records):
    taken = {rid for recs in records.values() for rid in recs}
    n = 1
    while prefix + str(n) in taken:
        n += 1
    return prefix + str(n)


def session_id(engine, as_of, root=ROOT):
    """The id the current session of this engine will close under."""
    return _next_id('session-' + engine + '-' + as_of + '-', all_records(root, private=False))


def _names(engine, root):
    contract = load_contract(engine, root)
    return contract['name'], contract['entry_request']


def handoff_message(record, root=ROOT):
    """The paste-ready instruction and message for one handoff."""
    d = record['detail']
    from_name, _ = _names(d['from_engine'], root)
    to_name, entry = _names(d['to_engine'], root)
    message = (entry + '. Pick up handoff ' + record['id'] + ' from ' + from_name + ': ' + d['what'].rstrip('.')
               + '. First: git pull, then ' + d['first_command'] + '.')
    if d.get('to_session_ref'):
        instruction = 'Send this to your ' + to_name + ' session at ' + d['to_session_ref'] + ':'
    else:
        instruction = ('Send this to your existing ' + to_name + ' session (paste that session\'s link here and '
                       'this session will pass it on), or start a new ' + to_name + ' session with it:')
    return {'id': record['id'], 'to_engine': d['to_engine'], 'instruction': instruction, 'message': message}


def handoff(from_engine, to_engine, what, why, links=(), opportunity_id=None, to_session=None, root=ROOT,
            now=None):
    """Append an open handoff to the target engine's queue. One session runs one engine: work it finds that
    another engine owns goes there, with the records it concerns."""
    as_of = calendar_date(now).isoformat() if now else today()
    for name in (from_engine, to_engine):
        if name not in ENGINES:
            raise ValueError('unknown engine: ' + str(name))
    if from_engine == to_engine:
        raise ValueError('a handoff goes to another engine; this is already ' + from_engine + '\'s work')
    whole = all_records(root, private=False)
    index = {rid: r for recs in whole.values() for rid, r in recs.items()}
    links = list(dict.fromkeys(links or ()))
    missing = [x for x in links if x not in index]
    if missing:
        raise ValueError('no record ' + ', '.join(missing) + ' to link')
    if opportunity_id is None:
        opportunity_id = next((index[x]['opportunity_id'] for x in links if index[x].get('opportunity_id')), None)
    from_name, _ = _names(from_engine, root)
    to_name, _ = _names(to_engine, root)
    sid = session_id(from_engine, as_of, root)
    title = 'Handoff from ' + from_name + ': ' + ' '.join(str(what).split())
    record = {'id': _next_id('handoff-' + from_engine + '-to-' + to_engine + '-' + as_of + '-', whole),
              'engine': to_engine, 'kind': 'handoff',
              'title': title if len(title) <= TITLE_MAX else title[:TITLE_MAX - 3].rstrip() + '...',
              'state': 'open', 'source': {'kind': 'session', 'ref': sid, 'observed_at': as_of},
              'next_owner': to_engine, 'next_action': 'Pick up the handoff from ' + from_name + ': ' + str(what),
              'revisit_when': 'the next ' + to_name + ' session', 'links': links, 'updated_at': as_of,
              'detail': {'from_engine': from_engine, 'to_engine': to_engine, 'from_session': sid,
                         'to_session_ref': to_session or None, 'what': what, 'why_not_here': why,
                         'first_command': 'python growth.py engine start ' + to_engine}}
    if opportunity_id:
        record['opportunity_id'] = opportunity_id
    append(to_engine, record, root)
    return record


def _promotion_errors(engine, learnings, earlier, root):
    errors, promoted = [], {}
    for p in learnings.get('promoted') or []:
        if isinstance(p, dict) and isinstance(p.get('to'), str):
            path = Path(root) / p['to'] if _safe_path(p['to']) else None
            if path is None or not path.is_file():
                errors.append('promoted to ' + p['to'] + ': no such file in the repository')
            elif normal(p.get('learning', '')) not in normal(path.read_text(encoding='utf-8-sig')):
                errors.append('promoted to ' + p['to'] + ': the learning is not written there yet; add its words '
                              'to that file before close')
            else:
                promoted[normal(p.get('learning', ''))] = p['to']
    homes = ('engines/' + engine + '.json', 'jobs/' + engine + '.md')
    for line in learnings.get('better_next_time') or []:
        if not isinstance(line, str) or normal(line) not in earlier:
            continue
        to = promoted.get(normal(line))
        if not to or not (to in homes or to.startswith('social/lessons/')):
            errors.append('better_next_time repeats a learning from ' + earlier[normal(line)] + ': "' + line.strip()
                          + '". Promote it into ' + ' or '.join(homes) + ' or a social/lessons record, then list'
                          ' it under promoted with that path')
    return errors


def close(engine, learnings, root=ROOT, now=None):
    """Write this session's record: what it did, what it would do better next time, and every handoff it made.
    Refuses weak or repeated learnings and unreported handoffs."""
    as_of = calendar_date(now).isoformat() if now else today()
    if engine not in ENGINES:
        raise ValueError('unknown engine: ' + str(engine))
    if not isinstance(learnings, dict):
        raise ValueError('the learnings file must be a JSON object')
    unknown = [k for k in learnings if k not in SESSION_KEYS]
    errors = ['unknown key ' + k + ' in the learnings file' for k in unknown]
    errors += learning_errors(learnings.get('better_next_time'))
    whole = all_records(root, private=False)
    handoffs = _handoffs(whole)
    listed = learnings.get('handoffs') or []
    if not isinstance(listed, list):
        errors.append('handoffs must be a list of handoff record ids')
        listed = []
    for hid in listed:
        if hid not in handoffs:
            errors.append('handoff ' + str(hid) + ' does not exist')
        elif handoffs[hid]['detail'].get('from_engine') != engine:
            errors.append('handoff ' + hid + ' is not from ' + engine)
    sessions = _sessions(whole[engine])
    earlier = {}
    for r in sessions:
        for line in r['detail'].get('better_next_time', []):
            earlier.setdefault(normal(line), r['id'])
    errors += _promotion_errors(engine, learnings, earlier, root)
    reported = {h for r in sessions for h in r['detail'].get('handoffs', [])}
    unlisted = sorted(hid for hid, h in handoffs.items() if h['detail'].get('from_engine') == engine
                      and _created(h) == as_of and hid not in reported and hid not in listed)
    if unlisted:
        errors.append('handoffs made today from ' + engine + ' are not listed: ' + ', '.join(unlisted)
                      + '; list every handoff so nothing handed off goes unreported')
    if errors:
        raise ValueError('; '.join(errors))
    name, _ = _names(engine, root)
    sid = session_id(engine, as_of, root)
    detail = {'session_ref': learnings.get('session_ref') or None, 'did': learnings.get('did') or [],
              'better_next_time': learnings['better_next_time'], 'worked': learnings.get('worked') or [],
              'handoffs': list(listed), 'promoted': learnings.get('promoted') or []}
    record = {'id': sid, 'engine': engine, 'kind': 'session',
              'title': name + ' session ' + as_of + ': what to do better next time', 'state': CLOSED,
              'source': {'kind': 'session', 'ref': sid, 'observed_at': as_of}, 'next_owner': 'none',
              'next_action': None, 'revisit_when': None, 'links': list(listed), 'updated_at': as_of,
              'detail': detail}
    append(engine, record, root)
    current = load(engine, root, private=False)
    still_open = [{k: r.get(k) for k in ('id', 'kind', 'title', 'state', 'next_owner', 'next_action')}
                  for r in sorted(current.values(), key=lambda r: (str(r.get('updated_at')), r['id']))
                  if r.get('kind') != 'session' and not is_closed(engine, r.get('state'))]
    return {'session': record, 'better_next_time': record['detail']['better_next_time'],
            'handoffs': [handoff_message(handoffs[h], root) for h in listed], 'still_open': still_open}


def done(engine, record_id, note, root=ROOT, now=None):
    """Close one of this engine's own records, an inbound handoff included, with a note. Keeps history."""
    as_of = calendar_date(now).isoformat() if now else today()
    if not _one_line(note):
        raise ValueError('--note must be one non-empty line')
    records = load(engine, root, private=False)
    if record_id not in records:
        owner = next((e for e, recs in all_records(root, private=False).items() if record_id in recs), None)
        raise ValueError(record_id + (' is ' + owner + '\'s record; only ' + owner + ' closes it' if owner
                                      else ' is not a record') + '; ' + engine + ' closes only its own records')
    current = records[record_id]
    if is_closed(engine, current.get('state')):
        raise ValueError(record_id + ' is already ' + str(current.get('state')))
    kind, mod = current.get('kind'), package.module(engine)
    if kind in getattr(mod, 'NO_PLAIN_CLOSE', ()):
        raise ValueError('a ' + engine + ' ' + kind + ' closes only through its own rule, not engine done')
    if kind == 'session':
        raise ValueError('a session record is already closed')
    if current.get('next_owner') == 'krish':
        raise ValueError(record_id + ' waits on Krish; only his decision closes it, not engine done')
    line = dict(current, state=CLOSED, revisit_when=None, updated_at=max(as_of, str(current.get('updated_at'))),
                detail=dict(current['detail'], done_note=note, done_on=as_of))
    if kind == 'handoff':
        line['next_action'] = None
    admit = getattr(mod, 'admit_errors', None)
    errors = admit(own(records), line) if admit and kind not in SHARED_KINDS else []
    if errors:
        raise ValueError('; '.join(errors))
    return append(engine, line, root)


def report_text(report, root=ROOT):
    """The closing report for Krish, ready to end the session's final message."""
    out = ['What I would do better next time:']
    out += ['- ' + line for line in report['better_next_time']]
    if report['handoffs']:
        out += ['', 'Handoffs:']
        for h in report['handoffs']:
            out += ['', h['instruction'], '', '    ' + h['message']]
    else:
        out += ['', 'Handoffs: none.']
    out += ['', 'Still open in ' + report['session']['engine'] + ':']
    out += ['- ' + r['id'] + ' (' + str(r['state']) + '): ' + str(r['next_action'] or r['title'])
            for r in report['still_open']] or ['- nothing']
    return '\n'.join(out)


def handoff_text(record, root=ROOT):
    m = handoff_message(record, root)
    return m['instruction'] + '\n\n    ' + m['message']


def _read_learnings(path):
    with open(path, encoding='utf-8-sig') as handle:
        try:
            return json.load(handle)
        except ValueError as error:
            raise ValueError(str(path) + ': not JSON: ' + str(error)) from None


def command(argv, root=ROOT, out=print):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', default=argparse.SUPPRESS,
                        help='repository root holding engines/ (default: ' + ROOT_ENV + ' or this repository)')
    parser = argparse.ArgumentParser(prog='growth.py engine', parents=[common],
                                     description='Run one of the four engines. start, check, show and history '
                                                 'read only; handoff, close and done append one record.')
    sub = parser.add_subparsers(dest='cmd')
    s = sub.add_parser('start', parents=[common], help='what a fresh chat recovers first for one engine')
    s.add_argument('name', choices=ENGINES); s.add_argument('--now', help='YYYY-MM-DD')
    s.add_argument('--no-private', action='store_true', help='ignore the private overlay in .scratch/engines/')
    sub.add_parser('check', parents=[common], help='validate every committed engine record and contract')
    w = sub.add_parser('show', parents=[common], help='current records of one engine, or one record')
    w.add_argument('name', choices=ENGINES); w.add_argument('id', nargs='?')
    w.add_argument('--no-private', action='store_true')
    h = sub.add_parser('history', parents=[common], help='every committed line of one record')
    h.add_argument('name', choices=ENGINES); h.add_argument('id')
    o = sub.add_parser('handoff', parents=[common], help='hand work another engine owns to that engine\'s queue')
    o.add_argument('from_engine', choices=ENGINES); o.add_argument('to_engine', choices=ENGINES)
    o.add_argument('--what', required=True, help='the work, in one line')
    o.add_argument('--why', required=True, help='why this session does not do it, in one line')
    o.add_argument('--link', action='append', default=[], help='a record id the handoff concerns (repeatable)')
    o.add_argument('--opportunity-id'); o.add_argument('--to-session', help='the target session link, if known')
    o.add_argument('--now', help='YYYY-MM-DD')
    c = sub.add_parser('close', parents=[common], help='record this session\'s learnings and handoffs')
    c.add_argument('name', choices=ENGINES); c.add_argument('--learnings', required=True, help='a JSON file')
    c.add_argument('--now', help='YYYY-MM-DD')
    d = sub.add_parser('done', parents=[common], help='close one of this engine\'s records, a handoff included')
    d.add_argument('name', choices=ENGINES); d.add_argument('id'); d.add_argument('--note', required=True)
    d.add_argument('--now', help='YYYY-MM-DD')
    args = parser.parse_args(argv)
    root = Path(getattr(args, 'root', None) or os.environ.get(ROOT_ENV, '').strip() or root)
    if args.cmd == 'start':
        result = start(args.name, root, args.now, not args.no_private)
    elif args.cmd == 'check':
        errors = check(root)
        out(json.dumps({'ok': not errors, 'errors': errors}, indent=2, ensure_ascii=False))
        return int(bool(errors))
    elif args.cmd == 'show':
        result = load(args.name, root, not args.no_private)
        if args.id:
            if args.id not in result:
                raise ValueError('no ' + args.name + ' record ' + args.id)
            result = result[args.id]
    elif args.cmd == 'history':
        result = history(args.name, args.id, root)
        if not result:
            raise ValueError('no ' + args.name + ' record ' + args.id)
    elif args.cmd == 'handoff':
        record = handoff(args.from_engine, args.to_engine, args.what, args.why, args.link, args.opportunity_id,
                         args.to_session, root, args.now)
        out(json.dumps(record, indent=2, ensure_ascii=False))
        out('\n' + handoff_text(record, root))
        return 0
    elif args.cmd == 'close':
        report = close(args.name, _read_learnings(args.learnings), root, args.now)
        out(json.dumps(report, indent=2, ensure_ascii=False))
        out('\n' + report_text(report, root))
        return 0
    elif args.cmd == 'done':
        result = done(args.name, args.id, args.note, root, args.now)
    else:
        parser.print_help()
        return 0
    out(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
