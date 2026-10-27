# Routine: make (daily, 06:00 UTC)

This file is the whole instruction for a Claude cloud routine whose standing
text is "Clone krishanraja/growth-makeyourmindup (main) and follow
routines/make.md". Each run is a fresh session that remembers nothing. The
repository is public. Lane L1 (`docs/LANES.md`).

## Connectors

- **Control Center**: read only (approved pieces, publish boards, decisions,
  `get_venture_state`). No session holds the Control Center token: never look
  for it or ask for it. Writes reach Control Center only through the GitHub
  runner (step 8). Call no Control Center write tool.
- **Canva**: designs from the brand kit "Make Your Mind Up" (`kAHZOJ-K6I8`).
- **Buffer**: drafts only.
- **GitHub**: only to wake this repository's own workflow (step 8).

A connector missing or signed out: stop and report which.

## Walls

1. Never publish, schedule, send, delete or spend. Only drafts and proposals.
2. Buffer: every `create_post` has `saveToDraft: true`, `schedulingType:
   "automatic"`, no `dueAt` and no `mode`. Never pass a publish mode
   (`shareNow`, `shareNext`, `customScheduled`, `addToQueue`). Never edit or
   delete a post this run did not create.
3. Never print a secret, token or key, and never ask for one.
4. No figures in the public repository: commit nothing. Words, ids and
   readbacks stay in `.scratch/` (ignored) and in your summary.
5. The Codex in-app browser rules do not apply: this is a cloud session with
   no browser. Use the connectors only.
6. Stop and report on any uncertainty: a missing file, a lint error, an
   unknown channel id, a format you cannot place. After a timeout, read back
   first; never retry blindly.

## Steps

1. Note today's UTC date (`date -u +%F`). Read `docs/RUN.md`,
   `docs/ACCOUNT-VOICE.md` and `docs/PUBLISHING-AUTHORITY.md`. Run
   `python growth.py doctor --offline`.
2. **Slots.** Read today's slots from `calendar/v1.json`. Missing file or no
   slot today: report `calendar_missing` or `no_slots` and go to step 9.
3. **What is approved.** Through the Control Center connector, read the
   approved pieces and their publish boards (article, assets, video
   recordings) and Krish's decisions. Build a slot only from a piece whose
   publish board he approved (Ruling, Krish, 27 Oct 2026). Its derivatives
   (Notes, Threads, X, Instagram, Facebook, YouTube, TikTok, Stories) need no
   per-post sign-off, but until 29 Nov 2026 each derivative batch is shown to
   him first (step 8). A carousel, a meme or any format he has not approved
   before needs his eyes per item: build it, mark it `per_item_review`, and
   keep its words plain English, human and humble. Unapproved board: hold
   `board_not_approved`.
4. **Build in Canva.** Brand kit `kAHZOJ-K6I8`, templates only from
   `social/brand/kit.json` (missing file or no template for the format: hold
   `template_missing`). Every quote is a literal match to the published
   piece. Use `autofill-design` and `resize-design`; never publish from
   Canva. Export with `export-design` at the channel's size.
5. **Words.** Write each slot's words in its account's voice
   (`docs/ACCOUNT-VOICE.md`): Krish's personal accounts (X, TikTok, Threads,
   LinkedIn, Notes from his profile) sincere, warm and humble; publication
   accounts in their editorial voice. Facts only from the published piece. No
   em dashes, no percentages. Follow `python growth.py social route CHANNEL
   FORMAT` for each slot.
6. **Lint.** Put the slots in a draft spec at
   `.scratch/runs/<run>/draft.json` (`python growth.py run new --start
   <date> --kind piece`), fill hashes with `python growth.py run new --from
   .scratch/runs/<run>/draft.json --out .scratch/runs/<run>/spec.json`, then
   run `python growth.py run lint .scratch/runs/<run>/spec.json --record`,
   `python growth.py run plain` on each slot's words and `python growth.py
   run canva lint` on each export. Any error, or "not built yet", holds the
   slot with its code. Never type a hash by hand.
7. **Buffer drafts.** `get_account`, then `list_channels`; use exact channel
   ids, never guessed. Save each passing slot as a draft (wall 2). An asset
   needs a lasting public https URL; without one, hold `asset_url_missing`.
   LinkedIn slots go in as drafts too, `publish_mode` `krish_click`: Krish
   publishes them himself. Read each back with `get_post`: status draft, the
   exact words, asset order, no due time. Record its `buffer_draft_id`.
8. **Propose the go-live manifest through the runner.** The manifest is
   `run_id` plus, per slot, `slot`, `channel`, `buffer_draft_id`,
   `payload_sha256`, `per_item_review` and the spec slot's `format`,
   `due_at`, `link_placement` and `publish_mode`: ids, codes, times and
   hashes only, no words. Send it as the `repository_dispatch` type
   `growth-go-live-manifest` with `gh api
   repos/krishanraja/growth-makeyourmindup/dispatches --input FILE`, where
   FILE holds `{"event_type": "growth-go-live-manifest", "client_payload":
   MANIFEST}` (or the GitHub connector's dispatch tool). The runner
   (`.github/workflows/handoff.yml`) holds the token, checks each draft
   against its hash and proposes it to Control Center. The dispatch fails:
   hold `runner_path_missing` and put the manifest in your summary.
9. **Meter yourself.** Run `python growth.py run cost self --claude-dir
   ~/.claude/projects --since <today>` and paste its one line. (The full
   aggregate is `python growth.py run cost baseline --claude-dir
   ~/.claude/projects --since <today>`; it is never committed from here.)

## Summary (your last message)

- Built: each slot, channel, `buffer_draft_id`, and whether it needs his eyes.
- Held: each slot with its reason code and one plain sentence.
- Manifest: sent (event type) or held.
- Cost: the one line from step 9.

Nothing was published, scheduled, sent, deleted or spent. Say so.
