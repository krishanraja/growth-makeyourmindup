# Run sessions

The standing doc a run session reads first. `growth.py run pack` puts it on
top of every session pack. The plan behind it is
`docs/plans/2026-10-27-engine-architecture.md` (Krish, 27 Oct 2026).

## What a run session does

A run carries one signed spec (`growth-run-spec/1`) from draft to verdict:
a `week`, one published `piece` (day 0 to day 7) or one `express` idea. Krish
signs exact payloads; the engine releases exactly what he signed, reads it back
and measures it. LinkedIn stays his own click. Nothing is spent.

A session does one job, then ends at a gate packet:

- **Release:** only the L0 job `release.yml` (`run autorelease`), and only
  for a go-live Krish approved, read from Control Center in its own run.
  `decision.json` is written only from that readback, never by hand. Every
  30 minutes it schedules a signed draft only 5 to 90 minutes before its time,
  so a No before then stops it; one still scheduled after a No fails the run.
  A session never schedules a Buffer post or uses `--deliver`; it saves
  drafts. Scheduled is never live.
- **Measure:** L0 `measure.yml` gives verdicts three times a day. A session
  reads back "sent" and the native URL and checks the express intake.
- **Express:** one approved idea into the waiting go-live, or its own.

No mid-turn questions: every question becomes a gate packet; the session
ends. A run session commits nothing to `engine/`.

## Lanes

L0 (GitHub Actions) runs alone; L2 is one press in Control Center; L3 is
Krish's hands (`docs/LANES.md`). No Claude routines (Krish, 29 Oct);
makers follow `docs/TASTE.md`.

## Commands

A session's commands are offline: none posts, sends, schedules or spends.

- `python growth.py run new --start YYYY-MM-DD [--kind week|piece|express]`:
  a skeleton with its computed fields.
- `python growth.py run new --from DRAFT --out SPEC`: fill `week_target` and
  every `payload_sha256` from their sources. Never type them by hand.
- `run drafts SPEC --posts DIR`: fill `buffer_draft_id`, `buffer_channel_id`
  and `meta` from each `get_post` readback; lint again.
- `python growth.py run lint SPEC [--record]`: errors (exit 1) and warnings as
  JSON. `--record` writes `lint.json` for status.
- `python growth.py run status SPEC`: each slot's stage, computed from evidence.
- `python growth.py run pack SPEC [--day YYYY-MM-DD] [--channel ID]`: this pack.
  Over 36 KB, or a part over its budget (`engine/run/pack.py`), is refused;
  narrow it. Crew cards load by the week's flag (`w45`), else by channel.
- `python growth.py run card lint FILE`: a Codex task card, before dispatch.
- `run calendar lint [FILE]`: the V1 calendar.
- `run plain lint FILE` (or `run carousel lint`): plain English.
- `run canva lint DESIGN`: a design against the brand kit.
- `run cost self --claude-dir DIR --since DATE`: the newest session's cost.
- `release`, `measure`, `northstar`, `verdict`, `ga4`: see `--help`.
- L0 only, in Actions, never a session (`docs/LANES.md`): `run autorelease`,
  `run measure auto`, `run keys`, `run dispatch-check`, `run handoff`.

Keep each real spec at `.scratch/runs/<run>/spec.json`, never in git: it holds
unpublished words. The run folder is the `run_id` with each `:` as `_`.

## What lint refuses

Schema errors; a `week_target` that is not the ladder rung in
`docs/NORTH_STAR.md` for the Monday (New York) of `window.start`; a
`payload_sha256` that does not recompute; words that fail `prose_errors` (em
dashes, stock phrases and other house rules); an unknown channel or format, or
a format the channel does not take (`social/channels`, `social/formats`);
`publish_mode` other than `krish_click` on a human-publish-only channel
(LinkedIn) or other than `engine` elsewhere; a `krish_click` slot with a
`due_at`; `spend_usd` above 0; two experiments on one channel; an arm that is
not registered; an asset hash that is not 64 lowercase hex; more scheduled
slots on a New York day than the channel's `daily_posts_target` (null: no cap;
Story frames do not count); an engine slot asset in no manifest with a
`creative_approval_ref` (release holds it too); a window that is not New York
midnights 7 (week, from a Monday), 8 (piece) or 1 (express) days long.
Warnings include an engine slot with no `due_at`: it cannot release, and the
daily cap counts only scheduled slots.

A slot's `payload_sha256` covers exactly `channel`, `format`, `words`, the
ordered asset hashes, `link_placement`, `due_at`, `publish_mode`, `meta`
(what the edit sends besides words and time) and `buffer_channel_id`, as
canonical JSON (`canonical_json`).

## Readiness is computed, never written

`drafted, linted, reviewed, signed, queued, live, measured, verdict`. Each stage
needs the previous one and its evidence under `.scratch/runs/<run>/`:

- `lint.json`: written by `run lint --record`, no errors, bound to this spec
  less `signature` and `buffer_draft_id` (signing and queueing keep it valid;
  any other edit needs `--record` again).
- `review/<slot>.json`: `verdict` "pass", a `lens` id from a fresh-context
  reviewer and the `payload_sha256` it reviewed.
- `decision.json` (the shape `run release` reads): `run_id`, `proposal_id`,
  `decision` "approved", `decided_at`, `slots` {slot: signed digest} and,
  optionally, `amended` {slot: Krish's amended payload}. The spec `signature`
  must name `proposal_id` and hold `decision_digest`, the sha256 of the
  canonical `slots` map. A slot's digest equals its `payload_sha256`, or
  recomputes from its amended payload; his version is what releases, so
  rewrite the slot with it before release. A mismatch is never signed.
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
bytes at release time; a 4 Growth file is never trusted for where it lives.

## Budgets (provisional until the Phase 0 baseline)

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
4. Creative feedback goes to Content Engine through its handoff.
5. Point `docs/SESSION-HANDOVER.md` and `NOW.md` at the dated private closeout:
   what is draft, approved, scheduled, published, held or unknown.
6. Snapshot run evidence before cleanup.
7. A changed automation: verify its owner and schedule; never duplicate it.

## Rules live elsewhere

- `invariants/rules.json`: each rule with its verbatim source quote.
- `docs/PUBLISHING-AUTHORITY.md`: who may publish where.
- `docs/ACCOUNT-VOICE.md`: each account's voice; LinkedIn is his click only.
- `AGENTS.md`: outreach belongs to Control Center; this engine never delivers
  pitches, partners or swaps packs (`post --deliver` refuses them).
