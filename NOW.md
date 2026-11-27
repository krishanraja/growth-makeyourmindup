---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-27
head: e8cde21
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

Since 26 November 2026 (Ruling, Krish): Content-engine makes every asset (hero pieces, carousels, memes, Substack Notes images and copy, captions and titles per channel, covers, thumbnails, cuts and the weekly edition package) and hands Growth finished, approved assets with captions in the piece manifest; growth-makeyourmindup grows the channel: posting, scheduling in Buffer, the edition's Substack placement, distribution, the subscribe route, measurement, learning, mix.json and experiments, and reports performance back. This engine makes no asset and writes no caption
(`docs/ENGINE-BOUNDARY.md`, "26 November 2026").

The makeyourmindup growth engine: it plans, schedules, posts and measures the work that brings new readers to the publication, and drafts its outreach and engagement, with no paid boosts. It runs as four engines, one per session (Acquisition, Engagement, Publishing, and Measurement and Allocation), beside ten GitHub Actions workflows and ten PC automations: nine kept until W46, and the weekly Substack read (`jobs/subscribers.md`), which stands.

## Who it is for and why it matters for Mindmake

People who make the calls or make the work in the creative, arts, music, entertainment, media and sports industries (`docs/NORTH_STAR.md`, narrowed 26 Nov 2026). Start with `docs/V5-REBRAND.md`.

## Where it is right now (as of 2026-11-27)

<!-- north-star-state {"week_of":"2026-11-09","week_target":162,"current":0,"current_as_of":"2026-11-15","current_source":"Substack new-subscriber emails to Krish's inbox, New York week of 2026-11-09: 0 new, 0 organic; counted by Control Center","urgency":5,"urgency_reason":"under 40% of the week's target two weeks running (0% now)"} --> **North Star number: U5, stalled.** New publication subscribers a week from organic posts and shares, zero paid: 0, against 162 in the week of 9 November 2026, on the way to 2,500 by 28 December 2026. Everything else pauses unless it moves the number.

The last reading is the whole week of 2 November: 1 new subscriber of 86, all sources and organic alike, read from Substack on 12 November (`jobs/subscribers.md`). The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet: the engine's own reading of an unmeasured week is U4 (`engine/intensity.py`), raised to U5 by Control Center's directive, so the runs go at U5 and the subscriber push is on. The line above changes only on a measured reading: `growth.py run subscribers ingest` or `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- The v5 docs now lead a cold session to the rebrand: RUN.md, AGENTS.md, PLAYBOOK.md, CHANNEL_PLAYBOOK.md and COPY-DOCTRINE.md point at docs/V5-REBRAND.md and the promise, and V5-REBRAND.md carries the right marks, fonts, covers script, ManyChat state and Krish's approved positioning lines (27 Nov 2026). (2026-11-27)
- docs/V5-REBRAND.md now names Archivo as a v5 face (structure and video captions) beside Anton, Fraunces and DM Mono; only IBM Plex Mono is retired. (2026-11-26)
- This engine now carries the makeyourmindup v5 rebrand in docs/V5-REBRAND.md, read first from AGENTS.md: the locked look and what is retired, the daily Edition and its promise, no series names on new surfaces, the Saturday edition to all subscribers (Krish, 26 Nov), nothing sent until Substack's branding is v5, content-engine making every asset, and the social profiles and ManyChat work in flight. (2026-11-26)
- docs/V5-REBRAND.md section 7 now says the v5 profile set is final, in Drive 1 Brand kit (permanent) > Channel art and in the makeyourmindup brand kit zip under Channel art/, and that content-engine scripts/channel-kit/ is retired. (2026-11-26)
- docs/BRAND-KIT.md and docs/ASSET-STORAGE.md describe the v5 brand kit in Drive: one folder, 1 Brand kit (permanent), with Channel art inside it; 2 Channel art (permanent) is retired and everything older is in _Archive / 2026-11-26 v4 brand (retired, do not use). (2026-11-26)
- No branch is left unmerged: the hourly stray guard (.github/workflows/stray-guard.yml) deletes merged and closed-PR branches, opens a pull request for any branch idle six hours, marks drafts idle a day ready, merges green ones and lists the rest in one issue; AGENTS.md tells every session to read open pull requests first and land or delete its branch. (2026-11-26)
- tests/test_lane_docs.py no longer checks the links inside the krish-canon block, which is rendered from ai-harness and names files in other repositories, so the canon sync pull request can pass. (2026-11-26)
- Growth grows the channel and makes no asset: content-engine makes every asset and caption (Krish, 26 Nov), Growth's render kit, Canva lane and caption writer are deleted, a production boundary guard (R132) keeps them out, and the North Star reader is the creative, arts, music, entertainment, media and sports industries. (2026-11-26)

## What changed recently

- 2026-11-27 docs/V5-REBRAND.md marks table, fonts, make_covers path, DM words and ManyChat state; the reader in NOW.md; the stray-branch rule's lost names in AGENTS.md.
- 2026-11-19 Krish's 28-day Instagram read, checked live on the worker; he approved the bio and the caption line word for word.
- 2026-11-18 Ruling (Krish, 2026-11-18): "i have abandoned the prediction format, it feels lame"; the copy doctrine, channel playbook, daily pack, series table and hook families drop dated calls and the calls record, and content-engine, the site's brand-kit builder and ai-harness's content-corpus skill get the same change in their own pull requests. Krish asked (18 Nov) to pick up the growth push; comments under media accounts are now an observed dead end (social/lessons/media-account-comments.json) and Substack Live co-hosting facts are recorded (social/lessons/substack-live-cohost.json).
- 2026-11-18 render/templates/carousel-body.html, render/templates.json, render/KIT_RULES.md, engine/run/kits.py, tests/test_render_templates.py, tests/test_piece_kits.py.
- 2026-11-17 Ruling (Krish, 2026-11-17): no dated-and-scored calls. Offer 3 (the scored call) is replaced by the live disagreement. Fix C7, the playbook scoreboard row and item 7 of the content-engine brief are withdrawn, and the copy doctrine no longer leans on checkable calls. The cover's scoreboard is removed in krishanraja/makeyourmindup PR 48.
- 2026-11-16 Comment drafts now follow krish-voice humour.md and comment-evidence.md (Krish, 16 Nov: "They're too pristine, not sharp enough, and not rough and human enough."). Krish asked for an aggressive 7-day push (16 Nov): the analysis first, then a comment campaign approved in batches in Codex, and a boost test on the top performers, each boost on his Yes.
- 2026-11-17 engine/humour.py, engine/control_center.py (Client.humour), growth.py, tests/test_humour.py, requirements-humour*.txt, AGENTS.md, docs/ENGAGEMENT-LOOP.md, CHANGES.md.
- 2026-11-16 Krish asked for an aggressive 7-day push (16 Nov): the analysis first, then a comment campaign approved in batches in Codex, and a boost test on the top performers, each boost on his Yes.
- 2026-11-15 Krish asked to improve automated creative production and advertising analysis, with ad account changes draft-only and no launches or budget changes.
- 2026-11-15 copied from content-engine (krishanraja/content-engine#719), where it was tested live on 15 Nov.

## What is next and what is waiting on Krish

- Next (2026-11-27): Krish decides whether to stay on ManyChat Pro (the trial ended 27 Nov) and approves the exact DM words before any flow goes live.
- Waiting on Krish (11 November): run Tasks 2 and 4 of the Cowork subscriber-push brief, the subscribe surfaces and the ranked swap list for Acquisition (`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`). Its Task 1 reading is now the weekly subscriber job (`jobs/subscribers.md`, first run 12 November) and its Task 3 profile links are the browser audit's (`jobs/channel-audit.md`, approved 12 November).
- Waiting on Krish (10 November): his yes or no on one outreach draft at his gate, a recommendation ask to Nate's Newsletter. Its author, Nate B. Jones, wrote the post it cites, read in full; it passed `growth.py check` and the voice check. He sends it from his own Codex session, on the exact draft he approves. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), and an ask to Gennaro Cuofano (The Business Engineer). Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`.
- Waiting on Krish (10 November): two rulings, nothing built until he gives them. At U5, may the swaps and pitches jobs research more than three a run (`intensity.json` raises only posts and engagement taps)? Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)? The third question, whether Substack shows subscribers per Note, was answered by the 12 November read: it found per-item subscriber metrics for posts and for Notes (two items inspected, not the whole week).
- Waiting on Krish (30 October): whether a past piece's repurposed carousel belongs in the Sunday mix or goes live per post. Today it is not in the mix, so the derived lane neither makes nor releases it.
- Waiting on Krish (29 October, not re-checked since): six set-up answers. The Canva Cowork prompt (retired with the Canva lane on 26 November); the Substack handle (@mindmake belongs to another profile named Mindmake); the Buffer plan purchase, his click; whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry.
- Waiting on Krish (11 November, optional): one instruction from Control Centre's Engine drawer, to prove protocol 1.20.0 live end to end. The runner acks it received, then a workspace job or an engine session acks started, done or blocked.
- Open elsewhere: the GA4 paid event name (`invariants/ga4.json`; `sign_up` is verified, 12 November), and the Wave 2 fields Control Center was asked to name on 29 October, not re-checked since (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`).
- North Star check (2026-11-27): holds.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.
- `docs/history/LOG.md`: what this page used to say, verbatim.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack. The maker's failed runs from 30 October to 11 November were the loud hold for weeks whose mix plan or slots record never reached Control Center, not a fault in its code; since 12 November a week with no approved mix raises one ask instead, and since 26 November it drafts nothing (`docs/MAKER.md`, "With no approved mix").
