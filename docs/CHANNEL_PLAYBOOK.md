# Channel audit and implementation brief

Prepared 17 October 2026. This is a source-backed action plan and operating
checklist, not a claim that the external surfaces have been changed. Krish
acts on platforms; website and Control Centre changes go to their owners.
A suggested improvement is a hypothesis until measured. Keep published
facts, promise and series consistent across all entries.

## First actions, in order

| Priority | Observed in this audit | Concrete change | Verification |
|---|---|---|---|
| 1 | Substack About reverses the Monday and Wednesday series; website has the correct order | Replace the cadence block with the copy below | Read both pages logged out on mobile; all three days agree |
| 1 | Subscribe entry relies heavily on a brand image and launch-age text | Put a readable reader benefit and cadence next to the email field | Benefit is available as actual text, visible before the primary action |
| 1 | Website's email form exposes no incoming-source handoff | Preserve consented acquisition through the existing subscription route; record completion only from a confirmed event | Start from a tagged external visit, traverse the site, confirm the original source survives; human test required |
| 1 | X pin is from 3 January 2025; recent article links inspected lacked tracking | Refresh pin, align bio and use distinct matched placement links on future drafts | Pin and profile land on the promised current read; tags resolve once |
| 2 | Website calls scoreboard labels its entries as examples | Replace examples only with real dated calls/outcomes from published sources; otherwise label the empty state plainly | Every real row has original call URL/date, due date, outcome evidence and checked date |
| 2 | One of nine recent feed items has no readable body; no explicit article/video pair was verified in the latest public dry run | Read the published video page and document the true links; add bidirectional navigation where appropriate in the publishing system | Both directions reach the right live asset; missing bodies remain blocked until checked |
| 2 | Current dashboard registry does not include the main website's GA property; private channel insights are incomplete | Hand the missing property/source connections to the dashboard owner with availability states | Main site and Substack report their own sources without double-counting; missing data stays null |

The first four public-surface findings were captured during the 17 October
read-only audit. The feed count is from the later public acceptance run on
the same day. Re-read each surface before applying a change; do not assume
an observation remains current forever.

Ready-to-paste cadence block for [Substack About](https://home.makeyourmindup.ai/about):

> Monday: follow.the.money. I follow who gets paid.
> Wednesday: under.the.hood. I look at how it really works.
> Friday: mind.the.gap. I look at where it leads, with a dated call.

Suggested subscribe benefit text, preserving the existing promise:

> What's coming in AI, before it's obvious.
> Three times a week I take one AI story apart: who gets paid, what's real,
> and where it leads. You make your mind up.

Use the existing subscribe control with a clear label such as "Get the next
breakdown". Do not promise free or paid benefits that have not been verified.
Keep policy/consent information readable. The benefit must be accessible
text even when the brand image is hidden.

Suggested X pin structure for Krish to fill from a real published piece:
first-person promise, the actual sourced finding, and one tracked link to
the best relevant start. No unverified audience size, endorsement or
experience. Pick the live source first; do not publish a placeholder.

## Shared quality checks for every surface

- Display name, recognisable handle/avatar, promise and public contact
  `hello@krishraja.com` agree. Banner text remains legible after mobile crop.
- The opening tells a particular reader what they get. Hook, thumbnail,
  title and delivered finding agree. First-person experience has a source.
- One primary next step. Label destination honestly; make topic, format and
  free/paid boundary clear before the click. No fake scarcity or engagement bait.
- Check logged-out and mobile destinations, redirects, query preservation,
  accidental auth walls, dead links, app deep links, private/deleted media
  and fallbacks. A blocked page is an access gap, not proof of a broken link.
- Clean captions, names and numbers; transcript when useful; meaningful alt
  text; contrast, readable subtitle size, safe cropping and a useful first
  frame. Avoid platform watermarks on original re-exports. Growth flags media
  defects to the publishing owner rather than producing a second edit.
- Verify keyboard focus, meaningful labels, tap targets and reduced-motion
  behaviour on owned web surfaces. Keep text readable without images.
- Audit the newest real content and a strong evergreen path. Expired pins,
  inconsistent cadence and an empty "start here" are fix candidates.
- Give each external placement a stable ID and one functional destination.
  Keep native referral codes. Preserve original acquisition through internal
  pages; consent and data minimisation belong in the actual instrumentation.
- Every fix has an owner, exact surface, observed date, evidence, estimated
  effort and a check that can fail. "Posted" alone does not verify a fix.

## Substack: discovery, activation and reader loops

1. Align publication title, subtitle, About, subscribe page and welcome email
   with the three series. Remove contradictory cadence statements.
2. Use accessible benefit text above the email action; check small screens,
   image failures, dark mode and focus. Audit the actual native subscription
   route without submitting a form during read-only checks.
3. Make one start-here choice useful to a new reader. Label series by reader
   question, not merely an unexplained branded name. Link related published
   pieces where the reader naturally wants the next answer.
4. Article and video versions should name and link the corresponding live
   asset. A short answer/summary must remain accurate and be supported by the
   article. Growth suggests it as a fix; editorial ownership remains separate.
5. Welcome: deliver the promised first read and cadence. Ask for one action
   at a time. A later reply can reveal reader needs; a forward/referral ask
   belongs after value, not beside three competing first-day requests.
6. Place a forward line at a useful finding, with a specific intended reader.
   A native forward should preserve the correct landing and author identity.
7. Recommend publications for audience fit, with a precise blurb. Check real
   subscriber yield and retention; no reciprocal obligation or automatic swaps.
8. Verify native referrals and reward fulfilment before proposing a reward.
   Prefer identity/knowledge benefits already deliverable; avoid unapproved
   cost or editorial promises. Keep confirmation and unsubscribe paths clear.
9. Measure actual acquisition, confirmed clicks, useful replies, unsubscribes
   and complete cohorts. Email opens alone are unreliable evidence.
10. Preserve the article sitemap and NewsArticle markup already supplied by
    Substack. Audit actual coverage, canonical URLs and cross-domain links
    before proposing more schema or a competing article archive.

## Main website: the organic discovery and conversion spine

1. Promise, series and primary action should be visible on the first mobile
   screen. Repeat a useful subscribe path after enough value, without hiding
   the article. Check loading, layout movement and form usability on a real
   low-bandwidth/mobile profile when the website owner implements changes.
2. Record initial source before internal navigation changes it. Carry the
   consented source to the existing subscriber route using supported fields
   or a server-side event. Never put email addresses or secrets in URLs.
3. Distinguish form submit, redirect, confirmed subscription and activation.
   A click is not a subscription. Deduplicate completion by actual subscriber
   event where the provider supports it; otherwise report the visibility gap.
4. Add useful topic/series navigation only where published material supports
   it. Candidates are a money map, a theatre/claims index, and a dated calls
   record. These are derivative evidence resources, not thin AI pages or a
   second article pipeline. Do not claim they currently exist.
5. Match the external entry to an article, source list or topic page. Avoid
   sending every interested reader to the same generic homepage.
6. Audit status codes, robots/noindex, canonical tags, sitemap coverage,
   descriptive titles, honest snippets, Open Graph/card images, image sizes,
   author information and mobile rendering. The main-site sitemap inspected
   exposed the homepage; Substack independently exposes article URLs.
7. Do not duplicate full Substack articles under a new canonical without a
   deliberate publishing decision. Link relevant evidence and distinct
   resources instead. Avoid doorway pages and keyword permutations.
8. In Search Console, verify both relevant properties and canonical/indexing
   coverage. Compare query intent and page performance in matching windows.
   Do not invent access or submit changes during this task.
9. For AI answers, write quotable, accurate answers with dated evidence and
   clear attribution where editorially useful. Read AEO results; never run
   the paid engine from here or guarantee citations. The full strategy is
   "Search and AI answers: GEO and AEO" below.
10. Keep the real calls record useful even when a call is wrong: original
    wording, publication date, due date, public outcome, uncertainty and
    correction. Sample data must stay clearly labelled until replaced.

## LinkedIn: authority to a useful read

1. Audit headline, banner crop, About opening and Featured links for the
   promise and current start. Use one relevant destination before a link list.
2. A native post starts with topic and stake, then one useful sourced finding.
   Preview the fold; character targets are house aids, not ranking laws.
3. A useful document outline has an intelligible first slide, one idea per
   page, legible proof and a matched last-page continuation. Accessibility
   text and final PDF/media production stay with the publishing owner.
4. A reply answers the specific thread. No comment links, invented
   familiarity, generic praise or promotional hijacking. Re-read before posting.
5. Use a profile/Featured or post-body link when an external read is the
   intended next step. Do not claim a universal algorithm penalty without
   evidence. Compare qualified visits and subscribers, not reactions alone.
6. Real collaborations can be co-made case studies, conversations or a quote
   asset. Verify permission and context; a drafted tag is not an endorsement.

## X: discussion to a current pin and matched article

1. Refresh the dated pin, check banner/name/bio link and keep the benefit
   legible. Use the best actual start, not necessarily the newest article.
2. Thread opening stands alone. Each post delivers information; the final
   continuation names what the reader gets. Separate posts clearly.
3. URLs use the platform's transformed length. The local checker counts
   URLs and Unicode conservatively; preview joined emoji and unusual URLs.
4. Reply only where a particular fact helps. Track thread age and suppress
   expired candidates. No unrelated tags, hashtag piles or automated DMs.
5. Give pin, bio, thread and partner quote their own placement IDs. Compare
   what was actually posted, clicks, subscriptions and retention where shown.

## YouTube: Short to long, long to owned reader

1. Verify channel About, banner, trailer, home sections and search words.
   Organise actual series into useful playlists; avoid empty or duplicate lists.
2. Shorts need a verified related-video feature/path to a live long video.
   Links in Shorts descriptions/comments are not clickable. Use a native
   continuation and spoken/on-screen identity instead of a false link promise.
3. Long descriptions and captions belong to the publish board; audit the
   tracked destination and flag defects to that owner. Growth adds a pinned
   comment that invites a useful question and a matched continuation.
4. Audit end screens/cards, mobile safe areas, playlist order, caption errors
   and chapter usefulness when available. No feature is assumed enabled.
5. Community questions should uncover a real reader question, with answer
   choices grounded in the piece. A poll is optional, not engagement bait.
6. Diagnose impressions, click-through, watch time, retention, returning
   viewers and subscriber gains using their own units/windows. A Short view
   is not a qualified website visit or a unique person reached.
7. Make public article/video links bidirectional when the publishing owner
   can. Test the exact published asset, not a draft or Studio-only URL.

## Instagram: reach, saved proof, Story conversion

1. Profile name, bio and first link explain the benefit. Audit eligibility,
   the visible ordering of links and the matching landing on a real phone.
2. Pin actual manifesto/start, proof and a useful recent or evergreen piece.
   Highlights can preserve Start, Money, Hood, Gap and Calls if content exists;
   do not create empty shells just to fill a profile.
3. Reels use a legible, supported first-frame idea. Growth flags cropping,
   subtitles and source context to the content owner, then drafts a useful
   native continuation rather than duplicating the Reel caption.
4. Carousels offer saveable proof, not text split arbitrarily. Give the last
   slide one next step. Story frames move from finding to proof to an actual
   link sticker, with its own tracked placement and honest destination.
5. Collab invitations need a relevant named partner, source and consent.
   A proposal does not imply acceptance or shared audience reach.
6. Inspect saves, sends/shares, reach, profile visits and link taps separately.
   Do not attribute all profile-link subscriptions to the newest Reel.

## TikTok: native follow-up before a conditional bio link

1. Audit name, bio, pin relevance, searchable language and current handle.
   Confirm website-link eligibility on this account. Do not promise a link
   that does not appear for a logged-out viewer.
2. Each clip should stand alone with a true finding, captions and a named
   continuation. Numbered series are useful only when the sequence exists.
3. A video reply can answer a real comment; preserve its question and source.
   Growth suggests the distribution opportunity, not a duplicate script.
4. Pin a useful start/proof/series entry from published clips. No irrelevant
   sounds, trends, recycled watermarks, hashtag piles or invented test results.
5. Compare actual views, watch time, completion, profile visits and qualified
   onward visits. Account-level growth is not proof a particular clip caused it.

## Spotify and audio

1. The show was being set up at audit time. Verify the public show and episode
   URLs first. Missing integration is not a zero listener count.
2. Audit show name/description/art crop, episode naming, notes, timestamps,
   transcript and the best-start episode where supported. Existing publish
   captions/descriptions remain with the content engine.
3. A spoken continuation should say the destination plainly and notes should
   lead to the episode's matched article. One ask after value, not a list of
   every social profile. Test links on the native mobile app when authorised.
4. Distinguish starts, plays, followers and retained listeners; define the
   platform's reporting window. Native polls/Q&A/clips are conditional on
   actual account features and workflow ownership, not assumed available.

## Communities, partners and reader propagation

1. Reddit/other communities: read the rules, answer the question in full,
   disclose authorship if linking, and skip promotional contexts. No account
   creation, unsolicited messages or hidden affiliation.
2. Research specific podcasts, guest sessions, newsletters and communities.
   Offer a published finding or source list relevant to their audience.
3. A partner kit includes the exact relevant excerpt, a faithful optional
   quote, matched landing, placement ID and easy choice. No bulk sends or
   implied endorsement. Record permission and actual publication separately.
4. Keep genuine recommendations distinct from paid endorsements or quid pro
   quo. Respect a decline and do not advance a relationship for a draft.
5. A useful reader forward should say who it helps and why. Use native
   referral facilities once verified. No contact scraping or automatic invites.
6. Close the loop in reporting: original acquisition, actual published asset,
   subscription confirmation, welcome/activation, later retention and measured
   effort. Unknown links remain visible; do not manufacture a complete funnel.

## Search and AI answers: GEO and AEO

Added 21 October 2026 at Krish's request for a GEO and AEO strategy, AI
crawler access, favicon and social cards, and a recurring answer piece
that Google and AI assistants can see. This repository has no website: it
drafts, and Krish applies everything below on the hosts himself. Each item
is a check he can run, not a claim that it is already true or already
missing. Re-read the live page before changing it.

Goal: when a leader asks Google or an AI assistant a question that a
makeyourmindup piece answers, the answer cites the piece and the reader
lands on the matched article, then subscribes. That serves the North Star
directly: useful posts, no paid boosts, the right readers.

### One rule above the rest: the same page for everyone

Humans and crawlers get identical content. No cloaking, no text hidden from
readers, no separate page or summary served only to bots, no keyword blocks,
no markup describing anything a reader cannot see on the page. `llms.txt`
and structured data only restate what is already visible. If a change would
only make sense to a machine, do not make it.

### Answer-first structure (every piece, and the weekly answer piece)

1. The title or first subhead is the question in the words a reader uses.
2. The first lines answer it in at most 60 words, so the paragraph can be
   quoted alone and still be right. Names, a date and the finding go there.
3. Then the evidence: each claim next to its source, named and dated.
4. Subheads are the follow-up questions, each answered at its top.
5. The dated call (mind.the.gap) is quoted word for word with its date,
   so a later check can cite it either way.
6. A visible published date and, when edited, an updated date and what
   changed. A correction is stated, not silently overwritten.

`jobs/answer.md` makes one such draft a week from a published piece and a
real reader question; `growth.py check` enforces its shape (question first
line, answer in at most 60 words, link back to the source piece) and its
evidence (the published piece plus the record of the question).

### Where questions come from

Only real ones, each with a record: public comments and replies on the
pieces (Substack, YouTube, LinkedIn, X), the AEO-Engine's list of buyer
questions makeyourmindup is missing from (read in Control Center), Search
Console queries Krish shares, and questions a human verified. Keep the
reader's wording. No invented questions, no keyword permutations, no page
per variant of the same question. A question the published work does not
answer goes to Krish as a topic; the engine does not write the answer.

### What makes a page worth citing

- Something only makeyourmindup has: who gets paid, how it really works,
  a dated call. A summary of other people's news is not that.
- Precise, checkable statements with named sources and dates, close to
  the claim. Counts and plain words, no inflated numbers.
- A stable URL per piece, a clear author (Krish Raja, with an about page
  that says who he is and links his profiles) and the same names
  everywhere: makeyourmindup, the three series, Krish Raja.
- The calls record kept honest, right or wrong, with the original wording.
- Article and video link to each other, so either can be cited and found.

### Host checklist (Krish applies; the engine never changes a host)

The hosts are Substack (`home.makeyourmindup.ai`) and the website
(`makeyourmindup.ai`). Verify each on the live host, logged out, on mobile.

**Crawler access.** Decide per crawler, in `robots.txt` (website) and the
publication's settings (Substack: check what its AI and search settings
actually control on this account before relying on them).
- Search and answer crawlers that cite with a link: `Googlebot`, `Bingbot`
  (Copilot and other assistants draw on Bing's index), `OAI-SearchBot`
  and `ChatGPT-User` (OpenAI), `Claude-SearchBot` and `Claude-User`
  (Anthropic), `PerplexityBot` and `Perplexity-User`, `Applebot`.
  Recommended: allow. Blocking these removes the publication from answers.
- Model-training crawlers and tokens: `GPTBot`, `ClaudeBot`,
  `Google-Extended` (a control token; it does not affect Google Search),
  `Applebot-Extended`, `CCBot`, `meta-externalagent`, `Bytespider`. This is
  Krish's ruling, separate from visibility. Record it in `CHANGES.md`.
- No `noindex` on pieces, the about page, series pages or the calls record.
  Check that a CDN or bot-protection setting is not blocking the allowed
  agents (a firewall challenge is a block even when `robots.txt` allows).
- Sitemaps: Substack's article sitemap exists; the website sitemap should
  list every real page and be named in its `robots.txt`.

**`llms.txt` (website).** A plain Markdown file at
`https://makeyourmindup.ai/llms.txt`: the promise, the three series with
what each asks, the start-here read, the calls record, and the best pieces
with one line each and their canonical Substack URLs. It is a proposed
convention, not something any engine has confirmed it reads: cheap, so do
it, but never claim it raises citations. It must say only what the site
already says. Substack offers no root file control as far as this audit
knows; verify before assuming one way or the other.

**Structured data (JSON-LD, describing only what is visible).**
- Website home: `Organization` (name, url, logo, `sameAs` to Substack,
  YouTube, Instagram, TikTok, X, LinkedIn) and `WebSite`.
- About page: `Person` for Krish Raja (name, url, `sameAs` LinkedIn and X,
  `jobTitle` only as he states it).
- Any article or answer page on the website: `Article` with `headline`,
  `author` (the Person), `datePublished`, `dateModified`, `image` and
  `mainEntityOfPage`; `VideoObject` when the video is embedded;
  `BreadcrumbList` for series pages.
- Substack already emits article markup; audit it, do not duplicate it.
- `FAQPage` only where the visible page really is questions and answers.
  Google shows FAQ rich results only for a small set of authoritative
  sites, so expect no rich result from it.
- Validate with Google's Rich Results Test and the Schema.org validator.

**Favicon and icons.**
- Website: a square icon at a stable, crawlable URL (`/favicon.ico` with
  48 by 48 among its sizes, plus an SVG), `apple-touch-icon` at 180 by
  180, and a web manifest with 192 and 512 icons. Google shows the site
  favicon in results; it must be square and readable at small size.
- Substack: the publication icon in its settings, square and readable at
  small size. The same mark on both hosts.

**Social cards.**
- Every page: `og:title`, `og:description`, `og:url`, `og:type`,
  `og:image` at 1200 by 630 with `og:image:alt`, and
  `twitter:card` set to `summary_large_image`. Titles and descriptions
  match the visible page.
- Substack: set each post's social image and description so the card
  carries the finding, readable without the logo. The card's words are
  real text on the page as well.
- Check with LinkedIn's Post Inspector and a logged-out link preview on X
  and Instagram. Krish runs these previews; the engine never types into a
  compose box.

**Search consoles.** Google Search Console and Bing Webmaster Tools for
both hosts: sitemap submitted, canonical URLs indexed, no coverage errors.

### Measurement: how to tell if AI answers cite it

- **AEO-Engine** (separate repository, fortnightly, read in Control
  Center) is the citation measure: which buyer questions cite
  makeyourmindup in ChatGPT, Claude, Perplexity and Grok. Ask Krish to add
  each answer piece's question to its question set; never run it from here.
- **Referral visits.** In Substack and website analytics, record `visits`
  from `chatgpt.com`, `perplexity.ai`, `claude.ai`, `copilot.microsoft.com`
  and `gemini.google.com` as observations with the referrer in `scope`,
  same windows week to week. Missing or not shown stays null with a reason.
- **Search.** Search Console clicks and impressions for the answer piece's
  question; Google counts AI Overviews inside ordinary web results, so
  they are not separable there. Do not claim they are.
- **Spot checks.** Krish may ask the assistants the week's question by
  hand; a check is recorded with date, engine, question, cited or not, and
  a screenshot kept locally. One check is an anecdote, not a trend.
- A citation is an association with a subscriber, never proof of cause.
  The decision runs through the planned `answer-first-pieces` experiment
  in `experiments.json`, which Krish starts or declines.

## Operating order

Fix clear promise/destination defects first. Establish trustworthy source
measurement next. Then choose one native continuation and one relevant
borrowed-audience test. Review complete windows and subscriber quality
before expanding formats. The nine existing jobs handle this work through
one budgeted queue; this checklist does not add a second publishing calendar.
