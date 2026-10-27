# Run sessions

The only standing doc a run session reads. `growth.py run pack` puts it at the
top of every session pack. The plan behind it is
`docs/plans/2026-10-27-engine-architecture.md` (Krish, 27 Oct 2026).

## What a run session does

A run carries one signed spec (`growth-run-spec/1`) from draft to verdict:
a `week`, one published `piece` (day 0 to day 7) or one `express` idea. Krish
signs exact payloads; the engine releases exactly what he signed, reads it back
and measures it. LinkedIn stays his own click. Nothing is spent.

A session does one job, then ends at a gate packet:

- **Release:** one short session per signed go-live. Create each signed slot in
  Buffer with the exact `dueAt` from the manifest, then read back "scheduled".
  Buffer does the posting. Scheduled is never live.
- **Measure (daily):** read back "sent" and the native URL, capture metrics at
  their windows, write verdicts, check the express intake.
- **Express:** build one approved idea into the waiting go-live, or its own.

No mid-turn questions: every question becomes a gate packet and the session
ends. A run session commits nothing to `engine/`.

## Commands

All offline; none posts, sends, schedules or spends.

- `python growth.py run new --start YYYY-MM-DD [--kind week|piece|express]`:
  a skeleton with its computed fields.
- `python growth.py run new --from DRAFT --out SPEC`: fill `week_target` and
  every `payload_sha256` from their sources. Never type them by hand.
- `python growth.py run lint SPEC [--record]`: errors (exit 1) and warnings as
  JSON. `--record` writes `lint.json` for status.
- `python growth.py run status SPEC`: each slot's stage, computed from evidence.
- `python growth.py run pack SPEC [--day YYYY-MM-DD] [--channel ID]`: this pack.
  Over 36 KB is refused; narrow it.
- `python growth.py run card lint FILE`: a Codex task card, before dispatch.
- `release`, `measure`, `northstar`, `verdict`, `cost`: each says "not built
  yet" until its module lands.

Keep each real spec at `.scratch/runs/<run>/spec.json`, never in git: it holds
unpublished words. The run folder is the `run_id` with each `:` as `_`.

## What lint refuses

Schema errors; a `week_target` that is not the ladder rung in
`docs/NORTH_STAR.md` for the Monday (New York) of `window.start`; a
`payload_sha256` that does not recompute; words that fail `prose_errors`
(em dashes, stock phrases and the other house rules); an unknown channel or
format, or a format the channel does not take (`social/channels`,
`social/formats`); `publish_mode` other than `krish_click` on a
human-publish-only channel (LinkedIn) or other than `engine` elsewhere; a `krish_click` slot with a `due_at`; `spend_usd` above 0; two
experiments on one channel; an arm that is not registered; an asset hash that
is not 64 lowercase hex; more than 3 Notes on one New York day.

A slot's `payload_sha256` covers exactly `channel`, `format`, `words`, the
ordered asset hashes, `link_placement`, `due_at` and `publish_mode`, as
canonical JSON (`engine/control_center.py` `canonical_json`).

## Readiness is computed, never written

`drafted, linted, reviewed, signed, queued, live, measured, verdict`. Each stage
needs the previous one and its evidence under `.scratch/runs/<run>/`:

- `lint.json`: written by `run lint --record`, bound to this exact spec, no errors.
- `review/<slot>.json`: `verdict` "pass" and a `lens` id from a fresh-context
  reviewer. A `payload_sha256`, if present, must match.
- `decision.json`: `run_id` and `slots.<slot>` with `approved` true and a
  `digest` equal to the slot's `payload_sha256`. If Krish amended it, `amended`
  holds the amended payload and `digest` must recompute from it; his version
  is what releases. A digest mismatch is never signed.
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
  as one go-live; payloads of 8,000 characters or less, split if larger.
- **G-B, Mon/Wed/Fri (up to 5 min each):** a piece's batch across channels.
- **G-X, express (up to 2 min):** joins the waiting go-live; one a day.
- **Check-ins:** Sunday (with the What-Works ledger) and Wednesday.

Control Center shows one ask per engine at a time. Release checks each slot's
bytes against the signed manifest line at release time; a file in 4 Growth is
never trusted for where it lives.

## Budgets (provisional until the Phase 0 baseline)

- Release: up to 25 calls, 0.6M tokens, 15 engine minutes.
- Measure: up to 20 calls, 0.5M tokens.
- Express: up to 15 calls, 0.5M tokens.
- Krish: 20 minutes a weekday, 30 on Sunday; gates first.
- Spend: 0. Over budget, the session ends at a gate packet; it never loops.

## Closeout (docs/ASSET-STORAGE.md)

1. Approved delivery assets and exact copy go to the existing Drive
   **4 Growth** library, one `YYYY-MM-DD - Topic - Channel` folder each, with
   a SHA-256 manifest. No other Growth root.
2. Private evidence (readbacks, journals, inventories) stays in `.scratch/`;
   never in 4 Growth, which anyone with its link can edit.
3. Lessons go to `social/lessons/`; run `python growth.py social check`.
4. Point `docs/SESSION-HANDOVER.md` and `NOW.md` at the dated private closeout:
   what is draft, approved, scheduled, published, held or unknown.
5. Snapshot run evidence before workspace cleanup; a local archive is not an
   off-device backup.

## Rules live elsewhere

- `invariants/rules.json`: each rule with its verbatim source quote.
- `docs/PUBLISHING-AUTHORITY.md`: who may publish where.
- `AGENTS.md`: outreach belongs to Control Center; this engine never delivers
  pitches, partners or swaps packs.
