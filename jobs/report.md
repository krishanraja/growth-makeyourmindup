# Job: weekly review

Kind `report`. Read shared instructions and `docs/ENGINE.md`. Sunday's total
queue budget is 30 minutes, including radar and any other pending work.

First, before reading any source: `python growth.py cc start --job report --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read the last eight days' packs/statuses and published pieces. Read local
   evidence envelopes and observations. Posted marks alone do not establish
   sent URLs or outcomes. Obtain actual human-confirmed event evidence when
   available; report missing execution visibility explicitly.
2. Compare like snapshots and disjoint metric windows. Record freshness and
   missing dashboard access. Never sum rolling weeks, views as unique reach,
   free-to-paid upgrades as new people, or double-count subscriber sources.
   Direct remains unattributed. Subscriber yield needs an attributed numerator
   and matching unique reach; otherwise "not shown". `growth.py measure`
   checks these boundaries. No inferred causal return from temporal growth.
3. Report net people, actual source mix, confirmed published assets and
   qualified journeys when available. Distinguish observed from proposed
   fixes. Include 30-day retention by acquisition cohort and measured effort
   only when those records exist; otherwise mark them unknown. Privacy-
   distorted email opens do not establish activation or reader quality.
4. Rank assets by attributed retained subscribers per measured hour when
   known; otherwise show the limited metric actually available. Review
   `experiments.json`: one variable, comparison, complete window, predeclared
   metric, minimum sample and quality guardrail. Low sample means collect
   more. Propose keep/test/fix, with uncertainty; Krish decides kill/scale.
   `growth.py experiment` guards incomplete or undersampled decisions.
   For each pilot in `lists/pilots.json` past its judge window, record the
   windows measured (`measured`: window and `captured_at`) and, once the
   What-Works Analyst gives one, its verdict (works, neutral, fails or
   insufficient) with `verdict_recorded_at`. Never a reading or a number:
   those stay in `.scratch`. The GitHub runner reports what is recorded.
5. Frame tests with the test record mapping in `knowledge/COPY-DOCTRINE.md`
   (weakest link first, biggest variable first). Money-model or paid tier
   ideas appear only here, as proposals with evidence. Each recommendation
   needs source/date, expected mechanism (a hypothesis),
   owner, effort, prerequisite and a verifiable success check. Pick at most
   three next-week priorities within the real time budget. A subjective
   breakout score informs planning, not a promise of results. Editorial
   input can name a supported question; do not create articles or scripts.
6. AI visibility: read the latest AEO result only when one ran, fortnightly
   on odd ISO Sundays from 25 October 2026. Quote its actual questions and
   cited sources, with run date/freshness. Missing or stale is explicit.
   Never run the paid AEO engine. Monthly, revisit deferred channels only
   against evidence and Krish's instructions; Notes/WhatsApp/paid stay off.
   27 October 2026 (`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`):
   Notes are back, from Krish's Substack profile, and Threads joins; report both as channels, each with its
   two-week baseline before any verdict. WhatsApp and paid stay off. The
   What-Works Analyst's ledger (`crew/what-works/`) goes into the Sunday
   check-in.
7. Prepare/check the v2 report. Current Control Centre cannot show all rich
   fields; include essential context in card prose and retain full local
   records. Apply the `AGENTS.md` delivery rule. UI requirements are a brief,
   not permission to modify Control Centre.
8. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job report --envelope .scratch/report.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
