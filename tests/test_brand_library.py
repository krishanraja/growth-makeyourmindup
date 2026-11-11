"""The brand library index (social/brand/library.json): one canonical kit, every asset findable by Drive id."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVE_ID = re.compile(r'^[A-Za-z0-9_-]{25,}$')


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class BrandLibraryTests(unittest.TestCase):
    def setUp(self):
        self.lib = load('social/brand/library.json')

    def test_one_canonical_kit(self):
        kit = self.lib['canonical_kit']
        self.assertEqual(kit['name'], '1 Brand kit (permanent)')
        self.assertTrue(DRIVE_ID.match(kit['id']))

    def test_every_drive_asset_has_id_path_and_use(self):
        for name, asset in self.lib['assets'].items():
            self.assertIn('use', asset, name)
            if name == 'canva_kit':
                continue
            drive_id = asset.get('id') or asset.get('drive_id')
            self.assertTrue(drive_id and DRIVE_ID.match(drive_id), name)
            self.assertTrue(asset.get('path'), name)

    def test_brand_assets_never_point_at_old_or_archived_folders(self):
        for name, asset in self.lib['assets'].items():
            path = asset.get('path', '')
            self.assertNotIn('_Archive', path, name)
            self.assertFalse(path.startswith('00_Brand-Assets'), name)

    def test_canva_ids_match_kit(self):
        kit = load('social/brand/kit.json')
        canva = self.lib['assets']['canva_kit']
        self.assertEqual(canva['canva_brand_kit_id'], kit['kit_id'])
        self.assertEqual(canva['canva_template_folder'], kit['template_folder'])

    def test_docs_point_here(self):
        for doc in ('docs/BRAND-KIT.md', 'docs/ASSET-STORAGE.md', 'social/README.md'):
            self.assertIn('library.json', (ROOT / doc).read_text(encoding='utf-8'), doc)


if __name__ == '__main__':
    unittest.main()
