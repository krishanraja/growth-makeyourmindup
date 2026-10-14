# growth-makeyourmindup

The makeyourmindup growth engine. It drafts what brings relevant new
followers and subscribers to Krish Raja's channels, with no paid boosts. It
runs as scheduled Codex sessions. Every run reports into Control Center
(Growth > Packs), where Krish copies each draft, posts it himself, and marks
it Posted or Skipped.

- How it works and the rules: `AGENTS.md` (Codex reads it on every run).
- The jobs: `jobs/`. The one tool: `growth.py` (Python standard library only).
- The operating system: `PLAYBOOK.md`, from the documents in `knowledge/`. Browser rules: `BROWSER.md`.
- Earlier research: `research.md`. Hooks by platform: `hooks.json`. Krish's changes: `CHANGES.md`.

Nothing here posts, sends, comments, follows or spends. The content engine
(krishanraja/content-engine) is not used: facts come from the published
articles in the public feed.

## Setting it up (Krish, once)

1. **The key** (one minute; exact steps in `docs/KEY.md`). Make it on your
   Mac, save it where the engine looks, and put the same value in Vercel.
2. **Open this repository in the Codex app** on your Mac (Add project,
   choose your clone of krishanraja/growth-makeyourmindup), and stay signed
   in to Substack, YouTube Studio, Instagram, TikTok, X and LinkedIn in your
   browser.
3. **Start a Codex chat in this project and type: `create the automations`.**
   Codex checks the machine (`python3 growth.py doctor`), creates the eight
   scheduled tasks from `automations.json`, reads them back, and runs the
   numbers job once to prove a pack lands in Control Center (`AGENTS.md`,
   "When Krish says: create the automations").
4. Keep the Mac on, and the app running, at the scheduled times.

Optional: connect Gmail in Codex so pitches and swap asks are also saved as
Gmail drafts (never sent).

The schedule (New York time; `automations.json` is the source):

| Name | When | Prompt |
|---|---|---|
| Growth: numbers | daily 06:00 | `Run jobs/numbers.md as AGENTS.md says.` |
| Growth: radar | daily 06:30 | `Run jobs/radar.md as AGENTS.md says.` |
| Growth: day pack | Mon, Wed, Fri 13:30 | `Run jobs/daily-pack.md as AGENTS.md says.` |
| Growth: pitches | Tue 07:00 | `Run jobs/pitches.md as AGENTS.md says.` |
| Growth: partners | Wed 07:00 | `Run jobs/partners.md as AGENTS.md says.` |
| Growth: recommendations | Thu 07:00 | `Run jobs/swaps.md as AGENTS.md says.` |
| Growth: front door | Sat 07:00 | `Run jobs/conversion.md as AGENTS.md says.` |
| Growth: report | Sun 07:00 | `Run jobs/report.md as AGENTS.md says.` |
