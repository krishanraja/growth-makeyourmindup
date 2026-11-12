---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-12
head: d435431
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

## Where it is right now (as of 2026-11-12)

<!-- north-star-state {"week_of": "2026-11-02", "week_target": 86, "current": 1, "current_as_of": "2026-11-08", "current_source": "Substack Growth sources, new subscribers, Custom... (2026-11-02 to 2026-11-08), read 2026-11-12: all sources 1, organic 1", "urgency": 5, "urgency_reason": "1 of 86; under two fifths two weeks running"} --> **North Star number: U5, stalled.** 1 of 86 new publication subscribers this week from organic posts and shares, read on 8 November 2026.

The last reading is 1 of 86 new publication subscribers for the week of 2 November, read on 5 November. The week of 9 November (162 on the ladder in `docs/NORTH_STAR.md`) is not measured yet, so the engine reads it as U4 (`engine/intensity.py`) and the subscriber push is on. The line above changes only on a measured reading: `growth.py run northstar` from a capture, or Control Center's North Star refresh from this engine's own live report.

Lifecycle: live. The detail is in `README.md`.

- A Growth render job wears a series colour only on that series' day or when it carries the series piece; a job with no tone is mint (`scripts/render_mocks.mjs`, `tests/test_render_templates.py` ToneFollowsTheDay). (2026-11-12)
- The 2–8 November capture was generated and validated with the current main subscriber command, then ingested with --write. Commit 937d9753b7be7fe934b5a186a6035a318a358457 records the North Star state and ledger on main; both files passed exact-content readback. Organic count: 1 of 86, U5. The private capture remains outside the public repository. Per-item inspection was partial: subscriber metrics exist for both posts and Notes; the capture contains the two items inspected, not a complete weekly item inventory. Scheduling: Neither Growth: subscribers nor Growth: answer piece was created or changed. Codex project and automation calls failed; the desktop connection subsequently became unavailable. The AGENTS.md Open setup line is retained because scheduling was not verified. No Substack settings, subscriber lists, cookies or passwords were changed. (2026-11-12)
- Growth's carousel and meme templates follow content-engine's brand palette: one house close for every carousel (takeaway, Subscribe free, wordmark bottom right), the meme mark in the bottom right, lilac as a fourth tone, and the art-direction gate refuses a new piece kit's own close. (2026-11-12)
- Every Buffer post on the engine's pinned channels must carry the tagged subscribe route at U4 and U5 (Ruling, Krish, 2026-11-12). A PreToolUse hook on the Buffer connector's create_post and edit_post runs `engine/subscribe_gate.py` and refuses a post without it (`subscribe_route_missing`), so hand-run session drafts are held to the same rule as release and preflight. Tests: `tests/test_subscribe_gate.py`. (2026-11-12)
- Krish approved the source classification and the subscriber rule on 12 November ("i approve 3, 4, 5"). `invariants/sources.json` is approved (approved_by Krish, 2026-11-12), so weekly readings count organic subscribers toward the North Star, with the all-source count beside them. The rule that judges a post by subscribers is approved as it stands: one sign-up in its first seven days works, none on at least 30 visits to its own link fails, anything else is insufficient (`FAILS_AT_SESSIONS`, engine/run/measure.py). The YouTube Data API is live in Control Center's gateway for this engine's research (first read: @makeyourmind-up, 20 videos, 707 views, 0 YouTube subscribers). (2026-11-12)
- Growth follows the one place an off-day post's day lives (content-engine `offday_items`; Ruling, Krish, 2026-11-12: any off-day post or idea moves to any day at his press, and the move updates every place that names its day). Each option he approved is bound to the day the board says (`autorelease.bound_options`), so a moved post goes out on its new day and is held on the day it left; `growth.py run board offer --file <offdays.json> --deliver` hands Growth's own options to the live board; `growth.py run board posts --deliver` (in release.yml after the tick) writes back each off-day post Growth made, scheduled or posted, from its own record (the index and Buffer, or a session's receipts with `--record`), so the board shows Growth's off-day posts out and says what is still scheduled for a day it left. (2026-11-12)
- The maker no longer fails while a week's mix waits on Krish (Ruling, Krish, 2026-11-12: with no approved weekly mix, the maker drafts from the standing plan and asks him once a week instead of failing). It had failed all 13 runs from 30 October to 11 November (`mix_plan_not_reported` for W44 and W46, `slots_record_missing` for W45) and made nothing. Now, until a week's mix is approved on the board, it drafts one X text post a day from a piece already published (`specs/standing-plan.json`'s cadence; Instagram, TikTok and YouTube Shorts need an edition he approved, so they get nothing), keeps each day's drafts in Control Center only (`makeyourmindup:standing:<day>`, never Buffer, never handed to release), and raises "This week's mix isn't approved" on his list once that ISO week (`makeyourmindup:mixask:<week>`). Once he approves the mix, the next run makes his plan. A past week with nothing left to make (its Sunday) is skipped and noted. Release and every gate are unchanged; a test proves a standing draft handed to release holds without his approvals (`docs/MAKER.md`, "With no approved mix"). (2026-11-12)
- The engine reads subscribers every week (Ruling, Krish, 2026-11-12: the engine reads subscribers every week and judges posts by subscribers, not engagement). A tenth PC automation, "Growth: subscribers" (Mondays 06:15 New York, `jobs/subscribers.md`, `standing` in `lanes.json` because only his signed-in browser can read Substack), fills `.scratch/substack/week-<Monday>.json` from the dashboard (total, new by source, per post and per Note where shown) and records the week's North Star reading through `python growth.py run subscribers ingest --write` (NOW.md state line when it loses nothing, `lists/northstar-history.jsonl` once); a read not taken is unknown with its code, never zero. GA4 `sign_up` is verified from Control Center's live Events report (`invariants/ga4.json`, `verified_from`); the paid event name stays open. Built and tested; the automation is not created yet, and the line counts organic subscribers only once Krish approves `invariants/sources.json`. (2026-11-12)

## What changed recently

- 2026-11-12 The full-week organic reading is now measured and recorded; the current week remains unmeasured.
- 2026-11-12 five piece kits had ended five different ways and memes carried the logo at the top; the palette Krish approved on 12 Nov allows one close and no logo at the top.
- 2026-11-12 58 posts went out through Buffer from 2 to 11 November with no subscribe ask, because hand-run drafts skipped preflight; the gate now sits on the path they took.
- 2026-11-12 `engine/cc_loop.py`, `engine/control_center.py`, `engine/mix.py`, the protocol and schema copies in `docs/control-center/`, `docs/ENGINE.md`, `docs/MIX.md`, `jobs/daily-pack.md`, tests.
- 2026-11-12 **Docs audit and the closeout fold.** The 32 waiting notes and NOW.md's old lines moved verbatim to `docs/history/LOG.md`; `next_steps` also sends NOW.md's "Waiting on Krish" items.
- 2026-11-12 **One live publish board (#67).** AGENTS.md says where the live board is and what Growth does on it; each ledger row's board link opens the live board at its week and day (Ruling, Krish, 2026-11-11: one live board, in Control Centre; the old board is a read-only archive).
- 2026-11-11 **Protocol 1.20.0 (#66).** Krish's instruction reaches the engine in the directive: the runner acks it received by id, a second wake the same day reports under its own run_id, a workspace job acts on it first and acks started, done or blocked, and every report that pulls the directive carries the engine's priorities, obsessions and next steps.
- 2026-11-11 **The subscriber push (#61).** Ruling (Krish, 2026-11-11): "dial up its urgency in getting me new subscribers to my substack". The Substack half is a Cowork brief, `docs/briefs/2026-11-11-cowork-substack-subscriber-push.md`.
- 2026-11-11 **One canonical brand kit (#62 to #65).** Everything moved, nothing deleted, except `00_Brand-Assets`, which went to the Drive bin on Krish's instruction once music moved into the kit. The kit's Music and Style references stay as content-engine's mirrors.
- 2026-11-10 **Skills uplift (#60).** Acquisition ran by hand: one recommendation ask waits at his gate and three are held until their source is read in full; `growth.py check` refuses unsourced statistics. Claude sessions show Krish the Codex sign-in link and code when Codex is signed out (`.claude/hooks/codex-login.sh`).

## What is next and what is waiting on Krish

- Next (2026-11-12): Give the daily maker's render jobs their post date, so Monday, Wednesday and Friday posts made from the series piece wear its colour.
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
