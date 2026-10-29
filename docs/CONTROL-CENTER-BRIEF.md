# Control Center brief: growth-makeyourmindup

**Status (2026-10-19): adopted in this repository.** The client, the workspace steps (`growth.py cc start` and `cc finish`) and the dispatch workflow are built and tested against a local stand-in; see `docs/ENGINE.md`, "Reporting to Control Center". The first live run is the next dispatch.

Written 2026-10-18 by Control Center. This brief **supersedes `docs/CONTROL_CENTER_HANDOFF.md`**. Krish ruled that every growth engine reports through one protocol (ADR-038 in Control Center). Phases 2 and 3 of your handoff (one action list, honest numbers) are what the protocol gives you. Packs stay for the drafts Krish copies and posts.

## What Control Center now does for you

- **Pushes you one next action every day, chosen by rule.**
- **Puts every post, pitch and send that only Krish can do on his one list**, with Clear, Bump and Purge. It returns his decision bound to the exact words.
- **Shows your health, objectives, today's push and what you did** on Growth > Engines.

## Your registry row

| | |
|---|---|
| Slug in the path | `makeyourmindup` |
| `engine_id` | `growth-makeyourmindup` |
| `product_slug` | `publication` |
| Aim | The publication grows every week from posts people share because they are useful, with zero paid boosts, and the right leaders make up most of the new subscribers. By 2026-12-31 |
| Objectives | `new_subscribers`: no target set yet, per week (America/New_York); `paid_boosts_usd`: target 0 |
| Cadence | daily |
| State | Switched on 2026-10-18, with dispatch on. Your bearer arrives in this repository's secrets as `CONTROL_CENTER_ENGINE_TOKEN`, with `CONTROL_CENTER_URL` as a variable. Until then, build against `mode: synthetic` |

## The protocol, in short

The full spec is `docs/control-center/ENGINE-PROTOCOL.md`, with the report and directive schemas and a worked example beside it. In short:

**Base URL and auth.**
- Base: `CONTROL_CENTER_URL`, which is `https://controlcenter.krishraja.com`.
- Bearer: `Authorization: Bearer $CONTROL_CENTER_ENGINE_TOKEN`. This is a `gen1_` token issued for this engine alone. Control Center keeps only its SHA-256, and it opens this engine's routes and no others.
- Transport: HTTPS only. Follow no redirects, use bounded timeouts, and read back before retrying any write.

**Every run, in this order:**
1. `POST {base}/api/growth/engines/makeyourmindup/attempts` with `status: started`, before reading any source.
2. `GET {base}/api/growth/engines/makeyourmindup/directive` returns today's `next_action`, your objectives with their targets and latest values, his decisions of the last seven days, and the walls.
3. Do the work, inside the walls. The rule, word for word: "Nothing sends, posts, spends, deletes or changes a permission without a decision from Krish whose payload_sha256 matches what you are about to do."
4. `POST {base}/api/growth/engines/makeyourmindup/reports` with header `Idempotency-Key: {run_id}`. The body is the report envelope:
   - `schema_version: "1.0.0"`, `engine_id`, `product_slug`, `run_id`, `mode`, `observed_at`, `source`, `status`
   - `objectives[]`, `activity[]`, `proposals[]`, `events[]`, `holds[]`
   - `payload_sha256`: the SHA-256 of the canonical JSON without that field, with keys sorted at every depth and no whitespace

   An unknown field is refused, never dropped. Then `GET .../reports/{run_id}` and compare the digest.
5. `POST .../attempts` again with the terminal state (`succeeded`, `failed` with a lower_snake `error_code`, or `unknown`) and `finished_at`. A terminal record never changes.
6. `GET {base}/api/growth/engines/makeyourmindup/decisions?since={last run}` returns his yes and no, each with the `payload_sha256` it was made on. Act on a yes only when that digest equals the payload you are about to use. A changed payload is a new ask, and it goes back to him by itself when you report it.

**How proposals and readings are judged.**
- A proposal behind a wall (`spend` with its `amount_usd`, `send` or `post` with its `exact_payload`, or `strategy`) goes on Krish's one list on Home, where Clear approves it, Purge declines it and Bump defers it a day.
- A proposal inside the walls is yours to do. Control Center may pick it as your next push.
- Unknown is `value: null` with a `reason`, never zero. A measured zero is `0`.
- `mode: synthetic` is stored and read back but never touches his numbers or his list. Use it to prove your client before Krish switches you on. A live report is refused (409 `engine_inactive`) until he does.

**The wake-up.** Control Center wakes you once a day around 06:10 London with `repository_dispatch` of type `cc-growth-directive`, whose `client_payload` is `{ directive_id, engine_id }` and nothing else. Add that trigger to your workflow. If you do not run on GitHub Actions, pull the directive at the start of your own run instead; it is the same directive.

## How your old handoff maps

| Your contract | In the protocol |
|---|---|
| v2 `metadata` (`priority`, `minutes`, `why_now`, `success_check`, `blocked_by`, `expires_at`) | A proposal: `why` carries `why_now`, `close_condition.event` carries `success_check`, `expires_at` is unchanged, and `blocked_by` becomes a `holds[]` entry |
| Completion labels (Published, Sent, Applied, Verified, Reviewed, Skipped) | `events[]` with the event name and `evidence_url`. Skipped is his Purge, which arrives as `declined` in `GET decisions` |
| Measurements (`window_kind`, `availability`, `missing_reason`) | `objectives[]`, with `availability` and `reason`. A rolling week replaces its window; never add one to another |
| Relationship events (`confirmed_by: Krish`) | `events[]` with `evidence_url`, reported only after he confirms |
| Experiments | A `strategy` proposal for his decision to start or stop one. Observations go in `activity[]` |

## What you build now

1. The client for the six calls, used only on a run you have marked `--deliver`.
2. A pull of the directive at the start of each automation, because you do not run on GitHub Actions.
3. A proposal per item that needs Krish, inside your 20-minute daily budget. Each one goes out (`wall: post` or `send`) with `exact_payload`.
4. A synthetic report, read back by digest.

## What you stop

- Waiting for a packs v2 parser in Control Center. Packs stay as they are for the drafts.
- Expecting Control Center to rebuild the Substack schema.

## Acceptance

- A post proposal appears on Krish's list with its exact words, and his Clear comes back with your digest.
- A missing measure shows as unknown with its reason, never as zero.

## Prepaid credits (protocol 1.16.0)

Added 2026-10-29. Ruling (Krish, 2026-10-29): a growth engine may spend up to its placement share of a tool's prepaid credits each cycle with no per-batch approval, and reports what it made. The spec is `docs/control-center/ENGINE-PROTOCOL.md`, "Prepaid credits: spend your share before it is wiped (1.16.0)".

**What arrives.** The directive may carry `credits`: `{ rule, pools[] }`, each pool `{ pool, tool, unit, share, share_amount, spent_this_cycle, remaining_for_you, pool_balance, balance_as_of, use_by, resets_on, days_left, unit_costs[] }`, soonest wipe first. No `credits` block means the pools could not be read today: unknown, never a share of zero.

**This engine's pools** (venture key `publication`):

| Pool | Share | Cycle | Note |
|---|---|---|---|
| ElevenLabs (main) | about 50,000 of the 100,000 credits a month | renews on the 10th; unused credits roll over two months | Krish's voice clone: anything made with it needs his approval before it is published |
| Apify (main) | $5.80 of the $29 included usage | resets on the 21st | anything over the included $29 is new money |

The directive's figures win over this table: read `share_amount` and `remaining_for_you` each run.

**What to do.** Spend up to `remaining_for_you` of each pool on work that moves this engine's objectives (`new_subscribers` first), with no proposal: for example narrated audio of a published piece for a Short, or an Apify extraction that feeds the radar or the numbers job. Make stills before video. Report every spend in the report's `credits_spent[]`, `{ pool, amount, asset, objective_key }`, at most 40, with the report at `schema_version: "1.16.0"`. `asset` says what was made in words, never an address.

**The walls.**
- Never past `remaining_for_you`, and never a top-up, a plan change or new money.
- Nothing made with credits is published, posted or sent without its own approval: the go-live, or an approved concept under the 2026-10-29 mix plan ruling (AGENTS.md, "Autonomy"). Anything in Krish's cloned voice needs his approval to publish.
- Never spend to exhaust a pool: credits serve the objectives, not the other way round.
