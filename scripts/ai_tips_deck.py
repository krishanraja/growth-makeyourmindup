"""Build, render and check one week's AI-tips carousel from a week file.

  python3 scripts/ai_tips_deck.py WEEK.json --assets DIR --out DIR [--no-render]

WEEK.json is one week's plan (example: calendar/ai-tips/2026-11-05.json). Every image path in it
(cover scene, cover flow crops, job screenshots) is relative to --assets, and logos are read from
DIR/logos/<name>.png. Screenshots stay out of this public repository: keep them in --assets.

It writes, into --out: jobs.json (render jobs for the ai-tips-screen kit), the twelve PNGs and
manifest.json (unless --no-render), and caption.txt. It exits non-zero on any failed check.

The checks are the format's standard made executable (docs/briefs/ai-tips-carousel.md):
  * shape: 5 to 8 jobs, so a cover and a close make at most 10 cards (Buffer's limit), each with 2 to 4 tools, one prompt, exactly three steps, one image;
  * sources: every tool has a vendor page and a check date no older than 7 days before the post;
  * sync: each image says what it shows, and that text shares a word with the prompt;
  * freshness: no job headline and no lead tool repeats a week file dated in the 28 days before;
  * words: content-engine copy lint (carousel text), prose and plain-English checks, no series
    name, no "Not X, Y" turn, no em dash, no quote marks around the prompt;
  * paint: no series colour (butter, lilac, coral) and no font outside the kit, from the manifest;
  * caption: content-engine copy lint (channel copy) and Instagram's 2,200 character limit.
Run from the repository root.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.copy_lint import copy_lint_errors  # noqa: E402
from engine.packs import prose_errors  # noqa: E402
from engine.run.plain import lint_text  # noqa: E402

KIT = 'ai-tips-screen'
SERIES_NAMES = re.compile(r'follow[\s._-]?the[\s._-]?money|under[\s._-]?the[\s._-]?hood|mind[\s._-]?the[\s._-]?gap', re.I)
NOT_X_Y = re.compile(r"\bnot\b[^.!?]{0,40}[,;]\s*(?:but\s+)?\w+|\bnot just\b|\bisn'?t\b[^.!?]{0,40},", re.I)
SERIES_COLOURS = {'#FFD84D': 'butter', '#B7A6FF': 'lilac', '#FF6A4D': 'coral'}
KIT_FONTS = {'Anton', 'Archivo', 'Fraunces', 'IBM Plex Mono'}
CAPTION_LIMIT = 2200
MAX_CARDS = 10
SOURCE_MAX_AGE = 7
NO_REPEAT_DAYS = 28
STOP = set('a an and the to of for in on my me your our this that it is be with from what who i by as at or'.split())


def words(t):
    return {w for w in re.findall(r'[a-z0-9]+', t.lower()) if w not in STOP and len(w) > 2}


def check_week(week, others=()):
    """Every rule that needs no rendering. Returns a list of error strings."""
    errs = []
    day = dt.date.fromisoformat(week['date'])
    jobs = week.get('jobs', [])
    # Buffer takes at most ten cards a carousel, cover and close included (Krish, 5 Nov 2026).
    # From 6 Nov 2026; the 5 Nov edition went out natively at twelve cards.
    if not 5 <= len(jobs) <= (10 if day <= dt.date(2026, 11, 5) else MAX_CARDS - 2):
        errs.append('jobs: %d, want 5 to %d (a cover and a close make at most %d cards)' % (len(jobs), MAX_CARDS - 2, MAX_CARDS))
    for n, j in enumerate(jobs, 1):
        at = 'job %d' % n
        tools = j.get('tools', [])
        if not 2 <= len(tools) <= 4:
            errs.append('%s: %d tools, want 2 to 4 (name the other tools that do the job)' % (at, len(tools)))
        for t in tools:
            if not t.get('url') or not t.get('checked'):
                errs.append('%s: %s has no vendor page or check date' % (at, t.get('name')))
                continue
            age = (day - dt.date.fromisoformat(t['checked'])).days
            if age > SOURCE_MAX_AGE or age < 0:
                errs.append('%s: %s checked %s, more than %d days before the post' % (at, t['name'], t['checked'], SOURCE_MAX_AGE))
        if len(j.get('steps', [])) != 3:
            errs.append('%s: want exactly three steps' % at)
        p = j.get('prompt', '')
        if not p or p[0] in '"“' or p[-1] in '"”':
            errs.append('%s: prompt missing or wrapped in quote marks (the card draws its own)' % at)
        img = j.get('image') or {}
        if not img.get('file') or not img.get('credit') or not img.get('shows'):
            errs.append('%s: image needs file, credit and shows' % at)
        elif not words(img['shows']) & words(p):
            errs.append('%s: image and prompt out of sync: "%s" vs "%s"' % (at, img['shows'], p))
    lead = {j['tools'][0]['name'] for j in jobs if j.get('tools')}
    heads = {j.get('headline', '').lower() for j in jobs}
    for o in others:
        gap = (day - dt.date.fromisoformat(o['date'])).days
        if 0 < gap <= NO_REPEAT_DAYS:
            for j in o.get('jobs', []):
                if j.get('headline', '').lower() in heads:
                    errs.append('repeat within %d days of %s: %s' % (NO_REPEAT_DAYS, o['date'], j['headline']))
                if j.get('tools') and j['tools'][0]['name'] in lead:
                    errs.append('lead tool repeats within %d days of %s: %s' % (NO_REPEAT_DAYS, o['date'], j['tools'][0]['name']))
    return errs


def build_jobs(week, assets):
    a = Path(assets).resolve()
    total = len(week['jobs'])
    c = week['cover']
    cover = dict(headline=c['headline'], accent=c['accent'], dek=c['dek'], photo=str(a / c['scene']['file']))
    credits = {'photo': c['scene']['credit']}
    template = 'cover'
    if c.get('flow'):
        template = 'cover-flow'
        for k, step in enumerate(c['flow'], 1):
            cover['step%d' % k] = str(a / step['file'])
            cover['label%d' % k] = step['label']
            credits['step%d' % k] = step['credit']
    out = [dict(template='piece:%s/%s' % (KIT, template), out='00-cover.png', fields=cover, credits=credits)]
    for n, j in enumerate(week['jobs'], 1):
        f = dict(headline=j['headline'], accent=j['accent'],
                 shot=str(a / j['image']['file']), steps=[[str(i), s] for i, s in enumerate(j['steps'], 1)])
        f['try'] = j['prompt']
        cr = {'shot': j['image']['credit']}
        for k, t in enumerate(j['tools'][:4], 1):
            f['logo%d' % k] = str(a / 'logos' / (t['logo'] + '.png'))
            cr['logo%d' % k] = 'Brandfetch'
        out.append(dict(template='piece:%s/tip' % KIT, out='%02d-tip.png' % n, fields=f, credits=cr))
    out.append(dict(template='piece:%s/close' % KIT, out='%02d-close.png' % (total + 1), fields=dict(week['close'])))
    return out


def check_words(jobs):
    errs = []
    for job in jobs:
        for k, v in job['fields'].items():
            if k in ('photo', 'shot') or k.startswith(('logo', 'step')) and k != 'steps':
                continue
            for t in ([' '.join(r) for r in v] if isinstance(v, list) else [str(v)]):
                at = '%s %s' % (job['out'], k)
                errs += ['%s: %s' % (at, e) for e in copy_lint_errors(t, 'carousel_text')]
                errs += ['%s: %s' % (at, e) for e in prose_errors(t)]
                if k != 'count':
                    errs += ['%s: plain %s' % (at, f['code']) for f in lint_text(t) if f['code'] != 'stacked_fragments']
                if SERIES_NAMES.search(t):
                    errs.append(at + ': names a series')
                if NOT_X_Y.search(t):
                    errs.append('%s: a "Not X, Y" turn: %s' % (at, t))
                if '—' in t:
                    errs.append(at + ': em dash')
    return errs


def check_paint(manifest):
    errs = []
    for card in manifest:
        for c in card.get('colours', []):
            if c.upper() in SERIES_COLOURS:
                errs.append('%s: paints the series colour %s' % (card['out'], SERIES_COLOURS[c.upper()]))
        bad = set(card.get('fonts', [])) - KIT_FONTS
        if bad:
            errs.append('%s: fonts outside the kit: %s' % (card['out'], ', '.join(sorted(bad))))
    return errs


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%b'), d.year)


def caption(week):
    cap = week['caption']
    lines = [cap['intro'], '', 'Where to start (checked %s):' % pretty(week['date']), '']
    for n, j in enumerate(week['jobs'], 1):
        # The caption leads with the tool the screenshot shows, so the image and its link agree.
        shown = j.get('image', {}).get('tool')
        lead = next((t for t in j['tools'] if t['name'] == shown), j['tools'][0])
        rest = [t['name'] for t in j['tools'] if t is not lead]
        line = '%d. %s: %s, %s.' % (n, j['label'], lead['name'], lead['url'])
        if rest:
            line += ' Also ' + (', '.join(rest[:-1]) + ' and ' + rest[-1] if len(rest) > 1 else rest[0]) + '.'
        lines.append(line)
    lines += ['', cap['outro']]
    if cap.get('tags'):
        lines += ['', cap['tags']]
    return '\n'.join(lines) + '\n'


def check_caption(text):
    errs = ['caption: ' + e for e in copy_lint_errors(text, 'channel_copy') + prose_errors(text)]
    if len(text) > CAPTION_LIMIT:
        errs.append('caption: %d characters, Instagram allows %d' % (len(text), CAPTION_LIMIT))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('week')
    ap.add_argument('--assets', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-render', action='store_true')
    args = ap.parse_args(argv)
    week_path = Path(args.week)
    week = json.loads(week_path.read_text())
    others = [json.loads(p.read_text()) for p in week_path.parent.glob('*.json') if p.resolve() != week_path.resolve()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    errs = check_week(week, others)
    jobs = build_jobs(week, args.assets)
    errs += check_words(jobs)
    cap = caption(week)
    errs += check_caption(cap)
    (out / 'jobs.json').write_text(json.dumps(jobs, indent=1))
    (out / 'caption.txt').write_text(cap)
    if not args.no_render and not errs:
        r = subprocess.run(['node', str(ROOT / 'scripts' / 'render_mocks.mjs'), str(out / 'jobs.json'),
                            '--manifest', str(out / 'manifest.json'), '--verify'], cwd=ROOT)
        if r.returncode:
            errs.append('render failed (fit, fonts or a second render that differs)')
        else:
            errs += check_paint(json.loads((out / 'manifest.json').read_text()))
    for e in errs:
        print(e)
    print('FAIL %d' % len(errs) if errs else 'PASS: %s' % out)
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
