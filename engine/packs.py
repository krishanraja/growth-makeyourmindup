"""A versioned evidence envelope and an explicit legacy API projection.

The linter verifies provenance structure and literal excerpts, not the truth of
a paraphrase. A human must still compare each claim with its cited source.
"""
import datetime as dt
import re
import unicodedata
from urllib.parse import parse_qsl, urlsplit

from .core import KINDS, OWN_HOSTS, PLATFORMS, calendar_date, canonical, http_url, identity, instant

EM_DASH = re.compile('\u2014')
PERCENT = re.compile(r'\d\s*%|\bper ?cent\b', re.I)
SLOP = ('delve', "in today's", 'in a world where', "it's worth noting", 'navigate', 'landscape',
        'game-changer', 'game changer', 'seamless', 'unlock', 'harness', 'leverage', 'robust',
        'crucial', 'pivotal', 'moreover', 'furthermore', "here's the thing", 'the reality is',
        'at the end of the day', 'a testament to', 'tapestry', 'realm', 'ever-evolving',
        'cutting-edge', 'revolutionize', 'revolutionise', 'transformative', 'paradigm', 'synergy',
        'buckle up', "let's dive", 'deep dive', 'a new era', 'make no mistake', 'let that sink in',
        'unpopular opinion', 'thoughts?', 'agree?')
NOT_BUT = re.compile(r"\b(?:it'?s|this is|that'?s)\s+not\s+[^.;:!?]{1,60}[,;]\s*(?:it'?s|but)\b"
                     r"|\bisn'?t\s+(?:just|only)\b", re.I)
URL = re.compile(r'https?://[^\s<>\]\["\']+', re.I)
ACTING = {'send', 'post', 'publish', 'schedule', 'send_at', 'post_at', 'publish_at', 'scheduled_at', 'auto_post'}
ITEM_WIRE = ('platform', 'target_url', 'target_name', 'why', 'text', 'status')
NUMBER_WIRE = ('platform', 'followers', 'new_this_week', 'reach', 'visits', 'new_free', 'new_paid', 'unsubscribes', 'top_source', 'note')


def x_weight(text):
    # X's URL weight is 23. Unicode v3 ranges are one unit; other codepoints
    # two. Counting joined emoji separately is deliberately conservative.
    # This is not a full twitter-text implementation; preview complex emoji
    # and unusual URLs in the native client before posting.
    text = unicodedata.normalize('NFC', text)
    urls = list(URL.finditer(text))
    plain = URL.sub(lambda m: m.group()[len(m.group().rstrip('.,;!?)')):], text)
    return 23 * len(urls) + sum(1 if ord(c) <= 0x10ff or 0x2000 <= ord(c) <= 0x200d
                               or 0x2010 <= ord(c) <= 0x201f or 0x2032 <= ord(c) <= 0x2037 else 2 for c in plain)


def prose_errors(text):
    out = []
    # Percent-encoded URLs aren't percentages in prose.
    prose = URL.sub('', text)
    if EM_DASH.search(prose):
        out.append('has an em dash')
    if PERCENT.search(prose):
        out.append('has a percentage')
    for phrase in SLOP:
        if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', prose, re.I):
            out.append('uses stock phrase "' + phrase + '"')
    if NOT_BUT.search(prose):
        out.append('uses the "it\'s not X, it\'s Y" turn')
    return out


def problems(item, kind=None):
    if not isinstance(item, dict):
        return ['must be an object']
    errors = []
    text = item.get('text')
    if not isinstance(text, str) or not text.strip():
        return ['has no text']
    if item.get('platform') not in PLATFORMS:
        errors.append('unknown platform')
    errors += prose_errors(text)
    if len(text.encode('utf-16-le')) // 2 > 4000:
        errors.append('exceeds the API limit of 4000 UTF-16 units')
    if item.get('platform') == 'x':
        for i, part in enumerate(re.split(r'\n\s*\n', text.strip()), 1):
            if x_weight(part) > 280:
                errors.append('X post ' + str(i) + ' exceeds 280 weighted characters')
    limit = {'linkedin': 3000, 'reddit': 1500}.get(item.get('platform'))
    if limit and len(text) > limit:
        errors.append('exceeds the platform text limit')
    if item.get('platform') == 'linkedin' and (item.get('kind_hint') == 'comment' or kind == 'radar') and URL.search(text):
        errors.append('a LinkedIn comment must have no links')
    if kind == 'radar' and len(text.split()) > 60:
        errors.append('a radar reply must be at most 60 words')
    for field in ('target_url',):
        if item.get(field) is not None and not http_url(item[field]):
            errors.append(field + ' must be an http or https URL')
    for field in ('target_name', 'why'):
        if item.get(field) is not None:
            if not isinstance(item[field], str) or len(item[field].encode('utf-16-le')) // 2 > 4000:
                errors.append(field + ' must be text within 4000 UTF-16 units')
            else:
                errors += [field + ' ' + e for e in prose_errors(item[field])]
    if item.get('status') not in (None, 'posted', 'skipped', 'draft'):
        errors.append('unknown item status')
    if ACTING.intersection(item):
        errors.append('acting keys are forbidden')
    for match in URL.finditer(text):
        url = match.group().rstrip('.,;!?)')
        if not http_url(url):
            errors.append('invalid URL in draft')
            continue
        u = urlsplit(url)
        if u.hostname in OWN_HOSTS and not re.match(r'^/(publish(?:/|$)|settings(?:/|$)|account(?:/|$))', u.path):
            pairs = parse_qsl(u.query, keep_blank_values=True)
            tags = dict(pairs)
            if any(sum(k == key for k, _ in pairs) != 1 or not tags.get(key)
                   for key in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')):
                errors.append('own link is not tracked with four unique complete UTM tags')
            elif tags['utm_source'] != item.get('platform') or tags['utm_medium'] != 'organic' or tags['utm_campaign'] != 'growth':
                errors.append('own link tracking does not match this platform and engine')
    return errors


def check_pack(pack):
    if not isinstance(pack, dict):
        return ['pack must be an object']
    errors = []
    if pack.get('kind') not in KINDS:
        errors.append('unknown kind')
    try:
        calendar_date(pack.get('pack_date'))
    except (ValueError, TypeError):
        errors.append('pack_date must be a real YYYY-MM-DD date')
    head = pack.get('headline')
    if not isinstance(head, str) or not head.strip() or len(head.encode('utf-16-le')) // 2 > 500:
        errors.append('headline must be nonempty and within 500 UTF-16 units')
    else:
        errors += ['headline ' + p for p in prose_errors(head)]
    if pack.get('link') is not None and not http_url(pack['link']):
        errors.append('link must be an http or https URL')
    if ACTING.intersection(pack):
        errors.append('acting keys are forbidden')
    items = pack.get('items', [])
    if not isinstance(items, list) or len(items) > 40:
        errors.append('items must be a list of at most 40 drafts')
    else:
        for i, item in enumerate(items, 1):
            errors += ['draft ' + str(i) + ': ' + e for e in problems(item, pack.get('kind'))]
    numbers = pack.get('numbers')
    if numbers is not None:
        if pack.get('kind') != 'numbers' or not isinstance(numbers, list) or len(numbers) > 40:
            errors.append('numbers must be a list of at most 40 rows, only in a numbers pack')
        else:
            import math
            for i, row in enumerate(numbers):
                if not isinstance(row, dict):
                    errors.append('number row must be an object')
                    continue
                if row.get('platform') not in PLATFORMS or 'followers' not in row:
                    errors.append('number row needs platform and followers (null if unavailable)')
                for field in NUMBER_WIRE[1:8]:
                    value = row.get(field)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                              or not math.isfinite(value) or (value < 0 and field != 'new_this_week')):
                        errors.append('invalid number field ' + field)
                for field in ('note', 'top_source'):
                    if row.get(field) is not None and not isinstance(row[field], str):
                        errors.append(field + ' must be text')
                    elif isinstance(row.get(field), str):
                        if len(row[field].encode('utf-16-le')) // 2 > 4000:
                            errors.append(field + ' exceeds 4000 UTF-16 units')
                        errors += [field + ' ' + e for e in prose_errors(row[field])]
    return errors


def seal(pack, evidence, metadata, now=None, observations=None):
    """Attach reviewable sources. Never creates unsupported publication copy."""
    errors = check_pack(pack)
    if errors:
        raise ValueError('; '.join(errors))
    if len(metadata) != len(pack.get('items', [])):
        raise ValueError('one metadata record is required for each draft')
    observations = observations or []
    from .operations import validate_observation
    for observation in observations:
        validate_observation(observation)
        if instant(observation['captured_at']) > instant(now):
            raise ValueError('measurement capture cannot be in the future')
    for number in pack.get('numbers') or []:
        if number.get('new_this_week') is not None:
            raise ValueError('v2 daily numbers must not mix rolling weekly counts into daily rows')
        if not number.get('note'):
            raise ValueError('numbers rows need source, window and availability in note')
        for metric in ('followers', 'reach', 'visits', 'new_free', 'new_paid', 'unsubscribes'):
            value = number.get(metric)
            metric_names = ('followers', 'subscribers') if metric == 'followers' else (metric,)
            if value is not None and not any(r['platform'] == number['platform'] and r['metric'] in metric_names
                                             and r['value'] == value for r in observations):
                raise ValueError('number has no matching structured observation: ' + metric)
    evidence_map = {}
    for source in evidence:
        if not isinstance(source, dict) or source.get('kind') not in ('published_piece', 'source_thread', 'dashboard', 'audit', 'policy'):
            raise ValueError('unknown evidence kind')
        if not http_url(source.get('url')) or not source.get('excerpt') or not isinstance(source['excerpt'], str):
            raise ValueError('evidence needs source URL and literal excerpt')
        instant(source['observed_at'])
        if instant(source['observed_at']) > instant(now):
            raise ValueError('evidence cannot be observed in the future')
        if source['kind'] == 'source_thread':
            if not source.get('created_at') or instant(source['created_at']) > instant(source['observed_at']):
                raise ValueError('thread evidence needs a real creation time no later than observation')
        uid = source.get('evidence_id')
        expected = identity('evidence', canonical(source['url']), source['excerpt'])
        if uid != expected or uid in evidence_map:
            raise ValueError('invalid or duplicate evidence_id; derive it from URL and excerpt')
        if source.get('snapshot') is not None and source['excerpt'] not in source['snapshot']:
            raise ValueError('literal excerpt is absent from source snapshot')
        evidence_map[uid] = source
    stamped = []
    for index, (item, meta) in enumerate(zip(pack.get('items', []), metadata)):
        required = ('asset_id', 'placement', 'variant', 'evidence_ids', 'priority', 'minutes', 'why_now', 'success_check')
        if any(not meta.get(key) for key in required):
            raise ValueError('draft ' + str(index + 1) + ' needs identity, evidence, priority, time, why now and success check')
        if any(not isinstance(meta[key], str) or not meta[key].strip() for key in ('asset_id', 'placement', 'variant', 'why_now', 'success_check')):
            raise ValueError('identity and review fields must be text')
        refs = meta['evidence_ids']
        if not isinstance(refs, list) or not refs or any(ref not in evidence_map for ref in refs):
            raise ValueError('draft references missing evidence')
        if pack['kind'] in ('daily', 'radar', 'partners', 'pitches', 'swaps') and not any(
                evidence_map[ref]['kind'] in ('published_piece', 'source_thread') for ref in refs):
            raise ValueError('publication and outreach drafts need a published piece or source thread')
        if pack['kind'] == 'radar' and (not meta.get('expires_at') or not any(evidence_map[ref]['kind'] == 'source_thread' for ref in refs)):
            raise ValueError('radar needs thread evidence and an expiry')
        if pack['kind'] == 'radar':
            threads = [evidence_map[ref] for ref in refs if evidence_map[ref]['kind'] == 'source_thread']
            if any(instant(meta['expires_at']) > instant(source['created_at']) + dt.timedelta(hours=12) for source in threads):
                raise ValueError('radar expires no later than 12 hours after thread creation')
        for quote in meta.get('quotes', []):
            if not isinstance(quote, str) or not any(quote in evidence_map[ref]['excerpt'] for ref in refs):
                raise ValueError('quoted text is absent from cited excerpts')
        if meta.get('expires_at'):
            instant(meta['expires_at'])
        for match in URL.finditer(item['text']):
            url = match.group().rstrip('.,;!?)')
            parsed = urlsplit(url)
            if parsed.hostname in OWN_HOSTS and not re.match(r'^/(publish(?:/|$)|settings(?:/|$)|account(?:/|$))', parsed.path):
                expected = identity('placement', meta['asset_id'], item['platform'], meta['placement'], meta['variant'])
                if dict(parse_qsl(parsed.query)).get('utm_content') != expected:
                    raise ValueError('v2 own link needs matching asset/placement/variant tracking')
        uid = identity('item', meta['asset_id'], item['platform'], meta['placement'], meta['variant'])
        stamped.append({**meta, 'item_id': uid, 'revision_id': identity('copy', item['text']),
                        'status': item.get('status') or 'draft'})
    if len({m['item_id'] for m in stamped}) != len(stamped):
        raise ValueError('duplicate asset/platform/placement/variant identity')
    from .operations import daily_queue
    daily_queue(stamped, now)  # Validates estimates and priorities, including empty packs.
    return {'schema_version': 2, 'prepared_at': instant(now).isoformat(), 'pack': pack,
            'evidence': evidence, 'metadata': stamped, 'observations': observations,
            'review_notice': 'Provenance checks do not prove paraphrase accuracy. Compare every claim with the cited excerpt. Krish publishes.'}


def validate_envelope(envelope, now=None):
    if not isinstance(envelope, dict) or envelope.get('schema_version') != 2:
        raise ValueError('expected an evidence envelope with schema_version 2')
    prepared_at = instant(envelope.get('prepared_at')) if envelope.get('prepared_at') else None
    if prepared_at is None or prepared_at > instant(now):
        raise ValueError('invalid preparation timestamp')
    sealed = seal(envelope['pack'], envelope['evidence'], envelope['metadata'], now, envelope.get('observations'))
    for old, new in zip(envelope['metadata'], sealed['metadata']):
        if old.get('item_id') != new['item_id'] or old.get('revision_id') != new['revision_id']:
            raise ValueError('item identity or copy changed; prepare again')
    return envelope


def wire_pack(envelope, now=None):
    validate_envelope(envelope, now)
    pack = envelope['pack']
    # New fields never silently travel to an API that discards them. Full
    # provenance stays in the local envelope until the CC handoff is built.
    items = []
    for item in pack.get('items', []):
        projected = {k: item[k] for k in ITEM_WIRE if k in item and item[k] is not None and k != 'status'}
        if EM_DASH.search(projected['text']) or PERCENT.search(projected['text']):
            raise ValueError('legacy API house rule also scans URLs; this encoded URL cannot be delivered unchanged')
        # Agent delivery never asserts that Krish posted or skipped a draft.
        items.append(projected)
    numbers = pack.get('numbers')
    if PERCENT.search(pack['headline']) or EM_DASH.search(pack['headline']):
        raise ValueError('headline fails the legacy API house rule')
    return {'pack_date': pack['pack_date'], 'kind': pack['kind'], 'headline': pack['headline'],
            'items': items, 'numbers': [{k: r[k] for k in NUMBER_WIRE if k in r} for r in numbers] if numbers is not None else None,
            'link': pack.get('link'), 'source': 'codex'}
