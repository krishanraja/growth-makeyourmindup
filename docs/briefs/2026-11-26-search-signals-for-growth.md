# Control Center brief: serve search signals to the publication's growth engine (2026-11-26)

From growth-makeyourmindup, for a Control Center session. This repository changes nothing in Control Center; this brief is the handoff.

**Why.** Krish, 26 November 2026: "make sure that this page is the most discoverable page by search engines and AI engines and hand growth the job of improving that from there over time." Growth now runs a weekly discoverability reading (`engine/run/discoverability.py`, `.github/workflows/discoverability.yml`, Mondays 07:41 UTC). It needs four numbers it cannot read today:

- pages Google shows in search, and pages Bing has indexed;
- Google impressions and clicks by desk (`/music`, `/film-tv`, `/gaming`, `/sport`, `/publishing-media`, `/art-design`, the home page, `/creative-24`, the edition pages, and the pieces on `home.makeyourmindup.ai`).

Control Center already reads all of this every day into `growth_search_signals` and `growth_search_reads` (`api/_searchSignals.ts`, inside the site-visits check at 13:20 UTC), and serves it to AEO-Engine through content-engine's `/api/aeo/context`. It does not serve it to a venture's own growth engine. Until it does, the weekly reading records these parts as unknown with that reason, never zero. The engine keeps no Search Console, Bing or GA4 key of its own (Ruling, Krish, 2026-10-27: through Control Center, never directly).

## The ask

1. **Serve `search_signals` in growth-makeyourmindup's directive**, behind a new `features.search_signals: true`, the way `subscribers` is served (1.32.0):
   - `search_signals: { through, days, rows, reads }` for the publication's hosts (`makeyourmindup.ai`, `www.makeyourmindup.ai`, `home.makeyourmindup.ai`), the last 28 days through the newest day read.
   - `rows`: the `growth_search_signals` rows as they are stored, `{ source, kind, host, page, query, day, day_to, impressions, clicks, position, indexed, last_crawled }`, oldest day first. Page rows (`kind: page`) are enough for the weekly reading; `query_page` rows help the desk-title work later (below). A cap of a few thousand rows is fine; say when it cut.
   - `reads`: the `growth_search_reads` rows for those hosts, `{ source, part, host, ok, reason }`, so the engine can say why a part is unknown.
   - Absent when the store could not be read; an unknown is never a zero. Counts only: no person, no address.
   The engine's reader is already built against exactly this shape (`search_block` and `search_part` in `engine/run/discoverability.py`, tested in `tests/test_run_discoverability.py`), so the change on this side is the flag only.
2. **Search Console access.** makeyourmindup.ai has been a verified Domain property in Search Console since 25 September 2026, and verified in Bing Webmaster Tools since 10 November 2026. Bing already reads: `growth_search_reads` shows its queries, pages and crawl issues read for makeyourmindup.ai on 25 November (no rows yet). Search Console does not: the same table says the property is not shared with the service account `searchConsoleTokens()` uses. Krish adds that account to the property as a restricted user; nothing else on this side changes.
3. **Later, not blocking:** `query_page` rows let Growth test desk titles and descriptions against the queries each desk is actually shown for (docs/DISCOVERABILITY.md, "Improving it over time").

## What the engine does with it

Each Monday it reports, to Control Center only, `pages_in_google`, `pages_indexed_bing`, `search_impressions` and `search_clicks` as objectives, and the by-desk breakdown as activity lines, beside the sitemap count, AI citations by engine and new subscribers from search, AI and the site. Nothing is written to this public repository or its log.
