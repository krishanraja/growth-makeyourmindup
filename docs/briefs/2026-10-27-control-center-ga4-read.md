# Brief for Control Center: a bounded GA4 read for the makeyourmindup growth engine

From the growth-makeyourmindup engine, 27 October 2026. Krish: "You have Google Analytics installed already and Control Centre can see that. Make sure this is a part of your Measurement Specialist." This repository changes nothing in Control Center (AGENTS rule 7); this brief asks for a route. Use it only if Control Center does not already give this engine the data below through its directive.

## What exists (read live, 27 Oct)

- GA4 property **G-VC5V9LDE17** is installed on the Substack publication home.makeyourmindup.ai through Substack's native integration. Substack says that integration tracks page views, sign-ups and paid subscriptions (faq.substack.com, "Using Advertising Analytics on Substack"). The exact event names are not yet confirmed.
- Every own link the engine posts carries `utm_source` (the platform), `utm_medium`, `utm_campaign`, and `utm_content` set to a stable placement identity for that post (`engine/core.py`, `tracked`). Joining GA4 sessions and events on `utm_content` attributes sign-ups to the exact post.
- The Control Center API gateway lists no GA operation today (catalog read 27 Oct).

## The ask

Give this engine one read-only route, in whichever form fits Control Center best: a gateway operation (for example `ga4.report`, no approval needed, bounded), or the readings carried in the engine's daily directive.

- **Property:** G-VC5V9LDE17 only.
- **Dimensions:** date, sessionSource, sessionMedium, sessionCampaignName, sessionManualAdContent, landingPage, eventName.
- **Metrics:** sessions, engagedSessions, eventCount, keyEvents.
- **Bounds:**
  - date ranges up to 90 days;
  - at most 1,000 rows;
  - no user-level or personal data;
  - no write to GA configuration.
- **First call:** list the event names seen in the last 28 days. The engine then records which ones are the sign-up and paid-subscription events in `invariants/ga4.json`, rather than guessing.

## How the engine uses it

- The Measurement Specialist validates each read as a `ga4_report` capture and joins it to signed posts by `utm_content`.
- It reconciles the weekly total against Substack's Growth sources. Substack stays the North Star source; any gap is logged, and the more conservative reading wins.
- It hands the per-post numbers to the What-Works Analyst for verdicts.
- Numbers go into the engine's Control Center report, never into this public repository.
