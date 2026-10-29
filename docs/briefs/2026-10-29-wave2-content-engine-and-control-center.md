# Brief: Wave 2 contracts Growth now reads (content-engine, Control Center)

From growth-makeyourmindup, 29 October 2026. Growth changes nothing in your
repositories; this is what its code now expects, so W2.8 and W2.9 meet in the
middle. Every example in Growth's tests is synthetic.

## Content-engine: the piece manifest (W2.8)

- Write `0 Publish/manifest.json` per piece to the closed shape in
  `specs/schema/piece-manifest.schema.json` (schema
  `content-engine-piece-manifest/1`): piece_id, approval_sha256 (the publish
  board approval), qa {state, checked_at}, assets [{name, drive_id, sha256,
  order}], channels {channel: {words, alt_text, assets}}.
- In the go-live dispatch (`growth-go-live-manifest`), name it as
  `"piece_manifest": {"url": <a direct download of the file itself, never a
  Drive viewer page>, "sha256": <sha256 of those bytes>}`.
- Growth holds a slot whose Buffer draft is not exactly the manifest's post
  for its channel (`manifest_differs`), and every slot when the manifest is
  not passed QA (`manifest_qa_not_passed`), has no approval digest
  (`manifest_unapproved`) or does not hash to its sha (`manifest_sha_mismatch`).
- One decision per post: mark every slot `"per_item_review": true`. Each then
  becomes its own go-live, bound to its payload_sha256, Buffer channel id
  and due time.

## Control Center: the Pull, and the clock rows Growth reports (W2.2, W2.8)

- The Pull is a No on that post's go-live. Before release schedules it (5 to
  90 minutes ahead of its slot) the post stays a draft. After it is
  scheduled, Growth's release run fails loudly (`scheduled_after_decline`)
  and never unschedules: that stays his call. A Pull press that writes a
  declined decision on the post's go-live is all it needs.
- Growth's reports will carry `engage_done`, `offday_stocked` and
  `offday_slots_filled` facts as activity lines first; name the field you
  want them in for DONE_CHECKS and Growth adds it.
