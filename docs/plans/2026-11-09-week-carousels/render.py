#!/usr/bin/env python3
"""Draw one derived carousel from its carousel-deck/1 file.

    python3 render.py mon        writes mon/cards/card-N.html, then shoot.mjs turns them into 1080 x 1350 PNGs

The words come only from <day>/deck.json (checked by content-engine's scripts/carousel_check.py first). Each card's
picture is <day>/devices/card-N.svg (built by Codex to devices/BRIEF.md); the cover's scene is <day>/devices/cover.png.
<day>/style.json holds what is not words: the series name and colour (the deck carries the piece), and which phrase
of each headline takes the accent. Brand: kit/ fonts and the official wordmark only (content-engine
config/brand-palette.json); ink, cream, mint, green and the series colour.
"""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, CREAM, MINT, GREEN = '#0C1512', '#F4EFE4', '#7EF0C0', '#2F6B5C'

CSS = """
@font-face{font-family:Anton;src:url(../../kit/Anton-Regular.ttf)}
@font-face{font-family:Archivo;src:url(../../kit/Archivo-Variable.ttf);font-weight:100 900;font-stretch:62%% 125%%}
@font-face{font-family:Plex;src:url(../../kit/IBMPlexMono-Medium.ttf);font-weight:500}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;background:%(ink)s;overflow:hidden}
.card{position:relative;width:1080px;height:1350px;background:%(ink)s;color:%(cream)s;overflow:hidden}
.glow{position:absolute;inset:0;background:radial-gradient(900px 700px at 50%% 62%%,rgba(47,107,92,.30),rgba(12,21,18,0) 70%%)}
.head{position:absolute;left:80px;right:80px;top:96px;font-family:Anton;font-size:96px;line-height:1.02;
      text-transform:uppercase;letter-spacing:.5px;color:%(cream)s}
.head .a{color:var(--accent)}
.line{position:absolute;left:80px;right:80px;font-family:Archivo;font-weight:500;font-size:36px;line-height:1.3;
      color:rgba(244,239,228,.86)}
.flow{position:absolute;left:80px;right:80px;top:96px;bottom:130px;display:flex;flex-direction:column}
.flow .head,.flow .line{position:static}
.flow .line{margin-top:26px}
.pic{flex:1;display:flex;align-items:center;justify-content:center;min-height:0;margin-top:30px}
.close .flow{bottom:270px;align-items:center}
.pic svg{display:block;width:100%%;height:100%%;max-width:920px}
.mark{position:absolute;right:72px;bottom:64px;width:210px;height:25px;background:url(../../kit/wordmark.png) no-repeat right center/contain;opacity:.9}
.cover .scene{position:absolute;left:0;top:0;width:1080px;height:1350px;object-fit:cover}
.cover .fade{position:absolute;left:0;right:0;bottom:0;height:780px;
      background:linear-gradient(to bottom,rgba(12,21,18,0) 0%%,rgba(12,21,18,.78) 30%%,rgba(12,21,18,.97) 52%%,%(ink)s 100%%)}
.cover .stack{position:absolute;left:80px;right:80px;bottom:140px;display:flex;flex-direction:column;align-items:flex-start;gap:26px}
.cover .pill{font-family:Plex;font-weight:500;font-size:26px;letter-spacing:2px;
      color:%(ink)s;background:var(--accent);padding:10px 22px;border-radius:999px}
.cover .stack .head,.cover .stack .line{position:static}
.close{text-align:center}
.close .head{text-align:center}
.close .line{text-align:center}
.close .follow{position:absolute;left:0;right:0;bottom:178px;text-align:center;font-family:Anton;font-size:64px;
      text-transform:uppercase;letter-spacing:1px;color:%(mint)s}
.close .bigmark{position:absolute;left:50%%;transform:translateX(-50%%);bottom:96px;width:420px;height:50px;
      background:url(../../kit/wordmark.png) no-repeat center/contain}
""" % {'ink': INK, 'cream': CREAM, 'mint': MINT}


def headline(text, accent, br=None):
    text = html.escape(text)
    if br and html.escape(br) in text:
        text = text.replace(html.escape(br), '<br>' + html.escape(br), 1)
    if accent:
        a = html.escape(accent)
        if a in text:
            text = text.replace(a, '<span class="a">' + a + '</span>', 1)
    return text


def svg(folder, n):
    """The card's picture, inlined so it draws in the kit's fonts and its logos load (devices/BRIEF.md)."""
    text = (folder / 'devices' / ('card-%d.svg' % n)).read_text(encoding='utf-8')
    return text[text.index('<svg'):]


def page(body, colour, title):
    return ('<!doctype html><html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head>'
            '<body style="--accent:%s">%s</body></html>' % (html.escape(title), CSS, colour, body))


def main(day):
    folder = HERE / day
    deck = json.loads((folder / 'deck.json').read_text(encoding='utf-8'))
    style = json.loads((folder / 'style.json').read_text(encoding='utf-8'))
    colour, accents = style['colour'], style.get('accent', {})
    lay = style.get('layout', {})
    cards = deck['cards']
    out = folder / 'cards'
    out.mkdir(exist_ok=True)
    for n, card in enumerate(cards, 1):
        acc = accents.get(str(n))
        L = lay.get(str(n), {})
        if n == 1:
            body = ('<div class="card cover"><img class="scene" src="../devices/cover.png"><div class="fade"></div>'
                    '<div class="stack"><div class="pill">%s</div><div class="head" style="font-size:%dpx">%s</div><div class="line">%s</div></div>'
                    '<div class="mark"></div></div>') % (html.escape(style['series_name']), L.get('size', 108), headline(card['headline'], acc, style.get('br', {}).get(str(n))),
                                                         html.escape(card['line']))
        elif n == len(cards):
            line = card['line'].replace('Follow for more.', '').strip()
            body = ('<div class="card close"><div class="glow"></div><div class="flow"><div class="head" style="font-size:%dpx">%s</div>'
                    '<div class="line">%s</div><div class="pic">%s</div></div>'
                    '<div class="follow">Follow for more</div><div class="bigmark"></div></div>') % (
                L.get('size', 96), headline(card['headline'], acc, style.get('br', {}).get(str(n))), html.escape(line), svg(folder, n))
        else:
            body = ('<div class="card"><div class="glow"></div><div class="flow"><div class="head" style="font-size:%dpx">%s</div>'
                    '<div class="line">%s</div><div class="pic">%s</div></div><div class="mark"></div></div>') % (
                L.get('size', 96), headline(card['headline'], acc, style.get('br', {}).get(str(n))), html.escape(card['line']), svg(folder, n))
        (out / ('card-%d.html' % n)).write_text(page(body, colour, '%s card %d' % (day, n)), encoding='utf-8')
    print('%s: %d cards written to %s' % (day, len(cards), out))


if __name__ == '__main__':
    main(sys.argv[1])
