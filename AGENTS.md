# The makeyourmindup growth engine

<!-- north-star:start -->
## North Star: read it first, every session

This repository's North Star is [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md): an ambition Krish set that is not reached yet.

- Read it before any work, every session.
- Before you start, say which part of it the task moves. If it moves nothing, say so first and let Krish decide.
- Prefer the work that moves it furthest, and close by noting what moved.
- Check the North Star number and its urgency (U1 to U5) on the first line under "Where it is right now" in `NOW.md`, and push at the intensity [the harness contract](https://github.com/krishanraja/ai-harness/blob/main/contract/north-star-metric.md) sets for that level. Update it whenever you can measure it; a number nobody measures is U4.
- Only Krish changes it.
<!-- north-star:end -->

## Asset continuity (Krish, 27 October 2026)

Read `docs/ASSET-STORAGE.md` and `docs/SESSION-HANDOVER.md` at the start of
every session. Use the existing Drive **4 Growth** folder for structured,
versioned distribution assets and clean delivery copy. Content Engine keeps
its separate production home. Preserve private evidence and rejected versions
locally with a dated hash inventory before closing or cleaning a workspace.
The supplied Drive folder is link-editable: never upload private run backups
there. Update the handover, NOW.md and owning structured lessons at closeout.

## Architecture upgrade (Krish, 27 October 2026)

Krish adopted `docs/plans/2026-10-27-engine-architecture.md` (`CHANGES.md`,
27 October 2026). A run session reads `docs/RUN.md` first: it is the only
standing doc a run session reads, and `growth.py run pack` puts it on top.
New channels: Substack Notes from Krish's Substack profile (handle in
`social/channels/substack-notes.json`; up to two a day, as he signs) and
Threads (one a day, his personal voice); signed exact payloads go out through
the go-live step and LinkedIn stays his click. The Canva lane makes what
content-engine does not cover (`social/guides/canva.md`).
The Measurement Specialist (`crew/attribution-ladder/`) owns the North Star:
Substack Growth sources stay its source, `growth.py run northstar` computes
the NOW.md line from a capture, and GA4 is read directly for per-post joins on
`utm_content`. The What-Works Analyst (`crew/what-works/`) owns what works.
Older lines below stay as written; where they say otherwise, this wins.

## Open setup: read before any other work

Written 2026-10-21. Any session that can do one of these does it, then
deletes its line here in the same commit. Leave a line in place if you
cannot do it, and say why in one sentence at the end of your run.

- **The ninth automation is not scheduled yet.** `automations.json` gained
  "Growth: answer piece" (Saturdays 09:00 New York, `jobs/answer.md`) on
  2026-10-21, after the other eight were created in Codex. A Codex session
  that can create scheduled tasks runs steps 1, 2, 4 and 5 of "When Krish
  says: create the automations" below for that one entry, updating rather
  than duplicating. A session that cannot (the GitHub Actions runner, a
  Claude session) reports it as a hold on Krish's list with reason
  `automation_missing` and does not ask him to paste anything.
- **The answer piece's question set.** Each answer piece's question also
  belongs in AEO-Engine's question set (`krishanraja/AEO-Engine`), so the
  fortnightly check measures whether it is cited. The `answer` job adds it
  as a line in its final message; whoever next works in AEO-Engine commits
  it there. Never run AEO-Engine from here.

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


## Growth ownership (Ruling, Krish, 2026-10-26)

**Publishing authority: latest ruling, 26 October.** Read
docs/PUBLISHING-AUTHORITY.md. Approved content has delegated packaging and
cadence on branded channels and scoped X/TikTok, aiming for one useful daily
post where an approved native edition exists. X/TikTok retain personal voice.
LinkedIn stays unscheduled drafts for Krish's final click, with no daily quota.
Other connected personal identities are not automatically in scope. This
supersedes older contradictory publication rules, preserving all spend,
engagement, creative-approval and account-setting boundaries.

27 October 2026 (`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`):
Threads and Substack Notes join that delegated cadence with Krish's personal
voice, Notes from his Substack profile at up to two a day as he signs.
The line above that other personal identities are not automatically in scope
still holds for every identity except Threads and his Substack profile for
Notes.

**Use structured operating contracts.** Start social execution at social/README.md
and run `python growth.py social route CHANNEL FORMAT`. The channel, format,
tool and evidence-linked lesson records own their respective instructions.
Reuse verified procedures; recheck only a named changed/unknown capability
plus mandatory live identity/schema/authority checks. Capture consequential
results in the owning record, not as another general instruction here.

**Personal-account voice is non-negotiable.** Read docs/ACCOUNT-VOICE.md
before preparing anything for Krish's personal accounts. Be sincere, warm,
humble and pleased to share something useful, especially on LinkedIn.
No arrogance, lecture voice or performative humility. Publication Instagram
makeyourmind.up uses its editorial voice and is explicitly excepted from
that personal-sharing requirement. Classify the account before writing.

This repository owns posting strategy, amplification planning, social media
management and authorised automatic distribution for the publication and
Krish's named personal accounts. Read docs/ENGINE-BOUNDARY.md before work.
Growth originates amplification ideas from published work, finds useful
channels/placements Krish is missing, and owns current social/channel best
practices and experiments. Do not wait for him to request each carousel or
distribution opportunity. Turn observations into a concrete native posting
plan. Production standards for every format remain in content-engine.
Content-engine alone owns content production and production standards.
Commission the required carousel, Short or other edition there, receive a
checked asset package, then manage its platform delivery and measurement
here. Return content defects and creative feedback to content-engine.
Growth drives the amplification work and invokes content-engine's production
capabilities and standards as needed. Do not build a parallel production
pipeline or quality canon in Growth. Keep responsibility for progress and
delivery here. Legacy local pilot assets retain their review provenance.

27 October 2026 (`CHANGES.md`; `docs/ENGINE-BOUNDARY.md`, "the Canva lane"):
Growth now produces, in Canva, the formats content-engine does not cover
(today Substack Notes and memes). For that lane only, this supersedes the
parallel-production line above; content-engine keeps every other format and
its standards, and the lane applies them by reference.

Growth strategy is self-contained here. Content-engine supplies production
assets; Control Center is the eventual unified review surface. Scheduled
jobs may use the supported growth routes. Interactive work makes no Control
Center writes. Existing publishing and engagement authority still applies.

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
That historical separation is clarified by the 2026-10-26 ruling above:
independent engines, with an explicit production-to-distribution handoff.

## Outreach belongs to Control Center (Ruling, Krish, 2026-10-21)

Control Center's People tab (Guests, weighted 70 to this show) and Visibility already find, draft and track outreach to shows and guests, drafted from Jonny's mailbox. So this engine proposes posts and measures. It proposes no pitch, swap or partner note: `growth.py cc finish` holds that work with the reason "Control Center's People and Visibility own outreach to shows and guests". The Tuesday, Wednesday and Thursday jobs below may still prepare lists and research for Krish's own use, but nothing from them reaches his list. His list also shows one of this engine's asks at a time, a go-live first, then a check-in, then a plan, so never add a second ask of a kind that already waits.

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
   as him. The 2026-10-24 BROWSER.md ruling permits LinkedIn comment
   preparation for Krish's own final submission. Never otherwise type
   into a platform's compose box. Never send an
   email: at most save a draft. Never spend money. If a step seems to need
   any of that, write the draft and stop. `BROWSER.md` has the full line.
   Exceptions are the scoped weekly browser-audit edits above, the explicit
   unscheduled Buffer draft preparation in BROWSER.md, and an approved
   go-live taken live by the engine's go-live step. Draft saves never
   authorise scheduling or publication.
2. **Facts only from his published pieces.** Every fact, number and name in
   a draft comes from an article `python3 growth.py pieces
   --full` prints, or from the thread you are replying to. Never invent a
   number, a quote or a result. If you are unsure, leave it out.
3. **Standards have one production owner.** Content-engine owns production
   and voice standards for every format. Growth owns channel strategy,
   native posting packages, captions/links and engagement preparation,
   applying those accepted standards and the applicable krish-voice guidance.
   Use the established production route for finished creative. Existing-field
   repairs preserve meaning and voice; never invent experience or a claim.
4. **Say something real.** A reply responds to the actual thread in ordinary
   human language. A specific observation, honest reaction or relevant
   question can be enough. Never force a fact from his piece or a sales
   angle into a conversation. If using facts or personal experience, cite
   their source internally and never invent them. No links in LinkedIn
   comments. The 2026-10-24 ruling in BROWSER.md permits preparing one comment
   for Krish to review and post; it never permits submitting it.
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
   27 October 2026 (`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`):
   pitches, partners and swaps are held (Control Center owns
   outreach): skip `post --deliver` for those kinds, which exits 1 with the
   outreach hold; `cc finish` still reports the hold.
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

   **His approved voice rules** (protocol 1.5.0). The directive may carry
   `taste`: the voice rules Krish approved or reworded in Control Center.
   `cc start` prints them as a block headed "KRISH'S APPROVED VOICE RULES"
   and keeps the same block in `.scratch/cc/voice-rules.txt` for the
   drafting step. Every draft in his name or for makeyourmindup follows
   them for how it is written, alongside rule 3 below; where they disagree
   on how to write, his approved rule wins, and rules 1, 2, 4, 5 and 6
   still bind. They never choose what a draft is about. They never feed a
   judge, a score, a rubric, the breakout score, the queue or
   `growth.py check`: review and rank exactly as if they were not there.
   An empty list means none is approved yet: never invent one. No block
   ("Could not be read today") means unknown: draft to rule 3 as before.
2. **Last, after the job's own checks:**
   `python growth.py cc finish --job KIND --envelope FILE --queue .scratch/queue.json --deliver`
   (the numbers job adds `--observations .scratch/observations.json`). It
   turns the selected drafts into proposals for Krish (posts and comments
   behind the `post` wall, pitches and asks held as Control Center's (above), report
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
Only the GitHub runner (a repository secret) and Krish's PC (the file, for
Codex workspace runs) hold it. A Claude session never sets or reads it: it
reads Control Center through the Control Center connector, and a cloud
routine's Control Center traffic goes through the runner (`docs/LANES.md`).
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
| Tuesday 07:00 | Pitches (held: Control Center owns outreach) | `pitches` | `jobs/pitches.md` |
| Wednesday 07:00 | Partners (held: Control Center owns outreach) | `partners` | `jobs/partners.md` |
| Thursday 07:00 | Recommendations (held: Control Center owns outreach) | `swaps` | `jobs/swaps.md` |
| Saturday 09:00 | The answer piece | `daily` | `jobs/answer.md` |
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
4. **Create the nine scheduled tasks** from `automations.json`, using
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
7. **Finish** with one line: "9 automations live. First radar at 06:30
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
here: a run spends money and needs Krish's yes. The strategy for being cited
(answer-first pieces, the host checklist Krish applies, measurement) is in
`docs/CHANNEL_PLAYBOOK.md`, "Search and AI answers: GEO and AEO"; the
weekly `answer` job drafts one answer-first piece from a real question.

## Why it works this way

`PLAYBOOK.md` is the operating system (seven engines, the channel jobs,
tracked links, kill-keep-scale), taken from the documents in `knowledge/`
that Krish gave it on 14 October 2026. `knowledge/README.md` says where his
own rules override them (no Notes, no percentages, he does every post). The
first research behind the engine is in `research.md`. Hooks by platform are
in `hooks.json`.

27 October 2026: "no Notes" and "he does every post" are superseded
(`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`). Substack Notes
are back, posted from Krish's Substack profile at up to two a day as he
signs, and Threads joins with delegated cadence. Signed exact payloads on X,
TikTok, Threads and Notes go out through the go-live step; LinkedIn stays his
click. No percentages still holds.

## Changing the engine

Krish keeps or kills a job from the Sunday report. Record his words with the
date in `CHANGES.md`, then change the job file. The schedule itself lives in
Codex (`README.md`, "Setting it up").
