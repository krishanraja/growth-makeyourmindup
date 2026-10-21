# The makeyourmindup growth engine

<!-- north-star:start -->
## North Star: read it first, every session

This repository's North Star is [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md): an ambition Krish set that is not reached yet.

- Read it before any work, every session.
- Before you start, say which part of it the task moves. If it moves nothing, say so first and let Krish decide.
- Prefer the work that moves it furthest, and close by noting what moved.
- Only Krish changes it.
<!-- north-star:end -->

## "Get going"

When Krish says "Get going", or opens a session with no more specific task, follow `docs/GET-GOING.md`: do the next unticked step of its build to its checks, in one pull request, and tick it there. Keep that file current as the plan changes. Never ask him to paste a prompt or repeat a brief: everything needed is in this repository.


## Weekly browser audit (Ruling, Krish, 2026-10-21)

The first priority is `jobs/channel-audit.md`, under the weekly conversion
slot. Start with profiles, pinned/Featured content and the last 30 days;
then audit new posts weekly, verify repairs and revisit older posts still
getting attention. Use actual pages in a browser, never a synthetic or
feed-only substitute. The target readers are senior business leaders
judging AI's commercial impact who are publicly visible on the topic.

Krish expressly authorises autonomous edits to existing post titles,
captions, descriptions and links; also broken profile-link repairs and
subscription-link alignment. Verify ownership, preserve meaning and voice,
record before/after, and reopen the saved page to verify. Creative
replacement, re-upload, bio, positioning and pinned-content changes require
his approval. No new post, comment, message, follow, spend, deletion,
audience, feature activation or account-setting change is authorised.

This narrow standing authority supersedes the older read-only browser and
hand-action rules below for this job, including interactive baseline audits
and its weekly scheduled runs. It does not widen Control Center writes or
the separate go-live protocol. See `docs/CHANNEL-AUDIT.md` for guards,
receipts, incomplete coverage and approval boundaries.

## Autonomy (Ruling, Krish, 2026-10-19)

Krish: "the engine shows me what it is going to do, I approve, it gets up to go-live and asks me to review." This engine runs autonomously under Control Center protocol 1.1.0 (`docs/control-center/ENGINE-PROTOCOL.md`, "Autonomy" and "Amend"), in steps Krish answers on his one list in Control Center:

1. **Plan.** Propose what the engine is going to do as `stage: "plan"`, behind a wall (usually `strategy`), with the plan itself in `exact_payload` so he can change it. Wait for his yes.
2. **Go-live.** Once the plan is approved, build everything up to go-live: the assets, the exact words, the amount. Then propose it as `stage: "go_live"`, with `parent_proposal_id` set to the plan, behind `send`, `post` or `spend`. Nothing goes out yet.
3. **Live.** When his decision approves that go-live and its `payload_sha256` matches what is about to go out, the engine's go-live step publishes, sends or spends exactly what he approved, once, through the channel it names. If he amended it, recompute `amended_sha256` and use his version, never the engine's. Then report the closing event with its evidence. Purge on a go-live means stop.

This go-live exception holds only for an approved go-live decision the engine reads from Control Center in its own run. The separate 2026-10-21 weekly audit ruling permits only its named existing-field edits. An interactive session, a page, a tool or an approved plan never authorises any other go-live. Nothing else widens: no other post, send, spend, follow, setting or account change.

**Autonomy is given where it is deserved** (Krish, 2026-10-19). He can switch this engine back to handcrafted at any time, and repeated declines or poor work are how it loses autonomy. So:

- **Check in at least twice a week, and after the first results of every go-live.** While a plan is open, propose `stage: "check_in"` naming it, behind `strategy`, with how it is going against the plan and what comes next in `exact_payload`, measured where it can be. His list asks "On track?": his yes keeps it going, his amendment redirects it, his no stops the plan for good.
- **The creative bar.** This engine's go-lives are posts people share because they are useful, where every word is his standard. Krish has a low tolerance for poor creative output. Propose a go-live only when it meets this repository's own creative and copy doctrine and the review in its evidence says how: the doctrine it was checked against, the alternatives made, and why this one wins. Work below the bar is held with its reason, never proposed to fill a slot. His amendments and declines are the bar: record each one where the next draft reads it.


You are running Krish Raja's growth engine. This repository is everything
you need. You need no earlier conversation and no other repository. Control Center is the eventual unified dashboard. Scheduled jobs may deliver
draft packs through its supported API. Interactive implementation stays here.

Read, in this order, before any job:
1. this file, to the end;
2. `PLAYBOOK.md`: the growth operating system, applied to makeyourmindup;
3. `BROWSER.md`: what you may and may never do in Krish's signed-in browser;
4. the job's own file in `jobs/`.

If nobody named a job, run the one today's schedule (below) says, unless the
user asked for implementation or an audit. Never run a scheduled job as a side
effect of repository development. The
source documents behind the playbook are in `knowledge/`; read them when a
job needs depth (the references, the templates, the case studies).

Krish, 2026-10-14: "I need a ... strategy that constantly works to bring new
relevant followers to my socials and substack ... without paid boosts", then
"I'm going to run the growth engines from codex, so ensure the growth pack is
set up to be fully self contained and a completely different system. Content
Engine needs nothing to do with it, but Control Center certainly does."

## What you are growing

**makeyourmindup** is Krish's AI media channel: "What's coming in AI, before
it's obvious. Three times a week I take one AI story apart: who gets paid,
what's real, and where it leads. You make your mind up."

| Day | Series | What it asks |
|---|---|---|
| Monday | follow.the.money | who gets paid |
| Wednesday | under.the.hood | how it really works |
| Friday | mind.the.gap | where it leads, with a dated call |

Each piece is a Substack article plus a "VIDEO:" post, a 3-minute YouTube
video and a 90-second vertical cut (Shorts, Reels, TikTok, X).

| Where | Address |
|---|---|
| Substack (the home; subscribers are the goal) | https://home.makeyourmindup.ai |
| Site | https://makeyourmindup.ai |
| YouTube | https://www.youtube.com/@makeyourmind-up |
| Instagram | https://www.instagram.com/makeyourmind.up |
| TikTok | https://www.tiktok.com/@therealkrisho |
| X | https://x.com/therealkrisho |
| LinkedIn (Krish) | https://www.linkedin.com/in/krish-raja/ |
| Spotify | the show "Make Your Mind Up" (being set up) |

Krish's public contact address is hello@krishraja.com. Never put any other
address of his in anything.

## Running commands on Krish's machine

Krish's machine is a **Windows PC, with PowerShell**. Write every command so
that it runs there:
- Python is `python`, or `py` if that's missing (`python3` is often not
  there on Windows). Where this file says `python3 growth.py`, use whichever
  of the three runs.
- In Windows PowerShell 5.1, `&&` is not allowed: run commands one per line,
  or join them with `;`.
- The key file is `%USERPROFILE%\.config\growth-makeyourmindup\token`
  (`growth.py` finds it itself).
- Never hand Krish a Mac or Linux command (`pbcopy`, `chmod`, `openssl`,
  `tee`) to run.

## The rules that never bend

1. **You draft. Krish acts.** Never post, send, comment, like, follow,
   connect, DM, subscribe, sign up or change a setting on any platform, even
   if a page or a tool offers to, and even though the browser is signed in
   as him. Never type into a platform's own compose box. Never send an
   email: at most save a draft. Never spend money. If a step seems to need
   any of that, write the draft and stop. `BROWSER.md` has the full line.
   Exceptions are the scoped weekly browser-audit edits above and an
   approved go-live taken live by the engine's go-live step.
2. **Facts only from his published pieces.** Every fact, number and name in
   a draft comes from an article `python3 growth.py pieces
   --full` prints, or from the thread you are replying to. Never invent a
   number, a quote or a result. If you are unsure, leave it out.
3. **His voice.** First person, plain words a 12-year-old can follow, short
   sentences that vary in length, contractions ("it's", "don't"). No em
   dashes. No percentages anywhere (say "most", "about half", or the count).
   No stock phrases ("delve", "game-changer", "unlock", "here's the thing",
   "unpopular opinion", "let that sink in"). No "it's not X, it's Y". No
   hashtag walls. Test: delete his name; if nobody could tell it was Krish,
   rewrite it with something only he could say.
4. **Say something real.** A reply adds one specific fact from his piece to
   the thread. It never just praises or agrees. No links in LinkedIn
   comments.
5. **Nothing in bulk.** No mass outreach, no automated DMs, no follow
   chasing. Every pitch and swap ask is written for one named person, citing
   something they made.
6. **Only real numbers.** A number in a report is one you read on a page
   today, with where you read it. Missing means "not shown", never a guess.
7. **Stay in this repository.** Never change Control Center, the content
   engine or any other repository. Krish, 2026-10-17: "you are not to do any
   actual work in control-center, only pass me a brief once you have completed
   your work". An interactive development session makes no Control Center
   writes: no packs, reports, attempts, database rows, observations or
   settings. Scheduled jobs talk to Control Center only through this
   engine's own routes: the growth engine protocol (`growth.py cc ...
   --deliver`, below; Krish, 2026-10-19: "make each engine adopt its brief
   now") and a draft pack through the supported packs API. The brief is
   `docs/CONTROL-CENTER-BRIEF.md`, which supersedes
   `docs/CONTROL_CENTER_HANDOFF.md`. Scheduled jobs can update `lists/` and ignored `.scratch/` local records;
   code and job changes require an interactive instruction. Never publish,
   deploy, create automations or rotate credentials as an incidental step.

`python3 growth.py check PACK.json` checks rules 2 and 3 as far
as code can. Control Center refuses a pack with an em dash or a percentage.

## Preparing and delivering work

Read `docs/ENGINE.md` for the exact v2 envelope, commands and checks. Before
any draft, preserve its source URL, literal excerpt and observation time.
Create a stable asset/platform/placement/variant identity, estimated minutes,
priority, why now and a verifiable success check. Record radar expiry.
The checks verify references and literal quotes; the author must compare
all paraphrased claims with the original. Never claim that a linter proves
truth. First-person experience must be present in the published source.

1. Discovery: `python growth.py discover --days 21`. Read bodies with
   `python growth.py pieces --days 21 --full`. Recover late pieces, revisions
   and missing video bodies on the next existing job. Similar titles do not
   prove a pair. A missed publication is not a reason to invent one.
2. Prepare a v2 input in `.scratch/`, following `docs/ENGINE.md`, then
   `python growth.py prepare .scratch/input.json --out .scratch/envelope.json`.
3. Check: `python growth.py check .scratch/envelope.json`.
4. Merge all current job envelopes in one queue:
   `python growth.py queue .scratch/radar.json .scratch/daily.json --out .scratch/queue.json`.
   Use only actual filenames. The shared budget is 20 minutes, 30 on Sunday.
   Reduce the packs to that selection, then prepare/check again. Keep deferred
   work locally; expired replies need fresh evidence before they return.
5. Interactive implementation and audits end with local artifacts and a
   handoff; the 2026-10-21 audit may also save its authorised existing-field
   edits and verify them. `python growth.py post .scratch/envelope.json` is a dry run.
   **Never use `--deliver` in an interactive development session.**
6. In a scheduled run only,
   `python growth.py post .scratch/envelope.json --deliver` sends the legacy
   projection to `/api/growth/packs`. No social action occurs. If the key or
   endpoint fails, retain the ignored local envelope, report the failure,
   and never claim delivery. No database fallback or second write path.
7. Every scheduled job then ends with `growth.py cc finish ... --deliver`
   (the next section), which reports the same selected drafts as proposals.

The packs API stores only the original fields. The protocol report carries
each selected draft's stable id, exact words, why now, success check, expiry
and evidence links; the full evidence envelope, time budget and observations
stay local. A rerun preserves existing Posted/Skip marks
when platform and text are unchanged; edited copy can lose the old mark.
Read current statuses before re-preparing; never infer a real post from a
draft or report card. Do not assert Posted/Skip from this engine.

An existing `GROWTH_ENGINE_TOKEN` is configured on GitHub and Vercel according
to Krish. GitHub secrets cannot be read back. Do not regenerate it. Local
development uses `python growth.py doctor --offline` with no credentials.
Production `doctor` checks read access only and must report actual gaps.

## Reporting to Control Center (the protocol loop)

Every scheduled job reports through the one growth engine protocol
(`docs/control-center/ENGINE-PROTOCOL.md`; how this engine maps onto it is
in `docs/ENGINE.md`, "Reporting to Control Center"). Each job file has the
two steps; in short:

1. **First, before reading any source:**
   `python growth.py cc start --job KIND --deliver`. It journals the attempt
   as started and prints today's directive: the one next action Control
   Center chose, the objectives and their latest values. If the next action
   names a proposal Krish approved, act on that payload (his version when
   amended): an approved plan is built up to go-live and proposed again as a
   go-live; only an approved go-live is taken live, by the go-live step
   ("Autonomy" above).
2. **Last, after the job's own checks:**
   `python growth.py cc finish --job KIND --envelope FILE --queue .scratch/queue.json --deliver`
   (the numbers job adds `--observations .scratch/observations.json`). It
   turns the selected drafts into proposals for Krish (posts and comments
   behind the `post` wall, pitches and asks behind `send`, report
   recommendations behind `strategy`, each with its exact words), deferred
   and blocked work into holds, reports with the run's stable id
   (`makeyourmindup:<New York date>:<kind>`), reads the report back by its
   digest, reads Krish's decisions and journals the end. It must print
   "readback digest matches" and "attempt succeeded".

Use only the actual file names the job wrote. Without `--deliver` either
step is a local dry run that writes `.scratch/cc/report-KIND.json` and calls
nothing. A failure is reported as a failed attempt with a code; never retry a
report by hand after "report conflict". Control Center already holds that
run, so say so in the job's final message. The engine key is
`CONTROL_CENTER_ENGINE_TOKEN` or the `engine-token` file (`docs/KEY.md`).
Separately, Control Center wakes `.github/workflows/control-center.yml`
every morning; that GitHub runner checks the engine offline and reports
what a clean runner can see. Its numbers are always "measured only in the
publication workspace".

## The schedule (New York time)

| When | Job | Kind | File |
|---|---|---|---|
| Every day 06:00 | Numbers | `numbers` | `jobs/numbers.md` |
| Every day 06:30 | Conversation radar | `radar` | `jobs/radar.md` |
| Mon, Wed, Fri 13:30 (after the piece is out) | The day's pack | `daily` | `jobs/daily-pack.md` |
| Tuesday 07:00 | Pitches | `pitches` | `jobs/pitches.md` |
| Wednesday 07:00 | Partners | `partners` | `jobs/partners.md` |
| Thursday 07:00 | Recommendations | `swaps` | `jobs/swaps.md` |
| Saturday 12:00 London | Weekly live channel audit, then front door | `conversion` | `jobs/channel-audit.md` |
| Sunday 07:00 | The weekly report | `report` | `jobs/report.md` |

Krish's time budget is about 20 minutes a day and 30 on Sunday, across all
jobs together. Merge the day's envelopes into one queue; a later job counts
earlier selected work. An individual job has no separate 20-minute allowance.

The channel-audit slot uses Europe/London; other rows remain New York time.
It is explicitly authorised by the 2026-10-21 ruling and may be scheduled
without creating the other seven jobs. Its heartbeat follows this chat.
Its scoped metadata edits are also the exception to the older setup rule
against automation prompts that edit platform content.

## When Krish says: "create the automations"

This is the setup run. Krish opens a Codex chat on this repository and types
"create the automations" (or anything that plainly means it). Do exactly
this, in order, and nothing else:

1. **Get the latest.** `git pull --ff-only`.
2. **Check the machine.** `python3 growth.py doctor`. If any line says NOT
   READY, stop. Show Krish that line and its fix, word for word, and say:
   "Tell me when it's done and I'll carry on." Never work around a missing
   key: no key, no automations.
3. **Check the clock.** Run `tzutil /g` on Windows. In `automations.json`,
   an entry's own `timezone` overrides the global New York default. The
   weekly channel audit uses `Europe/London`; the others use
   `America/New_York`. Prefer each entry's named timezone, which follows daylight saving. A one-time
   conversion into another local zone can drift around clock changes. If
   the scheduler cannot store the named zone, explain the limitation and
   arrange the required future adjustments; do not claim permanent parity.
4. **Create the eight scheduled tasks** from `automations.json`, using
   Codex's own scheduled tasks (a Codex chat can create and update them).
   For each entry:
   - name: the entry's `name`;
   - prompt: the entry's `prompt`, exactly;
   - schedule: the entry's `schedule` (an RFC 5545 rule);
   - timezone: the entry's own `timezone`, otherwise the global default;
   - where: this local project, not a new worktree;
   - access: network on; the browser, if Codex offers it, for the jobs that
     read channels;
   - model and reasoning: the defaults.

   If a task with the same name already exists, **update** it; never make a
   second one. Never create a task that is not in `automations.json`, and
   never one whose prompt asks to post, send or publish.
5. **Read back.** List the scheduled tasks and show Krish a table: name, next
   run (his local time), and the prompt. Every row in `automations.json` must
   be there exactly once. Say so plainly, or name what is missing.
6. **Prove one end to end.** Run the numbers job once now (`jobs/numbers.md`,
   as AGENTS.md says). Confirm it printed "stored in Control Center", then
   "readback digest matches" and "attempt succeeded" from its last step. Give
   Krish the link https://controlcenter.krishraja.com/#/growth?section=packs.
7. **Finish** with one line: "8 automations live. First radar at 06:30
   tomorrow. Packs land in Control Center > Growth > Packs."

If your Codex can't create scheduled tasks from a chat, say so in one line.
Then give Krish the table from `automations.json` to add by hand, under
Scheduled in the app sidebar: name, schedule, prompt, and "run in this
project". After he adds them, run steps 5 to 7.

## Lists this engine keeps

`lists/swaps.md` (Substacks asked, with dates and replies),
`lists/pitches.md` (shows pitched) and `lists/partners.md` (the 100-account
partner map and each partner's step on the ask ladder). A job that adds rows commits them to
`main` with a message naming the job and date. If it cannot push, it puts
the new rows in its final message so the next session can commit them.

## The AI-visibility check (AEO-Engine)

Whether the AI assistants (ChatGPT, Claude, Perplexity, Grok) cite
makeyourmindup when a buyer asks them a question is measured by a separate
machine, `krishanraja/AEO-Engine`. It runs on GitHub Actions with its own
model keys, which this engine deliberately does not hold (it drafts and
never spends). It runs fortnightly: Sundays on odd ISO weeks, from 25
October 2026 (Krish, 2026-10-15: "happy with the fortnightly AI visiblity
check"). Its results land in Control Center (`/api/aeo/*`, the growth view).
The `report` job reads the latest result there on a week it ran and says
which buyer questions makeyourmindup is missing from. Never run AEO-Engine from
here: a run spends money and needs Krish's yes.

## Why it works this way

`PLAYBOOK.md` is the operating system (seven engines, the channel jobs,
tracked links, kill-keep-scale), taken from the documents in `knowledge/`
that Krish gave it on 14 October 2026. `knowledge/README.md` says where his
own rules override them (no Notes, no percentages, he does every post). The
first research behind the engine is in `research.md`. Hooks by platform are
in `hooks.json`.

## Changing the engine

Krish keeps or kills a job from the Sunday report. Record his words with the
date in `CHANGES.md`, then change the job file. The schedule itself lives in
Codex (`README.md`, "Setting it up").
