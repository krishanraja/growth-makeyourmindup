# Job: Run Publishing

The entry point when Krish says "Run Publishing". One engine, one job: get
each approved edition to its intended destination and close it against
what a reader can see and do. The other three engines (Acquisition,
Engagement, Measurement) run as their own jobs; do not do their work here.
Contract: `engines/publishing.json`. Review: `docs/reviews/2026-11-05-growth-engine-review.md`, sections 6 and 7.

## This session

One engine per session: this one. Run `git pull`, then take `inbound_handoffs` from `engine
start`, oldest first, and close each with `python growth.py engine done publishing ID --note
TEXT`. Work another engine owns becomes a handoff: `python growth.py engine handoff publishing
TO --what TEXT --why TEXT --link ID`. Publishing scheduled a post: the live check of the reader
view stays here; the measured results go to Measurement (link the edition). A working
continuation with few visits goes to Acquisition. When Krish pastes a session link for a
handoff, send the handoff message to that session with the Codex tools available; if none can,
give him the message to paste. Never do the other engine's work in this session.

## Read first

1. `AGENTS.md` (the rules that never bend), `BROWSER.md` and
   `docs/PUBLISHING-AUTHORITY.md`.
2. `social/README.md`, then the route for the edition in hand:
   `python growth.py social route CHANNEL FORMAT`.
3. Then run, before anything else:

   `python growth.py engine start publishing`

   It reads only. Its `recover` block is the queue: due slots, approved
   editions, existing provider records (post IDs), route holds (from
   `social/tools/buffer.json` and the records), editions on a held route,
   unresolved public checks and overdue rechecks. Start from its
   `next_action`.

## What it may do

- Read every engine's records and contracts, `social/` and the release
  ledgers, and read back the public reader view of a post.
- Record each reader-facing check, hold a failed route and close an
  edition, through `engine.engines.publishing` and `core.append`. Exact
  captions, post URLs and raw receipts go only in
  `.scratch/engines/publishing.jsonl`.

## What it must not do

Post, publish, schedule, send, comment, like or follow. Spend money or
credits. Write to Control Center. Close a check on a saved setting or an
API success. Attempt a held route again before its recheck condition
changes. Schedule a LinkedIn edition: LinkedIn follows its human
publication rule, Krish's click. Commit a caption, a post URL or a raw
receipt.

## The rules for each edition

- An `edition` is one approved edition to one destination, bound to the
  approved payload by `payload_sha256`. Once it is public it carries its
  provider `post_id`.
- Each destination closes against separate `check` records on the same
  post ID: scheduled and public everywhere (public only on LinkedIn),
  plus grid cover and player cover on Facebook Reels, the continuation
  link on a YouTube Short, and playable video and email delivery on
  Substack. `publishing.applicable_checks` is the list.
- Only a readback of the public reader view closes a check
  (`publishing.readback`, source `live_readback`). A correct grid cover
  closes the grid check and nothing else.
- A miss stays open as a `discrepancy` on the same post ID with a dated
  recheck in `revisit_when`. Where the post ID is not yet known, the
  recheck is dated once it is recovered.
- A check counts for an edition only on the edition's own channel,
  format and post ID. A check closes only as `passed`; it is never
  marked closed or not applicable.
- A YouTube Short's continuation closes only after the native Short ID
  exists, the related full video is attached and the link works from the
  public Short.
- `publishing.close_edition` refuses while any check is open, and
  `engine check` refuses a `done` edition whose applicable checks are
  not all passed on its post.

## Route holds

A failed route is a `route_hold` naming the tool, account, format, the
failure, the date it was held, an explicit recheck condition and the
alternative. The tool record carries it as `"status": "held"`, so
`social route` returns `route_held_after_provider_rejection` with the
alternative instead of suggesting another check. Buffer TikTok video is
held (review section 7); the verified Buffer TikTok photo carousel route
is untouched; native TikTok video goes to Krish under the applicable
approval.

## How it records

Append one line per change through `engine.engines.core.append`
(committed) or with `private=True` (the overlay), then run
`python growth.py engine check`. The latest line for an id is current.
Every open record carries its source, observation date, next owner, next
action and revisit condition.

## Done

Each destination records what was scheduled, what became public, what
the reader experienced and any remaining repair. A failed route carries a
recheck condition. A done edition goes to Measurement for its
observation window; a broken continuation stays here as a defect; a
working continuation with few visits goes to Acquisition as an
experiment.

## Close

Hand off anything left for another engine, then write
`.scratch/engines/publishing-learnings.json` with `did`, `better_next_time` (specific changes),
`worked`, `handoffs` (every id made), `promoted` and `session_ref` (Krish's session link), and
run `python growth.py engine close publishing --learnings
.scratch/engines/publishing-learnings.json`. A repeat of an earlier session's line is refused
until its words are written into this file, `engines/publishing.json` or a `social/lessons/`
record and listed under `promoted`. Then commit `engines/records/*.jsonl` to `main` with a
message naming Publishing and the date, and push: another engine's session sees a handoff only
after `git pull`. If the push fails, put each new record line in the final message. End the
final message with the learnings and each paste-ready handoff message the close prints.
