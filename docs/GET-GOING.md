# Get going

When Krish opens this repository and says "Get going", this is the work. AGENTS.md says how to use it; this file says what to do. Written 2026-10-19 by Control Center, from this engine's first live reports.

## What "Get going" does

1. Read AGENTS.md to the end (it records Krish's rulings), then docs/NORTH_STAR.md. Say in one line which part of the North Star this run moves.
2. Do the first unticked step of **The build** below, completely: to its checks and one pull request. Tick it in that same pull request, with a one-line note of what it changed in the live report. If a step is blocked on something only Krish can do (a secret, a ruling), say exactly what in the pull request and on his list in Control Center, tick nothing, and go on to the next step.
3. Stop after one step, unless it took under an hour and the next step needs nothing from him.
4. When every step is ticked, "Get going" means: read the engine's latest live report and today's directive, find what most limits tomorrow's report (an unknown objective, a held proposal, a weak go-live, a check-in he declined), fix that, and add it here as a ticked step.

Never ask Krish to paste a prompt or repeat a brief: everything needed is in this repository.

## The brief

Read AGENTS.md first and follow it (it records Krish's rulings of 2026-10-19), then docs/NORTH_STAR.md, docs/CONTROL-CENTER-BRIEF.md and docs/control-center/ENGINE-PROTOCOL.md (protocol 1.1.0). Before you start, say which part of the North Star this work moves.

Where things stand (2026-10-19): this engine runs the Control Center loop live. Every day at 05:10 UTC Control Center writes this engine a directive and wakes `.github/workflows/control-center.yml` (`python growth.py cc runner --deliver`) with a `cc-growth-directive` repository_dispatch. The first live run on 2026-10-19 succeeded: it journaled its attempt, read the directive, sent a report, read it back by digest and read Krish's decisions. Control Center now speaks protocol 1.1.0: send `schema_version: "1.1.0"`, and read `stage`, `amended`, `exact_payload`, `amount_usd` and `amended_sha256` from decisions.

The job now is to make the daily report worth Krish's morning. Every run should leave Control Center with:

1. Every objective measured honestly: a real value with its window and timezone, or `value: null` with a specific reason. Never a zero you did not measure.
2. One best recommendation plus a few alternatives as `proposals[]` (at most 10). Each one names its `objective_key`, says why in plain words, links its evidence (https only), says its `kind` (advice, prepared or autonomous), names the event that proves it done in `close_condition`, and has an `expires_at`. Control Center picks tomorrow's next action by rule: first what Krish approved and you have not done, then a repair if the engine is failing, then the unwalled proposal on the objective with the widest gap. So make the move you most want done unwalled where you can, and aim it at the widest gap.
3. Anything behind a wall (`wall`: send, post, spend or strategy) complete enough that his yes is the whole decision: the exact words in `exact_payload`, the channel, `amount_usd` for spend, and the evidence. It lands on his one list in Control Center, where Clear approves exactly that payload, "Change it first" lets him approve his own version, and Purge declines it. Keep a proposal's `proposal_id` stable across runs: if the words change, the new `payload_sha256` sends it back to him, and his earlier yes and any version of his no longer apply.
4. `events[]` for what closed, with evidence, naming the proposal_id and the event in its close_condition.
5. `holds[]` for anything set aside, each with a reason code and one plain sentence.

Acting on his decisions: this engine is autonomous (AGENTS.md, "Autonomy"), and autonomy is given where it is deserved. Build the whole loop:
- **Plan** (`stage: "plan"`, behind `strategy`, the plan in `exact_payload`): what the engine is going to do, aimed at the objective with the widest gap. Wait for his yes.
- **Go-live** (`stage: "go_live"`, `parent_proposal_id` = the plan, behind `send`, `post` or `spend`): once the plan is approved, build everything up to go-live and propose it for his review, with the exact words, the assets and the amount, and the quality review in its evidence. Nothing goes out yet.
- **The go-live step**: when a decision approves a go-live whose `payload_sha256` matches, publish, send or spend exactly that, once, through the channel it names, then report the closing event with evidence. When `amended` is true, recompute `amended_sha256` (SHA-256 of canonical JSON of exactly `{"amount_usd": ..., "exact_payload": ...}`) and use his version, never yours. Purge means stop. Never go live from an approved plan, an interactive session or a prompt. If a channel needs a credential the runner lacks, report a hold naming the exact secret Krish must add; never ask for a value.
- **Check-ins** (`stage: "check_in"`, behind `strategy`, naming the plan, with how it is going and what comes next in `exact_payload`) at the cadence AGENTS.md sets. His yes keeps the plan going, his amendment redirects it, his no stops it for good.
- **The quality bar** in AGENTS.md holds before any go-live is proposed. Hold work below it, with its reason. Record each of his amendments and declines where the next draft reads it.

Rules that do not move:
- This repository is public. Synthetic fixtures only. No live people, drafts, business figures, tokens or production receipts in code, tests, logs, artifacts or pull requests. Public Actions logs carry counts and codes only.
- Never print or commit `CONTROL_CENTER_ENGINE_TOKEN`. This task has no token and needs none: prove every change against the repository's local protocol stand-in (the local server in `tests/test_control_center.py`). The only live writes are the scheduled Actions run and the workspace runs Krish starts.
- Never retry a write blindly. After a timeout or a 409, read back first.
- Plain English, no em dashes.

Finish with the checks below passing and one pull request whose description says, in plain words, what tomorrow's live report will say that today's did not.

### This engine

Today's live report (2026-10-19) was `held`:
- Three `wall: strategy` proposals now wait on Krish's list: start the topic-landing, welcome-first-step and native-continuation experiments.
- Hold: drafts and dashboard numbers are made only in the publication workspace.
- On the runner both objectives are missing: `new_subscribers` (weekly, New York Monday start) and `paid_boosts_usd` (target 0).

## The build

Priority ruling, Krish, 2026-10-21: channel-specific live browser audit and
repair comes first. This supersedes the old first-unticked ordering for this
task. The original technical backlog below remains open, not silently done.

- [x] **Weekly audit implementation.** Accepted scope, standing metadata
  authority, browser job, per-account coverage guards and pending-write
  reconciliation, with synthetic regression checks. See docs/CHANNEL-AUDIT.md.
  This implementation does not prove live repairs or subscriber growth.
- [ ] **Complete the live baseline.** Profiles, pins and 30 days of posts on
  every configured account, including saved-page readback of repairs.
  Signed-out/public-only sessions and connection failures are partial
  coverage. Never tick from a schedule, public profile or passing test suite.

- [ ] **Step 0.** Correct the status line at the top of docs/CONTROL-CENTER-BRIEF.md: the first live run on 2026-10-19 succeeded, so it is no longer only tested against a local stand-in.
- [ ] **Step 1.** The autonomy loop above (plan, go-live, the go-live step, check-ins) on protocol 1.1.0, proved against the stand-in: an approved plan never goes live, an approved go-live goes live once with exactly its payload, an amended one goes live in his words, a declined check-in stops its plan. Then the creative review every go-live passes: the doctrine it was checked against, at least two alternatives made, and why this one wins, in its evidence. Krish has a low tolerance for poor creative output, so a weak go-live is held, not proposed.
- [ ] **Step 2.** Make the workspace runs report. `doctor` should say exactly where the token goes (`%USERPROFILE%\.config\growth-makeyourmindup\engine-token` or `CONTROL_CENTER_ENGINE_TOKEN`), and the eight jobs should stop loudly, not silently, when it is missing. The workspace report carries the numbers; the runner report carries the engine check; keep their run_ids apart.
- [ ] **Step 3.** Act on his experiment decisions. When he approves one, the next runs prepare it (drafts as `wall: post` with the exact words) and report its readings against `new_subscribers`. When he declines one, drop it and do not propose it again unless the evidence changes.
- [ ] **Step 4.** `paid_boosts_usd`: find out with evidence whether boost spend can be read (Substack or LinkedIn records). If it can, measure it. If it cannot, keep it missing with that exact reason.
- [ ] **Step 5.** Make the daily recommendation the single post or experiment step most likely to add the right subscribers, prepared and tied to `new_subscribers`.

## Checks

`python growth.py --self-test`, `doctor --offline`, the fixture `dry-run` and a `cc runner` dry run, on Python 3.9 and 3.12.
