# Run sessions

Read first in every run session (`run pack` puts it atop each pack). Plan:
`docs/plans/2026-10-27-engine-architecture.md` (Krish, 27 Oct).

## What a run session does

A run carries one signed spec (`growth-run-spec/1`) from draft to verdict:
a `week`, one published `piece` (days 0 to 7) or one `express` idea. Krish
signs exact payloads; the engine releases exactly what he signed, reads it back
and measures it. LinkedIn stays his own click. Nothing is spent.

A session does one job, then ends at a gate packet:

- **Release, two paths.** L0 `run autorelease` schedules the go-lives he
  approved in Control Center (`release.yml`, never by hand), one go-live per
  New York day ("Approve each day Monday", 28 Oct). `run release` is only
  each route's capability check. Only this engine's eight Buffer channels;
  copy lint, a share ask or a format unlike its draft holds. A draft is
  scheduled 5 to 90 minutes before its time, so a No first stops it;
  scheduled after a No, or while a stop cannot be read, fails the run.
  Sessions save drafts, never `--deliver`. Scheduled is never live.
- **Measure:** L0 `measure.yml` gives verdicts thrice daily; a session reads
  back "sent" and native URLs, metrics at their windows and the express
  intake.
- **Express:** one approved idea into the waiting go-live, or its own.

No mid-turn questions: each becomes a gate packet and the session ends. A
run session commits nothing to `engine/`.

## Lanes

L0 runs alone on GitHub Actions, L2 is one press in Control Center, L3 his
hands (`docs/LANES.md`). No Claude routines; makers follow `docs/TASTE.md`.

## Commands

All offline (`python growth.py run ...`); none posts, sends, schedules or
spends.

- `run new --start YYYY-MM-DD [--kind week|piece|express]`: a skeleton,
  computed fields filled.
- `run new --from DRAFT --out SPEC`: fill `week_target`, every
  `payload_sha256` and each `share`'s `forward_line`. Never by hand.
- `run drafts SPEC --posts DIR`: Buffer ids and `meta` from `get_post`
  readbacks.
- `run lint SPEC [--record]`: errors (exit 1) and warnings as JSON.
- `run status SPEC`: each slot's stage, computed from evidence.
- `run pack SPEC [--day YYYY-MM-DD] [--channel ID]`: this pack. Over 36 KB,
  or a part over its budget (this doc 8 KB, slice 10, cards 12, findings
  and status 6), is refused; narrow it. Crew cards load by the
  week's registry flag (`w45`), else by channel.
- `run card lint FILE`: a Codex task card, before dispatch.
- `run release plan|check SPEC ...`: exact Buffer calls, then readback
  evidence.
- `run send-test SPEC SLOT`: the blind send test.
- `run calendar|plain|canva lint`: the V1 calendar, plain English, the
  brand kit.
- `run measure`, `northstar`, `verdict`, `cost`, `ga4`: see `--help`.

Keep a real spec at `.scratch/runs/<run>/spec.json`, never in git: it holds
unpublished words. The run folder is the `run_id` with each `:` as `_`.

## What lint refuses

Schema errors; a `week_target` off the `docs/NORTH_STAR.md` ladder rung for
the New York Monday of `window.start`; a `payload_sha256` that does not
recompute; words failing `prose_errors` (em dashes, stock phrases, house
rules) or content-engine's copy lint (eyebrow labels, asterisks, AI notes,
take labels); a snackable slot with no valid `share`, a stale `forward_line`
or a share ask (`social/share.json`); an unknown channel or format, or one the
channel does not take (`social/channels`, `social/formats`); `publish_mode`
not `krish_click` on a human-publish-only channel (LinkedIn) or not `engine`
elsewhere; a `krish_click` slot with a `due_at`; `spend_usd` above 0; two
experiments on one channel; an unregistered arm; an asset hash not 64
lowercase hex; more scheduled slots on a New York day than the channel's
`daily_posts_target` (null: no cap; U3+ lifts it to its policy bound; Story
frames do not count); an engine slot asset in no manifest with a
`creative_approval_ref` (release holds it too); a window not New York
midnights 7 (week, from a Monday), 8 (piece) or 1 (express) days long; a slot
with no `ecosystem_cta` (docs/ENGINE.md). Warning: an engine slot with no
`due_at` cannot release, and the daily cap counts only scheduled slots.

A slot's `payload_sha256` digests (`canonical_json`) exactly `channel`,
`format`, `words`, ordered asset hashes, `link_placement`, `due_at`,
`publish_mode`, `meta` (an edit's other fields), `buffer_channel_id` and the
run-spec domain; a go-live line has its own, so no yes acts on both paths.

## Readiness is computed, never written

`drafted, linted, reviewed, signed, queued, live, measured, verdict`. Each stage
needs the previous one and its evidence under `.scratch/runs/<run>/`:

- `lint.json`: from `run lint --record`, no errors, bound to the spec less
  `signature` and `buffer_draft_id` (signing and queueing keep it valid;
  other edits need `--record` again).
- `review/<slot>.json`: `verdict` "pass", a `lens` id from a fresh-context
  reviewer and the `payload_sha256` it reviewed. Snackable slots use lens
  `send-test` (`run send-test --answer FILE --record`).
- `decision.json` (what `run release` reads): `run_id`, `proposal_id`,
  `decision` "approved", `decided_at`, `slots` {slot: signed digest} and
  optional `amended` {slot: his amended payload}. The spec `signature` names
  `proposal_id` and holds `decision_digest`, the sha256 of the canonical
  `slots` map. Each digest equals the slot's `payload_sha256` or recomputes
  from his amended payload, which is what releases: rewrite the slot with it
  first. A mismatch is never signed.
- `queued/<slot>.json`: `status` "scheduled" or "draft" (always "draft" for
  `krish_click`) and the signed digest as `payload_sha256`.
- `live/<slot>.json`: `status` "sent" and an https `native_url` read back from
  the platform.
- `measured/<slot>-<window>.json` (`24h`, `72h`, `7d`) with `captured_at`.
- `verdict/<slot>.json`: `works`, `neutral`, `fails` or `insufficient`.

A missing or invalid file stops the slot at the previous stage, with a reason.
Draft counts are never outcomes.

## Gates

- **Standing plan:** one `plan` proposal (wall `strategy`) for W45 to W52;
  every go-live names it as `parent_proposal_id`.
- **G-A, Sunday (up to 15 min):** the week's Notes, Threads and evergreen slots,
  a go-live a day; each up to 8,000 characters, split if larger.
- **G-B, Mon/Wed/Fri (up to 5 min each):** a piece's batch across channels.
- **G-X, express (up to 2 min):** joins the waiting go-live; one a day.
- **Check-ins:** Sunday (with the What-Works ledger) and Wednesday.

Control Center shows one ask per engine at a time. Release checks each slot's
bytes against its signed manifest line; a file in 4 Growth is never trusted.

## Budgets (provisional until the Phase 0 baseline)

- Measure up to 20 calls, express up to 15; 0.5M tokens each.
- Krish: 20 minutes a weekday, 30 on Sunday; gates first.
- Spend: 0. Over budget, the session ends at a gate packet; it never loops.

## Closeout (docs/ASSET-STORAGE.md)

1. Approved delivery assets and exact copy go to the Drive
   **4 Growth** library, one `YYYY-MM-DD - Topic - Channel` folder each with
   a SHA-256 manifest; no other Growth root.
2. Private evidence stays in `.scratch/`; never in 4 Growth, which anyone
   with its link can edit.
3. Lessons go to `social/lessons/`; run `python growth.py social check`.
4. Creative feedback goes to Content Engine through its handoff; it owns
   the craft.
5. Point `docs/SESSION-HANDOVER.md` and `NOW.md` at the dated private closeout:
   what is draft, approved, scheduled, published, held or unknown.
6. Snapshot run evidence before cleanup.
7. A changed automation: verify its owner and schedule; never duplicate it.

## Rules a run session also reads

- `invariants/rules.json`: each rule with its verbatim source quote.
- `docs/PUBLISHING-AUTHORITY.md`: who may publish where.
- `docs/ACCOUNT-VOICE.md`: X, TikTok, Threads and LinkedIn are his personal
  accounts, in his own voice (sincere, warm, humble).
- `AGENTS.md` ("The rules that never bend", "Autonomy"): outreach belongs to
  Control Center; this engine never delivers pitches, partners or swaps
  packs.
