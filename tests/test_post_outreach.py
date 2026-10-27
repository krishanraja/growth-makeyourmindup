"""G2: Control Center owns outreach (Krish, 21 Oct 2026), so post --deliver never sends it."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import growth
from engine.core import write_json


class PostOutreachTests(unittest.TestCase):
    def test_post_deliver_refuses_outreach_kinds(self):
        trap = AssertionError('token read or network call')
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(growth, 'token', side_effect=trap), \
                patch.object(growth, 'engine_token', side_effect=trap), \
                patch('urllib.request.urlopen', side_effect=trap), \
                patch('urllib.request.OpenerDirector.open', side_effect=trap), \
                patch.object(growth, 'wire_pack', side_effect=AssertionError('validated before refusing')), \
                contextlib.redirect_stdout(io.StringIO()):
            for kind in ('pitches', 'partners', 'swaps'):
                envelope = Path(folder) / (kind + '.json')
                write_json(envelope, {'schema_version': 2, 'pack': {'kind': kind, 'pack_date': '2026-10-27',
                                                                    'headline': 'TEST FIXTURE ONLY', 'items': []}})
                with self.assertRaisesRegex(ValueError, "Control Center's People and Visibility own outreach"):
                    growth.main(['post', str(envelope), '--deliver'])
                legacy = Path(folder) / (kind + '-legacy.json')
                write_json(legacy, {'kind': kind, 'pack_date': '2026-10-27', 'headline': 'TEST FIXTURE ONLY'})
                with self.assertRaisesRegex(ValueError, 'own outreach'):
                    growth.main(['post', str(legacy), '--deliver'])
                # The transport refuses it too, before it reads a token.
                with self.assertRaisesRegex(ValueError, 'own outreach'):
                    growth.call('POST', '/api/growth/packs', {'kind': kind, 'items': []}, deliver=True)

    def test_post_deliver_still_carries_other_kinds_to_the_transport(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(growth, 'wire_pack', return_value={'kind': 'daily', 'pack_date': '2026-10-27'}), \
                patch.object(growth, 'call', return_value={'ok': True}) as call, \
                contextlib.redirect_stdout(io.StringIO()):
            envelope = Path(folder) / 'daily.json'
            write_json(envelope, {'schema_version': 2, 'pack': {'kind': 'daily'}})
            self.assertEqual(growth.main(['post', str(envelope), '--deliver']), 0)
            self.assertEqual(call.call_count, 1)
            write_json(envelope, {'schema_version': 2, 'pack': {'kind': 'pitches'}})
            with patch.object(growth, 'wire_pack', return_value={'kind': 'pitches', 'pack_date': '2026-10-27'}):
                self.assertEqual(growth.main(['post', str(envelope)]), 0, 'a local dry run still validates outreach drafts')
            self.assertEqual(call.call_count, 1)


if __name__ == '__main__':
    unittest.main()
