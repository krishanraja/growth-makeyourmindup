# Social operating system

Start here for distribution work. Growth owns channel strategy, amplification,
delivery, tool operation and learning. Content-engine owns production and all
production standards. Do not copy its visual or narrative canon into this tree.
The one exception is the Canva lane (Krish, 27 October 2026): Growth makes the
formats content-engine does not cover, today `note` and `meme`, under
`guides/canva.md`, applying content-engine's standards by reference.

## Locate the work before reading more

Asset homes and mandatory closeout: `docs/ASSET-STORAGE.md`. Read it before
creating or uploading a package; keep private evidence out of the shared library.

| Question | Canonical owner |
|---|---|
| Which account, audience, register and purpose? | `channels/<channel>.json`, then its guide and `docs/ACCOUNT-VOICE.md` |
| How does this format reach that destination? | `formats/<format>.json` and `guides/formats.md` |
| How do we safely operate the selected tool? | `tools/<tool>.json` and its guide |
| What actually worked, failed, or remains a hypothesis? | One evidence-linked record per lesson in `lessons/` |
| What exact post is proposed? | Private package conforming to `schemas/package.schema.json` |
| Why would one person send it to another? | The package's `share` block, checked against `share.json`; the blind reader is `crew/send-test/` |
| How is creative made and judged? | Content-engine's production contract; see `docs/ENGINE-BOUNDARY.md` |
| How are Notes and memes made? | `guides/canva.md` (format `production_owner` is `growth-canva`) |
| What is live right now? | Actual owned native pages and tool readback; private run evidence |

These are typed contracts, not a second queue or publishing orchestrator. They
feed the existing daily job, audit and go-live route. Existing account authority,
private evidence, shared locks and approval walls continue to apply.

## Fast path

From the repository, with no token or network:

```powershell
python growth.py social check
python growth.py social route instagram carousel
python growth.py social route linkedin single-image
python growth.py social route threads text
python growth.py social preflight .scratch/my-post/package.json
python growth.py social send-test .scratch/my-post/package.json
```

The route command returns the narrow reading path, relevant learned rules,
specific tested tool capability, remaining holds and mandatory live checks.
Preflight verifies identity/context, format, publication mode, production asset
bytes and any stored exact-payload digest. Read docs/PUBLISHING-AUTHORITY.md:
approved brand content and scoped X, TikTok and Threads have delegated
cadence. LinkedIn remains an unscheduled draft for Krish's manual final
publication.
Every snackable package (its format profile says `"snackable": true`) carries a
`share` block, and its copy never asks for the share (Krish, 28 October 2026;
`guides/formats.md`, "Built to be sent"). Preflight holds it until a blind
send-test answer to this exact revision (its `request_sha256`) is supplied
with `--send-test ANSWER.json` and matches; `social send-test PACKAGE.json
--stage FOLDER` prepares the only things the reader is given.
Preflight never authenticates approval or grants permission
to publish. It has no network, write, schedule or publication capability.

## What is reusable and what must be refreshed

Use a known successful procedure first. Do not rediscover selectors, repeat
failed upload explorations or repeat broad tool discovery without a named gap.
An observation supports only its actual channel/format/account scope. The pilot
proved Instagram eight-image draft preparation and LinkedIn single-image draft
preparation, not every Buffer capability. Unknown routes remain unknown.

Always check current account identity, existing human work, tool input schema,
exact draft revision and action authority. A changed UI, schema error, expired
session or different format triggers one bounded relevant recheck. The tool
profile sets a seven-day capability review interval; this is a local freshness
policy, not a claim that Buffer changes weekly. Old evidence remains historical.
Never promise that discovery will be unnecessary forever.

## Capture each consequential lesson where the next run consumes it

1. Record the actual attempt and authoritative result privately as it happens.
   Preserve uncertainty, retry counts, before/after, native IDs and asset hashes.
2. Add one small record under `lessons/`, using its schema. Classify it as an
   observed mechanism, testable hypothesis, explicit accepted user ruling, or
   superseded finding. Include scope, dated evidence, result and revisit trigger.
   A model cannot promote a performance hypothesis to an accepted user ruling.
3. For a reusable operating change, update the owning channel/format/tool guide
   and profile in the same change. Link the lesson from affected channel
   profiles. Avoid appending general instructions to AGENTS.md or BROWSER.md.
4. Run `social check` and the affected route/preflight, then preserve the change
   in the repository. Private live payloads and business/person metrics stay in
   ignored `.scratch`; public lesson records contain safe reusable summaries.
5. Keep prior evidence. A changed conclusion names `supersedes`; update current
   capability status rather than erasing the failed attempt. Production lessons
   go to content-engine with evidence; Growth records the delivery consequence.

Performance learning records the exact edition, hypothesis, source, native URL,
publication time, comparable baseline and exposed outcomes. Keep 24h, 72h and
seven-day checkpoints relative to actual publication. Draft volume, impressions
and two different channel audiences are not financial ROI or a controlled A/B
test. Choose keep/change/stop only to the strength of the observed evidence.

## Schema maintenance

All five schemas are closed JSON Schema Draft 2020-12 objects. The standard-library
validator implements only their documented subset and rejects unknown schema
keywords. Changes to the schema subset require validator and regression updates.
No dependency, browser automation, provider adapter or parallel executor is added.
