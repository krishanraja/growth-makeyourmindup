---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-11-05
head: d5671ca
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

The makeyourmindup growth engine: it plans, schedules, posts and measures the work that brings new readers to the publication, and drafts its outreach and engagement, with no paid boosts. Since 5 November it runs as four engines: Acquisition, Engagement, Publishing, and Measurement and Allocation.

## Who it is for and why it matters for Mindmake

Senior commercial leaders who should be reading makeyourmindup. The publication is the front door to Mindmake.

## Where it is right now (as of 2026-11-05)

<!-- north-star-state {"week_of": "2026-11-02", "week_target": 86, "current": 1, "current_as_of": "2026-11-05", "current_source": "Substack Growth sources, new subscribers, 7 days to 2026-11-05, read 2026-11-05 in Krish's working copy and recorded in docs/reviews/2026-11-05-growth-engine-review.md: all sources 1, under Substack then its child category Notes, counted once; organic not classified; the Note and any outreach link unknown", "urgency": 5, "urgency_reason": "1 of 86; under two fifths two weeks running"} --> **North Star number: U5, stalled.** 1 of 86 new publication subscribers this week from organic posts and shares, read on 5 November 2026.

Lifecycle: live. The detail is in `README.md`.

**Current (5 November 2026).** The four growth engines are built (AGENTS.md, "Four engines"; `now-notes/2026-11-05-four-engines.md`). Start a session with "Run Acquisition", "Run Engagement", "Run Publishing" or "Run Measurement": one engine per session, first command `python growth.py engine start NAME`. This is the shadow week: the nine automations, `jobs/daily-growth.md` and the GitHub workflows keep running, and Measurement then compares the engines' decisions with what they did. Make Your Mind Up outreach is this engine's, owned by Acquisition; Krish enacts outreach and social engagement in his own Codex sessions on the exact payload he approves; only Mindmake's outreach stays with Control Center (Ruling, Krish, 2026-11-05). Buffer's TikTok short-video route is held; the native TikTok uploader is the alternative (`social/tools/buffer.json`).



Dated checkpoints from 30 October to 1 November (measurement, midpoint, Sunday review) are in `docs/SESSION-HANDOVER.md` and `now-notes/`. The 30 October subscriber reading is superseded by the 5 November one above.

28 October, Wave 1 of the plan Krish approved that day ("Make Your Mind Up:
one weekly chain that runs on time"): release is pinned to this engine's
eight Buffer channels by channelId as well as service and name, checked
against a read-only list of all twelve channels in the shared organisation.
The fulltime.fm, Heartside and both yourdoghasnotes channels are refused by
id in every release step and in social preflight, which a Buffer draft
package passes before the daily job saves it (`engine/buffer_channels.py`).
Content-engine's copy lint (version 2026-10-29.3, which also refuses
"Krish's read" and "illustrative" labels and, since 29 October, his name
anywhere in public copy) is vendored and runs in run lint, social preflight
(captions and alt text), release (words, carried alt text and titles),
autonomous audit repairs, drafted pack replies and the post drafts the
Control Center loop proposes. On a route not yet verified, release sends only the run's earliest
approved post, as that route's capability check, and holds the rest. His 28
October rulings are recorded: go-live is "Approve each day Monday", every
route goes through Buffer with a first-post capability check, Growth makes
derived carousels to content-engine's standard, owns the Tuesday, Thursday,
Saturday and Sunday lane on Instagram, TikTok and Shorts, and prepares a
daily 10-minute engage queue. Nothing new posts yet: the per-post go-live
reads, the pull, the manifest, the lane and the queue are Wave 2.
The share package (built to be sent, his 28 October ruling) is merged on the
same branch: every snackable package and run slot declares a share block (who
sends it to whom, for which job, in what words), snackable copy carries no
generic share ask (refused in run lint, preflight and release), and a blind
send-test reader must name the declared receiver and job before Krish sees it
(R99; run status compares that answer again on every read). Sends and saves
per reach are the snackable lane's measure, a house hypothesis until MYMU's
own dated data confirms it. Pitches, swaps and partner notes are private
emails he sends from his own address, so they may carry his signature; every
public draft is still refused if it names him. 376 local tests pass (29 October).

## What changed recently

- 2026-11-05 **Four engines, and Make Your Mind Up outreach is this engine's.** Built from `docs/reviews/2026-11-05-growth-engine-review.md`: `growth.py engine` (start, check, show, history, handoff, done, close, session), contracts in `engines/`, records in `engines/records/`. Every session closes with "better next time" learnings; work for another engine is handed off after asking Krish "Do you have a session running for the X engine?". Pitches, partners and swaps packs still never go to Control Center. Buffer TikTok short-video is held. Nothing posted, sent or spent.
- 2026-10-30 **One press on the board approves the week's mix (R124).** Krish: "approve the week's mix once, let Growth fill it". Release and the maker now take his "Approve this week's mix" press on content-engine's board (pieces route `mix`, read with GROWTH_WRITEBACK_TOKEN) as the derived lane's approval, only on the hash of the mix Growth proposes from its own plan (`offday.proposed_mix`, mirroring content-engine), and only inside it (day, option concept, channel:format). No press holds quietly; another hash holds loudly and is proposed again. His Control Center no still stops; series go-lives are unchanged. Nothing posted, sent or spent.
- 2026-10-29 **Wave 2's Growth parts are built, in PRs #32 to #34 (stacked, open, each merged with main after PR #31).** W2.8: a go-live dispatch can name content-engine's piece manifest, and any draft that is not exactly its channel's post is held (R115); one go-live per post through `per_item_review`, with his No before release as the Pull; each engage tap opens the exact post or profile (R116); sends and saves per reach reach the measure report (R117); YouTube long-form is a route. W2.9, after his "Mix wins: every day": `growth.py mix offdays`, `mix topup` (never the series slot or over a cap, R118) and `mix clock`; a filler claim with a figure names its source (R119). W2.11 and W2.12: `config/studio.json` and a path guard (R120); NOW.md history moved to `docs/history/LOG.md` under a 16 KB cap. W3.3: a SessionEnd hook keeps his flagged, scrubbed corrections locally (R121). Nothing posted, sent or spent.
- 2026-10-29 **The maker and Codex art direction are built.** `maker.yml` (L0, 04:30 UTC) drafts the next New York day's posts from ideas and mocks Krish approved: the exact approved mock bytes from Drive (`4 Growth/mocks`, shared by link), his claim word for word, words and a separate blind review through the Anthropic API, a Buffer draft with no due time, handed off for release; it never schedules. `artdirect.yml` (L0, Saturdays 07:00 UTC) has Codex invent one visual idea per piece as a piece kit (`render/pieces/`), which the renderer's checks gate; passing kits come as a pull request. Rulings: the code renderer draws every post (blind bake-off, he picked it), Codex art-directs, Canva is reference only, and both model jobs stay in L0. All 130 W45 mock files are in Drive and verified by sha256 through their public links. 827 tests.
- 2026-10-29 **The mock kit matches the published artwork.** The renderer (`render/`, `scripts/render_mocks.mjs`) now draws the wordmark, two-tone headlines, versus rows, number cards, video chapter cards and evidence cards from the 19 and 26 October publish boards Krish pointed to; `render/KIT.md` marks each rule observed or interpreted. The passports motif and his headshot are left out (his ruling; no content names him). Every template renders byte-identically, so a mock's hash is reproducible. The W45 board went to his list as three asks.

## What is next and what is waiting on Krish

- Next (5 November): Krish runs one engine session ("Run Acquisition" first) to start the shadow week, and rules on the one open conflict: the review keeps every ready LinkedIn draft open in its tab, while BROWSER.md allows one prefilled LinkedIn box at a time (BROWSER.md holds until he does).
- North Star check (2026-11-05): 1 of 86, U5 stalled; holds, no recalibration proposed.
- Waiting on Krish (2026-11-10, skills uplift): one outreach draft sits at his gate, for one named person and checked (`growth.py check`; `check_voice` email cold passes with no hard fails, its two-question count is the `?` in the tracked link): a recommendation ask to Nate B. Jones (Nate's Newsletter), whose post was read in full. Three more are held, not at his gate, until their source is read in full: pitches to Claire Vo (How I AI) and Dan Turchin (AI and the Future of Work), built from episode notes with neither episode heard, and an ask to Gennaro Cuofano (The Business Engineer), whose post was read only to its paywall. Rows are in `lists/swaps.md` and `lists/pitches.md`; exact words stay in the ignored `.scratch/`. He sends from his own Codex session, on the exact draft he approves. Three asks, nothing built until he rules:
  1. At U5, may the swaps and pitches jobs research more than three a run? `intensity.json` raises only posts and engagement taps.
  2. Is one honest follow-up, seven or more days after no reply, allowed under "no follow chasing" (rule 5)?
  3. Does Substack show subscribers per Note, or only the Notes category? Per-Note attribution gets built only if it shows them.
- Cadence (Krish, 29 October, late): Mon/Wed/Fri restarts on Mon 2 Nov with the 30 Oct recording, then Wed 4 the 28 Oct recording, Fri 6 the 23 Oct piece, Mon 9 the 26 Oct piece. Until then the mix carries carousels, memes and explainers. Release each piece on its new day once content-engine has moved the board.
- Board tick (R122, 29 October): after each release run Growth ticks the publish board box for every piece post Buffer shows sent, through content-engine's `/api/board/<Monday>/posted`. It waits on Krish setting the GROWTH_WRITEBACK_TOKEN secret here and in content-engine's Vercel, and on the board's `/pieces` read. The sent listing now asks Buffer for `sentAt`; suspected the measure job skipped every live sent post before this, to confirm on its first run after merge.
- Protocol 1.17.0 (R123, 29 October): each go-live's report names the pinned Buffer channels, which Control Center now requires before he can approve a go-live of posts; measure sends per-post numbers, the daily report the week's off-day options; his off-day top-up press is accepted. Open: the "filler slots filled" count on the off-day clock line.
- Next (in this order, agreed with Krish 29 October):
  1. W45 goes live: one `growth-mix-plan` dispatch with the identical W45 plan plus `mock_files` (the 130 Drive ids, kept privately by the session that verified them) and `records_only: true` writes the slots and mock manifest records (dry run first). Krish approves the three W45 parts on Sunday 1 November; the maker's 04:30 UTC run on 2 November drafts Monday, release schedules it. Release holds every post on a route not yet recorded as passed in `social/tools/buffer.json` (none is yet), so each route's first real post (Instagram, YouTube Shorts, TikTok, X) goes out as its capability check through `growth.py run release`, approved by Krish that morning, and each route that passes is recorded. First live checks: Buffer keeps the Drive asset URL (else `draft_assets_differ_from_mock`), the draft is a draft with no due time, and the first `artdirect` run's Codex cost, reported before its second run.
  2. Built on 29 October in PRs #32, #33 and #34 (Growth's part of Waves 2 and 3; merge in order, each green): a new session finishes Wave 2 and Wave 3 of the engine upgrades (Wave 2: one go-live decision read per post, the manifest, route checks, metrics, the engage queue and the off-day lane) before any further production work.
  3. Content-engine (content.krishraja.com, its own repository) shifts every piece on the Publish Board back one week so w/c 26 October is blank and next week has a full queue on schedule. Critical, and not this repository's to do.
  4. A separate session post-produces this week's Wednesday and Friday videos from the Inbox on the upgraded engine: art direction locked with Krish first (mocks of the intro, scene changes and outro), and the audio levelled to a measured standard (about -14 LUFS integrated, true peak under -1 dBTP, voice clarity), since Monday and Wednesday were soft. Target by Sunday: both videos ready for next Wednesday and Friday, and the following week fully planned.
  Then content-engine writes `0 Publish/manifest.json` and dispatches with `piece_manifest` and `per_item_review` on every slot, and Control Center names the fields for `engage_done`, `offday_stocked`, `offday_slots_filled` and the backstop's `taste_reports` route (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`). First off-day posts Tuesday 10 November.
  The GA4 event-name readback (`invariants/ga4.json`) is still open; LinkedIn stays his own click.
- Waiting on Krish (R124): a past piece's repurposed carousel is not in the board's mix (the Off-days file carries the filler lanes only), so it is not made or released through the derived lane. Should the Sunday mix carry it, or does it go live per post?
- Waiting on Krish: run the Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake);  the Buffer plan purchase (his click: he keeps Buffer for makeyourmindup and Heartside, 29 October; Essentials keeps every capability the engine uses, Full Time is added at its launch); whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry: @therealkrisho (X and TikTok), krishraja1 (Threads), linkedin.com/in/krish-raja and hello@krishraja.com (nothing renamed). The architecture branch is now merged into main. New Claude cloud scheduled tasks (the architecture plan's release and measure automations) are off the table: Krish, 2026-10-29, "I want zero Claude routines. No Claude schedules of any kind in this architecture"; a new schedule here is a GitHub Actions job.
- North Star check (2026-10-29, Wave 2 session): holds. Still 0 of 25 at U4; Wave 2 moved the posting path (approved posts checked against the board, top-ups into free slots), not the number.
- Earlier check (2026-10-29, late): holds. Still 0 of 25 at U4. The machinery for the floor is built (maker, art direction, kit); the number moves once W45 is approved and the maker's first drafts go out from 2 November. Still 0 of 25 at U4; this session moved the floor's machinery, not the number: once he approves W45 and the `BUFFER_API_KEY` secret is set, Instagram, YouTube Shorts, TikTok and X can carry three to four posts a day.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack.
