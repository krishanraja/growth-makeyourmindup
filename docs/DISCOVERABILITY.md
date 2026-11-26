# makeyourmindup.ai: discoverability by search and AI engines

Krish, 26 November 2026: "make sure that this page is the most discoverable page by search engines and AI engines and hand growth the job of improving that from there over time. Feel free to co-opt the Answers engine for this too."

Growth owns this from 26 November 2026. The site itself lives in the `makeyourmindup` repository and its daily news in content-engine's hub; Growth measures, asks and proposes, and changes a page only through a pull request in the repository that owns it. It moves the North Star through discovery: a reader who finds a desk, an edition or the Creative 24 from a search or an assistant answer, and subscribes.

## What is live (26 November 2026)

- **Pages.** Dated editions at `/edition/YYYY-MM-DD` (the first automatic one is 27 November, 06:00 UTC), six desks (`/music`, `/film-tv`, `/gaming`, `/sport`, `/publishing-media`, `/art-design`), `/creative-24` (a schema.org Dataset), `/editions`. makeyourmindup #57.
- **Discovery files.** `sitemap.xml` (every edition date), `news-sitemap.xml`, `/edition/feed.xml`, `llms.txt` and `llms-full.txt`, and a `robots.txt` that names and allows every AI crawler.
- **The apex redirects to www.** `makeyourmindup.ai` answers 308 to `www.makeyourmindup.ai`, and every canonical, sitemap URL and feed link uses `www`. Keep it that way.
- **Search consoles.** Search Console has held makeyourmindup.ai as a verified Domain property since 25 September 2026, which covers `www`, the apex and `home.makeyourmindup.ai`. Bing Webmaster Tools verified `https://makeyourmindup.ai/` on 10 November 2026, and Control Center's Bing key already reads it. On 19 November Search Console warned of "Page with redirect" and "Duplicate, Google chose different canonical than user" for pages in a submitted sitemap; its indexing report names the pages. Control Center's Search Console service account has no access to the property yet, so its daily read holds no Google rows for the publication.
- **AEO-Engine's six site gates**, checked by hand on 26 November against the live site: `www.makeyourmindup.ai` passes all six (both bot gates, home page 200, server-rendered, one H1, sitemap present). `home.makeyourmindup.ai` is Substack's page and has no H1 on its home page, which Growth cannot change.
- **IndexNow.** The site's `POST /api/indexnow` (guarded by `INDEXNOW_SECRET`) submits the day's edition, the home page and the desks. content-engine #987 calls it right after the 06:00 UTC edition saves. Both secrets were set on Krish's yes on 26 November: one shared value, stored as sensitive in each Vercel project's production environment (`INDEXNOW_SECRET` on makeyourmindup, `MAKEYOURMINDUP_INDEXNOW_SECRET` on content-engine). Each project reads it from its next production deploy. A refused or failed call is logged as `failed` and never stops the edition.

## The weekly reading

`.github/workflows/discoverability.yml` runs `python growth.py run discoverability --deliver` every Monday at 07:41 UTC and reports to Control Center (run id `makeyourmindup:<date>:discoverability`):

| Part | Objective keys | Source | Served today? |
|---|---|---|---|
| Pages submitted | `sitemap_pages` | the live sitemaps | yes |
| Pages in Google, pages in Bing's index | `pages_in_google`, `pages_indexed_bing` | Control Center's search signals | not yet: `docs/briefs/2026-11-26-search-signals-for-growth.md` |
| Impressions and clicks by desk | `search_impressions`, `search_clicks`, by-desk activity line | the same | not yet |
| AI citations by engine | `ai_questions_asked`, `ai_cited_first`, `ai_cited_any`, by-engine activity line | AEO-Engine's research, the directive's `ai_answers` | once AEO asks the publication's questions |
| New subscribers from search, AI and the site | `subscribers_from_search`, `subscribers_from_ai`, `subscribers_from_site` | the directive's `subscribers`, by Substack's own label | yes, when Control Center has read Substack's notices |
| AI assistant visits | `ai_visits` | GA4 source rows in `web_analytics` (the Substack host) | yes |

A part that is not served is unknown with its reason, never zero. The numbers live in Control Center only: this repository is public, so its log says which parts were read and never a number. Read a past week with `GET reports/<run id>`.

## Improving it over time

Each is a proposal to Krish or a pull request in the repository that owns the page. Words on the site go through `check_voice`.

1. **Desk titles and descriptions from real queries.** Once Search Console rows flow, take each desk's top queries by impressions over 28 days. Where a desk is shown for a query its title does not say, propose one new title or description for that desk, one change at a time, and read it again four weeks later.
2. **Internal links from the pieces to the desks.** Each Substack piece on `home.makeyourmindup.ai` that covers a sector links to that desk. A link from a high-traffic piece is the cheapest way to get a desk crawled and ranked.
3. **Earned links to `/creative-24`.** The index is the site's one citable data asset. Offer it, with its method, to writers who cover creative-industry stocks; a draft goes to Krish and nothing is sent without his yes.
4. **`llms.txt` current.** It carries the day's stories from the hub, so it stays current as long as the edition runs. Check it each Monday reads a date in the last two days.
5. **AEO-Engine.** Its research runs fortnightly. Each run audits the publication's hosts and asks the questions Krish approved (`config/ai-answer-questions.json`). Its site fixes are acted on here or in the site repository; a win kit is a strategy ask and needs Krish's yes before a page ships for it.

## Rules

- The site never names Krish, mind/make or CTRL. No badges and no em dashes, British spelling.
- Nothing is sent, published, posted or spent, and no account setting is changed, without Krish's yes for that action. Setting a secret, adding a DNS record, submitting a sitemap and starting a paid AEO run each need it.
