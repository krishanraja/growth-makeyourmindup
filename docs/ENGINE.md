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

An answer piece (`placement: "answer-piece"`, platform `substack` or
`seo`, from `jobs/answer.md`) has extra checks at `prepare` and `check`:
the reader's question alone on the first line ending in `?`, then an answer
of at most 60 words that does not end in a question, and a link to an own
host. Its evidence must include the `published_piece` and the record of the
real question (`source_thread`, `dashboard` or `audit`).
`tests/fixtures/answer-input.json` is a labelled synthetic example.

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

## The content backlog

`python growth.py backlog` lists every published piece against the channels
it could run on, oldest unamplified first, then partly amplified, then
covered, and ends with "Backlog remaining N": the pieces with no native
edition yet. It reads the public feed as far back as it reaches (366 days)
and merges `.scratch/catalog.json`, so a piece that has left the feed stays
in the backlog. A video post folds into its article only on an explicit
published link, the same rule as discovery. The open channels are every
channel record in `social/channels/` except `substack`, the piece's home.
Each piece also lists its open formats (`formats_open`): every channel and
format pair with no edition in that exact format, so one Instagram carousel
closes Instagram as a channel but leaves its short video and story open. An
edition that names no format closes none.

A native edition counts from two places: a committed pilot in
`lists/pilots.json` that names its `piece_url` (and its `editions`), and the
local ledger `.scratch/backlog/amplified.json`. Add a live edition with
`python growth.py backlog record --piece URL --channel ID --format ID
--native-url URL --at TIME` once its native URL reads back; a draft or a
scheduled post is never an edition. The inventory is written to
`.scratch/backlog/inventory.json`. Only `backlog/inventory.schema.json`,
`backlog/amplified.schema.json` and the synthetic `backlog/fixture.json` are
committed. The GitHub runner reports "Backlog remaining N" from the public
feed and the committed pilots only, and says that workspace editions are not
visible to it. The day's pack takes the oldest unamplified piece worth a new
edition alongside the day's new piece (`jobs/daily-pack.md`).

## The weekly mix

`python growth.py mix plan --week-of MONDAY` turns the backlog into carousel
concepts and interleaves them with memes, positive news and level-up advice,
three or four a day on Instagram, YouTube, TikTok and X, and writes the one
plan proposal of the week's ideas and mocks. `python growth.py mix learn`
joins each post's verdict to its concept and lane for next week's ratio.
Concept approval, release and learning: `docs/MIX.md` (Ruling, Krish,
2026-10-29; R101 to R103).

## The four engine sessions

Built 5 November 2026 from `docs/reviews/2026-11-05-growth-engine-review.md`
(`AGENTS.md`, "Four engines"). Acquisition, Engagement, Publishing, and
Measurement and Allocation each run as one Codex session Krish opens on
request ("Run Acquisition" and so on), never on a schedule. Each follows its
job file (`jobs/acquisition.md`, `jobs/engagement.md`, `jobs/publishing.md`,
`jobs/measurement.md`) and its contract in `engines/NAME.json`, and records
what it did in `engines/records/`. `engine/engines/core.py` (`command`) is
the code:

| Command | What it does |
|---|---|
| `growth.py engine start NAME [--session LINK]` | What a fresh session recovers first: its queue, inbound handoffs and the last sessions' learnings. `--session` records this session's own link (its one write) |
| `growth.py engine check` | Validates every committed engine record and contract |
| `growth.py engine show NAME [ID]` and `engine history NAME ID` | One engine's current records, or every committed line of one record |
| `growth.py engine handoff FROM TO --what TEXT --why TEXT [--link ID]` | Hands work another engine owns to that engine's queue and prints the question for Krish and the message for the other session |
| `growth.py engine done NAME ID --note TEXT [--next TEXT]` | Closes one record; for a handoff it prints the report-back |
| `growth.py engine session set|show|clear` | Krish's session links, kept only in the ignored `.scratch/engines/sessions.json` |
| `growth.py engine close NAME --learnings FILE` | Ends the session; refuses to close without specific "better next time" lines |

`NAME` is `acquisition`, `engagement`, `publishing` or `measurement`.
Committed records stay privacy-safe: exact words, recipients and post URLs
live only in `.scratch/engines/`. This is the shadow week: the daily job,
the PC automations and the L0 workflows keep running, and Measurement then
compares the engines' decisions with what the operation did.

## Ecosystem routes

Every run spec slot names a route into the wider ecosystem
(`ecosystem_cta`, `engine/run/spec.py` lint). The
publication is the front door to Mindmake (NOW.md), so a post that only
points at the newsletter, an article or the subscribe page has no route
beyond it. Each slot names one verified route from `journeys.json`
(`ecosystem`): the show's own YouTube channel (`/@makeyourmind-up`) or a
long video whose id is in the route's `video_ids`, or Mindmake at
mindmake.co. The Spotify show is a route row with `verified` false, so lint
refuses it until its URL is verified. Each names its URL and placement:
`in_post` (the URL is in the words, tracked or not) or `first_reply` (the
slot's `link_placement` is `first_reply`). A profile link is not a
placement: the only profile link the engine may set is the newsletter's
subscribe page (`engine/channel_audit.py`), which is no route beyond the
newsletter. Lint refuses no route, an unknown or unverified route, a
newsletter URL, a URL off the route (another channel, an unlisted video),
an `in_post` URL missing from the words and a `first_reply` route without a
first-reply placement. A new route, or a newly verified video, is a row in
`journeys.json`; each journey there names the route its readers continue
on (`ecosystem_route`).
`ecosystem_cta` is outside the digest: an `in_post` URL is already in the
signed words.

## Intensity: the gap sets the volume

Ruling (Krish, 2026-10-29): At U3 to U5, engines and Control Center may
raise volume caps up to each repo's existing policy bounds without a signed
week spec. This is volume only: walls unchanged.

`engine/intensity.py` reads this week's gap from NOW.md's state line and the
ladder in docs/NORTH_STAR.md, and takes Control Center's urgency instead
when the directive's `north_star.intensity` is higher. A week nobody has
measured is U4; a week with no ladder rung raises nothing. Every report,
from the runner and from each workspace job, leads with the gap line
"X of Y, U-n, short by Z" (an unmeasured week reads "not measured of Y, U4,
short by unknown", never zero). At U3 and above the caps rise to the bounds
in `intensity.json`: a channel's scheduled posts a day only to its own
policy bound in `engine/social.py` (Instagram, YouTube, TikTok and X four
with a floor of three, the 29 Oct ruling; Substack Notes four, raised from two
on 11 Nov, and every other channel one, the 27 Oct ruling; every channel already sits there, so `run
lint` reads the urgency and no urgency caps those four below three; a
human-only channel stays manual), and the day's engagement taps from 5 to 10, 15 and 25 at U3, U4
and U5, Control Center's ceiling. Raised volume comes from the taps. Zero spend, approvals and the
creative bar never move with it.

### The subscriber push (Ruling, Krish, 2026-11-11)

At U4 and U5 (`intensity.json`, `conversion`) every run spec slot and social package names a
subscribe route, `subscribe_cta` {url, placement}: the subscribe page
(`https://home.makeyourmindup.ai/subscribe`) with its `utm_source` and `utm_content` tags (`python
growth.py link ... conversion` makes them), placed `in_post` (the URL is in the words),
`first_reply` (the slot's `link_placement` is `first_reply`) or `profile_link` (only Instagram and
TikTok, and the words point to the profile link). `run lint`, social preflight and release all
refuse a post without one; release holds it as `subscribe_cta_refused`. It sits beside the
ecosystem route, never in place of it, and it is a destination, never a share ask. At U3 to U5
Acquisition's `recover` names the day's outreach batch (`daily_outreach`: 2, 3 and 5 one-person
drafts), leaning on Substack recommendation swaps, cross-posts and guest pieces. The browser half
(the reading, the profile links, the swap list) is the Cowork brief in
`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`.

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

### Judged by subscribers (Ruling, Krish, 2026-11-12)

"The engine reads subscribers every week and judges posts by subscribers, not
engagement." Each sent post's verdict in the measure job (`growth.py run
measure auto`, `engine/run/measure_auto.py` `subscriber_verdicts`) is the
sign-ups its own tracked link brought over its first seven New York days: the
GA4 `sign_up` rows (verified in `invariants/ga4.json`; not a key event, so the
sessions it fired in) on the post's `utm_content`, from Control Center's
`web_analytics` block, only on those seven days (`ga4.post_window`). The rule
is `engine/run/measure.py` `judge_subscribers`: one sign-up works; none fails
only when the link brought at least `FAILS_AT_SESSIONS` (30) visits in those
days; anything else is insufficient, with its reason code: no tracked own
link, a link another post shares, GA4 rows not read, the sign-up event name
not verified, seven days not passed, a day with no GA4 capture (the block's
`coverage.dates`), or no sign-up on too few visits. The bands are proposed
defaults for Krish at G-A. Association, not cause. Each post's engagement
against its own channel's median (`engagement_verdicts`, the old verdict) stays
beside it as supporting evidence only. Substack's own per-post and per-Note
numbers, where the weekly read (`jobs/subscribers.md`) finds them, are judged
by the same rule. The weekly learn (`docs/MIX.md`, "Learning") turns these
verdicts into next week's mix.

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

## Reporting to Control Center

`engine/control_center.py` is the one Control Center transport: the
bounded HTTPS calls (the legacy packs call in `growth.py` shares its
no-redirect opener), the canonical digest, a validator for the published
report schema in `docs/control-center/`, the report builder and the client
for the protocol routes. `engine/cc_loop.py` runs the loop. Every run, in
order: attempt `started` (before any source is read), `GET directive`, the
job's own work, `POST reports` with `Idempotency-Key: <run_id>` and a
readback of the stored digest, `GET decisions?since=`, then exactly one
terminal attempt (`succeeded`, or `failed` with a lower_snake code).

| Command | What it does |
|---|---|
| `growth.py cc start --job KIND --deliver` | Journal the start, pull and print the directive, keep the attempt in `.scratch/cc/KIND.state.json`, Krish's approved voice rules (protocol 1.5.0 `taste`) in `.scratch/cc/voice-rules.txt` for drafting only, and his inspiration board (1.15.0 `inspiration`) in `.scratch/cc/inspiration.txt` for planning |
| `growth.py cc finish --job KIND --envelope F --queue F [--observations F]... [--completions F] --deliver` | Build the report from the job's files, report, read back, read decisions, journal the end |
| `growth.py cc run --job KIND ... --deliver` | Both in one call |
| `growth.py cc runner --deliver` | The GitHub runner's loop (below) |

Without `--deliver` nothing reads the key or calls the network: `finish`
writes the report it would send to `.scratch/cc/report-KIND.json`.

**The directive's version.** The client accepts any 1.x directive and
ignores fields it does not know; it never checks `schema_version`. From
1.5.0 the directive may carry `taste`, Krish's approved voice rules.
`engine/cc_loop.py` (`voice_rules`, `voice_block`) turns them into one
labelled block for the drafting steps: how a draft is written, never what
it is about. Absent `taste` prints "Could not be read today"; an empty
list prints "None approved yet" and nothing is invented. Nothing that
checks, scores, queues or reports a draft reads them, and the GitHub
runner never prints them. The report stays at 1.0.0: 1.5.0 adds nothing
to it.

**His inspiration board is the baseline (1.15.0).** Krish, 2026-10-29:
"When the growth-makeyourmindup repository plans: In all this content, it
should know what I've suggested already and try and use that as the
baseline standard." From 1.15.0 the directive may carry `inspiration`:
what he saved on Control Center's inspiration board, why in his words, and
what he wants tried. A trial is one of four taps: record like this (he
records a piece to camera in that style, often for the off days), reskin
the news (positive or real-world AI news rebuilt as our post), reskin the
meme, and borrow the format (an infographic, a subtitle style, a carousel
layout). `engine/cc_loop.py` (`inspiration_suggestions`,
`inspiration_block`) writes it to `.scratch/cc/inspiration.txt` at every
start. Every week, piece and express spec reads it before choosing slots:
each tagged trial is either a slot that trials it, rebuilt in the
publication's voice and look and never copied, or a line in the spec
saying why it waits. His words are quoted as his; a reason he tapped is a
guess he agreed with. Absent prints "Could not be read today" and nothing
is invented; an empty list means he has suggested nothing yet. Like the
voice rules, nothing that checks, scores, ranks, queues or reports a draft
reads it, and the GitHub runner never prints it.

**A card he ticked is an instruction (1.21.0).** Ruling (Krish, 2026-11-12):
an inspiration card he ticks is an instruction that jumps the queue: Content
means make it into a piece now, Production means use the style within a
week. A Production card he ticked comes in `inspiration` with an
`instruction` (its due date and his words) and is listed first in
`inspiration.txt` as MUST USE BY its date (PAST DUE once late). The next
fitting carousel, meme or off-day post uses that style, rebuilt in our voice
and look: its concept names the card as `style_card` in the mocks file
(`docs/MIX.md`), and once the mock is made the workspace report says so in
`inspiration_used` (only when the directive's `features.inspiration_used` is
true), which closes his tick in Control Center. Past its date and unused,
his Publish Board says so in one line. A Content tick is content-engine's to
make into a piece, never this engine's.

**Identity.** Slug `makeyourmindup`, `engine_id` `growth-makeyourmindup`,
`product_slug` `publication`. `run_id` is `makeyourmindup:<New York
date>:<kind>` (or `:runner`); the attempt id adds the start time. A second
run of the same kind on the same day with different content gets a 409:
the client reads the stored report back, never resends, and ends the
attempt `failed` with `report_conflict`.

**How the v2 work maps.** The job's selected queue items become proposals
(at most ten; the rest are holds):

| Pack kind | Wall | Closes on |
|---|---|---|
| daily | `post`, with the exact words | `published` |
| radar | `post`: one engagement task for the day (below) | `tapped` |
| conversion | `post`, the exact copy | `applied` |
| pitches, swaps, partners | never proposed: each item is a hold (below) | not reported |
| report | `strategy` | `reviewed` |
| numbers | `none` | `verified` |

**Outreach never goes to Control Center** (Ruling, Krish, 2026-11-05;
`AGENTS.md`, "Outreach for Make Your Mind Up"). Make Your Mind Up outreach is
this engine's own, owned by the Acquisition engine, and Krish enacts it in
his own Codex sessions on the exact payload he approves. So `cc finish`
turns every pitches, swaps or partners item into a hold with the reason
"Make Your Mind Up outreach is this engine's own, enacted in Krish's Codex
sessions; it never goes to Control Center" (`engine/cc_loop.py`,
`OWNED_REASON`), and `post --deliver` refuses those packs. Only Mindmake's
own outreach is Control Center's.

**The engagement task (protocol 1.14.0).** The radar's selected replies and
comments go as one ask, `makeyourmindup:engage:<New York date>`, never one
proposal each: Control Center's version 2 action of kind `copy_open` on the
`engage` channel, behind `post`, with no stage. Its `exact_payload` is the
canonical JSON `{version: 2, channel: "engage", kind: "copy_open", body,
taps: [{label, text, url}]}`: each tap the exact words to copy and the public
https page to open. Krish pastes and posts each one himself and marks the
task carried out (`tapped`); nothing in this engine or Control Center posts.
The task carries as many as cleared the bar, up to today's cap
(`intensity.json`: 5, then 10, 15 and 20 at U3, U4 and U5); a tap past the
cap, or one with no public https page or with an address or a phone number
in its words, is held by name. The report goes at 1.14.0 only where
capabilities list it and `features.copy_open` is true. If Control Center
cannot take the task (`schema_version_unsupported`,
`schema_version_unconfirmed`, `copy_open_unsupported` or a 400), the loop
rebuilds the report once with the same taps as one plain `advice` proposal
behind `post`, at the old version, and says so; nothing else is resent.
The wire shape is in `docs/control-center/ENGINE-PROTOCOL.md`.

`proposal_id` is `makeyourmindup:<item_id>`, so it survives a copy edit
while `payload_sha256` (SHA-256 of the canonical `{channel, exact_payload,
target}`) changes and sends the edit back to Krish. `why` carries
`why_now` plus the minutes, `close_condition.reference` carries the
`success_check`, `expires_at` is kept and https evidence links travel as
`evidence[]`. Deferred and `blocked_by` items become `holds[]`. Completion
labels Krish confirmed go in a `--completions` JSON list,
`{label, item_id, at, evidence_url, confirmed_by: "Krish"}`, where the
label is Published, Sent, Applied, Verified or Reviewed; each becomes an
event. Skipped is his Purge and arrives as `declined`. Planned experiment
templates are `strategy` proposals for his decision to start one, sent once
by the GitHub runner (below).

**Objectives.** `new_subscribers` (people, New York week) is the sum of this
week's Substack `new_free` observations, validated and added with the same
rules as `growth.py measure --aggregate`, only when the windows start on
Monday at midnight New York time and have no gap. Anything else is `null`
with its reason; a measured zero is `0`. `paid_boosts_usd` is always
missing with its reason: this engine has no spend authority, bought no
boosts and does not read platform ad spend.

**Decisions.** `finish` records every proposal it reported in
`.scratch/cc/proposals.json` and Krish's decisions in
`.scratch/cc/decisions.json`. A yes counts only when its `payload_sha256`
equals the reported payload. Even then the engine posts and sends nothing:
the yes means Krish approved those exact words, and he acts.

**The GitHub runner.** `.github/workflows/control-center.yml` runs on
`repository_dispatch` (`cc-growth-directive`) and `workflow_dispatch`, with
`contents: read`, one concurrency group and a 20 minute timeout. It runs
`growth.py cc runner --deliver`: the unit tests, `doctor --offline` and the
fixture `dry-run` in child processes that never see a key, and a read of
the committed channels, journeys and experiments. Its report is `held`
(`degraded` with a failed attempt if a check fails), both objectives are
missing with "Measured only in the publication workspace", and its log
prints only codes, counts and digests, never the directive, because this
repository is public. It uploads no artifact. A missing secret or variable
stops the job with an error and nothing reported.

**Each ask once** (plan item D2, 2026-10-29). Before it reports, the runner
reads what Krish already has (`already_sent`). A clean runner keeps no state,
so Control Center is the ledger. It reads every decision since 2026-10-19,
page by page, because the route serves only the oldest 100 after `since`; a
decision dated after the run's own time is not counted. It also reads the
latest earlier runner report of the same mode within 14 days that read its
own ledger. That report's proposals and its "Waiting on Krish, not sent
again" holds count as pending, and its "Answered by Krish, not sent again"
holds (`id=decision`) count as answered, so a decision the route no longer
reaches still counts. A report of the other mode (a synthetic run never
counts for a live one), or one that could not read its ledger, is passed
over. Each hold names whole ids, as many as fit its 1,000 characters, and
starts another when they do not; an id is never clipped. An ask he answered
(approved, declined or done, on any payload) is never sent again; one still
waiting is named in a waiting hold and not resent. Today's own report is
never read, so a rerun with the same `--now` makes the same report and
replays; a rerun at a later time changes `observed_at`, and may see a newer
decision, so Control Center keeps the first report and the attempt is
journaled as a conflict. If any read fails, or the decision pages do not
end, nothing is proposed and the hold says so. Fourteen days in a row
without a readable ledger would lose what it carried, and the asks would go
again. The standing W45 to W52 plan (`specs/standing-plan.json`, docs/RUN.md
"Gates") goes once as `stage: "plan"` behind `strategy`; its words are frozen
there so the digest he approves is the one every go-live names, and a changed
plan is a new `proposal_id`. Each amplification pilot in `lists/pilots.json`
is reported by its verdict path, never as a proposal: its recorded verdict,
or a hold saying it awaits measurement (or a verdict), when its judge window
ends and what closes it.

**Errors.** 401 `unauthorized`, 403 `forbidden`, 409 `report_conflict` or
`engine_inactive`, 413 `payload_too_large`, 429 `rate_limited`, 5xx
`server_error`, a redirect `redirect_refused`, no answer `unreachable` or
`timeout`. Remote bodies are never echoed, and the bearer never appears in
output, files or exceptions. `tests/test_control_center.py` proves the loop
against a local stand-in server, including the worked example's digest.

### Krish's instruction and the engine's state (protocol 1.20.0)

Ruling (Krish, 2026-11-11): every growth engine's priorities, obsessions,
next steps and outstanding items feed live across Control Centre, and Krish
instructs each engine with his next best action, which starts it. His
words: "They are responsible for driving the overall success of each
venture, so make sure I can instruct each one with my next best action and
have it get going (as well as always understand the current state of play
and what's outstanding)." The code is `engine/engine_state.py`; the tests
are `tests/test_engine_state.py`.

**Nothing new until it is served.** Every new field is sent only when the
directive says `features.engine_state: true`. Before that the reports are
exactly as they were. A report carrying one goes at 1.20.0, only where
capabilities list it and `features.engine_state` is true. If Control Center
cannot take it (`schema_version_unsupported`, `schema_version_unconfirmed`,
`engine_state_unsupported` or a 400), the loop sends the same report once
without the new fields and without any line naming his instruction, and
says "engine state not taken".

**His instruction.** `krish_instruction` is null (none open), absent (not
read today, or an older Control Center) or `{ id, words, given_at,
given_by, supersedes }`. It is never an approval: the walls do not move.

- The runner (the 05:10 UTC push, and a wake his instruction starts) cannot
  draft, so it acks `received` with the line that the next publication
  workspace job acts on it first. An instruction wake carries
  `client_payload.instruction_id`, and the workflow then runs `cc runner
  --deliver --wake gh<run id>.<attempt>`: that report's run_id is
  `makeyourmindup:<date>:runner:wake-<...>`, so it never conflicts with the
  morning's report, and it reads the morning's report before proposing, so
  nothing is proposed twice. A run by hand (`workflow_dispatch`) wakes the
  same way. A wake's run is named "control-center instruction wake" (the
  workflow's `run-name`), and the 05:40 UTC backup never counts it as the
  morning push (`engine/run/backup.py`), so an instruction given before
  05:40 UTC cannot stop the backup on a day the 05:10 push never came.
- A workspace job prints the block first at `cc start`, keeps it in
  `.scratch/cc/instruction.txt`, acts on it first, and finishes with
  `--ack started|done|blocked --ack-line "..."` (AGENTS.md, "His
  instruction"). Its report acks `received` (when no earlier report named
  it) and then what it did. `.scratch/cc/instructions.json` keeps the acks
  sent from this workspace, so a later job never sends `received` again and
  is told when one was acked done.
- The four engine sessions see it too. `cc start` also keeps it,
  structured, in the ignored `.scratch/cc/instruction.json`, and `growth.py
  engine start NAME` shows it first as `krish_instruction`: his words, when
  it was pulled (a pull from an earlier day says it may have closed since),
  and how to act on it. The session whose work it is acts on it first,
  inside the walls; another engine's is handed off. The session closes with
  `"instruction_ack": {"state": "started|done|blocked", "line": "..."}` in
  its learnings file, checked as `cc finish --ack` is (never his words) and
  kept as a pending ack in `.scratch/cc/instructions.json`, never in a
  committed record. The next workspace job's `cc finish` carries it to
  Control Center (when the job gives no `--ack` of its own) and clears it,
  so an engine session never writes to Control Center itself.
- `received` goes once: an earlier report naming the instruction (this
  engine's latest live reports, `GET reports?recent=10`, or the workspace's
  own record) counts. If those cannot be read, `received` is sent again,
  which Control Center counts as stale and ignores.
- A held engine is told only its hold (`krish_instruction` null). An
  instruction handed to it anyway is acked `received` and then `blocked`
  ("engine held"), and nothing is acted on.
- His words never reach a public log, a commit or a report: the runner
  prints only the id and what it acked, an activity line names the id
  (activity lines only), no state or ack line carries the id (24 hex
  characters can hold ten digits in a row, which Control Center reads as a
  phone number), and `cc finish` refuses an ack line that repeats six of
  his words in order.

**The engine's state**, on every report that pulls the directive (the
runner, every workspace job, the measure lane and, since 12 November, the
maker's standing-plan and weekly-ask reports, which pull it once a run in
`report_state`), because Control Center shows the newest live report's
state on every place. The handoff's records and release's claims pull no
directive and carry none, so for the hours between one of those and the
next runner or measure report Control Center shows no priorities or
obsessions and takes the next steps from NOW.md's "What is next":

- `priorities`: the North Star gap ("X of Y this week, U-n, short by Z"),
  then the levers `intensity.json` sets at this urgency (the subscribe
  route, the daily outreach drafts, the volume bounds), then zero paid
  boosts.
- `obsessions`: Krish's own quoted aims in `config/engine-state.json`, each
  kept only while the file it is quoted from still holds the quote word for
  word. Never a paraphrase and never a goal of the engine's own.
- `next_steps`: his open instruction first, then the newest now-notes'
  `Next:` lines (until the fold on main writes them into NOW.md), NOW.md's
  first "Next" item, the first unticked step of `docs/GET-GOING.md` and
  NOW.md's "Waiting on Krish" items, at most five, each a whole sentence or
  a whole leading clause of at most 200 characters, never cut mid-clause.

A field with nothing in it is left out of the report (`build_report`), as
the protocol asks, so Control Center says "Not reported yet" or, for
`next_steps`, shows NOW.md's "What is next" instead of an empty list.

Every line is plain text with no address or phone number; anything else
is refused here before it is sent.

## Autonomy loop

GET-GOING Step 1 on protocol 1.1.0 (`engine/control_center.py`,
`engine/cc_loop.py`, proved in `tests/test_autonomy.py` against the stand-in).

**Stages.** `proposal(..., stage=, parent_proposal_id=)` builds a `plan`, a
`go_live` (a send, post or spend naming its plan) or a `check_in` (a strategy
call naming its plan). A report is `1.1.0` only when a proposal uses those
fields, else `1.0.0`; `validate_report` refuses any other pairing. A 1.1.0
report goes only after capabilities list `1.1.0`, else the run fails closed
(`schema_version_unsupported`, or `schema_version_unconfirmed` when they
cannot be read) and nothing is downgraded or sent.

**Amendments.** `amended_sha256` must recompute as the SHA-256 of the
canonical JSON of exactly `{amount_usd, exact_payload}`, null when absent,
or it is held (`amended_digest_mismatch`). When it matches, his version acts.

**The go-live step.** `golive_actions(proposals, decisions, ledger, now)` is
pure and acts on nothing; `golive_review` adds a reason code for each hold. A
go-live acts only when never claimed, approved (latest dated decision) on the
digest its reported fields recompute to, with its plan approved and not
stopped, and in date. Holds fail closed: an undated decision on it or its plan
(`undated_decision`), a declined check-in whose record is not at hand
(`stop_unresolved`, every go-live), an expiry with no `now`
(`expiry_unchecked`) or unreadable (`bad_expiry`). A declined check-in or plan
stops the plan for good, even a later changed version. Spends and LinkedIn are
always held. Reports carry no `target`, so a go-live built with one is held.

**The ledger.** `claim_golives(root, ...)` reads the clock when given no
`now`, merges the staged proposals `remember()` kept, and claims each go-live
once by `proposal_id` in `.scratch/cc/golive-ledger.json` (`write_json` under
`locked`) before anything acts, with its stops and unresolved check-ins. The
caller passes every decision on each open plan, not only the latest read. The
ledger is local on the PC. On the GitHub runner, L0 autorelease seeds it
each run from the claims it reported to Control Center (one per go-live
whose every line is done, `makeyourmindup:claimed:<32 hex>`), so a go-live
acts once across clean runners and is only checked after.

**Objective.** Substack scope `publication` is all sources and wins;
`source:<name>` rows are added per source and summed, but only when a
`source:direct` row (any case) is among them: the numbers job records
attributed sources separately and leaves Direct unattributed, so without it
the sum would undercount. Any other scope, or attributed rows without the
all-source or direct row, makes `new_subscribers` missing, never a guess.
