"""The engines' shared history (engine/engines/core.py): store, overlay, privacy, links, read-only start, CLI.

Synthetic records only, through a stand-in engine module, so these hold whatever kinds each engine defines.
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import growth
from engine import engines
from engine.engines import core

ROOT = Path(__file__).resolve().parents[1]

FAKE = types.SimpleNamespace(
    KINDS=('opportunity',), STATES={'opportunity': ('open', 'awaiting_krish')}, CLOSED_STATES=('declined',),
    validate_detail=lambda record: [] if 'route' in record['detail'] else ['detail.route is required'],
    recover=lambda records, everything, now: {'open': sorted(r['id'] for r in records.values()
                                                             if r['state'] != 'declined'), 'now': now})


def record(rid='opp-one', **changes):
    value = {'id': rid, 'engine': 'acquisition', 'kind': 'opportunity', 'title': 'A synthetic opportunity',
             'state': 'open', 'source': {'kind': 'review', 'ref': 'docs/reviews/x.md', 'observed_at': '2026-11-05'},
             'next_owner': 'acquisition', 'next_action': 'qualify the route', 'revisit_when': 'after a reply',
             'links': [], 'updated_at': '2026-11-05', 'detail': {'route': 'newsletter'}}
    value.update(changes)
    return value


def files(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob('*') if p.is_file())


class EngineCoreTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines', ignore=shutil.ignore_patterns('records'))
        patcher = mock.patch.object(engines, 'module', lambda name: FAKE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_round_trip_latest_wins_and_history_keeps_every_line(self):
        core.append('acquisition', record(), self.root)
        core.append('acquisition', record(state='declined', revisit_when=None, updated_at='2026-11-06'), self.root)
        self.assertEqual(core.load('acquisition', self.root)['opp-one']['state'], 'declined')
        self.assertEqual([r['state'] for r in core.history('acquisition', 'opp-one', self.root)], ['open', 'declined'])
        self.assertEqual(core.check(self.root), [])

    def test_private_overlay_merges_field_by_field_and_detail_shallowly(self):
        core.append('acquisition', record(), self.root)
        core.append('acquisition', {'id': 'opp-one', 'detail': {'body': 'Hello, exact words',
                                                                'recipient_address': 'someone@example.com'}},
                    self.root, private=True)
        merged = core.load('acquisition', self.root)['opp-one']
        self.assertEqual(merged['detail'], {'route': 'newsletter', 'body': 'Hello, exact words',
                                            'recipient_address': 'someone@example.com'})
        self.assertEqual(merged['title'], 'A synthetic opportunity')
        self.assertNotIn('body', core.load('acquisition', self.root, private=False)['opp-one']['detail'])
        self.assertTrue((self.root / '.scratch' / 'engines' / 'acquisition.jsonl').is_file())
        self.assertEqual(core.check(self.root), [])

    def test_committed_records_refuse_private_material(self):
        for bad in (record(title='write to someone@example.com'), record(detail={'route': 'x', 'body': 'words'}),
                    record(detail={'route': 'x', 'nested': [{'email': 'hidden'}]}),
                    record(next_action='open C:\\Users\\someone\\notes.md')):
            with self.assertRaises(ValueError):
                core.append('acquisition', bad, self.root)
        self.assertFalse((self.root / 'engines' / 'records' / 'acquisition.jsonl').exists())
        fine = record(title='Reply to hello@krishraja.com',
                      source={'kind': 'private_file', 'ref': 'D:/Users/someone/work/.scratch/a.md',
                              'observed_at': '2026-11-05'},
                      detail={'route': 'x', 'evidence_ref': 'D:\\work\\.scratch\\receipt.json'})
        self.assertEqual(core.privacy_errors(fine), [])
        core.append('acquisition', fine, self.root)

    def test_schema_refusals(self):
        self.assertTrue(core.validate(record(id='Bad Id')))
        self.assertTrue(core.validate(record(kind='nope')))
        self.assertTrue(core.validate(record(state='nope')))
        self.assertTrue(core.validate(record(revisit_when='')))
        self.assertEqual(core.validate(record(state='closed', revisit_when=None)), [])
        self.assertTrue(core.validate(record(next_owner='someone')))
        self.assertTrue(core.validate(record(source={'kind': 'chat', 'ref': 'x', 'observed_at': '2026-11-05'})))
        self.assertTrue(core.validate(record(extra=1)))
        self.assertEqual(core.validate(record(detail={})), ['detail.route is required'])
        with self.assertRaises(ValueError):
            core.append('engagement', record(), self.root)

    def test_links_resolve_across_engines_and_ids_stay_unique(self):
        core.append('acquisition', record(links=['msr-one'], opportunity_id='opp-one'), self.root)
        self.assertEqual(core.check(self.root), [records_path('acquisition') + ':1: link msr-one resolves to no record'])
        core.append('measurement', record('msr-one', engine='measurement', next_owner='measurement'), self.root)
        self.assertEqual(core.check(self.root), [])
        core.append('engagement', record('msr-one', engine='engagement'), self.root)
        self.assertIn('id msr-one is already in engagement', ' '.join(core.check(self.root)))

    def test_check_reports_bad_lines_and_tolerates_missing_files(self):
        self.assertEqual(core.check(self.root), [])
        path = self.root / 'engines' / 'records' / 'publishing.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('not json\n' + json.dumps(record()) + '\n', encoding='utf-8')
        errors = core.check(self.root)
        self.assertIn(records_path('publishing') + ':1: not a JSON object', errors)
        self.assertIn(records_path('publishing') + ':2: engine field must be publishing', errors)

    def test_start_reads_only_and_carries_contract_and_recovery(self):
        core.append('acquisition', record(), self.root)
        core.append('acquisition', {'id': 'opp-one', 'detail': {'body': 'x'}}, self.root, private=True)
        before = files(self.root)
        result = core.start('acquisition', self.root, now='2026-11-05')
        self.assertEqual(files(self.root), before)
        self.assertEqual(result['entry_request'], 'Run Acquisition')
        self.assertEqual(result['job'], 'jobs/acquisition.md')
        self.assertTrue(result['single_job'])
        self.assertEqual(result['recover'], {'open': ['opp-one'], 'now': '2026-11-05'})
        self.assertEqual(result['next_action']['id'], 'opp-one')
        self.assertIn('write to Control Center', result['authority']['forbidden_actions'])
        self.assertIsNone(core.start('engagement', self.root, now='2026-11-05')['next_action'])

    def test_cli_start_check_show_history_through_growth_main(self):
        core.append('acquisition', record(), self.root)
        code, text = cli(['engine', 'start', 'acquisition', '--now', '2026-11-05', '--root', str(self.root)])
        self.assertEqual((code, json.loads(text)['engine']), (0, 'acquisition'))
        with mock.patch.dict(os.environ, {core.ROOT_ENV: str(self.root)}):
            code, text = cli(['engine', 'check'])
            self.assertEqual((code, json.loads(text)), (0, {'ok': True, 'errors': []}))
            code, text = cli(['engine', 'show', 'acquisition', 'opp-one'])
            self.assertEqual(json.loads(text)['state'], 'open')
            code, text = cli(['engine', 'history', 'acquisition', 'opp-one'])
            self.assertEqual(len(json.loads(text)), 1)
            with self.assertRaises(ValueError):
                cli(['engine', 'show', 'acquisition', 'missing'])


class CommittedRecordsTests(unittest.TestCase):
    def test_the_committed_records_and_contracts_pass_check(self):
        self.assertEqual(core.check(ROOT), [])

    def test_every_engine_has_a_named_entry_point_and_a_module(self):
        for name in engines.ENGINES:
            contract = core.load_contract(name)
            self.assertEqual(contract['job'], 'jobs/' + name + '.md')
            self.assertTrue(contract['entry_request'].startswith('Run '))
            mod = engines.module(name)
            for attr in ('KINDS', 'STATES', 'CLOSED_STATES', 'validate_detail', 'recover'):
                self.assertTrue(hasattr(mod, attr), name + '.' + attr)
        with self.assertRaises(ValueError):
            engines.module('outreach')


def records_path(engine):
    return 'engines/records/' + engine + '.jsonl'


def cli(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = growth.main(argv)
    return code, buffer.getvalue()


if __name__ == '__main__':
    unittest.main()
