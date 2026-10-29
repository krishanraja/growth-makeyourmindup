"""Built to be sent (Ruling, Krish, 2026-10-28): the share block, the share-CTA lint and the blind send test.

Offline and pure. Nothing here calls a model, opens a network connection or acts
on a platform. The words and patterns live in social/share.json; the block's
shape lives in social/schemas/package.schema.json. The send test is defined as
data (the reader's prompt) plus pure functions: one builds the only request a
fresh reader may see, bound to the exact post by its request_sha256, the other
compares the reader's answer with the declared block. stage_send_test is the
one writer: it copies the assets, under blind names, into a new folder.
"""
import hashlib
import json
from pathlib import Path
import re

from .copy_lint import normalise
from .packs import prose_errors

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'social' / 'share.json'
JOBS = ('in_the_know', 'helps_them', 'so_us', 'settles_it', 'warns_them', 'laugh_or_awe')
SHARE_FIELDS = ('sender', 'receiver', 'job', 'dm_line', 'moment', 'standalone')
WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
WORD_SETS = ('filler_words', 'crowd_words', 'generic_words', 'descriptor_words', 'vague_qualifiers',
             'role_prepositions', 'receiver_own_openers', 'receiver_other_openers', 'receiver_personal_words')
SCOPES = ('snackable', 'all_post_copy')
ANSWER_FIELDS = ('would_send', 'receiver', 'job', 'dm_line', 'why', 'request_sha256')
SUFFIX = re.compile(r'^\.[a-z0-9]{1,8}$')


class StaleSendTest(ValueError):
    """A reader's answer given for another request: another revision of the post, or none named."""


def _words(text):
    return WORD.findall(text.lower().replace('’', "'"))


def load_rules(path=RULES):
    """social/share.json, checked and with its patterns compiled. Raises ValueError when malformed."""
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('kind') != 'share_rules' or data.get('schema_version') != 1:
        raise ValueError('share.json must be a share_rules object, schema_version 1')
    if tuple(data.get('jobs', {})) != JOBS or not all(isinstance(v, str) and v.strip() for v in data['jobs'].values()):
        raise ValueError('share.json jobs must be exactly ' + ', '.join(JOBS) + ', each described')
    limit = data.get('dm_line_max_chars')
    if type(limit) is not int or not 20 <= limit <= 280:
        raise ValueError('share.json dm_line_max_chars must be a whole number from 20 to 280')
    for name in WORD_SETS + ('generic_dm_phrases',):
        values = data.get(name)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise ValueError('share.json ' + name + ' must be a nonempty list of words')
    aliases = data.get('receiver_aliases')
    if not isinstance(aliases, dict) or not all(isinstance(v, list) and v for v in aliases.values()):
        raise ValueError('share.json receiver_aliases must map a canonical word to its other names')
    breaks = data.get('receiver_clause_breaks')
    if not isinstance(breaks, list) or not breaks or not all(isinstance(b, str) and b for b in breaks):
        raise ValueError('share.json receiver_clause_breaks must list where the role in a receiver ends')
    if data.get('share_cta_scope') not in SCOPES:
        raise ValueError('share.json share_cta_scope must be one of ' + ', '.join(SCOPES))
    anchor = data.get('imperative_anchor')
    if not isinstance(anchor, str) or not anchor:
        raise ValueError('share.json imperative_anchor must be a pattern')
    patterns = []
    for entry in data.get('share_cta') or []:
        if not isinstance(entry, dict) or not entry.get('id') or not entry.get('pattern'):
            raise ValueError('each share_cta entry needs an id and a pattern')
        if type(entry.get('anchored', False)) is not bool:
            raise ValueError('share_cta ' + entry['id'] + ' anchored must be true or false')
        # An anchored ask is an imperative: it counts only where a sentence, line or if-clause starts.
        source = anchor + '(?P<ask>' + entry['pattern'] + ')' if entry.get('anchored') else entry['pattern']
        try:
            patterns.append((entry['id'], re.compile(source, re.I)))
        except re.error as exc:
            raise ValueError('share_cta ' + entry['id'] + ' does not compile: ' + str(exc)) from None
    if not patterns:
        raise ValueError('share.json needs share_cta patterns')
    test = data.get('send_test') or {}
    if not isinstance(test.get('prompt'), list) or not test['prompt'] or not all(
            isinstance(line, str) and line.strip() for line in test['prompt']):
        raise ValueError('share.json send_test.prompt must be a nonempty list of lines')
    if tuple(test.get('answer_fields') or ()) != ANSWER_FIELDS:
        raise ValueError('share.json send_test.answer_fields must be exactly ' + ', '.join(ANSWER_FIELDS))
    reader = test.get('reader')
    if not isinstance(reader, dict) or not (reader.get('persona') is None or isinstance(reader['persona'], str)) \
            or not isinstance(reader.get('decision'), str) or not reader['decision'].strip():
        raise ValueError('share.json send_test.reader records the persona (or null) and whose decision it is')
    for line in test['prompt'] + list(data['jobs'].values()):
        if prose_errors(line):
            raise ValueError('share.json text ' + prose_errors(line)[0])
    rules = dict(data)
    rules['_cta'] = patterns
    rules['_sets'] = {name: frozenset(w.lower() for w in data[name]) for name in WORD_SETS}
    rules['_alias'] = sorted(((other.lower(), canon.lower()) for canon, others in aliases.items() for other in others),
                             key=lambda pair: -len(pair[0]))
    rules['_phrases'] = sorted((p.lower() for p in data['generic_dm_phrases']), key=len, reverse=True)
    return rules


_DEFAULT = []


def rules_or_default(rules=None):
    if rules is not None:
        return rules
    if not _DEFAULT:
        _DEFAULT.append(load_rules())
    return _DEFAULT[0]


# The share-CTA lint -------------------------------------------------------

def cta_applies(snackable, rules=None):
    """Whether post copy of this kind is checked for share asks (share.json share_cta_scope)."""
    return bool(snackable) or rules_or_default(rules)['share_cta_scope'] == 'all_post_copy'


def cta_errors(text, rules=None):
    """Each generic share call to action in post copy, as 'id: "matched words"'. Empty means clean."""
    rules = rules_or_default(rules)
    if not isinstance(text, str):
        return []
    # Odd spaces and line ends read as content-engine's copy lint reads them, so a no-break space
    # or a U+2028 line end never hides an ask.
    text = normalise(text).replace('’', "'")
    found = []
    for name, pattern in rules['_cta']:
        match = pattern.search(text)
        if match:
            words = match.groupdict().get('ask') or match.group(0)
            found.append(name + ': "' + words.strip() + '"')
    return found


# The share block ----------------------------------------------------------

def _role(text, rules):
    """The words before the first clause break: who the person is, never what the clause says they do."""
    role = ' ' + (text if isinstance(text, str) else '').lower().replace('’', "'") + ' '
    for mark in rules['receiver_clause_breaks']:
        role = role.split(mark, 1)[0] + ' '
    return _words(role)


def _head(text, rules):
    """The role up to its first preposition: "a friend at work" is a friend, "your mate in sales" a mate."""
    head = []
    for word in _role(text, rules):
        if word in rules['_sets']['role_prepositions']:
            break
        head.append(word)
    return head


def person_errors(text, field, rules=None):
    """A sender or receiver names one specific person by role or relationship, never a crowd or a blank."""
    rules = rules_or_default(rules)
    if not isinstance(text, str) or not text.strip():
        return [field + ' must name a person']
    sets = rules['_sets']
    head = _head(text, rules)
    crowd = [w for w in head if w in sets['crowd_words']]
    if crowd:
        return [field + ' "' + text.strip() + '" is a crowd ("' + crowd[0] + '"); name one specific person']
    empty = sets['filler_words'] | sets['generic_words'] | sets['vague_qualifiers']
    if not [w for w in head if w not in empty]:
        return [field + ' "' + text.strip() + '" is vague; open with the role or relationship, for example'
                ' "a head of marketing" to "her CEO"']
    return []


def _content(text, rules):
    return [w for w in _words(text) if w not in rules['_sets']['filler_words']]


def _specific_words(text, rules):
    lowered = ' ' + ' '.join(_words(text)) + ' '
    for phrase in rules['_phrases']:
        lowered = lowered.replace(' ' + ' '.join(_words(phrase)) + ' ', ' ')
    return [w for w in lowered.split() if w not in rules['_sets']['filler_words']
            and w not in rules['_sets']['generic_words']]


def dm_line_errors(text, rules=None):
    """The exact words the sender types: short, plain, specific, and never a call to action.

    The generic check is a floor (a phrase list and a count of the words left);
    whether a stranger would really type it is the blind reader's test.
    """
    rules = rules_or_default(rules)
    if not isinstance(text, str) or not text.strip():
        return ['dm_line must be the exact words the sender would type']
    errors = []
    if '\n' in text or '\r' in text:
        errors.append('dm_line must be one line')
    if len(text.strip()) > rules['dm_line_max_chars']:
        errors.append('dm_line is ' + str(len(text.strip())) + ' characters; the limit is '
                      + str(rules['dm_line_max_chars']))
    errors += ['dm_line ' + e for e in prose_errors(text)]
    cta = cta_errors(text, rules)
    if cta:
        errors.append('dm_line is a share call to action (' + cta[0] + '); write what the sender would say')
    elif len(_specific_words(text, rules)) < rules['min_specific_words']['dm_line']:
        errors.append('dm_line "' + text.strip() + '" is too generic; say the specific reason this person'
                      ' sends it to that one')
    return errors


def share_errors(share, snackable=True, rules=None):
    """Every reason a package's share block fails; empty when it is complete and specific."""
    rules = rules_or_default(rules)
    if share is None:
        return ['a snackable package needs a share block (sender, receiver, job, dm_line, moment, standalone)'] \
            if snackable else []
    if not isinstance(share, dict):
        return ['share must be an object']
    missing = [f for f in SHARE_FIELDS if f not in share]
    extra = sorted(set(share) - set(SHARE_FIELDS))
    if missing or extra:
        return ['share needs exactly ' + ', '.join(SHARE_FIELDS)
                + (': missing ' + ', '.join(missing) if missing else '')
                + (': unknown ' + ', '.join(extra) if extra else '')]
    errors = person_errors(share['sender'], 'sender', rules) + person_errors(share['receiver'], 'receiver', rules)
    if not errors and not receiver_key(share['receiver'], rules):
        errors.append('receiver must open with the role or relationship, before any comma or "who" clause')
    for field in ('sender', 'receiver', 'moment'):
        if isinstance(share[field], str):
            errors += [field + ' ' + e for e in prose_errors(share[field])]
    if share['job'] not in JOBS:
        errors.append('job must be one of ' + ', '.join(JOBS))
    errors += dm_line_errors(share['dm_line'], rules)
    moment = share['moment']
    if not isinstance(moment, str) or len(_content(moment, rules)) < rules['min_specific_words']['moment']:
        errors.append('moment must describe the everyday situation that brings the post to mind')
    if type(share['standalone']) is not bool:
        errors.append('standalone must be true or false')
    elif snackable and not share['standalone']:
        errors.append('a snackable post is sent to someone who never saw the source, so it must work with no'
                      ' context (standalone true) before it can pass')
    return errors


def share_line(share, rules=None):
    """One plain line for a board or a run spec's forward_line: who sends it to whom, why, and the words."""
    rules = rules_or_default(rules)
    if share_errors(share, True, rules):
        raise ValueError('share block is incomplete: ' + share_errors(share, True, rules)[0])
    job = share['job'].replace('_', ' ')
    return share['sender'].strip() + ' sends it to ' + share['receiver'].strip() + ' (' + job + '): "' \
        + share['dm_line'].strip() + '"'


def receiver_key(text, rules=None):
    """The words that identify a receiver, aliases folded, so 'her chief executive' meets 'my CEO'.

    Only the role is compared: the description after a comma or a relative
    clause ("who keeps asking...") is context, and matching on it would let a
    shared topic word pass for the same person.
    """
    rules = rules_or_default(rules)
    lowered = ' ' + ' '.join(_role(text, rules)) + ' '
    for other, canon in rules['_alias']:
        lowered = lowered.replace(' ' + ' '.join(_words(other)) + ' ', ' ' + canon + ' ')
    sets = rules['_sets']
    skip = (sets['filler_words'] | sets['generic_words'] | sets['crowd_words'] | sets['vague_qualifiers']
            | sets['role_prepositions'])
    terms = []
    for word in lowered.split():
        if word in skip:
            continue
        if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
            word = word[:-1]
        terms.append(word)
    core = {w for w in terms if w not in sets['descriptor_words']}
    return core or set(terms)


def receiver_relation(text, rules=None):
    """'own' for the sender's own person (her CEO), 'other' for plainly someone else's (a CEO at a
    competitor), else None. A reader's 'a CEO I report to' names someone personal, so it is not 'other'."""
    rules = rules_or_default(rules)
    role, sets = _role(text, rules), rules['_sets']
    if not role:
        return None
    if role[0] in sets['receiver_own_openers']:
        return 'own'
    if role[0] in sets['receiver_other_openers'] and not any(w in sets['receiver_personal_words'] for w in role):
        return 'other'
    return None


# The blind send test ------------------------------------------------------

def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def request_digest(prompt, post):
    """The sha256 of the canonical {prompt, post}: what binds a reader's answer to one revision."""
    return hashlib.sha256(_canonical({'prompt': prompt, 'post': post}).encode('utf-8')).hexdigest()


def blind_name(index, source):
    """asset-<n> plus the file's own extension: no folder, no package name, nothing to follow back."""
    suffix = Path(str(source)).suffix.lower()
    return 'asset-' + str(index) + (suffix if SUFFIX.match(suffix) else '')


def _request(fmt, copy, assets, rules):
    prompt = '\n'.join(rules['send_test']['prompt'])
    post = {'format': fmt, 'copy': copy,
            'assets': [{'name': blind_name(i, source), 'sha256': sha} for i, (source, sha) in enumerate(assets, 1)]}
    return {'local_only': True, 'blind': True, 'reader_card': rules['send_test']['reader_card'],
            'prompt': prompt, 'post': post, 'request_sha256': request_digest(prompt, post)}


def send_test_request(package, rules=None):
    """The only thing a fresh reader sees: the prompt, the format, the copy and the asset bytes by blind name.

    Never the share block, the source, the channel, a production note or a path,
    so its answer cannot echo what the author declared. request_sha256 changes
    with any change to the prompt, the format, the copy or the asset bytes.
    """
    rules = rules_or_default(rules)
    return _request(package['format'], package['caption'],
                    [(a['path'], a['sha256']) for a in package['assets']], rules)


def slot_send_test_request(slot, rules=None):
    """The same blind request for a run-spec slot: its format, its words and its asset hashes."""
    rules = rules_or_default(rules)
    return _request(slot['format'], slot['words'], [(a['name'], a['sha256']) for a in slot['assets']], rules)


def _stage(request, sources, folder):
    """Copy each (path, sha256) under its blind name, with request.json, into a new or empty folder."""
    folder = Path(folder)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('the send-test folder must be new or empty: ' + str(folder))
    files = []
    for (path, sha), entry in zip(sources, request['post']['assets']):
        if not Path(path).is_file():
            raise ValueError('asset file not found for ' + entry['name'] + ': ' + Path(path).name)
        data = Path(path).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('asset bytes do not match their sha256: ' + entry['name'])
        files.append((entry['name'], data))
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in files:
        (folder / name).write_bytes(data)
    (folder / 'request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return request


def stage_send_test(package, folder, root=ROOT, rules=None):
    """Copy the package's assets under their blind names, with request.json, into a new or empty folder.

    The reader is handed only that folder, so no path leads it back to the
    package or its share block. Refuses changed bytes and a folder in use.
    """
    rules = rules_or_default(rules)
    sources = []
    for asset in package['assets']:
        path = Path(asset['path'])
        sources.append((path if path.is_absolute() else Path(root) / path, asset['sha256']))
    return _stage(send_test_request(package, rules), sources, folder)


def stage_slot_send_test(slot, folder, assets, rules=None):
    """The same staging for a run slot: each asset is found by its slot name in the assets folder.

    The folder holds fresh copies of the slot's assets (their names are the
    slot's, which can hint at the receiver), so they are checked against their
    sha256 and copied under blind names; the reader is handed only the new folder.
    """
    rules = rules_or_default(rules)
    assets = Path(assets)
    if not assets.is_dir():
        raise ValueError('the assets folder does not exist: ' + str(assets))
    sources = []
    for asset in slot['assets']:
        name = asset['name']
        if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..'):
            raise ValueError('a slot asset name must be a plain file name: ' + repr(name))
        sources.append((assets / name, asset['sha256']))
    if Path(folder).resolve() == assets.resolve():
        raise ValueError('stage into a new folder, never the assets folder')
    return _stage(slot_send_test_request(slot, rules), sources, folder)


def compare_send_test(declared, answer, request, rules=None):
    """Pass when the blind reader's receiver and job match the declared share block; else revise.

    The answer must name the request_sha256 of this exact request: an answer to
    an earlier revision, or to none, raises StaleSendTest. The reader's answer
    is returned whole so the revision starts from what a stranger actually said.
    """
    rules = rules_or_default(rules)
    problems = share_errors(declared, True, rules)
    if problems:
        raise ValueError('declared share block is incomplete: ' + problems[0])
    if not isinstance(request, dict) or not isinstance(request.get('request_sha256'), str) \
            or request['request_sha256'] != request_digest(request.get('prompt'), request.get('post')):
        raise ValueError('the send-test request does not recompute; build it with send_test_request')
    if not isinstance(answer, dict) or type(answer.get('would_send')) is not bool:
        raise ValueError('the reader answer needs would_send true or false')
    unknown = sorted(set(answer) - set(rules['send_test']['answer_fields']))
    if unknown:
        raise ValueError('the reader answer has unknown fields: ' + ', '.join(unknown))
    named = answer.get('request_sha256')
    if named != request['request_sha256']:
        raise StaleSendTest(('the reader answer names no request_sha256' if not isinstance(named, str) else
                             'the reader answered request ' + named[:12] + ', not ' + request['request_sha256'][:12])
                            + '; an earlier answer never carries over, so run a fresh reader on this revision')
    reasons = []
    if not answer['would_send']:
        reasons.append('the blind reader would not send it to anyone')
    else:
        for field in ('receiver', 'dm_line'):
            if not isinstance(answer.get(field), str) or not answer[field].strip():
                raise ValueError('a reader who would send it names the ' + field)
        if answer.get('job') not in JOBS:
            raise ValueError('the reader answer job must be one of ' + ', '.join(JOBS))
        if answer['job'] != declared['job']:
            reasons.append('the reader would send it to ' + answer['job'].replace('_', ' ') + ', not to '
                           + declared['job'].replace('_', ' '))
        other = (receiver_relation(declared['receiver'], rules) == 'own'
                 and receiver_relation(answer['receiver'], rules) == 'other')
        if other or not receiver_key(declared['receiver'], rules) & receiver_key(answer['receiver'], rules):
            reasons.append('the reader would send it to "' + answer['receiver'].strip() + '", not to "'
                           + declared['receiver'].strip() + '"')
    return {'local_only': True, 'verdict': 'revise' if reasons else 'pass', 'reasons': reasons,
            'request_sha256': request['request_sha256'],
            'declared': {'receiver': declared['receiver'], 'job': declared['job']}, 'reader_answer': answer}
