"""The preserved source documents keep their exact bytes, and the doctrine keeps the house rules."""
import hashlib
import json
from pathlib import Path
import unittest

from engine.packs import EM_DASH, PERCENT

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'knowledge' / 'corpus' / 'manifest.json'
DOCTRINE = ROOT / 'knowledge' / 'COPY-DOCTRINE.md'


class KnowledgeTests(unittest.TestCase):
    def test_every_manifest_file_matches_its_recorded_bytes_and_sha256(self):
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        self.assertTrue(manifest['files'])
        for entry in manifest['files']:
            with self.subTest(path=entry['repository_path']):
                data = (ROOT / entry['repository_path']).read_bytes()
                self.assertEqual(len(data), entry['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])

    def test_copywriting_corpus_is_indexed(self):
        paths = {e['repository_path'] for e in json.loads(MANIFEST.read_text(encoding='utf-8'))['files']}
        self.assertIn('knowledge/corpus/copywriting-offers-demand-corpus.md', paths)
        self.assertIn('knowledge/corpus/copywriting-offers-demand-corpus-summary.md', paths)

    def test_line_ending_conversion_cannot_touch_preserved_originals(self):
        rules = (ROOT / '.gitattributes').read_text(encoding='utf-8').split('\n')
        self.assertIn('knowledge/corpus/** -text', rules)

    def test_doctrine_keeps_house_rules_and_stays_short(self):
        text = DOCTRINE.read_text(encoding='utf-8')
        self.assertIsNone(EM_DASH.search(text))
        self.assertIsNone(PERCENT.search(text))
        self.assertNotIn('%', text)
        self.assertLess(len(text.splitlines()), 250)


if __name__ == '__main__':
    unittest.main()
