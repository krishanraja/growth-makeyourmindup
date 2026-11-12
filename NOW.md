---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-12
head: ed49aaa
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

The makeyourmindup growth engine: it plans, schedules, posts and measures the work that brings new readers to the publication, and drafts its outreach and engagement, with no paid boosts. It runs as four engines, one per session (Acquisition, Engagement, Publishing, and Measurement and Allocation), beside nine GitHub Actions workflows and ten PC automations: nine kept until W46, and the weekly Substack read (`jobs/subscribers.md`), which stands.

## Who it is for and why it matters for Mindmake

Senior commercial leaders who should be reading makeyourmindup. The publication is the front door to Mindmake.

## Where it is right now (as of 2026-11-12)

<!-- north-star-state {"week_of": "2026-11-02", "week_target": 86, "current": 1, "current_as_of": "2026-11-05", "current_source": "Substack Growth sources, new subscribers, 7 days to 2026-11-05, read 2026-11-05 in Krish's working copy and recorded in docs/reviews/2026-11-05-growth-engine-review.md: all sources 1, under Substack then its child category Notes, counted once; organic not classified; the Note and any outreach link unknown", "urgency": 5, "urgency_reason": "1 of 86; under two fifths two weeks running"} --> **North Star number: U5, stalled.** 1 of 86 new publication subscribers this week from organic posts and shares, read on 5 November 2026.

The last reading is 1 of 86 new publication subscribers for the week of 2 November, read on 5 November. The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet, so the engine reads it as U4 (`engine/intensity.py`) and the subscriber push is on. The line above changes only on a measured reading: `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- Every report that pulls the directive has carried protocol 1.20.0's state (priorities, obsessions and next steps) since the measure run of 12 November at 01:18 UTC. Krish has given this engine no instruction yet (read live on 12 November). (2026-11-12)
- The GitHub runner, release, measure, the key check and the ledger succeed every day. The maker has failed on every run since 30 October on a loud hold: W45's mix plan reached Control Center without its slots record (`slots_record_missing`), and W44's and W46's never reached it (`mix_plan_not_reported`), so the maker has drafted nothing. Release read no decisions on 12 November. All four secrets the maker reads are set. What unblocks it is a week's mix plan sent through the `growth-mix-plan` handoff with its slots and mock records (`growth.py mix plan`; `docs/MIX.md`). (2026-11-12)
- The live publish board is Control Centre's Content tab; content.krishraja.com/board is a read-only archive, and every ledger row links to the live board. Growth's off-day options (`growth.py mix offdays`) reach the live board only once content-engine's view reads them. (2026-11-12)
- The subscriber push is on (Ruling, Krish, 2026-11-11): at U4 and U5 every run slot and social package carries a tagged subscribe route (`subscribe_cta`), Acquisition prepares 2, 3 or 5 one-person outreach drafts a day at U3 to U5, Substack Notes rise to four a day and U5 engagement taps to 25. (2026-11-11)
- One canonical brand kit lives in Drive, `makeyourmindup / 1 Brand kit (permanent)`, indexed for agents in `social/brand/library.json` (`docs/BRAND-KIT.md`). (2026-11-11)
- Every post this engine makes or releases passes Control Center's one voice check before Buffer holds or schedules it, Krish's personal accounts and the publication's alike (`engine/voice.py`). (2026-11-09)
- The work runs as four engines, one per session (AGENTS.md, "Four engines"). Make Your Mind Up outreach is this engine's, owned by Acquisition, and Krish enacts it and social engagement in his own Codex sessions; only Mindmake's outreach stays with Control Center (Ruling, Krish, 2026-11-05). Buffer's TikTok short-video route is held; the native TikTok uploader is the alternative (`social/tools/buffer.json`). (2026-11-05)

## What changed recently

- 2026-11-12 **One live publish board (#67).** AGENTS.md says where the live board is and what Growth does on it; each ledger row's board link opens the live board at its week and day (Ruling, Krish, 2026-11-11: one live board, in Control Centre; the old board is a read-only archive).
- 2026-11-11 **Protocol 1.20.0 (#66).** Krish's instruction reaches the engine in the directive: the runner acks it received by id, a second wake the same day reports under its own run_id, a workspace job acts on it first and acks started, done or blocked, and every report that pulls the directive carries the engine's priorities, obsessions and next steps.
- 2026-11-11 **The subscriber push (#61).** Ruling (Krish, 2026-11-11): "dial up its urgency in getting me new subscribers to my substack". The Substack half is a Cowork brief, `docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`.
- 2026-11-11 **One canonical brand kit (#62 to #65).** Everything moved, nothing deleted, except `00_Brand-Assets`, which went to the Drive bin on Krish's instruction once music moved into the kit. The kit's Music and Style references stay as content-engine's mirrors.
- 2026-11-10 **Skills uplift (#60).** Acquisition ran by hand: one recommendation ask waits at his gate and three are held until their source is read in full; `growth.py check` refuses unsourced statistics. Claude sessions show Krish the Codex sign-in link and code when Codex is signed out (`.claude/hooks/codex-login.sh`).
- 2026-11-09 **One voice check for everything (#58, #59).** Krish, 2026-11-09: "we need to make sure everything goes through the same voice system. Absolutely everything."
- 2026-11-05 **Four engines, and Make Your Mind Up outreach is this engine's.** Built from `docs/reviews/2026-11-05-growth-engine-review.md`: `growth.py engine` (start, check, show, history, handoff, done, close, session), contracts in `engines/`, records in `engines/records/`. Every session closes with "better next time" learnings; work for another engine is handed off after asking Krish "Do you have a session running for the X engine?". Pitches, partners and swaps packs still never go to Control Center. Buffer TikTok short-video is held. Nothing posted, sent or spent.

## What is next and what is waiting on Krish

- Next (2026-11-12): build next week's mix plan (`growth.py mix plan`) and send it through the `growth-mix-plan` handoff with its slots and mock records, so Krish can approve its ideas and mocks and the maker drafts from them instead of failing.
- Waiting on Krish (11 November): run the Cowork subscriber-push brief. It gives this week's subscriber reading for Measurement and a ranked swap list for Acquisition (`docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`).
- Waiting on Krish (10 November): his yes or no on one outreach draft at his gate, a recommendation ask to Nate's Newsletter. Its author, Nate B. Jones, wrote the post it cites, read in full; it passed `growth.py check` and the voice check. He sends it from his own Codex session, on the exact draft he approves. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), and an ask to Gennaro Cuofano (The Business Engineer). Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`.
- Waiting on Krish (10 November): three rulings, nothing built until he gives them. At U5, may the swaps and pitches jobs research more than three a run (`intensity.json` raises only posts and engagement taps)? Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)? Does Substack show subscribers per Note, or only the Notes category?
- Waiting on Krish (5 November): his ruling on how many prefilled LinkedIn drafts may be open at once. The engine review keeps every ready draft open in its tab, while BROWSER.md allows one prefilled box at a time; BROWSER.md holds until he rules.
- Waiting on Krish (30 October): whether a past piece's repurposed carousel belongs in the Sunday mix or goes live per post. Today it is not in the mix, so the derived lane neither makes nor releases it.
- Waiting on Krish (29 October, not re-checked since): six set-up answers. The Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake); the Buffer plan purchase, his click; whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry.
- Waiting on Krish (11 November, optional): one instruction from Control Centre's Engine drawer, to prove protocol 1.20.0 live end to end. The runner acks it received, then a workspace job or an engine session acks started, done or blocked.
- Open elsewhere: the GA4 paid event name (`invariants/ga4.json`; `sign_up` is verified, 12 November), and the Wave 2 fields Control Center was asked to name on 29 October, not re-checked since (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`).
- North Star check (2026-11-12): holds.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.
- `docs/history/LOG.md`: what this page used to say, verbatim.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack. Do not read the maker's daily failed run as a fault in its code: it is the loud hold for a week whose mix plan or slots record never reached Control Center.
