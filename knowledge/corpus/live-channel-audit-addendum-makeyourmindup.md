# Live Channel Audit Addendum: makeyourmindup

## Direct diagnosis

The core editorial product is considerably stronger than the generic blueprint assumed. The cover already has a differentiated promise—“AI, unpicked”—three named franchises, a public prediction ledger, recent proof assets, a free email form and a multi-channel directory.[^1] The primary constraint is no longer brand invention; it is **conversion continuity and launch-stage distribution**.

The current estate has three distinct surfaces:

- `makeyourmindup.ai`: polished editorial cover, discovery and proof.
- `home.makeyourmindup.ai`: Substack reading, subscription and membership engine.
- Social profiles: discovery surfaces, currently at very different levels of maturity.

The right fix is not to replace the cover with Substack. Keep both, but assign them precise jobs and stop making social visitors infer where to go next.

## What is working

The editorial architecture is excellent:

- **follow.the.money:** who pays and who benefits.
- **under.the.hood:** what is real versus theatre.
- **mind.the.gap:** what disconnected signals mean and what happens next.
- Every piece ends with a dated prediction, confidence level and eventual public score.

This gives makeyourmindup a stronger subscription proposition than “AI news.” The cover metadata promises what is coming before it is obvious, three issues per week, plain language and specific editorial lenses.[^1] Preserve this system.

The live Instagram launch language—“the real deal on what AI is changing in business in the most unboring way possible”—adds useful tonal energy, but “in business” is narrower than the cover and should be either adopted everywhere or removed.[^2] Consistency matters more than choosing either formulation.

## Highest-priority leaks

### The first click is ambiguous

The X and TikTok profiles point to `makeyourmindup.ai`, which is strong for exploration but adds a step before subscription. The cover’s main email form submits to Substack’s `/subscribe` route, while its article cards, channel directory and footer create several competing onward paths.

That is appropriate for homepage visitors, but not for every social campaign. Use three destinations:

| Intent | Destination | Use case |
|---|---|---|
| Subscribe now | `home.makeyourmindup.ai/subscribe` | Bio CTA, profile conversion and explicit subscription asks |
| Read this argument | Matching `home.makeyourmindup.ai/p/...` page | Topic-specific posts, clips and threads |
| Explore the publication | `makeyourmindup.ai` | Press, partners, search, general introductions |

Substack officially supports direct `/subscribe` URLs.[^3] Make the bio link title or surrounding copy describe the outcome: **“Get AI, unpicked—free Monday, Wednesday and Friday.”**

### The cover and Substack promises diverge

The cover description is precise and outcome-led. The Substack metadata is generic: “We follow the money, look under the hood and mind the gap. You make your mind up.” That line is memorable for existing readers but weak for cold social visitors because it does not explicitly say AI, frequency or reader benefit.

Recommended Substack short description:

> **AI, unpicked. Three times a week: who gets paid, what’s real, and what’s coming—plainly explained, every call dated and scored.**

Recommended subscribe benefit line:

> **Get every free issue in your inbox on Monday, Wednesday and Friday. No jargon, no sermons, and every prediction scored in public.**

Substack allows custom plan-benefit messaging on the subscribe page.[^4] This is the highest-leverage copy change because it improves every direct social-to-subscribe visit.

### The editorial schedule conflicts

The cover’s metadata and hero describe three issues per week, but the Substack About copy assigns `under.the.hood` to Monday and `follow.the.money` to Wednesday. The cover navigation shows `follow.the.money` on Monday and `under.the.hood` on Wednesday. This is a small detail with a large trust cost: a new reader cannot form a stable expectation.

Choose one canonical schedule and update:

- Cover navigation.
- Cover hero and metadata.
- Substack About page.
- Welcome email.
- Social bios.
- Series labels inside posts.

Recommended order if the cover reflects the intended product:

- Monday: `follow.the.money`
- Wednesday: `under.the.hood`
- Friday: `mind.the.gap`

### The About page ends weakly

The About page contains the differentiation, but its closing subscription module falls back to the generic phrase “We follow the money, look under the hood and mind the gap.” The page should close the argument with a specific contract.

Recommended closing block:

```markdown
## Make your mind up before the consensus does.

Three free pieces every week:
- Monday: who gets paid.
- Wednesday: what is real and what is theatre.
- Friday: what the signals add up to next.

Every call is dated. Every source is named. Every miss stays public.

**[Send me every issue free]**
```

Substack has reported that About pages are among its highest-converting publication surfaces, making this more than an editorial tidy-up.[^5]

### Social proof is not carried into conversion

The cover shows a strong proof mechanism—the scored public prediction—but the subscribe path does not foreground it. A cold visitor needs immediate proof of method, not merely a publication title.

Place one compact proof strip beside or directly below the subscription ask:

> **Three issues a week · Every source named · Every prediction dated · Every hit and miss scored**

Do not use “hundreds of subscribers” as the main proof while the brand is new. The editorial mechanism is more distinctive and more credible.

### Tracking appears incomplete

The visible cover links do not carry source or content parameters. Without tagged links, direct traffic and multi-step journeys will be difficult to attribute. Substack can send page-view, sign-up and paid-subscription events to GA4 and provides built-in source reporting.[^6][^7]

Create a link registry immediately:

```text
X bio
https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_medium=organic_social&utm_campaign=launch_30d&utm_content=bio

TikTok bio
https://home.makeyourmindup.ai/subscribe?utm_source=tiktok&utm_medium=organic_video&utm_campaign=launch_30d&utm_content=bio

Instagram bio
https://home.makeyourmindup.ai/subscribe?utm_source=instagram&utm_medium=organic_social&utm_campaign=launch_30d&utm_content=bio

Cover hero
https://home.makeyourmindup.ai/subscribe?utm_source=cover&utm_medium=owned_web&utm_campaign=always_on&utm_content=hero_form
```

If Substack’s form redirects strip custom parameters, use campaign-specific redirect paths on the cover, preserve UTMs, and confirm the final signup event in GA4 before scaling distribution.

## Profile audit

### X: @TheRealKrisho

The profile is at launch stage: 16 followers, 174 following, 37 posts and a pinned post from January 2025. Its current bio is strong—“Editor of makeyourmindup. AI, unpicked: who gets paid, what’s real, what’s coming. Every call dated and scored in public, misses included.”—but the pinned asset predates the October 2026 publication launch.

**Change today:**

- Replace the old pinned post with the October manifesto.
- Use a direct, tagged subscribe URL rather than the general cover for at least the 30-day sprint.
- Add the Monday/Wednesday/Friday cadence to the banner image.
- Publish the full argument natively before linking.
- Build Lists for AI labs, retailers/platforms, media/music rights, builders and intended readers.

Recommended pinned post:

```text
AI coverage tells you what happened.

makeyourmindup tells you:
— who gets paid
— what is real and what is theatre
— what the signals say happens next

Three free pieces a week. Every call dated and scored in public, misses included.

Start here: [tagged subscribe link]
```

The current profile’s following-to-follower ratio is not a growth defect by itself, but it signals that the account needs a public reply and relationship programme rather than more outbound links. X recommendations use follows, Topics, Lists, replies, reposts and network activity as signals.[^8] Build topical presence through useful replies before expecting 37 posts to create meaningful distribution.

Use zero to two hashtags, not the current habit of three broad tags such as `#meta #Siri #ai`; X itself recommends no more than two.[^9] Prefer no hashtag unless joining a genuine live topic.

### TikTok: @therealkrisho

The profile has one follower, follows four accounts and has two videos. The bio is aligned: “AI, unpicked. Who gets paid, what’s real, what’s coming. makeyourmindup.ai.” This is an account-seeding problem, not an optimisation-at-scale problem.

**Change today:**

- Set the display name to `Krish Raja | AI, unpicked` for search clarity.
- Make the link destination the tagged direct subscribe page if the account has link access; otherwise use the memorable cover domain and make the subscribe action unmistakable on the cover.
- Pin three videos as soon as available: the manifesto, the strongest `under.the.hood` teardown and the sharpest `follow.the.money` story.
- Follow a curated starting graph of 30–50 relevant sources and audience accounts over time, not through automated bursts.
- Publish 10–14 clips in the next seven days so the account has enough inventory to reveal topic and hook patterns.

TikTok Creator Search Insights exposes frequent searches, content gaps and search analytics.[^10] Translate each franchise into search-led questions:

- “Who gets paid when AI makes music?”
- “What is Meta Muse actually?”
- “Is Higgsfield real or hype?”
- “Why did Amazon block Meta’s AI?”

TikTok says watch time and early attention matter, relevant hashtags help categorise the video, and adding more hashtags or `#FYP` does not guarantee reach.[^11] Use a spoken exact question in the opening, the same question on-screen, a natural-language caption and 2–4 precise tags.

### Instagram: @makeyourmind.up

Public search confirms the launch framing but the platform’s public page could not be fully audited without login.[^2] Use the following implementation checklist against the live profile:

- Name field: `makeyourmindup.ai | AI explained`.
- Bio: `Who gets paid. What’s real. What’s coming. Free Mon/Wed/Fri ↓`.
- Primary link: tagged direct subscribe URL titled `Get every free issue`.
- Highlights: `Start`, `Money`, `Real/Theatre`, `Predictions`, `About`.
- Pins: launch manifesto, strongest carousel, best Reel.

Instagram advises original Reels, strong opening seconds, searchable keywords in the profile and captions, and Collabs for shared audience distribution.[^12][^13] Do not treat the platform as a mirror of TikTok: pair each Reel with a publication-native carousel that explains the entire argument and ends with a specific subscription reason.

## Content-to-subscribe bridge

The current X post language—“Read in full at…”—describes format, not benefit. Replace it with the missing value.

### Meta Muse example

Current pattern:

> “Let’s explore what’s under the hood? Read in full…”

Better:

> **Meta’s Muse looks like a chatbot. It is actually a third category of AI—and Amazon and Walmart have already picked opposite sides. The full teardown scores Muse against Siri on six things and explains who this model threatens. Get it free:** [matching article]

### Suno example

> **Warner sued Suno. Now Warner takes a cut. The important question is not whether AI music survives—it is who gets paid each time a fan generates a song. The full money trail is free:** [matching article]

### Video outro

> **That is the headline. The free written piece follows the money, names every source and makes a dated prediction. Get it at makeyourmindup.ai.**

For YouTube Shorts, pasted URLs in Shorts descriptions and comments are not clickable; use the channel’s first profile link and a related long-form video.[^14] Say “first link on the channel,” not “link below,” unless the platform makes that route clickable.

## Revised 30-day priorities

### Days 1–2: Repair continuity

- Reconcile the franchise schedule everywhere.
- Rewrite Substack short description and subscribe benefits.
- Replace X pinned post.
- Install tagged links by source and placement.
- Verify GA4 signup events end to end.
- Rework About-page closing CTA.
- Confirm Instagram profile against the checklist.

### Days 3–7: Seed inventory

- Publish one definitive piece in each franchise.
- Create three distinct short-video hooks per piece.
- Publish at least 10 TikToks, 7 Reels, 7 Shorts, 15–25 X posts/replies and 15–25 Substack Notes.
- Pin the three best orientation assets on each available platform.
- Record profile visit, click and subscription yield by asset.

### Days 8–14: Find the wedge

- Identify which franchise produces the highest subscriptions per 1,000 impressions.
- Produce three sequels around the winning reader question.
- Build one collaboration around a current story with an existing warm relationship.
- Turn on and curate Substack Recommendations.
- Add a referral reward only if fulfilment is ready.

### Days 15–21: Create an event

- Publish a definitive reference asset: “The AI Money Map,” “The Real/Theatre Index” or “The 2027 Prediction Ledger.”
- Launch it with a live briefing, partner contribution or public scoring event.
- Give every platform a native argument and direct subscription path.
- Ask existing readers to refer one person at the moment the asset delivers value.

### Days 22–30: Concentrate

- Stop the bottom third of formats by subscriber yield.
- Double the output around the winning franchise, topic and hook.
- Release the first scorecard showing which calls held, broke or remain unclear.
- Introduce paid perks only after stating a concrete utility beyond support.

## Paid conversion

The current About page says every written piece is free in full. That is a powerful free-growth promise, but it means paid cannot later be framed as ordinary article access without breaking the contract.

Use a **free editorial / paid utility** model:

- Free: every written issue, audio edition and public prediction score.
- Paid: source dossiers, data tables, comparison matrices, decision templates, monthly live “make your mind up” briefing and searchable prediction database.
- Founding: small-group editorial council or quarterly private briefing.

Substack recommends that new publications can keep most material free while enabling paid, and it frames paid value around ongoing access to the creator’s worldview rather than one isolated post.[^15][^16] Do not launch paid because the payment switch exists. Launch when there is one completed member asset, one scheduled live benefit and a visible 90-day benefit calendar.

## Exact priority order

1. **Fix the schedule contradiction.**
2. **Change the Substack description and subscribe benefit copy.**
3. **Replace X’s obsolete pinned post.**
4. **Install tracked, source-specific conversion links.**
5. **Seed TikTok from two videos to enough inventory to learn.**
6. **Turn each social CTA from “read in full” into a named reader benefit.**
7. **Use Notes and Recommendations as distribution channels, not merely Substack features.**
8. **Create one referenceable launch event rather than relying on routine cadence to produce 10,000 subscribers.**

The brand foundation does not need reinventing. The next gains come from making the same sharp editorial contract survive every transition: **feed → profile → click → subscribe → first issue → habit → referral → paid utility.**

---

## References

1. [makeyourmindup: AI, unpicked](https://www.makeyourmindup.ai/) - We follow the money, look under the hood and mind the gap. You make your mind up. A free publication...

2. [makeyourmindup.ai (@makeyourmind.up)](https://www.instagram.com/makeyourmind.up/) - Hello my friends. Welcome to my new channel where I give you the real deal on what AI is changing in...

3. [How do readers subscribe to my Substack publication?](https://support.substack.com/hc/en-us/articles/360037830631-How-do-readers-subscribe-to-my-Substack-publication) - To link readers straight to it, add /subscribe to the end of your. This also works if you use a cust...

4. [Can I customize my subscription benefits?](https://support.substack.com/hc/en-us/articles/360042017071-Can-I-customize-my-subscription-benefits) - You can customize the messaging for each subscription plan so your readers can get a better understa...

5. [Subscription platform - Get started on Substack](https://on.substack.com/p/going-paid-checklist) - Get our PDF download covering how to turn on paid subscriptions

6. [How do I connect Google Analytics 4 to my Substack publication?](https://support.substack.com/hc/en-us/articles/15955098199444-How-do-I-connect-Google-Analytics-4-to-my-Substack-publication) - Connecting Google Analytics to Substack allows you to track page views, sign ups, and paid subscript...

7. [Where can I see how readers got to my Substack post?](https://support.substack.com/hc/en-us/articles/4415094770964-Where-can-I-see-how-readers-got-to-my-Substack-post) - When logged into your Substack account, head to your Posts tab and click on the post you want to see...

8. [About our approach to recommendations](https://help.x.com/en/rules-and-policies/recommendations)

9. [How to use hashtags](https://help.x.com/en/using-x/how-to-use-hashtags) - Get an overview on hashtags, including best practice tips.

10. [Creator Search Insights - TikTok Support](https://support.tiktok.com/en/using-tiktok/growing-your-audience/creator-search-insights) - With Creator Search Insights, you can browse topics that are frequently searched for on TikTok and d...

11. [5 tips for TikTok creators](https://newsroom.tiktok.com/en-us/5-tips-for-tiktok-creators) - Hashtags: Add hashtags to your captions that are relevant to your videos so they're more likely to b...

12. [Instagram for Creators: Frequently Asked Questions](https://creators.instagram.com/faq) - Trending hashtags that are relevant to the topics in your reel can help you reach more people, who a...

13. [Tips for Improving Your Reach | Instagram for Creators](https://creators.instagram.com/blog/tips-for-improving-your-reach) - Keep your reels short. ✅ Post original content, avoid reposted content. As we recommend more content...

14. [Sharing links with your audiences - YouTube Help](https://support.google.com/youtube/answer/13748639?hl=en) - Creators can share links with their audiences on YouTube, but only certain kinds of links are clicka...

15. [When should I turn on paid subscriptions? - Substack](https://on.substack.com/p/turn-on-paid) - At Substack, we believe that writing is inherently valuable. We make it easy to earn money for your ...

16. [Going paid guide - Substack](https://substack.com/going-paid-guide) - If you’re writing on Substack and considering adding paid subscriptions, this guide will help you de...

