# Run sessions

Read first; `growth.py run pack` puts it on top of every pack. Plan:
`docs/plans/2026-10-27-engine-architecture.md` (Krish, 27 Oct 2026).

## What a run session does

A run carries one signed spec (`growth-run-spec/1`) from draft to verdict:
a `week`, one published `piece` (days 0 to 7) or one `express` idea. Krish
signs exact payloads, or a concept's idea and mock (R101); the engine releases
exactly that, reads it back and measures it. LinkedIn stays his click.
Nothing is spent.

A session does one job, then ends at a gate packet:

- **Release:** only through `growth.py run release`, for an approved go-live
  decision the engine reads from Control Center in its own run ("Approve each
  day Monday", 28 Oct), or the week's approved mix plan for posts made from its
  concepts (docs/CONCEPT-MANIFEST.md). `decision.json` is written only from
  that readback, never by hand. It acts only on this engine's eight Buffer
  channels, pinned by channelId, holds a slot whose words fail the copy lint,
  and releases only an unverified route's first post, its check.
  An interactive session never releases or uses `--deliver`.
  Scheduled is never live.
- **Measure (daily):** read back "sent" and the native URL, capture metrics at
  their windows, write verdicts, check the express intake.
- **Express:** one approved idea into the waiting go-live, or its own.

No mid-turn questions: every question becomes a gate packet and the session
ends. A run session commits nothing to `engine/`.

## Commands

All offline (`python growth.py run ...`); none posts, sends, schedules or
spends.

- `run new --start YYYY-MM-DD [--kind week|piece|express]`: a skeleton with
  its computed fields.
- `run new --from DRAFT --out SPEC`: fill `week_target`, every
  `payload_sha256` and each `share`'s `forward_line`. Never by hand.
- `run lint SPEC [--record]`: errors (exit 1) and warnings as JSON.
- `run status SPEC`: each slot's stage, computed from evidence.
- `run pack SPEC [--day YYYY-MM-DD] [--channel ID]`: this pack. Over 36 KB,
  or a part over its budget (this doc 8 KB, the slice 10 KB, the cards 12 KB,
  findings and status 6 KB), is refused; narrow it. Crew cards load by the
  registry flag for the run's week, else by channel.
- `run card lint FILE`: a Codex task card, before dispatch.
- `run release plan|check SPEC ...`: Buffer call arguments, then readback.
- `run decide SPEC`: decision.json from the week's mix plan decision.
- `run send-test SPEC SLOT`: the blind send test.
- `run measure`, `northstar`, `verdict`, `cost`, `ga4`: see `--help`.

Keep a real spec at `.scratch/runs/<run>/spec.json`, never in git: it holds
unpublished words. The run folder is the `run_id` with each `:` as `_`.

## What lint refuses

Schema errors; a `week_target` that is not the `docs/NORTH_STAR.md` rung for
the New York Monday of `window.start`; a `payload_sha256` that does not recompute; words that fail `prose_errors` (em
dashes, house rules) or content-engine's copy lint
(eyebrow labels, asterisks, AI notes, take labels); a snackable slot with no
valid `share`, a stale `forward_line` or a share ask (`social/share.json`); an
unknown channel or format, or a format the channel does not take
(`social/channels`, `social/formats`); `publish_mode` other than `krish_click`
on a human-publish-only channel (LinkedIn) or other than `engine` elsewhere; a
`krish_click` slot with a `due_at`; `spend_usd` above 0; two experiments on one
channel; an unregistered arm; an asset hash that is not 64 lowercase hex; more
scheduled slots on a New York day than the channel's `daily_posts_target`
(null: no cap; U3+ lifts it to its policy bound); an engine slot asset in no
manifest with a `creative_approval_ref` (release holds it too); a window that
is not New York midnights 7 (week, from a Monday), 8 (piece) or 1 (express)
days long; a slot with no `ecosystem_cta` (docs/ENGINE.md). Warnings include
an engine slot with no `due_at`: it cannot release, and the daily cap counts
only scheduled slots.

A slot's `payload_sha256` covers exactly `channel`, `format`, `words`, the
ordered asset hashes, `link_placement`, `due_at` and `publish_mode`, as
canonical JSON (`engine/control_center.py` `canonical_json`).

## Readiness is computed, never written

`drafted, linted, reviewed, signed, queued, live, measured, verdict`. Each stage
needs the previous one and its evidence under `.scratch/runs/<run>/`:

- `lint.json`: written by `run lint --record`, no errors, bound to this spec
  less `signature` and `buffer_draft_id` (signing and queueing keep it valid;
  any other edit needs `--record` again).
- `review/<slot>.json`: `verdict` "pass", a `lens` id from a fresh-context
  reviewer and the `payload_sha256` it reviewed. Snackable slots use lens
  `send-test` (`run send-test --answer FILE --record`).
- `decision.json` (the shape `run release` reads): `run_id`, `proposal_id`,
  `decision` "approved", `decided_at`, `slots` {slot: signed digest} and,
  optionally, `amended` {slot: Krish's amended payload}. The spec `signature`
  must name `proposal_id` and hold `decision_digest`, the sha256 of the
  canonical `slots` map. A slot's digest equals its `payload_sha256`, or
  recomputes from its amended payload; his version is what releases, so
  rewrite the slot with it before release. A mismatch is never signed.
  Concept-only: `proposal_id` and `decision` null, `slots` {}.
- `queued/<slot>.json`: `status` "scheduled" or "draft" (always "draft" for
  `krish_click`) and `payload_sha256` equal to the signed digest.
- `live/<slot>.json`: `status` "sent" and an https `native_url` read back from
  the platform.
- `measured/<slot>-<window>.json` (window such as `24h`, `72h`, `7d`) with
  `captured_at`.
- `verdict/<slot>.json`: `works`, `neutral`, `fails` or `insufficient`.

A missing or invalid file stops the slot at the previous stage, with a reason.
Draft counts are never outcomes.

## Gates

- **Standing plan:** one `plan` proposal (wall `strategy`) for W45 to W52;
  every go-live names it as `parent_proposal_id`.
- **G-A, Sunday (up to 15 min):** the week's Notes, Threads and evergreen slots
  as one go-live; payloads up to 8,000 characters, split if larger.
- **G-B, Mon/Wed/Fri (up to 5 min each):** a piece's batch across channels.
- **G-X, express (up to 2 min):** joins the waiting go-live; one a day.
- **Check-ins:** Sunday (with the What-Works ledger) and Wednesday.

Control Center shows one ask per engine at a time. Release checks each slot's
bytes against its signed manifest line, never where a file lives.

## Budgets (provisional until the Phase 0 baseline)

- Release: up to 45 calls, 1M tokens, 30 engine minutes (about 16 concept
  posts a day plus readbacks) until Phase 0 replaces it.
- Measure: up to 20 calls, 0.5M tokens.
- Express: up to 15 calls, 0.5M tokens.
- Krish: 20 minutes a weekday, 30 on Sunday; gates first.
- Spend: 0. Over budget, the session ends at a gate packet; it never loops.

## Closeout (docs/ASSET-STORAGE.md)

1. Approved delivery assets and exact copy go to the Drive
   **4 Growth** library, one `YYYY-MM-DD - Topic - Channel` folder each, with
   a SHA-256 manifest. No other Growth root.
2. Private evidence stays in `.scratch/`, never in 4 Growth (link-editable).
3. Lessons go to `social/lessons/`; run `python growth.py social check`.
4. Creative feedback goes to Content Engine, which owns the craft.
5. Point `docs/SESSION-HANDOVER.md` and `NOW.md` at the dated private closeout:
   what is draft, approved, scheduled, published, held or unknown.
6. Snapshot run evidence before cleanup; a local archive is no backup.
7. A changed automation: verify its owner and schedule; update it, never
   duplicate it.

## Rules a run session also reads

- `invariants/rules.json`: each rule with its verbatim source quote.
- `docs/PUBLISHING-AUTHORITY.md`: who may publish where.
- `docs/ACCOUNT-VOICE.md`: X, TikTok, Threads and LinkedIn are Krish's
  personal accounts, in his voice (sincere, warm, humble).
- `AGENTS.md` ("The rules that never bend", "Autonomy"): outreach belongs to
  Control Center; this engine never delivers pitches, partners or swaps packs
  (`post --deliver` refuses them).
