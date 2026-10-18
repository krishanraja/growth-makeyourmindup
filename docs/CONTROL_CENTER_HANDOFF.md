> **Superseded on 2026-10-18** by [`docs/CONTROL-CENTER-BRIEF.md`](CONTROL-CENTER-BRIEF.md): Control Center now runs one protocol for every growth engine. Kept for its history.

# Control Centre handoff: MYMU growth engine

Prepared 17 October 2026. Implementation scope: this growth repository only.
Krish's instruction: "you are not to do any actual work in control-center,
only pass me a brief once you have completed your work". No Control Centre
code, configuration, schema, observation or pack writes were made in this
implementation. No deployment, social publication or settings changes.

Before Krish corrected the scope, the earlier audit had already stored a
report pack in Control Centre. This implementation did not update or remove
that existing record; the no-write boundary applies from the correction.

The receiving owner can implement this brief in Control Centre separately.
The growth engine is ready to supply the records described below. This
brief is the handoff, not a request for another discovery exercise.

## Problem and resulting experience

A draft pack currently stores copy and Posted/Skip marks. The upgraded
engine also knows the source, placement, priority, estimated effort,
expiry, prerequisites, actual measurement window and a verifiable next
step. The current API discards that richer information. As a result, Krish
cannot reliably work all channels in one budget, distinguish a proposed
fix from a verified fix, or trace a growth recommendation to its evidence.

Extend the existing Home waiting list and Growth views so that Krish sees
one useful next action, the supporting evidence, the time it needs and a
clear way to record the real result. Reuse the existing Clear/Bump/Purge
interaction language where appropriate. Do not add another overlapping
work queue, dashboard or publishing system.

## What is already implemented here

- Versioned evidence envelopes, literal source excerpts, stable item and
  copy-revision IDs, platform/house checks and explicit legacy projection.
- Proper URL parsing, complete attribution tags, placement identity and a
  separate original-acquisition/internal-placement contract.
- New York business dates, Windows fallback, delayed publication recovery,
  body revision detection and explicit-link-only article/video pairing.
- Structured measurement validation, duplicate-window replacement, overlap
  refusal, null availability and conservative attributed subscriber yield.
- A global 20-minute queue, 30 on Sunday; priorities, estimates, expiry,
  prerequisites and deferred reasons. All eight job prompts use it.
- Relationship events that distinguish drafted from confirmed sent/replied/
  booked/published; no draft-driven cooldown or stage advancement.
- Planned experiments and incomplete-window/sample guards; no automatic
  causal, kill or scale conclusion.
- Full channel/journey inventory and actionable audit in
  `docs/CHANNEL_PLAYBOOK.md`. No external surface was changed.

## Current contract, verified read-only

Reference: Control Centre main at
`379d193052027fe290bafca4f37f9ef902a0b112`, shared `growthPacks.ts`, checked
17 October. Re-read the live main before implementation to detect drift.
The compatibility test runs against a separately available read-only
snapshot; private Control Centre source is not copied into this public repo.

| Capability | Current behaviour | Consequence |
|---|---|---|
| POST `/api/growth/packs` | Engine bearer; accepts existing eight kinds and legacy fields | Keep this delivery contract working |
| GET packs | Bearer or session; default 14 days, maximum 60, optional kind | Do not assume all-time history or full retention cohorts |
| PATCH status | Session; item index and Posted/Skipped/null | No stable item identity or fix verification |
| Legacy item | platform, target_url, target_name, why, text, status | Other item fields are discarded |
| Legacy number | platform, followers, new_this_week, reach, visits, new_free, new_paid, unsubscribes, top_source, note | Windows, capture times, units and source lineage are not structured |
| Pack limits | 40 items, headline 500, item text 4000, real date, HTTP(S) URLs, finite counts | Preserve limits and draft-only refusal of action keys |
| Rerun status | Unchanged platform plus text keeps existing marks; changed text may lose them | Do not claim every rerun loses marks; migrate to stable IDs |
| Existing UI | Growth Next/Packs/Week/Numbers/Places/Buyers plus Home waiting list | Extend these surfaces rather than creating a parallel app |

The legacy API's house rule also scans URL text, so some percent-encoded
functional destinations can be rejected. The engine refuses these at export
rather than silently altering a native referral parameter. A future parser
fix should distinguish URLs from prose, with regression coverage.

## Delivery phases and acceptance criteria

### 1. Preserve and admit the richer record

Add a backward-compatible v2 input or versioned envelope endpoint within
the existing growth ingestion boundary. Do not send unknown fields to the
old parser and assume they survived. Keep legacy reads and clients working.
The v2 source of truth is `engine/packs.py` and `docs/ENGINE.md` here:

| Record | Required fields |
|---|---|
| Envelope | schema_version, prepared_at, pack, evidence, metadata, observations |
| Item identity | item_id, revision_id, asset_id, platform, placement, variant |
| Source evidence | evidence_id, kind, url, literal excerpt, observed_at; optional private snapshot |
| Work instruction | why_now, priority, estimated minutes, success_check, blocked_by, expires_at |
| Measurement | metric, unit, window_kind, platform, scope, asset_id, source, start/end, timezone, captured_at, availability, value, missing reason |
| Relationship event | event_id, person_id, type, at; real actions require human confirmation and evidence |

Use stable item identity for upsert and status continuity. A changed revision
must be reviewable without silently reopening a completed action or marking
new copy as published. A deleted/replaced action needs an explicit history
entry. Preserve existing platform/text marks during migration; ambiguous
matches need review. The engine never sets real publication status itself.

Accept only the authenticated engine or authenticated session's allowed
scope. Keep excerpts/private evidence within the proper access boundary;
never expose message URLs or dashboard captures in a public report. No
PII in query strings or analytics events. Keep the supported draft-only
rule and refuse all send/post/publish/schedule action keys.

Acceptance: ingest then read a v2 fixture and assert field-for-field source,
identity, units and windows survive. Repeat the same record without making
another action. Change text, inspect revision history, and confirm existing
real action evidence remains attached to its original revision. Existing
legacy pack tests continue to pass. No posting or sending is triggered.

### 2. One action list with the right completion controls

Admit actionable growth items to the existing Home waiting list using its
established row/admission adapter. Inspect that adapter's actual shape;
do not bypass it by inventing another table or copying pack cards wholesale.
Use these semantic mappings in the existing row format:

| Existing row concern | Growth value |
|---|---|
| Source/deep link | Growth item and exact evidence/source surface |
| Clear action | Specific next action and verifiable success check |
| Urgency/order | Priority, expiry, prerequisite and why now |
| Time | Labelled estimate; measured effort kept separately |
| Completion | Event appropriate to the action type with evidence |
| Bump | Deliberate defer date/reason; expired replies require fresh evidence |
| Purge | Explicit skip/archive with reason, preserving historical actions |

Group by reader journey or current priority while keeping channel visible.
Budget is one total across all jobs, including Wednesday's radar/partners/
daily work and Sunday's review. Show the selected work and deferred reasons;
do not imply the estimate is measured effort. Reports/numbers are read-only
information, not copy-to-post tasks. A blocked video is not an actionable card.

Use an appropriate completion label: Published for a social draft, Sent for
an outreach draft, Applied for a settings/copy change, Verified for a tested
fix, Reviewed for a report, Skipped for a conscious rejection. Applying a fix
must not mark it verified. Krish supplies publication/message URL and time,
or an explicit private confirmation where no public link is possible.
No platform API action follows a completion button.

Acceptance: a mixture of jobs fits one daily budget; handled and expired
items cannot reappear as ready on rerun. A report has no Posted control.
An Applied website fix stays awaiting verification until its success check
has evidence. A draft partner message leaves relationship state untouched.
Mobile navigation exposes the action and evidence without opening six tabs.

### 3. Honest numbers and experiment review

Extend Numbers/Week with measurement availability, capture freshness, actual
source windows, units and scope. The denominator must be visible beside a
yield or conversion value. Views are not unique reach; a later follower
snapshot is not a daily acquisition event. Repeated rolling-week captures
replace the exact window; they do not add to it. Show direct as unattributed.
A free-to-paid upgrade changes membership, not necessarily total people.

Original acquisition and internal journey events are separate. Link external
placements to confirmed subscription events only through a supported,
consented provider mechanism; otherwise show the gap. The website owner's
attribution implementation is a separate surface task, not solved by adding
a dashboard chart. Do not claim a correlation proves causation.

A planned experiment shows hypothesis, comparison, primary metric, complete
window, sample requirement, quality guardrail, owner and decision rule.
Keep low-sample decisions at Collect. Retention requires complete 30-day
cohorts; retained subscribers per hour requires measured effort. Both remain
unknown until the data exists. Open rates alone are not activation proof.

Acceptance: duplicate daily captures cannot inflate a week; overlaps and
mixed scopes cannot generate a total/yield; unavailable is visibly different
from zero. A delayed source remains dated and visible. An incomplete cohort
or a tiny experiment cannot trigger an automatic kill/scale recommendation.

### 4. Close the surface-verification loop

Use the existing Places/Next context to show each channel's entry, matched
landing, subscription and activation path. Import `channels.json` and
`journeys.json` as intent, then attach real observed checks; do not mark the
paths verified simply because a configuration file lists them.

For each change: observed defect, exact surface, copy/config proposal,
owner, prerequisite, estimate, status and verification evidence. Start with
the seven priority findings in `docs/CHANNEL_PLAYBOOK.md`. Put the series
cadence and benefit text fixes ahead of speculative new content volume.

Acceptance: opening a journey shows the actual broken/unverified step,
what to do and how to prove it worked. An unavailable platform feature is
labelled conditional. No tool changes a profile, welcome email, setting or
subscription during an audit.

## Access and visibility that remain separate

The earlier audit verified GitHub repository access and Vercel project
visibility. The implementation's runtime itself has no bound growth token
or signed-in social dashboards. Krish says the GitHub secret exists;
GitHub secrets cannot be read back. Vercel visibility does not grant native
Substack/YouTube/Instagram/TikTok/X/LinkedIn/Spotify insights automatically.
Record each as available/signed out/not connected/not shown, with a check date.
Do not claim complete private analytics or exact subscriber/retention counts.

The audit found the main-site property absent from the dashboard registry,
incomplete native social insight coverage, and stale/partial platform
registry entries. These are dated observations to recheck before changing
connections. The AEO integration belongs to its separate paid engine; read
its results only. Substack's own article sitemap/NewsArticle output already
exists; do not build a duplicate based on an incorrect missing-schema claim.

## Handoff is complete when the receiving implementation proves

1. Legacy and v2 ingestion round-trip without silent metadata loss.
2. Identity/revision migration keeps real action history on rerun and edit.
3. Home admits one budgeted action list with type-appropriate completion.
4. Evidence, actual execution, availability and freshness are visible.
5. Metric windows, denominators and incomplete cohorts remain honest.
6. Surface fixes need a separate verification event and can be worked on mobile.
7. Existing platform and credential boundaries remain draft-only.

This growth repository has supplied the implementation, checks and brief.
Control Centre work above has deliberately not been performed here.
