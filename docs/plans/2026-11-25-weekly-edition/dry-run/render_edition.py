"""Render an edition package (content-engine-edition/1) to a plain preview page, and check it.

Dry run only: structure, real text, no v5 styling (the Library is not approved yet).
Usage: python -I render_edition.py <package.json> <out.html>
"""
import hashlib
import html
import json
import re
import sys
from urllib.parse import parse_qs, urlsplit

TAGS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
CONTENT = re.compile(r'^edition-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{1,40}$')


def words(text):
    return len(re.findall(r"[A-Za-z0-9$£%'.,-]+", text))


def check(pkg):
    problems = []
    secs = pkg['sections']
    kinds = [s['kind'] for s in secs]
    if kinds[0] != 'opener' or kinds[1] != 'contents' or kinds[-2:] != ['pass_it_on', 'close']:
        problems.append('section order')
    opener = secs[0]['text']
    if words(opener) > 60:
        problems.append(f'opener {words(opener)} words')
    pieces = [s for s in secs if s['kind'] == 'piece']
    if not 1 <= len(pieces) <= 3:
        problems.append('piece count')
    for p in pieces:
        n = words(p['summary'])
        if not 50 <= n <= 80:
            problems.append(f"{p['day']} summary {n} words")
    news = [i for s in secs if s['kind'] == 'news' for g in s['groups'] for i in g['items']]
    if not 4 <= len(news) <= 10:
        problems.append(f'news items {len(news)}')
    for i in news:
        if not i.get('source_url', '').startswith('https://') or not i.get('quote'):
            problems.append('news item without a source or quote: ' + i['text'][:40])
    links = [s.get('url') for s in secs if s.get('url')] + [s.get('video_url') for s in secs if s.get('video_url')]
    for link in links:
        q = {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}
        if not all(q.get(t) for t in TAGS) or q['utm_source'] != 'newsletter' or q['utm_medium'] != 'email' \
                or q['utm_campaign'] != 'weekly' or not CONTENT.match(q['utm_content']):
            problems.append('untagged link ' + link)
    blob = json.dumps(pkg, ensure_ascii=False)
    if '—' in blob or '–' in blob:
        problems.append('em or en dash')
    if '!' in ' '.join(s.get('text', '') + s.get('summary', '') for s in secs):
        problems.append('exclamation mark')
    if re.search(r'\bKrish\b|mind/make|\bCTRL\b', blob):
        problems.append('names Krish, mind/make or CTRL')
    return problems


def long_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return d.strftime('%A ') + str(d.day) + d.strftime(' %B %Y')


def render(pkg):
    e = html.escape
    out = [
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(pkg['name'])}, {e(pkg['edition_date'])} (dry run)</title>",
        '<style>body{margin:0;background:#eee;font:17px/1.55 Georgia,serif;color:#111}'
        '.mail{max-width:600px;margin:24px auto;background:#fff;padding:32px}'
        '.meta{font:13px/1.4 system-ui,sans-serif;color:#555;border-bottom:1px solid #ddd;padding-bottom:12px;margin-bottom:24px}'
        '.meta b{color:#111}.label{font:12px/1.3 ui-monospace,monospace;text-transform:uppercase;letter-spacing:.06em;color:#555;margin:0}'
        'h1{font:700 26px/1.2 system-ui,sans-serif;margin:0 0 4px}h2{font:700 22px/1.25 system-ui,sans-serif;margin:6px 0 10px}'
        'h3{font:700 15px/1.3 system-ui,sans-serif;margin:22px 0 6px;text-transform:uppercase;letter-spacing:.04em}'
        'section{border-top:1px solid #ddd;padding-top:22px;margin-top:26px}img{width:100%;height:auto;display:block;margin:8px 0 12px}'
        'a{color:#0b5d4b}.src{font:13px/1.4 system-ui,sans-serif;color:#555}ul.contents{padding-left:20px}'
        '.note{font:13px/1.45 system-ui,sans-serif;background:#fff8d6;border:1px solid #e6d37a;padding:10px 12px;margin-bottom:20px}'
        '</style></head><body><div class="mail">',
        '<p class="note">Dry run of edition one, for approval. Structure only: the v5 look comes from the Library '
        'template once approved. Nothing here has been sent.</p>',
        f"<div class=\"meta\">From <b>makeyourmind/up</b><br>Subject: <b>{e(pkg['subject'])}</b><br>"
        f"Preview: {e(pkg['preview_text'])}</div>",
        f"<p class=\"label\">{e(pkg['name'])}, {e(long_date(pkg['edition_date']))}</p>",
    ]
    for s in pkg['sections']:
        k = s['kind']
        if k == 'opener':
            out.append(f"<p>{e(s['text'])}</p>")
        elif k == 'contents':
            out.append('<h3>In this edition</h3><ul class="contents">' +
                       ''.join(f'<li>{e(x)}</li>' for x in s['lines']) + '</ul>')
        elif k == 'piece':
            c = s['cover']
            link = f"<a href=\"{e(s['url'])}\">Read the piece, or watch its 5-minute video</a>"
            out.append(f"<section><p class=\"label\">{e(s['label'])}</p><h2>{e(s['title'])}</h2>"
                       f"<a href=\"{e(s['url'])}\"><img src=\"{e(c['url'])}\" alt=\"{e(c['alt'])}\"></a>"
                       f"<p>{e(s['summary'])}</p><p>{link}</p></section>")
        elif k == 'news':
            out.append('<section><h2>Also this week</h2>')
            for g in s['groups']:
                out.append(f"<h3>{e(g['topic'])}</h3>")
                for i in g['items']:
                    out.append(f"<p>{e(i['text'])} <span class=\"src\">Source: "
                               f"<a href=\"{e(i['source_url'])}\">{e(i['source_name'])}</a></span></p>")
            out.append('</section>')
        elif k == 'pass_it_on':
            out.append(f"<section><h3>Pass it on</h3><p>{e(s['text'])} "
                       f"<a href=\"{e(s['url'])}\">Subscribe here</a>.</p></section>")
        elif k == 'close':
            out.append(f"<p>{e(s['text'])}</p>")
    out.append('<p class="src">Email preferences and unsubscribe: Substack adds them here.</p></div></body></html>')
    return '\n'.join(out)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, encoding='utf-8').read()
    pkg = json.loads(raw)
    canon = json.dumps(pkg, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    problems = check(pkg)
    open(dst, 'w', encoding='utf-8').write(render(pkg))
    total = sum(words(s.get('text', '') + ' ' + s.get('summary', '') + ' ' + ' '.join(s.get('lines', [])))
                for s in pkg['sections']) + sum(words(i['text']) for s in pkg['sections'] if s['kind'] == 'news'
                                                for g in s['groups'] for i in g['items'])
    print('sha256', hashlib.sha256(canon.encode('utf-8')).hexdigest())
    print('words', total)
    print('problems', problems or 'none')
