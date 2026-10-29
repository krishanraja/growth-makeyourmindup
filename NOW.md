---
repo: krishanraja/growth-makeyourmindup
product: makeyourmindup growth engine
as_of: 2026-10-29
head: fe391f0
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

## Where it is right now (as of 2026-10-29)

<!-- north-star-state {"week_of": "2026-10-26", "week_target": 25, "current": 0, "current_as_of": "2026-10-29", "current_source": "Substack Growth sources, new subscribers, 7 days (2026-10-22 to 2026-10-29), read 2026-10-29: all sources 0, organic not classified", "urgency": 4, "urgency_reason": "0 of 25; under two fifths"} --> **North Star number: U4, far behind.** 0 of 25 new publication subscribers this week from organic posts and shares, read on 29 October 2026.

Lifecycle: live. The detail is in `README.md`.

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

- 2026-10-29 **Wave 2's Growth parts are built, in PRs #32 to #34 (stacked, open).** W2.8: a go-live dispatch can name content-engine's piece manifest, and any draft that is not exactly its channel's post is held (R115); one go-live per post through `per_item_review`, with his No before release as the Pull; each engage tap opens the exact post or profile (R116); sends and saves per reach reach the measure report (R117); YouTube long-form is a route. W2.9, after his "Mix wins: every day": `growth.py mix offdays`, `mix topup` (never the series slot or over a cap, R118) and `mix clock`; a filler claim with a figure names its source (R119). W2.11 and W2.12: `config/studio.json` and a path guard (R120); NOW.md history moved to `docs/history/LOG.md` under a 16 KB cap. W3.3: a SessionEnd hook keeps his flagged, scrubbed corrections locally (R121). Nothing posted, sent or spent.
- 2026-10-29 **The mock kit matches the published artwork.** The renderer (`render/`, `scripts/render_mocks.mjs`) now draws the wordmark, two-tone headlines, versus rows, number cards, video chapter cards and evidence cards from the 19 and 26 October publish boards Krish pointed to; `render/KIT.md` marks each rule observed or interpreted. The passports motif and his headshot are left out (his ruling; no content names him). Every template renders byte-identically, so a mock's hash is reproducible. The W45 board went to his list as three asks.
- 2026-10-29 **PR #19 merged (`fe391f0`) after four adversarial reviews of the concept posting path.** His no on any part of any version stops the week for good; a line he adds or changes in an amended yes holds it; a concept he deleted or edited stays stopped; a concept goes out once per channel a week, as Buffer shows it; a post still scheduled or sent after his no is loud; the mock link he opens must download to a mock hash he approves; the local `run release` counts the day from Buffer too. Failures F120 to F132, rules R111 to R113, 745 tests on Python 3.9 and 3.12. Read back on main: keys, measure and release each ran green by hand with counts-only logs (release stops at "BUFFER_API_KEY not set"). The first W45 `growth-mix-plan` dispatch was refused `bad_weights`: GitHub hands the client_payload over with its keys reordered, and the handoff required mix.json's order. It now accepts any order and restores mix.json's (F132). The W45 board is published privately for Krish with every mock and its hash.
- 2026-10-29 **Concept approval runs on GitHub Actions** (branch of PR #19, merged with main's PR #26). Main's rules R101 to R104 keep their numbers; this branch's R101 to R106 are now R105 to R110. L0 `run autorelease` is the one executor for posts made from an idea and mock Krish approved in the week's mix plan: it reads the plan, his decision and each post's review back from Control Center by digest (never a local file, a dispatch or a PC `.scratch`), applies main's own readback rules (`engine/run/decision.py` `judge`, `cc_readback`, `concept_part`) and release's own checks (`concepts.authority`, `release.concept_post_hold` with `spec.review_reason`, the daily cap counted from Buffer), and schedules each 5 to 90 minutes before its time. A new handoff event, `growth-mix-plan`, takes the ideas board to his list without a PC `.scratch`, in parts of at most 8,000 characters when a week is longer. The go-live ledger is real on the runner (claims kept in Control Center), and a go-live naming more than one New York day holds (R94). Failures F111 to F119. Built and tested, not activated: nothing has been dispatched or scheduled this way.
- 2026-10-29 **V1 of the daily engine is merged with main (PR #19).** GitHub Actions (L0) runs everything mechanical with no session, no token in a session and no PC: the Control Center loop (05:10 UTC, backup 05:40), a daily key check (06:50), release of approved go-lives into Buffer every 30 minutes (`release.yml`, `run autorelease`: the exact signed words, assets, `meta` and Buffer channel, once, never LinkedIn, scheduled only 5 to 90 minutes before its time, and a loud `scheduled_after_decline` alarm), measurement at 07:00, 13:00 and 19:00, and the handoff that turns saved Buffer drafts into one-press go-lives. Under main's walls L0 release pins each account by name and channelId, holds any word that fails the copy lint (text, carried alt text, titles, first comments), any share ask, and every route not yet recorded as passed, whose one capability check goes through `run release`; today no route is recorded, so L0 releases nothing yet. Lanes are L0, L2 and L3 (`lanes.json`, `docs/LANES.md`; no Claude routines, Ruling, Krish, 2026-10-29); `invariants/authority.json` holds the standing derivative approval, shown first through 29 November; carousels and captions pass the plain-English lint; the Canva kit has its own lint; `calendar/v1.json` takes daily caps only from the channel records and `intensity.json`, so Threads and X stay at one a day until those change; makers follow `docs/TASTE.md` and read Inspiration House. Buffer stays for makeyourmindup and Heartside (Krish, 29 October); the plan purchase is his click, and Essentials keeps every capability the engine uses. Failures F66 to F99; this branch's rules R92 to R97 are renumbered R101 to R106 after main's R92 to R100. Waiting on Krish from it: the `BUFFER_API_KEY` GitHub secret (`docs/SETUP-ONCE.md`; release and measure do nothing with Buffer until it is set), trashing seven unused Canva drafts in the account root, and approving `invariants/sources.json` at G-A. 602 tests on Python 3.9 and 3.12.
- 2026-10-29 **The cloud runner sends each ask once** (plan item D2). It stopped re-proposing the four planned experiments every day: it reads Krish's decisions and its own latest earlier report from Control Center, never resends an ask he answered or one still waiting, and proposes nothing if it cannot read them. The standing W45 to W52 plan (`specs/standing-plan.json`) goes on his list once, as a plan behind strategy. The 26 October carousel pilot (`lists/pilots.json`) is reported as awaiting measurement with what closes it, until the Sunday report records its verdict.
- 2026-10-29 **Pitches, swaps and partner notes may carry his signature.** They are private emails Krish sends himself, not published content, so `engine/packs.py` skips only the `no_name` pattern for those pack kinds; every other copy-lint pattern still runs on them. The Tuesday pitch pack no longer fails its check on the sign-off in `jobs/pitches.md`.
- 2026-10-29 **No content names Krish** (his ruling of 28 October: "Remember, no content refers to Krish, ever."). The copy lint is re-vendored at 2026-10-29.3 with the `no_name` pattern and the `article_body` surface, which `engine/copy_lint.py` now knows; alt text (as carousel text), release titles and the Control Center loop's post drafts are linted too; the doctrine says the publication speaks as "we" and his personal accounts stay personal, never naming him. Rule R100.
- 2026-10-29 **Review fixes on the merged branch.** Share asks are refused only where they open a sentence, except three no true sentence about other people says, so true reporting ("X removed the share button") passes; run status compares a recorded send test again with the slot's share block; `social preflight --target` checks a reused Buffer draft's get_post readback before any edit_post; release holds a snackable slot that asks for the share and holds a route whose capability check another run released; `run send-test --stage` stages a slot's assets under blind names; the copy lint reads U+2028, U+2029 and U+0085 as line ends, as content-engine does; report and numbers packs may quote held copy; rule ids run past R99.

## What is next and what is waiting on Krish

- Next: merge #32, #33 and #34 in order (each green on CI), and PR #31 (the maker) beside them. Then content-engine writes `0 Publish/manifest.json` and dispatches with `piece_manifest` and `per_item_review` on every slot (`docs/briefs/2026-10-29-wave2-content-engine-and-control-center.md`), and Control Center names the fields for `engage_done`, `offday_stocked`, `offday_slots_filled` and the backstop's `taste_reports` route. Krish approves the W45 mix plan on his list. For Monday 2 November, prepare each Buffer route's first real post as its capability check for him, through `growth.py run release`, and record each that passes in `social/tools/buffer.json`. First off-day posts Tuesday 10 November. The GA4 event-name readback (`invariants/ga4.json`) is still open; LinkedIn stays his own click.
- Waiting on Krish: run the Canva Cowork prompt; the Substack handle (@mindmake belongs to another profile named Mindmake);  the Buffer plan purchase (his click: he keeps Buffer for makeyourmindup and Heartside, 29 October; Essentials keeps every capability the engine uses, Full Time is added at its launch); whether the blind send-test reader gets the North Star persona (`send_test.reader` in `social/share.json`) and whether share asks are refused beyond snackable posts (`share_cta_scope`); and his own handles and address that spell his name, which public copy can no longer carry: @therealkrisho (X and TikTok), krishraja1 (Threads), linkedin.com/in/krish-raja and hello@krishraja.com (nothing renamed). The architecture branch is now merged into main. New Claude cloud scheduled tasks (the architecture plan's release and measure automations) are off the table: Krish, 2026-10-29, "I want zero Claude routines. No Claude schedules of any kind in this architecture"; a new schedule here is a GitHub Actions job.
- North Star check (2026-10-29, Wave 2 session): holds. Still 0 of 25 at U4; Wave 2 moved the posting path (approved posts checked against the board, top-ups into free slots), not the number.
- Earlier check (2026-10-29, after the merge): holds. Still 0 of 25 at U4; this session moved the floor's machinery, not the number: once he approves W45 and the `BUFFER_API_KEY` secret is set, Instagram, YouTube Shorts, TikTok and X can carry three to four posts a day.

## Read next

- `docs/NORTH_STAR.md`: the North Star, its number and its weekly ladder.
- `README.md`: what this repository is and how it runs.

## Do not trust

Do not treat old draft IDs as immutable creative approvals: the Instagram and LinkedIn pilot revisions supersede their preserved before states. The rejected TikTok image revision and prior X draft remain held. Do not infer completed audit coverage, live automated posting or financial ROI from a prepared review pack.
