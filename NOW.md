---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-17
head: e710d5d
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

The makeyourmindup growth engine: it plans, schedules, posts and measures the work that brings new readers to the publication, and drafts its outreach and engagement, with no paid boosts. It runs as four engines, one per session (Acquisition, Engagement, Publishing, and Measurement and Allocation), beside ten GitHub Actions workflows and ten PC automations: nine kept until W46, and the weekly Substack read (`jobs/subscribers.md`), which stands.

## Who it is for and why it matters for Mindmake

Senior commercial leaders who should be reading makeyourmindup. The publication is the front door to Mindmake.

## Where it is right now (as of 2026-11-17)

<!-- north-star-state {"week_of":"2026-11-09","week_target":162,"current":0,"current_as_of":"2026-11-15","current_source":"Substack new-subscriber emails to Krish's inbox, New York week of 2026-11-09: 0 new, 0 organic; counted by Control Center","urgency":5,"urgency_reason":"under 40% of the week's target two weeks running (0% now)"} --> **North Star number: U5, stalled.** New publication subscribers a week from organic posts and shares, zero paid: 0, against 162 in the week of 9 November 2026, on the way to 2,500 by 28 December 2026. Everything else pauses unless it moves the number.

The last reading is the whole week of 2 November: 1 new subscriber of 86, all sources and organic alike, read from Substack on 12 November (`jobs/subscribers.md`). The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet: the engine's own reading of an unmeasured week is U4 (`engine/intensity.py`), raised to U5 by Control Center's directive, so the runs go at U5 and the subscriber push is on. The line above changes only on a measured reading: `growth.py run subscribers ingest` or `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- The humour engine is on call here: `python growth.py humour check|compare|doctor` (engine/humour.py), holding three house rules (no joke at the poster, no humour on Mindmake, no joke that needs explaining), with AGENTS.md saying when to consult it. (2026-11-17)
- Every Make Your Mind Up post from 5 Oct to 14 Nov (139, read from Buffer) is analysed in docs/reviews/2026-11-16-what-works.md, with four new lessons: reach, not polish, is the constraint; Instagram video that opens on one named thing holds people; a written Substack Note brought the only subscriber; Threads and X video earn almost nothing. Four posts still look paid, unconfirmed, because Codex could not reach the browser. (2026-11-16)
- AGENTS.md says where each kind of Codex work runs (Ruling, Krish, 2026-11-15): visual builds are content production, queued as cards from any session and built by his PC's lane, never shown in Codex Desktop; social legwork is started only from a Claude session on his own computer, through scripts/codex_thread.mjs, so it shows in his Codex Desktop app. (2026-11-15)
- `growth.py run paid audit` reads paid reach apart from organic interest, read only (R131): on 15 Nov's Buffer read it found the same four posts that look paid as the hand review (TikTok and YouTube 11 Nov, YouTube and Facebook 13 Nov), none with a boost reading. HyperFrames and Claude Ads were evaluated and neither is installed (docs/reviews/2026-11-15-hyperframes-and-claude-ads.md); the slideshow video job keeps its seconds with mixed frame sizes. (2026-11-15)
- scripts/codex_thread.mjs carries the canonical header (ai-harness holds the source, byte for byte, since Krish approved the visible Codex sessions proposal), and AGENTS.md says so. (2026-11-15)
- the branch sweep takes an approved list (branch@sha) on a hand run and deletes each named branch only at that exact commit, skipping and logging anything else; the weekly run is unchanged. Copied from ai-harness's canonical script and workflow. (2026-11-15)
- Claude starts Codex only through scripts/codex_thread.mjs, focus sprints included: a permanent thread in Krish's Codex Desktop recents, released after every turn so he can type in it too. (2026-11-15)
- A weekly branch sweep (`.github/workflows/branch-sweep.yml`, Sunday 03:17 UTC, and by hand) deletes every remote branch whose work is already on main and lists each branch it keeps with why: unmerged work, an open pull request, protected (Ruling, Krish, 2026-11-15). The script is `.github/scripts/branch_sweep.py`, copied unchanged from ai-harness, which holds the canonical copy. (2026-11-15)

## What changed recently

- 2026-11-17 engine/humour.py, engine/control_center.py (Client.humour), growth.py, tests/test_humour.py, requirements-humour*.txt, AGENTS.md, docs/ENGAGEMENT-LOOP.md, CHANGES.md.
- 2026-11-16 Krish asked for an aggressive 7-day push (16 Nov): the analysis first, then a comment campaign approved in batches in Codex, and a boost test on the top performers, each boost on his Yes.
- 2026-11-15 Krish asked to improve automated creative production and advertising analysis, with ad account changes draft-only and no launches or budget changes.
- 2026-11-15 copied from content-engine (krishanraja/content-engine#719), where it was tested live on 15 Nov.
- 2026-11-15 Krish, 15 Nov: "the thumbnail is ridiculously poor, and that must never be the case"; the cover did not look like a front cover; the cards were bland, off centre and too short to follow; the POV meme was not centred.
- 2026-11-14 Fleet integration items I-09 and I-14, this repository's halves: tolerant readers behind flags, nothing made, scheduled or posted.
- 2026-11-14 Fixes from the fleet integration audit of 14 November 2026 (gmymu-1 to gmymu-6, gha-1, ai-cost-4): hardening and de-duplication only, nothing drafted, scheduled or posted.
- 2026-11-13 Krish ruled that Saturday's post, and all vertical content, goes to all five; Threads and X now take carousels and Threads takes shorts.
- 2026-11-13 The calendar's four weekly LinkedIn drafts and its LinkedIn cap are gone, the engagement queue is X, TikTok and Instagram, the handoff and release hold a LinkedIn slot before reading its draft, a week packet holds a LinkedIn slot and never names it in the ask, a tap opening a linkedin.com or lnkd.in page is refused whatever platform it claims, and LinkedIn's Buffer channel is no longer pinned and is refused by id (seven pinned channels), by the Buffer subscribe gate hook too, at every urgency. An edit goes by the channel its post was read on (a hook records it; an unread post's edit waits for get_post), an Engagement item is LinkedIn's by the page it opens, a page is read as a browser reads its host, the board tick never ticks LinkedIn, a go-live still waiting with a LinkedIn line is proposed again without it (only the 10 newest reports are looked at, the most Control Center serves, and the runner says so when that page is full), and the measure job, the learn job and the ledger still judge LinkedIn posts from before the handover, with no hold. AGENTS.md, CHANGES.md, docs/PUBLISHING-AUTHORITY.md and R125.
- 2026-11-13 Krish asked for an uplifting carousel on AI correcting past mistakes, then rebuilt it from his Perplexity research, then put the wider piece "The Great Recount" (human plus AI beats either alone) on Fri 20 Nov. Content-engine #627 moved the data-centres piece forward to Tue 17 Nov.

## What is next and what is waiting on Krish

- Next (2026-11-17): Run `python growth.py humour doctor` in the next session on Krish's computer that drafts a comment batch, and check each funny comment before the batch goes to him.
- Waiting on Krish (11 November): run Tasks 2 and 4 of the Cowork subscriber-push brief, the subscribe surfaces and the ranked swap list for Acquisition (`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`). Its Task 1 reading is now the weekly subscriber job (`jobs/subscribers.md`, first run 12 November) and its Task 3 profile links are the browser audit's (`jobs/channel-audit.md`, approved 12 November).
- Waiting on Krish (10 November): his yes or no on one outreach draft at his gate, a recommendation ask to Nate's Newsletter. Its author, Nate B. Jones, wrote the post it cites, read in full; it passed `growth.py check` and the voice check. He sends it from his own Codex session, on the exact draft he approves. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), and an ask to Gennaro Cuofano (The Business Engineer). Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`.
- Waiting on Krish (10 November): two rulings, nothing built until he gives them. At U5, may the swaps and pitches jobs research more than three a run (`intensity.json` raises only posts and engagement taps)? Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)? The third question, whether Substack shows subscribers per Note, was answered by the 12 November read: it found per-item subscriber metrics for posts and for Notes (two items inspected, not the whole week).
- Waiting on Krish (30 October): whether a past piece's repurposed carousel belongs in the Sunday mix or goes live per post. Today it is not in the mix, so the derived lane neither makes nor releases it.
- Waiting on Krish (29 October, not re-checked since): six set-up answers. The Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake); the Buffer plan purchase, his click; whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry.
- Waiting on Krish (11 November, optional): one instruction from Control Centre's Engine drawer, to prove protocol 1.20.0 live end to end. The runner acks it received, then a workspace job or an engine session acks started, done or blocked.
- Open elsewhere: the GA4 paid event name (`invariants/ga4.json`; `sign_up` is verified, 12 November), and the Wave 2 fields Control Center was asked to name on 29 October, not re-checked since (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`).
- North Star check (2026-11-17): holds.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.
- `docs/history/LOG.md`: what this page used to say, verbatim.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack. The maker's failed runs from 30 October to 11 November were the loud hold for weeks whose mix plan or slots record never reached Control Center, not a fault in its code; since 12 November a week with no approved mix is drafted from the standing plan instead (`docs/MAKER.md`, "With no approved mix").
