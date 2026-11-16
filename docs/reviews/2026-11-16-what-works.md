# What works on Make Your Mind Up's channels, and why (16 Nov 2026)

Krish asked on 16 Nov 2026 for an analysis of every Make Your Mind Up post through Buffer, ingested into the
learnings: what works and why, with paid boosts kept apart from organic. This follows
`docs/reviews/2026-11-15-interest-vs-paid.md` and covers the whole run, 139 posts from 5 Oct to 14 Nov.
Everything here was read, not changed. A number not shown is unknown, never zero.

## Sources read

| Source | What | Window | Read |
|---|---|---|---|
| Buffer `list_posts`, sent, with metrics (read only) | 139 posts: Instagram 30, YouTube 23, Facebook 20, X 17, Threads 16, TikTok 14, LinkedIn 11 (history only, growth-mindmake's since 13 Nov), Substack Notes 8 | 5 Oct to 14 Nov 2026 | 16 Nov 2026 08:57 UTC; metrics lag up to a day |
| `growth.py run paid audit` on that read | per-channel organic medians, suspected paid, organic breakouts | same | 16 Nov 2026 |
| Codex, read only, in a thread Krish can see | Meta Ads Manager, TikTok Promote, YouTube Studio, X Ads, Substack subscribers by source | 1 Oct to 16 Nov | **Not read.** Codex reported "The browser access host is unavailable", so no ads manager and no Substack page was opened |

Paid is therefore still suspected, never confirmed. The raw read stays in the ignored `.scratch/buffer/`.

## The one finding that matters most: reach is the constraint, not polish

| Week of | Posts | Organic exposures | Interactions |
|---|---|---|---|
| 5 Oct | 20 | 1,876 | 77 |
| 12 Oct | 18 | 1,355 | 32 |
| 19 Oct | 9 | 657 | 10 |
| 26 Oct | 10 | 201 | 0 |
| 2 Nov | 28 | 2,395 | 46 |
| 9 Nov | 50 | 3,696 | 64 |

The suspected paid posts are left out. Posting 2.5 times as often (20 to 50 a week) did not even double the organic
exposure, and interactions fell from about 4 a post to about 1. The organic median exposure per post is 2 on
Facebook, 4 on Substack Notes, 5 on Threads, 7 on X and 13 on YouTube. Only TikTok (about 280, because its feed
shows posts to people who do not follow the account) and Instagram (about 58) reach anyone at all.

**Why:** the accounts have almost no audience yet, and cross-posting the same asset into near-empty feeds adds posts,
not readers. More of the same will not move the number. Borrowed audiences will: comments on bigger accounts,
recommendation swaps, Notes conversations and collaborations. That is where this week's effort goes.

## What earns genuine interest, and why

**1. Instagram video is the best organic format.** Median exposure is 116 for a video, against 25 for a carousel and
23 for a single image, and Instagram videos earned 9 of the run's 10 organic shares. The videos people stay with
(average watch per view):

| Post (first line) | Date | Watch | Signal |
|---|---|---|---|
| In the belly of the $1B beast: Higgsfield | 8 Oct | 44.6 s | 111 interactions per 1,000 |
| Google paid $2.7 billion for the founders. Disney is paying for the rest | 9 Nov | 39.7 s | |
| The UK number two you've been dancing to started as an AI demo | 11 Nov | 28.5 s | 211 views, 4 shares |
| Imagine waiting forty minutes for a refund you never asked for | 3 Nov | 24.9 s | 160 views |
| Claude Duet messages you first | 4 Nov | 13.9 s | 124 interactions per 1,000 (pooled channel rate 33), 4 shares |

**Why:** each opens on one named, concrete thing (a product, a deal, a song, a refund), then follows the money or a
surprise. The reader recognises it or could use it today. Abstract framing ("Every AI has two passports") holds
people for less time (17.5 s) and earns no shares.

**2. Substack Notes converts, but only as a written Note.** The only subscriber Buffer shows in the whole run came
from one Note: "The interesting bit of Claude Duet is who starts the work" (4 Nov, plain text, an opinion about a
product people can use). It reached 208 against a Notes median of 4, with 8 interactions. The six image cross-posts
on Notes reached a median of 4 and brought none.

**Why:** Notes sits inside Substack, one tap from Subscribe, and Substack spreads Notes that start conversations. A
pasted image post is not a conversation.

**3. TikTok gives a steady floor of about 280 views, but short-video attention is low** (median watch 2.5 to 7 s). The
best interest per view came from workplace absurdity: "Meta and Amazon ranked staff by how much AI they used" (40
per 1,000, against a channel rate of 7). The carousel "AI is going back over old work and catching what we missed"
held 21.2 s, the longest on TikTok.

**4. Threads, X, Facebook and YouTube earn almost nothing unpaid.** On Threads, carousels (median 35) beat videos (5).
On YouTube one Short broke out organically: the Disney and Character.AI money story (9 Nov, 266 views, 15 per 1,000,
24 times the median). Same pattern as Instagram: who got paid, named.

**5. Not one of the 139 posts carried a subscribe ask.** This was already found on 13 Nov (`intensity.json`,
`conversion`). It is still true of everything sent up to 14 Nov.

**6. LinkedIn, history only.** It had the highest interest per view of any channel (85 to 105 per 1,000 on clips, a
thank-you text post 260 impressions). It is growth-mindmake's since 13 Nov and is recorded here only as history.

## Reach without interest: suspected paid, still unconfirmed

| Post | Channel | Reach | Times the organic median | Interactions per 1,000 (channel rate) |
|---|---|---|---|---|
| The UK number two (11 Nov) | YouTube | 5,974 | 543 | 0 (4.2) |
| The UK number two (11 Nov) | TikTok | 17,991 | 65 | 1.0 (7.2) |
| When an AI agent gets a computer (13 Nov) | Facebook | 16,252 | 8,126 | 5.4, with 5 shares and 13 clicks |
| When an AI agent gets a computer (13 Nov) | YouTube | 1,363 | 124 | 3.7 (4.2) |

The Facebook post's reach rose from 8,984 on 15 Nov to 16,252 on 16 Nov, which looks like a boost still running. No
boost is recorded in this repository, and none brought a subscriber that Buffer can see. The paid audit's
`boosts_recorded` and `zero_paid_line` checks stay fail and unknown until Codex reads the ads managers.

## Do more, stop

Do more:
1. Instagram video that opens on one named, concrete AI thing, then the money or the surprise.
2. A written Substack Note a day: an opinion about something a reader can use, never a pasted image.
3. Borrowed audiences: comments on bigger accounts, Notes conversations, recommendation swaps.
4. A tagged subscribe route on every post (the U4 and U5 rule already says so; the posts did not carry it).

Stop or cut:
1. Pasting image cross-posts into Substack Notes.
2. Videos on Threads and X: Threads carousels did better; X has no audience yet.
3. Counting more posts as progress: week 9 Nov had 50 posts and about one interaction each.

## Boost candidates, on the bar Krish approved (16 Nov)

Krish ruled on 16 Nov 2026 to boost the top performers this week as a test. Each boost needs his Yes on its amount,
it is reported apart and it never counts in the organic number. The bar (from the 15 Nov review): organic, at least
twice its channel's interactions per 1,000 at 72 hours, and at least one share.

- **Passes:** Instagram, "Claude Duet messages you first" (4 Nov): 124 per 1,000 against the channel's 33, 4 shares.
- **Near miss:** Instagram, "The UK number two" (11 Nov): 52 per 1,000 (twice the rate would be 65), 4 shares, 28.5 s
  watch. It needs his explicit Yes as an exception.
- Nothing else passes. The Claude Duet Note cannot be boosted (Notes has no ads platform).

A boost cannot be placed or read until Codex can reach the browser.

## Confirmed later on 16 Nov: what the boosts bought

Read by Codex in the worker's Chromium (`BROWSER.md`, "The worker's Chromium"), read only, with each number checked by
Claude against Codex's screenshots. Recorded as `msr-paid-boost-tiktok-2026-11-11`, `msr-paid-boost-youtube-2026-11-12`
and `msr-substack-new-subscribers-2026-11-09` in `engines/records/measurement.jsonl`.

| Boost | Spend | What it bought | Subscribers |
|---|---|---|---|
| TikTok Promote, "The UK number two" (order 11 Nov, completed) | $24 | 16,090 views, 1 new follower, 38 profile views, 14 likes; 0.6 in 100 watched the whole video, all "below average" | none visible |
| YouTube promotion of the 5:02 "A Reiki master wrote a UK number two" video (12 to 17 Nov, still running, £20 budget) | £13.90 so far | 7,061 impressions, 2,936 views, 364 clicks to home.makeyourmindup.ai | 0 new in Substack, 9 to 15 Nov |

- **Substack, week of 9 Nov: 0 new subscribers** ("No subscribers found for selected time period"). Week of 2 Nov: 1, from
  Notes. 497 subscribers in total on 16 Nov.
- The 13 Nov YouTube Shorts were **not** promoted: "Your AI agent, without the setup" took 95.8 in 100 of its views from
  the Shorts feed. The audit's suspicion on them was wrong; their reach was YouTube's own feed.
- Facebook's 13 Nov reach (16,252) is still unexplained: Meta and X were signed out in the worker's Chromium.

**Verdict on the boosts so far:** about £33 bought roughly 19,000 paid views, 364 clicks to the home page and one follower,
and no subscriber. Neither boosted post passes the boost bar above. Krish stopped the YouTube promotion on 16 Nov ("Yes, stop it"): Codex paused it on the worker
and the saved page reads Paused, at £13.90 of £20 (final: 7,070 impressions, 2,941 views, 366 visits).

## Meta and X, read later on 16 Nov

The worker's Chromium is signed in (Facebook as Krish Raja with Makeyourmind/up among his Pages; X as @TheRealKrisho).
The earlier "Log in to Ads Manager" page was the wrong door: Ads Manager's own link opens Heartside's ad account. The
Page's Ad Centre lists five boosts, all of Instagram posts, created by makeyourmind.up (checked against its pages):

| Boost | Window | Spent | Results |
|---|---|---|---|
| "When an AI agent gets a computer" | 14 to 20 Nov, **active** | $0.00 of $18 | reached 0 accounts |
| "The UK number two" | from 11 Nov | $32.72 of $36 | 3,561 views, 3,247 reach, 409 link clicks |
| "Ten jobs you can hand to AI" | from 11 Nov | $29.73 of $30 | 2,013 views, 1,666 reach, 71 profile visits |
| "Ten jobs you can hand to AI" | from 5 Nov | $29.39 of $30 | 3,160 views, 2,642 reach, 98 profile visits |
| "New AI model release day" | 21 to 25 Oct | $3.84 (Codex's read) of $20 | 82 views, 181 reach, 13 link clicks, 9 landing page views |

X Ads: $0.00 and 0 impressions from 1 Oct to 16 Nov. The Facebook post of 13 Nov (reach 16,252) was not boosted; its
reach is Facebook's own distribution, still unexplained.

**All paid since October:** about $119.68 on Meta and TikTok and £13.90 on YouTube. In return: 27,847 paid views,
409 + 366 + 13 clicks, 169 profile visits and one TikTok follower. Substack shows one new subscriber in the whole
period (2 to 8 Nov, from Notes, organic) and none in the boost week. Paid reach has not bought a reader yet.
