# Job: acquisition

Krish says "Run Acquisition". This file is the whole job. The rules come from the growth engine
review of 5 November 2026 (`docs/reviews/2026-11-05-growth-engine-review.md`, sections 1 to 3)
and the outreach ruling of the same day (`AGENTS.md`, "Outreach for Make Your Mind Up").

## This session

One engine per session: this one. Run `git pull`, then take `inbound_handoffs` from `engine
start`, oldest first, and close each with `python growth.py engine done acquisition ID --note
TEXT`. Work another engine owns becomes a handoff: `python growth.py engine handoff acquisition
TO --what TEXT --why TEXT --link ID`. A commissioned comment goes to Engagement (link the batch
from `commission_comment`); a live placement and its results go to Measurement; a broken reader
link goes to Publishing. When Krish pastes a session link for a handoff, send the handoff
message to that session with the Codex tools available; if none can, give him the message to
paste. Never do the other engine's work in this session.

## Read, in this order

`AGENTS.md` (the rules that never bend), then `engines/acquisition.json` (what this engine owns,
may do and must not do), then this file.

## The single job

Put MYMU in front of people who already care about the story, by the strongest route available,
with a way for them to follow and subscribe. Start every run with that route into an audience.
Individual conversations come later, and Engagement prepares them.

## First command

    python growth.py engine start acquisition

It only reads. Its `recover` block names the best open opportunity, the evidence of access, the
outstanding approvals, the closed and declined routes with what is suppressed, the active
experiment, the rules and any conflicts. `next_action` is where the run begins. With no
qualified route, it says to find one.

## Ranking a route

`rank_routes` in `engine/engines/acquisition.py` orders open opportunities:

- A reader path first. An interested reader can find, follow and subscribe to MYMU afterward. A
  route with no path never outranks one with a path.
- Fit: demonstrated audience interest in this specific story, kept as `fit_evidence`. A senior
  title alone counts for little. A fit score with no evidence is refused.
- Access: evidence that the route accepts contributions (`access_evidence`).
- Then speed, less work, likelihood of credit, and delivered reach.
- `publisher_audience` is the publisher's whole audience. `delivered_reach` is what the
  placement delivers. Only the second enters the ranking.

## What it may do

- Find and qualify editorial features with an identifiable intake, newsletter placements using
  an existing MYMU piece, creator collaborations with a specific contribution and discovery
  experiments.
- Prepare one draft for one recipient. `outreach_errors` must pass: a short introduction of
  Krish and MYMU with a clickable publication link, a specific reason for this recipient, one
  useful contribution and one proportionate ask.
- Hand an outgoing comment to Engagement with `commission_comment`. It returns the acquisition
  line and an Engagement batch with the same `opportunity_id`: append the first with
  `acquisition.add` and the second with `core.append('engagement', ...)`, so a fresh "Run
  Engagement" sees it. Commission bounded creative from Content Engine.
- Record what Krish decides and reports: `approve`, `record_outcome`, `redirect`, `decline`. A
  decline goes through `decline`, which closes the opportunity and suppresses it with its
  pitches. A redirect keeps the rungs the earlier recipient reached under `detail.redirects`.

## What it must not do

- Post, schedule or spend. Send, reply or comment except under the outreach rule below. Write
  nothing to Control Center.
- Touch the batch waiting at Krish's approval gate. `acquisition.add` accepts only his approval,
  a redirect or a decline for it, and refuses any line that reopens a declined, suppressed
  record.
- Carry an approval to a new recipient. `approval_digest` binds sender, recipient, channel,
  subject, body and links. Any change needs a fresh decision. A redirected inbox goes through
  `redirect`.
- Ask again after a decline, or open a second pitch or brief for the same opportunity.
  `acquisition.add` refuses both.
- Treat a later rung as proof of an earlier one. Sent, delivered, replied, declined, booked,
  live and subscriber attributed are each recorded on their own, with evidence.

## Outreach (Ruling, Krish, 2026-11-05)

Acquisition owns Make Your Mind Up outreach: shows, newsletters, creators, editorial features,
swaps and partners. Mindmake outreach stays with Control Center; nothing goes to Control Center.
In a Codex session Krish is driving, this session may enact one outreach send through the
browser or a connector only after Krish approves that exact bound payload (its `approval_digest`
of sender, recipient, channel, subject, body and links) in that session, immediately before
sending. It then records the receipt as sent and nothing further until evidenced. Scheduled jobs
and sessions he is not driving only draft.

## Recording and handing off

Committed records in `engines/records/acquisition.jsonl` carry digests, states and decisions.
Exact words, recipient addresses, URLs and receipts go only in
`.scratch/engines/acquisition.jsonl`. Every record carries its source, observation date, state,
next owner and revisit condition. Append committed lines with `acquisition.add`, then run
`python growth.py engine check`. Hand live placements and attributable results to Measurement,
which judges what worked.

## Done

Each opportunity touched has a verified route, a concrete offer, a next action and a recorded
disposition. A successful placement has a live reference and a route into MYMU. Attributable
results are attached when available. Close by naming what moved the North Star, or saying
nothing did.

## Close

Hand off anything left for another engine, then write
`.scratch/engines/acquisition-learnings.json` with `did`, `better_next_time` (specific changes),
`worked`, `handoffs` (every id made), `promoted` and `session_ref` (Krish's session link), and
run `python growth.py engine close acquisition --learnings
.scratch/engines/acquisition-learnings.json`. A repeat of an earlier session's line is refused
until its words are written into this file, `engines/acquisition.json` or a `social/lessons/`
record and listed under `promoted`. Then commit `engines/records/*.jsonl` to `main` with a
message naming Acquisition and the date, and push: another engine's session sees a handoff only
after `git pull`. If the push fails, put each new record line in the final message. End the
final message with the learnings and each paste-ready handoff message the close prints.
