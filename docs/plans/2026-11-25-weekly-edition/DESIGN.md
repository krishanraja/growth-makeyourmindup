# The weekly edition: how makeyourmindup reaches its readers (design, 25 Nov 2026)

Status: **approved by Krish on 25 Nov 2026** ("Yes take all recommendations - but Claude now in charge of Buffer
scheduling not Codex"). His answers and the one change are in [`DECISIONS.md`](DECISIONS.md); the build is in
[`IMPLEMENTATION.md`](IMPLEMENTATION.md). Nothing here is sent until he presses Approve for send on an edition.

The brief (Drive, Ventures/Temp, "2026-11-25 makeyourmindup channels and distribution"), in Krish's words of 25 Nov 2026:
"nobody cares enough to receive 3 deep dives a week, valuable though they are. We should figure out how to deliver an
overarching newsletter with the 3 deep dives of the week, and then all the rest of the things a reader needs to know that
has happened recently."

**North Star.** This moves this repository's number (new subscribers a week from organic posts and shares, zero paid,
U5) through the two levers the reviews found: keeping the readers we already have (more leave than join) and giving
every reader one email worth forwarding. It changes no goal, audience, channel or format without Krish's decision.

## The design in one paragraph

Subscribers get **one email a week: the weekly edition, every Saturday at 08:00 New York (13:00 London).** It carries
the week's three pieces (a plain summary, one picture and a link each), then six to ten short news items from the
creative industries, each checked against its primary source and grouped by topic, then one line asking the reader to
pass it on. The Monday, Wednesday and Friday pieces keep their days and go live on the web and in the Substack app
**without an email**. A reader who wants every piece as it lands switches that on with one click. Every other channel
keeps its order and now points to one promise: the Saturday edition, through the one tagged subscribe route. The
pipeline drafts the edition by Friday evening, Krish presses Approve once, and the post is scheduled, sent and read back
without him.

## Why: what the evidence says

| Finding | Source |
|---|---|
| 497 subscribers on 16 Nov, 26 fewer than 90 days before: about 33 joined and about 59 left. 254 of the accounts were imported, not earned. | `docs/reviews/2026-11-16-where-subscribers-come-from.md`, findings 1 and 2 |
| The 30-day open rate is 21.6% on three sends a week. | same, finding 1 |
| Three emails a week went out from 2 to 13 Nov (one Substack Video post per piece). **Nothing has been published since Fri 13 Nov**: the last twelve days are silent. Before November the rhythm was irregular, and some pieces sent two emails (a "VIDEO:" post and the article). | the publication's public archive, read 25 Nov 2026 |
| 23 of 27 new accounts in 90 days already had a Substack account: new readers come from inside Substack. | `where-subscribers-come-from.md`, finding 3 |
| A written Substack Note brought the only organic subscriber of the month; not one of 139 posts carried a subscribe ask. | `docs/reviews/2026-11-16-what-works.md`, lessons 2 and 5 |
| The in-article subscribe ask (C6) and the "forward to one colleague" ask (D5, C9) are briefed and not built. | `docs/reviews/2026-11-16-fix-list.md` |
| The first lever of 17 Nov is pointing Krish's own audiences at the tagged subscribe link. | `docs/reviews/2026-11-17-reorientation.md`, lever 1 |
| content-engine's Saturday good-news run already finds five stories a week, each checked against its primary source; its beat config narrows every feed to the creative industries. | content-engine `docs/CADENCE.md`, `config/good-news.json`, `config/beat.json` |

*Inference, not proven:* three emails a week to a list that is half imported, opened by about one in five, is what
Krish named: more than readers want. Unsubscribes by date have not been read, so the link between frequency and churn
is unproven; the next weekly read takes it (Assumption A1 below).

## 1. What readers receive

| Reader | What lands | When (New York) | Where |
|---|---|---|---|
| Every subscriber | **The weekly edition** | Saturday 08:00 | Email, the web, the Substack app |
| A reader who opts in to "every piece" | Each piece as its own email | Monday, Wednesday, Friday, when the piece goes live (about 12:30) | Email |
| Everyone | Each piece | Monday, Wednesday, Friday | The web and the Substack app, no email |

- The pieces keep their days, their links and their pages. Only the email moves.
- How, in Substack's own terms (section 11): each piece is published with "Send via email and Substack app inbox"
  unticked. The opt-in is a section that starts empty ("Add new subscribers by default" and "Copy your email list" both
  off), which readers switch on in their email preferences; each piece then emails only that section, either published
  into it or sent with "Only send to a specific audience segment". Which of the two is a build detail, chosen when the
  first piece is tested.
- **Not yet verified:** Substack documents the web-only box for posts and podcasts, not for Video posts, and every piece
  is a Video post. Before any piece relies on it, a draft Video post's publish screen is read for the box and for the
  segment option (nothing published). If neither exists, Krish decides between a text post with the video embedded and
  keeping the Video post's email.
- The edition is itself a post: it has a web page, a link Notes and social can point at, and its own comments.
- Sunday stays rest: nothing publishes on a Sunday (Ruling, Krish, 2026-11-02).
- A week with no live piece sends no edition: it holds and asks Krish. A week with one or two pieces sends with what went
  live.

## 2. The edition, section by section

The order follows the example Krish shared (the ultrathink newsletter of 25 Nov 2026). The structure is taken; the voice
and the look are not.

| # | The example's section | makeyourmindup's section | What it holds | Size |
|---|---|---|---|---|
| 1 | A short personal opener | **Opener** | Two to four plain sentences on what the week was about, in the publication's "we". Unsigned: makeyourmindup never names Krish (v5 rules, 25 Nov). | up to 60 words |
| 2 | "What else we've got for you today" | **In this edition** | One line per piece, then one "Also" line naming the news topics. | 4 lines |
| 3 | Named sections for each deep piece | **The three pieces**, one section each | A plain label (the day and its question: "Monday: who gets paid"), the piece's own approved title, a summary of 50 to 80 words that says the facts plainly and leaves the landing for the piece, its approved cover picture, and two links: read the full piece, watch the 5-minute video. | about 250 words |
| 4 | "More stories to catch up on", by topic | **Also this week** | Six to ten items, at most two a subsector, under the hub's subsector heads, the rooms of makeyourmindup.ai (today Music; Film & TV; Gaming; Sport; Publishing & Media; Art & Design, as content-engine `config/hub-sources.json` lists them; 26 Nov 2026, section 3), plus a "Good news" group of up to three from the good-news run. Each item is one or two sentences, with its primary source linked. | about 400 words |
| 5 | A job board | **Pass it on** (replaces the job board) | One sentence asking the reader to forward the edition to one person in their industry, and a tagged subscribe link for whoever receives it. makeyourmindup has no job board; this is the fix list's D5 and C9, built. Substack's referral link can sit under it if Krish switches the referral setting on (D5 already asks). | 2 lines |
| 6 | A closing line and footer | **Close** | One closing line, then Substack's own footer (email preferences and unsubscribe). | 1 line |

The whole edition reads in about five minutes (700 to 1,000 words). Every line passes Control Center's `check_voice`
(channel `substack`): no em dashes, no exclamation marks, British spelling, and Krish's copy rule of 25 Nov: "Copy like
that which is vague and smart arse needs to be banned." Every line makes sense read aloud, names the real thing and uses
no insider shorthand (approved taste, voice lane).

**The look.** The edition uses the v5 Library's `newsletter-weekly-edition` template (content-engine, branch
`look/v5-library-system`, `docs/ve/cards/library/`) once Krish approves the Library; until then the dry run uses the
structure only. No new look is drawn here. One constraint the Library needs to know: a Substack email is assembled in
Substack's own editor (text, headings, pictures, post cards, buttons, dividers), and Substack documents no way to send
custom HTML (section 11). So the template reaches the inbox through three things: the email header picture
(`newsletter-substack-email-header`, set once in Substack's email settings), each piece's cover picture
(`newsletter-substack-cover-wide`, or Substack's own large post card, which shows it) and the publication's theme.
Template details that are styling only (the coloured rules between sections, Anton headings, mono labels) could reach an
email only as pictures, which many inboxes block and screen readers cannot read; this design keeps every headline and
sentence as real text. The template has slots for exactly five news items; the edition needs up to ten, in topic
groups, and a "Pass it on" line. Both are written here and flagged to the Library session.

## 3. "Everything a reader needs to know": what qualifies, where it comes from, how it is checked

**What qualifies.** An item goes in when all of these hold:

1. It happened in the seven days to Friday 12:00 New York.
2. It sits in one of the hub's subsectors (content-engine `config/hub-sources.json`), never on the beat's avoid list
   (`config/beat.json`: governance, regulation, security, privacy and enterprise productivity with no creative angle).
3. It names one concrete thing: a company, a deal, a number, a product or a person (fix list C3).
4. A reader in those industries would decide, buy, say or do something differently for knowing it.
5. It is not one of the week's three pieces.

**Where it comes from**, in this order:

1. The week's daily hub editions: content-engine's hub pipeline writes one snapshot a day (`hub_snapshots`, the items
   makeyourmindup.ai shows), already gathered, placed in a subsector, de-duplicated with its coverage count and checked
   against the report it came from. The edition reads them and runs no gathering of its own (26 Nov 2026, below).
2. The Saturday good-news run: its five stories, checked against their primary sources, feed the "Good news" group.
3. The ideas the Sunday run found and Krish filed "for later" or "trend" on the ideas board.
4. Anything Krish drops in the Cold Ideas and Inspo folder that week.

**How each item is checked.** Every item carries its primary source: the company's own announcement, the filing, the
court record, the dataset, or the official statement, never only an article about it. The item's sentences are checked
against that source's text; every number is quoted exactly, with its unit and date. An item whose primary source cannot
be found or does not say what the item says is dropped, never softened. This is the good-news run's rule, applied to
every item. A hub item's address is the report the hub's writer read, usually a trade title, so it is where the search
for the primary source starts, never the source itself.

**26 Nov 2026, the news comes from the hub.** Krish approved makeyourmindup.ai as a daily creative-industry news hub
that day ("just keep it focused on the subsectors"), and the coordinating session asked, through the story-engine
session, that the edition read a week of the hub's rows instead of gathering its own. So the candidates are the hub's,
the heads are the hub's subsectors (which brings in Sport, one of its rooms) and an edition carries at most two items a
subsector; the checks above do not change.

**Who drafts it.** content-engine, which produces and drafts: a weekly edition run (Claude Code inside GitHub Actions on
Krish's subscription, like the Sunday ideas run), which gathers, checks, writes and renders the edition. growth does not
write it ("Growth adds no article", `specs/standing-plan.json`).

## 4. Automation: who does what, and where Krish presses

| When (New York) | Step | Owner | Runs on | Krish |
|---|---|---|---|---|
| Mon, Wed, Fri, about 12:30 | The day's piece goes live on Substack, **web only** (and to the "every piece" readers, if chosen). | content-engine's publish kit says how; the publishing route is unchanged | Krish's existing Monday "Approve for publish" press, then the route he uses today | unchanged |
| Fri 13:00, again 19:00 | **Draft the edition**: read the three live pieces from their records, gather and check the news, write, run the voice check and the kill list, render the preview, and put the edition on the Saturday card of the week's board with the hash of its exact words. The second run does nothing if the first finished. | content-engine | GitHub Actions (cron fires twice because GitHub's schedule runs late), Claude Code on his subscription | none |
| Fri evening | **Build the Substack draft** from that package, draft only; send Substack's test email to Krish; read the draft back and record its link and hash on the card. | growth | Codex on the worker, in its signed-in Chromium (Ruling, Krish, 2026-11-16) | none |
| By Sat 07:30 | **One press: Approve for send**, on the Saturday card in Control Center's Content tab, bound to the hash. It also shows on his one list. | Control Center | | **one press** |
| Sat 07:30 | **Schedule** the post for 08:00 with email on ("Schedule time to email and publish"), only if his press matches the hash; read back that it is scheduled. Substack schedules in the scheduling device's time zone, so the worker's browser time is converted and the scheduled time is read back in New York time. No press, or a changed edition: nothing is scheduled and the card says why. | growth | Codex on the worker | none |
| Sat 08:00 | Substack sends. | Substack | | none |
| Sat 08:30 | **Read back**: the post is live and the email went; tick the board. | growth | Codex on the worker | none |
| Sat, after his Note sign-off | **Schedule the Saturday Note** that points to the edition, and any social post that points to it, in Buffer (Buffer's Substack channel posts Notes only). | growth | Claude, through Buffer (Ruling, Krish, 2026-11-25) | signs the Note, as every Note today |
| Mon 06:15 | **Measure**: the weekly Substack read adds the edition's numbers and confirms each piece sent no email. | growth | the existing "Growth: subscribers" job | none |

Zero Claude routines (Ruling, Krish, 2026-10-29): every timed step is a GitHub Actions schedule or one of growth's
existing Codex automations; nothing runs on a claude.ai schedule.

**What stops a send.** No press, no send. An edition whose words changed after his press holds. A news item that fails
its source check is dropped; the edition still goes with at least four items. If Codex finds Substack signed out or its
editor changed, the card says so and links the prepared draft, and Krish can press Publish there himself.

**His time.** Reading the edition and one press, about five minutes on a Friday evening or Saturday morning.

## 5. Every other channel

**The standing order stays**: Substack, YouTube, YouTube Shorts, TikTok and Instagram Reels for every piece, then
LinkedIn and Spotify when he wants them (content-engine `docs/AMPLIFICATION.md`, "The order"). No channel is added or
removed. What changes:

1. **The promise.** Every caption and description that ends "Get the next one in your inbox:" says instead what the
   reader gets and when (draft: "Get the week's pieces and the news that matters, in one email every Saturday:"), still
   followed by the one tagged route, `https://home.makeyourmindup.ai/subscribe` (Ruling, Krish, 2026-11-12). The spoken
   close of a script is unchanged (house rule SCRIPT_CLOSE).
2. **The edition's own links are tagged**: a new source in `specs/subscribe-route.json`, `utm_source=newsletter`,
   `utm_medium=email`, `utm_campaign=weekly`, and `utm_content=edition-<YYYY-MM-DD>-<place>` (`forward`, `piece-mon`,
   and so on), so a subscriber who arrives from a forwarded edition is credited to it.
3. **A Saturday Note** points at the edition: Notes are the one format that has converted. content-engine makes it with
   its other Notes (Ruling, Krish, 2026-11-26: all asset production is content-engine's); Krish signs it, as he signs
   every Note today (`docs/PUBLISHING-AUTHORITY.md`), and once signed Claude schedules it in Buffer.
4. **The promise everywhere a reader decides to subscribe**: Substack's publication description ("Three short reads a
   week for leaders...") and welcome email, and the site's description ("Free, every Monday, Wednesday and Friday",
   makeyourmindup `apps/cover/content/site.json`) say what the reader now gets. The v5 rebrand session owns the new
   Substack copy and the new site; this design hands it the promise line.
5. **What runs on its own after his approval**: the edition's schedule and read-back in Substack's editor (Codex on the
   worker, the Substack step only), and every Buffer post, which Claude now schedules (Ruling, Krish, 2026-11-25:
   "Claude now in charge of Buffer scheduling not Codex"). Buffer's Substack channel posts Notes only, never newsletter
   posts (Buffer Help Centre, "Using Substack with Buffer"). Notes and series posts still sign post by post.

## 6. Measurement

Read the way this engine already reads: the weekly Substack read on Monday (`jobs/subscribers.md`), counts only,
judged by subscribers through the tagged route.

- **The North Star does not change**: new subscribers a week from organic posts and shares.
- **The edition, each week**: recipients; click rate (unique clicks over recipients), read first, because Substack's
  open rate is noisy (Apple Mail loads pictures, app readers now count, and email opens from France and Italy stopped
  counting on 14 Oct 2026); open rate; clicks into each piece; unsubscribes from that email; new subscribers
  Substack credits to the edition post; subscribers through `utm_source=newsletter`.
- **The pieces, each week**: web views in their first seven days, and a check that each sent no email (recipients 0
  outside the "every piece" readers). A piece that emailed everyone is a failure in the Sunday report.
- **Baselines to read before edition one**: the 21.6% open rate is known; unsubscribes a week, clicks per send and a
  piece's web views in its first week are not read yet.
- **Bars, after four editions** (proposed; Krish sets them): open rate above 35%; unsubscribes a week below the
  three-send baseline; clicks into the three pieces from the edition at least the clicks they had from their own
  emails; at least one subscriber a week through a forwarded edition.

## 7. What stops, and how it stays stopped

| Stops | Kept from coming back by |
|---|---|
| One email per piece to every subscriber | content-engine's publish kit says "web only" for the Substack step and its self-test fails on "send to everyone"; a growth invariant and test say a series post's Substack step never emails the whole list; the Monday read flags any piece that did. |
| "Three times a week" and "every Monday, Wednesday and Friday" as the promise | the copy check on the site and the Substack kit copy refuses those phrases on a promise line; the v5 Substack copy carries the new line. |
| "Get the next one in your inbox:" | the publish kit's self-test checks the new promise line. |

Nothing else stops: Notes, social posts, comments, swaps and the off-day lane carry on as they are.

## 8. Moving the current subscribers over

1. Everyone moves to the weekly edition: it is the main list's email.
2. Edition one says what changed in two plain sentences near the top, with a one-click way to get every piece by email
   as well (if Krish chooses that option), and a link to email preferences.
3. New subscribers hear the same promise on the subscribe page, in the welcome email and on the site.
4. Edition one follows at least twelve silent days, so its subject line is the week's strongest story, not the change.
   Substack's own guidance is the reason for a fixed day: "Readers open more when they know when to expect you. Long
   gaps between posts, or suddenly posting more often, can lower your open rate." (HC 55092108035220, 22 Nov 2026)
5. The "still want this?" email to imported subscribers who have not opened in 60 days stays a separate decision.

## 9. Considered and not recommended

- **Keep three emails and add the weekly**: four emails a week, the opposite of the brief.
- **Move the list to another platform** (the example is sent with beehiiv): 85% of new readers come from inside
  Substack, and a move is a channel change.
- **A Sunday edition**: Sunday is rest.
- **A Monday edition**: it summarises the week before, a week late, and lands on Monday's piece.
- **Sending without a press**: against the approval wall.

## 10. Assumptions this rests on

| # | Belief | Confidence | Evidence | Flips when |
|---|---|---|---|---|
| A1 | Part of the churn is frequency. | medium | Krish's read; 21.6% opens; more leave than join | unsubscribe dates show the churn began before three sends a week; then the re-permission email matters more than the edition |
| A2 | Saturday morning suits this reader. | low to medium | weekly roundups are read at leisure; Sunday is ruled out | after four editions the click rate is under 4%: test Friday 16:00 New York for four |
| A3 | Pieces without their own email are still read, through the edition, the app and social. | medium | the edition links each piece; a web-only post skips the app inbox but stays on the publication's page in the app (section 11) | a piece's first-week web views fall by more than half for three weeks running |
| A4 | Codex can build and schedule a Substack post reliably. | medium | it already reads the Substack dashboard each week | two failed schedules: Krish presses Publish on the prepared draft himself |

## 11. What Substack can and cannot do (verified from Substack's own documentation)

Read on 25 Nov 2026 from Substack's Help Centre (support.substack.com, through its public article API, because the
pages refuse plain fetches) and on.substack.com. "HC n" is `https://support.substack.com/hc/en-us/articles/n`; the date
is the article's last edit. **Re-read** means this session read the article text itself; **checked** means a research
pass read it and this session did not re-read it.

| What the design needs | Status | What Substack documents | Source |
|---|---|---|---|
| Publish a post to the web without emailing | **Verified, re-read** | Posts email by default; to only publish, untick "Send via email and Substack app inbox" after clicking Publish. A web-only post skips the app inbox but still shows on the publication's page in the app (checked). An emailed post cannot be resent. | HC 360037831771 (19 Nov 2026) |
| **Publish a Video post to the web without emailing** | **Not verified** | The video guide says only: adjust the publishing settings, then "Send to &lt;audience&gt; now". No web-only option for video posts is documented. Every piece is a Video post today, so this is tested on a draft before anything relies on it (DECISIONS.md, question 1). | HC 21093671091220 (29 Oct 2026) |
| Email a post to part of the list only | **Verified, re-read** | Publish settings, Advanced, "Only send to a specific audience segment": the post stays visible to everyone and only the segment gets the email or app notice. | HC 52113249525140 (6 Aug 2026) |
| Sections, and readers choosing their emails | **Verified, re-read** | A section is a separate newsletter. "Add new subscribers by default" off means new subscribers must opt in; "Copy your email list" off means current subscribers are not added. A section post emails only that section's subscribers. Readers switch each section on or off in their settings or through the unsubscribe link (checked). | HC 360060687771 (12 Nov 2026); HC 8914938285204 (checked) |
| Scheduling | **Verified, re-read** | "Schedule time to email and publish", up to three months ahead, in the time zone of the device that schedules it, on the web only; it covers articles, podcasts and video posts. Notes can be scheduled since 8 Apr 2026 (checked). | HC 360037870412 (13 May 2026); on.substack.com, 8 Apr 2026 (checked) |
| An official API | **Verified, checked** | The Developer API covers public profile and publication data only (name, total subscribers, rankings). Substack's MCP server reads stats for Bestseller publications and cannot publish or post Notes. **No way to publish or schedule by API is documented**, so publishing stays a browser step. | substack.com/api-tos (8 Jan 2026); HC 50834026608916 (5 Jul 2026) |
| Notes | **Verified, checked** | Short public posts in the Home feed and on profiles; no email per Note (readers may get a Notes digest); a Note can share a post; Notes can be scheduled; no Notes API. | HC 14564821756308; HC 14742669797396 |
| Building a roundup email | **Verified, checked** | Pasting a post's link embeds a card for it (small, medium, large or plain link), own posts included; share, subscribe and custom buttons; pictures; saved post templates (April 2026). The email header and footer are set once for free readers and once for paid readers. No automatic digest of a publication's own posts exists, so the edition is built. A way to send custom HTML is not documented. | HC 4406444950804; HC 360056142311; on.substack.com, 8 Apr 2026 |
| Referrals and recommendations | **Verified, checked** | "Enable subscriber referral program" adds a referral link to emails, with rewards counted in new free subscribers and a public leaderboard. Recommendations show after sign-up, in the sidebar and in Substack's digests. | HC 16142857300372 (28 Jun 2026); HC 5036794583828 (29 Oct 2026) |
| Deliverability and cadence | **Verified, re-read** | "Readers open more when they know when to expect you. Long gaps between posts, or suddenly posting more often, can lower your open rate." Gmail's Promotions tab is a common landing spot; Apple Mail's privacy feature inflates opens; open rate now counts app readers (checked) and stops counting email opens from France and Italy on posts sent after 14 Oct 2026 (checked). | HC 55092108035220 (22 Nov 2026) |
| Emailing part of the list, and inactive readers | **Verified, checked** | A targeted email goes to a filtered or saved segment (activity rating, opens in the last 30 days, sign-up date, country, section), can be scheduled, and has no web post. A filtered set can be removed. "Prune inactive subscribers" exists only for some publications. | HC 19163529016212 (25 Aug 2026); HC 52113249525140; HC 360058529871 |

**What this changes in the design.** The pieces stop emailing everyone with the web-only box, or, for a reader who opts
in, with a section or a segment-only send; scheduling and publishing are a browser step because no publishing API
exists; the edition shows each piece through Substack's own post card or the piece's cover picture; the referral link
can carry "Pass it on"; and because open rates are noisy (Apple Mail, app readers, France and Italy), clicks are the
number the edition is judged on first.

## 12. What each repository changes (the plan follows Krish's decisions)

| Repository | Owns | Changes |
|---|---|---|
| content-engine | production and drafting | the weekly edition run and its record on the board; the news gathering and source check; the render through the v5 template; the publish kit's Substack step (web only) and promise line; `docs/AMPLIFICATION.md` and `docs/CADENCE.md` |
| growth-makeyourmindup | distribution and measurement | `utm_source=newsletter` in `specs/subscribe-route.json`; a job that builds, schedules and reads back the Substack post on the worker; the edition's go-live in the release path; the edition's numbers and the no-email check in the weekly read; the invariant; this design |
| makeyourmindup | the site and the subscribe page | the promise line on the cover and in the Substack kit copy |
| control-center | the board and his list | the Saturday card and its one press, if the board needs a new card kind |
