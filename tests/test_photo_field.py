"""The photo field: a real picture of the story, filled only at render time from a local file, always with its credit.
Krish, 2026-11-02: "build out the carousel with real life imagery or screenshots"."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine.run import artdirect

ROOT = Path(__file__).resolve().parent.parent
SIZES = {(1080, 1350)}


def spec(fields, required, example):
    return {'file': 'templates/item.html', 'width': 1080, 'height': 1350, 'fields': fields, 'required': required,
            'example': example, 'note': 'test'}


class PhotoField(unittest.TestCase):
    def test_photo_needs_a_required_credit(self):
        bad = artdirect.spec_errors('item', spec({'photo': 'photo'}, ['photo'], {'photo': 'The story photo'}), SIZES)
        self.assertTrue(any('requires a credit' in e for e in bad), bad)
        good = artdirect.spec_errors('item', spec({'photo': 'photo', 'credit': 'text'}, ['photo', 'credit'],
                                                  {'photo': 'The story photo', 'credit': 'Whose photo it is'}), SIZES)
        self.assertEqual(good, [])

    def test_placeholder_reads_the_photo_kind(self):
        self.assertEqual(artdirect.PLACEHOLDER.findall('{{photo:photo}} {{credit}}'), [('photo', 'photo'), ('', 'credit')])

    def test_filler_takes_a_local_file_and_refuses_an_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            pic = Path(tmp, 'p.png')
            pic.write_bytes(b'\x89PNG\r\n\x1a\n')
            kit = Path(tmp, 'pieces', 'tk')
            (kit / 'templates').mkdir(parents=True)
            (kit / 'templates.json').write_text(json.dumps({'piece_id': 'tk', 'templates': {'item': {
                'file': 'templates/item.html', 'width': 1080, 'height': 1350,
                'fields': {'photo': 'photo', 'credit': 'text'}, 'required': ['photo', 'credit']}}}))
            (kit / 'templates' / 'item.html').write_text('<div>{{photo:photo}}{{credit}}</div>')
            script = (
                "import { fill } from './scripts/render_mocks.mjs';"
                "const [pic, pieces] = process.argv.slice(1);"
                "const job = (p) => ({ template: 'piece:tk/item', fields: { photo: p, credit: 'c' } });"
                "const ok = fill({ templates: {} }, job(pic), pieces);"
                "console.log('local:' + ok.html.includes('<img class=\"photo\" src=\"/photos/photo.png\"') + ':' + (ok.photos['/photos/photo.png'] === pic));"
                "try { fill({ templates: {} }, job('https://x.test/a.png'), pieces); console.log('no-refusal'); }"
                " catch (e) { console.log('refused:' + /local/.test(e.message)); }"
            )
            out = subprocess.run(['node', '--input-type=module', '-e', script, str(pic), str(Path(tmp, 'pieces'))],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertIn('local:true:true', out.stdout, out.stderr)
            self.assertIn('refused:true', out.stdout, out.stderr)


if __name__ == '__main__':
    unittest.main()
