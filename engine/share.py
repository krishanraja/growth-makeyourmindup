"""Built to be sent (Ruling, Krish, 2026-10-28): the share block, the share-CTA lint and the blind send test.

Offline and pure. Nothing here calls a model, opens a network connection or acts
on a platform. The words and patterns live in social/share.json; the block's
shape lives in social/schemas/package.schema.json. The send test is defined as
data (the reader's prompt) plus pure functions: one builds the only request a
fresh reader may see, the other compares its answer with the declared block.
"""
import json
from pathlib import Path
import re

from .packs import prose_errors

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'social' / 'share.json'
JOBS = ('in_the_know', 'helps_them', 'so_us', 'settles_it', 'warns_them', 'laugh_or_awe')
SHARE_FIELDS = ('sender', 'receiver', 'job', 'dm_line', 'moment', 'standalone')
WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
LISTS = ('filler_words', 'crowd_words', 'generic_words', 'descriptor_words', 'generic_dm_phrases')


def _words(text):
    return WORD.findall(text.lower().replace('\u2019', "'"))


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
    for name in LISTS:
        values = data.get(name)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise ValueError('share.json ' + name + ' must be a nonempty list of words')
    aliases = data.get('receiver_aliases')
    if not isinstance(aliases, dict) or not all(isinstance(v, list) and v for v in aliases.values()):
        raise ValueError('share.json receiver_aliases must map a canonical word to its other names')
    breaks = data.get('receiver_clause_breaks')
    if not isinstance(breaks, list) or not breaks or not all(isinstance(b, str) and b for b in breaks):
        raise ValueError('share.json receiver_clause_breaks must list where the role in a receiver ends')
    patterns = []
    for entry in data.get('share_cta') or []:
        if not isinstance(entry, dict) or not entry.get('id') or not entry.get('pattern'):
            raise ValueError('each share_cta entry needs an id and a pattern')
        try:
            patterns.append((entry['id'], re.compile(entry['pattern'], re.I)))
        except re.error as exc:
            raise ValueError('share_cta ' + entry['id'] + ' does not compile: ' + str(exc)) from None
    if not patterns:
        raise ValueError('share.json needs share_cta patterns')
    test = data.get('send_test') or {}
    if not isinstance(test.get('prompt'), list) or not test['prompt'] or not all(
            isinstance(line, str) and line.strip() for line in test['prompt']):
        raise ValueError('share.json send_test.prompt must be a nonempty list of lines')
    for line in test['prompt'] + list(data['jobs'].values()):
        if prose_errors(line):
            raise ValueError('share.json text ' + prose_errors(line)[0])
    rules = dict(data)
    rules['_cta'] = patterns
    rules['_sets'] = {name: frozenset(w.lower() for w in data[name]) for name in LISTS[:4]}
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

def cta_errors(text, rules=None):
    """Each generic share call to action in post copy, as 'id: "matched words"'. Empty means clean."""
    rules = rules_or_default(rules)
    if not isinstance(text, str):
        return []
    text = text.replace('\u2019', "'")
    found = []
    for name, pattern in rules['_cta']:
        match = pattern.search(text)
        if match:
            found.append(name + ': "' + match.group(0).strip() + '"')
    return found


# The share block ----------------------------------------------------------

def _content(text, rules):
    return [w for w in _words(text) if w not in rules['_sets']['filler_words']]


def person_errors(text, field, rules=None):
    """A sender or receiver names one specific person by role or relationship, never a crowd."""
    rules = rules_or_default(rules)
    if not isinstance(text, str) or not text.strip():
        return [field + ' must name a person']
    words = _words(text)
    crowd = [w for w in words if w in rules['_sets']['crowd_words']]
    if crowd:
        return [field + ' "' + text.strip() + '" is a crowd ("' + crowd[0] + '"); name one specific person']
    content = _content(text, rules)
    if not content or all(w in rules['_sets']['generic_words'] for w in content):
        return [field + ' "' + text.strip() + '" is vague; name the person by role or relationship,'
                ' for example "a head of marketing to her CEO"']
    return []


def _specific_words(text, rules):
    lowered = ' ' + ' '.join(_words(text)) + ' '
    for phrase in rules['_phrases']:
        lowered = lowered.replace(' ' + ' '.join(_words(phrase)) + ' ', ' ')
    return [w for w in lowered.split() if w not in rules['_sets']['filler_words']
            and w not in rules['_sets']['generic_words']]


def dm_line_errors(text, rules=None):
    """The exact words the sender types: short, plain, specific, and never a call to action."""
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
        errors.append('dm_line "' + text.strip() + '" is a generic call to action; say the specific reason'
                      ' this person sends it to that one')
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


# The blind send test ------------------------------------------------------

def send_test_request(package, rules=None):
    """The only thing a fresh reader sees: the prompt, the format, the copy and the exact asset bytes.

    Never the share block, the source, the channel or any production note, so its
    answer cannot echo what the author declared.
    """
    rules = rules_or_default(rules)
    return {'local_only': True, 'blind': True, 'reader_card': rules['send_test']['reader_card'],
            'prompt': '\n'.join(rules['send_test']['prompt']),
            'post': {'format': package['format'], 'copy': package['caption'],
                     'assets': [{'path': a['path'], 'sha256': a['sha256']} for a in package['assets']]}}


def receiver_key(text, rules=None):
    """The words that identify a receiver, aliases folded, so 'her chief executive' meets 'my CEO'.

    Only the role is compared: the description after a comma or a relative
    clause ("who keeps asking...") is context, and matching on it would let a
    shared topic word pass for the same person.
    """
    rules = rules_or_default(rules)
    role = ' ' + (text if isinstance(text, str) else '').lower().replace('\u2019', "'") + ' '
    for mark in rules['receiver_clause_breaks']:
        role = role.split(mark, 1)[0] + ' '
    lowered = ' ' + ' '.join(_words(role)) + ' '
    for other, canon in rules['_alias']:
        lowered = lowered.replace(' ' + ' '.join(_words(other)) + ' ', ' ' + canon + ' ')
    sets = rules['_sets']
    terms = []
    for word in lowered.split():
        if word in sets['filler_words'] or word in sets['generic_words'] or word in sets['crowd_words']:
            continue
        if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
            word = word[:-1]
        terms.append(word)
    core = {w for w in terms if w not in sets['descriptor_words']}
    return core or set(terms)


def compare_send_test(declared, answer, rules=None):
    """Pass when the blind reader's receiver and job match the declared share block; else revise.

    The reader's answer is returned whole so the revision starts from what a
    stranger actually said.
    """
    rules = rules_or_default(rules)
    problems = share_errors(declared, True, rules)
    if problems:
        raise ValueError('declared share block is incomplete: ' + problems[0])
    if not isinstance(answer, dict) or type(answer.get('would_send')) is not bool:
        raise ValueError('the reader answer needs would_send true or false')
    unknown = sorted(set(answer) - set(rules['send_test']['answer_fields']))
    if unknown:
        raise ValueError('the reader answer has unknown fields: ' + ', '.join(unknown))
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
        if not receiver_key(declared['receiver'], rules) & receiver_key(answer['receiver'], rules):
            reasons.append('the reader would send it to "' + answer['receiver'].strip() + '", not to "'
                           + declared['receiver'].strip() + '"')
    return {'local_only': True, 'verdict': 'revise' if reasons else 'pass', 'reasons': reasons,
            'declared': {'receiver': declared['receiver'], 'job': declared['job']}, 'reader_answer': answer}
