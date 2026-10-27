# Buffer: verified operating procedure

Owner: Growth. Evidence baseline: 26 October 2026. Capability status and review
interval live in `../tools/buffer.json`; do not duplicate a status table here.
Publication authority comes from docs/PUBLISHING-AUTHORITY.md. Approved branded
content has delegated cadence; LinkedIn remains an unscheduled draft; scoped X, TikTok and Threads have delegated cadence.
Browser operations use
only the Codex in-app browser. Never use Chrome, Skyvern, Stripe or cookie export.

## Prepare and save an unscheduled draft

1. Run the selected `social route`. Check actual `get_account`, organization,
   `list_channels` and native account ownership; derive current IDs there.
2. Read the queue, draft list and native source post identities. Reuse an
   intended existing draft only after recording its current exact contents.
   Identify the revision by text and ordered asset hashes, not draft ID alone.
3. Obtain the accepted package from content-engine or, for `growth-canva`
   formats, from the Canva lane (`canva.md`). Record its approval
   evidence, immutable hashes, order and alt text. Apply the account voice rule.
   Keep the exact caption and proposed time in the private posting package.
4. Inspect the current domain tool schema. Journal operation, target, payload,
   before-state and attempt count *before* saving. Use `edit_post` for a known
   intended draft; use create only when no intended draft exists. Set
   `saveToDraft: true`; do not supply a due time. Never rely on default queue mode.
5. The verified image asset shape was
   `{image: {url: uploadedUrl, metadata: {altText: acceptedAltText}}}`.
   Instagram's tested metadata was
   `{instagram: {type: 'post', shouldShareToFeed: true, isAiGenerated: true}}`.
   The AI flag reflects this pilot's generated illustrations; derive it from
   actual asset provenance for future work. These are observed shapes, not a
   substitute for the live schema.
6. Wait for completion. Read `get_post` independently: exact caption, account,
   ordered assets/alt text, intended metadata, `status: draft`, `dueAt: null`.
   Reopen the actual saved draft in Codex and compare the visible edition.
   Re-download transformed media when needed and verify pixels/dimensions;
   preserve the accepted original. Record proof and leave the draft reviewable.

## Local image upload: known successful route

Use a supported direct upload if available. When the Codex file-chooser handoff
fails in the same way as this pilot, use the documented tab clipboard for PNGs:

```javascript
// Read the accepted local PNG with local file I/O, never browser internals.
await tab.clipboard.write([{entries: [{mimeType: 'image/png', base64: pngBase64}]}]);
await tab.playwright.getByRole('textbox', {name: 'composer textbox', exact: true})
  .press('Control+V');
```

Check current DOM before using that locator. Wait for each attachment's upload
completion before pasting the next. Capture returned URLs from actual visible
media, not private app state. A temporary composer is staging, not a saved post:
preserve any existing human draft, never queue/publish it, and close it after
verifying the intended saved drafts. Reconcile draft counts to avoid duplicates.

The pilot's eight uploaded PNGs matched accepted source pixels exactly after
download through page media. No universal compression guarantee or image-count
limit follows. PNG success does not prove PDF, video or another account's route.
Do not target an OS-wide Open dialog or native desktop app for this work.
The current user boundary is Codex in-app browser only.

## Document draft preview, observed 27 October

A supported in-app file chooser uploaded the accepted six-page PDF. The stored
file matched its original bytes, but Buffer's reopened draft omitted the carousel
and returned zero pages. Reattachment and connector re-save did not repair it.
Native LinkedIn processed all six pages and preserved an unscheduled draft.
Do not repeat those attempts or call Buffer's saved preview verified. Reconcile
the exact native draft before any new work; Krish alone publishes LinkedIn.
The earlier file-chooser failure describes its old attempt, not a universal ban
on the now-observed supported chooser. No native desktop or OS dialog is allowed.

## Nullable preview clear procedure

The domain tool rejected `metadata.linkedin.linkAttachment: null` in input
validation. Fresh `get_post` proved that the original value remained unchanged.
The provider's *inspected* schema exposed `EditPostInput` with a nullable clear.
One narrow `editPost(input: $input)` mutation saved the intended image draft and
cleared the obsolete preview, using `id`, `saveToDraft: true`, the exact text,
one image asset and `metadata.linkedin: {annotations: [], linkAttachment: null}`.
The success fragment returned `post {id status dueAt}`; `MutationError` returned
`message`. Only use this fallback for the uncovered operation, with fresh schema
and readback. Never turn a validation rejection into an excuse for arbitrary API
calls or retry an uncertain provider mutation. Prefer the domain tool afterward.

## Save-state ledger and recovery

| Authoritative state | Next step |
|---|---|
| Original value proved unchanged | At most one retry within the preserved attempt budget |
| Correct target value persisted | Stop saving; capture readback |
| Timeout or unknown completion | Hold mutation; read back first, never assume failure |
| Wrong/partial persisted content | Preserve result; diagnose a new bounded correction |
| Account/schema/session changed | Hold only that route, record the changed blocker |

A subsequent intentional one-field correction to a fully verified save is a
new journalled payload, not a blind retry. Retain the old payload and count.
No delete/re-upload workaround, approval bypass or checkpoint advancement.

## Scheduling approved branded content

For approved branded content, the current standing permission delegates timing;
record it separately from creative approval. LinkedIn never enters this scheduling/publication procedure: Krish makes its final publication manually. X, TikTok and Threads are explicitly delegated for approved content.

Use the authorised delivery route with the exact account, text, media,
metadata and time. Do not infer permission from this guide or a boolean in a
local file. Capture fresh available baselines first. A queued item proves only
queue state; actual publication needs native post URL, correct account/content,
working continuation and dated independent readback. Reconcile before retrying.

On 26 October, scheduling-only `edit_post` with mode, dueAt and saveToDraft=false
was rejected because text, media and Instagram type were required. Independent
get_post proved the original draft unchanged. One retry with the complete
accepted text, eight image/alt assets and Instagram metadata, plus
`mode: customScheduled`, `schedulingType: automatic`, `saveToDraft: false` and
the ISO dueAt succeeded. Reopened native Queue and get_post both showed the
correct London time, scheduled state and unchanged accepted content. Use the
complete validated payload for this route; preserve the two-attempt journal.

TikTok photo drafts rejected isAiGenerated=true with an explicit unsupported
photo-disclosure error. Readback proved the original unchanged; one retry
omitted the unsupported field. The resulting draft saved, but no native AI
label was applied. Krish subsequently prohibited public illustration
boilerplate; that copy was removed and independently read back. Do not restore
it as a workaround. Recheck supported native metadata before a live action.

## Stories and paired Meta delivery

One image per native Story post was accepted in the actual Facebook composer;
selecting Story hides the text editor and disables further attachments. The
known clipboard route can stage accepted images in an owned Post composer,
then switch a single image to Story for preview. Preserve human unfinished
work. Multiple DOM copies can be thumbnail/preview duplicates: deduplicate
identical returned media URLs, not source files or Story frames.

Use one-image payloads with instagram.type=story, shouldShareToFeed=false,
or facebook.type=story. Verify each saved type, asset and account. A Story
draft does not prove scheduling, delivery, music, polls or link stickers.
Record only the operations actually verified. Follow up after feed delivery;
do not route a Story to a missing/failed feed post. Keep IG/FB output paired,
and reconcile native automatic sharing before creating a duplicate.

The 26 October native release verified three ordered one-image Stories on
each Meta account. Read back `sent` and each native URL before counting a
release. The Instagram Link sticker switched Automatic to Notify Me in the
actual composer; the test was not saved. Do not claim automatic link stickers.
The approved continuation referred to the already-live carousel. Buffer preview
did not reproduce Facebook's native AI-content overlay exactly; retain a
native safe-area check for every frame, including small branding.
