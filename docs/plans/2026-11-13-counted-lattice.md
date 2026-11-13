# The Counted Lattice: the U5 exhibit and plan (13 November 2026)

**1 of 86, U5, short by 85.** That is the week of 2 November, the last week measured. The week of 9 November
(162 on the ladder) is read on Monday 16 November (`jobs/subscribers.md`).

Krish approved this plan as the build on 13 November 2026. It aims at the number itself: new publication
subscribers a week from organic posts and shares, zero paid (`docs/NORTH_STAR.md`). Every send, post, spend
and permission change still needs his yes at that moment; urgency raises intensity, never authority.

## What is true today (measured)

- The automatic path (mix, maker, handoff, release) has never shipped a post. Every live post was hand-made,
  and none of the 70 posts Buffer listed to 11 November carried a subscribe ask; 51 carried no link.
- The week of 2 November: 28 posts, 2,367 exposures, 1 subscriber, from a Note on 4 November (208
  impressions). Notes since: 9, 3, 3 and 2 impressions.
- The standing W45 to W52 plan is undecided, so `handoff.open_plan` returns `no_open_plan` and every go-live
  holds. Nothing the engine makes can go live until Krish answers it.

## The reverse funnel

At the measured 4.4 counted subscribers per 1,000 Note impressions (1 of 225; exact 95% interval 0.11 to
24.8), 2,500 a week needs about 563,000 counted impressions a week, or about 101,000 at the top of that
interval. Owned surfaces delivered 2,367. That is 42 to 235 times short. Only borrowed audiences close a gap
of that order: placements, recommendations and founder visibility, each Krish's ruling.

| Week of | 16 Nov | 23 Nov | 30 Nov | 7 Dec | 14 Dec | 21 Dec | 28 Dec | Total |
|---|---|---|---|---|---|---|---|---|
| Ladder | 271 | 424 | 636 | 925 | 1,312 | 1,826 | 2,500 | 7,894 |
| Central (measured rates only) | 3.6 | 7.2 | 7.2 | 7.2 | 7.2 | 5.0 | 5.0 | about 42 |
| Stretch (two placements, two recommendation edges, one Live co-stream; every rate an assumption) | 12 | 25 | 25 | 114 | 156 | 31 | 31 | about 393 |

Central assumes 24 Notes a week from the first engine go-live at the mean 45 impressions, and routed
derivatives at about 2,400 exposures and 1.0 per 1,000 (the upper bound for unrouted posts). Holiday weeks
take x0.7. No scenario meets a rung. The 100x claim this plan pre-registers is counted subscribers per
Krish-minute, base week 23 November, read weekly.

## What was built (branch `claude/sharp-knuth-2qb0jp`)

1. **The source clock** (`engine/run/source_clock.py`): every post's own Buffer counts, each Note's free
   subscriptions among them, kept as a `growth-source-clock/1` record each measure run. Checked on the 13
   November readback: the 4 November Note reads 1 free subscription over 208 impressions.
2. **The hook fails closed** (`.claude/hooks/buffer-subscribe-gate.py`): an unreadable call, a broken gate or a
   machine with no Python refuses instead of passing.
3. **One tracked route** (`engine/route.py`): all four UTM tags GA4 credits, `utm_medium=social`, a unique
   `utm_content`; the gate now requires the four, and the go-live path holds a routeless line.
4. **Reconciliation and outcome rows** (`engine/run/reconcile.py`, `engine/run/outcome.py`): every post,
   Buffer-made or native, is checked for a route each measure run; each run ends advanced, nothing_to_do,
   held_below_bar or blocked with its way out.

Stop rule: if these are not merged and running by 23 November, no more code; the 7 December read decides.

## The questions for Krish (answer each by number, as with `sources.json` on 12 November)

0. **Gate 0. Approve the standing W45 to W52 plan, amended:** four Notes a day (Ruling, 11 Nov) and Threads at
   @makeyourmind.up (Ruling, 13 Nov). Your amended version wins (`amended_sha256`).
1. **Plan or target (weekly from Sunday 15 November):** keep 2,500 by 28 December and back borrowed audience
   (questions 3 and 4), or rebase to a number you name?
2. **Pause the 29 October mix until 28 December** (its lanes, its floor of three, its weekly ask), with the
   maker running Notes and quote posts from published pieces?
3. **The lattice:** 3a, a scheduled Codex automation drafting up to 5 one-person asks a day only to people you
   name or that MYMU recommended on merit, you send each; 3b, research up to 10 publications a run; 3c, keep
   the weekly channel audit past W46.
4. **Founder visibility, for one event:** may the engine propose one Substack Live co-stream or guest slot with
   a publication you name, with your face and voice? It is the only lever as large as the gap.
5. **Move the named third parties** in `lists/swaps.md`, `lists/pitches.md` and NOW.md's pitch line out of
   this public repository?

A blanket yes, or a yes on any plan, go-live or check-in, grants none of these.

## The three U5 recovery plays

1. **Warm placements:** a cross-post, guest piece or recommendation with people you name, each read at 72
   hours, landing in buckets `invariants/sources.json` counts as organic.
2. **One founder-visible Substack Live co-stream**, if question 4 is yes.
3. **Your own LinkedIn post for each approved piece**, with the tagged route, by your click.

## Test cards (declared before launch; a card is invalid, not lost, when under 90% of its units are attributable)

| Card | Kill | Graduate |
|---|---|---|
| T0 in-week source clock against Monday's Substack truth | off by more than 2, or 25%, two weeks running | within tolerance two weeks: the clock drives 72-hour calls |
| T1 a tracked route on every unit | 0 counted over 5,000 tagged exposures: change placement once | 3 or more counted over 5,000 |
| T2 four Notes a day | after 40 Notes, under 2,000 impressions and 0 subscribers: drop to 1 a day | 3 or more over 40 Notes; the winning hook family takes half the slots |
| T3 warm placement | 0 accepted of the first 5: question 4 goes to the top | 2 or more accepted: ask for 5 more names |
| T4 the 17,985-view TikTok (read 16 November, beside `direct`) | 2 or fewer: short video stays derivative | 10 or more: content-engine makes a video cut |
| T5 a recommendation edge | 0 in 28 days | 10 or more a week: offer a cross-post |
| T6 a borrowed-audience event (72 hours) | under 1 per 1,000 on 5,000 or more exposures | 4.4 or more per 1,000: seek two more |
| T8 desk throughput | under 3 sends in two weeks | 5 or more sends, press latency 24 hours or less |
| T9 go-live amend and decline rate per hook family | over 30% amended two weeks running: the press rereads the taste ledger | 10% or less: widen hook families |
| T10 ManyChat keyword DM (`keyword-dm`) | its own card, `docs/plans/2026-11-13-keyword-dm-test.md` | same |

Recalibration on Monday 7 December: below Central and no placement yielding means no more building past
Phase B, and the exhibit leads with a rebase proposal and question 4.

## What we stop doing at U5

- The owned-feed meme, positive-news and level-up fan-out and the weekly mix chain (on question 2).
- Building lanes before gate 0 and before measured rates.
- New invariants that protect no counted route.
- Writing third-party names into the public repository.
- Counting `direct` or `email` as wins, and treating volume as a goal.
