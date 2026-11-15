# HyperFrames and Claude Ads: what to take, what to leave (15 Nov 2026)

Asked by Krish on 15 Nov 2026: evaluate heygen-com/hyperframes and AgriciDaniel/claude-ads to "Improve automated
creative production and advertising analysis for Make Your Mind Up", consume content-engine before duplicating it,
keep the growth architecture, add no orchestration framework and no second analytics, build only what is missing,
and keep every advertising account change "draft-only" with "No campaign launches or budget changes".

**North Star.** New subscribers from organic posts and shares, zero paid (`docs/NORTH_STAR.md`); U5, 1 of 86 for the
week of 2 Nov, the week of 9 Nov not read yet (`NOW.md`). The creative half serves the organic posts. The advertising
half adds no subscriber: it keeps paid reach out of the organic number and the organic picture the mix is judged on.

## The calls

| Project | Installed? | Taken | Left |
|---|---|---|---|
| HyperFrames (HeyGen, Apache 2.0, CLI 0.9.54, commit 490199c of 15 Nov) | No | Nothing new. content-engine already took its motion rules and a caption system built on it, as its own code | Its runtime, CLI, Studio, skills and registry |
| Claude Ads (MIT, claude-ads-core 2.0.0, commit fc3908e of 17 Oct) | No | Its audit contract, as behaviour: four results, unknown is a real answer, evidence per finding, read-only by default, optimisation as drafts | Its 33 skills, 25 agents, control plane, cockpit and installer |
| What was missing | Built | `growth.py run paid audit` (`engine/run/paid_audit.py`, R131) and a fix to the slideshow video job | |

### HyperFrames: consume content-engine, add nothing here

- **content-engine already decided.** It read HyperFrames on 13 Nov through OpenMontage
  (`krishanraja/content-engine` `docs/ve/sources/openmontage.md`): "What we do not take: the HyperFrames runtime (ve
  stays on Remotion)". It took HyperFrames' energy-tiered transitions as its own numbers
  (`apps/renderer/src/engine/kit/ingredients.ts`) and rebuilt a HyperFrames caption system as its `cinematic` caption
  style (`apps/renderer/src/engine/captions/names.ts`). Every render is Remotion through `scripts/ve.py render`
  (`config/ve/tools.json`), with FormatMaster at 9:16 and 16:9.
- **Growth may not run a second renderer.** `docs/ENGINE-BOUNDARY.md`: Growth "does not run a competing renderer".
  Carousels, memes and Notes images are made from a Claude session with a Codex card, and off-day voiceover shorts on
  content-engine's ve route (`AGENTS.md`, "Carousels, memes and Notes images: one route").
- **How Growth reuses programmatic rendering, by job:**

| Job | Route | Owner |
|---|---|---|
| Branded social stills (covers, cards, memes, frames) | the house kit, `scripts/render_mocks.mjs` with `render/templates`, built from a Codex card | Growth, to content-engine's standard |
| Campaign variants (one message at every placement) | one job list naming the template family at each size: `carousel-cover` 1080x1350, `story-frame` 1080x1920, `chapter-card` 1920x1080, `meme-square` 1080x1080 | Growth |
| Video components (motion, captions, transitions) | `python3 scripts/ve.py card`, rendered by content-engine's Remotion lane | content-engine |
| Stills to a short (YouTube takes video, never a still) | the video job in `scripts/render_mocks.mjs` | Growth |

- **If a HyperFrames block is ever wanted** (its registry has about 450: charts, kinetic type, maps), it goes to
  content-engine as a brief for a Remotion ingredient, never into this repository. None is needed for anything on the
  board today.
- **One note for content-engine, not acted on here** (this repository never changes it): its OpenMontage note says
  the vendored HyperFrames skills' "upstream licence was **not checked here**". HyperFrames' LICENSE at 490199c is
  Apache 2.0.

### Claude Ads: take the contract, not the product

- **It is built for paid acquisition accounts, which this engine has none of.** Twelve ad platforms, audits of
  campaigns with monthly spend, budget plans, launch drafts. Nothing in it reads organic posts or boosted posts (no
  check mentions a boost).
- **Its connectors read exports only.** Its capability manifest (`control-plane/manifests/capability-manifest.json`)
  is read-only by default: on all twelve platforms account mutation is disabled, account-health scoring is disabled,
  and export ingestion is "fixture-verified" for API-shaped CSV projections (Meta Insights campaign rows, TikTok's
  integrated ad report). There is no live connector to reuse.
- **It brings its own orchestration**: an `/ads` orchestrator skill with 25 agents and a control plane, installed into
  `~/.claude/skills` and `~/.claude/agents`. This engine already has four engines and the Measurement engine's records;
  a second one would compete with them.
- **Its runtime does not fit CI**: Python 3.11 or 3.12, where `check.yml` also runs 3.9.
- **What is worth taking, and was taken as behaviour (no code copied):** every check ends `pass`, `fail`, `unknown` or
  `not_applicable`; unknown is a real answer and never a guess (this engine's rule 6 already says so); each finding
  carries its evidence; and optimisation is a draft that changes nothing.

## What was built

**`growth.py run paid audit`** (`engine/run/paid_audit.py`; rule R131; `jobs/measurement.md`). It makes the 15 Nov
interest-versus-paid review (`docs/reviews/2026-11-15-interest-vs-paid.md`) repeatable, and closes three gaps:

1. **Native posts were never read.** The measure job reads only posts Buffer sent (F17). 67 of the 128 posts on this
   engine's seven channels since 5 Oct were posted natively, and three of the four posts that look paid are native.
   The audit reads them, marked by `via`.
2. **Paid reach sat inside the organic medians** the measure job compares every post with. The audit holds paid and
   suspected-paid posts out of the baseline and says when holding them out moves a channel's median by more than a
   quarter.
3. **Nothing tied a boost to the North Star.** `invariants/sources.json` counts Substack's facebook, instagram,
   threads, tiktok, youtube and x sources as organic. A subscriber Substack credits to a platform during that
   platform's boost is not provably organic. The audit names how many and recommends holding them out; it never
   changes the number (only Krish does).

Its inputs are a saved Buffer list_posts capture (with metrics), the Measurement engine's `paid_boost` observations
(validated by `engine/engines/measurement.py`) and, optionally, a Substack growth-sources capture. It opens no
network connection, has no `--deliver`, writes to the ignored `.scratch/paid/`, and can recommend only four things:
read a boost, hold subscribers out, buy no new boosts, make more like a post people stayed with. Each is a draft with
`mutation: none`, awaiting Krish's Yes. A test refuses `launch`, `boost`, `pause`, `budget`, `increase_spend` and
`edit_campaign`.

**Proposed defaults for Krish's approval** (they decide nothing on their own): a post is far past its channel at ten
times the median of its channel's ordinary organic posts; on a channel an ads platform can boost, with at least
1,000 views or impressions, it is suspected paid at half the channel's pooled interactions per 1,000 or less, or at a
hundred times the median whatever its rate; a breakout needs at least three interactions; a post sent up to three
days before a recorded boost window is inside it. Substack Notes has no ads platform, so a Note is never suspected.

**The slideshow video job** in `scripts/render_mocks.mjs` dropped seconds when its frames differed in size: a 9:16
cover then a 4:5 card, asked for 3 and 2 seconds, came out 2.03 s with the card unpadded on a green field (ffmpeg 6.1
reinitialised its filters mid-stream). Each frame is now its own input, padded onto ink, then joined: 5.00 s, 150
frames, the card centred on ink (`tests/test_render_templates.py`, `VideoJobs`).

## Validation

**Sample advertising analysis, on live authorised data.** Buffer read tools only (list_posts with metrics, two pages),
128 sent posts on the seven pinned channels, 5 Oct to 14 Nov, read 15 Nov 2026 21:07 UTC; nothing in Buffer was
created, changed or scheduled. The channel rate in brackets is the pooled rate of that channel's ordinary organic posts,
the one each post is compared with. The capture stays in the session's scratch space, never committed.

| Post (first line) | Channel | Posted | Views or impressions | Interactions per 1,000 (channel) | Call |
|---|---|---|---|---|---|
| The UK number two you've been dancing to started as an AI demo | TikTok | native, 11 Nov | 17,991 | 1.0 (7.2) | suspected paid, reach without interest |
| Movin' To The Sun reached number two in the UK | YouTube | native, 11 Nov | 4,805 | 0 (4.2) | suspected paid, 437 times the median |
| When an AI agent gets a computer and no instructions | YouTube | native, 13 Nov | 1,166 | 4.3 (4.2) | suspected paid, 106 times the median |
| When an AI agent gets a computer and no instructions | Facebook | Buffer, 13 Nov | 16,252 | 5.4 (0) | suspected paid, the Page's median is 2 |
| The interesting bit of Claude Duet is who starts the work | Substack Notes | Buffer, 4 Nov | 208 | 38.5 (0) | organic breakout, 69 times the median |
| Disney has asked a dying AI company to go bust | YouTube | native, 9 Nov | 221 | 18.1 (4.2) | organic breakout, 20 times the median |

The four suspects are the four posts the 15 Nov review found by hand; the audit found no others. The Facebook post's
reach has grown since that review (8,984 then, 12,991 reach and 16,252 impressions now), which fits a boost still
running. Checks: `boosts_recorded` fail (four posts look paid, no reading covers them); `organic_baseline` fail on
YouTube (median 20 with them, 13 without); `spend_known` not applicable; `north_star_exposure` unknown (no Substack
read for 9 to 15 Nov yet); `zero_paid_line` unknown until the boosts are read. Seven drafts, none acted on: four reads
for Codex (Meta Ads Manager, TikTok Promote, YouTube Studio traffic sources), no new boosts until subscribers per pound
is known, and make more like the Claude Duet Note and the Disney Short.

**Representative creative.** One message from the published Claude Duet posts ("Claude Duet messages you first";
"The interesting bit is who starts the work."), the 15 Nov review's lead recommendation, rendered as a campaign variant
set through the house kit with `--verify`: a 4:5 feed cover, a 9:16 frame, a 16:9 card and a 5 s 9:16 short, each
byte-identical on a second render, in kit colours and fonts only. It validates the route; it was not judged, filed or
posted, and it stays in scratch.

**Tests.** `tests/test_paid_audit.py` (25, synthetic) and `VideoJobs`; `python growth.py --self-test` passes.

## Dependencies, costs and security

| | HyperFrames | Claude Ads | What was built |
|---|---|---|---|
| Runtime | Node 22 or later, FFmpeg, a Chrome it downloads (puppeteer-core, @puppeteer/browsers) | Python 3.11 or 3.12; WeasyPrint for PDF | Python 3.9 standard library; the existing Node, Playwright and FFmpeg for renders |
| Cost | Free; its Studio Pro plan and Pro skills (`/reverse-any-video`, `/style-sampling`) are paid | Free | None. Two Buffer read calls; no credits, generation or spend |
| Telemetry and network | CLI telemetry to PostHog on by default (off with `HYPERFRAMES_NO_TELEMETRY` or `DO_NOT_TRACK`); share routes upload to a hosted page | None found in `claude_ads_core` or `scripts` | None: no network import, refused by a test |
| What it writes | Skills into the agent's home | 25 agents and 33 skills into `~/.claude`, `~/.codex` and others, plus a managed venv | Only `.scratch/paid/`, ignored |

Both repositories were cloned into the session's scratch space as untrusted data and only read; none of their code
was run. An ads export or a capture can hold spend and post text: it stays in `.scratch/` or scratch, never committed.

## Blocked, and what unblocks it

- **The four suspects are unreconciled.** Only Krish's signed-in browser reaches Meta Ads Manager, TikTok Promote and
  YouTube Studio. Unblock: a Claude session on his computer runs the four reads through Codex
  (`scripts/codex_thread.mjs`), read only, and records each as a `paid_boost` observation; the next audit then holds
  those posts out and the zero-paid check turns from unknown to a measured result.
- **North Star exposure is unknown.** It needs the Substack growth-sources read for 9 to 15 Nov (`jobs/subscribers.md`,
  Monday). Unblock: pass that capture with `--substack`.
- **The Codex card route was not exercised.** This cloud session has no signed-in Codex; the creative was rendered
  with the kit directly to validate the route.
- **Nothing pushed.** The commit is local on `claude/great-ride-swa5qf` until Krish says push.
