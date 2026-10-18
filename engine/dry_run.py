"""Repeatable local acceptance flow. No Control Centre or social writes."""
from pathlib import Path

from .catalog import discover, parse_feed, pieces
from .core import identity, instant, today, tracked, write_json
from .operations import daily_queue, relationship
from .packs import seal, wire_pack


def run(root, out, live=False):
    out = Path(out)
    now = instant() if live else instant('2026-10-17T18:00:00Z')
    rows = pieces(30, now) if live else parse_feed((root / 'tests/fixtures/feed.xml').read_bytes(), 30, now)
    catalog = discover(rows, now=now)
    replay = discover(rows, catalog, now)
    if replay['changes']:
        raise ValueError('discovery replay was not idempotent')
    readable = [row for row in rows if row['text']]
    if not readable:
        raise ValueError('no published body available: cannot prepare evidence')
    row = readable[0]
    excerpt = row['text'][:300]
    evidence = [{'evidence_id': identity('evidence', row['url'], excerpt), 'kind': 'published_piece',
                 'url': row['url'], 'excerpt': excerpt, 'snapshot': row['text'], 'observed_at': now.isoformat()}]
    asset = row['piece_id']
    # This is a source-review card, not a pretend social campaign. No invented
    # source claims or automated creative generation in the acceptance flow.
    text = 'Read the published source before choosing a draft.\n' + tracked(row['url'], 'other', 'report', today(now), asset, 'source-review')
    pack = {'pack_date': today(now), 'kind': 'report', 'headline': 'Source review dry run',
            'items': [{'platform': 'other', 'text': text, 'target_url': row['url']}], 'numbers': None}
    metadata = [{'asset_id': asset, 'placement': 'source-review', 'variant': 'a',
                 'evidence_ids': [evidence[0]['evidence_id']], 'priority': 1, 'minutes': 2,
                 'why_now': 'Check source availability before drafting.',
                 'success_check': 'The source is readable and each future claim can be cited.'}]
    envelope = seal(pack, evidence, metadata, now)
    wire = wire_pack(envelope, now)
    queue = daily_queue([{**item, **meta} for item, meta in zip(pack['items'], envelope['metadata'])], now)
    draft = {'event_id': 'fixture-draft', 'person_id': 'fixture-only', 'type': 'drafted', 'at': now.isoformat()}
    untouched = relationship([draft], 'fixture-only', now)
    if untouched['state'] != 'uncontacted' or not untouched['eligible']:
        raise ValueError('draft incorrectly advanced outreach state')
    for name, value in (('catalog', catalog), ('envelope', envelope), ('legacy-pack', wire), ('queue', queue)):
        write_json(out / (name + '.json'), value)
    result = {'mode': 'public-feed-read-only' if live else 'offline-fixture', 'completed_at': now.isoformat(),
              'pieces_seen': len(rows), 'readable_bodies': len(readable), 'missing_bodies': len(rows) - len(readable),
              'verified_pairs': len(catalog['verified_pairs']), 'replay_new_tasks': len(replay['changes']),
              'draft_did_not_advance_outreach': True, 'schema_version': 2,
              'legacy_projection_valid': True, 'queue_minutes': queue['estimated_minutes'],
              'external_writes': 0, 'out': str(out),
              'limitations': ['Social dashboards not exercised.', 'Control Centre delivery deliberately not exercised.',
                              'Provenance does not prove the accuracy of future paraphrases.',
                              'No social copy or campaign was published.']}
    write_json(out / 'result.json', result)
    return result
