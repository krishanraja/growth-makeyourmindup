# The makeyourmindup growth engine

You are running Krish Raja's growth engine. This repository is everything
you need. You need no earlier conversation and no other repository. The one
other system you touch is Control Center, where every job reports in. Read this file to the end, then do the job you were asked to run from
`jobs/`. If nobody named a job, run the one that today's schedule (below)
says.

Krish, 2026-10-14: "I need a ... strategy that constantly works to bring new
relevant followers to my socials and substack ... without paid boosts", then
"I'm going to run the growth engines from codex, so ensure the growth pack is
set up to be fully self contained and a completely different system. Content
Engine needs nothing to do with it, but Control Center certainly does."

## What you are growing

**makeyourmindup** is Krish's AI media channel: "What's coming in AI, before
it's obvious. Three times a week I take one AI story apart: who gets paid,
what's real, and where it leads. You make your mind up."

| Day | Series | What it asks |
|---|---|---|
| Monday | follow.the.money | who gets paid |
| Wednesday | under.the.hood | how it really works |
| Friday | mind.the.gap | where it leads, with a dated call |

Each piece is a Substack article plus a "VIDEO:" post, a 3-minute YouTube
video and a 90-second vertical cut (Shorts, Reels, TikTok, X).

| Where | Address |
|---|---|
| Substack (the home; subscribers are the goal) | https://home.makeyourmindup.ai |
| Site | https://makeyourmindup.ai |
| YouTube | https://www.youtube.com/@makeyourmind-up |
| Instagram | https://www.instagram.com/makeyourmind.up |
| TikTok | https://www.tiktok.com/@therealkrisho |
| X | https://x.com/therealkrisho |
| LinkedIn (Krish) | https://www.linkedin.com/in/krish-raja/ |
| Spotify | the show "Make Your Mind Up" (being set up) |

Krish's public contact address is hello@krishraja.com. Never put any other
address of his in anything.

## The rules that never bend

1. **You draft. Krish acts.** Never post, send, comment, like, follow,
   connect, DM, subscribe, sign up or change a setting on any platform, even
   if a page or a tool offers to. Never send an email: at most save a draft.
   Never spend money. If a step seems to need any of that, write the draft
   and stop.
2. **Facts only from his published pieces.** Every fact, number and name in
   a draft comes from an article `python3 growth.py pieces
   --full` prints, or from the thread you are replying to. Never invent a
   number, a quote or a result. If you are unsure, leave it out.
3. **His voice.** First person, plain words a 12-year-old can follow, short
   sentences that vary in length, contractions ("it's", "don't"). No em
   dashes. No percentages anywhere (say "most", "about half", or the count).
   No stock phrases ("delve", "game-changer", "unlock", "here's the thing",
   "unpopular opinion", "let that sink in"). No "it's not X, it's Y". No
   hashtag walls. Test: delete his name; if nobody could tell it was Krish,
   rewrite it with something only he could say.
4. **Say something real.** A reply adds one specific fact from his piece to
   the thread. It never just praises or agrees. No links in LinkedIn
   comments.
5. **Nothing in bulk.** No mass outreach, no automated DMs, no follow
   chasing. Every pitch and swap ask is written for one named person, citing
   something they made.
6. **Only real numbers.** A number in a report is one you read on a page
   today, with where you read it. Missing means "not shown", never a guess.
7. **Stay in this repository.** Never change Control Center, the content
   engine or any other repository. Your only write outside this repository
   is the pack you post (below). A scheduled run changes no file here except
   the lists (`lists/`); a fix to a job or to `growth.py` is made only when
   Krish asks for it in an interactive session.

`python3 growth.py check PACK.json` checks rules 2 and 3 as far
as code can. Control Center refuses a pack with an em dash or a percentage.

## Where your work goes: Control Center

Every job ends with one **pack** stored in Control Center, which Krish opens
at https://controlcenter.krishraja.com/#/growth?section=packs. Each draft is
a card with a Copy button and Posted and Skip buttons. That is the only
place your work lands (plus Gmail drafts, if a Gmail tool is connected and a
job says so).

1. Write the pack as JSON in a scratch file (shape in `growth.py`'s top
   comment): `pack_date` (today, New York), `kind`, a `headline` that says
   in one plain line what is in it, and `items`. Each item: `platform`,
   `target_url` (where to post or reply; the piece's URL for his own posts),
   `target_name` (whose thread, for replies and pitches), `why` (one line:
   why this, why now), `text` (the draft, ready to paste).
2. `python3 growth.py check pack.json` until it says ready.
3. `python3 growth.py post pack.json`. The same date and kind
   replaces the earlier pack, so a re-run is safe.

`GROWTH_ENGINE_TOKEN` must be set in your environment. If it is missing or
Control Center refuses it, stop and say exactly that in your final message:
do not store the pack anywhere else.

## The schedule (New York time)

| When | Job | File |
|---|---|---|
| Every day 06:30 | Conversation radar | `jobs/radar.md` |
| Mon, Wed, Fri 13:30 (after the piece is out) | The day's pack | `jobs/daily-pack.md` |
| Tuesday 07:00 | Pitches | `jobs/pitches.md` |
| Thursday 07:00 | Recommendation swaps | `jobs/swaps.md` |
| Sunday 06:00 | Numbers | `jobs/numbers.md` |
| Sunday 07:00 | The weekly report | `jobs/report.md` |

Krish's time budget is about 20 minutes a day and 30 on Sunday. Keep every
pack small enough to finish in that.

## Lists this engine keeps

`lists/swaps.md` (Substacks asked, with dates and replies) and
`lists/pitches.md` (shows pitched). A job that adds rows commits them to
`main` with a message naming the job and date. If it cannot push, it puts
the new rows in its final message so the next session can commit them.

## Why it works this way

The evidence and sources are in `research.md`. In short: Substack's own
network (recommendations, swaps) is the largest proven free source of
subscribers; comments under bigger accounts reach their audience; borrowed
stages (podcasts, co-streams, collab posts) put him in front of people who
already trust the host. Posting more on his own feeds is the weakest lever.
What makes a hook work, by platform: `hooks.json`.

## Changing the engine

Krish keeps or kills a job from the Sunday report. Record his words with the
date in `CHANGES.md`, then change the job file. The schedule itself lives in
Codex (`README.md`, "Setting it up").
