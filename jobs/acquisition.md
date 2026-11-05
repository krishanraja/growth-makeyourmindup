# Job: acquisition

Krish says "Run Acquisition". This file is the whole job. The rules come
from the growth engine review of 5 November 2026
(`docs/reviews/2026-11-05-growth-engine-review.md`, sections 1 to 3) and
the outreach ruling of the same day (`AGENTS.md`, "Outreach for Make Your
Mind Up").

## Read, in this order

1. `AGENTS.md`, the rules that never bend.
2. `engines/acquisition.json`: what this engine owns, may do and must not do.
3. This file.

## The single job

Put MYMU in front of people who already care about the story, by the
strongest route available, with a way for them to follow and subscribe.
Start every run with that route into an audience. Individual conversations
come later, and Engagement prepares them.

## First command

    python growth.py engine start acquisition

It only reads. Its `recover` block names the best open opportunity, the
evidence of access, the outstanding approvals, the closed and declined
routes with what is suppressed, the active experiment, the rules and any
conflicts. `next_action` is where the run begins. With no qualified route,
it says to find one.

## Ranking a route

`rank_routes` in `engine/engines/acquisition.py` orders open opportunities:

- A reader path first. An interested reader can find, follow and subscribe
  to MYMU afterward. A route with no path never outranks one with a path.
- Fit: demonstrated audience interest in this specific story, kept as
  `fit_evidence`. A senior title alone counts for little. A fit score with
  no evidence is refused.
- Access: evidence that the route accepts contributions (`access_evidence`).
- Then speed, less work, likelihood of credit, and delivered reach.
- `publisher_audience` is the publisher's whole audience. `delivered_reach`
  is what the placement delivers. Only the second enters the ranking.

## What it may do

- Find and qualify editorial features with an identifiable intake,
  newsletter placements using an existing MYMU piece, creator
  collaborations with a specific contribution and discovery experiments.
- Prepare one draft for one recipient. `outreach_errors` must pass: a short
  introduction of Krish and MYMU with a clickable publication link, a
  specific reason for this recipient, one useful contribution and one
  proportionate ask.
- Hand an outgoing comment to Engagement with `commission_comment`. It
  returns the acquisition line and an Engagement batch with the same
  `opportunity_id`: append the first with `acquisition.add` and the second
  with `core.append('engagement', ...)`, so a fresh "Run Engagement" sees it.
  Commission bounded creative from Content Engine.
- Record what Krish decides and reports: `approve`, `record_outcome`,
  `redirect`, `decline`. A decline goes through `decline`, which closes the
  opportunity and suppresses it with its pitches. A redirect keeps the rungs
  the earlier recipient reached under `detail.redirects`.

## What it must not do

- Post, send, reply, comment, schedule or spend. Write nothing to Control
  Center. Krish enacts each exact approved draft in his own session.
- Touch the batch waiting at Krish's approval gate. `acquisition.add`
  accepts only his approval, a redirect or a decline for it, and refuses
  any line that reopens a declined, suppressed record.
- Carry an approval to a new recipient. `approval_digest` binds sender,
  recipient, channel, subject, body and links. Any change needs a fresh
  decision. A redirected inbox goes through `redirect`.
- Ask again after a decline, or open a second pitch or brief for the same
  opportunity. `acquisition.add` refuses both.
- Treat a later rung as proof of an earlier one. Sent, delivered, replied,
  declined, booked, live and subscriber attributed are each recorded on
  their own, with evidence.

## Recording and handing off

Committed records in `engines/records/acquisition.jsonl` carry digests,
states and decisions. Exact words, recipient addresses, URLs and receipts
go only in `.scratch/engines/acquisition.jsonl`. Every record carries its
source, observation date, state, next owner and revisit condition. Append
committed lines with `acquisition.add`, then run
`python growth.py engine check`. Hand live placements and attributable
results to Measurement, which judges what worked.

## Done

Each opportunity touched has a verified route, a concrete offer, a next
action and a recorded disposition. A successful placement has a live
reference and a route into MYMU. Attributable results are attached when
available. Close by naming what moved the North Star, or saying nothing did.
