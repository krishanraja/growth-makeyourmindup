"""The Canva brand lint: a design summary checked against social/brand/kit.json.

Offline only. Canva builds and exports; it never publishes (social/guides/canva.md).
lint_design takes a JSON summary of one design, such as a Canva design dataset
read back after an export, and returns error codes. It does not call Canva.

A summary: {"channel": "x", "width": 1600, "height": 900, "size": "x-card" (optional),
"template": "<kit template key>" (optional), "colours": ["#0C1512"], "fonts": ["Anton"],
"texts": ["..."], "quotes": ["..."] (optional; any double-quoted text also counts),
"required_texts": ["..."] (optional; Krish's quotes from growth.py mix briefs, each on the design exactly),
"date": "YYYY-MM-DD" (optional; the publishing day, which decides the accent: R125, engine/day_colours.py)}.
"""
import argparse
import json
from pathlib import Path
import re

from ..core import read_json
from ..social import has_boilerplate
from .. import day_colours

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / 'social' / 'brand' / 'kit.json'
HEX = re.compile(r'^#?([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')
QUOTED = re.compile(r'"([^"]{3,})"')
QUOTE_MARKS = {'‘': "'", '’': "'", '‚': "'", '‛': "'", '′': "'",
               '“': '"', '”': '"', '„': '"', '‟': '"', '″': '"'}


def finding(code, at, detail):
    return {'code': code, 'at': at, 'detail': detail}


def load_kit(root=ROOT):
    kit = read_json(Path(root) / 'social' / 'brand' / 'kit.json')
    for field in ('kit_id', 'name', 'palette', 'fonts', 'dimensions', 'templates'):
        if field not in kit:
            raise ValueError('kit.json needs ' + field)
    return kit


def colour(value):
    """'#0c1512', '0C1512' and '#0c1' style values as '#0C1512'; None if not a hex colour."""
    match = HEX.match(value.strip()) if isinstance(value, str) else None
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(c * 2 for c in digits)
    return '#' + digits.upper()


def font_ok(name, families):
    name = ' '.join(name.lower().split()) if isinstance(name, str) else ''
    return any(name == f or name.startswith(f + ' ') or name.startswith(f + '-') for f in families)


def normalise(text):
    """Quote-insensitive and whitespace-insensitive form, for the literal-match check."""
    for mark, plain in QUOTE_MARKS.items():
        text = text.replace(mark, plain)
    return ' '.join(text.split())


def quotes_of(dataset):
    """Explicit quotes, plus any text set in double quote marks."""
    found = [q for q in dataset.get('quotes') or [] if isinstance(q, str)]
    for text in dataset.get('texts') or []:
        if isinstance(text, str):
            found += QUOTED.findall(normalise(text))
    return [normalise(q).strip(' "\'') for q in found if normalise(q).strip(' "\'')]


def sizes_for(kit, channel):
    return {name: dims for name, dims in kit['dimensions'].items() if channel in dims['channels']}


def lint_design(dataset, piece_text=None, kit=None, root=ROOT, require_template=True):
    """Error codes for one design: off-kit colour or font, wrong size, an unfaithful quote, boilerplate."""
    kit = kit or load_kit(root)
    if not isinstance(dataset, dict):
        return [finding('bad_dataset', '$', 'a design summary is a JSON object')]
    out = []
    for field, kind in (('channel', str), ('width', int), ('height', int), ('colours', list), ('fonts', list),
                        ('texts', list)):
        if not isinstance(dataset.get(field), kind) or isinstance(dataset.get(field), bool):
            out.append(finding('bad_dataset', '$.' + field, field + ' is required'))
    if out:
        return out
    palette = {colour(entry['hex']) for entry in kit['palette']}
    for i, value in enumerate(dataset['colours']):
        if colour(value) not in palette:
            out.append(finding('off_kit_colour', '$.colours[%d]' % i, str(value)))
    if dataset.get('date'):
        # The day decides the accent (R125): a series day wears only its own subchannel colour, an off day none.
        try:
            for problem in day_colours.colour_errors([colour(v) for v in dataset['colours']], dataset['date']):
                out.append(finding('wrong_day_colour', '$.colours', problem))
        except ValueError:
            out.append(finding('bad_dataset', '$.date', 'date is YYYY-MM-DD'))
    families = [' '.join(f.lower().split()) for f in kit['fonts'].values()]
    for i, name in enumerate(dataset['fonts']):
        if not font_ok(name, families):
            out.append(finding('off_kit_font', '$.fonts[%d]' % i, str(name)))
    sizes = sizes_for(kit, dataset['channel'])
    size = (dataset['width'], dataset['height'])
    named = dataset.get('size')
    if not sizes:
        out.append(finding('unknown_channel', '$.channel', dataset['channel'] + ' has no size in the brand kit'))
    elif named is not None and (named not in sizes or (sizes[named]['width'], sizes[named]['height']) != size):
        out.append(finding('wrong_dimensions', '$.size', '%s is not %dx%d for %s' % ((named,) + size + (dataset['channel'],))))
    elif size not in {(d['width'], d['height']) for d in sizes.values()}:
        out.append(finding('wrong_dimensions', '$.width', '%dx%d is no %s size in the kit' % (size + (dataset['channel'],))))
    template = dataset.get('template')
    if require_template and (not isinstance(template, str) or template not in kit['templates']):
        out.append(finding('template_not_approved', '$.template', str(template) + ' is not an approved kit template'))
    # Krish's quotes on the option (offday.mock_briefs required_texts; Ruling, Krish, 2026-11-02): each must be on the
    # design exactly as he wrote it. Only where a line breaks may differ, since the layout sets the breaks.
    flat = lambda t: ' '.join(normalise(t).split())
    on_design = [flat(t) for t in dataset.get('texts') or [] if isinstance(t, str)]
    joined = ' '.join(on_design)
    for i, want in enumerate(dataset.get('required_texts') or []):
        if not isinstance(want, str) or not want.strip() or flat(want) not in joined:
            out.append(finding('required_text_missing', '$.required_texts[%d]' % i, str(want)[:60]))
    quotes = quotes_of(dataset)
    if quotes and not isinstance(piece_text, str):
        out.append(finding('no_piece_text', '$.quotes', 'a quote needs the published piece text to check against'))
    elif quotes:
        piece = normalise(piece_text)
        out += [finding('quote_not_in_piece', '$.quotes', q[:60]) for q in quotes if q not in piece]
    for i, text in enumerate(dataset['texts']):
        if isinstance(text, str) and has_boilerplate(text):
            out.append(finding('boilerplate', '$.texts[%d]' % i, 'illustration-disclaimer boilerplate'))
    return out


def lint(dataset, piece_text=None, root=ROOT):
    """The Canva Studio crew lint (crew/registry.json): lint_design against the checked-in kit."""
    return lint_design(dataset, piece_text, root=root)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run canva')
    parser.add_argument('command', choices=['canva'])
    parser.add_argument('action', choices=['lint'])
    parser.add_argument('design', help='JSON summary of one Canva design')
    parser.add_argument('--piece', help='text file of the published piece, for the quote check')
    args = parser.parse_args(argv)
    try:
        dataset = read_json(Path(args.design))
        piece = Path(args.piece).read_text(encoding='utf-8-sig') if args.piece else None
    except (OSError, ValueError) as exc:
        print(json.dumps({'valid': False, 'findings': [finding('read', '$', str(exc))]}))
        return 1
    found = lint(dataset, piece)
    print(json.dumps({'valid': not found, 'codes': sorted({f['code'] for f in found}), 'findings': found}, indent=1))
    return 0 if not found else 1
