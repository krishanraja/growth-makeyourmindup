# Brief for Control Center: give the makeyourmindup growth engine its GA4 readings

From the growth-makeyourmindup engine, 27 October 2026. This is the primary route. Krish, 27 Oct: "just get google analytics from control center, might be easier." This repository changes nothing in Control Center (AGENTS rule 7; Krish, 17 Oct: "only pass me a brief"). A Control Center session applies this.

## What Control Center already has (read from its code at 0d4193e, 27 Oct)

- `src/lib/webProperties.ts` registers property **mymu**: home.makeyourmindup.ai, measurement ID `G-VC5V9LDE17`, numeric ID from `GA4_PROPERTY_MAKEYOURMINDUP`, venture `publication`.
- `api/growth/snapshot.ts` runs a daily `runGa4Batch` (`api/_google.ts`). Headline totals go into `growth_metrics` (`mymu_*` keys).
- Breakdowns go into `web_analytics_daily` (migration `20260925090000`): property, metric_date, `dim_type` (`source_medium` | `landing_page`), dim_value, sessions, users and key_events.

## What the engine cannot get today

1. **Nothing reaches the engine.** The engine protocol's directive (`api/_growthEngines.ts`, `op === 'directive'`) carries only the engine's own reported objectives. No GA reading reaches it.
2. **No per-post breakdown.** The breakdowns stop at source/medium and landing page. Every post the engine publishes carries `utm_content` set to a stable placement identity for that one post (growth repo `engine/core.py`, `tracked`). Without a `sessionManualAdContent` breakdown, sign-ups cannot be tied to the post that caused them.
3. **Event names are unknown.** Substack says its GA4 integration sends page views, sign-ups and paid subscriptions, but the exact event names on this property are not confirmed.

## The change (smallest that works)

1. **Snapshot, mymu only.** Add a third breakdown, `dim_type = 'utm_content'`:
   - dimensions `sessionManualAdContent`, `sessionSource` and `eventName`;
   - metrics `sessions`, `keyEvents` and `eventCount`.

   Store it in the same `web_analytics_daily` table, with the value encoded as `content|source|event`, or add columns if Control Center prefers. Keep "(not set)" rows out of the per-post view.
2. **Event names.** Once, and then weekly, list the property's event names and which are marked key events (`ga4AdminGet`, already in `api/_google.ts`). Record them so the engine can confirm the sign-up and paid-subscription events.
3. **Directive.** In the makeyourmindup engine's directive, add an optional `web_analytics` block as a new minor protocol version. Engines that do not use it ignore it ("Raise yours only for a field you use"):

   ```json
   { "property": "mymu", "measurement_id": "G-VC5V9LDE17", "through": "YYYY-MM-DD", "days": 28,
     "events": [{ "name": "...", "key_event": true, "count_28d": 0 }],
     "rows": [{ "date": "YYYY-MM-DD", "dim_type": "source_medium|landing_page|utm_content", "value": "...",
                "sessions": 0, "users": 0, "key_events": 0, "event_name": null }],
     "coverage": { "complete": true, "reason": null } }
   ```

   A part that cannot be read is `null`, never zero, with a reason, following the protocol's existing rule. No personal data.

## How the engine uses it (growth repo, already built or building)

- `growth.py cc start` keeps the directive. The Measurement Specialist (`engine/run/measure.py`, `engine/run/ga4.py`) turns `web_analytics` into a `ga4_report` capture.
- It joins rows to signed posts on `utm_content`.
- It reconciles the weekly sign-up total with Substack's Growth sources. Substack stays the North Star source; any gap is logged, and the more conservative reading wins.
- It hands per-post sign-ups and paid subscriptions to the What-Works Analyst.
- Event names are used only once confirmed.
- Numbers go back to Control Center in the engine's report, never into the public growth repository.

## Fallback

The growth repo also contains a direct GA4 reader, which runs only with `GA4_PROPERTY_ID` and `GA4_SERVICE_ACCOUNT_JSON` set. Krish preferred this Control Center route, so those stay unset.
