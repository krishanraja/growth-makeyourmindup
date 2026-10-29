# The concept manifest: what a release executor reads

Ruling (Krish, 2026-10-29): approval moves to the idea and the mock on
Instagram, YouTube, TikTok and X, within three or four posts a day each
(`CHANGES.md`, R101, R104). This page names the exact fields a release
executor (the one scheduler, `engine/run/autorelease.py` when it lands) reads
to post from an approved concept. `engine/run/release.py` enforces every rule
below today; an executor that schedules must enforce them too, and never
schedules anything `release plan` would hold.

## Where the authority comes from

His decision on the week's mix plan proposal (`makeyourmindup:mix:<ISO week>`,
stage plan, wall strategy, `docs/MIX.md`), read from Control Center in the
loop's own run. Right after the loop matches decisions (`engine/cc_loop.py`),
`engine/run/decision.py` checks the plan file against the proposal it
reported, keeps the result in `.scratch/mix/decision-<Monday>.json`, and writes
each run's `decision.json` and spec signature. `growth.py run decide SPEC` does
the same for a run spec made later. Nothing else writes them, and never by
hand.

- His yes on the plan's exact `payload_sha256` approves each ready concept.
- His amended yes, when `amended_sha256` recomputes, approves each ready
  concept whose line stands in his version exactly; a line he deleted or
  changed stops that concept (`stopped_concepts`; changed ones also in
  `changed_concepts`).
- His no, a declined check-in on the plan, or the plan stopped in the go-live
  ledger stops every concept. A stop never lifts.
- A stale yes, an amendment that does not recompute, an undated decision or a
  plan file changed after it was proposed approves nothing.

## decision.json (`specs/schema/decision.schema.json`)

The go-live part is unchanged: `run_id`, `proposal_id`, `decision`,
`decided_at`, `slots` {slot_id: payload_sha256}, `amended`. With no go-live
for the week the file is concept-only: `proposal_id` null, `decision` null,
`decided_at` null, `slots` {}. The approved mix plan is then the only
authority, and only posts made from its concepts can release.

The concept part:

- `concepts`: {`concept_id`: `concept_sha256`}, the approved concepts.
- `concept_proposal_id`: the week's mix plan proposal.
- `concept_decision`: `decision` (approved or declined), `decided_at`,
  `plan_payload_sha256`, `amended`, `amended_sha256`, `read_at`.
- `concept_manifest`: one entry per key of `concepts`, with `concept_id`,
  `lane`, `idea`, `claim`, `source_url`, `piece_id`, `mock_sha256` (the mock
  file hashes), `placements` (each `channel` and `format`) and
  `concept_sha256`. The sha256 of the canonical JSON of the entry's first eight
  fields (`engine/concepts.py` `concept_payload`) must equal `concept_sha256`
  and `concepts[concept_id]`; an entry that does not recompute authorises
  nothing.
- `concept_daily_caps`: {channel: scheduled posts a New York day may carry},
  read when the file was written. The cap counts every scheduled post on the
  channel across every run, signed or derived. Release enforces the live cap;
  an executor never exceeds either.
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
- no decline in the go-live ledger still unmatched to its plan.

A slot with no `concept_id` still needs its digest in `slots` from the week's
go-live decision, exactly as before.
