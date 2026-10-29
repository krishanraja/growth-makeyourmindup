"""Art direction: one visual idea per piece, built by Codex as a piece kit and gated by the renderer's checks.

Rulings (Krish, 29 Oct 2026): the code renderer in render/ produces every post;
Codex art-directs ONE visual idea per piece as a piece kit; Canva is reference
only. "The most stunning visual art direction I've seen thus far comes from the
AI Passports post ... we need to find a way of combining strengths." The
passports motif itself is never templatised: each piece gets its own idea.

A piece kit is render/pieces/<piece_id>/ (render/KIT.md, "Piece kits"):
templates/*.html, piece.css (kit tokens only), templates.json (the shape of
render/templates.json, kind piece_kit) and idea.md (one plain paragraph).

    growth.py run artdirect [make] [--week-of D] [--pieces F | --mix F | --inventory F] [--max-pieces 3]
    growth.py run artdirect gate          (after the renderer has rendered each kit)
    growth.py run artdirect check DIR...  (the static checks on kits already made)

`make` runs Codex once per piece, up to --max-pieces (the spend cap), with no
network, in the piece's own folder, then runs the static checks; a kit that
fails is removed and the piece falls back to the house kit (piece_kit_refused).
The engine never runs the renderer (Node is not part of the engine): the
workflow renders each surviving kit twice between `make` and `gate`, and `gate`
holds the renderer's own report to the kit's colours, fonts and sizes.

Nothing here posts, schedules, sends or spends beyond the capped Codex runs.
What it prints is counts and codes only: this repository is public.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from ..copy_lint import copy_lint_errors
from ..core import instant, ny_time, read_json, write_json
from ..packs import prose_errors
from .plain import lint_text

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / 'render'
PIECES = RENDER / 'pieces'
PROMPT = RENDER / 'ARTDIRECT_PROMPT.md'
OUT = Path('.scratch') / 'artdirect'
MAX_PIECES = 3
CODEX_TIMEOUT = 1800

KIT_FONTS = ('Anton', 'Fraunces', 'Archivo', 'IBM Plex Mono')
GENERIC_FONTS = ('serif', 'sans-serif', 'monospace')
COLOUR_TOKENS = ('--ink', '--ink-deep', '--cream', '--green', '--mint', '--butter', '--coral', '--lilac')
FONT_TOKENS = ('--heading', '--sub', '--body', '--mono')
PIECE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{1,63}$')
TEMPLATE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
PLACEHOLDER = re.compile(r'\{\{(?:(rows|options):)?([a-z0-9_]+)\}\}')
SPEC_REQUIRED = ('file', 'width', 'height', 'fields', 'required', 'example')
SPEC_OPTIONAL = ('choices', 'note', 'safe')
FIELD_TYPES = ('text', 'rows', 'options')
SAFE_VERTICAL = {'top': 250, 'bottom': 340}
MAX_TEMPLATES = 8
MAX_FILE_BYTES = 64 * 1024
KIT_CSS_LINK = '<link rel="stylesheet" href="../../../kit.css">'
PIECE_CSS_LINK = '<link rel="stylesheet" href="../piece.css">'
FIT_SCRIPT = '<script src="../../../fit.js"></script>'
WORDMARK = ('<div class="wordmark"><span class="mark"><i></i><i></i><i></i></span>'
            '<span class="words">MAKE YOUR MIND/</span><span class="up">UP</span></div>')
EM_DASH = '—'
# Anything that could reach past render/: a scheme, a protocol-relative address, url() or @import.
REMOTE = re.compile(r'\b(?:https?|ftp|wss?):|\b(?:data|blob|javascript|file|about|chrome):(?!\s|$)|'
                    r'(?:src|href|srcset|action|poster)\s*=\s*["\']?\s*//|\burl\s*\(|@import', re.I)
FORBIDDEN_TAGS = re.compile(r'<\s*(img|picture|image|svg|canvas|video|audio|iframe|frame|object|embed|source|'
                            r'track|base|form|input|button|select|textarea|meter|progress|mark|portal|math)\b', re.I)
HANDLER = re.compile(r'\son[a-z]+\s*=', re.I)
HEX = re.compile(r'#[0-9A-Fa-f]{3,8}\b')
COLOUR_FUNCTION = re.compile(r'\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix|device-cmyk|'
                             r'light-dark|contrast-color)\s*\(', re.I)
NAMED_COLOURS = frozenset((
    'aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood '
    'cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod '
    'darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon '
    'darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray '
    'dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green '
    'greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon '
    'lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon '
    'lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen '
    'magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue '
    'mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy '
    'oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred '
    'papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown '
    'salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen '
    'steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen '
    'canvas canvastext linktext visitedtext activetext buttonface buttontext buttonborder field fieldtext '
    'highlight highlighttext selecteditem selecteditemtext mark marktext graytext accentcolor accentcolortext').split())
FORBIDDEN_PROPERTIES = ('filter', 'backdrop-filter', 'mix-blend-mode', 'background-blend-mode', 'animation',
                        'animation-name', 'transition')
WORDMARK_PROPERTIES = re.compile(r'^(?:--wm|margin(?:-[a-z]+)?|align-self|justify-self|justify-content|order|'
                                 r'flex(?:-[a-z]+)?|position|top|right|bottom|left|z-index)$')
SECRET = re.compile(r'\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgen1_[A-Za-z0-9_-]{8,}')
NEVER_WORDS = ('passport', 'krish')
CODES = ('piece_kit_refused', 'codex_failed', 'not_attempted_cap', 'kit_exists', 'bad_piece')


# The kit itself ---------------------------------------------------------------

def house_manifest(root=ROOT):
    return read_json(Path(root) / 'render' / 'templates.json')


def kit_colours(root=ROOT):
    return {c.upper() for c in house_manifest(root)['kit']['colours'].values()}


def house_sizes(root=ROOT):
    return {(t['width'], t['height']) for t in house_manifest(root)['templates'].values()}


def _strings(value):
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return [str(value)]


def _rules(css):
    """(selector, [(property, value)]) for each rule; css holds no at-rules once checked."""
    css = re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)
    out = []
    for selector, body in re.findall(r'([^{}]*)\{([^{}]*)\}', css):
        decls = []
        for part in body.split(';'):
            if ':' in part:
                name, value = part.split(':', 1)
                decls.append((name.strip().lower(), value.strip()))
        out.append((' '.join(selector.split()), decls))
    return out


def _declaration_errors(name, value, at):
    """One CSS declaration against the kit: kit colour tokens, kit fonts, no filters, no remote."""
    errors = []
    bare = re.sub(r'(["\']).*?\1', ' ', value)  # quoted strings say nothing about colour
    if HEX.search(bare):
        errors.append(at + ': a hex colour (' + name + '); use a kit token such as var(--ink)')
    if COLOUR_FUNCTION.search(bare):
        errors.append(at + ': a colour function (' + name + '); use a kit token such as var(--ink)')
    for token in re.findall(r'(?<![\w-])[a-z][a-z-]*(?![\w-])', re.sub(r'var\([^)]*\)', ' ', bare.lower())):
        if token in NAMED_COLOURS:
            errors.append(at + ': the named colour ' + token + ' (' + name + ')')
    if name in FORBIDDEN_PROPERTIES:
        errors.append(at + ': ' + name + ' is not allowed in a piece kit')
    if name in COLOUR_TOKENS or name in FONT_TOKENS:
        errors.append(at + ': redefines the kit token ' + name)
    if name == 'font-family':
        for family in [f.strip().strip('\'"') for f in value.split(',')]:
            if not (family in KIT_FONTS or family in GENERIC_FONTS
                    or re.fullmatch(r'var\((?:' + '|'.join(FONT_TOKENS) + r')\)', family)):
                errors.append(at + ': the font ' + family + ' is not a kit font')
    if name == 'font' and not re.search(r'var\((?:' + '|'.join(FONT_TOKENS) + r')\)', value):
        errors.append(at + ': the font shorthand names no kit font token')
    if (name in ('letter-spacing', 'word-spacing') and value.startswith('-')) or (
            name == 'word-break' and 'break-all' in value):
        errors.append(at + ': ' + name + ' runs words together')
    return errors


def css_errors(css, at):
    """A stylesheet, a <style> block or a style="" attribute, held to the house kit's tokens."""
    errors = []
    if re.search(r'@[a-z-]+', re.sub(r'(["\']).*?\1', ' ', css), re.I):
        errors.append(at + ': an at-rule (@font-face, @import, @media and the rest are not allowed)')
    for selector, decls in _rules(css):
        touches_wordmark = re.search(r'\.(?:mark|words|up)(?![\w-])', selector)
        for name, value in decls:
            errors += _declaration_errors(name, value, at)
            if touches_wordmark or (re.search(r'\.wordmark(?![\w-])', selector)
                                    and not WORDMARK_PROPERTIES.match(name)):
                errors.append(at + ': restyles the wordmark (' + selector + ' ' + name + '); only size and place it')
    return errors


def _attributes_css(html):
    return [m.group(2) for m in re.finditer(r'\sstyle\s*=\s*(["\'])(.*?)\1', html, re.S)]


def template_errors(kit_dir, tid, spec, sizes):
    """One template's HTML: the fixed head and script, its size, its fields, no pictures and kit CSS only."""
    at = 'templates/' + tid + '.html'
    path = kit_dir / spec['file']
    html = path.read_text(encoding='utf-8')
    errors = []
    if not html.lstrip().lower().startswith('<!doctype html>'):
        errors.append(at + ': starts with <!doctype html>')
    links = re.findall(r'<link\b[^>]*>', html, re.I)
    if links != [KIT_CSS_LINK, PIECE_CSS_LINK]:
        errors.append(at + ': links exactly ../../../kit.css then ../piece.css, and nothing else')
    scripts = re.findall(r'<script\b[^>]*>.*?</script\s*>', html, re.I | re.S)
    if scripts != [FIT_SCRIPT] or len(re.findall(r'<script\b', html, re.I)) != 1:
        errors.append(at + ': its one script is ../../../fit.js')
    for tag in sorted({m.group(1).lower() for m in FORBIDDEN_TAGS.finditer(html)}):
        errors.append(at + ': a <' + tag + '> (a kit draws with boxes and type; no picture of anyone)')
    if HANDLER.search(html):
        errors.append(at + ': an inline event handler')
    if re.search(r'<meta\b[^>]*http-equiv', html, re.I) or re.search(r'<a\b[^>]*\bhref', html, re.I):
        errors.append(at + ': a refresh or a link')
    if not re.search(r'class\s*=\s*"[^"]*\bframe\b', html):
        errors.append(at + ': has no element with class="frame"')
    w, h = spec['width'], spec['height']
    if '--w: %dpx' % w not in html or '--h: %dpx' % h not in html:
        errors.append(at + ': sets --w: %dpx and --h: %dpx' % (w, h))
    if (w, h) == (1080, 1920) and ('--top: 250px' not in html or '--bottom: 340px' not in html):
        errors.append(at + ': a vertical frame sets --top: 250px and --bottom: 340px')
    used = {}
    for kind, name in PLACEHOLDER.findall(html):
        if used.get(name, kind or 'text') != (kind or 'text'):
            errors.append(at + ': ' + name + ' is used as two kinds')
        used[name] = kind or 'text'
    if used != spec['fields']:
        errors.append(at + ': its placeholders are not exactly the declared fields')
    if 'class="wordmark"' in html and html.count('class="wordmark"') != html.count(WORDMARK):
        errors.append(at + ': the wordmark is not the house markup')
    for block in (re.findall(r'<style\b[^>]*>(.*?)</style\s*>', html, re.I | re.S)):
        errors += css_errors(block, at + ' <style>')
    for block in _attributes_css(html):
        errors += css_errors('x{' + block + '}', at + ' style=""')
    return errors


def spec_errors(tid, spec, sizes):
    at = 'templates.json ' + tid
    if not TEMPLATE_ID.match(tid):
        return [at + ': a template id is lower case, digits and hyphens']
    if not isinstance(spec, dict) or not set(SPEC_REQUIRED) <= set(spec) or not set(spec) <= set(SPEC_REQUIRED
                                                                                                   + SPEC_OPTIONAL):
        return [at + ': has ' + ', '.join(SPEC_REQUIRED) + ' and may have ' + ', '.join(SPEC_OPTIONAL)]
    errors = []
    if spec['file'] != 'templates/' + tid + '.html':
        errors.append(at + ': file is templates/' + tid + '.html')
    if (spec['width'], spec['height']) not in sizes:
        errors.append(at + ': %sx%s is not a house size' % (spec['width'], spec['height']))
    if (spec['width'], spec['height']) == (1080, 1920) and spec.get('safe') != SAFE_VERTICAL:
        errors.append(at + ': a 1080x1920 template keeps the safe zones (top 250, bottom 340)')
    fields = spec['fields']
    if not isinstance(fields, dict) or not fields or any(v not in FIELD_TYPES for v in fields.values()):
        return errors + [at + ': fields map names to text, rows or options']
    required, example = spec['required'], spec['example']
    if not isinstance(required, list) or not set(required) <= set(fields):
        errors.append(at + ': required names declared fields')
    if not isinstance(example, dict) or not set(example) <= set(fields) or not set(required or []) <= set(example):
        return errors + [at + ': the example fills every required field and names only declared ones']
    for name, value in example.items():
        kind = fields[name]
        ok = (isinstance(value, str) if kind == 'text' else
              isinstance(value, list) and 0 < len(value) and all(
                  isinstance(r, list) and len(r) in (2, 3) and all(isinstance(x, str) for x in r) for r in value)
              if kind == 'rows' else
              isinstance(value, list) and 0 < len(value) <= 4 and all(isinstance(x, str) for x in value))
        if not ok:
            errors.append(at + ': the example ' + name + ' is not ' + kind)
    for name, allowed in (spec.get('choices') or {}).items():
        if name not in fields or not isinstance(allowed, list) or not all(isinstance(a, str) for a in allowed):
            errors.append(at + ': choices name a declared field and list words')
        elif example.get(name) not in (None, '') and example[name] not in allowed:
            errors.append(at + ': the example ' + name + ' is not one of its choices')
    for name, value in example.items():
        for text in _strings(value):
            where = at + ' example ' + name
            errors += [where + ': ' + e for e in copy_lint_errors(text, 'carousel_text')]
            errors += [where + ': ' + e for e in prose_errors(text)]
            errors += [where + ': plain ' + f['code'] for f in lint_text(text)]
    return errors


def idea_errors(text):
    errors = []
    body = text.strip()
    if not body:
        return ['idea.md: names the visual idea in one paragraph']
    if '\n\n' in body.replace('\r\n', '\n') or body.startswith('#'):
        errors.append('idea.md: one paragraph, no heading')
    if not 12 <= len(body.split()) <= 160:
        errors.append('idea.md: between 12 and 160 words')
    errors += ['idea.md: plain ' + f['code'] for f in lint_text(body)]
    errors += ['idea.md: ' + e for e in prose_errors(body)]
    errors += ['idea.md: ' + e for e in copy_lint_errors(body, 'channel_copy')]
    return errors


def kit_files(kit_dir):
    return sorted(p for p in Path(kit_dir).rglob('*'))


def kit_errors(kit_dir, root=ROOT, secrets=(), others=None):
    """Every static check on one piece kit; [] when it may be rendered.

    secrets are values that must never appear in a kit (the runner passes its own key).
    others is the folder of piece kits to compare against for reuse (default: its parent)."""
    kit_dir = Path(kit_dir)
    piece_id = kit_dir.name
    if not PIECE_ID.match(piece_id):
        return [piece_id + ': a piece id is lower case, digits and hyphens']
    if not kit_dir.is_dir():
        return [piece_id + ': no kit folder']
    errors = []
    allowed_top = {'idea.md', 'piece.css', 'templates.json', 'templates'}
    texts = {}
    for path in kit_files(kit_dir):
        rel = path.relative_to(kit_dir).as_posix()
        if path.is_symlink():
            errors.append(rel + ': a link; a kit holds plain files only')
            continue
        if path.is_dir():
            if rel != 'templates':
                errors.append(rel + ': a folder a kit does not have')
            continue
        top = rel.split('/')[0]
        if top not in allowed_top or (top == 'templates' and not re.fullmatch(r'templates/[a-z0-9-]+\.html', rel)):
            errors.append(rel + ': a file a kit does not have (only idea.md, piece.css, templates.json, '
                                'templates/*.html)')
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(rel + ': larger than 64 KB')
            continue
        try:
            texts[rel] = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            errors.append(rel + ': not UTF-8 text')
    for name in ('idea.md', 'piece.css', 'templates.json'):
        if name not in texts:
            errors.append(name + ': missing')
    for rel, text in sorted(texts.items()):
        lower = text.lower()
        if EM_DASH in text:
            errors.append(rel + ': an em dash')
        if REMOTE.search(text):
            errors.append(rel + ': a remote address or url(); a kit reaches nothing outside render/')
        for word in NEVER_WORDS:
            if word in lower:
                errors.append(rel + ': names ' + ('the passports idea, which belongs to one piece' if word == 'passport'
                                                  else 'a person; a kit never names anyone'))
        if SECRET.search(text) or any(s and s in text for s in secrets):
            errors.append(rel + ': holds something shaped like a key')
    if 'idea.md' in texts:
        errors += idea_errors(texts['idea.md'])
    if 'piece.css' in texts:
        errors += css_errors(texts['piece.css'], 'piece.css')
    manifest = None
    if 'templates.json' in texts:
        try:
            manifest = json.loads(texts['templates.json'])
        except ValueError:
            errors.append('templates.json: not JSON')
    if manifest is not None:
        if not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'kind', 'piece_id', 'about',
                                                                'templates'}:
            errors.append('templates.json: exactly schema_version, kind, piece_id, about and templates')
        elif (manifest['schema_version'] != 1 or manifest['kind'] != 'piece_kit' or manifest['piece_id'] != piece_id
              or not isinstance(manifest['about'], str)):
            errors.append('templates.json: schema_version 1, kind piece_kit, piece_id ' + piece_id)
        elif not isinstance(manifest['templates'], dict) or not 1 <= len(manifest['templates']) <= MAX_TEMPLATES:
            errors.append('templates.json: one to %d templates' % MAX_TEMPLATES)
        else:
            sizes = house_sizes(root)
            for tid, spec in manifest['templates'].items():
                found = spec_errors(tid, spec, sizes)
                errors += found
                if not found:
                    if spec['file'] not in texts:
                        errors.append(spec['file'] + ': missing')
                    else:
                        errors += template_errors(kit_dir, tid, spec, sizes)
            named = {'templates/' + t + '.html' for t in manifest['templates']}
            on_disk = {rel for rel in texts if rel.startswith('templates/')}
            errors += [rel + ': a template templates.json does not declare' for rel in sorted(on_disk - named)]
    errors += reuse_errors(kit_dir, texts, root, others)
    return errors


def reuse_errors(kit_dir, texts, root=ROOT, others=None):
    """A kit is its piece's own: no template the same as a house template, nor a file the same as another kit's."""
    errors = []
    house = {p.read_text(encoding='utf-8') for p in (Path(root) / 'render' / 'templates').glob('*.html')}
    for rel, text in texts.items():
        if rel.startswith('templates/') and text in house:
            errors.append(rel + ': a copy of a house template')
    folder = Path(others) if others else Path(kit_dir).parent
    for other in sorted(p for p in folder.iterdir() if p.is_dir() and p.resolve() != Path(kit_dir).resolve()) \
            if folder.is_dir() else []:
        for rel, text in texts.items():
            if rel == 'templates.json':
                continue
            twin = other / rel
            if twin.is_file() and twin.read_text(encoding='utf-8', errors='replace') == text:
                errors.append(rel + ': the same as another piece kit (each piece gets its own idea)')
    return errors


def secret_values(environ=None):
    environ = os.environ if environ is None else environ
    return tuple(v for k, v in environ.items() if k in ('OPENAI_API_KEY', 'CODEX_API_KEY') and v and len(v) >= 8)


def words_errors(kit_dir, piece):
    """The piece's own title and claims stay out of this public repository: a kit holds placeholders only."""
    collapse = lambda t: ' '.join(str(t).lower().split())
    texts = ' '.join(collapse(p.read_text(encoding='utf-8', errors='replace'))
                     for p in kit_files(kit_dir) if p.is_file())
    out = []
    for kind, value in [('title', piece.get('title'))] + [('claim', c) for c in piece.get('claims') or []]:
        if isinstance(value, str) and len(value.strip()) >= 12 and collapse(value) in texts:
            out.append('the piece\'s ' + kind + ' is in the kit; examples are placeholders')
    return out


def render_jobs(kit_dir):
    """The renderer's jobs for a kit: each template from its own example."""
    manifest = read_json(Path(kit_dir) / 'templates.json')
    pid = Path(kit_dir).name
    return [{'template': 'piece:' + pid + '/' + tid, 'fields': spec['example'], 'out': tid + '.png'}
            for tid, spec in manifest['templates'].items()]


def painted_errors(kit_dir, results, root=ROOT):
    """The renderer's own report on a kit: every template rendered at its size, in kit colours and fonts only."""
    manifest = read_json(Path(kit_dir) / 'templates.json')
    pid = Path(kit_dir).name
    colours = kit_colours(root)
    by_template = {r.get('template'): r for r in results if isinstance(r, dict)}
    errors = []
    for tid, spec in manifest['templates'].items():
        result = by_template.get('piece:' + pid + '/' + tid)
        if result is None:
            errors.append(tid + ': not rendered')
            continue
        if (result.get('width'), result.get('height')) != (spec['width'], spec['height']):
            errors.append(tid + ': rendered at another size')
        painted = set(result.get('colours') or [])
        fonts = set(result.get('fonts') or [])
        if not painted or not painted <= colours:
            errors.append(tid + ': paints a colour outside the kit (' + ', '.join(sorted(painted - colours)) + ')')
        if not fonts or not fonts <= set(KIT_FONTS):
            errors.append(tid + ': paints a font outside the kit (' + ', '.join(sorted(fonts - set(KIT_FONTS))) + ')')
    return errors


# The week's pieces ------------------------------------------------------------

def coming_monday(now=None):
    day = ny_time(instant(now)).date()
    return day + dt.timedelta(days=(7 - day.weekday()) or 7)


def week_label(week_of):
    year, week = dt.date.fromisoformat(str(week_of)).isocalendar()[:2]
    return '%d-W%02d' % (year, week)


def pieces_from_mix(mix, inventory=None):
    """The week's mix plan (growth.py mix plan) as pieces, in the order their first post is due."""
    titles = {p['piece_id']: p['title'] for p in (inventory or {}).get('pieces') or []}
    first = {}
    for slot in mix.get('slots') or []:
        cid = slot.get('concept_id')
        if cid:
            due = instant(slot['due_at'])
            first[cid] = min(first.get(cid, due), due)
    late = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    concepts = sorted(mix.get('concepts') or [], key=lambda c: (first.get(c['concept_id'], late), c['concept_id']))
    return [{'piece_id': c['concept_id'], 'title': titles.get(c.get('piece_id')) or c['idea'],
             'claims': [c['claim']] if c.get('claim') else [], 'lane': c['lane']} for c in concepts]


def week_pieces(week_of, inventory=None, root=ROOT):
    """The coming week's pieces from the engine's own reader: the backlog inventory laid out by the mix plan."""
    from .. import backlog, intensity, mix as mix_rules
    if inventory is None:
        inventory, reason = backlog.for_runner(root)
        if inventory is None:
            raise ValueError(reason)
    mix = mix_rules.plan(inventory, str(week_of), root=root, urgency=intensity.state(root)['urgency'])
    return pieces_from_mix(mix, inventory)


def piece_errors(piece):
    if not isinstance(piece, dict):
        return 'a piece is an object'
    if not isinstance(piece.get('piece_id'), str) or not PIECE_ID.match(piece['piece_id']):
        return 'piece_id is lower case, digits and hyphens'
    if not isinstance(piece.get('title'), str) or not piece['title'].strip():
        return 'a piece has a title'
    if not isinstance(piece.get('claims', []), list) or not all(isinstance(c, str) for c in piece.get('claims', [])):
        return 'claims is a list of strings'
    if not isinstance(piece.get('lane'), str) or not piece['lane'].strip():
        return 'a piece has a lane'
    return None


# Codex ------------------------------------------------------------------------

def build_prompt(piece, template=None):
    text = template if template is not None else PROMPT.read_text(encoding='utf-8')
    claims = '\n'.join('  - ' + ' '.join(c.split()) for c in piece.get('claims') or []) or '  - (none given)'
    values = {'piece_id': piece['piece_id'], 'lane': piece['lane'], 'title': ' '.join(piece['title'].split()),
              'claims': claims}
    return re.sub(r'\{\{(piece_id|lane|title|claims)\}\}', lambda m: values[m.group(1)], text)


def codex_command(kit_dir, codex='codex'):
    """codex exec in the piece's own folder, writing only there, with no network and no inherited secrets."""
    return [codex, 'exec', '--json', '--skip-git-repo-check', '-s', 'workspace-write', '-C', str(kit_dir),
            '-c', 'sandbox_workspace_write.network_access=false',
            '-c', 'shell_environment_policy.inherit="core"', '-']


def codex_env(environ=None):
    environ = os.environ if environ is None else environ
    keep = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', 'CODEX_HOME', 'OPENAI_API_KEY', 'SYSTEMROOT', 'USERPROFILE',
            'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP')
    return {k: v for k, v in environ.items() if k in keep}


def run_codex(cmd, prompt, cwd, env):
    """(exit code, stdout): the default runner. Codex's own words never reach the log."""
    try:
        done = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=str(cwd), env=env,
                              timeout=CODEX_TIMEOUT)
        return done.returncode, done.stdout
    except FileNotFoundError:
        return 127, ''
    except subprocess.TimeoutExpired:
        return 124, ''


def token_usage(stdout):
    """Codex's token counts from its JSON events: each turn.completed carries the turn's usage."""
    total = {'input_tokens': 0, 'cached_input_tokens': 0, 'output_tokens': 0, 'reasoning_output_tokens': 0}
    failed = False
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        if kind == 'turn.failed':
            failed = True
        usage = event.get('usage') if kind == 'turn.completed' else None
        if isinstance(usage, dict):
            for key in total:
                if isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool):
                    total[key] += usage[key]
    return total, failed


def git_paths(root=ROOT):
    """Paths git sees as changed or new, for proving Codex wrote only in its own folder."""
    try:
        done = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=str(root),
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode:
        return None
    return {line[3:].strip().strip('"').split(' -> ')[-1] for line in done.stdout.splitlines() if line.strip()}


# The run ----------------------------------------------------------------------

def _remove(kit_dir):
    shutil.rmtree(str(kit_dir), ignore_errors=True)


def make(pieces, week_of, out_dir=OUT, runner=run_codex, max_pieces=MAX_PIECES, pieces_dir=PIECES, root=ROOT,
         prompt=None, codex='codex', changes=git_paths, environ=None):
    """Codex once per piece up to the cap, then the static checks. Returns the summary (also written to out_dir)."""
    out_dir, pieces_dir = Path(out_dir), Path(pieces_dir)
    template = prompt if prompt is not None else PROMPT.read_text(encoding='utf-8')
    secrets = secret_values(environ)
    env = codex_env(environ)
    usage = {'input_tokens': 0, 'cached_input_tokens': 0, 'output_tokens': 0, 'reasoning_output_tokens': 0}
    rows, attempted = [], 0
    (out_dir / 'jobs').mkdir(parents=True, exist_ok=True)
    for piece in pieces:
        bad = piece_errors(piece)
        if bad:
            rows.append({'piece_id': piece.get('piece_id') if isinstance(piece, dict) else None, 'kit': 'house',
                         'code': 'bad_piece', 'reasons': [bad]})
            continue
        pid = piece['piece_id']
        kit_dir = pieces_dir / pid
        if kit_dir.exists():
            rows.append({'piece_id': pid, 'kit': 'existing', 'code': 'kit_exists', 'reasons': []})
            continue
        if attempted >= max_pieces:
            rows.append({'piece_id': pid, 'kit': 'house', 'code': 'not_attempted_cap', 'reasons': []})
            continue
        attempted += 1
        before = changes(root) if changes else None
        kit_dir.mkdir(parents=True)
        code, stdout = runner(codex_command(kit_dir, codex), build_prompt(piece, template), root, env)
        turn, failed = token_usage(stdout)
        for key in usage:
            usage[key] += turn[key]
        after = changes(root) if changes else None
        mine = pieces_dir.resolve()
        outside = []
        if before is not None and after is not None:
            for rel in sorted(after - before):
                full = (Path(root) / rel).resolve()
                if not (str(full).startswith(str(kit_dir.resolve()) + os.sep) or str(full).startswith(
                        str(out_dir.resolve()) + os.sep)):
                    outside.append(rel)
        if code != 0 or failed:
            _remove(kit_dir)
            rows.append({'piece_id': pid, 'kit': 'house', 'code': 'codex_failed',
                         'reasons': ['codex exit %d' % code if code else 'codex reported a failed turn']
                         + (['wrote outside its folder'] if outside else [])})
            continue
        errors = (['wrote outside its folder'] if outside else []) + kit_errors(kit_dir, root, secrets, mine) \
            + words_errors(kit_dir, piece)
        if errors:
            _remove(kit_dir)
            rows.append({'piece_id': pid, 'kit': 'house', 'code': 'piece_kit_refused',
                         'reasons': [e[:200] for e in errors[:40]]})
            continue
        write_json(out_dir / 'jobs' / (pid + '.json'), render_jobs(kit_dir))
        rows.append({'piece_id': pid, 'kit': 'awaiting_render', 'code': None, 'reasons': []})
    summary = {'schema': 'growth-artdirect/1', 'week_of': str(week_of), 'week': week_label(week_of),
               'max_pieces': max_pieces, 'codex_runs': attempted, 'codex_tokens': usage, 'pieces': rows,
               'local_only': True, 'external_writes': 0}
    write_json(out_dir / 'summary.json', summary)
    return summary


def gate(out_dir=OUT, pieces_dir=PIECES, root=ROOT):
    """Hold each kit that passed the static checks to the renderer's own report; refuse the rest."""
    out_dir, pieces_dir = Path(out_dir), Path(pieces_dir)
    summary = read_json(out_dir / 'summary.json')
    for row in summary['pieces']:
        if row['kit'] != 'awaiting_render':
            continue
        kit_dir = pieces_dir / row['piece_id']
        report = out_dir / 'rendered' / (row['piece_id'] + '.json')
        try:
            results = read_json(report)
            errors = painted_errors(kit_dir, results, root) if isinstance(results, list) else ['no render report']
        except (OSError, ValueError):
            errors = ['the renderer refused it or did not render it twice the same']
        if errors:
            _remove(kit_dir)
            row.update(kit='house', code='piece_kit_refused', reasons=[e[:200] for e in errors[:40]])
        else:
            row.update(kit='piece', code=None)
    summary['gated'] = True
    write_json(out_dir / 'summary.json', summary)
    passed = [r['piece_id'] for r in summary['pieces'] if r['kit'] == 'piece']
    (out_dir / 'passed.txt').write_text(''.join(p + '\n' for p in passed), encoding='utf-8')
    (out_dir / 'pr.md').write_text(pr_body(summary), encoding='utf-8')
    return summary


def pr_body(summary):
    """The pull request's words: counts and codes only, and what his review binds."""
    lines = summary_lines(summary)
    return '\n\n'.join([
        'Art direction for week ' + summary['week'] + ': one visual idea per piece, built by Codex as a piece kit'
        ' (render/KIT.md, "Piece kits").',
        lines[0] + '.', lines[1] + '.',
        'Every kit here passed the static checks (`python growth.py run artdirect check render/pieces/<piece_id>`),'
        ' rendered the same bytes twice, and painted only kit colours and fonts. A piece whose kit failed was'
        ' removed and goes out in the house kit (piece_kit_refused).',
        'Read each kit\'s idea.md and render its templates to look at them. This workflow never merges.'
        ' Approving a concept binds the exact mock hashes rendered from these templates.']) + '\n'


def counts(summary):
    out = {}
    for row in summary['pieces']:
        key = row['code'] or ('piece_kit' if row['kit'] == 'piece' else row['kit'])
        out[key] = out.get(key, 0) + 1
    return out


def summary_lines(summary):
    """Counts and codes only: no titles, ids, words or reasons (this repository and its logs are public)."""
    c = counts(summary)
    t = summary['codex_tokens']
    parts = ['%s %d' % (k, c[k]) for k in sorted(c)]
    return ['artdirect %s: %d pieces, Codex ran %d of a cap of %d; %s'
            % (summary['week'], len(summary['pieces']), summary['codex_runs'], summary['max_pieces'],
               ', '.join(parts) if parts else 'nothing to do'),
            'Codex tokens: %d input (%d cached), %d output (%d reasoning), %d in all'
            % (t['input_tokens'], t['cached_input_tokens'], t['output_tokens'], t['reasoning_output_tokens'],
               t['input_tokens'] + t['output_tokens'])]


def main(argv=None):
    argv = list(argv or [])
    if argv and argv[0] == 'artdirect':
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run artdirect',
                                     description='One visual idea per piece, made by Codex as a piece kit.')
    parser.add_argument('action', nargs='?', choices=('make', 'gate', 'check'), default='make')
    parser.add_argument('kits', nargs='*', help='check: the kit folders')
    parser.add_argument('--week-of', help='the Monday, YYYY-MM-DD (default: the coming Monday, New York)')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--pieces', help='a JSON list of {piece_id, title, claims, lane}')
    source.add_argument('--mix', help="the week's mix plan (growth.py mix plan --out)")
    source.add_argument('--inventory', help='a backlog inventory (default: the public feed, as on the runner)')
    parser.add_argument('--max-pieces', type=int, default=MAX_PIECES)
    parser.add_argument('--out', default=str(OUT))
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--now')
    args = parser.parse_args(argv)
    if args.action == 'check':
        failed = 0
        for kit in args.kits:
            errors = kit_errors(Path(kit))
            failed += bool(errors)
            print(Path(kit).name + (': passes the static checks' if not errors else ': ' + str(len(errors))
                                    + ' problems'))
            for error in errors:
                print('  ' + error)
        return int(bool(failed))
    if args.action == 'gate':
        summary = gate(args.out)
        for line in summary_lines(summary):
            print(line)
        print('written locally to ' + str(Path(args.out) / 'summary.json') + '; no external write')
        return 0
    if args.max_pieces < 0:
        parser.error('--max-pieces is zero or more')
    week_of = dt.date.fromisoformat(args.week_of) if args.week_of else coming_monday(args.now)
    if week_of.weekday() != 0:
        parser.error('--week-of is a Monday')
    if args.pieces:
        pieces = read_json(args.pieces)
        if not isinstance(pieces, list):
            parser.error('--pieces is a JSON list')
    elif args.mix:
        pieces = pieces_from_mix(read_json(args.mix))
    else:
        try:
            pieces = week_pieces(week_of, read_json(args.inventory) if args.inventory else None)
        except ValueError as exc:
            print('artdirect: the week could not be read: ' + str(exc))
            return 1
    summary = make(pieces, week_of, args.out, max_pieces=args.max_pieces, codex=args.codex)
    for line in summary_lines(summary):
        print(line)
    print('written locally to ' + str(Path(args.out) / 'summary.json') + '; no external write')
    return 0
