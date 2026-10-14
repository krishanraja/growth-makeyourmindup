# The playbook: the operating system, applied to makeyourmindup

Source: `knowledge/10k-operating-system.md`, as Krish gave it on 14 October
2026. Where his own rules change it, see `knowledge/README.md`. Every job
reads this file before it starts.

## The one idea

"Do not try to post your way to 10,000. Engineer a 30-day media event in
which every channel, collaborator, reader and content asset feeds one owned
destination." The owned destination is the Substack:
https://home.makeyourmindup.ai. A follower elsewhere is not a subscriber.
Every draft ends in a reason to subscribe there.

The equation that decides where effort goes:

    net subscribers = qualified reach x visit rate x subscribe rate
                      + native subscriptions + referrals - people who leave

Judge every source and every asset by the **subscribers it brings**, never
by reach alone. Subscriber yield = subscribers it brought, per 1,000 people
reached.

## The seven engines, and which job runs each

| Engine | What it means here | Job |
|---|---|---|
| 1. A precise promise | "What's coming in AI, before it's obvious." Every page and profile must say who it is for, what it does each week, why it's different, and why subscribe rather than follow | `conversion` (weekly audit), `report` |
| 2. A signature franchise | The three series: follow.the.money, under.the.hood, mind.the.gap, and the dated calls. Each piece has a forwardable unit: a named finding, a chart, a call | `daily-pack` finds it and builds every draft around it |
| 3. A conversion spine | Four doors: welcome page, about/manifesto, start-here pack, the day's piece. Substack is the first link on every profile. Every link is tracked | `conversion` |
| 4. Substack-native distribution | Recommendations (three circles: peers, category leaders, adjacent bridges). Notes are **off** by Krish's choice | `swaps` |
| 5. Borrowed distribution | Podcasts, guest posts, co-streams, collab posts, communities: the 100-account partner map and the ask ladder | `pitches`, `partners`, `radar` |
| 6. Constructed word of mouth | Forward prompts at the most useful moment, Substack referrals with identity rewards, reader status | `conversion` drafts the settings and the copy; `daily-pack` adds forward lines |
| 7. A measurement loop | Daily numbers by source; weekly kill, keep, scale | `numbers` (daily), `report` (Sunday) |

## Each channel's job (from the document's channel table)

| Channel | Job | What the engine drafts | Where the subscribe path goes |
|---|---|---|---|
| Substack | Owning the reader | Recommendation asks; welcome, about and email copy fixes; forward lines | Native subscribe |
| LinkedIn | Professional authority | 3 to 5 native posts a week: tension in the first two lines, the finding, 3 to 5 useful points, what to do, a matched ask. One document post a week. 10 comments a workday through the radar | Featured section: the welcome page and start-here pack; link in the post body, never in comments |
| X | Ideas and discussion | A thread on publishing days (hook, stakes, evidence, framework, use, open loop, specific subscribe line). 5 to 10 replies a day through the radar | Bio link and the last post of each thread |
| YouTube | Search and lasting trust | Long description with the tracked link in the first lines, pinned comment, one community post per piece | Links in Shorts descriptions and comments are not clickable: Shorts say the name "makeyourmindup" aloud and on screen, and link the related long video |
| Instagram | Trust, saves and shares | Reel caption with search words, a carousel's slide text, a Story sequence (tension, insight, proof, link sticker), collab post invitations | Story link sticker, first bio link, pinned posts |
| TikTok | Reach | Caption, the on-screen hook (3 to 7 words), one spoken closing line that names makeyourmindup | Bio link to the matched page |
| Spotify | Habit | Show notes with the matched link, a clip caption under 90 seconds, the "best place to start" pick | Spoken ask and the show-note link |

The **publish board** (in the content engine, outside this repository)
already gives Krish the captions and descriptions he needs to post the
videos. Don't redo those. This engine adds what makes people move: the
pinned comment, the Story sequence, community posts, threads, partner kits,
replies and asks.

## Every tracked link

Every link in a draft that points at makeyourmindup carries:

    ?utm_source=<platform>&utm_medium=organic&utm_campaign=growth&utm_content=<job>-<YYYYMMDD>

Build it with `python3 growth.py link <url> <platform> <job>`.
`growth.py check` refuses a draft with an untracked makeyourmindup link.

## The hooks and the asks

- **Hook families:** prediction, contrarian claim, new evidence, avoidable
  loss, audience identity, confession, specific utility, narrative scene,
  curiosity gap, public challenge. Rotate them; the report says which family
  brought subscribers. Hooks by platform are in `hooks.json`.
- **The ask ladder, by how warm the reader is:**
  - cold: save it, watch part two, read the free breakdown;
  - curious: get the full finding or source list;
  - warm: subscribe for the next piece;
  - an engaged free reader: forward it to one person;
  - a subscriber: refer one sharp person.

  Match the ask to the reader, and change it often rather than repeating one
  line.
- **Forward prompts** sit at the most useful moment ("Know someone deciding
  this? Send them this one.").

## The breakout score (every published piece, in the report)

Score the piece 0 to 2 on each: novel, useful, identity-rich, specific,
timely, credible, works across formats, tense enough to discuss, ownable as
a franchise, naturally leads to subscribing. Report the total out of 20 and
the weakest two. A piece under 15 should not carry a big push. The report
tells Krish which kinds of piece score high, as input to his planning.

## Kill, keep, scale (the report applies these every Sunday)

- High reach, few visits: rewrite the hook and the ask, or stop.
- Many visits, few subscribers: fix the promise or the page (conversion).
- Strong conversion, little reach: put more distribution behind it.
- Brings subscribers again and again: make it a franchise.
- Volume with people leaving fast: protect quality and reduce that source.

Decision points from the document, counted from the day the engine started
(day 1 is the first pack in Control Center):

| Day | The question |
|---|---|
| 3 | Is the promise understood, and are visitors subscribing? Which hook and channel show a signal? |
| 7 | Which asset brought the most subscribers per 1,000 reached? Move at least half of the discretionary effort to the top two engines |
| 14 | Are recommendations compounding? Are enough collaborations booked? If not, more co-made assets and direct partner asks, not more posting |
| 21 | Which free benefits cause sharing? What becomes a permanent franchise? |
| 30 | Net and active subscribers, repeatable engines, recurring partners, the honest next-60-day path |

## What a pack must never become

- A generic link hub, or the same post pasted on every platform.
- Hashtag stuffing, or tagging big accounts that had nothing to do with it.
- Followers counted as subscribers, or views counted as success.
- A claim that any of this "cannot fail".
