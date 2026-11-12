# Job: measurement

Krish says "Run Measurement". This file is the whole job. The rules come from the growth engine
review of 5 November 2026 (`docs/reviews/2026-11-05-growth-engine-review.md`, "What Measurement &
Allocation should produce") and build on the Measurement Specialist
(`crew/attribution-ladder/card.md`) and the What-Works Analyst (`crew/what-works/card.md`).

## This session

One engine per session: this one. Run `git pull` and the first command below, then take
`inbound_handoffs` oldest first; `python growth.py engine done measurement ID --note TEXT --next
TEXT` closes each and prints a report-back to send to the session that sent it (with the Codex
tools available, or Krish pastes it). Work another engine owns becomes `python growth.py engine
handoff measurement TO --what TEXT --why TEXT --link ID`. An allocation change goes to the engine
that owns the work: a broken continuation to Publishing as a defect, a weak working continuation
or a route to test to Acquisition, a response pattern to Engagement. Before anything else with
that item, ask Krish the question it prints, exactly as printed ("Do you have a session running
for the X engine? ..."). If he says to create one, create a new Codex session with the Codex tools
available, start it with the handoff message and record its link with `python growth.py engine
session set TO LINK`; if he pastes a link, record it and send the message there. Commit and push
the new handoff line before sending the message, so `git pull` there finds it. Parallel work goes
the same way: dispatch it and carry on here without waiting, unless this engine's next step
depends on the result. Record a report-back from another session (`engine done` or an update on
the linked record) and carry on. Never do the other engine's work in this session.

## Read, in this order

1. `AGENTS.md`, the rules that never bend.
2. `docs/NORTH_STAR.md`: the number and its ladder.
3. `engines/measurement.json`: what this engine owns, may do and must not do.
4. This file.

## The single job

Answer one question each week: where should the next five hours go, and what evidence would change
that decision? Other engines record what they did. This engine judges what worked.

## First command

    python growth.py engine start measurement --session LINK

Pass `--session` with this session's link when Krish has given it: the one write start makes, into
the private `.scratch/engines/sessions.json`, so other sessions can report back here. Otherwise it
only reads. Its `recover` block gives the current number and its source, the comparable
observation windows, overdue measurements, the largest observed constraint and the open resource
decision. Act first on `krish_instruction` (his instruction; its own lines say how to act on it and ack it), then on `next_action`.

## Measuring

- Weekly organic subscribers against the ladder, from Substack Growth
  sources. `scorecard` in `engine/engines/measurement.py` reads the week's
  target from `docs/NORTH_STAR.md` and records source, window and freshness.
- A missing reading is unavailable with its reason, never zero.
- Count each subscriber once. A platform shows a subscriber under a parent
  and its child category (Substack and Substack > Notes). Record the rows as
  the platform shows them in `detail.source_rows`; the attribution must
  equal `attribute(source_rows)`, which gives the subscriber to the deepest
  path.
- A source attribution never implies an activity attribution. The
  specific post and any outreach link stay unknown until evidence names them.
- Direct stays unattributed. Paid never counts toward the North Star.
- Two readings compare only when metric, source and window length match.
- Where people drop out: a `funnel` record per engine, from access to
  subscriptions for Acquisition, responses for Engagement, delivery and
  defects for Publishing.

## Judging and allocating

- Judge windows: a Note at 24 hours; LinkedIn, X and Threads at 48 hours;
  a Reel, Short or TikTok at 72 hours; subscriber impact at 7 days. An
  earlier read is recorded, not judged.
- Posts are judged by the subscribers they brought, engagement only as support (Ruling, Krish, 2026-11-12; `docs/ENGINE.md`, "Judged by subscribers"; next week's mix learns from it, `docs/MIX.md`).
- A performance claim that would increase, reduce or stop something names
  its linked `experiment` record. `engine check` recomputes the decision with
  `performance_decision`, which calls `engine.operations.experiment_decision`
  with at least 6 observations. Until then the recommendation is a test or
  continue.
- Verified operational failures and explicit owner corrections apply at once:
  the evidence must name a held route or open discrepancy, or a record whose
  source is Krish's ruling (`user_ruling`). A standing rule only continues.
- `allocation_errors` checks each memo. Each recommendation names action,
  what moves, from, to, hours or cost, duration, evidence, uncertainty,
  owner, review date and reversal condition.
- Proposed spending stays apart from approved spending. Only Krish
  approves. A spend increase or test (a cost, or spending named in what,
  from or to) and every proposed item needs a `spend_case` that its evidence
  shows: an acquisition record booked or live, a funnel with visits, follows
  or subscriptions, or a funnel loss with a cost. Paid boosts sit outside
  the organic target.
- A scorecard's target is the ladder's for its week, and an open scorecard
  must equal `scorecard()` over its linked observation.

## What it must not do

- Post, send, schedule or spend. Write nothing to Control Center.
- Change `docs/NORTH_STAR.md`. Only Krish changes it.
- Claim subscriber growth from a decision. That needs later outcome evidence.

## Recording and handing off

Append to `engines/records/measurement.jsonl` with `core.append`, then run `python growth.py
engine check`. Raw receipts stay in `.scratch/engines/measurement.jsonl`. A broken continuation
goes to Publishing as a defect. A working continuation with few visits goes to Acquisition as an
experiment. The memo goes to Krish.

## Done

A dated scorecard and a decision memo say what to increase, reduce, stop, continue or test, each
with its evidence, uncertainty, owner, review date and reversal condition. Close by naming what
moved the North Star, or saying nothing did.

## Close

Hand off anything left for another engine (asked and sent as above), then write
`.scratch/engines/measurement-learnings.json` with `did`, `better_next_time` (specific changes),
`worked`, `handoffs` (every id made), `promoted` and `session_ref` (this session's link,
`my_session_ref`) and any `instruction_ack`, and run `python growth.py engine close measurement --learnings
.scratch/engines/measurement-learnings.json`. A repeat of an earlier session's line is refused
until its words are written into this file, `engines/measurement.json` or a `social/lessons/`
record and listed under `promoted`. Then commit `engines/records/*.jsonl` to `main` with a message
naming Measurement and the date, and push: another engine's session sees a handoff only after `git
pull`. If the push fails, put each new record line in the final message. End the final message
with the learnings, each handoff's question and message the close prints, and any unsent
report-back.
