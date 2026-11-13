"""Ask content-engine's 10/10 judges about one finished derived carousel (GROWTH-HANDOFF.md). Prints the verdict."""
import hashlib, json, sys, urllib.request
day = sys.argv[1]
BASE = 'https://content-engine-flame-nu.vercel.app'
deck = json.load(open(f'{day}/deck.json'))
words = '\n\n'.join(c['headline'] + '\n' + c['line'] for c in deck['cards'])
words += '\n\n---\n' + open(f'{day}/carousel-caption.txt').read().strip()
assets = []
for n in range(1, len(deck['cards']) + 1):
    b = open(f'{day}/cards/card-{n}.png', 'rb').read()
    assets.append({'name': f'card-{n}.png', 'sha256': hashlib.sha256(b).hexdigest()})
slot = {'slot_id': f'derived-carousel-{deck["carries"][:8]}', 'format': 'carousel', 'channel': 'linkedin'}
body = {'op': 'judge', 'item': slot['slot_id'], 'format': 'carousel', 'channel': 'linkedin', 'concept_id': deck['carries'],
        'claim': deck['five_whys'][-1]['a'], 'words': words, 'assets': assets}
req = urllib.request.Request(f'{BASE}/api/board/2026-11-09/judge', data=json.dumps(body).encode(), method='POST',
                             headers={'Content-Type': 'application/json', 'Authorization': 'Bearer dummy'})
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        print(r.status, r.read().decode()[:4000])
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode()[:2000])
