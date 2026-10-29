"""W3.3: the runner files the backstop's kept lines in taste_reports once each. Synthetic rows only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from engine import backstop
from engine.control_center import ProtocolError


def row(line, posted=False):
    return {'schema': 'growth-taste-backstop/1', 'venture': 'publication', 'repository': 'krishanraja/growth-makeyourmindup',
            'kind': 'correction_or_rejection', 'line': line, 'line_sha256': hashlib.sha256(line.encode()).hexdigest(),
            'session': 'synthetic', 'noted_at': '2026-10-29T20:00:00Z', 'posted': posted}


class FakeClient:
    def __init__(self, answer=None, fail=False):
        self.calls, self.answer, self.fail = [], answer, fail

    def post_flagged_lines(self, route, feature, rows):
        assert (route, feature) == ('taste', 'taste_backstop')
        self.calls.append(rows)
        if self.fail:
            raise ProtocolError('unreachable')
        return {'ok': True, 'results': [{'line_sha256': r['line_sha256'], 'result': self.answer(r)} for r in rows]}


class BackstopPost(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / backstop.OUTBOX
        self.path.parent.mkdir(parents=True)
        rows = [row('No, not that layout.'), row('Make the hook shorter instead.'), row('Already sent.', True),
                row('Refused one, synthetic.')]
        self.path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def posted(self):
        return {json.loads(l)['line']: json.loads(l)['posted'] for l in self.path.read_text().splitlines()}

    def test_dry_run_counts_and_calls_nothing(self):
        self.assertEqual(backstop.post(None, self.root)['waiting'], 3)

    def test_filed_and_duplicate_are_marked_posted_and_refused_is_kept(self):
        client = FakeClient(lambda r: 'refused' if r['line'].startswith('Refused') else
                            ('duplicate' if 'hook' in r['line'] else 'filed'))
        summary = backstop.post(client, self.root, deliver=True)
        self.assertEqual((summary['filed'], summary['duplicate'], summary['refused']), (1, 1, 1))
        self.assertEqual(len(client.calls[0]), 3, 'an already posted line is never sent again')
        self.assertEqual({r['kind'] for r in client.calls[0]}, {'rejection', 'correction'})
        self.assertEqual(self.posted(), {'No, not that layout.': True, 'Make the hook shorter instead.': True,
                                         'Already sent.': True, 'Refused one, synthetic.': False})
        again = backstop.post(FakeClient(lambda r: 'refused'), self.root, deliver=True)
        self.assertEqual(again['waiting'], 1)

    def test_a_failed_call_keeps_every_line_waiting(self):
        summary = backstop.post(FakeClient(fail=True), self.root, deliver=True)
        self.assertEqual(summary['error'], 'unreachable')
        self.assertEqual(sum(1 for v in self.posted().values() if not v), 3)

    def test_kind_mapping(self):
        self.assertEqual(backstop.kind('No, wrong file.'), 'rejection')
        self.assertEqual(backstop.kind("That doesn't fly with me."), 'rejection')
        self.assertEqual(backstop.kind('Use the mix instead.'), 'correction')


if __name__ == '__main__':
    unittest.main()
