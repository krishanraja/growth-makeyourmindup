# Routine: plan (Sundays, 05:30 UTC)

This file is the whole instruction for a Claude cloud routine whose standing
text is "Clone krishanraja/growth-makeyourmindup (main) and follow
routines/plan.md". Each run is a fresh session that remembers nothing. The
repository is public. Lane L1 (`docs/LANES.md`).

## Connectors

- **Control Center**: read only (verdicts from the measure output, decisions,
  `get_venture_state`, the content-engine calendar). No session holds the
  Control Center token: never look for it or ask for it. Writes reach Control
  Center only through the GitHub runner (step 6). Call no Control Center
  write tool.
- **Buffer**: read only (`list_posts`, `get_post`, `get_aggregated_post_metrics`).
- **Canva**: read only, to check a template still exists.
- **GitHub**: only to wake this repository's own workflow (step 6).

A connector missing or signed out: stop and report which.

## Walls

1. Never publish, schedule, send, delete or spend. Only drafts and proposals.
2. Never call a Buffer write or a publish mode (`shareNow`, `shareNext`,
   `customScheduled`, `addToQueue`). This routine makes no Buffer post.
3. Never print a secret, token or key, and never ask for one.
4. No figures in the public repository: commit nothing. Numbers, words and
   the packet stay in `.scratch/` (ignored) and in your summary.
5. The Codex in-app browser rules do not apply: this is a cloud session with
   no browser. Use the connectors only.
6. Stop and report on any uncertainty. Change the calendar only through a
   registered experiment (`experiments.json`); never edit `calendar/v1.json`
   by hand from here.

## Steps

1. Note today's UTC date (`date -u +%F`) and next week's Monday. The week
   number is the ISO week of that Monday (W45, W46, ...). Read `docs/RUN.md`,
   `docs/NORTH_STAR.md` and `docs/ACCOUNT-VOICE.md`. Run `python growth.py
   doctor --offline`.
2. **Verdicts.** Through the Control Center connector, read last week's
   measure output: each slot's verdict (`works`, `neutral`, `fails`,
   `insufficient`) and the North Star line from `get_venture_state`. Missing
   means unknown, never zero.
3. **The ladder gap.** Next week's rung is in `docs/NORTH_STAR.md` (the
   ladder). The gap is the rung less the last measured week. Unmeasured: say
   so and plan to the rung.
4. **The calendar.** Read the content-engine calendar through Control Center
   and this repository's `calendar/v1.json` (missing: hold
   `calendar_missing`). List next week's pieces and slots.
5. **The week packet.** Build the W-number packet in
   `.scratch/runs/<run>/`: start it with `python growth.py run new --start
   <Monday> --kind week`, fill it from the calendar, then `python growth.py
   run new --from DRAFT --out SPEC` and `python growth.py run lint SPEC
   --record`. It names the week, the rung, the gap, what worked and what to
   stop, each slot, and any calendar change. A calendar change is allowed
   only as an arm of a registered experiment in `experiments.json`, at most
   one experiment per channel; otherwise leave it out and say why. Lint
   errors hold the packet.
6. **Propose the Sunday sign-off through the runner.** The proposal is the
   `run_id`, the week number, the spec's lint digest and each slot's
   `payload_sha256`: ids and hashes only. If a workflow under
   `.github/workflows/` on main lists the `repository_dispatch` type
   `growth-week-packet`, send it with `gh api
   repos/krishanraja/growth-makeyourmindup/dispatches --input FILE`, where
   FILE holds `{"event_type": "growth-week-packet", "client_payload":
   PACKET}` (or the GitHub connector's dispatch tool). The runner holds the
   token and proposes it as the Sunday sign-off (G-A). No such workflow:
   send nothing, hold `runner_path_missing`, and put the packet in your
   summary.
7. **Meter yourself.** Run `python growth.py run cost self --claude-dir
   ~/.claude/projects --since <today>` and paste its one line.

## Summary (your last message)

- The week number, the rung and the gap, with where each was read.
- What worked, what failed, what is insufficient.
- The packet: sent (event type) or held, with each slot in one line.
- Calendar changes proposed, each with its experiment id.
- Cost: the one line from step 7.

Nothing was published, scheduled, sent, deleted or spent. Say so.
