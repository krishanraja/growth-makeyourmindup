"""Quote-anchored rules, the failure register and the crew cards. Offline only.

Each loader raises ValueError on a malformed file; each check returns a list
of problems, empty when the invariant holds. Nothing here reads the network,
writes a file or acts on any platform.
"""
import datetime
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RULE_SOURCES = ('AGENTS.md', 'BROWSER.md', 'CHANGES.md', 'docs/PUBLISHING-AUTHORITY.md',
                'docs/ASSET-STORAGE.md', 'docs/ACCOUNT-VOICE.md')
RULE_FIELDS = ('id', 'statement', 'source_file', 'quote', 'enforced_by', 'tests')
FAILURE_FIELDS = ('id', 'title', 'source', 'guard', 'tests', 'status')
STATUSES = ('tested', 'doc-only', 'process', 'open', 'superseded', 'pending-build')
# F01 to F54 and G1 to G9 are the plan appendix; F55 onwards were learned after it.
LAST_F = 132
FAILURE_IDS = (tuple('F{:02d}'.format(n) for n in range(1, LAST_F + 1))
               + tuple('G{}'.format(n) for n in range(1, 10)))
CREW_FIELDS = ('id', 'name', 'owns', 'channels', 'formats', 'lint', 'check', 'card', 'lens', 'w45')
W45 = {'substack', 'threads', 'attribution-ladder', 'what-works', 'release-gate'}
CARD_BYTES, LENS_BYTES = 3072, 1024
MIN_QUOTE = 40
SOURCE_CLASSES = ('organic', 'unattributed', 'paid')
OWNERS = ('content-engine', 'growth-canva', 'growth-copy')
GUARD_PATH = r'engine/[a-z0-9_/]+\.py:[A-Za-z_][A-Za-z0-9_]*'
GUARD = re.compile('^' + GUARD_PATH + '$')
TEST_DEF = re.compile(r'^\s*def (test_[A-Za-z0-9_]+)\(', re.M)
HOUSE = re.compile('\u2014|\x25|\\bper ?cent\\b', re.I)
PLAY = re.compile(r'\bP[1-9]\b')
# Two or three digits: R01 to R99, then R100 onwards for the rulings still to come.
RULE_REF = re.compile(r'\bR\d{2,3}\b')
FAILURE_REF = re.compile(r'\b(?:F\d{2,3}|G[1-9])\b')  # F01 to F99, then F100 onwards


def read(path):
    with open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def collapse(text):
    """Whitespace-insensitive form, so rewrapping a paragraph is not drift."""
    return ' '.join(text.split())


def house_errors(text):
    """The house rules for text a person reads: no em dash, no percentages."""
    return ['has an em dash or a percentage'] if HOUSE.search(text) else []


def test_names(root=ROOT):
    names = set()
    for path in sorted((Path(root) / 'tests').glob('test_*.py')):
        names.update(TEST_DEF.findall(path.read_text(encoding='utf-8')))
    return names


def _strings(value, field, at):
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(at + ': ' + field + ' must be a list of names')


def _pending(entry, at):
    """pending_tests are being built by another work item, named in pending_item."""
    if 'pending_tests' in entry:
        _strings(entry['pending_tests'], 'pending_tests', at)
    if (entry.get('pending_tests') or entry.get('status') == 'pending-build') and not (
            isinstance(entry.get('pending_item'), str) and entry['pending_item'].strip()):
        raise ValueError(at + ': pending work needs pending_item')


def load_rules(root=ROOT):
    rules = read(Path(root) / 'invariants' / 'rules.json').get('rules')
    if not isinstance(rules, list) or not rules:
        raise ValueError('rules.json needs a nonempty rules list')
    seen = set()
    for rule in rules:
        at = str(rule.get('id')) if isinstance(rule, dict) else '?'
        if not isinstance(rule, dict) or any(f not in rule for f in RULE_FIELDS):
            raise ValueError(at + ': rule needs ' + ', '.join(RULE_FIELDS))
        if not re.match(r'^R\d{2,3}$', rule['id']) or rule['id'] in seen:
            raise ValueError(at + ': rule id must be unique, like R01')
        seen.add(rule['id'])
        if rule['source_file'] not in RULE_SOURCES:
            raise ValueError(at + ': unknown source file')
        if not isinstance(rule['quote'], str) or len(collapse(rule['quote'])) < MIN_QUOTE:
            raise ValueError(at + ': quote must be at least 40 characters')
        if not isinstance(rule['statement'], str) or not rule['statement'].strip():
            raise ValueError(at + ': statement required')
        _strings(rule['enforced_by'], 'enforced_by', at)
        if not rule['enforced_by'] or any(not (GUARD.match(g) or g in ('doc-only', 'process'))
                                          for g in rule['enforced_by']):
            raise ValueError(at + ': enforced_by is engine/<file>.py:<function>, doc-only or process')
        if not isinstance(rule['tests'], list):
            raise ValueError(at + ': tests must be a list')
        _strings(rule['tests'], 'tests', at)
        _pending(rule, at)
    return rules


def check_quotes(rules, root=ROOT):
    """Each quote must still be a verbatim substring of its source file."""
    errors, texts = [], {}
    for rule in rules:
        name = rule['source_file']
        if name not in texts:
            path = Path(root) / name
            texts[name] = collapse(path.read_text(encoding='utf-8-sig')) if path.is_file() else None
        if texts[name] is None:
            errors.append(rule['id'] + ': source file missing: ' + name)
        elif collapse(rule['quote']) not in texts[name]:
            errors.append(rule['id'] + ': quote drifted from ' + name)
    return errors


def guard_exists(guard, root=ROOT):
    """engine/<file>.py:<name> names a def or class that exists in that file now."""
    path, _, name = guard.partition(':')
    path = Path(root) / path
    if not path.is_file():
        return False
    return bool(re.search(r'^\s*(?:def|class) ' + re.escape(name) + r'\b', path.read_text(encoding='utf-8'), re.M))


def check_rule_links(rules, root=ROOT, allow_pending=True):
    """Every named guard and test exists; pending tests only once allowed."""
    errors, names = [], test_names(root)
    for rule in rules:
        for guard in rule['enforced_by']:
            if GUARD.match(guard) and not guard_exists(guard, root):
                errors.append(rule['id'] + ': guard not found: ' + guard)
        wanted = rule['tests'] + ([] if allow_pending else rule.get('pending_tests', []))
        errors += [rule['id'] + ': test not found: ' + t for t in wanted if t not in names]
    return errors


def load_failures(root=ROOT):
    failures = read(Path(root) / 'invariants' / 'failures.json').get('failures')
    if not isinstance(failures, list):
        raise ValueError('failures.json needs a failures list')
    ids = [f.get('id') if isinstance(f, dict) else None for f in failures]
    if tuple(ids) != FAILURE_IDS:
        raise ValueError('the register is F01 to F54 from the plan, F55 to F{} after it, then G1 to G9, '
                         'once each, in order'.format(LAST_F))
    for entry in failures:
        at = entry['id']
        if any(f not in entry for f in FAILURE_FIELDS):
            raise ValueError(at + ': entry needs ' + ', '.join(FAILURE_FIELDS))
        if entry['status'] not in STATUSES:
            raise ValueError(at + ': unknown status')
        for field in ('title', 'source', 'guard'):
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise ValueError(at + ': ' + field + ' required')
        if not isinstance(entry['tests'], list):
            raise ValueError(at + ': tests must be a list')
        _strings(entry['tests'], 'tests', at)
        if 'planned_tests' in entry:
            _strings(entry['planned_tests'], 'planned_tests', at)
        if entry['status'] in ('tested', 'pending-build') and not entry['tests']:
            raise ValueError(at + ': a ' + entry['status'] + ' entry names its tests')
        _pending(entry, at)
    return failures


def check_failures(failures, root=ROOT, allow_pending=True):
    """Every named test is a def in tests/, unless another item is still building it.

    With allow_pending False, pending-build entries and pending_tests must
    exist too: the setting for after those work items have merged.
    """
    errors, names = [], test_names(root)
    for entry in failures:
        wanted = [] if entry['status'] == 'pending-build' and allow_pending else list(entry['tests'])
        if not allow_pending:
            wanted += entry.get('pending_tests', [])
        errors += [entry['id'] + ': test not found: ' + t for t in wanted if t not in names]
        for guard in re.findall(GUARD_PATH, entry['guard']):
            if entry['status'] == 'tested' and not guard_exists(guard, root):
                errors.append(entry['id'] + ': guard not found: ' + guard)
    return errors


def load_registry(root=ROOT):
    crew = read(Path(root) / 'crew' / 'registry.json').get('crew')
    if not isinstance(crew, list) or not crew:
        raise ValueError('registry.json needs a nonempty crew list')
    seen = set()
    for entry in crew:
        at = str(entry.get('id')) if isinstance(entry, dict) else '?'
        if not isinstance(entry, dict) or any(f not in entry for f in CREW_FIELDS):
            raise ValueError(at + ': crew entry needs ' + ', '.join(CREW_FIELDS))
        if not re.match(r'^[a-z][a-z0-9-]*$', entry['id']) or entry['id'] in seen:
            raise ValueError(at + ': crew id must be unique and lower-case')
        seen.add(entry['id'])
        for field in ('owns', 'channels', 'formats'):
            _strings(entry[field], field, at)
        for field in ('lint', 'check'):
            if not GUARD.match(entry[field]):
                raise ValueError(at + ': ' + field + ' is a planned engine/<file>.py:<function> path')
        if entry['card'] != 'crew/' + entry['id'] + '/card.md' or entry['lens'] != 'crew/' + entry['id'] + '/lens.md':
            raise ValueError(at + ': card and lens live in crew/<id>/')
        if type(entry['w45']) is not bool:
            raise ValueError(at + ': w45 must be true or false')
        if 'row' in entry and entry['row'] is not None and (type(entry['row']) is not int or entry['row'] < 1):
            raise ValueError(at + ': row is the plan section 3 row number, or null for the Release Gate')
    return crew


def check_cards(crew, root=ROOT, rule_ids=None, failure_ids=None):
    """Size limits, house rules, decision-table shape and live citations."""
    errors = []
    if {e['id'] for e in crew if e['w45']} != W45:
        errors.append('W45 crew must be exactly ' + ', '.join(sorted(W45)))
    for entry in crew:
        for field, limit in (('card', CARD_BYTES), ('lens', LENS_BYTES)):
            path = Path(root) / entry[field]
            if not path.is_file():
                errors.append(entry['id'] + ': missing ' + entry[field])
                continue
            data = path.read_bytes()
            text = data.decode('utf-8')
            if len(data) > limit:
                errors.append(entry['id'] + ': ' + field + ' is over ' + str(limit) + ' bytes')
            errors += [entry['id'] + ': ' + field + ' ' + e for e in house_errors(text)]
            if field == 'lens' and text.count('?') != 1:
                errors.append(entry['id'] + ': lens asks exactly one question')
            if field == 'card':
                errors += [entry['id'] + ': card ' + e for e in _card_errors(text, rule_ids, failure_ids)]
    return errors


def _card_errors(text, rule_ids=None, failure_ids=None):
    lines = text.splitlines()
    errors = []
    if not any(re.match(r'^\|\s*If\s*\|\s*Then\s*\|', line) for line in lines):
        errors.append('needs an If | Then decision table')
    rows = [line for line in lines if line.startswith('|') and not re.match(r'^\|\s*(If\s*\||-)', line)]
    if len(rows) < 3:
        errors.append('needs at least three decision rows')
    if any(re.match(r'^\s*(?:[-*+]|\d+[.)])\s', line) for line in lines):
        errors.append('has a free-text list; write it as decision rows')
    if not PLAY.search(text):
        errors.append('cites no play (P1 to P9)')
    cited = set(RULE_REF.findall(text))
    if not cited:
        errors.append('cites no invariant rule')
    if rule_ids is not None:
        errors += ['cites unknown rule ' + r for r in sorted(cited - set(rule_ids))]
    if failure_ids is not None:
        errors += ['cites unknown failure ' + f for f in sorted(set(FAILURE_REF.findall(text)) - set(failure_ids))]
    return errors


def load_sources(root=ROOT):
    data = read(Path(root) / 'invariants' / 'sources.json')
    for field in ('approved', 'approved_by', 'approved_at', 'note', 'categories'):
        if field not in data:
            raise ValueError('sources.json needs ' + field)
    if not isinstance(data['categories'], dict) or not data['categories']:
        raise ValueError('sources.json needs categories')
    for label, value in data['categories'].items():
        if label != label.lower() or label != label.strip() or value not in SOURCE_CLASSES:
            raise ValueError('source ' + repr(label) + ' must be lower-case and organic, unattributed or paid')
    if data['approved'] is not True and (data['approved_by'] is not None or data['approved_at'] is not None):
        raise ValueError('an unapproved classification names no approver')
    return data


def load_boundary(root=ROOT):
    data = read(Path(root) / 'invariants' / 'boundary.json')
    for field in ('source_file', 'quote', 'owners'):
        if field not in data:
            raise ValueError('boundary.json needs ' + field)
    if not isinstance(data['owners'], dict) or any(v not in OWNERS for v in data['owners'].values()):
        raise ValueError('every format names content-engine, growth-canva or growth-copy')
    return data


# Authority and lanes (Krish, 27 Oct 2026: rules R105 to R107) -----------------

AUTHORITY_FIELDS = ('schema_version', 'kind', 'note', 'source_file', 'first_signed_week', 'show_before_post_until',
                    'publish_board', 'derivative_formats', 'new_formats_need_eyes', 'any_other_class', 'krish_hands')
BOARD = ('article', 'assets', 'video-recordings')
HANDS = ('linkedin-posting', 'plan-purchase', 'credential-creation', 'account-connection')
NEW_FORMATS = ('carousel', 'meme', 'opinion', 'reactive')
ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
ISO_WEEK = re.compile(r'^(\d{4})-W(\d{2})$')
# No L1: there are no Claude routines and no Claude schedules of any kind (Krish, 29 Oct 2026). A new
# schedule is an L0 GitHub Actions job; making is done by sessions and the PC automations under the walls.
LANES = ('L0_code', 'L2_eyes', 'L3_hands')
LANE_JOB_FIELDS = ('id', 'lane', 'workflow', 'trigger', 'may_write', 'never', 'actions', 'secrets')
AUTOMATION_FIELDS = ('name', 'source', 'jobs', 'status', 'successor')
# The jobs Krish's lanes ruling names (CHANGES.md, 27 Oct evening); each is in lanes.json exactly once.
LANE_JOBS = {'L0_code': ('control-center', 'release', 'measure', 'keys', 'handoff', 'maker'),
             'L2_eyes': ('publish-board', 'preview-packet', 'new-format-item', 'week-sign-off'),
             'L3_hands': ('linkedin-posting', 'buffer-plan', 'one-time-setup')}
ENGINE_KEYS = ('CONTROL_CENTER_ENGINE_TOKEN', 'GROWTH_ENGINE_TOKEN')


def _closed(value, fields, at):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(at + ' needs exactly ' + ', '.join(fields))


def _classes(entries, at):
    if not isinstance(entries, list) or not entries:
        raise ValueError(at + ' needs a nonempty list')
    for entry in entries:
        _closed(entry, ('class', 'what', 'formats'), at)
        if not isinstance(entry['class'], str) or not ID.match(entry['class']):
            raise ValueError(at + ': class must be a lower-case id')
        if not isinstance(entry['what'], str) or not entry['what'].strip():
            raise ValueError(at + ': ' + entry['class'] + ' says what it is')
        _strings(entry['formats'], 'formats', at + '.' + entry['class'])
        if not entry['formats'] or not all(ID.match(f) for f in entry['formats']):
            raise ValueError(at + '.' + entry['class'] + ': formats are social/formats ids')
    return [entry['class'] for entry in entries]


def preview_end(first_week):
    """The Sunday that ends the fourth signed week (Monday-start New York weeks, ISO numbered)."""
    match = ISO_WEEK.match(first_week) if isinstance(first_week, str) else None
    if not match:
        raise ValueError('first_signed_week must look like 2026-W45')
    start = datetime.date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
    return start + datetime.timedelta(days=27)


def load_authority(root=ROOT):
    """invariants/authority.json in its closed shape. Raises ValueError when malformed."""
    data = read(Path(root) / 'invariants' / 'authority.json')
    _closed(data, AUTHORITY_FIELDS, 'authority.json')
    if data['schema_version'] != 1 or data['kind'] != 'authority':
        raise ValueError('authority.json is schema_version 1, kind authority')
    if data['source_file'] not in RULE_SOURCES:
        raise ValueError('authority.json cites a rule source file')
    try:
        until = datetime.date.fromisoformat(data['show_before_post_until'])
    except (TypeError, ValueError):
        raise ValueError('show_before_post_until must be YYYY-MM-DD') from None
    if until != preview_end(data['first_signed_week']):
        raise ValueError('show_before_post_until is four weeks from the first signed week: '
                         + preview_end(data['first_signed_week']).isoformat())
    board = data['publish_board']
    _closed(board, ('includes', 'approved_in', 'unlocks'), 'publish_board')
    if not isinstance(board['includes'], list) or tuple(board['includes']) != BOARD:
        raise ValueError('a publish board includes the article, the assets and the video recordings')
    derivative = _classes(data['derivative_formats'], 'derivative_formats')
    new = _classes(data['new_formats_need_eyes'], 'new_formats_need_eyes')
    if len(set(derivative + new)) != len(derivative) + len(new):
        raise ValueError('a class is either a derivative or a new format, once')
    if not set(NEW_FORMATS) <= set(new):
        raise ValueError('carousel, meme, opinion and reactive always need his eyes')
    if data['any_other_class'] != 'needs_eyes':
        raise ValueError('any class not listed as a derivative needs his eyes')
    hands = data['krish_hands']
    if not isinstance(hands, list):
        raise ValueError('krish_hands needs a list')
    for entry in hands:
        _closed(entry, ('id', 'what', 'channels'), 'krish_hands')
        if not isinstance(entry['channels'], list) or not all(isinstance(c, str) for c in entry['channels']):
            raise ValueError('krish_hands.' + str(entry['id']) + ': channels is a list')
    ids = [entry['id'] for entry in hands]
    if len(ids) != len(set(ids)) or not set(HANDS) <= set(ids):
        raise ValueError('krish_hands names ' + ', '.join(HANDS) + ', once each')
    if 'linkedin' not in hands_channels(data):
        raise ValueError('LinkedIn posting stays in his hands')
    return data


def hands_channels(authority):
    return {c for entry in authority['krish_hands'] for c in entry['channels']}


def check_authority(authority, root=ROOT):
    """Every named format and channel exists, and every human-only channel stays in his hands."""
    from ..social import inventory
    records = inventory(root)
    errors = []
    for field in ('derivative_formats', 'new_formats_need_eyes'):
        for entry in authority[field]:
            errors += [field + '.' + entry['class'] + ': unknown format ' + f
                       for f in entry['formats'] if f not in records['format']]
    errors += ['krish_hands: unknown channel ' + c for c in sorted(hands_channels(authority))
               if c not in records['channel']]
    errors += [c + ' is human_publish_only but not in krish_hands' for c, obj in sorted(records['channel'].items())
               if obj['publication_mode'] == 'human_publish_only' and c not in hands_channels(authority)]
    return errors


def class_of(authority, name):
    """('derivative' | 'new', formats) for a listed class; ('new', None) for any other."""
    for kind, field in (('derivative', 'derivative_formats'), ('new', 'new_formats_need_eyes')):
        for entry in authority[field]:
            if entry['class'] == name:
                return kind, entry['formats']
    return 'new', None


def posting_lane(authority, name, channel, format_id=None):
    """The lane a post of this class lands in. An unknown or mismatched class needs his eyes.

    A derivative of an approved piece is released by code (release.yml, L0) with no per-post press.
    """
    if channel in hands_channels(authority):
        return 'L3_hands'
    kind, formats = class_of(authority, name)
    if kind == 'derivative' and (format_id is None or format_id in formats):
        return 'L0_code'
    return 'L2_eyes'


def needs_preview(authority, day):
    """True on or before show_before_post_until: each batch is shown to Krish first."""
    day = day if isinstance(day, datetime.date) else datetime.date.fromisoformat(day)
    return day <= datetime.date.fromisoformat(authority['show_before_post_until'])


def may_post_alone(authority, name, channel, format_id, day, board_approved=False, preview_approved=False,
                   item_approved=False):
    """(allowed, reason) for one post. Never for his hands; a new format needs its own approval."""
    lane = posting_lane(authority, name, channel, format_id)
    if lane == 'L3_hands':
        return False, 'krish_hands'
    if lane == 'L2_eyes':
        return (True, 'item_approved') if item_approved else (False, 'needs_eyes')
    if not board_approved:
        return False, 'publish_board_not_approved'
    if needs_preview(authority, day) and not preview_approved:
        return False, 'preview_packet_needed'
    return True, 'derivative'


def load_lanes(root=ROOT):
    """lanes.json in its closed shape. Raises ValueError when malformed."""
    data = read(Path(root) / 'lanes.json')
    _closed(data, ('schema_version', 'kind', 'note', 'authority', 'lanes', 'jobs', 'automations'), 'lanes.json')
    if data['schema_version'] != 1 or data['kind'] != 'lanes' or data['authority'] != 'invariants/authority.json':
        raise ValueError('lanes.json is schema_version 1, kind lanes, reading invariants/authority.json')
    if not isinstance(data['lanes'], dict) or tuple(data['lanes']) != LANES:
        raise ValueError('lanes are ' + ', '.join(LANES) + ', in order')
    for name, lane in data['lanes'].items():
        _closed(lane, ('who', 'runs_on', 'model'), 'lanes.' + name)
        if lane['model'] is not False:
            raise ValueError('lanes.' + name + ': no lane runs a model; there are no Claude routines'
                             ' (Krish, 29 Oct 2026)')
    if not isinstance(data['jobs'], list) or not isinstance(data['automations'], list):
        raise ValueError('jobs and automations are lists')
    for job in data['jobs']:
        _closed(job, LANE_JOB_FIELDS, 'job ' + str(job.get('id') if isinstance(job, dict) else '?'))
        at = 'job ' + str(job['id'])
        if not isinstance(job['id'], str) or not ID.match(job['id']) or job['lane'] not in LANES:
            raise ValueError(at + ': id is lower-case and lane is one of ' + ', '.join(LANES))
        if not isinstance(job['trigger'], str) or not job['trigger'].strip():
            raise ValueError(at + ': trigger required')
        for field in ('may_write', 'never', 'actions', 'secrets'):
            if not isinstance(job[field], list) or not all(isinstance(x, str) and x.strip() for x in job[field]):
                raise ValueError(at + ': ' + field + ' is a list of strings')
        if not job['never']:
            raise ValueError(at + ': says what it must never do')
        if (job['lane'] == 'L0_code') != isinstance(job['workflow'], str):
            raise ValueError(at + ': an L0 job names its workflow file; no other lane has one')
        if isinstance(job['workflow'], str) and not re.match(r'^[a-z0-9][a-z0-9-]*\.yml$', job['workflow']):
            raise ValueError(at + ': workflow is a file name in .github/workflows')
    for entry in data['automations']:
        _closed(entry, AUTOMATION_FIELDS, 'automation ' + str(entry.get('name') if isinstance(entry, dict) else '?'))
        at = 'automation ' + str(entry['name'])
        if entry['status'] != 'kept-until-W46':
            raise ValueError(at + ': status kept-until-W46')
        _strings(entry['jobs'], 'jobs', at)
        if entry['source'] not in ('automations.json', 'heartbeat'):
            raise ValueError(at + ': source is automations.json or heartbeat')
    return data


def check_lanes(lanes, authority, root=ROOT):
    """Every workflow and job sits in exactly one lane; no L0 job holds his hands or his eyes.

    A workflow lanes.json declares but that does not exist yet passes (another
    item may still be building it); a workflow file lanes.json does not name fails.
    A routines/ folder fails: there are no Claude routines (Krish, 29 Oct 2026).
    """
    root = Path(root)
    errors = []
    if (root / 'routines').exists():
        errors.append('routines/ exists: there are no Claude routines (Krish, 29 Oct 2026); '
                      'a schedule is a GitHub Actions job')
    ids = [job['id'] for job in lanes['jobs']]
    everything = ids + [entry['name'] for entry in lanes['automations']]
    errors += ['named more than once: ' + n for n in sorted({n for n in everything if everything.count(n) > 1})]
    by_id = {job['id']: job for job in lanes['jobs']}
    for lane, wanted in sorted(LANE_JOBS.items()):
        for name in wanted:
            if name not in by_id:
                errors.append('missing job ' + name)
            elif by_id[name]['lane'] != lane:
                errors.append(name + ' belongs in ' + lane)
    declared = [job['workflow'] for job in lanes['jobs'] if job['workflow']]
    errors += ['workflow in two jobs: ' + w for w in sorted({w for w in declared if declared.count(w) > 1})]
    folder = root / '.github' / 'workflows'
    files = sorted(folder.glob('*.y*ml')) if folder.is_dir() else []
    for path in files:
        if path.name not in declared:
            errors.append('workflow not in lanes.json: ' + path.name)
            continue
        job = next(j for j in lanes['jobs'] if j['workflow'] == path.name)
        text = path.read_text(encoding='utf-8')
        errors += [path.name + ' reads ' + key + ' but job ' + job['id'] + ' does not declare it'
                   for key in ENGINE_KEYS if key in text and key not in job['secrets']]
    errors += [job['id'] + ': only L0 code on the GitHub runner holds a key'
               for job in lanes['jobs'] if job['lane'] != 'L0_code' and job['secrets']]
    hands = {entry['id'] for entry in authority['krish_hands']}
    eyes = {a for job in lanes['jobs'] if job['lane'] == 'L2_eyes' for a in job['actions']}
    for job in lanes['jobs']:
        if job['lane'] == 'L0_code':
            errors += [job['id'] + ' (' + job['lane'] + ') holds his hands: ' + a for a in job['actions'] if a in hands]
            errors += [job['id'] + ' (' + job['lane'] + ') holds his eyes: ' + a for a in job['actions'] if a in eyes]
        if job['lane'] == 'L3_hands':
            errors += [job['id'] + ': an L3 action is a krish_hands id, not ' + a
                       for a in job['actions'] if a not in hands]
    held = {a for job in lanes['jobs'] if job['lane'] == 'L3_hands' for a in job['actions']}
    errors += ['no L3 job holds ' + h for h in sorted(hands - held)]
    config = read(root / 'automations.json')['automations']
    listed = [entry['name'] for entry in lanes['automations'] if entry['source'] == 'automations.json']
    if sorted(listed) != sorted(entry['name'] for entry in config):
        errors.append('lanes.json automations must name every automations.json entry once')
    files_named = [f for entry in lanes['automations'] for f in entry['jobs']]
    on_disk = sorted('jobs/' + p.name for p in (root / 'jobs').glob('*.md'))
    errors += ['job file in no automation: ' + f for f in on_disk if f not in files_named]
    errors += ['job file named more than once: ' + f for f in sorted(set(files_named)) if files_named.count(f) > 1]
    errors += ['job file missing: ' + f for f in sorted(set(files_named)) if f not in on_disk]
    errors += [entry['name'] + ': successor ' + str(entry['successor']) + ' is not a lanes.json job'
               for entry in lanes['automations'] if entry['successor'] is not None and entry['successor'] not in by_id]
    return errors
