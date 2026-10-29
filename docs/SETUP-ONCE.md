# Set up once

The steps only Krish can do, each done once. They are lane L3 in
[LANES.md](LANES.md). Never paste a key into a chat, an issue or a file;
each key goes only where its step says.

## 1. Buffer API key, saved as a GitHub secret

This lets the GitHub runner read the Buffer drafts a session or PC
automation makes, check them against what you approved, and put only those
exact posts in Buffer's schedule. It never publishes at once, never deletes
and never touches LinkedIn. A check at 06:50 UTC each day fails, and GitHub
emails you, if Buffer refuses the key.

1. Open Buffer (https://publish.buffer.com) and sign in.
2. Click your profile picture (top right) to open the profile menu.
3. Click **API**.
4. Under **Personal Access**, click **New Key**.
5. Name it `growth-makeyourmindup runner`, set the expiry to **1 year**, and
   create it. Copy the key. Buffer shows it once.
6. Open https://github.com/krishanraja/growth-makeyourmindup/settings/secrets/actions
7. Click **New repository secret**.
8. Name: `BUFFER_API_KEY`. Secret: paste the key. Click **Add secret**.
9. Put a reminder in your calendar 11 months from today to make a new key
   and replace this secret the same way (step 7 becomes the pencil next to
   `BUFFER_API_KEY`, then **Update secret**).

## 2. Optional: remove the old engine key from the Claude cloud environment

Sessions no longer use the Control Center engine key. The GitHub runner
holds it as the repository secret `CONTROL_CENTER_ENGINE_TOKEN` (and your PC
keeps a file for Codex runs; [KEY.md](KEY.md)); sessions read Control Center
through its connector. If you once added `CONTROL_CENTER_ENGINE_TOKEN` to the
Claude cloud environment, that is the wrong place for it. If it is not the
engine's `gen1_` key, `growth.py doctor` warns and never uses it. Remove it:

1. In a Claude Code session on claude.ai, open the cloud environment menu in
   the session's title bar and click **Edit**.
2. Under environment variables (or Network secrets), find
   `CONTROL_CENTER_ENGINE_TOKEN` and delete that line.
3. Click **Save**. New sessions start without it.

Do not touch the GitHub secret of the same name: the runner needs it.

## 3. Nothing to create for making

There are no Claude routines to create (Krish, 29 Oct 2026: "I want zero
Claude routines. No Claude schedules of any kind in this architecture").
A new schedule is a GitHub Actions workflow; the ones this engine needs are
already in this repository. Making is done by sessions and the existing
automations on your PC.

If you created a "Growth: make", "Growth: plan" or "Growth: watch" routine
on claude.ai before 29 October, delete it: open **Code**, then
**Routines**, open each one and delete it.
