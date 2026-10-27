#!/usr/bin/env python3
"""Read published evidence, prepare growth drafts and plan a daily work queue.

Python 3.9+, standard library only. Development and dry runs need no token.
Control Centre delivery is a separate explicit --deliver action. Social
publication, outreach, settings changes and paid work remain Krish's actions.
See README.md and docs/ENGINE.md for the versioned envelope and commands, and
docs/ENGINE.md "Reporting to Control Center" for the `cc` protocol loop.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

from engine.catalog import FEED, discover, pieces, parse_feed, strip_html
from engine.cc_loop import CONTROL_CENTER_OWNS
from engine.control_center import APPROVED_ORIGIN, Client, NoRedirect, ProtocolError, opener
from engine.core import (KINDS, PLATFORMS, http_url, identity, instant, locked,
                         read_json, today, tracked, write_json)
from engine.operations import (aggregate, daily_queue, experiment_decision,
                               relationship, validate_observation, yield_per_thousand)
from engine.packs import check_pack, problems, seal, validate_envelope, wire_pack

ROOT = Path(__file__).resolve().parent
BASE = os.environ.get('CONTROL_CENTER_URL', 'https://controlcenter.krishraja.com').rstrip('/')
TOKEN_FILE = Path.home() / '.config' / 'growth-makeyourmindup' / 'token'
# The protocol bearer (gen1_) is a different key from the packs key above.
ENGINE_TOKEN_FILE = TOKEN_FILE.parent / 'engine-token'
# Control Center's People and Visibility own outreach to shows and guests
# (Krish, 21 Oct 2026; AGENTS.md "Outreach belongs to Control Center"). These
# packs never leave here.
OUTREACH = CONTROL_CENTER_OWNS  # one source: pitches, partners and swaps
OUTREACH_HELD = ("Control Center's People and Visibility own outreach to shows and guests; "
                 'pitches, partners and swaps packs are never delivered from this engine')


def outreach_kind(value):
    """The pack kind of an envelope, legacy pack or wire body when it is outreach."""
    if not isinstance(value, dict):
        return None
    pack = value.get('pack') if isinstance(value.get('pack'), dict) else value
    kind = pack.get('kind')
    return kind if isinstance(kind, str) and kind in OUTREACH else None


def token():
    value = os.environ.get('GROWTH_ENGINE_TOKEN', '').strip()
    if not value and TOKEN_FILE.exists():
        value = TOKEN_FILE.read_text(encoding='utf-8-sig').strip()
    return value


def engine_token():
    value = os.environ.get('CONTROL_CENTER_ENGINE_TOKEN', '').strip()
    if not value and ENGINE_TOKEN_FILE.exists():
        value = ENGINE_TOKEN_FILE.read_text(encoding='utf-8-sig').strip()
    return value


def engine_client():
    key = engine_token()
    if not key:
        raise ValueError('No Control Center engine key: set CONTROL_CENTER_ENGINE_TOKEN or the engine-token file. '
                         'Do not rotate or print it. See docs/KEY.md.')
    return Client(key, os.environ.get('CONTROL_CENTER_URL', '').strip() or APPROVED_ORIGIN)


def call(method, path, body=None, deliver=False):
    if BASE != APPROVED_ORIGIN:
        raise ValueError('CONTROL_CENTER_URL must be the approved HTTPS Control Centre origin')
    if method not in ('GET', 'POST') or path.partition('?')[0] != '/api/growth/packs':
        raise ValueError('only the supported packs endpoint is allowed')
    if method == 'POST' and (not deliver or path != '/api/growth/packs'):
        raise ValueError('Control Centre writes require explicit --deliver')
    if method == 'POST' and outreach_kind(body):
        raise ValueError(OUTREACH_HELD)
    key = token()
    if not key:
        raise ValueError('No Control Centre key: use the existing configured GROWTH_ENGINE_TOKEN or token file. Do not rotate or print it. See docs/KEY.md.')
    data = json.dumps(body, allow_nan=False).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with opener().open(req, timeout=30) as response:
            result = json.loads(response.read(4_000_000))
        if not isinstance(result, dict) or result.get('ok') is not True:
            raise ValueError('Control Centre did not confirm success')
        return result
    except urllib.error.HTTPError as error:
        # Never echo remote bodies: an upstream failure can include secrets.
        raise ValueError('Control Centre returned HTTP ' + str(error.code)) from None
    except urllib.error.URLError:
        raise ValueError('Could not reach Control Centre; no successful delivery confirmed') from None
    except ProtocolError:
        raise ValueError('Control Centre redirected the request; delivery stopped') from None


def doctor(offline=False):
    errors = []
    if sys.version_info < (3, 9):
        errors.append('Python 3.9 or newer required')
    try:
        config = read_json(ROOT / 'automations.json')
        if config['timezone'] != 'America/New_York' or len(config['automations']) != 9:
            errors.append('expected nine New York automations')
        if any(not (ROOT / entry['job']).is_file() for entry in config['automations']):
            errors.append('automation job file missing')
        for name in ('channels.json', 'journeys.json', 'experiments.json', 'hooks.json'):
            read_json(ROOT / name)
    except (KeyError, ValueError, OSError) as error:
        errors.append('configuration: ' + str(error))
    if not offline:
        for label, action in (('Control Centre read access', lambda: call('GET', '/api/growth/packs?days=1')),
                              ('Control Center engine protocol read access', lambda: engine_client().capabilities()),
                              ('public feed', lambda: pieces(30))):
            try:
                result = action()
                if not result:
                    errors.append(label + ': no records available')
            except (ValueError, OSError) as error:
                errors.append(label + ': ' + str(error))
    for error in errors:
        print('NOT READY ' + error)
    if not errors:
        print('ready: local development' if offline else 'ready: read-only runtime checks')
    if offline:
        print('Runtime credentials and signed-in social dashboards were not tested.')
    return int(bool(errors))


def self_test():
    import unittest
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    return int(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())


def main(argv=None):
    social_args = list(argv) if argv is not None else sys.argv[1:]
    if social_args and social_args[0] == 'social':
        from engine.social import command
        return command(social_args[1:])
    if social_args and social_args[0] == 'run':
        from engine.run.cli import main as run
        return run(social_args[1:])
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--self-test', action='store_true')
    sub = parser.add_subparsers(dest='cmd')
    sub.add_parser('social', help='offline channel, format and tool operating contracts')
    sub.add_parser('run', help='offline run specs, packs and task cards (see docs/RUN.md)')
    p = sub.add_parser('pieces'); p.add_argument('--days', type=int, default=21); p.add_argument('--full', action='store_true')
    p.add_argument('--feed-file'); p.add_argument('--now'); p.add_argument('--json', action='store_true')
    c = sub.add_parser('check'); c.add_argument('file'); c.add_argument('--now')
    s = sub.add_parser('post'); s.add_argument('file'); s.add_argument('--deliver', action='store_true')
    d = sub.add_parser('doctor'); d.add_argument('--offline', action='store_true')
    a = sub.add_parser('audit', help='local guards and receipts for the weekly live-browser audit')
    a.add_argument('action', choices=('plan', 'begin', 'reconcile', 'checkpoint'))
    a.add_argument('file'); a.add_argument('--out', required=True)
    a.add_argument('--state', default=str(ROOT / '.scratch' / 'channel-audit' / 'state.json'))
    a.add_argument('--now')
    lk = sub.add_parser('link'); lk.add_argument('url'); lk.add_argument('platform', choices=PLATFORMS); lk.add_argument('job', choices=KINDS)
    for arg in ('date', 'asset', 'placement', 'variant'):
        lk.add_argument('--' + arg, default='a' if arg == 'variant' else None)
    r = sub.add_parser('read'); r.add_argument('--days', type=int, choices=range(1, 61), default=7); r.add_argument('--kind', choices=KINDS)
    d = sub.add_parser('discover'); d.add_argument('--days', type=int, default=21); d.add_argument('--feed-file'); d.add_argument('--now')
    d.add_argument('--state', default='.scratch/catalog.json')
    p = sub.add_parser('prepare'); p.add_argument('file'); p.add_argument('--out', required=True); p.add_argument('--now')
    e = sub.add_parser('evidence'); e.add_argument('url'); e.add_argument('--kind', required=True, choices=('published_piece', 'source_thread', 'dashboard', 'audit', 'policy'))
    e.add_argument('--excerpt-file', required=True); e.add_argument('--snapshot-file'); e.add_argument('--out', required=True); e.add_argument('--now'); e.add_argument('--created-at')
    w = sub.add_parser('export'); w.add_argument('file'); w.add_argument('--out', required=True); w.add_argument('--now')
    q = sub.add_parser('queue'); q.add_argument('files', nargs='+'); q.add_argument('--now'); q.add_argument('--out')
    m = sub.add_parser('measure'); m.add_argument('file'); m.add_argument('--aggregate', action='store_true'); m.add_argument('--yield-pair', action='store_true')
    r = sub.add_parser('relationship'); r.add_argument('file'); r.add_argument('person_id'); r.add_argument('--now'); r.add_argument('--cooldown-days', type=int, choices=range(1, 366), default=60)
    e = sub.add_parser('experiment'); e.add_argument('file'); e.add_argument('observations'); e.add_argument('--now')
    d = sub.add_parser('dry-run'); d.add_argument('--out', default='.scratch/dry-run'); d.add_argument('--live', action='store_true')
    cc = sub.add_parser('cc', help='the Control Center protocol loop; network only with --deliver')
    ccsub = cc.add_subparsers(dest='cc_cmd')
    for name in ('start', 'finish', 'run', 'runner'):
        x = ccsub.add_parser(name)
        if name != 'runner':
            x.add_argument('--job', required=True, choices=KINDS)
            x.add_argument('--envelope', action='append', default=[]); x.add_argument('--queue')
            x.add_argument('--observations', action='append', default=[]); x.add_argument('--completions')
        x.add_argument('--deliver', action='store_true'); x.add_argument('--mode', choices=('live', 'synthetic'), default='live')
        x.add_argument('--run-id'); x.add_argument('--now')
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd == 'doctor':
        return doctor(args.offline)
    if args.cmd == 'audit':
        from engine.channel_audit import command
        return command(args.action, args.file, args.state, args.out, ROOT, args.now)
    if args.cmd == 'link':
        print(tracked(args.url, args.platform, args.job, args.date, args.asset, args.placement, args.variant)); return 0
    if args.cmd in ('pieces', 'discover'):
        rows = parse_feed(Path(args.feed_file).read_bytes(), args.days, args.now) if args.feed_file else pieces(args.days, args.now)
        if args.cmd == 'discover':
            with locked(args.state):
                previous = read_json(args.state) if Path(args.state).exists() else None
                result = discover(rows, previous, args.now)
                write_json(args.state, result)
            print(json.dumps({key: value for key, value in result.items() if key != 'pieces'}, indent=2)); return 0
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
        for row in rows:
            print(row['date'] + '  ' + row['kind'] + '  ' + row['title'] + '\n' + row['url'] + '\n' + row['piece_id'])
            if args.full:
                print(row['text'] or '[published body missing: read the page; do not infer]')
        return 0
    if args.cmd == 'check':
        value = read_json(args.file)
        if isinstance(value, dict) and value.get('schema_version') == 2:
            validate_envelope(value, args.now)
        else:
            errors = check_pack(value)
            if errors:
                raise ValueError('; '.join(errors))
            print('Legacy shape passes. Evidence is not verified; prepare a v2 envelope before delivery.')
        print('ready: draft validation passed'); return 0
    if args.cmd == 'prepare':
        value = read_json(args.file)
        result = seal(value['pack'], value['evidence'], value['metadata'], args.now, value.get('observations'))
        write_json(args.out, result)
        print('prepared locally: ' + args.out + '; no external write'); return 0
    if args.cmd == 'evidence':
        from engine.core import canonical
        excerpt = Path(args.excerpt_file).read_text(encoding='utf-8-sig').strip()
        if not excerpt:
            raise ValueError('source excerpt cannot be empty')
        snapshot = Path(args.snapshot_file).read_text(encoding='utf-8-sig') if args.snapshot_file else None
        if snapshot is not None and excerpt not in snapshot:
            raise ValueError('excerpt is absent from snapshot')
        url = canonical(args.url)
        result = {'evidence_id': identity('evidence', url, excerpt), 'kind': args.kind,
                  'url': url, 'excerpt': excerpt, 'observed_at': instant(args.now).isoformat()}
        if snapshot is not None:
            result['snapshot'] = snapshot
        if args.kind == 'source_thread':
            if not args.created_at or instant(args.created_at) > instant(args.now):
                raise ValueError('thread evidence requires --created-at no later than observation')
            result['created_at'] = instant(args.created_at).isoformat()
        write_json(args.out, result)
        print('source recorded locally: ' + args.out); return 0
    if args.cmd == 'export':
        result = wire_pack(read_json(args.file), args.now)
        write_json(args.out, result)
        print('legacy pack exported locally: ' + args.out + '; full provenance remains in envelope; no external write'); return 0
    if args.cmd == 'post':
        envelope = read_json(args.file)
        if args.deliver and outreach_kind(envelope):
            raise ValueError(OUTREACH_HELD)
        wire = wire_pack(envelope)
        if not args.deliver:
            print('Dry run: validated; no Control Centre write. Scheduled authorised delivery requires --deliver.'); return 0
        call('POST', '/api/growth/packs', wire, deliver=True)
        print('stored in Control Center: ' + wire['kind'] + ' ' + wire['pack_date'] + ' ' + BASE + '/#/growth?section=packs'); return 0
    if args.cmd == 'read':
        path = '/api/growth/packs?days=' + str(args.days) + ('&kind=' + args.kind if args.kind else '')
        print(json.dumps(call('GET', path), indent=2)); return 0
    if args.cmd == 'queue':
        items = []
        for path in args.files:
            value = read_json(path)
            validate_envelope(value, args.now)
            items += [{**item, **meta, 'pack_kind': value['pack']['kind']} for item, meta in zip(value['pack'].get('items', []), value['metadata'])]
        result = daily_queue(items, args.now)
        if args.out:
            write_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'measure':
        rows = read_json(args.file)
        for row in rows:
            validate_observation(row)
        if args.aggregate and args.yield_pair:
            raise ValueError('choose aggregation or a yield pair')
        result = aggregate(rows) if args.aggregate else {'valid_observations': len(rows)}
        if args.yield_pair:
            if len(rows) != 2:
                raise ValueError('yield pair needs new_free and reach, in that order')
            result = yield_per_thousand(*rows)
        print(json.dumps(result, indent=2)); return 0
    if args.cmd == 'relationship':
        result = relationship(read_json(args.file), args.person_id, args.now, args.cooldown_days)
        print(json.dumps(result, indent=2)); return 0
    if args.cmd == 'experiment':
        print(experiment_decision(read_json(args.file), read_json(args.observations), args.now)); return 0
    if args.cmd == 'dry-run':
        from engine.dry_run import run
        print(json.dumps(run(ROOT, args.out, args.live), indent=2)); return 0
    if args.cmd == 'cc':
        if not args.cc_cmd:
            raise ValueError('choose cc start, finish, run or runner')
        from engine.cc_loop import cli
        return cli(args, ROOT, engine_client)
    parser.print_help()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Not ready: ' + str(error), file=sys.stderr)
        sys.exit(1)
