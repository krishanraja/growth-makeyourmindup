"""The insight desk's sheet, checked here and turned into this week's mix ideas.

Ruling (Krish, 2026-11-24): the insight desk is the ai-harness `insight-desk` skill with a thin adapter in each
growth engine (config/insight-desk.json). The skill turns the North Star goal into an insight sheet
(`insight-sheet/1`) of up to three tested ideas, before any words are made. This module is the adapter's
deterministic half:

  check     every rule of the sheet's shape, and the rules a shape cannot hold: the stall is the idea or
            measurement; at U4 with nothing measured every idea is a measurement idea; a lead exists only when
            both blind passes picked it and it passed every test, its analogue linked and read; no scores; the
            sheet_sha256 matches the sheet. Standard library only, offline.
  to_ideas  each sheet idea as the mix's own idea shape (idea_id, lane, idea, claim, source_url, source_date,
            plus `source`, the sheet it came from), so `growth.py mix plan --insight <sheet>` lays it out exactly
            like an idea from --ideas. concept_sha256 is computed the same way (engine/concepts.py); the sheet's
            hash rides beside the plan as `insight`, never inside what Krish approves.

Ideas only (docs/ENGINE-BOUNDARY.md): the sheet carries a claim and a mechanic; content-engine keeps the story,
copy, design and rendering. An idea that failed a test on its sheet, or a measurement idea (which is not a post),
is refused with why and never laid out. Sheets live under .scratch/insight/ and are never committed.

The method names are the skill's own. When AI_HARNESS_ROOT names a local ai-harness checkout, a sheet's method
must be one of them; without it the method is only checked for form, and `methods_checked` says so.

Nothing here posts, sends, spends or makes a network call.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = Path('config') / 'insight-desk.json'
SCHEMA = 'insight-sheet/1'
TOP_KEYS = ('schema', 'venture', 'repo', 'harness_skill_sha', 'made_at', 'north_star', 'stall_check', 'insights',
            'chosen_insight', 'discarded_obvious', 'ideas', 'consults', 'lead', 'blind_passes', 'sheet_sha256')
DIAGNOSES = ('idea', 'distribution', 'offer', 'attribution', 'measurement')
LEVELS = ('execution', 'campaign', 'platform', 'business', 'measurement')
TEST_KEYS = ('specificity', 'share', 'analogue', 'floor', 'kill_the_favourite')
RESULTS = ('pass', 'fail', 'unavailable')
CONSULT_RESULTS = ('pass', 'flagged', 'unavailable')
ENGINES = ('divergent-thinker', 'humour-engine')
IDEA_KEYS = ('id', 'claim', 'mechanic', 'idea_level', 'method', 'channel_role', 'conversion_path',
             'kill_condition', 'tests')
INSIGHT_KEYS = ('audience', 'wants', 'but', 'because', 'source', 'read_at', 'assumption')
ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')
REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
SHA1 = re.compile(r'^[0-9a-f]{40}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
METHOD = re.compile(r'^[a-z0-9][a-z0-9-]*$')
SCORE_KEY = re.compile(r'(?i)^(score|scores|rating|points|weight|weighted_total|total)$')
EM_DASH = chr(0x2014)
METHODS_PATHS = (Path('skills') / 'insight-desk' / 'references' / 'methods-by-category.md',
                 Path('candidates') / 'insight-desk' / 'references' / 'methods-by-category.md')


# Reading -------------------------------------------------------------------------------------------------------

def adapter(root=ROOT):
    path = Path(root) / ADAPTER
    with open(path if path.is_file() else ROOT / ADAPTER, encoding='utf-8') as handle:
        return json.load(handle)


def known_methods(harness_root=None):
    """The skill's method names from a local ai-harness checkout, or None when there is none to read."""
    base = harness_root or os.environ.get('AI_HARNESS_ROOT')
    if not base:
        return None
    for rel in METHODS_PATHS:
        path = Path(base) / rel
        if path.is_file():
            return set(re.findall(r'(?m)^### `([a-z0-9-]+)`', path.read_text(encoding='utf-8')))
    return None


def canonical(sheet):
    body = {k: v for k, v in sheet.items() if k != 'sheet_sha256'}
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def sheet_sha(sheet):
    return hashlib.sha256(canonical(sheet)).hexdigest()


def _filled(value):
    return isinstance(value, str) and value.strip() != ''


def _date(value):
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _instant(value):
    if not isinstance(value, str) or 'T' not in value:
        return False
    try:
        dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


# Checking ------------------------------------------------------------------------------------------------------

def _scores(node, where, errors):
    if isinstance(node, dict):
        for key, value in node.items():
            if SCORE_KEY.match(str(key)):
                errors.append(where + '.' + str(key) + ': no scores; the sheet carries results and reasons only')
            _scores(value, where + '.' + str(key), errors)
    elif isinstance(node, list):
        for n, value in enumerate(node):
            _scores(value, where + '[' + str(n) + ']', errors)
    elif isinstance(node, str) and EM_DASH in node:
        errors.append(where + ': carries an em dash')


def _test(label, test, errors, analogue=False):
    if not isinstance(test, dict):
        errors.append(label + ': missing')
        return
    allowed = {'result', 'reason'} | ({'url', 'read_at'} if analogue else set())
    if set(test) - allowed:
        errors.append(label + ': unexpected fields ' + ', '.join(sorted(set(test) - allowed)))
    if test.get('result') not in RESULTS:
        errors.append(label + ': result is pass, fail or unavailable')
    if not _filled(test.get('reason')):
        errors.append(label + ': needs a reason')
    if analogue:
        for key in ('url', 'read_at'):
            if key not in test:
                errors.append(label + ': needs ' + key + ' (null when none was found)')
        if test.get('result') == 'pass':
            if not _filled(test.get('url')):
                errors.append(label + ': a passing analogue is linked')
            if not _date(test.get('read_at')):
                errors.append(label + ': a passing analogue records the date it was read')


def _idea(n, idea, methods, errors):
    label = 'ideas[' + str(n) + ']'
    if not isinstance(idea, dict):
        errors.append(label + ': not an object')
        return
    missing = [k for k in IDEA_KEYS if k not in idea]
    if missing:
        errors.append(label + ': missing ' + ', '.join(missing))
    if set(idea) - set(IDEA_KEYS):
        errors.append(label + ': unexpected fields ' + ', '.join(sorted(set(idea) - set(IDEA_KEYS))))
    if not (isinstance(idea.get('id'), str) and ID.match(idea['id'])):
        errors.append(label + ': id is lower-case letters, digits and hyphens')
    for key in ('claim', 'mechanic', 'channel_role', 'kill_condition'):
        if key in idea and not _filled(idea[key]):
            errors.append(label + ': ' + key + ' is empty')
    if idea.get('idea_level') not in LEVELS:
        errors.append(label + ': idea_level is one of ' + ', '.join(LEVELS))
    method = idea.get('method')
    if not (isinstance(method, str) and METHOD.match(method)):
        errors.append(label + ': method is one of the skill\'s method names')
    elif methods is not None and method not in methods:
        errors.append(label + ': method ' + method + ' is not one of the skill\'s methods')
    path = idea.get('conversion_path')
    if not isinstance(path, dict) or not all(_filled(path.get(k)) for k in ('offer', 'link', 'why_act')):
        errors.append(label + ': an idea with no full conversion path (offer, link, why_act) is held off the sheet')
    elif set(path) - {'offer', 'link', 'why_act'}:
        errors.append(label + ': conversion_path has unexpected fields')
    tests = idea.get('tests')
    if not isinstance(tests, dict):
        errors.append(label + ': tests missing')
        return
    if set(tests) - set(TEST_KEYS):
        errors.append(label + ': unexpected tests ' + ', '.join(sorted(set(tests) - set(TEST_KEYS))))
    for key in TEST_KEYS:
        _test(label + '.tests.' + key, tests.get(key), errors, analogue=key == 'analogue')


def _insight(n, insight, errors):
    label = 'insights[' + str(n) + ']'
    if not isinstance(insight, dict):
        errors.append(label + ': not an object')
        return
    for key in ('audience', 'wants', 'but', 'because'):
        if not _filled(insight.get(key)):
            errors.append(label + ': ' + key + ' is empty')
    if set(insight) - set(INSIGHT_KEYS):
        errors.append(label + ': unexpected fields ' + ', '.join(sorted(set(insight) - set(INSIGHT_KEYS))))
    sourced = 'source' in insight or 'read_at' in insight
    if sourced and 'assumption' in insight:
        errors.append(label + ': a source and read_at, or assumption: true, never both')
    elif 'assumption' in insight:
        if insight['assumption'] is not True:
            errors.append(label + ': assumption is true when present')
    elif not (_filled(insight.get('source')) and _date(insight.get('read_at'))):
        errors.append(label + ': needs a source and the date it was read, or assumption: true')


def check(sheet, methods=None):
    """Every reason the sheet is not a valid insight-sheet/1, or [] when it is."""
    if not isinstance(sheet, dict):
        return ['the sheet is not a JSON object']
    errors = []
    missing = [k for k in TOP_KEYS if k not in sheet]
    if missing:
        errors.append('missing ' + ', '.join(missing))
    if set(sheet) - set(TOP_KEYS):
        errors.append('unexpected fields ' + ', '.join(sorted(set(sheet) - set(TOP_KEYS))))
    if sheet.get('schema') != SCHEMA:
        errors.append('schema is ' + SCHEMA)
    if not _filled(sheet.get('venture')):
        errors.append('venture is empty')
    if not (isinstance(sheet.get('repo'), str) and REPO.match(sheet['repo'])):
        errors.append('repo is owner/name')
    if not (isinstance(sheet.get('harness_skill_sha'), str) and SHA1.match(sheet['harness_skill_sha'])):
        errors.append('harness_skill_sha is the 40-character commit the skill was read at')
    if not _instant(sheet.get('made_at')):
        errors.append('made_at is an ISO date-time')

    ns, urgency, current = sheet.get('north_star'), None, None
    if not isinstance(ns, dict) or set(ns) != {'metric', 'urgency', 'current', 'as_of'}:
        errors.append('north_star has exactly metric, urgency, current and as_of')
    else:
        urgency, current = ns.get('urgency'), ns.get('current')
        if not _filled(ns.get('metric')):
            errors.append('north_star.metric is empty')
        if not (_int(urgency) and 1 <= urgency <= 5):
            errors.append('north_star.urgency is 1 to 5')
        if current is not None and (isinstance(current, bool) or not isinstance(current, (int, float))):
            errors.append('north_star.current is a number or null')
        if ns.get('as_of') is not None and not _date(ns.get('as_of')):
            errors.append('north_star.as_of is a date or null')

    stall, diagnosis = sheet.get('stall_check'), None
    if not isinstance(stall, dict) or set(stall) != {'diagnosis', 'evidence'}:
        errors.append('stall_check has exactly diagnosis and evidence')
    else:
        diagnosis = stall.get('diagnosis')
        if diagnosis not in DIAGNOSES:
            errors.append('stall_check.diagnosis is one of ' + ', '.join(DIAGNOSES))
        elif diagnosis not in ('idea', 'measurement'):
            errors.append('the stall is ' + diagnosis + ', not the idea; the desk stops and makes no sheet')
        if not _filled(stall.get('evidence')):
            errors.append('stall_check.evidence is empty')

    insights = sheet.get('insights')
    if not isinstance(insights, list) or not 1 <= len(insights) <= 3:
        errors.append('insights hold one to three lines')
        insights = insights if isinstance(insights, list) else []
    for n, insight in enumerate(insights):
        _insight(n, insight, errors)
    chosen = sheet.get('chosen_insight')
    if not (_int(chosen) and 0 <= chosen < len(insights)):
        errors.append('chosen_insight points at one of the insights')

    obvious = sheet.get('discarded_obvious')
    if not (isinstance(obvious, list) and len(obvious) == 3 and all(_filled(o) for o in obvious)):
        errors.append('discarded_obvious holds exactly three ideas')
        obvious = []

    ideas = sheet.get('ideas')
    if not isinstance(ideas, list) or not 1 <= len(ideas) <= 3:
        errors.append('ideas hold one to three ideas')
        ideas = ideas if isinstance(ideas, list) else []
    for n, idea in enumerate(ideas):
        _idea(n, idea, methods, errors)
    by_id = {idea.get('id'): idea for idea in ideas if isinstance(idea, dict)}
    if len(by_id) != len(ideas):
        errors.append('idea ids are unique')
    plain = {' '.join(str(o).lower().split()) for o in obvious}
    for idea in by_id.values():
        if ' '.join(str(idea.get('claim', '')).lower().split()) in plain:
            errors.append('idea ' + str(idea.get('id')) + ': restates a discarded obvious idea')
    if diagnosis == 'measurement' or (urgency == 4 and current is None):
        for idea in by_id.values():
            if idea.get('idea_level') != 'measurement':
                errors.append('idea ' + str(idea.get('id')) + ': nothing is measured, so every idea is a measurement idea')

    consults = sheet.get('consults')
    if not isinstance(consults, list):
        errors.append('consults is a list (empty when no engine was called)')
        consults = []
    for n, consult in enumerate(consults):
        label = 'consults[' + str(n) + ']'
        if not isinstance(consult, dict) or set(consult) != {'engine', 'op', 'result', 'ref'}:
            errors.append(label + ': has exactly engine, op, result and ref')
            continue
        if consult['engine'] not in ENGINES:
            errors.append(label + ': engine is one of ' + ', '.join(ENGINES))
        if consult['result'] not in CONSULT_RESULTS:
            errors.append(label + ': result is pass, flagged or unavailable; exit 2 is unavailable, never pass')
        if not _filled(consult['op']) or not _filled(consult['ref']):
            errors.append(label + ': op and ref are filled')

    passes = sheet.get('blind_passes')
    if not isinstance(passes, list) or len(passes) != 2:
        errors.append('blind_passes hold exactly two passes')
        passes = []
    ids = sorted(k for k in by_id if isinstance(k, str))
    for n, blind in enumerate(passes):
        label = 'blind_passes[' + str(n) + ']'
        if not isinstance(blind, dict) or set(blind) != {'reader', 'order', 'lead'}:
            errors.append(label + ': has exactly reader, order and lead')
            continue
        if not _filled(blind['reader']):
            errors.append(label + ': names the reader')
        if not isinstance(blind['order'], list) or sorted(map(str, blind['order'])) != ids:
            errors.append(label + ': order lists every idea id once')
        if blind['lead'] is not None and blind['lead'] not in by_id:
            errors.append(label + ': lead is not an idea on the sheet')
    if len(passes) == 2 and all(isinstance(p, dict) for p in passes):
        if len(ids) > 1 and passes[0].get('order') == passes[1].get('order'):
            errors.append('blind_passes: the two orders are shuffled differently')
        if any(p.get('reader') in ('writer', 'author') for p in passes):
            errors.append('blind_passes: the reader is never the writer of the ideas')

    lead = sheet.get('lead')
    if lead is not None:
        if lead not in by_id:
            errors.append('lead is not an idea on the sheet')
        else:
            if not passes or any(isinstance(p, dict) and p.get('lead') != lead for p in passes):
                errors.append('lead: both blind passes pick the same lead, otherwise lead is null')
            tests = by_id[lead].get('tests') or {}
            for key in TEST_KEYS:
                result = (tests.get(key) or {}).get('result')
                if result != 'pass':
                    errors.append('lead ' + lead + ': ' + key + ' is ' + str(result)
                                  + '; an idea leads only when every test passed')

    _scores(sheet, 'sheet', errors)
    claimed = sheet.get('sheet_sha256')
    if not (isinstance(claimed, str) and SHA256.match(claimed)):
        errors.append('sheet_sha256 is 64 lower-case hex characters')
    elif claimed != sheet_sha(sheet):
        errors.append('sheet_sha256 does not match the sheet; recompute it with --print-sha')
    return errors


# Into the mix --------------------------------------------------------------------------------------------------

def to_ideas(sheet, lane, lanes, taken=()):
    """(ideas, refused, record): each sheet idea as the mix's idea shape for `lane`, the ones refused with why, and
    the provenance the plan carries beside it. The sheet must already pass check()."""
    if lane not in lanes:
        raise ValueError('lane ' + str(lane) + ' takes no ideas; one of ' + ', '.join(sorted(lanes)))
    taken = set(taken)
    ideas, refused = [], []
    source = 'insight-sheet:' + sheet['sheet_sha256']
    for idea in sheet['ideas']:
        failed = [k for k in TEST_KEYS if idea['tests'][k]['result'] == 'fail']
        why = None
        if idea['idea_level'] == 'measurement':
            why = 'a measurement idea is not a post; the Measurement engine takes it'
        elif failed:
            why = 'failed on its sheet: ' + ', '.join(failed)
        elif idea['id'] in taken:
            why = 'an idea with this idea_id is already in --ideas'
        if why:
            refused.append({'idea_id': idea['id'], 'lane': lane, 'why': why})
            continue
        ideas.append({'idea_id': idea['id'], 'lane': lane, 'idea': idea['mechanic'].strip(),
                      'claim': idea['claim'].strip(), 'source_url': None, 'source_date': None, 'source': source})
    record = {'schema': SCHEMA, 'sheet_sha256': sheet['sheet_sha256'],
              'harness_skill_sha': sheet['harness_skill_sha'], 'lane': lane, 'lead': sheet['lead'],
              'ideas': [i['idea_id'] for i in ideas], 'refused': refused}
    return ideas, refused, record


def load(path, methods=None):
    """The sheet at path, or ValueError naming every reason it is not valid."""
    with open(path, encoding='utf-8-sig') as handle:
        sheet = json.load(handle)
    errors = check(sheet, methods)
    if errors:
        raise ValueError('the insight sheet is not valid:\n  ' + '\n  '.join(errors))
    return sheet


# Command line --------------------------------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog='python3 -m engine.insight_sheet',
                                     description='Check an insight sheet (insight-sheet/1). Reads only.')
    parser.add_argument('sheet')
    parser.add_argument('--print-sha', action='store_true', help='print the sheet_sha256 the sheet should carry')
    args = parser.parse_args(argv)
    try:
        with open(args.sheet, encoding='utf-8-sig') as handle:
            sheet = json.load(handle)
    except (OSError, ValueError) as error:
        print('cannot read the sheet: ' + str(error), file=sys.stderr)
        return 2
    if args.print_sha:
        print(sheet_sha(sheet) if isinstance(sheet, dict) else '')
        return 0
    methods = known_methods()
    errors = check(sheet, methods)
    if errors:
        for error in errors:
            print('INVALID  ' + error)
        return 1
    print('VALID ' + SCHEMA + ': ' + str(len(sheet['ideas'])) + ' idea(s), lead ' + str(sheet['lead'] or 'none')
          + ('' if methods is not None else ' (methods checked for form only: set AI_HARNESS_ROOT to check names)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
