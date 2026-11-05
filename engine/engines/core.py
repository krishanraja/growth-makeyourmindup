"""One shared history for the four engines: append-only JSONL records, a private overlay and read-only start.

Committed records (engines/records/<engine>.jsonl) are privacy-safe: digests, states and decisions. Exact
words, recipients, URLs and raw receipts live only in the ignored overlay (.scratch/engines/<engine>.jsonl),
whose lines merge over the committed record with the same id. The latest line for an id is current; earlier
lines are its history. Nothing here posts, sends, schedules, spends or writes to Control Center.
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
SOURCE_KINDS = ('user_ruling', 'live_readback', 'published_source', 'private_file', 'review')
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
    if kind not in mod.KINDS:
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
        errors += mod.validate_detail(record)
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
    errors, seen, kinds, links = [], {}, {}, []
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
            if isinstance(last.get(rid), str) and isinstance(value.get('updated_at'), str) \
                    and value['updated_at'] < last[rid]:
                errors.append(where + 'id ' + rid + ' updated_at goes backwards')
            last[rid] = value.get('updated_at')
            links += [(where, link) for link in value.get('links') or [] if isinstance(link, str)]
    errors += [where + 'link ' + link + ' resolves to no record' for where, link in links if link not in seen]
    if not errors:  # rules across current records, once every line is valid
        everything = all_records(root, private=False)
        for engine in ENGINES:
            mod = package.module(engine)
            rules, shared = getattr(mod, 'check_records', None), getattr(mod, 'check_shared', None)
            name = RECORDS_DIR.as_posix() + '/' + engine + '.jsonl: '
            errors += [name + e for e in (rules(everything[engine]) if rules else [])]
            errors += [name + e for e in (shared(everything) if shared else [])]
    return errors


# Start --------------------------------------------------------------------------------------------------


def _first_action(engine, records):
    queue = sorted((r for r in records.values() if r.get('next_owner') in (engine, 'krish')
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
    everything = all_records(root, private)
    recovered = package.module(engine).recover(everything[engine], everything, as_of)
    first = recovered.get('next_action') if isinstance(recovered, dict) and 'next_action' in recovered \
        else _first_action(engine, everything[engine])
    return {'engine': engine, 'as_of': as_of, 'entry_request': contract['entry_request'], 'job': contract['job'],
            'single_job': True, 'recover': recovered, 'next_action': first,
            'authority': {'permitted_actions': contract['permitted_actions'],
                          'forbidden_actions': contract['forbidden_actions']}}


def command(argv, root=ROOT, out=print):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', default=argparse.SUPPRESS,
                        help='repository root holding engines/ (default: ' + ROOT_ENV + ' or this repository)')
    parser = argparse.ArgumentParser(prog='growth.py engine', parents=[common],
                                     description='Run one of the four engines. Read-only.')
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
    else:
        parser.print_help()
        return 0
    out(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
