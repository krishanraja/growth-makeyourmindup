# Routine: watch (daily, 07:30, 12:30 and 17:30 UTC)

This file is the whole instruction for a Claude cloud routine whose standing
text is "Clone krishanraja/growth-makeyourmindup (main) and follow
routines/watch.md". Each run is a fresh session that remembers nothing. The
repository is public. Lane L1 (`docs/LANES.md`).

## Connectors

- **Buffer**: read Ideas (`list_idea_groups`, `list_ideas`); save drafts.
- **Canva**: designs from the brand kit "Make Your Mind Up" (`kAHZOJ-K6I8`).
- **Control Center**: read only (publish boards, decisions,
  `get_venture_state`). No session holds the Control Center token: never
  look for it or ask for it. Writes reach Control Center only through the
  GitHub runner. Call no Control Center write tool.
- **GitHub**: only to wake this repository's own workflow.

A connector missing or signed out: stop and report which.

## Walls

1. Never publish, schedule, send, delete or spend. Only drafts and proposals.
2. Buffer: every `create_post` has `saveToDraft: true`, `schedulingType:
   "automatic"`, no `dueAt` and no `mode`. Never pass a publish mode
   (`shareNow`, `shareNext`, `customScheduled`, `addToQueue`). Never edit or
   delete an idea or a post this run did not create.
3. Never print a secret, token or key, and never ask for one.
4. No figures in the public repository: commit nothing. Words, ids and
   readbacks stay in `.scratch/` (ignored) and in your summary.
5. The Codex in-app browser rules do not apply: this is a cloud session with
   no browser. Use the connectors only.
6. Stop and report on any uncertainty. After a timeout, read back first;
   never retry blindly.

## Steps

1. Note the UTC time (`date -u +%FT%TZ`). Read `docs/RUN.md` and
   `docs/ACCOUNT-VOICE.md`. Run `python growth.py doctor --offline`.
2. **Express ideas.** `get_account`, then `list_ideas` for that
   organization. An express idea is one Krish added since the last watch
   (about five hours, or since 17:30 UTC yesterday for the 07:30 run). One
   express go-live a day: if one already waits, the newest idea waits too
   and you say so.
3. **Build each idea.** Follow `routines/make.md` steps 4 to 7 for it: Canva
   from the kit, words in the account voice, lint, Buffer drafts with their
   readback. A carousel, a meme or a format he has not approved before
   needs his eyes per item. Then make the G-X preview: the drafts' ids, the
   channels and each `payload_sha256` in `.scratch/runs/<run>/`, and
   propose it through the runner exactly as `routines/make.md` step 8 says,
   with event type `growth-go-live-manifest` and `"express": true` beside
   `run_id`. The dispatch fails: hold `runner_path_missing` with the preview
   in your summary.
4. **Newly approved publish boards.** Through the Control Center connector,
   read the publish boards Krish approved since the last watch. For each,
   send `{"event_type": "growth-make-piece", "client_payload": {"piece_id":
   ID}}` with `gh api repos/krishanraja/growth-makeyourmindup/dispatches
   --input FILE` (or the GitHub connector's dispatch tool); the runner only
   records it. Then follow `routines/make.md` steps 3 to 8 for that one
   piece in this session.
5. **Report anything held.** List every slot, idea or board held, from this
   run and from Control Center's holds for this engine, each with its
   reason code.
6. **Meter yourself.** Run `python growth.py run cost self --claude-dir
   ~/.claude/projects --since <today>` and paste its one line.

## Summary (your last message)

- Ideas found, built and previewed (G-X), with draft ids.
- Boards approved and what make did for each.
- Held: each item with its reason code and one plain sentence.
- Cost: the one line from step 6.

Nothing was published, scheduled, sent, deleted or spent. Say so.
