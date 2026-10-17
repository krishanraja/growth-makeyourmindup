# Engine contract and working procedure

Version 2 uses a local envelope around the current pack. This repository
owns source records, identity, checks, discovery, observations and queue
planning. Control Centre still understands the original pack shape. Keep
both facts explicit; no new fields are silently assumed to survive its API.

## Input and evidence

Create a scratch JSON file containing `pack`, `evidence`, `metadata`, and
optionally `observations`. `pack` keeps `pack_date` (a real New York date),
`kind`, `headline`, `items`, `numbers` and `link`. Existing eight kinds and
platform names remain accepted. At most 40 items, headline 500 UTF-16 units,
text 4000. Numbers belong only to `numbers` packs.

Each evidence object has:

| Field | Meaning |
|---|---|
| evidence_id | `identity('evidence', canonical_url, literal_excerpt)` |
| kind | published_piece, source_thread, dashboard, audit or policy |
| url | Actual source HTTP(S) URL, without embedded credentials |
| excerpt | Literal relevant source text, never a generated summary |
| snapshot | Optional read-only source text; excerpt must occur in it |
| observed_at | Offset-aware timestamp when the source was read |
| created_at | Required for a source thread; actual thread creation time |

For a convenient source ID, save the exact excerpt to a UTF-8 text file:

```powershell
python growth.py evidence https://home.makeyourmindup.ai/p/actual-piece --kind published_piece --excerpt-file .scratch/excerpt.txt --snapshot-file .scratch/source.txt --out .scratch/evidence.json
```

Do not create that example URL as an asset. Use the real URL from `pieces`.
Insert the resulting object into the input's `evidence` array. Published
sources and source threads are required for publication and outreach
packs; audit/policy/dashboard records support fixes and reports. Radar also
requires source-thread evidence, actual creation time and an expiry no later
than 12 hours after that creation time. The `evidence` command accepts
`--created-at` for a thread; do not guess a creation timestamp.

One metadata object, in matching order, is required for each item:

```json
{
  "asset_id": "piece_actual-stable-id",
  "placement": "linkedin-native-post",
  "variant": "a",
  "evidence_ids": ["evidence_actual-id"],
  "priority": 1,
  "minutes": 4,
  "why_now": "The published finding answers a current reader question.",
  "success_check": "The source supports each claim and the matched link opens.",
  "blocked_by": [],
  "quotes": [],
  "expires_at": null
}
```

The tool derives `item_id` from asset/platform/placement/variant, and
`revision_id` from draft text. Editing copy preserves the item identity but
changes its revision. A variant is a deliberate alternative, not a new ID
on every rerun. Use unique placements for launch, next-day discussion,
partner kit and evergreen retrieval. A literal declared quote must appear
in a cited excerpt. The linter does not infer all factual claims or prove
paraphrases. Human source comparison is a required drafting step.

`prepare` validates the input and writes a sealed envelope, including
`schema_version: 2` and `prepared_at`. `check` re-derives IDs and detects
post-preparation copy edits. Re-prepare after an edit. Legacy `check` can
lint the old pack shape, but delivery requires the evidence envelope.

`tests/fixtures/prepare-input.json` is a complete, labelled test input. A
repeatable local example (not a campaign or a deliverable social draft):

```powershell
python growth.py prepare tests/fixtures/prepare-input.json --out .scratch/example.json --now 2026-10-17T18:00:00Z
python growth.py check .scratch/example.json --now 2026-10-17T18:00:00Z
```

## Discovery and delayed publications

`pieces` reads the public RSS feed, preserving published time, New York
publication date, body availability, canonical URL, revision and links.
`discover` updates `.scratch/catalog.json` atomically under a lock. Repeated
identical scans create no new discovery changes. Revised bodies recover
on a later scan. First-seen times survive. Missing bodies stay pending.

Only a unique explicit published link verifies an article/video pairing.
Similar titles do not merge assets. A human can document a verified pair
as audit evidence, then use it while drafting; the catalog does not infer
it. A missing or ambiguous pair blocks that distribution placement, not the
whole article's work. Feed lookback is 21 days by default, maximum 366;
RSS may expose fewer items than requested. Older archive coverage requires
a read of the actual archive. Recheck on existing jobs; no new cron.

Discovery is not delivery state. A job must inspect its local envelopes
and real action evidence before deciding whether an unchanged piece needs
recovery, follow-up or no work. Publication after the nominal slot is
picked up at the next existing run, then allocated within the shared budget.

## Tracking and the work queue

```powershell
python growth.py link https://home.makeyourmindup.ai/p/actual-piece x daily --asset piece_actual-id --placement thread-last-post --variant a
```

The four tags are source, organic medium, growth campaign and a stable
hashed placement content value. Existing UTM tags are replaced once;
functional query values, native referral codes and fragments survive.
The simpler three-argument legacy command still uses job/date content.
V2 preparation requires the richer identity to match each item's metadata.
Do not insert UTMs into internal
navigation; `engine.core.acquisition` defines separate original acquisition
and internal placement records for the website handoff. It is not deployed
website instrumentation.

Prepare candidate envelopes for the day, then merge all of them with
`queue`. Priority 1 is highest. Estimated effort is an integer from 1 to
30 minutes; it is not measured time. Handled, blocked, expired or excess
items are deferred with reasons. Duplicate IDs fail visibly rather than
silently double-counting; supply only the newest envelope revision for a
placement. Queueing cannot claim a real-world action happened. Reduce the
candidate packs to the selected items and re-prepare before delivery.
Later jobs must include today's earlier selected work when budgeting.
The current dashboard cannot enforce the global budget; the local queue
and handoff explicitly address that gap.

## Measurement records

Use `engine.operations.METRICS` as the unit/window registry. Each observation
has platform, metric, unit, window_kind, source URL, scope, optional asset_id,
start, end, captured_at, timezone, availability, value and missing reason.
Times contain offsets; interval windows are half-open `[start, end)`.
The reporting timezone is America/New_York. Preserve the platform's actual
source timezone in a note if different and normalise instants honestly.

Available means a finite non-negative value; zero must be observed, never
filled in. Unavailable means null plus reason. Followers/subscribers are
snapshots (`start == end`); unique reach is accounts, impressions and views
keep their own units. A valid example is generated in the regression tests;
fixture values must never be ingested as real observations.

```powershell
python growth.py measure .scratch/observations.json
python growth.py measure .scratch/comparable-daily-windows.json --aggregate
python growth.py measure .scratch/attributed-new-free-and-reach.json --yield-pair
```

Aggregation deduplicates exact measurement windows by latest capture,
rejects conflicting same-time captures, overlaps, changed populations,
changed sources and snapshots, and returns unknown for gaps or missing
values. Yield requires matching scope, asset, platform, window and timezone,
a real attribution basis, new free people and unique reach. Impression or
view yield needs its own explicit metric; it is not silently substituted.

Number-display rows must have a source/window/availability `note`; each
non-null scalar must match a structured observation. Omit rolling
`new_this_week` in v2 daily packs. The structured `observations` array stays
local; the legacy pack contains only the old fields plus human-readable
context. Do not imply those notes are queryable structured analytics in CC.

## Relationships and experiments

Maintain a UTF-8 JSON event array in ignored scratch state, with event_id,
person_id, type and offset-aware at. Types: drafted, sent, replied, declined,
booked, published. All real events require `confirmed_by: Krish` and an
actual `evidence_url`. Preserve a public evidence link when possible; keep
private message evidence local and out of git. A drafted message never
counts as sent, never advances warmth and never starts a cooldown.

```powershell
python growth.py relationship .scratch/events.json actual-person-id --cooldown-days 90
python growth.py experiment .scratch/experiment.json .scratch/observations.json
```

A real inbound reply can make a relevant next step due. A decline blocks
further asks. The three lists are human-readable ledgers, not automated
send queues. Record actual events only after Krish confirms them.

Experiment templates have no start/end and cannot be evaluated as running.
Choose one, set real dates, comparison, minimum comparable observations,
metric and quality guardrail before starting. The review floor does not
establish significance. The decision checker requires a completed window
and enough distinct qualified observations; it never automatically kills
or scales a channel. Krish reviews the predeclared rule.
Retained-30-day observations require capture at least 30 days after the end
of the acquisition cohort. An immature cohort cannot pass validation.

## API compatibility, failures and boundaries

`export` produces exactly the current pack write fields. `post FILE` checks
but does not write. `post FILE --deliver` is only for a future separately
authorised scheduled delivery to the approved HTTPS packs endpoint. It
omits agent-supplied status marks and every rich metadata field. There is
no direct database fallback, no retry loop that might duplicate sends,
and no social action. A failed or unconfirmed response exits unsuccessfully.
A bearer credential is never forwarded across a redirect or printed in an
error. A legacy API edge case scans percent-encoded URLs as prose; the
export fails clearly if that rule would reject an unchanged destination.
Do not alter a functional referral code merely to bypass the server rule.

No credentials are required by the offline doctor, tests or dry run.
`.scratch/` is ignored; back it up in an appropriate private location if it
contains continuity records. Do not commit private dashboard captures or
messages. Corrupt/old catalog schemas fail visibly; preserve the file and
migrate deliberately. A lock is never stolen automatically. Before removing
a stale lock, verify the other process has stopped.

`tests/contract.mjs` can compare an exported pack against a separately
available read-only Control Centre TypeScript snapshot on Node 24. The
private source is deliberately not bundled into this public repository.
This is a compatibility check, not a CC change or API write.
