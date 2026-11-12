# growth-makeyourmindup

The social media manager and distribution engine for makeyourmindup and
Krish's named personal accounts. It owns posting strategy, amplification,
authorised automatic posting, engagement preparation, live audits and
channel performance. Content-engine owns production and all production
standards. [The ownership and handoff contract](docs/ENGINE-BOUNDARY.md)
keeps those responsibilities separate. Growth preserves evidence, tracks
each placement and fits human review into 20 minutes a day, 30 on Sunday. Krish
approves creative, positioning, bio and pinned-content changes. Weekly live
browser audits may repair existing metadata and subscription links under
the explicit scoped authority in AGENTS.md. Other publication stays gated.

27 October 2026 (`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`):
Growth also produces, in Canva, the formats content-engine does not cover
(today Substack Notes and memes; `docs/ENGINE-BOUNDARY.md`, "the Canva
lane"). Content-engine keeps every other format and all production standards.

**Current (5 November 2026).** The work runs as four engines, one per
session: Acquisition, Engagement, Publishing, and Measurement and
Allocation ([Four engines](#four-engines) below; AGENTS.md, "Four engines").
Make Your Mind Up outreach (shows, newsletters, creators, editorial
features, swaps and partners) is this engine's, owned by Acquisition, and
social engagement is Engagement's. Krish enacts both in his own Codex
sessions on the exact payload he approves; only Mindmake's outreach stays
with Control Center (AGENTS.md, "Outreach for Make Your Mind Up"). Through
the shadow week the PC automations, the daily heartbeat
([jobs/daily-growth.md](jobs/daily-growth.md)) and the GitHub workflows keep
running unchanged.

## Four engines

Krish opens a Codex session with "Run Acquisition", "Run Engagement", "Run
Publishing" or "Run Measurement". That session is that engine only and
follows its job file: [jobs/acquisition.md](jobs/acquisition.md),
[jobs/engagement.md](jobs/engagement.md),
[jobs/publishing.md](jobs/publishing.md) or
[jobs/measurement.md](jobs/measurement.md). Each engine's contract is
`engines/<name>.json`; its committed, privacy-safe records are
`engines/records/<name>.jsonl`; exact words, recipients, post URLs and
session links stay in the ignored `.scratch/engines/`. The spec is
[docs/reviews/2026-11-05-growth-engine-review.md](docs/reviews/2026-11-05-growth-engine-review.md).

```powershell
python growth.py engine start NAME [--session LINK]
python growth.py engine check
python growth.py engine show NAME [ID]
python growth.py engine history NAME ID
python growth.py engine handoff FROM TO --what TEXT --why TEXT [--link ID]
python growth.py engine done NAME ID --note TEXT [--next TEXT]
python growth.py engine close NAME --learnings FILE
python growth.py engine session set|show|clear ENGINE [LINK]
```

`start` shows Krish's open instruction first (`krish_instruction`, below),
then recovers the queue, inbound handoffs and the last sessions' learnings;
with `--session` it also records this session's own link.
`handoff` prints the question for Krish ("Do you have a session running for
the X engine? ...") and the exact message for that session. `done` on a
handoff prints the report-back for the session that sent it. `close`
refuses to close without specific "better next time" learnings, and takes
an `instruction_ack` when the session acted on his instruction.

## Lanes: what runs alone and what needs Krish

[docs/LANES.md](docs/LANES.md) says, in plain words, what runs on its own
(L0 GitHub Actions), what waits for one press in Control Center (L2) and
what waits for Krish's hands (L3: LinkedIn, the Buffer plan, one-time set-up
in [docs/SETUP-ONCE.md](docs/SETUP-ONCE.md)). GitHub Actions runs ten
workflows: control-center, release, measure, keys, handoff, check, artdirect,
maker ([docs/MAKER.md](docs/MAKER.md)), ledger and learn
([docs/MIX.md](docs/MIX.md), "Learning"). There
are no Claude routines and no Claude schedules of any kind (Krish, 29 Oct
2026): a new schedule is a GitHub Actions job. His one exception that day is
the daily credits session in `lanes.json` (`claude_sessions`,
[docs/CREDITS.md](docs/CREDITS.md)). Making (Canva assets, words,
Buffer drafts) is done by sessions and the automations on Krish's PC
(below; nine kept until W46) under the same walls, and follows
[docs/TASTE.md](docs/TASTE.md). Only the GitHub
runner (a repository secret) and Krish's PC (a file, for Codex workspace
runs) hold the Control Center engine key ([docs/KEY.md](docs/KEY.md)); a
Claude session reads Control Center through its connector.

## Weekly channel audit

[docs/CHANNEL-AUDIT.md](docs/CHANNEL-AUDIT.md) records the accepted brief,
authority and browser workflow. [jobs/channel-audit.md](jobs/channel-audit.md)
is the executable agent job. Initial coverage is profiles, pins and 30 days
of posts; subsequent runs use per-account complete checkpoints and revisit
older work still getting attention. `growth.py audit` guards edit scope and
journals browser intent/readback; it does not itself drive a browser.
The weekly slot is Saturday 12:00 Europe/London, following this Codex chat.
It needs the host online and account access in its available browser.

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

The last command is a dry run. No Control Center write happens without
`--deliver`, which is reserved for a separately authorised scheduled run.
An interactive session never delivers packs or changes Control Center.
The supported legacy API drops rich metadata, so full records stay local
until the handoff is implemented. No database fallback exists.

## Reporting to Control Center

Every scheduled job starts with `python growth.py cc start --job KIND --deliver`
and ends with `python growth.py cc finish --job KIND ... --deliver`: the growth
engine protocol loop (attempt, directive, report with a digest readback,
decisions, attempt end). Each selected post or comment draft goes to Krish as
a proposal with its exact words. Pitches, partners and swaps never go to
Control Center: `cc finish` holds them, because Make Your Mind Up outreach is
this engine's own. The loop itself never posts or sends; only an approved
go-live does, through the go-live step. Without `--deliver` both are
local dry runs. Control Center also wakes `.github/workflows/control-center.yml`
every morning; that runner checks the engine offline and reports what it can
see. Details: [docs/ENGINE.md](docs/ENGINE.md), "Reporting to Control Center",
and [docs/CONTROL-CENTER-BRIEF.md](docs/CONTROL-CENTER-BRIEF.md).

**Krish's instruction** (protocol 1.20.0). Krish can give this engine his
next best action from Control Center (the Engine drawer's Instruct). It comes
in the directive as `krish_instruction` and is never an approval: the walls
stay where they are. The runner acks it `received` by id; when it wakes the
runner a second time in a day, that run reports under its own `--wake`
run_id and is named "control-center instruction wake", which the 05:40 UTC
backup never mistakes for the morning push. `cc start` prints it first and
keeps it in the ignored `.scratch/cc/`; the job acts on it first and ends
with `cc finish --ack started|done|blocked --ack-line "..."`. The four engine
sessions see the same local copy at `engine start` and record what they did
with it at `engine close` (`instruction_ack`), and the next workspace job's
`cc finish` reports that ack. His words never reach a commit, a public log or
a report. Every report that pulls the directive also carries this engine's
state (priorities, obsessions and next steps), each left out when empty.
Details: AGENTS.md, "His instruction", and docs/ENGINE.md, "Krish's
instruction and the engine's state".

```powershell
python growth.py cc finish --job daily --envelope .scratch/daily.json --queue .scratch/queue.json
python growth.py cc runner
```

## Existing runtime

There are ten scheduled job definitions in `automations.json`, run on
Krish's PC (`lanes.json`). Nine are kept until W46. The tenth, the weekly
Substack read ([jobs/subscribers.md](jobs/subscribers.md)), was added on 12
November 2026 and stands, because only his signed-in browser can read
Substack (Ruling, Krish, 2026-11-12: the engine reads subscribers every week
and judges posts by subscribers, not engagement). The ninth, the weekly
answer piece, was added on 21 October 2026. Krish creates a new one in
Codex by saying "create the automations" again, which updates the existing
ones and adds the new one. The weekly conversion slot now runs the channel
audit at Saturday 12:00 `Europe/London`; all other times are in
`America/New_York`; use the scheduler's named timezone so daylight-saving
changes follow New York, rather than storing a one-time local conversion.

| Job | Time (New York unless stated) | Prompt |
|---|---|---|
| Numbers | daily 06:00 | `Run jobs/numbers.md as AGENTS.md says.` |
| Radar | daily 06:30 | `Run jobs/radar.md as AGENTS.md says.` |
| Subscribers (weekly Substack read) | Mon 06:15 | `Run jobs/subscribers.md as AGENTS.md says.` |
| Day pack | Mon/Wed/Fri 13:30 | `Run jobs/daily-pack.md as AGENTS.md says.` |
| Pitches | Tue 07:00 | `Run jobs/pitches.md as AGENTS.md says.` |
| Partners | Wed 07:00 | `Run jobs/partners.md as AGENTS.md says.` |
| Recommendations | Thu 07:00 | `Run jobs/swaps.md as AGENTS.md says.` |
| Answer piece | Sat 09:00 | `Run jobs/answer.md as AGENTS.md says.` |
| Weekly channel audit / front door | Sat 12:00 Europe/London | `Run jobs/conversion.md as AGENTS.md says, starting with jobs/channel-audit.md.` |
| Report | Sun 07:00 | `Run jobs/report.md as AGENTS.md says.` |

`python growth.py doctor` separately checks public-feed and authenticated
Control Center read access. It does not prove signed-in social insights are
available. Those access states are captured per observation. Existing
`GROWTH_ENGINE_TOKEN` setup is described in `docs/KEY.md`; do not regenerate
an already configured secret. GitHub secrets cannot be read back.

The content engine and AEO engine remain independent. No Notes, WhatsApp,
paid boosts or automated outreach. Only the scoped existing-field audit
repairs above may change social content without a fresh approval.

27 October 2026 (`CHANGES.md`; `docs/plans/2026-10-27-engine-architecture.md`):
"No Notes" above is superseded. Substack Notes are back, posted from Krish's
Substack profile at up to two a day as he signs, and Threads joins with
delegated cadence. Signed exact payloads on X, TikTok, Threads and Notes go
out through the go-live step; LinkedIn stays his click. A run session reads
`docs/RUN.md`. WhatsApp, paid boosts and automated outreach stay off.
