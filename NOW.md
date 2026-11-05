---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-05
head: 4f771dd
lifecycle: live
production_url: none
state_doc: README.md
history_log: docs/history/LOG.md
truth_files: [docs/NORTH_STAR.md]
authority_order: [docs/NORTH_STAR.md, README.md]
steward: https://github.com/krishanraja/ai-harness/blob/main/docs/steward/RUNBOOK.md
---

# makeyourmindup growth engine: where it is right now

## What it is

The makeyourmindup growth engine: it drafts the posts that bring new readers to the publication, with no paid boosts.

## Who it is for and why it matters for Mindmake

Senior commercial leaders who should be reading makeyourmindup. The publication is the front door to Mindmake.

## Where it is right now (as of 2026-11-04)

<!-- north-star-state {"week_of": "2026-10-26", "week_target": 25, "current": 0, "current_as_of": "2026-10-30", "current_source": "Substack Growth sources, new subscribers, 7 days (2026-10-23 to 2026-10-30), read 2026-10-30: all sources 0, organic not classified", "urgency": 4, "urgency_reason": "0 of 25; under two fifths"} --> **North Star number: U4, far behind.** 0 of 25 new publication subscribers this week from organic posts and shares, read on 30 October 2026.

Lifecycle: live. The detail is in `README.md`, `docs/ENGINE.md` and `docs/OPERATING_MODEL.md`.

- **The maker has made nothing since 30 October.** Every scheduled `maker.yml` run (30 Oct to 4 Nov, six runs) ends in the loud hold `slots_record_missing` (latest run 41828598486), so no derived or off-day post has been drafted by it. Cause not yet traced.
- **Release runs about four times a day, against a schedule of every 30 minutes** (4 Nov: 00:16, 06:46, 14:56, 21:01 UTC; GitHub thins scheduled runs). Release schedules a draft only 5 to 90 minutes before it is due, so most due posts would miss their window. Suspected, not yet measured on a real post.
- **Posting goes through Buffer only**, pinned to this engine's eight channels by id (`engine/buffer_channels.py`); the fulltime.fm, Heartside and yourdoghasnotes channels are refused by id. Content-engine's copy lint (2026-11-01.1) runs before every draft, title and alt text reaches Buffer.
- **What may go out:** his per-post go-live for series posts; for the derived and off-day lane, each off-day option he approved on the board (Ruling, Krish, 2026-11-01: "Mock looks right, lock it and build it"), inside the week's mix. Sunday is a rest day (Ruling, Krish, 2026-11-02). Four posts a day with a floor of three on Instagram, YouTube, TikTok and X (R102).
- **Assets:** the official logo file small in a bottom corner on carousels (3 Nov); his quoted words go on the picture word for word, and nothing he only asked for (2 Nov); finished posts are filed in 3 Posts, never 4 Growth (R46, 3 Nov); no Growth asset wears a series' colour (butter, lilac, coral) or name, on any day, since those belong to content-engine's weekly series pieces (R125, 4 Nov); the Tuesday meme carries only the house mark, small in the bottom-right corner; the Saturday carousel keeps the standard of the 7 Nov good news (`render/pieces/off-sat-goodnews/`).
- **The ledger** (`python growth.py ledger`) reads the board's build (4 Nov) and writes a row per day per slot; on 4 Nov one row reached stage 7, posted. The week's mix press on the board has not been pressed.
- **Docs were checked against the code on 4 November**; this repository has no closeout fold workflow, so its notes were folded by hand (`docs/history/LOG.md`).
- **Tests:** 951 local tests, all passing on 5 Nov, the Chromium renders included.

## What changed recently

- 2026-11-04 Krish: "I should be allowed to post random stuff on any day but it doesn't take on the brand colours of Follow the Money, Mind the Gap, or Under the Hood" (R125, replacing the same day's day-keyed colours). Growth's kit accent is the house mint; the renderer, the art-direction gate and the Canva lint refuse a series colour or name on every asset; memes carry the house mark bottom right and a Canva meme without it is refused.
- 2026-11-04 Docs pass across the three repositories (Krish: "every single word ... 100% clear and up to date before you merge"): the docs now describe per-option approval, the Sunday rest day, 3 Posts filing and nine workflows.
- 2026-11-03 Finished posts, the off days included, file into 3 Posts (R46), the one folder for the week.
- 2026-11-03 The drawn wordmark is gone: carousels carry the official logo file, small in a bottom corner.
- 2026-11-02 Sunday is a rest day, permanently ("Let's eliminate Sunday from Publishing anythign permanently"), and his quoted words on an approved option go on the picture word for word.
- 2026-11-01 Off-day approval is per option: board_tick reads the options whose idea and direction he approved.
- 2026-11-01 Copy lint 2026-11-01.1: Markdown, links, quote lines and backticks are refused before Buffer.
- 2026-11-01 The daily ledger first ran on GitHub (run 41282389838), reading Buffer and the board.
- 2026-10-31 One pipeline, with Growth holding the calendar ledger and all posting (`docs/OPERATING_MODEL.md`).
- 2026-10-30 One press on the board approved the week's mix (R124); since 1 Nov approval is per option instead.

Older lines are in `docs/history/LOG.md` (moved verbatim on 4 Nov) and `CHANGES.md`.

## What is next and what is waiting on Krish

- Next (2026-11-04): trace why `maker.yml` holds every run on `slots_record_missing` and get it drafting again; then measure whether release's thinned schedule misses due posts.
- Waiting on Krish: the week's mix press on the board; whether a past piece's repurposed carousel belongs in the mix; the Buffer plan purchase (his click; Buffer kept on 29 Oct); the Canva Cowork prompt; the Substack handle.
- Decisions the docs pass found (2026-11-04): AGENTS.md still names Sunday in the off-day lane against the 2 Nov rest-day ruling; COPY-DOCTRINE rule 9 has a reply add a fact from his piece, AGENTS.md rule 4 and R68 say never force one; GET-GOING Step 0.5 (his HeyGen avatar) is partly answered by the 28 Oct ruling; the local `run release` does not read the board approval that autorelease and the maker read.
- Waiting on Krish (2026-11-04): a pull request in ai-harness that gives this repository the closeout fold workflow and lets the docs steward run when a bot starts it.
- North Star check (2026-11-04): holds.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `AGENTS.md`: the whole brief for any agent here.
- `README.md`: what this repository is and how it runs.
- `docs/OPERATING_MODEL.md` and `docs/ENGINE.md`: the pipeline, the ledger and the engine.
- `docs/PUBLISHING-AUTHORITY.md` and `invariants/rules.json`: what may post, and every rule with its guard.

## Do not trust

- `docs/plans/2026-10-27-engine-architecture.md`: dated; later rulings win where it differs (3 Posts since 3 Nov, no Claude scheduled tasks since 29 Oct apart from the credits session, and `engine/run/intake.py` was never built).
- `docs/control-center/ENGINE-PROTOCOL.md`: Control Center's copy of 29 Oct, with known errors to fix upstream (the wake time, the flag count, the schema version range).
- `codex/queue/offday-kits-2026-11-02.md`: reads as pending, but its kits were never built.
- Old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states; the rejected TikTok image revision and the prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack.
