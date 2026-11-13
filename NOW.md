---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-13
head: 76cb028
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

## Where it is right now (as of 2026-11-13)

<!-- north-star-state {"week_of": "2026-11-02", "week_target": 86, "current": 1, "current_as_of": "2026-11-08", "current_source": "Substack Growth sources, new subscribers, Custom... (2026-11-02 to 2026-11-08), read 2026-11-12: all sources 1, organic 1", "urgency": 5, "urgency_reason": "1 of 86; under two fifths two weeks running"} --> **North Star number: U5, stalled.** 1 of 86 new publication subscribers in the week of 2 November 2026 from organic posts and shares, the whole week to 8 November 2026.

The last reading is the whole week of 2 November: 1 new subscriber of 86, all sources and organic alike, read from Substack on 12 November (`jobs/subscribers.md`). The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet: the engine's own reading of an unmeasured week is U4 (`engine/intensity.py`), raised to U5 by Control Center's directive, so the runs go at U5 and the subscriber push is on. The line above changes only on a measured reading: `growth.py run subscribers ingest` or `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- One plan now holds everything lined up for this engine: docs/plans/A1.md consolidates NOW.md's waiting items, GET-GOING's open steps, the counted-lattice exhibit, the keyword-DM plan, the briefs, experiments.json, lanes.json and failures.json, with duplicates merged, stale items closed, and the build steps that lived only in a session's plan file (first go-live, Note Press, release loop, lattice ledger) written in. GET-GOING points to it. (2026-11-13)
- Saturday 14 Nov's explainer carousel "AI is fixing what we got wrong" is made, at nine cards with a realistic scene on every card. It passes the ten-second swipe at 50 headline words and content-engine's 10/10 judges at 9 (ready). It is filed with send.py to 3 Posts/2026-11-14 Sat off.day - Five good things AI did for people/4 Social as "AI fixing what we got wrong v2" and read back with every hash matching; v1 is in the Drive bin on Krish's yes. Nothing is posted or scheduled. (2026-11-13)
- The Counted Lattice plan is built in its first three steps (branch claude/sharp-knuth-2qb0jp): the source clock keeps every post's Buffer counts, each Note's free subscriptions among them (the 4 November Note reads 1 over 208 impressions); the subscribe hook fails closed; one four-tag route is checked on the engine's own go-live path; every post, Buffer-made or native, is reconciled for a route; and each run ends with one outcome row. The U5 exhibit, its five numbered questions and the test cards are in docs/plans/2026-11-13-counted-lattice.md. (2026-11-13)
- Every carousel, meme and Notes image this engine makes is made in a Claude session with the Codex plugin building it (a ve card queued in codex/queue/ for the Codex lane, held to the brand palette and the references Krish ticked), and off-day voiceover shorts on content-engine's ve route; the Saturday art-direction workflow and its Codex runner are retired, the kit checks stay as growth.py run kit, and memes and Notes images left the Canva lane (R126). (2026-11-13)
- The GitHub runner takes back its own undecided asks once their week or window is over (Ruling, Krish, 2026-11-12), through the protocol's withdrawn[] with a one-line reason, and nothing new is asked about a week that has ended; its first run takes back the three parts of the mix plan for the week of 2 November. (2026-11-13) (2026-11-13)
- The engine proposes the publication's AI-answer questions for Krish's approval (Ruling, Krish, 2026-11-13). Twenty questions readers type or ask about the three series and Saturday's good news, each with its evidence and best piece (docs/ai-answers/2026-11-13-proposed-questions.md), go to his list once as one strategy ask (config/ai-answer-questions-proposed.json); on his yes, or his amended version, the runner writes exactly those into config/ai-answer-questions.json, asks AEO-Engine to track them and closes the ask, and the control-center workflow commits that one file. (2026-11-13)
- The publication's AI answers are AEO-Engine's, the one AI-answers specialist (Ruling, Krish, 2026-11-12): the runner reads the standing from the directive (protocol 1.22.0) and asks AEO to track the real reader questions in config/ai-answer-questions.json, which jobs/answer.md fills; none is on file yet, so nothing is asked. The protocol copy in docs/control-center/ is Control Center's at 36df34bc (protocol 1.22.0). (2026-11-13)
- Krish allowed one DM reply to someone who commented the keyword on that post (Ruling, Krish, 2026-11-13) and chose ManyChat, on a trial, for the keyword-DM test. Rule 5 in AGENTS.md and research.md, invariant R07 and the corpus digest now carry the exception, and the plan carries the setup. Nothing was posted, sent, spent or changed on any account. (2026-11-13)

## What changed recently

- 2026-11-13 Krish asked for an uplifting carousel on AI correcting past mistakes, then rebuilt it from his Perplexity research, then put the wider piece "The Great Recount" (human plus AI beats either alone) on Fri 20 Nov. Content-engine #627 moved the data-centres piece forward to Tue 17 Nov.
- 2026-11-13 Krish approved the plan as the build on 13 November 2026. The engine had shipped nothing on its automatic path, and no post carried a subscribe route, so the first steps make every unit attributable before any volume.
- 2026-11-13 Rulings (Krish, 2026-11-13): "all the carousels should now be done in Claude, but using the Codex plug in as per the other usual workflows"; "memes and Notes images should go the same way"; "Off-day voiceover shorts should go the same way too".
- 2026-11-13 An ask about a past week held every live ask behind it on Krish's one list (one ask per engine at a time), so the AI-answer questions and the keyword-DM experiment waited behind a mix plan for a week that was over. engine/stale_asks.py; docs/ENGINE.md, "Nothing stale on his list".
- 2026-11-13 AGENTS.md, research.md, invariants/rules.json, knowledge/corpus/external-growth-skills.md, experiments.json, docs/plans/2026-11-13-keyword-dm-test.md, docs/GET-GOING.md (Step 0.4).
- 2026-11-13 Ruling (Krish, 2026-11-12): "Judge them; count passes. Every Growth carousel goes through the same 10/10 judges, and each one that passes and goes live counts." engine/run/judges.py, the maker's step 6b, board tick's live report.
- 2026-11-13 Krish connected the correct account; live provider readback closed the connection hold. No post was created, moved or published.
- 2026-11-13 Krish ruled Threads always posts to makeyourmindup. Private receipts stay under ignored .scratch/channel-audit/profile-links-20261113.
- 2026-11-12 Krish, 2026-11-12: "make sure everything's a cohesive system and that the project documentation is 100% up to date with absolutely nothing old or misleading left in there".
- 2026-11-12 The full-week organic reading is now measured and recorded; the current week remains unmeasured.

## What is next and what is waiting on Krish

- Next (2026-11-13): Krish presses Yes on the standing W45 to W52 plan card in Control Center, typing in four Notes a day and Threads at @makeyourmind.up (A1.1); then the Growth: subscribers automation is scheduled before Monday 16 November (A1.2).
- Waiting on Krish (11 November): run Tasks 2 and 4 of the Cowork subscriber-push brief, the subscribe surfaces and the ranked swap list for Acquisition (`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`). Its Task 1 reading is now the weekly subscriber job (`jobs/subscribers.md`, first run 12 November) and its Task 3 profile links are the browser audit's (`jobs/channel-audit.md`, approved 12 November).
- Waiting on Krish (10 November): his yes or no on one outreach draft at his gate, a recommendation ask to Nate's Newsletter. Its author, Nate B. Jones, wrote the post it cites, read in full; it passed `growth.py check` and the voice check. He sends it from his own Codex session, on the exact draft he approves. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), and an ask to Gennaro Cuofano (The Business Engineer). Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`.
- Waiting on Krish (10 November): two rulings, nothing built until he gives them. At U5, may the swaps and pitches jobs research more than three a run (`intensity.json` raises only posts and engagement taps)? Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)? The third question, whether Substack shows subscribers per Note, was answered by the 12 November read: it found per-item subscriber metrics for posts and for Notes (two items inspected, not the whole week).
- Waiting on Krish (5 November): his ruling on how many prefilled LinkedIn drafts may be open at once. The engine review keeps every ready draft open in its tab, while BROWSER.md allows one prefilled box at a time; BROWSER.md holds until he rules.
- Waiting on Krish (30 October): whether a past piece's repurposed carousel belongs in the Sunday mix or goes live per post. Today it is not in the mix, so the derived lane neither makes nor releases it.
- Waiting on Krish (29 October, not re-checked since): six set-up answers. The Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake); the Buffer plan purchase, his click; whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry.
- Waiting on Krish (11 November, optional): one instruction from Control Centre's Engine drawer, to prove protocol 1.20.0 live end to end. The runner acks it received, then a workspace job or an engine session acks started, done or blocked.
- Open elsewhere: the GA4 paid event name (`invariants/ga4.json`; `sign_up` is verified, 12 November), and the Wave 2 fields Control Center was asked to name on 29 October, not re-checked since (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`).
- North Star check (2026-11-13): recalibration proposed. Central on measured rates is about 42 subscribers from 16 November to 28 December against a 7,894 ladder; Krish kept 2,500 and backed borrowed audiences on 13 November, so D1 (one founder-visible Live co-stream) and D2 (the lattice) are the next asks.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.
- `docs/history/LOG.md`: what this page used to say, verbatim.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack. The maker's failed runs from 30 October to 11 November were the loud hold for weeks whose mix plan or slots record never reached Control Center, not a fault in its code; since 12 November a week with no approved mix is drafted from the standing plan instead (`docs/MAKER.md`, "With no approved mix").
