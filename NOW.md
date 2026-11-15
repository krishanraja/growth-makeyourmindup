---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-15
head: 2162844
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

## Where it is right now (as of 2026-11-15)

<!-- north-star-state {"week_of": "2026-11-02", "week_target": 86, "current": 1, "current_as_of": "2026-11-08", "current_source": "Substack Growth sources, new subscribers, Custom... (2026-11-02 to 2026-11-08), read 2026-11-12: all sources 1, organic 1", "urgency": 5, "urgency_reason": "1 of 86; under two fifths two weeks running"} --> **North Star number: U5, stalled.** 1 of 86 new publication subscribers in the week of 2 November 2026 from organic posts and shares, the whole week to 8 November 2026.

The last reading is the whole week of 2 November: 1 new subscriber of 86, all sources and organic alike, read from Substack on 12 November (`jobs/subscribers.md`). The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet: the engine's own reading of an unmeasured week is U4 (`engine/intensity.py`), raised to U5 by Control Center's directive, so the runs go at U5 and the subscriber push is on. The line above changes only on a measured reading: `growth.py run subscribers ingest` or `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- A weekly branch sweep (`.github/workflows/branch-sweep.yml`, Sunday 03:17 UTC, and by hand) deletes every remote branch whose work is already on main and lists each branch it keeps with why: unmerged work, an open pull request, protected (Ruling, Krish, 2026-11-15). The script is `.github/scripts/branch_sweep.py`, copied unchanged from ai-harness, which holds the canonical copy. (2026-11-15)
- No video leaves this engine without its designed cover: Buffer takes no cover image, so `growth.py run cover append` appends the cover as the cut's last second and sets thumbnailOffset to it, and release, the L0 carry, the maker and the pre-send read hold any video with a null offset (F133, R128). The house carousel cover now looks like a front cover, body cards carry one full centred sentence of 8 to 20 words under a visual anchor, the renderer reports every line so the kit check refuses an off-centre or out-of-margin card, and the judges get each card's view link (R129). Tall frames keep to the clear box (y 270 to 1320, x 200 to 880) and `meme-tall` with `growth.py run meme compose` centres a clip by construction (R130). (2026-11-15)
- Claude and Codex division written in (Ruling, Krish, 2026-11-15): Codex does the visual builds and the social legwork (post approved work, read it back for cover, caption and call to action, read measurement and paid boosts) in sessions Krish watches in Codex Desktop, never touching Drive or ai-harness. The weekly review gains "What worked, what did not, and why" with paid split from organic, beside the Sunday learn workflow; boost readings are `paid_boost` observations. First analysis: `docs/reviews/2026-11-15-interest-vs-paid.md`. (2026-11-15)
- krish@mindmake.co is Krish's public contact address here: AGENTS.md, the podcast pitch sign-off, the shared surface check and the one address a committed record may carry (Ruling, Krish, 2026-11-14). hello@krishraja.com stays recognised as his and is never written. (2026-11-14)
- our own pull requests (Krish or the Actions bot, branch in this repository, ready, at the commit that passed) now merge themselves when every "check" run on that commit is green (.github/workflows/auto-merge.yml, rule .github/scripts/auto-merge-pick.jq, tested). Forks, drafts and strangers wait for a person. (2026-11-14)
- krishraja.com (with and without www) now counts as an organic subscriber source in `invariants/sources.json`, by Krish's decision 5.12 of 14 Nov. Its two subscribe links already carry the publication's tracking tags (krish-raja #46). (2026-11-14)
- docs/control-center/ is Control Center's protocol bundle 1.33.0, byte for byte (bundle_sha256 4b7175a8aebbb8979eaefbeea1b7f0f44f2cffa0bbba9cea341da784fe7fde4d), the last protocol version of 14 November. (2026-11-14)
- docs/control-center/ is Control Center's protocol bundle 1.28.0, byte for byte (bundle_sha256 b0dfa0d7aaa10aea0de45fb5f7dcc241c62bef70766f0fed9c6351d69af1b791), with bundle.json and a hash test that fails an edit in place (integration plan I-11). (2026-11-14)

## What changed recently

- 2026-11-15 Krish, 15 Nov: "the thumbnail is ridiculously poor, and that must never be the case"; the cover did not look like a front cover; the cards were bland, off centre and too short to follow; the POV meme was not centred.
- 2026-11-14 Fleet integration items I-09 and I-14, this repository's halves: tolerant readers behind flags, nothing made, scheduled or posted.
- 2026-11-14 Fixes from the fleet integration audit of 14 November 2026 (gmymu-1 to gmymu-6, gha-1, ai-cost-4): hardening and de-duplication only, nothing drafted, scheduled or posted.
- 2026-11-13 Krish ruled that Saturday's post, and all vertical content, goes to all five; Threads and X now take carousels and Threads takes shorts.
- 2026-11-13 The calendar's four weekly LinkedIn drafts and its LinkedIn cap are gone, the engagement queue is X, TikTok and Instagram, the handoff and release hold a LinkedIn slot before reading its draft, a week packet holds a LinkedIn slot and never names it in the ask, a tap opening a linkedin.com or lnkd.in page is refused whatever platform it claims, and LinkedIn's Buffer channel is no longer pinned and is refused by id (seven pinned channels), by the Buffer subscribe gate hook too, at every urgency. An edit goes by the channel its post was read on (a hook records it; an unread post's edit waits for get_post), an Engagement item is LinkedIn's by the page it opens, a page is read as a browser reads its host, the board tick never ticks LinkedIn, a go-live still waiting with a LinkedIn line is proposed again without it (only the 10 newest reports are looked at, the most Control Center serves, and the runner says so when that page is full), and the measure job, the learn job and the ledger still judge LinkedIn posts from before the handover, with no hold. AGENTS.md, CHANGES.md, docs/PUBLISHING-AUTHORITY.md and R125.
- 2026-11-13 Krish asked for an uplifting carousel on AI correcting past mistakes, then rebuilt it from his Perplexity research, then put the wider piece "The Great Recount" (human plus AI beats either alone) on Fri 20 Nov. Content-engine #627 moved the data-centres piece forward to Tue 17 Nov.
- 2026-11-13 Krish approved the plan as the build on 13 November 2026. The engine had shipped nothing on its automatic path, and no post carried a subscribe route, so the first steps make every unit attributable before any volume.
- 2026-11-13 Rulings (Krish, 2026-11-13): "all the carousels should now be done in Claude, but using the Codex plug in as per the other usual workflows"; "memes and Notes images should go the same way"; "Off-day voiceover shorts should go the same way too".
- 2026-11-13 An ask about a past week held every live ask behind it on Krish's one list (one ask per engine at a time), so the AI-answer questions and the keyword-DM experiment waited behind a mix plan for a week that was over. engine/stale_asks.py; docs/ENGINE.md, "Nothing stale on his list".
- 2026-11-13 AGENTS.md, research.md, invariants/rules.json, knowledge/corpus/external-growth-skills.md, experiments.json, docs/plans/2026-11-13-keyword-dm-test.md, docs/GET-GOING.md (Step 0.4).

## What is next and what is waiting on Krish

- Next (2026-11-15): content-engine's judge route reads each asset's view_url so its panel sees the cards, and its piece manifest writes the per-channel cover field Growth now reads.
- Waiting on Krish (11 November): run Tasks 2 and 4 of the Cowork subscriber-push brief, the subscribe surfaces and the ranked swap list for Acquisition (`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`). Its Task 1 reading is now the weekly subscriber job (`jobs/subscribers.md`, first run 12 November) and its Task 3 profile links are the browser audit's (`jobs/channel-audit.md`, approved 12 November).
- Waiting on Krish (10 November): his yes or no on one outreach draft at his gate, a recommendation ask to Nate's Newsletter. Its author, Nate B. Jones, wrote the post it cites, read in full; it passed `growth.py check` and the voice check. He sends it from his own Codex session, on the exact draft he approves. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), and an ask to Gennaro Cuofano (The Business Engineer). Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`.
- Waiting on Krish (10 November): two rulings, nothing built until he gives them. At U5, may the swaps and pitches jobs research more than three a run (`intensity.json` raises only posts and engagement taps)? Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)? The third question, whether Substack shows subscribers per Note, was answered by the 12 November read: it found per-item subscriber metrics for posts and for Notes (two items inspected, not the whole week).
- Waiting on Krish (30 October): whether a past piece's repurposed carousel belongs in the Sunday mix or goes live per post. Today it is not in the mix, so the derived lane neither makes nor releases it.
- Waiting on Krish (29 October, not re-checked since): six set-up answers. The Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake); the Buffer plan purchase, his click; whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry.
- Waiting on Krish (11 November, optional): one instruction from Control Centre's Engine drawer, to prove protocol 1.20.0 live end to end. The runner acks it received, then a workspace job or an engine session acks started, done or blocked.
- Open elsewhere: the GA4 paid event name (`invariants/ga4.json`; `sign_up` is verified, 12 November), and the Wave 2 fields Control Center was asked to name on 29 October, not re-checked since (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`).
- North Star check (2026-11-15): holds.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.
- `docs/history/LOG.md`: what this page used to say, verbatim.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack. The maker's failed runs from 30 October to 11 November were the loud hold for weeks whose mix plan or slots record never reached Control Center, not a fault in its code; since 12 November a week with no approved mix is drafted from the standing plan instead (`docs/MAKER.md`, "With no approved mix").
