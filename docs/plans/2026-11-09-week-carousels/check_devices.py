#!/usr/bin/env python3
"""Checks every card picture against BRIEF.md: present, parses, kit colours and fonts only, real logo files, no em dash."""
import json, re, sys
from pathlib import Path
from xml.etree import ElementTree as ET
HERE = Path(__file__).resolve().parent
BASE = {'#0c1512', '#070d0b', '#f4efe4', '#2f6b5c', '#7ef0c0', 'none', 'transparent', 'currentcolor'}
SERIES = {'mon': '#ffd84d', 'wed': '#b7a6ff', 'fri': '#ff6a4d'}
FONTS = {'anton', 'archivo', 'plex'}
bad = []
for day, colour in SERIES.items():
    deck = json.loads((HERE / day / 'deck.json').read_text())
    for n in range(2, len(deck['cards']) + 1):
        f = HERE / day / 'devices' / ('card-%d.svg' % n)
        if not f.is_file():
            bad.append('%s: missing' % f.name if False else '%s/%s missing' % (day, f.name)); continue
        t = f.read_text(encoding='utf-8')
        try:
            ET.fromstring(t[t.index('<svg'):])
        except Exception as e:
            bad.append('%s/%s does not parse: %s' % (day, f.name, e)); continue
        if '—' in t or '–' in t:
            bad.append('%s/%s has a dash' % (day, f.name))
        for c in re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', t):
            if c.lower() not in BASE | {colour}:
                bad.append('%s/%s off-kit colour %s' % (day, f.name, c))
        if re.search(r'\b(rgb|hsl)a?\(', t):
            bad.append('%s/%s uses rgb()/hsl(); hex only' % (day, f.name))
        for fam in re.findall(r'font-family\s*[:=]\s*["\']?([^;"\'>]+)', t):
            names = {x.strip().strip('\'"').lower() for x in fam.split(',')}
            if not names <= FONTS:
                bad.append('%s/%s font %s' % (day, f.name, fam))
        for href in re.findall(r'href="([^"]+)"', t):
            if not href.startswith('../devices/') or not (HERE / day / 'devices' / href.split('/')[-1]).is_file():
                bad.append('%s/%s bad image %s' % (day, f.name, href))
for b in bad:
    print('check_devices:', b)
print('check_devices: %s' % ('clean' if not bad else '%d problems' % len(bad)))
sys.exit(1 if bad else 0)
