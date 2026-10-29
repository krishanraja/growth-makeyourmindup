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
   Record the Substack all-source new-subscriber reading as `platform:
   substack`, `metric: new_free`, scope `publication` (rows with any other
   platform or metric are not counted); per-source rows use `source:<label>`, and Direct is
   recorded as `source:direct` whenever source rows are recorded without the
   publication row. Any other scope makes the weekly count missing
   (`docs/ENGINE.md`, "Objective").
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
9. Then file the chat backstop's kept lines in Control Center:
   `python growth.py cc backstop --deliver` (counts only; a line Control Center
   already holds answers duplicate).

## 27 October 2026: GA4 and the North Star line

Krish, 27 October 2026 (`CHANGES.md`;
`docs/plans/2026-10-27-engine-architecture.md`, sections 3 and 7). The
Measurement Specialist reads Google Analytics 4 directly, read-only, through
`python growth.py run ga4`: sessions, free sign-ups and paid subscriptions by
source, medium, campaign and `utm_content`, joined per post on `utm_content`
(the slot's placement identity). The steps:

1. `python growth.py run ga4 events --days 28 --live` lists the event names
   GA4 sees; record the confirmed sign-up and paid names in
   `invariants/ga4.json`. A report or join that relies on an unverified event
   name is refused; record those rows as missing with that refusal as reason.
2. `python growth.py run ga4 report --start YYYY-MM-DD --end YYYY-MM-DD --live`
   writes a new reading under `.scratch/ga4/` (or `--out FILE`).
3. `python growth.py run ga4 join CAPTURE SPEC` joins that reading per post.

Network happens only with `--live`, and only to Google's token and Data API
origins; without it the command prints what it would request. If this
checkout does not list `ga4` among the `growth.py run` commands yet, record
those rows as missing with reason `not_connected`; if the GA4 credentials are
not set, with reason `missing_credentials`. Never estimate them. GA4 numbers stay local and in the
Control Center report, never in the repository. Substack Growth sources stay
the North Star source: a weekly reconciliation keeps the more conservative
reading and logs the gap. `python growth.py run northstar --capture FILE`
computes the NOW.md North Star line from a settled Growth-sources capture
instead of a hand-written one. It only prints the line and the diff; NOW.md
and `lists/northstar-history.jsonl` change only with `--write`.
