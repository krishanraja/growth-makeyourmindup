"""The humour engine, on call: does a joke land, how, and at whose expense.

Krish, 2026-11-17: humour-engine (krishanraja/humour-engine) is the fleet's
one definition and understanding of humour, and each engine keeps its own
stylistic preferences. Asked how this engine should use it, he said "go ahead
on both, makeyourmindup first".

It reads, it never writes taste. The taste is the house register
(content-corpus `references/editorial-channels.md`) and ai-harness
`krish-voice` references/humour.md, which put Make Your Mind Up at
"Integrated" and anything sold under the Mindmake name at "Never". This file
turns the engine's reading into three of those rules a machine can hold:

  at_person          a comment on someone else's post jokes at a person (the
                     poster or another commenter). humour.md comment rule 3:
                     "the joke is never at the person's expense, more the
                     inanimate topic".
  mindmake_humour    a piece that sells, announces or links to Mindmake reads
                     as a joke (humour.md: Mindmake is "Never").
  needs_explaining   the joke leans on more than one outside reference, or on
                     context the reader does not have, so a stranger scrolling
                     past cannot share it (the North Star counts shares).

And one note, never a rule: a line that tries to be funny and does not land
(a "forced joke", which docs/ENGAGEMENT-LOOP.md bans in comments).

It runs through this engine's own Control Center client and bearer
(POST /api/growth/engines/makeyourmindup/humour, capped at 200 calls a day),
and needs the humour-engine package for the prompt and the validators
(`pip install -r requirements-humour.txt && pip install --no-deps -r
requirements-humour-engine.txt`). Without either it says
unavailable, and unavailable is never a pass.
"""

import hashlib
import os

from engine.control_center import SLUG, ProtocolError

SURFACES = {
    'caption': "Format: the caption under one of the publication's social posts",
    'comment': "Format: a public comment by the publication's account under another account's post",
    'onscreen': 'Format: words on screen in a short vertical video or a carousel card',
    'note': 'Format: a Substack Note from the publication',
    'line': 'Format: a single line of social copy',
}
AUDIENCE = 'People who follow AI news on social media: operators, builders and curious professionals'
HUMOUR_TIMEOUT = 150  # a comprehension call takes longer than the protocol's 20 s
EXIT = {'pass': 0, 'flagged': 1, 'unavailable': 2}


def words_sha(lines):
    return hashlib.sha256('\n'.join(lines).encode('utf-8')).hexdigest()[:16]


def request(lines, surface='line', context=(), request_id='mymu:check'):
    """The humour-engine AnalysisRequest for these lines: one segment a line, one model call."""
    segs = [{'segment_id': 'l%d' % n, 'text': w, 'sequence': n} for n, w in enumerate(lines, 1)]
    facts = [SURFACES.get(surface, SURFACES['line'])] + [str(c)[:500] for c in context][:5]
    return {
        'request_id': request_id,
        'focus_segment_ids': [s['segment_id'] for s in segs],
        'segments': segs,
        'context': {'provided_facts': facts, 'audience_description': AUDIENCE},
        'tasks': ['comprehension'],
        'provider_policy': {'allowed_provider_ids': ['controlcenter'], 'allow_external_inference': True},
        'budget': {'max_model_calls': 1, 'max_input_tokens': 9000, 'max_output_tokens': 2000},
    }


def transport_for(cc):
    """Adapt this engine's Client to humour-engine's ControlCenterProvider transport: (url, body) -> (status, json).
    The client's own origin lock, bearer and error codes apply; the provider's URL is ignored."""
    def transport(_url, body):
        try:
            return 200, cc.humour(body)
        except ProtocolError as e:
            return e.status or 503, {'ok': False, 'error': e.server_code or e.code}
    return transport


def reader(cc):
    """A function lines -> analysis dict, or None when the package is not installed or there is no client."""
    if cc is None or not hasattr(cc, 'humour'):
        return None
    try:
        import json
        from humour_engine.analysis.core import EngineDeps, analyse
        from humour_engine.contracts.analysis import AnalysisRequest
        from humour_engine.models.providers import ControlCenterProvider
    except ImportError:
        return None
    # The provider builds its URL from the engine slug; the transport ignores that URL and uses this engine's client.
    os.environ.setdefault(ControlCenterProvider.ENGINE_ENV, SLUG)
    deps = EngineDeps(providers={'controlcenter': ControlCenterProvider(transport=transport_for(cc))},
                      max_calls_per_request=1)

    def read(req):
        return json.loads(analyse(AnalysisRequest.model_validate(req), deps).model_dump_json())
    return read


def _main(result):
    main = [i for i in result.get('interpretations', []) if i.get('supported_reading')]
    return next((i for i in main if i.get('is_main')), main[0]) if main else None


def findings(result, surface='line', mindmake=False):
    """(rules broken, notes, labels) from one analysis. Rules hold a draft; notes inform it."""
    rules, notes, labels = [], [], {}
    reading = result.get('comic_reading')
    i = _main(result)
    if i:
        labels = {k: v for k, v in (i.get('labels_by_axis') or {}).items() if v}
        target = (i.get('target_and_subject') or {}).get('target')
        if target:
            labels['target'] = [target]
    attempted = (result.get('humour_attempt') or {}).get('status') in ('reported', 'supported_inference')
    if reading == 'supported':
        target = (labels.get('target') or [None])[0]
        if surface == 'comment' and target in ('other_person',):
            rules.append('at_person: the joke is at a person; on someone else\'s post it targets the topic or the '
                         'object, never the poster or a commenter (humour.md comment rule 3)')
        if mindmake:
            rules.append('mindmake_humour: this names Mindmake, and humour on Mindmake is "Never" (humour.md)')
        jumps = [d for d in result.get('context_dependencies', [])
                 if d.get('required') and d.get('source_kind') in ('cultural', 'topical')]
        if len(jumps) > 1 or result.get('missing_context'):
            rules.append('needs_explaining: it leans on more than one outside reference, so a stranger cannot share it')
    elif reading == 'insufficient_context' and attempted:
        rules.append('needs_explaining: the engine cannot read the joke without context the reader is not given')
    elif reading in ('ambiguous', 'not_supported') and attempted:
        notes.append('forced: it reads as an attempt at a joke that does not land; cut the joke or rewrite it '
                     '(docs/ENGAGEMENT-LOOP.md bans a forced joke in comments)')
    return rules, notes, labels


def consult(lines, surface='line', context=(), mindmake=False, read=None):
    """One read. status: pass, flagged or unavailable. Unavailable is never a pass."""
    lines = [w.strip() for w in lines if w and w.strip()]
    out = {'surface': surface, 'lines': len(lines), 'words_sha': words_sha(lines), 'mindmake': bool(mindmake)}
    if read is None:
        out.update(status='unavailable', reason='humour engine not reachable: run `python growth.py humour doctor`')
        return out
    try:
        result = read(request(lines, surface, context))
    except Exception as e:  # noqa: BLE001  a provider or contract failure is never a pass
        out.update(status='unavailable', reason='humour engine failed: ' + type(e).__name__)
        return out
    reading = result.get('comic_reading')
    if reading is None:
        codes = [e.get('code') for e in result.get('errors', []) if isinstance(e, dict)]
        out.update(status='unavailable', reason='no reading: ' + (', '.join(c for c in codes if c) or 'the engine abstained'))
        return out
    rules, notes, labels = findings(result, surface, mindmake)
    out.update(reading=reading, rules=rules, notes=notes, labels=labels,
               status='flagged' if rules or notes else 'pass')
    return out


def render(o, label=None):
    head = (label + ': ') if label else ''
    rows = ['%s%s  (%s, %d line(s), %s%s)' % (head, o['status'].upper(), o['surface'], o['lines'], o['words_sha'],
                                             ', names Mindmake' if o.get('mindmake') else '')]
    if o.get('reason'):
        rows.append('  ' + o['reason'])
    if o.get('reading'):
        rows.append('  reading: ' + o['reading'])
    for k in ('mechanism', 'rhetorical_mode', 'target'):
        if o.get('labels', {}).get(k):
            rows.append('  %s: %s' % (k, ', '.join(o['labels'][k])))
    rows += ['  - ' + r for r in o.get('rules', [])] + ['  - note: ' + n for n in o.get('notes', [])]
    return '\n'.join(rows)


def differences(a, b):
    """What the engine sees differently in two versions. Never a pick: that is taste, and taste is Krish's."""
    diffs = []
    for key in ('status', 'reading'):
        if a.get(key) != b.get(key):
            diffs.append('%s: A %s, B %s' % (key, a.get(key), b.get(key)))
    for k in ('mechanism', 'rhetorical_mode', 'target'):
        x, y = set(a.get('labels', {}).get(k, [])), set(b.get('labels', {}).get(k, []))
        if x != y:
            diffs.append('%s: only A %s, only B %s' % (k, sorted(x - y) or '-', sorted(y - x) or '-'))
    for key in ('rules', 'notes'):
        if a.get(key, []) != b.get(key, []):
            diffs.append('%s: A %d, B %d' % (key, len(a.get(key, [])), len(b.get(key, []))))
    return diffs


def doctor(cc, package=None):
    """(ok, lines). Checks the client, the package and that Control Center serves the route. No model call;
    never prints the token."""
    lines, ok = [], True
    if cc is None:
        ok = False
        lines.append('token: NOT READY. No gen1_ engine token here; the GitHub runner has it (docs/KEY.md)')
    else:
        lines.append('token: the engine token is set')
    if package is None:
        try:
            import humour_engine  # noqa: F401
            package = True
        except ImportError:
            package = False
    if package:
        lines.append('package: humour-engine installed')
    else:
        ok = False
        lines.append('package: NOT INSTALLED. pip install -r requirements-humour.txt && '
                     'pip install --no-deps -r requirements-humour-engine.txt')
    if cc is not None:
        try:
            features = (cc.capabilities() or {}).get('features') or {}
            if features.get('humour'):
                lines.append('route: Control Center serves the humour route to this engine')
            else:
                ok = False
                lines.append('route: NOT SERVED. Control Center answered, but features.humour is off for this engine')
        except ProtocolError as e:
            ok = False
            lines.append('route: UNREACHABLE (' + e.code + ')')
    lines.append('ready: the humour engine can be consulted' if ok
                 else 'ready: NO. `humour check` will say unavailable, never pass')
    return ok, lines


def command(argv, client_factory):
    import argparse
    import json
    p = argparse.ArgumentParser(prog='growth.py humour', description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='action', required=True)
    for name in ('check', 'compare'):
        x = sub.add_parser(name)
        if name == 'check':
            x.add_argument('lines', nargs='*'); x.add_argument('--file'); x.add_argument('--json', action='store_true')
        else:
            x.add_argument('a'); x.add_argument('b')
        x.add_argument('--surface', choices=sorted(SURFACES), default='line')
        x.add_argument('--context', action='append', default=[])
        x.add_argument('--mindmake', action='store_true', help='the piece sells, announces or links to Mindmake')
    sub.add_parser('doctor')
    a = p.parse_args(argv)

    def client():
        try:
            return client_factory()
        except ValueError:
            return None
    if a.action == 'doctor':
        ok, rows = doctor(client())
        print('\n'.join(rows))
        return 0 if ok else 2

    def lines_of(path):
        with open(path, encoding='utf-8-sig') as f:
            return [line.strip() for line in f if line.strip()]
    read = reader(client())
    if a.action == 'check':
        lines = list(a.lines) + (lines_of(a.file) if a.file else [])
        if not lines:
            p.error('give the line(s) as arguments or with --file')
        o = consult(lines, a.surface, a.context, a.mindmake, read)
        print(json.dumps(o, ensure_ascii=False, indent=2) if a.json else render(o))
        return EXIT[o['status']]
    ca = consult(lines_of(a.a), a.surface, a.context, a.mindmake, read)
    cb = consult(lines_of(a.b), a.surface, a.context, a.mindmake, read)
    print(render(ca, 'A')); print(render(cb, 'B'))
    d = differences(ca, cb)
    print('\ndifferences:\n' + ('\n'.join('  - ' + x for x in d) if d else
                                '  none the engine can see. The choice is taste: ask Krish.'))
    return max(EXIT[ca['status']], EXIT[cb['status']])
