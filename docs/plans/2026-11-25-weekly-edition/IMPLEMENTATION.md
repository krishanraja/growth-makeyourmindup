# The weekly edition: implementation plan (25 Nov 2026)

What gets built, by which repository, in which order, to deliver [`DESIGN.md`](DESIGN.md) as Krish decided it
([`DECISIONS.md`](DECISIONS.md)). Each repository changes only its own part (the brief: content-engine produces and
drafts, growth-makeyourmindup distributes and measures, makeyourmindup owns the site and the subscribe page,
control-center holds the board and his list). Every change is a draft pull request that Krish merges himself; every
repository changed gets a closeout note in `now-notes/`. Nothing in this plan sends, posts, schedules, publishes or
spends: the first send is edition one, on his Approve for send.

## Order

| Phase | What | Gate to the next phase |
|---|---|---|
| 0. Check | V1 and V2 below: read-only | V1 says whether a Video post can go web only |
| 1. Build | The pull requests below, in parallel: growth, content-engine and makeyourmindup first, control-center after content-engine's view change | Krish merges them |
| 2. Set up | K1 and K2: his settings in Substack | done in Substack, read back |
| 3. Dry run | Edition one drafted from 9 to 13 Nov's live pieces, for his approval (`dry-run/`) | his approval of the shape and the words |
| 4. Edition one | The first Saturday after phases 1 and 2 and the Library's approval, from that week's live pieces | his Approve for send |
| 5. Judge | After four editions, the bars in DESIGN.md section 6; two weeks after edition one, question 11's email | his yes on the email, and again on any removal |

## Phase 0. Check before anything relies on it

- **V1. Can a Video post skip the email?** Substack documents the "Send via email and Substack app inbox" box for posts
  and podcasts, not for Video posts (DESIGN.md section 11). Codex on the worker (Substack step only) opens a new Video
  post draft, goes to its publish settings, records whether the box and Advanced, "Only send to a specific audience
  segment" are there, and leaves without publishing. Result recorded in this folder. If neither exists, Krish chooses:
  a text post with the video embedded, or the Video post keeps its email.
  **Tried 25 Nov 2026, not settled.** Codex thread "MYMU V1: can a Substack Video post skip the email? (read only, 25
  Nov 2026)" on the worker found that Substack keeps Continue disabled until a video is attached, and the worker
  browser's upload tool refused every file path (it is outside the tool's workspace roots, even when the file is copied
  into the browser container). Nothing was published, sent, scheduled or uploaded; the test files were removed and the
  browser container was put back as it was. So V1 is settled the first time a Video post's publish screen is open with
  a video attached: Krish, when he next publishes a piece, or Codex once the worker's upload roots are configured.
  Until then C1 stays held and every piece keeps its current publish step. The same limit means the edition's Substack
  draft (G4) must need no upload: it uses Substack's post cards for the pieces, links and text, and the email header
  set once in Substack's settings.
- **V2. Baselines.** The Monday Substack read takes, for 2 to 13 Nov: unsubscribes a week, unique clicks a send, and each
  piece's web views in its first seven days (counts only). Without them the bars in DESIGN.md section 6 cannot be judged.

## Phase 1. The pull requests

### growth-makeyourmindup (distribution and measurement)

| # | Change | Files | Proof |
|---|---|---|---|
| G1 | The edition's own tagged links: an `edition` block in the one subscribe route (`utm_source=newsletter`, `utm_medium=email`, `utm_campaign=weekly`, `utm_content=edition-<YYYY-MM-DD>-<place>`), a builder for it, and the subscribe gate and GA4 reader crediting it to the source `newsletter`. The social `sources` stay exactly as they are. | `specs/subscribe-route.json`, `engine/route.py`, `engine/subscribe_gate.py`, `engine/run/ga4.py` | `tests/test_subscribe_route_spec.py` extended; every existing assertion kept |
| G2 | The invariant: a series piece's Substack step never emails the whole list. | `invariants/rules.json` | `tests/test_invariants.py` |
| G3 | The weekly read takes the edition's numbers (recipients, unique clicks, click rate, open rate, unsubscribes, subscriptions Substack credits to it) and each series post's recipients (0 outside the opt-in section), counts only, null with its reason when not shown; a series post that emailed everyone is a failure in the Sunday report. | `jobs/subscribers.md`, `engine/run/subscribers.py`, `jobs/report.md` | `tests/test_subscribers*.py` with fixtures |
| G4 | The Substack step, as a Codex job on the worker (Substack's editor only, never Buffer): Friday, build the draft from content-engine's edition package and send Substack's test email to Krish; Saturday 07:30 New York, schedule for 08:00 only when his Approve for send binds the package's sha256, converting the worker browser's time zone, and read back; 08:30, read back the send. Walls: no press or a changed package, no schedule; never publish now; never edit a sent post; record every outcome. | `jobs/edition.md`, `automations.json` | a dry pass on the dry run's package that stops before Schedule |
| G5 | The rulings in the rules this engine reads: Claude schedules in Buffer (Ruling, Krish, 2026-11-25); Codex keeps only the edition's Substack step; the publication now sends one email a week. | `AGENTS.md` ("Claude and Codex: who does what", "What you are growing"), `docs/PUBLISHING-AUTHORITY.md` (a dated 25 November section) | `tests/test_lane_docs.py` still green |
| G6 | Closeout note. | `now-notes/` | the closeout check |

### content-engine (production and drafting)

| # | Change | Files | Proof |
|---|---|---|---|
| C1 | The publish kit's Substack step says publish to the web only (untick "Send via email and Substack app inbox"), and how the opt-in readers get it; the subscribe line becomes the Saturday promise. **Held until V1 passes.** | `scripts/post-pack/publish_kit.py` (`SUBSCRIBE_ASK`, the Substack step), `docs/AMPLIFICATION.md` | the kit's self-test fails on "send to everyone" and on the old line |
| C2 | The vendored subscribe route, after G1. | `vendor/makeyourmindup/subscribe-route.json` | `tests/subscribe_route_test.py` (sha256) |
| C3 | The edition's settings: name, day and time, section order, word budgets, six to ten news items (at least four to send, at most two a subsector), topic heads read from the hub's `config/hub-sources.json` (26 Nov 2026; first `config/beat.json`), link tags. A setting is a row here, never code. | `config/weekly-edition.json` | schema test |
| C4 | The edition tools: `gather` (the week's live series pieces from their records, the good-news stories, the news candidates from the week's daily hub editions through `GET /api/board/<Monday>/edition/news`, which reads `hub_snapshots`; 26 Nov 2026, DESIGN.md section 3), `check` (every news item has a primary source address and the quote that supports it, word budgets, link tags, no em dash, no exclamation mark, the kill list), `render` (a preview page; the v5 template once approved), `package` (the edition draft with its sha256, filed like a post's manifest). | `scripts/edition/edition.py` | `tests/edition_test.py` with a fixture week |
| C5 | The weekly edition run: Claude Code in GitHub Actions on Krish's subscription, Friday 17:17 and 23:47 UTC (12:17 and 18:47 New York in winter), and a Run workflow button; a guard makes a second run do nothing; fenced like the good-news run (named scripts only, writes only under `docs/plans/`, no credentials in the checkout). It proposes; only his press sends. | `.github/workflows/weekly-edition.yml`, `.agents/skills/weekly-edition/SKILL.md`, `scripts/weekly_edition.py` (the guard) | a hand run on the fixture week |
| C6 | The Saturday card: the edition on the week's board as a Saturday item with its preview and its draft, and **Approve for send** bound to the draft's sha256 (409 if the draft changed). First choice: reuse the off-day manifest and its Approve for publish press; a new card kind only if that cannot carry it. | `apps/control-plane/api/board/` (`_manifest.ts`, `_yes.ts`, `_view.ts`, `view.schema.json`, fixtures) | the board's tests; the view contract version moves if its shape does |
| C7 | The rhythm and the handoff in the docs: the Friday run and the Saturday send in the week's clock; the edition package in the handoff to growth. | `docs/CADENCE.md`, `docs/GROWTH-HANDOFF.md` | |
| C8 | Closeout note. | `now-notes/` | |

### control-center (the board and his list)

| # | Change | Files | Proof |
|---|---|---|---|
| CC1 | The Content tab shows the Saturday edition card (its preview, its draft in Drive, Approve for send, and waiting, approved or changed), only if C6 needs more than the off-day card already shows. | `src/surfaces/content/board/` | the board's tests; a screenshot of the card |
| CC2 | His one list carries the press as a prepared item (ADR-034), if the off-day route does not already. | `api/_waiting.ts` | its tests |
| CC3 | Closeout note. | `now-notes/` | |

### makeyourmindup (the site and the subscribe page)

| # | Change | Files | Proof |
|---|---|---|---|
| M1 | The promise: the site's description and dek say one email every Saturday, not "three times a week" and "Free, every Monday, Wednesday and Friday"; the same in the Substack kit's copy. Words through `check_voice`. | `apps/cover/content/site.json`, `apps/cover/substack-kit/COPY.md`, `apps/cover/scripts/build-brand-kit.mjs` | the cover's tests; a copy test refusing the old promise |
| M2 | Closeout note. | `now-notes/` | |

The v5 site mock (makeyourmindup PR 54, the rebrand session's) carries the same promise line when it is wired in; the
line is handed to that session in the shared notes.

## Phase 2. Krish's settings (his yes, at the time)

- **K1.** In Substack, Settings, Sections, add the opt-in section for readers who want every piece by email, with "Add
  new subscribers by default" and "Copy your email list" both off. A publication setting: his click, or Codex's on his
  word.
- **K2.** Substack's publication description and welcome email say what a reader now gets. The rebrand session's
  Substack prompt holds the new copy; the promise line comes from this plan.

## What stays exactly as it is

Every channel and its order; the off-day lane; Notes and series posts signed post by post; the one subscribe route and
its social tags; the release job and every existing test, invariant and fix. Nothing retired comes back: the old
promise line and the per-piece email to everyone are refused by C1, G2 and M1.

## Where each piece is (25 Nov 2026, evening)

All drafts, held for the switch-over week (26 Nov: Krish allowed merging work that is 10/10, on the rebrand session's
advice, and that session's call is to hold them): they merge together once the rebrand session says the Library is
locked, V1 is read and K1 and K2 are done, and makeyourmindup 55 also needs Krish's own yes then, since it changes the
live site's promise. Merge order: growth 144, then content-engine 980 (once the hub pipeline has merged) and 979, then control-center, then makeyourmindup
55. This plan's own pull request (growth 143, documents only) merged on 26 Nov with that session's yes.

| Items | Pull request | State |
|---|---|---|
| G1 to G6 | krishanraja/growth-makeyourmindup#144 | built; 183 changed tests pass here, 1,492 on the worker; the Substack job reads the press from content-engine's edition route |
| C3 to C8 | krishanraja/content-engine#980 | built; the edition run, package and Saturday card (contract 1.35.0); the early run moved to 20:17 UTC and holds while a picked piece is not live; 26 Nov: its news comes from the week's daily hub editions, so it merges after the hub pipeline (content-engine `hub/daily-pipeline`, which brings `config/hub-sources.json` and `hub_snapshots`) and is rebased on it first |
| C1, C2 | krishanraja/content-engine#979 | built and held until V1; carries the vendored route from 144 |
| M1, M2 | krishanraja/makeyourmindup#55 | built; its red check is main's NOW.md over its byte cap, not this change |
| CC2 | krishanraja/control-center#1030 | built; his one list names the edition while it waits for Approve for send and opens the Saturday card (no Clear, Bump or Purge: his answer is the press on the card); 112 list tests pass here. CC1 is not needed (the board draws the new item generically) |
| V1 | not settled | the first Video post publish screen opened with a video attached |
| K1, K2 | Krish's Substack settings | not started |
| Dry run | `dry-run/` in this folder | held until the rebrand session says the Library is locked and names the template IDs (DECISIONS.md, 25 Nov: Krish's hold, then "it should wait on your say so"); then rendered by content-engine in the weekly edition template it names and brought back to Krish once, for the shape, the words and the look |
