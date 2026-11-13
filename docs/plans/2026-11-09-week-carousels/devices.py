#!/usr/bin/env python3
"""The card pictures (devices/card-N.svg) for the three decks, drawn to BRIEF.md. Kit colours, kit fonts, real logos."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, DEEP, CREAM, GREEN, MINT = '#0C1512', '#070D0B', '#F4EFE4', '#2F6B5C', '#7EF0C0'
SER = {'mon': '#FFD84D', 'wed': '#B7A6FF', 'fri': '#FF6A4D'}


def svg(body, h=620):
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 920 %d" '
            'width="920" height="%d">%s</svg>\n' % (h, h, body))


def t(x, y, s, size=30, fam='Anton', fill=CREAM, anchor='middle', extra=''):
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" fill="%s" text-anchor="%s" %s>%s</text>'
            % (x, y, fam, size, fill, anchor, extra, s))


def logo(f, x, y, w, h):
    return '<image href="../devices/%s" x="%s" y="%s" width="%s" height="%s" preserveAspectRatio="xMidYMid meet"/>' % (f, x, y, w, h)


def tile(f, x, y, w, h, pad=18, fill=CREAM):
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="%s"/>' % (x, y, w, h, fill)
            + logo(f, x + pad, y + pad, w - 2 * pad, h - 2 * pad))


def person(x, y, s=1.0, fill=CREAM, op=1.0):
    """A plain silhouette (no face): head and shoulders."""
    return ('<g transform="translate(%s %s) scale(%s)" fill="%s" fill-opacity="%s"><circle cx="0" cy="-34" r="13"/>'
            '<path d="M-20 0 Q-20 -18 0 -18 Q20 -18 20 0 Z"/></g>' % (x, y, s, fill, op))


def write(day, n, body, h=620):
    (HERE / day / 'devices' / ('card-%d.svg' % n)).write_text(svg(body, h), encoding='utf-8')


# ---------------- mon: follow.the.money (butter) ----------------
B = SER['mon']
# 2. timeline: the founders leave for Google; two years later the app goes bust
b = ['<line x1="60" y1="420" x2="860" y2="420" stroke="%s" stroke-width="8" stroke-linecap="round"/>' % GREEN,
     '<circle cx="190" cy="420" r="20" fill="%s"/>' % CREAM, '<circle cx="730" cy="420" r="20" fill="%s"/>' % B,
     t(190, 490, 'AUG 2024', 38, 'Plex'), t(730, 490, 'OCT 2026', 38, 'Plex', B),
     t(460, 405, 'TWO YEARS LATER', 30, 'Plex', CREAM, extra='fill-opacity="0.6"'),
     '<rect x="100" y="40" width="180" height="180" rx="24" fill="%s"/>' % CREAM, logo('google-g.svg', 132, 72, 116, 116)]
for i, x in enumerate([130, 190, 250]):
    b.append(person(x, 350, 1.9, CREAM, 1 - i * 0.12))
b += ['<path d="M190 300 L190 240" stroke="%s" stroke-width="7" stroke-linecap="round"/>' % B,
      '<path d="M168 262 L190 236 L212 262" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % B,
      t(190, 560, 'FOUNDERS GO TO GOOGLE', 34, 'Anton', CREAM),
      logo('characterai-cream.svg', 590, 300, 280, 40),
      '<g transform="rotate(-8 730 170)"><rect x="590" y="100" width="280" height="130" rx="14" fill="none" stroke="%s" stroke-width="9"/>' % B,
      t(730, 200, 'BUST', 96, 'Anton', B) + '</g>',
      t(730, 560, 'THE APP GOES BUST', 34, 'Anton', B)]
write('mon', 2, ''.join(b))

# 3. the Disney deal on OpenAI's Sora app, closed
b = [tile('disney-script-cream.svg', 40, 200, 250, 150, 24, INK)]
b[0] = ('<rect x="40" y="200" width="250" height="150" rx="18" fill="%s" stroke="%s" stroke-opacity="0.35" stroke-width="2"/>' % (DEEP, CREAM)
        + logo('disney-script-cream.svg', 64, 224, 202, 102))
b += ['<line x1="300" y1="275" x2="560" y2="275" stroke="%s" stroke-width="6" stroke-dasharray="14 12"/>' % CREAM,
      t(430, 245, '$1B DEAL', 40, 'Anton', CREAM),
      '<line x1="352" y1="232" x2="508" y2="232" stroke="%s" stroke-width="7"/>' % B]
# the phone
b += ['<rect x="590" y="40" width="250" height="480" rx="40" fill="%s" stroke="%s" stroke-width="6"/>' % (DEEP, CREAM),
      '<rect x="690" y="58" width="50" height="10" rx="5" fill="%s" fill-opacity="0.5"/>' % CREAM,
      logo('openai-symbol-cream.svg', 665, 120, 100, 100), t(715, 270, 'SORA', 44, 'Anton', CREAM, extra='fill-opacity="0.5"')]
# closed sign hung across
b += ['<line x1="640" y1="300" x2="700" y2="352" stroke="%s" stroke-width="4"/><line x1="790" y1="300" x2="730" y2="352" stroke="%s" stroke-width="4"/>' % (CREAM, CREAM),
      '<g transform="rotate(-6 715 400)"><rect x="590" y="352" width="250" height="96" rx="12" fill="%s"/>' % B,
      t(715, 420, 'CLOSED', 62, 'Anton', INK) + '</g>',
      t(715, 560, 'OPENAI SHUT IT, MARCH 2026', 24, 'Plex', CREAM, extra='fill-opacity="0.7"')]
write('mon', 3, ''.join(b))

# 4. 66 staff walk over to Disney, the lawsuits stay behind
b = []
k = 0
for r in range(6):
    for c in range(11):
        if k < 66:
            b.append(person(70 + c * 46, 140 + r * 56, 0.85, CREAM, 0.95))
            k += 1
b += [t(300, 60, '66 STAFF', 44, 'Anton', CREAM)]
b += ['<path d="M590 300 L680 300 M660 280 L684 300 L660 320" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % B]
b += ['<rect x="700" y="210" width="200" height="180" rx="18" fill="%s" stroke="%s" stroke-opacity="0.35" stroke-width="2"/>' % (DEEP, CREAM),
      logo('disney-script-cream.svg', 720, 240, 160, 120)]
# lawsuits pile left behind
for i in range(5):
    b.append('<rect x="%d" y="%d" width="150" height="26" rx="4" fill="%s" fill-opacity="%s" transform="rotate(%d %d %d)"/>'
             % (60 + (i % 2) * 8, 590 - i * 22, B, 0.95 - i * 0.08, (-3 if i % 2 else 2), 130, 590 - i * 22))
b += [t(240, 600, 'LAWSUITS STAY BEHIND', 28, 'Plex', B, 'start')]
b += [logo('characterai-cream.svg', 240, 528, 220, 34)]
write('mon', 4, ''.join(b))

# 5. RENT to OWN: Disney, Netflix, Warner Music
b = ['<rect x="40" y="60" width="250" height="500" rx="22" fill="none" stroke="%s" stroke-opacity="0.35" stroke-width="3" stroke-dasharray="12 10"/>' % CREAM,
     t(165, 140, 'RENT', 64, 'Anton', CREAM, extra='fill-opacity="0.45"'),
     t(165, 330, 'SOMEONE', 28, 'Plex', CREAM, extra='fill-opacity="0.45"'), t(165, 368, "ELSE'S AI", 28, 'Plex', CREAM, extra='fill-opacity="0.45"'),
     '<path d="M310 310 L400 310 M378 288 L404 310 L378 332" stroke="%s" stroke-width="8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % B,
     '<rect x="420" y="40" width="460" height="540" rx="22" fill="%s" fill-opacity="0.10" stroke="%s" stroke-width="4"/>' % (B, B),
     t(650, 120, 'OWN', 64, 'Anton', B)]
rows = [('disney-script-cream.svg', DEEP), ('netflix.svg', CREAM), ('warner-music-group-cream.svg', DEEP)]
for i, (f, bg) in enumerate(rows):
    y = 160 + i * 135
    b.append('<rect x="460" y="%d" width="230" height="110" rx="16" fill="%s" stroke="%s" stroke-opacity="0.3" stroke-width="2"/>' % (y, bg, CREAM))
    b.append(logo(f, 482, y + 18, 186, 74))
    b.append('<rect x="710" y="%d" width="140" height="50" rx="25" fill="%s"/>' % (y + 30, B))
    b.append(t(780, y + 66, 'BOUGHT', 28, 'Anton', INK))
write('mon', 5, ''.join(b))

# 6. the empty box
b = ['<ellipse cx="460" cy="560" rx="300" ry="26" fill="%s" fill-opacity="0.6"/>' % DEEP,
     '<path d="M230 330 L460 400 L690 330 L690 530 L460 600 L230 530 Z" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>' % (INK, CREAM),
     '<path d="M460 400 L460 600" stroke="%s" stroke-width="4"/>' % CREAM,
     '<path d="M230 330 L460 260 L690 330 L460 400 Z" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>' % (DEEP, CREAM),
     '<path d="M230 330 L150 250 L380 190 L460 260 Z" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>' % (INK, CREAM),
     '<path d="M690 330 L770 250 L540 190 L460 260 Z" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>' % (INK, CREAM),
     '<g fill="none" stroke="%s" stroke-width="5" stroke-opacity="0.55"><path d="M420 90 h120 a24 24 0 0 1 24 24 v40 a24 24 0 0 1 -24 24 h-70 l-26 22 v-22 h-24 a24 24 0 0 1 -24 -24 v-40 a24 24 0 0 1 24 -24 z"/></g>' % B,
     '<g fill="%s" fill-opacity="0.55"><circle cx="452" cy="134" r="7"/><circle cx="480" cy="134" r="7"/><circle cx="508" cy="134" r="7"/></g>' % B,
     ]
write('mon', 6, ''.join(b))

# 7. the checklist
qs = ['FOUNDERS STILL THERE?', 'YOUR TOOL ITS MAIN PRODUCT?', 'SHORT OF CASH?', 'COLLECTING LAWSUITS?']
b = ['<rect x="80" y="20" width="760" height="580" rx="24" fill="%s"/>' % CREAM,
     '<rect x="80" y="20" width="760" height="20" rx="10" fill="%s"/>' % B,
     t(130, 110, 'ABOUT THE MAKER OF YOUR AI', 30, 'Plex', INK, 'start', 'fill-opacity="0.6"')]
for i, q in enumerate(qs):
    y = 170 + i * 108
    b.append('<rect x="130" y="%d" width="62" height="62" rx="10" fill="none" stroke="%s" stroke-width="5"/>' % (y, INK))
    b.append(t(222, y + 47, q, 42, 'Anton', INK, 'start'))
    if i < 3:
        b.append('<line x1="130" y1="%d" x2="790" y2="%d" stroke="%s" stroke-opacity="0.15" stroke-width="2"/>' % (y + 88, y + 88, INK))
write('mon', 7, ''.join(b))

# 8. (last) the spare key on its hook
b = ['<circle cx="460" cy="60" r="18" fill="none" stroke="%s" stroke-width="8"/>' % CREAM,
     '<path d="M460 78 L460 118" stroke="%s" stroke-width="8" stroke-linecap="round"/>' % CREAM,
     '<circle cx="460" cy="200" r="78" fill="none" stroke="%s" stroke-width="26"/>' % B,
     '<rect x="446" y="272" width="28" height="200" rx="6" fill="%s"/>' % B,
     '<rect x="474" y="400" width="44" height="22" rx="4" fill="%s"/><rect x="474" y="440" width="30" height="22" rx="4" fill="%s"/>' % (B, B),
     '<path d="M510 160 L640 230" stroke="%s" stroke-width="3"/>' % CREAM,
     '<g transform="rotate(14 690 250)"><rect x="620" y="215" width="160" height="78" rx="10" fill="%s"/>' % CREAM,
     '<circle cx="640" cy="254" r="7" fill="%s"/>' % INK, t(710, 270, 'PLAN B', 42, 'Anton', INK) + '</g>']
write('mon', 8, ''.join(b), 520)

# ---------------- wed: under.the.hood (lilac) ----------------
L = SER['wed']
# 2. the layers of the song
layers = [("SINGER'S VOICE", L, INK), ("DJ'S REBUILD", GREEN, CREAM), ("AI APP'S FIRST SONG", DEEP, CREAM), ('HER WORDS', CREAM, INK)]
b = []
for i, (lab, fill, ink) in enumerate(layers):
    y = 40 + i * 132
    b.append('<rect x="20" y="%d" width="600" height="112" rx="18" fill="%s" stroke="%s" stroke-opacity="0.35" stroke-width="2"/>' % (y, fill, CREAM))
    b.append(t(56, y + 72, lab, 46, 'Anton', ink, 'start'))
b.append('<path d="M570 360 L570 70" stroke="%s" stroke-width="6" stroke-dasharray="4 14" stroke-linecap="round"/>' % L)
b.append('<circle cx="570" cy="360" r="12" fill="%s"/>' % L)
b += [t(660, 300, 'A TRACE OF', 28, 'Plex', L, 'start'), t(660, 338, 'THE AI VOICE,', 28, 'Plex', L, 'start'),
      t(660, 376, 'STILL UNDER', 28, 'Plex', L, 'start'),
      '<path d="M652 330 L590 345" stroke="%s" stroke-width="3"/>' % L]
write('wed', 2, ''.join(b))

# 3. the studio door, the demo slides under it
b = ['<rect x="300" y="20" width="320" height="520" rx="8" fill="%s" stroke="%s" stroke-width="6"/>' % (DEEP, CREAM),
     '<rect x="340" y="60" width="240" height="190" rx="6" fill="none" stroke="%s" stroke-opacity="0.35" stroke-width="3"/>' % CREAM,
     '<rect x="340" y="290" width="240" height="210" rx="6" fill="none" stroke="%s" stroke-opacity="0.35" stroke-width="3"/>' % CREAM,
     '<rect x="372" y="120" width="176" height="64" rx="8" fill="%s"/>' % CREAM, t(460, 167, 'STUDIO', 44, 'Anton', INK),
     '<circle cx="580" cy="300" r="12" fill="%s"/>' % CREAM,
     '<rect x="566" y="320" width="28" height="34" rx="5" fill="%s"/>' % CREAM,
     '<path d="M572 320 v-12 a8 8 0 0 1 16 0 v12" stroke="%s" stroke-width="5" fill="none"/>' % CREAM,
     '<line x1="120" y1="560" x2="800" y2="560" stroke="%s" stroke-width="4"/>' % GREEN]
# phone with waveform sliding out under the door
b += ['<g transform="translate(470 520) rotate(-4)"><rect x="0" y="-8" width="300" height="56" rx="14" fill="%s"/>' % L]
for i, hh in enumerate([10, 22, 36, 18, 30, 40, 24, 14, 32, 20, 38, 16, 26, 12]):
    b.append('<rect x="%d" y="%d" width="10" height="%d" rx="5" fill="%s"/>' % (24 + i * 19, 20 - hh // 2, hh, INK))
b.append('</g>')
b += [t(660, 610, 'HER DEMO', 28, 'Plex', L)]
write('wed', 3, ''.join(b))

# 4. uploads vs listening, to scale
full = 680
b = [logo('deezer.svg', 60, 20, 220, 62),
     t(60, 160, 'NEW SONGS UPLOADED EACH DAY', 28, 'Plex', CREAM, 'start', 'fill-opacity="0.8"'),
     '<rect x="60" y="180" width="%d" height="110" rx="12" fill="%s" fill-opacity="0.12"/>' % (full, CREAM),
     '<rect x="60" y="180" width="%d" height="110" rx="12" fill="%s"/>' % (int(full * 0.52), L),
     t(60 + int(full * 0.52) + 24, 258, '50%+ AI', 56, 'Anton', L, 'start'),
     t(60, 400, 'WHAT PEOPLE LISTEN TO', 28, 'Plex', CREAM, 'start', 'fill-opacity="0.8"'),
     '<rect x="60" y="420" width="%d" height="110" rx="12" fill="%s" fill-opacity="0.12"/>' % (full, CREAM),
     '<rect x="60" y="420" width="%d" height="110" rx="4" fill="%s"/>' % (int(full * 0.03), L),
     t(60 + int(full * 0.03) + 24, 498, '1 TO 3% AI', 56, 'Anton', L, 'start')]
write('wed', 4, ''.join(b))

# 5. the deck in three layers
b = []
for i, (lab, fill, ink) in enumerate([('FINISHED BY PEOPLE', MINT, INK), ('AI DRAFT', L, INK), ('IDEA', CREAM, INK)]):
    x, y = 150 + i * 70, 60 + i * 120
    b.append('<rect x="%d" y="%d" width="560" height="320" rx="16" fill="%s" stroke="%s" stroke-width="4"/>' % (x, y, fill, INK))
    b.append(t(x + 40, y + 70, lab, 46, 'Anton', ink, 'start'))
    for j in range(3):
        b.append('<rect x="%d" y="%d" width="%d" height="16" rx="8" fill="%s" fill-opacity="0.25"/>' % (x + 40, y + 120 + j * 40, 420 - j * 90, INK))
write('wed', 5, ''.join(b))

# 6. three questions on a form
b = ['<rect x="80" y="20" width="760" height="580" rx="24" fill="%s"/>' % CREAM,
     '<rect x="80" y="20" width="760" height="20" rx="10" fill="%s"/>' % L]
for i, q in enumerate(['WHOSE IDEA?', 'DRAFTED BY?', 'CHECKED AND SIGNED BY?']):
    y = 160 + i * 150
    b.append(t(130, y, q, 52, 'Anton', INK, 'start'))
    b.append('<line x1="130" y1="%d" x2="790" y2="%d" stroke="%s" stroke-width="4" stroke-opacity="0.35" stroke-dasharray="2 12" stroke-linecap="round"/>' % (y + 60, y + 60, INK))
write('wed', 6, ''.join(b))

# 7. (last) the filled sign-off
b = ['<rect x="210" y="10" width="500" height="490" rx="22" fill="%s"/>' % CREAM,
     '<rect x="210" y="10" width="500" height="18" rx="9" fill="%s"/>' % L]
for i, (q, w) in enumerate([('IDEA', 'M380 0 c20 -18 40 18 60 0 s40 -18 60 0 s30 14 50 0'),
                            ('DRAFT', 'M380 0 c14 -14 30 14 44 0 s28 -14 44 0 s34 16 60 0'),
                            ('SIGNED', 'M380 0 c10 -30 30 26 46 -6 s22 -22 40 4 s30 10 70 -8')]):
    y = 130 + i * 130
    b.append(t(250, y, q, 40, 'Anton', INK, 'start'))
    b.append('<path d="%s" transform="translate(-10 %d)" stroke="%s" stroke-width="5" fill="none" stroke-linecap="round"/>' % (w, y - 12, INK))
    b.append('<line x1="370" y1="%d" x2="660" y2="%d" stroke="%s" stroke-opacity="0.25" stroke-width="3"/>' % (y + 14, y + 14, INK))
b.append('<circle cx="640" cy="440" r="40" fill="%s"/><path d="M620 440 L636 456 L664 424" stroke="%s" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % (MINT, INK))
write('wed', 7, ''.join(b), 520)

# ---------------- fri: mind.the.gap (coral) ----------------
C = SER['fri']
# 2. the leaderboard
b = ['<rect x="40" y="20" width="840" height="580" rx="24" fill="%s" stroke="%s" stroke-opacity="0.3" stroke-width="2"/>' % (DEEP, CREAM),
     logo('meta-cream.svg', 80, 50, 150, 64), logo('amazon-cream.svg', 250, 46, 72, 72),
     t(840, 98, 'AI USE LEADERBOARD', 28, 'Plex', CREAM, 'end', 'fill-opacity="0.7"')]
rows = [('TOKEN LEGEND', 1.18, C), ('CACHE WIZARD', 0.62, CREAM), ('', 0.40, CREAM)]
for i, (name, w, fill) in enumerate(rows):
    y = 160 + i * 110
    b.append(t(80, y + 56, str(i + 1), 52, 'Anton', fill, 'start'))
    b.append('<rect x="140" y="%d" width="%d" height="76" rx="12" fill="%s" fill-opacity="%s"/>' % (y, int(620 * w), fill, 1 if i == 0 else 0.25))
    if name:
        b.append(t(170, y + 54, name, 40, 'Anton', INK if i == 0 else CREAM, 'start'))
b += ['<rect x="80" y="490" width="760" height="80" rx="14" fill="%s" fill-opacity="0.08"/>' % CREAM,
      t(110, 545, 'TOKENS IN 30 DAYS', 30, 'Plex', CREAM, 'start', 'fill-opacity="0.8"'),
      t(810, 550, '60 TRILLION', 50, 'Anton', C, 'end')]
write('fri', 2, ''.join(b))

# 3. a cent a tail, and the rat that walked away
b = ['<line x1="40" y1="520" x2="880" y2="520" stroke="%s" stroke-width="4"/>' % GREEN,
     t(140, 120, '1902, HANOI', 34, 'Plex', CREAM, 'start', 'fill-opacity="0.7"'),
     # coin
     '<circle cx="220" cy="300" r="96" fill="%s"/><circle cx="220" cy="300" r="78" fill="none" stroke="%s" stroke-width="4" stroke-opacity="0.5"/>' % (C, INK),
     t(220, 330, '1¢', 86, 'Anton', INK),
     t(220, 450, 'PER TAIL', 34, 'Anton', CREAM)]
for i in range(7):  # bundle of tails
    b.append('<path d="M400 %d q60 -40 120 -10 t110 -20" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round"/>' % (440 + i * 9, CREAM))
b.append('<rect x="452" y="418" width="16" height="80" rx="4" fill="%s"/>' % C)
# rat with no tail, walking right
b += ['<g transform="translate(700 470)" fill="%s"><ellipse cx="0" cy="0" rx="90" ry="48"/><ellipse cx="86" cy="-18" rx="40" ry="30"/>' % CREAM,
      '<circle cx="78" cy="-50" r="18"/><circle cx="104" cy="-22" r="5" fill="%s"/>' % INK,
      '<rect x="-56" y="34" width="16" height="22" rx="6"/><rect x="40" y="34" width="16" height="22" rx="6"/></g>',
      '<path d="M606 462 l-14 0" stroke="%s" stroke-width="6" stroke-linecap="round"/>' % C,
      t(700, 580, 'NO TAIL, STILL BREEDING', 26, 'Plex', C)]
write('fri', 3, ''.join(b))

# 4. queries down, sales up
b = ['<line x1="80" y1="520" x2="840" y2="520" stroke="%s" stroke-width="4"/>' % GREEN,
     '<rect x="140" y="140" width="220" height="380" rx="10" fill="%s" fill-opacity="0.18"/>' % CREAM,
     '<rect x="140" y="254" width="220" height="266" rx="10" fill="%s"/>' % CREAM,
     t(250, 116, 'AI QUERIES', 36, 'Anton', CREAM),
     '<path d="M250 160 L250 230 M228 208 L250 232 L272 208" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % INK,
     t(250, 580, 'ABOUT -30%', 40, 'Anton', CREAM)]
for i in range(4):
    b.append('<rect x="%d" y="%d" width="60" height="26" rx="4" fill="%s" fill-opacity="0.5" transform="rotate(%d %d %d)"/>' % (390, 150 + i * 40, CREAM, 12 + i * 8, 420, 160 + i * 40))
b += [t(470, 140, 'JUNK, GONE', 26, 'Plex', CREAM, 'start', 'fill-opacity="0.7"'),
      '<line x1="390" y1="170" x2="460" y2="300" stroke="%s" stroke-width="5"/>' % C,
      '<rect x="580" y="231" width="220" height="289" rx="10" fill="%s"/>' % C,
      '<line x1="566" y1="250" x2="814" y2="250" stroke="%s" stroke-width="4" stroke-dasharray="10 8"/>' % CREAM,
      t(822, 258, 'BEFORE', 24, 'Plex', CREAM, 'start', 'fill-opacity="0.8"'),
      t(690, 206, 'SALES', 36, 'Anton', C),
      '<path d="M690 470 L690 300 M666 324 L690 298 L714 324" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % INK,
      t(690, 580, '+7%', 56, 'Anton', C)]
write('fri', 4, ''.join(b))

# 5. three U-turns
b = []
for i, (f, w, h) in enumerate([('meta-cream.svg', 170, 74), ('amazon-cream.svg', 90, 90), ('duolingo-light.svg', 200, 48)]):
    cx = 160 + i * 300
    b.append(logo(f, cx - w // 2, 60 + (90 - h) // 2, w, h))
    b.append('<path d="M%d 480 L%d 290 A70 70 0 0 1 %d 290 L%d 400" stroke="%s" stroke-width="16" fill="none" stroke-linecap="round"/>' % (cx - 70, cx - 70, cx + 70, cx + 70, C))
    b.append('<path d="M%d 380 L%d 430 L%d 380" stroke="%s" stroke-width="16" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' % (cx + 40, cx + 70, cx + 100, C))
b += [t(460, 580, 'AI-USE SCORES', 52, 'Anton', CREAM),
      '<line x1="290" y1="562" x2="630" y2="562" stroke="%s" stroke-width="8"/>' % C]
write('fri', 5, ''.join(b))

# 6. the review form, AI usage struck out
b = ['<rect x="120" y="20" width="680" height="580" rx="24" fill="%s"/>' % CREAM,
     '<rect x="120" y="20" width="680" height="20" rx="10" fill="%s"/>' % GREEN,
     t(170, 110, 'PERFORMANCE REVIEW', 30, 'Plex', INK, 'start', 'fill-opacity="0.6"')]
for i, q in enumerate(['QUALITY OF WORK', 'RESULTS', 'AI USAGE', 'TEAMWORK']):
    y = 200 + i * 100
    b.append(t(170, y, q, 46, 'Anton', INK, 'start', '' if q != 'AI USAGE' else 'fill-opacity="0.55"'))
    b.append('<line x1="170" y1="%d" x2="750" y2="%d" stroke="%s" stroke-opacity="0.15" stroke-width="3"/>' % (y + 26, y + 26, INK))
b.append('<path d="M150 388 C320 372 520 392 770 370" stroke="%s" stroke-width="16" fill="none" stroke-linecap="round"/>' % C)
write('fri', 6, ''.join(b))

# 7. (last) the results gauge
b = ['<path d="M200 420 A260 260 0 0 1 720 420" stroke="%s" stroke-opacity="0.2" stroke-width="40" fill="none" stroke-linecap="round"/>' % CREAM,
     '<path d="M460 160 A260 260 0 0 1 720 420" stroke="%s" stroke-width="40" fill="none" stroke-linecap="round"/>' % MINT,
     '<line x1="460" y1="420" x2="640" y2="250" stroke="%s" stroke-width="14" stroke-linecap="round"/>' % MINT,
     '<circle cx="460" cy="420" r="28" fill="%s"/>' % CREAM,
     t(460, 500, 'RESULTS', 56, 'Anton', CREAM)]
write('fri', 7, ''.join(b), 520)
print('devices drawn')
