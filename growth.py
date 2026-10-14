#!/usr/bin/env python3
"""The growth engine's one tool: read what Krish has published, check a draft
against his house rules, and leave a pack in Control Center.

Standard library only. Runs anywhere Python 3.9+ runs (a Codex session, a Mac,
a cloud box). Nothing here posts, sends, comments, follows or DMs anywhere:
the only write is a pack of drafts into Control Center, where Krish reads
them and posts by hand.

    python3 growth.py pieces [--days 21] [--full]
        The published pieces, newest first, from the public feed
        (https://home.makeyourmindup.ai/feed). --full prints each article's
        text: the only source of facts for any draft.

    python3 growth.py check PACK.json
        The house rules on every draft in the pack (see RULES below). Exit 1
        names each draft that breaks one.

    python3 growth.py post PACK.json
        Checks, then stores the pack in Control Center (POST /api/growth/packs,
        Bearer $GROWTH_ENGINE_TOKEN). Same date and kind replaces the earlier
        pack. Shows on Control Center > Growth > Packs.

    python3 growth.py read [--days 7] [--kind daily]
        The packs already in Control Center (for the Sunday report).

    python3 growth.py --self-test

A pack file:
    {"pack_date": "2026-10-16", "kind": "daily",
     "headline": "Friday: 2 posts and 4 search fixes for the AI pick piece",
     "items": [{"platform": "linkedin", "target_url": "https://...",
                "target_name": "", "why": "...", "text": "..."}],
     "numbers": null, "link": null}

Kinds: daily, pitches, swaps, radar, numbers, report.
Environment: GROWTH_ENGINE_TOKEN (required to post or read),
CONTROL_CENTER_URL (default https://controlcenter.krishraja.com).
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

FEED = 'https://home.makeyourmindup.ai/feed'
BASE = os.environ.get('CONTROL_CENTER_URL', 'https://controlcenter.krishraja.com').rstrip('/')
KINDS = ('daily', 'pitches', 'swaps', 'radar', 'numbers', 'report')
PLATFORMS = ('linkedin', 'x', 'substack', 'youtube', 'instagram', 'tiktok', 'reddit', 'email', 'seo', 'podcast', 'other')

# Krish's house rules for anything written in his name. Control Center refuses
# the first two as well, so a pack that skips this check still cannot land.
EM_DASH = re.compile('—')
PERCENT = re.compile(r'\d\s*%|\bper ?cent\b', re.I)
SLOP = [
    'delve', "in today's", 'in a world where', "it's worth noting", 'navigate', 'landscape', 'game-changer',
    'game changer', 'seamless', 'unlock', 'harness', 'leverage', 'robust', 'crucial', 'pivotal', 'moreover',
    'furthermore', "here's the thing", 'the reality is', 'at the end of the day', 'a testament to', 'tapestry',
    'realm', 'ever-evolving', 'cutting-edge', 'revolutionize', 'revolutionise', 'transformative', 'paradigm',
    'synergy', 'buckle up', "let's dive", 'deep dive', 'a new era', 'make no mistake', 'let that sink in',
    'unpopular opinion', 'thoughts?', 'agree?',
]
NOT_BUT = re.compile(r"\b(?:it'?s|this is|that'?s)\s+not\s+(?:just\s+|only\s+|about\s+)?[^.;:!?]{1,60}[,;]\s*(?:it'?s|but)\b"
                     r"|\bisn'?t\s+(?:just|only)\b", re.I)
LIMITS = {'linkedin': 3000, 'x': 280, 'reddit': 1500}
X_THREAD_SPLIT = re.compile(r'\n\s*\n')


def problems(item):
    """Every house rule this one draft breaks, in plain words."""
    out = []
    text = item.get('text') or ''
    platform = (item.get('platform') or '').lower()
    if not text.strip():
        return ['it has no text']
    if platform not in PLATFORMS:
        out.append(f'platform "{platform}" is not one of {", ".join(PLATFORMS)}')
    if EM_DASH.search(text):
        out.append('it has an em dash (use a comma, a full stop or "and")')
    if PERCENT.search(text):
        out.append('it has a percentage (Krish uses none: say the number of things, or a plain word)')
    low = text.lower()
    for s in SLOP:
        if s in low:
            out.append(f'it says "{s}", a stock phrase that reads as machine-written')
    if NOT_BUT.search(text):
        out.append('it uses the "it\'s not X, it\'s Y" turn')
    if platform == 'x':
        for n, post in enumerate(X_THREAD_SPLIT.split(text.strip()), 1):
            if len(post) > LIMITS['x']:
                out.append(f'X post {n} is {len(post)} characters (280 at most; separate posts with a blank line)')
    elif platform in LIMITS and len(text) > LIMITS[platform]:
        out.append(f'it is {len(text)} characters ({LIMITS[platform]} at most on {platform})')
    if platform == 'linkedin' and item.get('kind_hint') == 'comment' and re.search(r'https?://', text):
        out.append('a LinkedIn comment with a link (LinkedIn hides those)')
    if len(text) > 4000:
        out.append('it is over 4,000 characters')
    return out


def check_pack(pack):
    errs = []
    if pack.get('kind') not in KINDS:
        errs.append(f'kind must be one of {", ".join(KINDS)}')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(pack.get('pack_date') or '')):
        errs.append('pack_date must be YYYY-MM-DD')
    head = (pack.get('headline') or '').strip()
    if not head:
        errs.append('headline is empty')
    elif EM_DASH.search(head) or PERCENT.search(head):
        errs.append('headline has an em dash or a percentage')
    items = pack.get('items') or []
    if len(items) > 40:
        errs.append('more than 40 drafts in one pack')
    for i, item in enumerate(items, 1):
        for p in problems(item):
            errs.append(f'draft {i} ({item.get("platform", "?")}): {p}')
    return errs


def call(method, path, body=None):
    token = os.environ.get('GROWTH_ENGINE_TOKEN', '')
    if not token:
        sys.exit('GROWTH_ENGINE_TOKEN is not set. Krish sets it once in this environment (growth-engine/README.md, step 2).')
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        sys.exit(f'Control Center said {e.code}: {e.read().decode(errors="replace")[:500]}')
    except urllib.error.URLError as e:
        sys.exit(f'Could not reach Control Center at {BASE}: {e.reason}')


def strip_html(s):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s or '', flags=re.S | re.I)
    s = re.sub(r'</(p|h\d|li|blockquote)>', '\n\n', s, flags=re.I)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', s)).strip()


def pieces(days):
    with urllib.request.urlopen(urllib.request.Request(FEED, headers={'User-Agent': 'growth-engine'}), timeout=60) as r:
        root = ET.fromstring(r.read())
    ns = {'c': 'http://purl.org/rss/1.0/modules/content/'}
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    out = []
    for it in root.iter('item'):
        when = email.utils.parsedate_to_datetime(it.findtext('pubDate'))
        if when < since:
            continue
        title = it.findtext('title') or ''
        out.append({
            'date': when.date().isoformat(),
            'title': title,
            'url': it.findtext('link'),
            'kind': 'video post' if title.upper().startswith('VIDEO:') else 'article',
            'subtitle': strip_html(it.findtext('description') or ''),
            'text': strip_html(it.findtext('c:encoded', namespaces=ns) or ''),
        })
    return out


def self_test():
    ok = 0
    def t(name, cond):
        nonlocal ok
        if not cond:
            sys.exit(f'self-test FAILED: {name}')
        ok += 1
    good = {'pack_date': '2026-10-16', 'kind': 'daily', 'headline': 'Friday pack',
            'items': [{'platform': 'linkedin', 'text': 'I asked two AI apps the same thing. One said no.'}]}
    t('a clean pack passes', check_pack(good) == [])
    t('an em dash is refused', any('em dash' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': 'Muse — Meta'}]})))
    t('a percentage is refused', any('percentage' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': '70% sure'}]})))
    t('"per cent" is refused', any('percentage' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': 'ten per cent'}]})))
    t('slop is named', any('delve' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': "Let's delve in"}]})))
    t('an over-long X post is caught', any('X post 1' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': 'a' * 281}]})))
    t('an X thread splits on blank lines', check_pack({**good, 'items': [{'platform': 'x', 'text': 'a' * 200 + '\n\n' + 'b' * 200}]}) == [])
    t('an unknown kind is refused', any('kind' in e for e in check_pack({**good, 'kind': 'notes'})))
    t('empty text is refused', any('no text' in e for e in check_pack({**good, 'items': [{'platform': 'x', 'text': ' '}]})))
    t('html becomes paragraphs', strip_html('<p>One &amp; two</p><p>Three</p>') == 'One & two\n\nThree')
    print(f'growth self-test passed: {ok} checks')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--self-test', action='store_true')
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('pieces'); p.add_argument('--days', type=int, default=21); p.add_argument('--full', action='store_true')
    c = sub.add_parser('check'); c.add_argument('file')
    s = sub.add_parser('post'); s.add_argument('file')
    r = sub.add_parser('read'); r.add_argument('--days', type=int, default=7); r.add_argument('--kind')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.cmd == 'pieces':
        for x in pieces(a.days):
            print(f"{x['date']}  {x['kind']:10}  {x['title']}\n            {x['url']}")
            if a.full:
                print('\n' + x['text'] + '\n' + '-' * 72)
        return
    if a.cmd in ('check', 'post'):
        pack = json.load(open(a.file))
        errs = check_pack(pack)
        if errs:
            print('Not ready:\n  ' + '\n  '.join(errs))
            sys.exit(1)
        if a.cmd == 'check':
            print(f'ready: {len(pack.get("items") or [])} drafts')
            return
        out = call('POST', '/api/growth/packs', pack)
        print(f'stored in Control Center: {pack["kind"]} {pack["pack_date"]} ({len(pack.get("items") or [])} drafts) '
              f'{BASE}/#/growth?section=packs' if out.get('ok') else json.dumps(out))
        return
    if a.cmd == 'read':
        q = f'/api/growth/packs?days={a.days}' + (f'&kind={a.kind}' if a.kind else '')
        print(json.dumps(call('GET', q), indent=1))
        return
    ap.print_help()


if __name__ == '__main__':
    main()
