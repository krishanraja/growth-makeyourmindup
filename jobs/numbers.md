# Job: numbers

Kind `numbers`. Read `BROWSER.md` and `docs/ENGINE.md`. This is observation,
not an invitation to change integrations or fabricate missing analytics.

First, before reading any source: `python growth.py cc start --job numbers --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read each available dashboard for the previous completed New York day.
   Capture the platform's displayed timezone and window. If it cannot show
   that day, record the actual window; do not relabel a rolling week as
   yesterday. Take followers/subscribers as a timestamped snapshot.
2. Record structured observations using the metric registry in
   `engine/operations.py`: source URL, scope, asset ID when known, capture
   time, start/end with offsets, reporting timezone, metric, unit,
   availability and value. Missing values are null with a reason such as
   signed_out, not_connected, not_shown, delayed or not_supported.
   Counts rounded on a public profile are not exact dashboard observations.
3. Keep unique reach, impressions, views, plays, sessions, link clicks,
   followers and subscribers distinct. Do not put views or plays in `reach`.
   On Substack, distinguish new people, free-to-paid upgrades, unsubscribes,
   reactivations and paid cancellations when shown. A cancellation does not
   automatically mean the person left the publication.
4. Record actual attributed source counts separately: native recommendations,
   app, partner, reader referral and external placement. Direct remains
   unattributed. Never assign it to owned social merely because it is direct.
   Capture source export/window and delayed reporting. Preserve original
   acquisition separately from subsequent internal placements.
5. Validate `python growth.py measure .scratch/observations.json`.
   Use `--aggregate` only for a comparable series of disjoint contiguous
   interval windows. Never add daily captures of the same rolling week or
   snapshots. A revised capture replaces the exact earlier window.
6. Prepare the legacy numbers display only from matching structured
   observations: `followers` is a snapshot, daily supported interval fields
   stay daily, `new_this_week` is omitted. Include source URL, actual window,
   capture time, timezone, units and missing reasons in every row's `note`,
   because today's API cannot store those fields structurally. If dashboard
   access is absent, state it and leave values null. Source observation time
   remains separate from pack date. Include `observations` in the v2 input.
7. Headline states the supported change or the access gap. A delta requires
   comparable snapshots. Never claim a social post caused the change.
   Prepare/check locally, then apply `AGENTS.md`'s delivery boundary.
8. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job numbers --envelope .scratch/numbers.json --queue .scratch/queue.json --observations .scratch/observations.json --deliver`.
   Pass `--observations` once for each observations file from this New York
   week, so the weekly new-subscriber count can start on Monday; a gap or an
   unread day reports the count as missing with its reason, never as zero.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
