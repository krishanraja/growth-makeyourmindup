# Growth asset storage and session closeout

Ruling: Krish, 27 October 2026. Preserve session learning and assets in structured
places every session. This applies to interactive work and scheduled jobs.

## One home per responsibility

- **Growth distribution library:** [makeyourmindup / 4 Growth](https://drive.google.com/drive/folders/1Ck0Eulgcs5pFIpS_Ds1vJ6mEAW__Xjwy).
  Reuse this existing folder. Do not create another Growth root.
- **Production source:** Content Engine retains its existing production folders,
  manifests, editable sources and standards. Growth references them and stores
  immutable distribution exports only when needed for delivery. Never move or
  rename the production originals or make a competing production canon.
- **Operating rules:** this repository, especially `social/` and its narrow guides.
- **Private evidence and recovery:** this repository's ignored `.scratch/`
  directories. Never upload an entire private run or session backup into a shared
  asset folder. These files must survive worktree/chat cleanup.

The supplied Drive folder was verified on 27 October 2026 as owned by Krish Raja
and editable by anyone with its link. Preserve sharing settings. Only publication
assets and sanitized delivery notes belong there under the current permissions.
Recheck access before uploading sensitive material; do not treat a folder named
Private as an access boundary. Do not put internal metrics, account inventories,
raw browser evidence, credentials or operational journals in this library.

## Every campaign

Use `YYYY-MM-DD - Topic - Channel` beneath 4 Growth. Put the exact approved
delivery PDF/images/video, exact post copy and separate comment copy there.
Use explicit revision names such as `approved v3`, never ambiguous `final-final`.
Keep a concise README explaining asset order, primary continuation and source
links. Store a manifest with SHA-256, byte size, revision, source identity and
approval scope. Approval of creative does not imply publication or scheduling.

Keep candidates/rejections and production prompts in their owning private or
Content Engine archive. They must never appear beside approved files without
an explicit historical/rejected label. Source filenames and bytes are preserved.
If an approved file changes, create a new revision and obtain the required review.
Do not overwrite the approved revision or silently update its approval digest.

Use Drive tools to inspect existing children before writes, prevent duplicates,
upload to the verified parent, and independently read back names, parents and
sizes (checksums when exposed). Record returned IDs/URLs privately. A local copy
or successful upload request alone is not proof of a verified cloud archive.
If Drive is unavailable, preserve locally and record the exact upload hold.

## Every session closeout

1. Preserve the exact delivery package, candidates and feedback before cleanup.
   Create a dated private inventory with original paths, sizes and hashes; verify
   copied bytes. Retain old journals and uncertain-save attempt budgets.
2. Store reusable distribution lessons in `social/lessons/`, link them from their
   owning channel/format/tool, and run `python growth.py social check`. Separate
   user rules, observed tool behaviour and untested performance hypotheses.
3. Save creative feedback for Content Engine through its existing handoff. Growth
   records the distribution requirement; Content Engine owns production craft.
4. Keep `docs/SESSION-HANDOVER.md` and `NOW.md` pointing to the latest dated private
   closeout. Record exactly what is draft, approved, scheduled, published, held or
   unknown. Saved IDs are checkpoints; reconcile live state before later action.
5. Snapshot private run evidence before workspace deletion. Check ZIP integrity
   and contents, retain an inventory and recovery instructions. A local archive
   is not an off-device backup; do not describe it as one.
6. Verify automation ownership/schedule if changed. Update existing jobs, never
   duplicate them. Ending a chat does not cancel ongoing daily/weekly duties.

## Current continuation

- Latest private closeout: `.scratch/session-closeout-20261027/CLOSEOUT.md`.
- Shopping-agent library: [27 October LinkedIn package](https://drive.google.com/drive/folders/1TJwaaZ5nf13CfwsgYVJiM0o5msYCxTl8).
- Existing pilot receipts remain under
  `.scratch/channel-audit/first-carousel-experiment-20261026/`.
- Latest measurements and next production brief: `.scratch/channel-audit/daily-20261027/`.

On 27 October Krish explicitly chose to publish the LinkedIn shopping-agent post
himself through Buffer. Preserve both saved drafts; no autonomous publication,
scheduling, engagement or cleanup. After he publishes, reconcile the one live
post, its next-read URL and background comment before proposing another edition.
Buffer's saved document preview remains unresolved despite byte-identical PDF
storage; see `social/lessons/buffer-document-preview-hold.json`.
