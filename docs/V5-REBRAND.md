# makeyourmindup v5: what changed, what it means for Growth (26 Nov 2026)

Written by the v5 rebrand session for this engine, at Krish's request on 26 Nov 2026: "ensure growth-makeyourmindup drives this session ... it has been upgraded with 100% of your and your sessions work". Read this before any Make Your Mind Up work. Where an older section of `AGENTS.md`, `docs/ACCOUNT-VOICE.md` or a plan says otherwise about the look, the copy or who makes what, this file wins until that section is rewritten.

## Why it exists, why these industries, what makes it different

(approved by Krish, 27 Nov 2026)

- **Why it exists:** "makeyourmindup exists so the people who make the work, and the businesses around them, use AI rather than get used by it: what it lets them make, earn and express, and who gets paid."
- **Why the creative industries:** "These industries run on creativity, and AI is changing how creative work makes money: who gets paid, what it costs, who wins the market. Our AI Music breakdown showed how much these readers want that explained."
- **What makes it different:** "We don't hand you a verdict. Every piece climbs five whys from one story to how the money moves, so you make your own mind up. Positive about what AI lets makers do, honest about who gets paid."

## 1. The look is locked: v5 only

Krish locked full look v5 on 25 Nov 2026 ("s3h is great, lock v5") and asked that everything before it be "unable to be accidentally used". Everything older is retired.

**Tokens:**

| Token | Value |
|---|---|
| ink | `#0C1512` |
| ink-deep | `#070D0B` |
| cream | `#F4EFE4` |
| mint (the one accent, "mint is the answer") | `#7EF0C0` |

- Coral, butter and lilac code a climb only.
- The day colours (yellow, purple, red) and the day pills are retired.

**Type:**
- Anton for cover headlines, one face per headline: no split headlines.
- Fraunces for headlines on the site and the share cards.
- Archivo for structure and video captions.
- DM Mono for labels and data. It replaces IBM Plex Mono, which is retired.
- The v5 fonts (Anton, Archivo, Fraunces upright and italic, DM Mono regular and medium) are in content-engine `assets/fonts/makeyourmindup/`; the IBMPlexMono files in that folder are retired. Growth's old render kit (its fonts, brand PNGs and `render/KIT.md`) is deleted from this repository, and a guard keeps it from coming back (R132).

**Marks:** content-engine `assets/brand/makeyourmindup/v5/`:

| File | What it is |
|---|---|
| `d-face-off.svg` | The icon. Favicons, the Substack logo. |
| `v4.svg` | The wordmark, on ink only. |
| `v9.svg` | The horizontal lockup, on ink only (mastheads, email banner). |
| `s3h.svg` | The square lockup with the icon as the O. Every profile picture, and the one wordmark on every video outro. |

Retired, though the files are still in the folder: `v10.svg`, `v6.svg` and every `-ink` variant (the on-light versions).

**Retired, never to be used again:**
- every id in content-engine `config/retired-styles.json`;
- makeyourmindup `apps/cover/substack-kit/images/`: the old wordmark PNGs, the email banner and the gift-box logo;
- the Mindmake splashes avatar;
- the YouTube watermark (v5: no watermark).

**Reference renders:**
- https://www.makeyourmindup.ai/opengraph-image is the approved share card.
- https://www.makeyourmindup.ai/icon.png is the icon.

**Rules on every surface:**
- One wordmark per item.
- No em dashes.
- No badges.

## 2. What the publication is now

- **Promise:** "AI news for the creative industries, every morning." Motto: "Creativity, AI and money, simplified." Both are live on the site and on every share card.
- **The Edition:** a daily news hub at makeyourmindup.ai, published 06:00 UTC by content-engine's hub pipeline. It covers six subsector desks (including Sport, which Krish approved) and the Creative 24 market board of delayed closes, never faked as live.
  - Archive API: `GET /api/hub/today?date=` and `?archive=1`.
  - The first automatic edition is 27 Nov 2026.
- **Series names:** Krish, 26 Nov: "it should just read like a curated news feed, the sub brands do not need to feature". So follow.the.money, under.the.hood and mind.the.gap don't appear on new surfaces. Neither does the Mon/Wed/Fri promise or "AI, unpicked".
- **The signature piece format is the 5 Whys** (Ruling, Krish, 2026-11-24). Nothing suggests predictions, calls, dates, odds or scores.

## 3. Names (unchanged, with one exception)

- makeyourmindup never names Krish, mind/make, Mindmake or CTRL, and never says "AI Brain".
- **The only exception (Krish, 26 Nov):** the Saturday email's signed footnote and his own handwritten opener. It is signed "Krish" with his signature, headshot and krishraja.com, and one line that links mindmake.co.
- His headshot and signature files are private. Never commit them or copy them into a shared folder.

## 4. Who makes what (Krish, 26 Nov)

- **content-engine makes every asset:**
  - pieces, covers, thumbnails, carousels, memes, Notes images and copy, captions (written into the piece manifest), derived cuts and the weekly edition's render;
  - its v5 Library (`docs/ve/cards/library/`) is the one template source, merged as content-engine #984;
  - covers go only through `scripts/covers/make_covers.py`.
- **Growth grows the channel:** posting, Buffer scheduling, distribution, the subscribe route, the Substack editor step for the edition, measurement, experiments, channel strategy, discoverability (`docs/DISCOVERABILITY.md`) and the social profiles.
- **Canva is retired:** "Canva is crap so we don't use that anymore".

## 5. The Saturday edition (Substack)

- **The email:** Substack-native, with real text and real links. The only images are the photos and the sign-off, each with alt text, so a reader who blocks images still gets every word.
  - Content-engine's Library template (`newsletter-weekly-edition`, local branch `library/weekly-edition-content`, status "proposed") renders the same content as an image for review.
- **Audience:** Krish, 26 Nov: "substack weekly should be sent to ALL subscribers". Every edition goes to everyone, free and paid.
- **Nothing sends** until the Substack branding is v5. Krish, 26 Nov: "send nothing until all this is done".
- **Edition one** is draft 226648035. One test went to his own address.
- **Substack branding:** the email banner becomes the v5 masthead and is the one masthead on every email. The edition body carries none.
- **Still open, Krish's call:** the publication name "makeyourmind/up" and the sender name "makeyourmindup" don't match.

## 6. The site (makeyourmindup.ai)

All live since 26 Nov:
- The Edition, with dated edition pages, the six desks, `/creative-24`, `/editions`, sitemaps and a news sitemap, the Edition RSS feed, `llms-full.txt`, JSON-LD and IndexNow after each edition (makeyourmindup #57, content-engine #987).
- A moving ticker of all 24 constituents.
- Scroll motion with a reduced-motion fallback.
- Generated v5 share cards on every page (makeyourmindup #59).

The site's discoverability is this engine's job (`docs/DISCOVERABILITY.md`).

## 7. In flight for Growth

- **Social profiles to v5:** YouTube `@makeyourmind-up`, Instagram `@makeyourmind.up`, the Facebook Page, Substack, and the header and bio on Krish's own X and TikTok. A worker session runs it from this repository.
  - The v5 profile set is final. It is in Drive, `makeyourmindup > 1 Brand kit (permanent) > Channel art` (folder id `1FVfcoSMT3DCzvyvsq0KHdSgr8JTzRBIe`), and in makeyourmindup `brand-kit/makeyourmindup-brand-kit.zip` under `Channel art/`, with the exact profile copy in `bios-and-descriptions.txt`. content-engine's `scripts/channel-kit/` is retired. A worker session uploads the set.
  - Record what each profile carries in content-engine `docs/AMPLIFICATION.md` ("The profiles every link lands on") and here.
- **ManyChat:** the keyword-DM test (`docs/plans/2026-11-13-keyword-dm-test.md`, `docs/GET-GOING.md` Step 0.4).
  - Rule 5 and R07 still bind: one DM reply to someone who commented the keyword on that post, nothing else.
  - The DM words quote the article's "3 things you can do tomorrow" section (content-engine rule 11, still enforced). Check them against the v5 piece and get Krish's approval of the exact words before any flow goes live.
  - State (27 Nov 2026): the keyword flow is kept as Draft and nothing is live. The trial ended on 27 Nov; staying on Pro is spend and waits on Krish's yes.
- **Old-look copy and assets in this repository** to rewrite or retire when touched:
  - the Mon/Wed/Fri and series lines in channel copy;
  - "AI, unpicked" bios.

## 8. Where things are

- **Rebrand handovers:** the v5 notes folder for these sessions (Krish's machine):
  - `mymu-v5-library-guardrails-handover.md`;
  - `mymu-discoverability-handover.md`;
  - `mymu-social-rebrand-worker-prompt.md`.
- **Distribution notes:** `distribution-weekly-edition.md`.
- **content-engine:**
  - `config/retired-styles.json`;
  - `config/floor-rulings.json` (the v5 rulings in his words);
  - `docs/ve/cards/library/`;
  - `assets/brand/makeyourmindup/v5/`.
