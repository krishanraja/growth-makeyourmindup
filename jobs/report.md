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
4b. **What worked, what did not, and why** (Ruling, Krish, 2026-11-15: "this full closed loop autonomous system
   must exist where I am shown every week what's working and what's not, but the system automatically
   incorporates what analyzes why things are working better than others").
   - Name the three posts that earned the most genuine interest and the three that earned the least, like with
     like per channel: subscribers their own link brought first, then shares, saves, comments and average watch
     per 1,000 views; each with why in one line (its hook, its subject, its format).
   - Split paid from organic. Every observation carrying `paid_boost` is reported apart, with what it bought
     (reach, clicks, subscribers if shown). A post whose reach is far over its channel's median while its
     engagement per 1,000 is under it is named "reach without interest; paid or not unknown" until Codex reads
     the ads manager. Paid never counts toward the North Star, and this engine's North Star is zero paid.
   - What feeds back with no press: the Sunday `learn` workflow reweights next week's mix by subscribers inside
     `mix.json`'s bounds. Anything beyond those bounds (a new lane, a channel's share, a boost) is a proposal.
   - Show Krish: the headline names the week's one winner and one loser, and the report's Control Center run
     proposes them as a `check_in` behind `strategy` ("On track?"), with the strategy changes in `exact_payload`.
   - Anything only his browser shows (the ads managers, Substack's subscriber sources, YouTube Studio's traffic
     sources) is read by Codex in a session he watches, and named unread until it is.
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
