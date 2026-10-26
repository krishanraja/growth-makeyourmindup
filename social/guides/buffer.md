# Buffer: verified operating procedure

Owner: Growth. Evidence baseline: 26 October 2026. Capability status and review
interval live in `../tools/buffer.json`; do not duplicate a status table here.
This procedure does not grant publication authority. Browser operations use
only the Codex in-app browser. Never use Chrome, Skyvern, Stripe or cookie export.

## Prepare and save an unscheduled draft

1. Run the selected `social route`. Check actual `get_account`, organization,
   `list_channels` and native account ownership; derive current IDs there.
2. Read the queue, draft list and native source post identities. Reuse an
   intended existing draft only after recording its current exact contents.
   Identify the revision by text and ordered asset hashes, not draft ID alone.
3. Obtain the accepted package from content-engine. Record its approval
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
Do not target an OS-wide Open dialog without reliable window ownership. The
failed chooser is dated evidence, not a permanent declaration of impossibility.

## Nullable preview clear

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

## After exact go-live approval

Use the existing authorised delivery route with the exact account, text, media,
metadata and time. Do not infer permission from this guide or a boolean in a
local file. Capture fresh available baselines first. A queued item proves only
queue state; actual publication needs native post URL, correct account/content,
working continuation and dated independent readback. Reconcile before retrying.
