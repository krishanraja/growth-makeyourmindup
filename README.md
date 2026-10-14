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

1. **The key.** On your Mac, run `openssl rand -hex 32` and copy the result.
   - In Vercel, open the control-center project > Settings > Environment
     Variables, and add `GROWTH_ENGINE_TOKEN` with that value for
     Production. Redeploy.
   - In Codex, open this repository's environment settings and add the same
     value as the secret `GROWTH_ENGINE_TOKEN`.
2. **The repository in Codex.** Connect krishanraja/growth-makeyourmindup in Codex
   (cloud or the desktop app), with internet access on, so a run can read
   public pages and reach controlcenter.krishraja.com.
3. **The browser.** The jobs read each channel's dashboard through a
   browser signed in as you (read only: `BROWSER.md`). In Codex, give the
   automations browser access (the Codex app with your Chrome profile, or a
   Codex environment with a signed-in browser), and stay signed in to
   Substack, YouTube Studio, Instagram, TikTok, X, LinkedIn and, later,
   Spotify for Creators. Without it, the jobs fall back to public pages and
   say so.
4. **The schedule.** Make eight Codex automations on this repository, New
   York time, each with the prompt shown:

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

5. **Optional:** connect Gmail in Codex so pitches and swap asks are also
   saved as Gmail drafts (never sent).

Test it once: run "Growth: day pack" by hand on a publishing day, then open
https://controlcenter.krishraja.com/#/growth?section=packs.
