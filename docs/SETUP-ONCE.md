# Set up once

The steps only Krish can do, each done once. They are lane L3 in
[LANES.md](LANES.md). Never paste a key into a chat, an issue or a file;
each key goes only where its step says.

## 1. Buffer API key, saved as a GitHub secret

This lets the GitHub runner read the Buffer drafts the routines make, so it
can check them against what you approved. It never posts with it.

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

Sessions no longer use the Control Center engine key. Only the GitHub runner
holds it, as the repository secret `CONTROL_CENTER_ENGINE_TOKEN`
([KEY.md](KEY.md)); sessions read Control Center through its connector. If
you once added `CONTROL_CENTER_ENGINE_TOKEN` to the Claude cloud
environment, remove it:

1. In a Claude Code session on claude.ai, open the cloud environment menu in
   the session's title bar and click **Edit**.
2. Under environment variables (or Network secrets), find
   `CONTROL_CENTER_ENGINE_TOKEN` and delete that line.
3. Click **Save**. New sessions start without it.

Do not touch the GitHub secret of the same name: the runner needs it.

## 3. If needed: create the three routines

Skip this if the routines `make`, `plan` and `watch` already exist. Each one
runs in a fresh cloud session and follows one file in `routines/`.

1. On claude.ai, open **Code**, then **Routines**, then **New routine**.
2. Repository: `krishanraja/growth-makeyourmindup`, branch `main`.
3. Connectors: turn on **Canva**, **Buffer** and **Control Center**. Leave
   every other connector off.
4. Text and schedule (times in UTC; if the page asks for a time zone, pick
   UTC):

| Name | Text (paste exactly) | Schedule | Cron |
|---|---|---|---|
| Growth: make | `Clone krishanraja/growth-makeyourmindup (main) and follow routines/make.md` | every day 06:00 UTC | `0 6 * * *` |
| Growth: plan | `Clone krishanraja/growth-makeyourmindup (main) and follow routines/plan.md` | Sundays 05:30 UTC | `30 5 * * 0` |
| Growth: watch | `Clone krishanraja/growth-makeyourmindup (main) and follow routines/watch.md` | every day 07:30, 12:30 and 17:30 UTC | `30 7,12,17 * * *` |

5. Save each one. If a routine can take only one time a day, make three
   `watch` routines, one per time, with the same text.
6. Read back: the routines page lists all three (or five, with three
   `watch`) with their next run. Each text must match the table exactly,
   because the cost meter knows a routine only by that text.

A routine never publishes, schedules, sends, deletes or spends. Its walls
are written at the top of its file in `routines/`.
