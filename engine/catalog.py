"""RSS snapshots and recovery without guessing an article/video pairing."""
import datetime as dt
import email.utils
import html
from html.parser import HTMLParser
import re
import urllib.request
import xml.etree.ElementTree as ET

from .core import canonical, http_url, identity, instant, ny_time, today

FEED = 'https://home.makeyourmindup.ai/feed'


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if not self.hidden and tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in ('p', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'div'):
            self.parts.append('\n\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def strip_html(value):
    parser = PlainText()
    parser.feed(value or '')
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', ''.join(parser.parts))).strip()


def parse_feed(data, days=21, now=None):
    if not isinstance(days, int) or not 1 <= days <= 366:
        raise ValueError('days must be between 1 and 366')
    now = instant(now)
    cutoff = now - dt.timedelta(days=days)
    if len(data) > 8_000_000:
        raise ValueError('feed exceeds the 8 MB read limit')
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise ValueError('feed is not valid RSS XML; no catalog state was changed') from None
    out = {}
    for item in root.iter('item'):
        try:
            when = instant(email.utils.parsedate_to_datetime(item.findtext('pubDate')))
        except (TypeError, ValueError):
            continue
        url = item.findtext('link')
        if not http_url(url) or not cutoff <= when <= now:
            continue
        url = canonical(url)
        title = html.unescape(item.findtext('title') or '').strip()
        body = item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or ''
        text = strip_html(body)
        links = sorted({canonical(html.unescape(link)) for link in
                        re.findall(r'href=[\'"]([^\'"]+)[\'"]', body, re.I) if http_url(html.unescape(link))})
        uid = identity('piece', url)
        row = {'piece_id': uid, 'date': ny_time(when).date().isoformat(), 'published_at': when.isoformat(),
               'title': title, 'url': url, 'kind': 'video post' if title.upper().startswith('VIDEO:') else 'article',
               'subtitle': strip_html(item.findtext('description') or ''), 'text': text, 'links': links,
               'revision': identity('revision', title, text), 'observed_at': now.isoformat(),
               'evidence_status': 'available' if text else 'body_missing'}
        # RSS may repeat an item. A duplicate must not create another task.
        out[uid] = row
    return sorted(out.values(), key=lambda x: (x['published_at'], x['piece_id']), reverse=True)


def pieces(days=21, now=None):
    request = urllib.request.Request(FEED, headers={'User-Agent': 'growth-makeyourmindup/2 (read-only)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_feed(response.read(8_000_001), days, now)


def discover(rows, previous=None, now=None):
    now = instant(now)
    previous = previous or {'schema_version': 2, 'pieces': {}}
    if previous.get('schema_version') != 2 or not isinstance(previous.get('pieces'), dict):
        raise ValueError('unsupported catalog state')
    entries = dict(previous['pieces'])
    changes, pairs = [], []
    for row in rows:
        old = entries.get(row['piece_id'])
        reason = 'new' if not old else ('revised' if old['revision'] != row['revision'] else None)
        if reason:
            changes.append({'piece_id': row['piece_id'], 'reason': reason,
                            'late': row['date'] < today(now), 'body_status': row['evidence_status']})
        entries[row['piece_id']] = {**row, 'first_seen_at': old['first_seen_at'] if old else now.isoformat()}
    all_rows = list(entries.values())
    for article in (r for r in all_rows if r['kind'] == 'article'):
        candidates = [r for r in all_rows if r['kind'] == 'video post' and
                      (r['url'] in article['links'] or article['url'] in r['links'])]
        if len(candidates) == 1:
            pairs.append({'article_id': article['piece_id'], 'video_id': candidates[0]['piece_id'],
                          'basis': 'explicit_published_link'})
    # Similar titles are suggestions for a human, never enough to merge IDs.
    pending = [{'piece_id': row['piece_id'], 'action': 'read published page; do not invent missing video facts'}
               for row in rows if not row['text']]
    return {'schema_version': 2, 'observed_at': now.isoformat(), 'pieces': entries,
            'changes': changes, 'verified_pairs': pairs, 'pending': pending,
            'recovery': 'Unchanged missing bodies remain pending on each scan. Retry at the next existing job; no extra automation. Feed pagination/older archive discovery needs a human read.'}
