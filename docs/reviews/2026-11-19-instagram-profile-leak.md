# Instagram: paid carries the funnel, and the profile has no exit (19 Nov 2026)

Krish shared a 28-day read of @makeyourmind.up on 19 Nov 2026 and asked this engine to act on it as its growth lead:
learn from it, improve the brain, and run the socials in the worker's Chromium. This review checks his read against a
live readback, corrects it where the page disagrees, records what changed, and says what comes next. A number not
shown is unknown, never zero.

## Sources read

| Source | What | Read |
|---|---|---|
| Krish's read, 19 Nov 2026 | 28-day account insights, follower count, his diagnosis and fix order | as given |
| Codex in the worker's Chromium, read only (thread "Make Your Mind Up: Instagram readback, 19 Nov 2026 (read only)") | Profile, bio and link, pins, highlights; 30-day account insights; Insights of all 16 posts published since 26 Oct; Facebook Ad Center promotions | 19 Nov 2026, 07:48 to 08:10 UTC; raw capture in the ignored `.scratch/ig/2026-11-19-readback.json` |
| `docs/reviews/2026-11-16-what-works.md` | Earlier boost reads and organic baselines | 16 Nov 2026 |

Instagram's desktop insights offer 7, 14, 30 and 90 days, not 28, so the account totals below are the 30-day view.

## What the live page agrees with

61 followers, 26 posts, following 3. 30 days: 8,331 views (his 28 days: 8,090), 4,597 viewers (his "accounts reached"
4,412), 251 profile visits (his 248), 2 external link taps (his 2). The 7 Oct launch video has 17 likes. 92.7 in 100
views came from non-followers; 73 in 100 were Reels, 26 in 100 Stories, under 1 in 100 feed posts.

## Where the page corrects the read

**1. "People here do tap through" is mostly paid.** One boosted carousel, "Ten jobs you can hand to AI this week"
(5 Nov, boosted twice, about $59 spent), shows 173 profile visits and 27 follows on its own Insights: 173 of the
account's 251 visits. The boosted "UK number two" Reel adds 1 follow. The 14 unboosted posts in the window earned:

| | Boosted (2 posts) | Unboosted (14 posts) |
|---|---|---|
| Views | 9,226 | 934 |
| Follows | 28 | **0** |
| Saves | 19 | 0 |
| Shares | 4 | 4 (all Claude Duet) |
| Likes | 16 | 26 |

(Post views are lifetime, so the boosted pair exceeds the 30-day account total; Reel profile visits are not shown on
desktop.) The contrast with the dog account's 6 profile visits is a contrast between a paid and an unpaid account,
not proof of organic pull. Organically, @makeyourmind.up reaches about a thousand people a month and gained no
follower from its own posts.

**2. The paid boosts bought follows, not readers.** Ad Center, read the same morning: all five promotions are now
Completed (the "When an AI agent gets a computer" boost spent $0 and reached 0). Substack showed 0 new subscribers in
the boost week (16 Nov read). At about $2 a follow and no subscriber, paid fails this engine's bar, and the North Star
counts zero paid in any case.

**3. The exit was missing, not mis-worded.** The bio already said "Free newsletter for leaders ↓" (16 Nov) and its link
already opens the tagged `/subscribe` page with its UTMs intact. What was missing: no pinned post, no highlight, and
none of the 16 captions named the newsletter (the newest carousel ends "Follow for more" with the link in a comment).
A visitor arriving from a "ten jobs" carousel met series names and nothing that continued what they came for.

## What is right in the read, and stays the plan

- Paid is doing the heavy lifting; if it stops, the account stalls. True, and stronger than stated (above).
- The follow math: at the current rate, organic follows are zero, not 35 a month. Followers are a discovery signal
  here; the number is subscribers (`docs/NORTH_STAR.md`).
- One sharp take per Reel, newsletter as the payoff, the follow reason explicit, the best take pinned. Agreed: the
  organic evidence (lesson `instagram-video-named-thing`) says Reels that open on one named thing are the only
  organic format with reach (unboosted Reel median 106 views, carousel median 23).
- "Use the ads to amplify the Reels that already convert": agreed in principle, but no Reel has converted a
  subscriber yet, so nothing qualifies. No boost is proposed until a Reel brings tagged subscribers organically.

## What changed on 19 Nov (Krish's approvals in this session)

| Change | Result | Approval |
|---|---|---|
| Pin "Ten jobs you can hand to AI this week", "The UK number two" and "Claude Duet messages you first" | Krish pinned them in the app. **Not visible** on the desktop profile: Codex checked the 26-post grid twice after 08:40 UTC and found no pin marker. Unconfirmed until read again | his own |
| Bio: "Daily AI take. Free newsletter ↓" plus the three series lines (link unchanged) | **Saved**, read back word for word after reload | Krish chose option A, word for word |
| Closing line "The full breakdown lands free in the newsletter every Mon, Wed and Fri. Link in bio." on the Claude Duet Reel | **Saved**, read back after reload | Krish, word for word |
| The same line on "Ten jobs" and "The UK number two" | **Held**: Instagram closed the editor on Done and showed the original caption after reload, twice. Both are the boosted posts; promoted posts commonly lock caption edits, which is the likely cause, not confirmed | Krish, word for word |

Before and after of each save are in the ignored `.scratch/ig/2026-11-19-edits.json`. A held edit is never retried by
deleting and reposting (`BROWSER.md`).

## Next, in order

1. **Read the exit in 7 days** (26 Nov): profile visits, link taps and follows from the 7-day view, unboosted only.
   Experiment `ig-profile-follow-reason` sets the bar: 5 taps in 100 organic visits.
2. **Make the take Reel the default organic format** (experiment `ig-one-take-reel`): 20 to 35 seconds, one named
   thing, the take in the first three seconds, the newsletter named as the payoff in the closing line. Content-engine
   produces; this engine briefs, posts and measures.
3. **Turn the Reel into a link** with the keyword DM (`docs/plans/2026-11-13-keyword-dm-test.md`, GET-GOING Step 0.4):
   Reels cannot carry a link, so this is the one mechanic that skips the profile step.
4. **A Start here highlight** with a tagged link sticker (`utm_content=highlight_start`): needs a Story frame from the
   Canva lane and Krish's yes on the frame.
5. **No paid** until a Reel brings tagged subscribers organically; then a boost is a separate test on his Yes.
