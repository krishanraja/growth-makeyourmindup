"""The copy lint: content-engine's deterministic check on every public word.

Krish, 2026-10-28: "don't add stupid eyebrow text and asterisks and "generated
by AI" and "Krish's take" verbal diahorrea like you tend to. This needs to feel
like a world class media channel".

content-engine owns the patterns (config/copy-lint.json there). This engine
runs a pinned copy, vendor/content-engine/copy-lint/copy-lint.json, read the
same way content-engine's scripts/post-pack/copy_lint.py reads it: flags i and
m only, ASCII word rules, odd spaces and line ends normalised first. Where it
came from and how to update it: vendor/content-engine/copy-lint/SOURCE.md.

Offline only: no model, no network, no secrets. A config that cannot be read
raises ValueError, so a caller refuses rather than letting copy through
unchecked.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'vendor' / 'content-engine' / 'copy-lint' / 'copy-lint.json'
SURFACES = ('channel_copy', 'carousel_text', 'video_onscreen', 'titles', 'article_metadata')
_FLAGS = {'i': re.IGNORECASE, 'm': re.MULTILINE}
_SPACES = re.compile('[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]')
_cache = {}


def load(path=CONFIG):
    """(version, [(id, compiled regex, surfaces)]) from the vendored config, read once."""
    path = Path(path)
    key = str(path)
    if key not in _cache:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ValueError('copy lint config unreadable: ' + str(exc))
        if not isinstance(data, dict) or not isinstance(data.get('version'), str) \
                or not isinstance(data.get('patterns'), list) or not data['patterns']:
            raise ValueError('copy lint config needs a version and a nonempty patterns list')
        out = []
        for p in data['patterns']:
            if not isinstance(p, dict) or not all(isinstance(p.get(k), str) and p[k] for k in ('id', 'regex')):
                raise ValueError('copy lint pattern needs an id and a regex')
            flags = 0
            for f in p.get('flags', ''):
                if f not in _FLAGS:
                    raise ValueError('copy lint pattern ' + p['id'] + ': flag ' + repr(f) + ' is not i or m')
                flags |= _FLAGS[f]
            surfaces = p.get('applies_to')
            if not isinstance(surfaces, list) or not surfaces or any(s not in SURFACES for s in surfaces):
                raise ValueError('copy lint pattern ' + p['id'] + ': applies_to must name known surfaces')
            try:
                rx = re.compile(p['regex'], flags | re.ASCII)
            except re.error as exc:
                raise ValueError('copy lint pattern ' + p['id'] + ' does not compile: ' + str(exc))
            out.append((p['id'], rx, tuple(surfaces)))
        _cache[key] = (data['version'], out)
    return _cache[key]


def version(path=CONFIG):
    return load(path)[0]


def normalise(text):
    """Line ends as \\n and every odd space as a plain one, as content-engine reads them."""
    return _SPACES.sub(' ', text.replace('\r\n', '\n').replace('\r', '\n'))


def copy_lint(text, applies_to, path=CONFIG):
    """Every hit in one piece of public copy, in order: [{'id', 'match', 'index', 'line'}]."""
    if applies_to not in SURFACES:
        raise ValueError('applies_to must be one of ' + ', '.join(SURFACES) + ', not ' + repr(applies_to))
    text = normalise(text or '')
    hits = []
    for pid, rx, surfaces in load(path)[1]:
        if applies_to not in surfaces:
            continue
        for m in rx.finditer(text):
            if m.group(0):
                hits.append({'id': pid, 'match': m.group(0), 'index': m.start(),
                             'line': text.count('\n', 0, m.start()) + 1})
    hits.sort(key=lambda h: (h['index'], h['id']))
    return hits


def copy_lint_errors(text, applies_to='channel_copy', path=CONFIG):
    """One line per hit, for refusals and lint findings."""
    return ['copy lint ' + h['id'] + ': ' + json.dumps(h['match'], ensure_ascii=False)
            for h in copy_lint(text, applies_to, path)]
