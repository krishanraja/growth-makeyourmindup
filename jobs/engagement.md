# Job: Run Engagement

The entry point when Krish says "Run Engagement". One engine, one job: answer people interacting
with MYMU, keep relationships, spot repeat questions and prepare the outgoing comments he asked
for. The other three engines (Acquisition, Publishing, Measurement) run as their own jobs; do
not do their work here. The contract is `engines/engagement.json`; the review that set it is
`docs/reviews/2026-11-05-growth-engine-review.md`, sections 4 and 5.

## This session

One engine per session: this one. Run `git pull`, then take `inbound_handoffs` from `engine
start`, oldest first, and close each with `python growth.py engine done engagement ID --note
TEXT`. Work another engine owns becomes a handoff: `python growth.py engine handoff engagement
TO --what TEXT --why TEXT --link ID`. A recurring audience question goes to Acquisition (and
Content Engine through its `question` record); substantive responses and repeat participants go
to Measurement; a broken post goes to Publishing. When Krish pastes a session link for a
handoff, send the handoff message to that session with the Codex tools available; if none can,
give him the message to paste. Never do the other engine's work in this session.

## Read first

1. `AGENTS.md` (the rules that never bend) and `BROWSER.md`.
2. `docs/ACCOUNT-VOICE.md` before writing for any personal account.
3. Then run, before anything else:

   `python growth.py engine start engagement`

   It reads only. Its `recover` block is the queue: unanswered incoming
   items, any requested outgoing batch with its ready count, unchecked
   identities, handled and excluded keys, stale `ready` states, returned
   candidates, open questions and decision conflicts. Start from its
   `next_action`.

## What it may do

- Read every engine's records and contracts.
- Open the actual post and read it in full before drafting.
- Draft a reply or comment in Krish's voice that says something real.
- Prepare a LinkedIn comment in the actual comment box for his final click (BROWSER.md,
  2026-10-24): one prefilled LinkedIn box at a time; preserve any existing human draft; verify
  account, exact post and parent comment first. On every other account, show the exact copy
  beside the open post.
- Append records to `engines/records/engagement.jsonl` and keep exact words, post URLs and
  recovery copy in `.scratch/engines/engagement.jsonl`.

## What it must not do

Post, publish, schedule, like or follow. Send, comment, reply or press any submit control except
under the rule below. Spend money or credits. Write to Control Center. Commit a post URL, exact
words, an address or a raw receipt. Count an incoming item toward an outgoing batch. Pad a batch
with a weak candidate. Leave more than one prefilled LinkedIn comment box open, or overwrite a
human draft.

## Social engagement in Krish's session (Ruling, Krish, 2026-11-05)

Social engagement for Make Your Mind Up is this engine's; nothing goes to Control Center. In a
Codex session Krish is driving, this session may submit one comment or reply through the browser
or a connector only on his explicit approval of the exact text in that session, immediately
before submitting, then record it as posted on his approval and nothing further until evidenced.
Otherwise the draft stays ready in the editor for his click. Scheduled jobs and sessions he is
not driving only draft.

## Open for Krish

The review asks that each ready LinkedIn draft keep its tab open, so a batch of nine would leave
nine prefilled boxes. BROWSER.md (2026-10-24) allows one prefilled box at a time and never
multiple stale drafts. These conflict. Until Krish rules, BROWSER.md holds: hand over one
prefilled box at a time and raise the conflict with him in the final message.

## The rules for each item

- Every interaction records its direction (incoming or outgoing), the parent post (committed as
  `parent_post_key`, the sha256 of its URL), the intended account and its state.
- An outgoing draft names what Krish adds after reading: a firsthand observation, a practical
  test or a real question. Personal encouragement alone is refused.
- An outgoing draft is ready only when the actual post was opened, the editor filled (LinkedIn
  only), you switched away and returned, the full text was read back and matches the draft
  digest, the tab is left open and recovery copy with the post URL is kept privately. A cleared
  editor is not ready. If 8 of 10 survive, report 8 ready.
- A replacement qualifies only after its post, contribution, account identity and retained text
  are checked, and only if it is neither privately excluded nor already handled. A weak
  candidate goes back to the researcher (`returned_to_researcher`).
- A comment Acquisition commissions keeps Acquisition's `opportunity_id`. Krish sees one draft
  and one decision for it.
- A question asked twice or more becomes a `question` record handed to both Acquisition and
  content-engine.

## How it records

Append one line per change through `engine.engines.core.append` (committed) or with
`private=True` (the overlay), then run `python growth.py engine check`. The latest line for an
id is current; earlier lines are its history. Every open record carries its source, observation
date, next owner, next action and revisit condition.

## Done

Each item is ready in the correct editor or has an accurate disposition: handled, skipped,
awaiting Krish, posted by Krish or returned to the researcher. The final message reports
incoming and outgoing counts separately and the number actually ready. Recurring questions are
with Acquisition and content-engine; substantive responses and repeat participants are recorded
for Measurement.

## Close

Hand off anything left for another engine, then write
`.scratch/engines/engagement-learnings.json` with `did`, `better_next_time` (specific changes),
`worked`, `handoffs` (every id made), `promoted` and `session_ref` (Krish's session link), and
run `python growth.py engine close engagement --learnings
.scratch/engines/engagement-learnings.json`. A repeat of an earlier session's line is refused
until its words are written into this file, `engines/engagement.json` or a `social/lessons/`
record and listed under `promoted`. Then commit `engines/records/*.jsonl` to `main` with a
message naming Engagement and the date, and push: another engine's session sees a handoff only
after `git pull`. If the push fails, put each new record line in the final message. End the
final message with the learnings and each paste-ready handoff message the close prints.
