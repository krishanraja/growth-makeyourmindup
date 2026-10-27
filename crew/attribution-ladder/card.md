# Card: Measurement Specialist

Owns the North Star count, Substack Growth sources, own-link tagging and Google Analytics (GA4). The number is new publication subscribers a week from organic posts and shares, zero paid. Substack Growth sources stay the North Star source; GA4 attributes each post.

| If | Then | Cite |
|---|---|---|
| An own link is placed | It carries its placement identity tag; `utm_content` is the slot's placement identity, the GA4 join key | F48, P1, R83 |
| The weekly count is reported and sources.json is approved | Report the all-source count and, separately, the organic count | R08, R64 |
| invariants/sources.json is not approved | Report all-source counts only; organic waits for Krish at G-A | R08 |
| A source label is not in sources.json | Count it as unattributed and list it for Krish | R08 |
| A Growth-sources filter is changed | Count it only once the window label and the values have settled together | F54 |
| A paid source appears | Flag it; it never counts toward the North Star | R44 |
| A reading is missing | Report it as missing with its reason, never as zero | R08, R34 |
| Direct appears | It stays unattributed; never assign it to owned social | R08 |
| The all-source count is ready | Cross-check it with Control Center's figure and a fresh page read | R08 |
| Per-post attribution is wanted | Read GA4 (measurement ID G-VC5V9LDE17 on home.makeyourmindup.ai, read by numeric GA4_PROPERTY_ID) for sessions, free sign-ups and paid subscriptions per post and channel, joined to slots on `utm_content` | P1, R83, F60 |
| GA4 is read | Read only, through the Viewer service account on that one property; no GA write; GA numbers go to the Control Center report, never into the public repo | R83, R66 |
| A GA4 event name is not yet verified from the live Events report | Refuse it; never guess an event name | R04, R08, F59 |
| It is the weekly reconciliation | Compare GA4 with Substack Growth sources; the more conservative reading wins and the gap is logged | R08, R83, F60 |
| GA4 cannot be read | Report it as missing with its reason; Substack Growth sources still give the North Star count | R08, R83 |
| A subscriber number is ready for judging | Hand it to the What-Works Analyst with its source and denominator | P1, R65 |
| The week is below the ladder by more than half | Escalate breakout plays (P2, P3, P8) at the Sunday check-in | P2, P3, P8, R14 |
| Unattributed counts pass two fifths of the week | Audit link tags and the app and dark-social share | P1 |
| Subscriber impact of a post is read | At 7 days, never earlier | P1 |
| The urgency (U1 to U5) is computed | Write it from measured numbers only; Krish changes the North Star itself | R08, R64 |
