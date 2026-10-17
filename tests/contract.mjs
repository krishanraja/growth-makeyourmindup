// Read-only contract snapshot, Control Centre main 379d193052027fe290bafca4f37f9ef902a0b112.
// Run on Node 24. No API calls, database, browser or application mutations.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
if (!process.argv[3]) throw new Error('Supply a separately available read-only growthPacks.ts snapshot as the third argument. No private source is bundled here.');
const {parsePack, carryStatus, PACK_KINDS} = await import(pathToFileURL(resolve(process.argv[3])).href);
const pack = JSON.parse(readFileSync(process.argv[2] || '.scratch/dry-run/legacy-pack.json', 'utf8'));
assert.equal(parsePack(pack).ok, true, 'export must pass the deployed parser');
for (const kind of PACK_KINDS) {
  const candidate = {...pack, kind};
  if (kind === 'numbers') candidate.numbers = [{platform: 'substack', followers: null, note: 'Not shown; signed-in dashboard unavailable.'}];
  assert.equal(parsePack(candidate).ok, true, kind);
}
const extra = parsePack({...pack, schema_version: 2, items: [{...pack.items[0], item_id: 'id', evidence_ids: ['id'], minutes: 2}]});
assert.equal(extra.ok, true);
assert.equal(extra.value.items[0].item_id, undefined, 'legacy parser discards richer metadata');
const prev = [{platform: 'x', text: 'Same copy', status: 'posted'}];
assert.equal(carryStatus(prev, [{platform: 'x', text: 'Same copy'}])[0].status, 'posted');
assert.equal(carryStatus(prev, [{platform: 'x', text: 'Edited copy'}])[0].status, undefined);
assert.equal(parsePack({...pack, send: false}).ok, false);
assert.equal(parsePack({...pack, pack_date: '2026-02-30'}).ok, false);
console.log('Control Centre snapshot contract passed: all eight kinds, metadata loss, status carry and refusal boundaries. No external writes.');
