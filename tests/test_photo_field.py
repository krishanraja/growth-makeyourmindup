"""The photo field: a real picture of the story, filled only at render time from a local file, always credited on its job, never on the card.
Krish, 2026-11-02: "build out the carousel with real life imagery or screenshots"."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine.run import kits

ROOT = Path(__file__).resolve().parent.parent
SIZES = {(1080, 1350)}


def spec(fields, required, example):
    return {'file': 'templates/item.html', 'width': 1080, 'height': 1350, 'fields': fields, 'required': required,
            'example': example, 'note': 'test'}


class PhotoField(unittest.TestCase):
    def test_a_photo_template_needs_no_credit_on_the_card(self):
        good = kits.spec_errors('item', spec({'photo': 'photo', 'headline': 'text'}, ['photo', 'headline'],
                                                  {'photo': 'The story photo', 'headline': 'The headline'}), SIZES)
        self.assertEqual(good, [])

    def test_placeholder_reads_the_photo_kind(self):
        self.assertEqual(kits.PLACEHOLDER.findall('{{photo:photo}} {{credit}}'), [('photo', 'photo'), ('', 'credit')])

    def test_filler_takes_a_local_file_and_refuses_an_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            pic = Path(tmp, 'p.png')
            pic.write_bytes(b'\x89PNG\r\n\x1a\n')
            kit = Path(tmp, 'pieces', 'tk')
            (kit / 'templates').mkdir(parents=True)
            (kit / 'templates.json').write_text(json.dumps({'piece_id': 'tk', 'templates': {'item': {
                'file': 'templates/item.html', 'width': 1080, 'height': 1350,
                'fields': {'photo': 'photo'}, 'required': ['photo']}}}))
            (kit / 'templates' / 'item.html').write_text('<div>{{photo:photo}}</div>')
            script = (
                "import { fill } from './scripts/render_mocks.mjs';"
                "const [pic, pieces] = process.argv.slice(1);"
                "const job = (p, c = { photo: 'Whose it is' }) => ({ template: 'piece:tk/item', fields: { photo: p }, credits: c });"
                "const ok = fill({ templates: {} }, job(pic), pieces);"
                "console.log('local:' + ok.html.includes('<img class=\"photo\" src=\"/photos/photo.png\"') + ':' + (ok.photos['/photos/photo.png'] === pic));"
                "try { fill({ templates: {} }, job('https://x.test/a.png'), pieces); console.log('no-refusal'); }"
                " catch (e) { console.log('refused:' + /local/.test(e.message)); }"
                "try { fill({ templates: {} }, job(pic, {}), pieces); console.log('no-credit-ok'); }"
                " catch (e) { console.log('credit-required:' + /credits.photo/.test(e.message)); }"
            )
            out = subprocess.run(['node', '--input-type=module', '-e', script, str(pic), str(Path(tmp, 'pieces'))],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertIn('local:true:true', out.stdout, out.stderr)
            self.assertIn('refused:true', out.stdout, out.stderr)
            self.assertIn('credit-required:true', out.stdout, out.stderr)


if __name__ == '__main__':
    unittest.main()
