"""Piece kits: the checks a kit passes before its pictures are used, whoever built it.

Ruling (Krish, 2026-11-13): every carousel is made in a Claude session, with the Codex plugin building it, as in the
other usual workflows ("all the carousels should now be done in Claude, but using the Codex plug in as per the other
usual workflows"); the same day, "memes and Notes images should go the same way". So a piece kit is built by Codex from
a card a Claude session writes (content-engine's `ve card`, kinds carousel, meme and notes_image), queued in
codex/queue/<id>.md and built through the plugin by the Codex lane, and the session verifies it. The Saturday
art-direction run that used to make kits here with Codex on an API key is retired. Content-engine's
docs/CAROUSEL-STANDARD.md, "How a carousel is made", is the route; render/KIT.md, "Piece kits", says what a kit holds,
and render/KIT_RULES.md is the brief a card points Codex to.

A piece kit is render/pieces/<piece_id>/: templates/*.html, piece.css (kit tokens only), templates.json (the shape of
render/templates.json, kind piece_kit) and idea.md (one plain paragraph). These are the card's acceptance:

    growth.py run kit check DIR... [--words FILE]   the static checks; --words (a JSON with title and claims, or a
                                                    carousel-deck/1 file) also refuses the piece's own words in the kit
    growth.py run kit jobs DIR --out FILE           the render jobs for the kit's own examples, for the renderer
    growth.py run kit painted DIR --report FILE     the renderer's own report (its --verify --manifest FILE)
                                                    held to the kit's colours, fonts and sizes

Nothing here posts, schedules, sends, spends or runs a model. What it prints is counts and reasons about code only:
this repository is public.
"""
import argparse
import json
import os
from pathlib import Path
import re

from ..copy_lint import copy_lint_errors
from ..core import read_json, write_json
from ..packs import prose_errors
from .plain import lint_text

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / 'render'
PIECES = RENDER / 'pieces'
RULES = RENDER / 'KIT_RULES.md'

KIT_FONTS = ('Anton', 'Fraunces', 'Archivo', 'IBM Plex Mono')
GENERIC_FONTS = ('serif', 'sans-serif', 'monospace')
COLOUR_TOKENS = ('--ink', '--ink-deep', '--cream', '--green', '--mint', '--butter', '--coral', '--lilac')
FONT_TOKENS = ('--heading', '--sub', '--body', '--mono')
PIECE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{1,63}$')
TEMPLATE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
PLACEHOLDER = re.compile(r'\{\{(?:(rows|options|photo):)?([a-z0-9_]+)\}\}')
SPEC_REQUIRED = ('file', 'width', 'height', 'fields', 'required', 'example')
SPEC_OPTIONAL = ('choices', 'note', 'safe')
# A photo is a real picture of the story (a photograph, never a screenshot of text), filled only at render time from a
# local file; the kit itself still holds no picture. Krish, 2026-11-02: "build out the carousel with real life imagery or
# screenshots". Every photo says whose it is, but off the card: the render job carries a `credits` entry for each photo
# field, and the credits go in the post's description (Krish, 2026-11-02: "all sources should go in the carousel post
# description").
FIELD_TYPES = ('text', 'rows', 'options', 'photo')
SAFE_VERTICAL = {'top': 250, 'bottom': 340}
MAX_TEMPLATES = 8
MAX_FILE_BYTES = 64 * 1024
# Every carousel ends on the house close (render/templates/carousel-close.html: the takeaway, Subscribe free and the
# wordmark small in the bottom right), never a close of its own (content-engine config/brand-palette.json
# house_close_slide; Ruling, Krish, 2026-11-12: "I approve the brand palette sheet, but only if it falls in line with
# the attached"). Five piece kits made five different endings before the palette; they keep theirs for the record, and
# Saturday good news keeps the close Krish fixed for it (docs/CAROUSEL-STANDARD.md in content-engine).
OWN_CLOSE = re.compile(r'(?:^|-)(?:close|closer|ending|end|outro|takeaway|cta)(?:-|$)')
OWN_CLOSE_KEPT = frozenset({'carousel-1aaf9a3ce399213eb222', 'carousel-2298e19a6b82b4543f0e', 'carousel-734e1efbef8f3b2199b4',
                            'carousel-96b5d3c036fad579a034', 'carousel-ce7f9aa2d1d6a9d5318f', 'off-sat-goodnews'})
KIT_CSS_LINK = '<link rel="stylesheet" href="../../../kit.css">'
PIECE_CSS_LINK = '<link rel="stylesheet" href="../piece.css">'
FIT_SCRIPT = '<script src="../../../fit.js"></script>'
# The brand mark is the official logo file, painted by kit.css from render/brand/ (Ruling, Krish, 2026-11-03: "You've
# fabricated my brand logo"). A kit places it with exactly this markup; the drawn wordmark it replaces is refused.
BRANDMARKS = ('<div class="brandmark"></div>', '<div class="brandmark corner"></div>')
DRAWN_WORDMARK = re.compile(r'class="(?:wordmark|mark|words|up)"|MAKE YOUR MIND/')
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
WORDMARK_PROPERTIES = re.compile(r'^(?:--bm|width|margin(?:-[a-z]+)?|align-self|justify-self|justify-content|order|'
                                 r'flex(?:-[a-z]+)?|position|top|right|bottom|left|z-index)$')
SECRET = re.compile(r'\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgen1_[A-Za-z0-9_-]{8,}')
NEVER_WORDS = ('passport', 'krish')


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
        for name, value in decls:
            errors += _declaration_errors(name, value, at)
            if re.search(r'\.brandmark(?![\w-])', selector) and not WORDMARK_PROPERTIES.match(name):
                errors.append(at + ': restyles the brand mark (' + selector + ' ' + name + '); only size and place it')
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
    if DRAWN_WORDMARK.search(html):
        errors.append(at + ': a wordmark set as type; the brand mark is the official file, <div class="brandmark"></div>')
    if html.count('class="brandmark') != sum(html.count(b) for b in BRANDMARKS):
        errors.append(at + ': the brand mark is not the house markup')
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
        return errors + [at + ': fields map names to text, rows, options or photo']
    required, example = spec['required'], spec['example']
    if not isinstance(required, list) or not set(required) <= set(fields):
        errors.append(at + ': required names declared fields')
    if not isinstance(example, dict) or not set(example) <= set(fields) or not set(required or []) <= set(example):
        return errors + [at + ': the example fills every required field and names only declared ones']
    for name, value in example.items():
        kind = fields[name]
        ok = (isinstance(value, str) if kind in ('text', 'photo') else
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
    if piece_id not in OWN_CLOSE_KEPT:
        for rel in sorted(texts):
            if rel.startswith('templates/') and OWN_CLOSE.search(rel[len('templates/'):-len('.html')]):
                errors.append(rel + ': a close of its own; every carousel ends on the house close '
                                    '(render/templates/carousel-close.html, config/brand-palette.json in content-engine)')
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


# The stand-in picture an example render puts in a photo slot: a flat grey block, since a kit holds no real picture.
PHOTO_EXAMPLE = ROOT / 'render' / 'photo-example.png'


def render_jobs(kit_dir):
    """The renderer's jobs for a kit: each template from its own example (a photo slot gets the grey stand-in)."""
    manifest = read_json(Path(kit_dir) / 'templates.json')
    pid = Path(kit_dir).name
    def fields(spec):
        return {k: (str(PHOTO_EXAMPLE) if spec['fields'].get(k) == 'photo' else v) for k, v in spec['example'].items()}
    def credits(spec):
        return {k: 'The example stand-in' for k, v in spec['fields'].items() if v == 'photo'}
    return [dict({'template': 'piece:' + pid + '/' + tid, 'fields': fields(spec), 'out': tid + '.png'},
                 **({'credits': credits(spec)} if credits(spec) else {}))
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


def deck_words(data):
    """The words a kit must not hold, from a piece ({title, claims}) or a carousel-deck/1 file (its title and every
    card's headline and line)."""
    if not isinstance(data, dict):
        return {}
    if data.get('schema') == 'carousel-deck/1':
        claims = [str(c.get(k) or '') for c in data.get('cards') or [] if isinstance(c, dict) for k in ('headline', 'line')]
        return {'title': data.get('title'), 'claims': [c for c in claims if c.strip()]}
    return {'title': data.get('title'), 'claims': data.get('claims') or []}


def main(argv=None):
    argv = list(argv or [])
    if argv and argv[0] == 'kit':
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run kit',
                                     description='The checks a piece kit passes before its pictures are used.')
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('check', help='the static checks')
    check.add_argument('kits', nargs='+', help='the kit folders')
    check.add_argument('--words', help='a piece ({title, claims}) or a carousel-deck/1 file whose words stay out')
    jobs = sub.add_parser('jobs', help='the render jobs for a kit\'s own examples')
    jobs.add_argument('kit')
    jobs.add_argument('--out', required=True)
    painted = sub.add_parser('painted', help='the renderer\'s report, held to the kit')
    painted.add_argument('kit')
    painted.add_argument('--report', required=True)
    args = parser.parse_args(argv)
    if args.action == 'jobs':
        write_json(Path(args.out), render_jobs(Path(args.kit)))
        print(Path(args.kit).name + ': ' + str(len(render_jobs(Path(args.kit)))) + ' render jobs written locally')
        return 0
    if args.action == 'painted':
        try:
            results = read_json(args.report)
            errors = painted_errors(Path(args.kit), results) if isinstance(results, list) else ['no render report']
        except (OSError, ValueError):
            errors = ['the renderer refused it or did not render it twice the same']
        print(Path(args.kit).name + (': painted only in the kit' if not errors else ': ' + str(len(errors)) + ' problems'))
        for error in errors:
            print('  ' + error)
        return int(bool(errors))
    words = deck_words(read_json(args.words)) if args.words else None
    failed = 0
    for kit in args.kits:
        errors = kit_errors(Path(kit), secrets=secret_values()) + (words_errors(Path(kit), words) if words else [])
        failed += bool(errors)
        print(Path(kit).name + (': passes the static checks' if not errors else ': ' + str(len(errors))
                                + ' problems'))
        for error in errors:
            print('  ' + error)
    return int(bool(failed))
