# Validation and scope record

Completed locally on 17 October 2026. The implementation is in the growth
repository only. No Control Centre write, deployment, credential change,
social publication, outreach send or platform setting change was performed
in this implementation. The earlier audit's pre-correction report is
acknowledged in the handoff.

## Checks completed

| Check | Result |
|---|---|
| `python growth.py --self-test` | 84 regression tests pass |
| `python growth.py doctor --offline` | Ready; no token or network needed |
| `python growth.py dry-run --out .scratch/final-offline` | Complete; replay creates no new tasks; draft does not advance contact |
| `python growth.py dry-run --live --out .scratch/public-acceptance` | Complete using the real public feed; no external write |
| `prepare` and `check` against labelled fixture | Complete with explicit fixture clock |
| Python byte compilation and JSON parsing | Pass |
| `git diff --check` | Pass |
| Legacy export against read-only CC parser snapshot | Pass for all eight kinds, extra-field loss, unchanged/edited status carry, bad date/action refusal |

The compatibility snapshot was read from an existing read-only local copy
of Control Centre main `379d193052027fe290bafca4f37f9ef902a0b112`. No private
Control Centre source is bundled here. `tests/contract.mjs` can repeat that
check with an independently available snapshot; it does not call the API.

CI uses the same tests, offline doctor and offline acceptance flow on
Ubuntu and Windows, Python 3.9 and 3.12. GitHub's check workflow records the
remote matrix outcome on the branch/PR. CI has no secrets or external writes.
The `automations.json` schedule/prompt definitions are unchanged.

## What the real feed run established

Observed at 09:55 UTC on 17 October:

- Nine recent feed items within the requested 30-day lookback.
- Eight readable bodies and one missing body, explicitly held pending.
- No article/video pair verified from a unique explicit published link in
  that sample. The engine did not guess a pair from a similar title.
- Replaying the same input produced zero new discovery tasks.
- One local source-review envelope, compatible pack and two-minute queue
  were produced. This was a review card, not a social campaign.

Artifacts remain in ignored `.scratch/`. The offline fixture has visibly
invented test text and a fixed 18:00 UTC fixture clock; its values are not
real analytics or a publication recommendation.

## Meaningful regression coverage

- UTC/New York date difference, both DST transitions, Windows without IANA
  data and invalid/naive timestamps.
- UTM replacement, encoding, functional/referral parameters, fragments,
  placement identity and original acquisition preservation.
- Late and revised publications, replay identity, missing body, ambiguous
  pairing, corrupt feed and lock/atomic-write behaviour.
- House rules, UTF-16 API limits, weighted X text, complete/matching link
  tags, LinkedIn comment restrictions and radar freshness.
- Required sources, literal excerpt/quote checks, forged or changed copy,
  future evidence, duplicate item identity and explicit API projection.
- Null/zero distinction, units, source/scope matching, duplicate captures,
  overlapping/gapped windows, snapshot refusal and attributed yield.
- Immature retention cohorts, incomplete/undersampled experiment decisions,
  shared daily/Sunday budgets, expired/blocked/handled work and bad estimates.
- Draft/contact distinction, real confirmation/evidence, send cooldown,
  inbound reply, decline and future relationship events.
- Credential-free development, explicit write gate, approved origin,
  redirect refusal and safe remote-error handling.

## Practical limits preserved in the handoff

The local runtime did not contain a bound growth token or a signed-in
social-dashboard session. This upgrade does not claim private subscriber,
source, cohort or retention values, nor a tested authenticated pack delivery.
Those are separately dated runtime access checks. GitHub secrets are not
readable values; Vercel access is not native social insight access.

The linter checks provenance and declared literal quotes. A human still
compares each paraphrased claim to the source. X emoji/URL parsing is
conservative, not a full twitter-text implementation. RSS may expose less
history than requested. Website instrumentation and social settings are
handoff actions, not changes already deployed. The current Control Centre
API drops rich fields; local envelopes retain them until the receiving
implementation is built.
