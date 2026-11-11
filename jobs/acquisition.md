# Job: acquisition

Krish says "Run Acquisition". This file is the whole job. The rules come from the growth engine
review of 5 November 2026 (`docs/reviews/2026-11-05-growth-engine-review.md`, sections 1 to 3) and
the outreach ruling of the same day (`AGENTS.md`, "Outreach for Make Your Mind Up"). Read
`AGENTS.md` (the rules that never bend), then `engines/acquisition.json` (what this engine owns,
may do and must not do), then this file.

## This session

One engine per session: this one. Run `git pull` and the first command below, then take
`inbound_handoffs` oldest first; `python growth.py engine done acquisition ID --note TEXT --next
TEXT` closes each and prints a report-back to send to the session that sent it. Work another
engine owns becomes `python growth.py engine handoff acquisition TO --what TEXT --why TEXT --link
ID`. A commissioned comment goes to Engagement (link the batch from `commission_comment`); a live
placement and its results go to Measurement; a broken reader link goes to Publishing. Before
anything else with that item, ask Krish the question it prints, exactly as printed ("Do you have a
session running for the X engine? ..."). If he says to create one, create a new Codex session with
the Codex tools available, start it with the handoff message and record its link with `python
growth.py engine session set TO LINK`; if he pastes a link, record it and send the message there.
Commit and push the new handoff line before sending the message, so `git pull` there finds it.
Parallel work goes the same way: dispatch it and carry on here without waiting, unless this
engine's next step depends on the result. Record a report-back from another session (`engine done`
or an update on the linked record) and carry on. Never do the other engine's work in this session.

## The single job

Put MYMU in front of people who already care about the story, by the strongest route available,
with a way for them to follow and subscribe. Start every run with that route into an audience.
Individual conversations come later, and Engagement prepares them.

## First command

    python growth.py engine start acquisition --session LINK

Pass `--session` with this session's link when Krish has given it: the one write start makes, into
the private `.scratch/engines/sessions.json`, so other sessions can report back here. Otherwise it
only reads. Its `recover` block names the best open opportunity, the evidence of access, the
outstanding approvals, the closed and declined routes with what is suppressed, the active
experiment, the rules and any conflicts. `next_action` is where the run begins. With no qualified
route, it says to find one, or at U3 to U5 to draft `recover.daily_outreach` (docs/ENGINE.md, "The subscriber push").

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
In a Codex session Krish is driving, this session may enact one outreach send through the browser
or a connector only after Krish approves that exact bound payload (its `approval_digest` of
sender, recipient, channel, subject, body and links) in that session, immediately before sending.
It then records the receipt as sent and nothing further until evidenced. Scheduled jobs and
sessions he is not driving only draft.

## Recording and handing off

Committed records in `engines/records/acquisition.jsonl` carry digests, states and decisions.
Exact words, recipient addresses, URLs and receipts go only in
`.scratch/engines/acquisition.jsonl`. Every record carries its source, observation date, state,
next owner and revisit condition. Append committed lines with `acquisition.add`, then run `python
growth.py engine check`. Hand live placements and attributable results to Measurement, which
judges what worked.

## Done

Each opportunity touched has a verified route, a concrete offer, a next action and a recorded
disposition. A successful placement has a live reference and a route into MYMU. Attributable
results are attached once known. Close by naming what moved the North Star, or that nothing did.

## Close

Hand off anything left for another engine (asked and sent as above), then write
`.scratch/engines/acquisition-learnings.json` with `did`, `better_next_time` (specific changes),
`worked`, `handoffs` (every id made), `promoted` and `session_ref` (this session's link,
`my_session_ref`), and run `python growth.py engine close acquisition --learnings
.scratch/engines/acquisition-learnings.json`. A repeat of an earlier session's line is refused
until its words are written into this file, `engines/acquisition.json` or a `social/lessons/`
record and listed under `promoted`. Then commit `engines/records/*.jsonl` to `main` with a message
naming Acquisition and the date, and push: another engine's session sees a handoff only after `git
pull`. If the push fails, put each new record line in the final message. End the final message
with the learnings, each handoff's question and message the close prints, and any unsent
report-back.
