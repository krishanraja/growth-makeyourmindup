# growth-makeyourmindup

The independent, draft-only growth engine for makeyourmindup. It finds
useful distribution opportunities, preserves their evidence, tracks each
placement, and fits the work into 20 minutes a day, 30 on Sunday. Krish
publishes, sends and changes settings himself.

The growth-repository upgrade is complete. Control Center's brief for this
engine is [docs/CONTROL-CENTER-BRIEF.md](docs/CONTROL-CENTER-BRIEF.md), which
supersedes [docs/CONTROL_CENTER_HANDOFF.md](docs/CONTROL_CENTER_HANDOFF.md).
The channel audit and exact next actions are in
[docs/CHANNEL_PLAYBOOK.md](docs/CHANNEL_PLAYBOOK.md). Validation evidence and
access limits are in [docs/VALIDATION.md](docs/VALIDATION.md).

Start with `AGENTS.md`, then `PLAYBOOK.md`, `BROWSER.md` and the named job.
`channels.json` inventories the surfaces, `journeys.json` maps the useful
paths, `hooks.json` contains testable house hypotheses, and
`experiments.json` holds unstarted experiment templates.

## Verify locally

Python 3.9 or newer. Standard library only. These commands work in Windows
PowerShell and need no key, social login or external write:

```powershell
python growth.py doctor --offline
python growth.py --self-test
python growth.py dry-run
```

Read the public feed through the same acceptance flow:

```powershell
python growth.py dry-run --live --out .scratch/public-check
python growth.py pieces --days 21 --full
python growth.py discover --days 21
```

Local records go in ignored `.scratch/`. Fixtures are visibly test data.
No live campaign is generated or published by the acceptance flow.

## Prepare work

See [docs/ENGINE.md](docs/ENGINE.md) for the input shape and workflow.
`prepare` requires evidence and review metadata; `check` catches source
reference errors, literal quote mismatches, house rules and platform limits.
It cannot prove a paraphrase is true. Compare the claims with the source.

```powershell
python growth.py prepare .scratch/input.json --out .scratch/envelope.json
python growth.py check .scratch/envelope.json
python growth.py queue .scratch/envelope.json --out .scratch/queue.json
python growth.py export .scratch/envelope.json --out .scratch/legacy-pack.json
python growth.py post .scratch/envelope.json
```

The last command is a dry run. No Control Centre write happens without
`--deliver`, which is reserved for a separately authorised scheduled run.
This implementation session does not deliver packs or change Control Centre.
The supported legacy API drops rich metadata, so full records stay local
until the handoff is implemented. No database fallback exists.

## Reporting to Control Center

Every scheduled job starts with `python growth.py cc start --job KIND --deliver`
and ends with `python growth.py cc finish --job KIND ... --deliver`: the growth
engine protocol loop (attempt, directive, report with a digest readback,
decisions, attempt end). Each selected draft goes to Krish as a proposal with
its exact words; the engine never posts or sends. Without `--deliver` both are
local dry runs. Control Center also wakes `.github/workflows/control-center.yml`
every morning; that runner checks the engine offline and reports what it can
see. Details: [docs/ENGINE.md](docs/ENGINE.md), "Reporting to Control Center",
and [docs/CONTROL-CENTER-BRIEF.md](docs/CONTROL-CENTER-BRIEF.md).

```powershell
python growth.py cc finish --job daily --envelope .scratch/daily.json --queue .scratch/queue.json
python growth.py cc runner
```

## Existing runtime

There are still eight scheduled job definitions in `automations.json`.
No automation is created or changed by this upgrade. All times are in
`America/New_York`; use the scheduler's named timezone so daylight-saving
changes follow New York, rather than storing a one-time local conversion.

| Job | New York time | Prompt |
|---|---|---|
| Numbers | daily 06:00 | `Run jobs/numbers.md as AGENTS.md says.` |
| Radar | daily 06:30 | `Run jobs/radar.md as AGENTS.md says.` |
| Day pack | Mon/Wed/Fri 13:30 | `Run jobs/daily-pack.md as AGENTS.md says.` |
| Pitches | Tue 07:00 | `Run jobs/pitches.md as AGENTS.md says.` |
| Partners | Wed 07:00 | `Run jobs/partners.md as AGENTS.md says.` |
| Recommendations | Thu 07:00 | `Run jobs/swaps.md as AGENTS.md says.` |
| Front door | Sat 07:00 | `Run jobs/conversion.md as AGENTS.md says.` |
| Report | Sun 07:00 | `Run jobs/report.md as AGENTS.md says.` |

`python growth.py doctor` separately checks public-feed and authenticated
Control Centre read access. It does not prove signed-in social insights are
available. Those access states are captured per observation. Existing
`GROWTH_ENGINE_TOKEN` setup is described in `docs/KEY.md`; do not regenerate
an already configured secret. GitHub secrets cannot be read back.

The content engine and AEO engine remain independent. No Notes, WhatsApp,
paid boosts, social publishing, automated outreach or profile changes.
