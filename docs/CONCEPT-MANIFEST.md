# The concept manifest: what a release executor reads

Ruling (Krish, 2026-10-29): approval moves to the idea and the mock on
Instagram, YouTube, TikTok and X, within three or four posts a day each
(`CHANGES.md`, R101, R104). This page names the exact fields a release
executor reads to post from an approved concept. The one scheduler,
`engine/run/autorelease.py`, has landed (L0, `release.yml`); on GitHub
Actions it reads its authority only from Control Center (below, "On GitHub
Actions"), never from a local file, a dispatch payload or a PC `.scratch`.
`engine/run/release.py` holds every rule below as functions, and
autorelease calls them rather than copying them, so it never schedules
anything `release plan` would hold.

## Where the authority comes from

His decision on the week's mix plan proposal (`makeyourmindup:mix:<ISO week>`,
stage plan, wall strategy, `docs/MIX.md`), read from Control Center in the
loop's own run. Right after the loop matches decisions (`engine/cc_loop.py`),
`engine/run/decision.py` checks the plan file against the proposal it
reported, keeps the result in `.scratch/mix/decision-<Monday>.json`, and writes
each run's `decision.json` and spec signature. `growth.py run decide SPEC` does
the same for a run spec made later. Nothing else writes them, and never by
hand.

- His no on the plan, on any digest at any time, or a stop on it in the
  go-live ledger stops every concept. It is read first, before anything
  about the plan file is trusted. A stop never lifts.
- His yes on the plan's exact `payload_sha256` approves each ready concept.
- His amended yes, when `amended_sha256` recomputes, approves each ready
  concept whose line stands in his version exactly; a line he deleted or
  changed stops that concept (`stopped_concepts`; changed ones also in
  `changed_concepts`). If he changed any other line of the plan (a cap, a
  channel, the slots, the walls), nothing is approved: his terms cannot be
  enforced from the engine's plan (`concept_hold` `amended_plan_terms`).
- A stale yes, an amendment that does not recompute or an undated decision
  approves nothing.

Every loop run, and every `run decide`, checks the approval again and fails
closed: decision.json is rewritten with `concepts` {} and the reason in
`concept_hold` while any of these holds:

- `plan_untrusted`: the week's plan file is missing, or its words no longer
  rebuild from the file and today's config, or its digest does not recompute;
- `stale_approval`: his yes was on a plan digest that is not the plan in
  force (`concept_decision.plan_payload_sha256` differs);
- `stop_unresolved`: a declined check-in in the go-live ledger is not yet
  matched to its plan, or the ledger cannot be read. The loop records stops
  and unresolved declines in that ledger each run (`cc_loop.record_stops`);
- `amended_plan_terms`: as above;
- `not_applied`: the record could not be applied for another reason.

## decision.json (`specs/schema/decision.schema.json`)

The go-live part is unchanged: `run_id`, `proposal_id`, `decision`,
`decided_at`, `slots` {slot_id: payload_sha256}, `amended`. With no go-live
for the week the file is concept-only: `proposal_id` null, `decision` null,
`decided_at` null, `slots` {}. The approved mix plan is then the only
authority, and only posts made from its concepts can release.

The concept part:

- `concepts`: {`concept_id`: `concept_sha256`}, the approved concepts.
- `concept_proposal_id`: the week's mix plan proposal.
- `concept_decision`: `decision` (approved, declined or held), `decided_at`,
  `plan_payload_sha256`, `amended`, `amended_sha256`, `read_at`; null when no
  decision is recorded.
- `concept_hold`: null, or the reason (a code from the list above first) no
  concept is approved this run. An executor schedules no derived post while
  it is set.
- `concept_manifest`: one entry per key of `concepts`, with `concept_id`,
  `lane`, `idea`, `claim`, `source_url`, `piece_id`, `mock_sha256` (the mock
  file hashes), `placements` (each `channel` and `format`) and
  `concept_sha256`. The sha256 of the canonical JSON of the entry's first eight
  fields (`engine/concepts.py` `concept_payload`) must equal `concept_sha256`
  and `concepts[concept_id]`; an entry that does not recompute authorises
  nothing.
- `concept_daily_caps`: {channel: the most scheduled posts a New York day may
  carry on it, as the approved plan states} (`engine/mix.py` `ceiling`). The
  cap counts every scheduled post on the channel across every run, signed or
  derived. Release enforces the lower of this and the live cap
  (`engine/intensity.py` `daily_cap`); an executor never exceeds either.
- `stopped_concepts`, `changed_concepts`: concept ids. A stopped concept holds
  every post made from it, including one signed alone.

## The spec signature

`signature.concepts_digest` is the sha256 of the canonical JSON of
`concepts`; `signature.concept_proposal_id` names the week's mix plan and
equals `decision.json`'s. Concept-only: `signature.go_live_proposal_id` null
and `signature.decision_digest` the sha256 of `{}`. Any mismatch refuses the
whole run.

## A derived slot

A run spec slot made from a concept names it in `concept_id` (outside
`payload_sha256`). It needs no digest of its own in `slots`. Its mock is its
`assets`: each `assets[].sha256` must be one of the concept's `mock_sha256`
(a text-only format carries none), its `channel` and `format` one of the
concept's `placements`, and its `words` must carry the concept's `claim` word
for word. Release binds the post to its exact bytes by its own
`payload_sha256`, so a scheduled Buffer post is rebuilt and checked against
that digest, never trusted.

Each derived post also needs, at release:

- `review/<slot>.json` passing at its own `payload_sha256` (the creative bar);
- room under its channel's daily cap;
- `publish_mode` engine (LinkedIn stays his click: never a concept post);
- copy lint, share asks, the ecosystem route, the Buffer channel lock and,
  on a route not yet verified, the route's one capability check;
- no decline in the go-live ledger still unmatched to its plan, and no
  `concept_hold`.

A slot with no `concept_id` still needs its digest in `slots` from the week's
go-live decision, exactly as before.

## On GitHub Actions

The runner has no `decision.json`: autorelease derives the same concept
part from Control Center readbacks, bound by digest, every run.

- The plan. The handoff (`growth-mix-plan`, `engine/run/handoff.py`)
  checks the plan file's closed shape, recomputes every `concept_sha256`
  and the plan's words, and reports the plan proposal in its own report
  (`<proposal_id>:<payload_sha256[:12]>`) with its concepts beside it. A
  week over 8,000 characters is split into parts in order: part 1 is
  `makeyourmindup:mix:<ISO week>` with every plan line, then `:p2`, `:p3`,
  each repeating the terms; one ask at a time. A version record
  (`makeyourmindup:mixplan:<ISO week>:<n>`) names the parts in force; the
  highest n wins, so a yes on an earlier digest is `stale_approval`.
- The readback. autorelease reads his decisions (every page, decline
  first), each part by its digest, checks each part's concepts against its
  words (`engine/run/decision.py` `part_errors`), and judges each part with
  `judge`, the loop's own rule (`cc_readback`). His no on any part stops
  every concept of the week; a concept is approved once part 1 and its own
  part are. `concept_part` then gives `concepts`, `concept_manifest`,
  `stopped_concepts`, `concept_hold` and `concept_daily_caps`, as `apply`
  writes them.
- A derived slot. The go-live manifest dispatch carries it with its
  `concept_id` and `review`; the handoff rebuilds it from its Buffer draft
  and reports the review at `makeyourmindup:review:<payload_sha256[:12]>`
  (the full sha in the record), listed in that New York day's index
  (`makeyourmindup:derived:<day>:<n>`). It is never a go-live.
- The checks, in order: a `concept_hold` or an unresolved stop holds every
  derived slot loudly; then on the draft read fresh, release's own
  `concepts.authority` (placement, mock files, the claim, not stopped),
  `concept_post_hold` (the review at the rebuilt digest, judged by
  `spec.review_reason`; the daily cap counted from every post scheduled on
  the channel that New York day in Buffer, plus each post he signed for it),
  copy lint, share asks, the route and the channel lock; then the draft
  digest, meta, format shape and the 5 to 90 minute window.
