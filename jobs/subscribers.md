# Job: subscribers (the weekly Substack read)

Ruling (Krish, 2026-11-12): the engine reads subscribers every week and judges posts by subscribers, not
engagement. This job is the weekly read. The automation "Growth: subscribers" (`automations.json`, Mondays
06:15 New York) runs it on Krish's PC, in his signed-in browser, because Substack has no public API. Follow
it exactly. It reads; it never changes anything in Substack.

Read `BROWSER.md` first. The walls for this job:

- Read only. Never change a setting, a page, a post, a Note, an email, a recommendation or a subscriber.
- Never export or open a subscriber list, an email address or a subscriber's profile. Counts only.
- Never read, copy, store or print a cookie, a password, a login code or a session token. If Substack asks
  you to sign in, stop and record `signed_out`: Krish signs in himself.
- Every number is one you read on the page today, exactly as shown. Missing is null with its reason, never
  zero and never an estimate.
- The capture holds private figures. It stays in the ignored `.scratch/substack/`; never commit it.

## Steps

Run each command on its own line in PowerShell (`python`, or `py` if that is missing).

1. Get the latest: `git pull --ff-only`.
2. Make this week's capture file:
   `python growth.py run subscribers template`
   It writes `.scratch/substack/week-<Monday>.json` for last week, Monday to Sunday in New York, and prints
   its path. Fill that file in the steps below; keep every field it has and add none.
3. Open the Substack dashboard for the publication in the signed-in browser
   (`https://home.makeyourmindup.ai/publish/home`), then its subscriber stats. Write down the address of
   each page you read; you need it below. If the browser is not signed in to Substack as Krish, set
   `"captured_at"` (now, with its offset), `"read": "not_taken"` and
   `"not_taken": {"code": "signed_out", "detail": null}`, save, and go to step 9. Do the same, with its own
   code, whenever a later step cannot be done: `browser_unavailable`, `substack_unreachable`,
   `page_changed`, `not_settled` or `window_unavailable`, and put back `growth_sources` null and `items`
   empty, so nothing half read is recorded.
4. **New subscribers by source.** Open the view that shows new subscribers by source (Substack calls it
   growth by source or growth sources). Choose the window **Monday to Sunday of last week**, the dates in
   the file's `week_of` and the six days after it: a custom range if the page offers one; otherwise the
   preset whose dates the page shows as exactly those days; otherwise "Last 7 days". Wait until the
   selected window's label and the table under it agree: the label changes before the old table goes
   (F54). Then fill `growth_sources`:
   - `kind` `substack_growth_sources`, `metric` `new_subscribers`, `captured_at` now with its offset,
     `source_url` the page's address;
   - `window`: `label` exactly as the page shows it, `start` and `end` the first and last day the page says
     it covers (`YYYY-MM-DD`), `tz` `America/New_York`;
   - `settled`: `label_seen` the label you saw above the values you copied, `values_seen_after_label` true;
   - `rows`: one per source, `source` exactly as shown, `new_free` and `new_paid` as shown (null where a
     column shows nothing). Where the page shows a parent and its child category (Substack, then Notes
     under it), record the child under its own label and the parent with the child's count taken off, so
     every subscriber is in one row;
   - `total_new_free`: the total the page shows, or null if it shows none. The rows must add up to it.
   If the page offers no window that covers last Monday to Sunday, record the one it does offer exactly:
   the ingest step decides whether it counts. If the view is not there, record `page_changed`; if the
   label and values never agree, `not_settled`.
5. **Total subscribers.** From the dashboard's subscriber count, fill `total_subscribers`: `value` (all),
   `free` and `paid` as shown, `source_url` the page's address, `reason` null. If it is not shown, `value`,
   `free` and `paid` null and `reason` saying what the page showed.
6. **Per post and per Note.** Check whether Substack shows new subscribers for each post or each Note
   (the post's stats, the Notes stats). Set `items_view`:
   - `per_item` if it does: add one `items` row for each post and each Note published last week, with
     `kind` (`post` or `note`), `url` (the post's or Note's own address on Substack), `window_label` (the
     period the page says the number covers, such as "All time") and `new_free` and `new_paid` as shown;
   - `category_only` if it shows subscribers only by source or category: leave `items` empty;
   - `not_checked` if you could not check: leave `items` empty.
7. Set `"captured_at"` (now, with its offset), `"read": "taken"` and `"not_taken": null`, and save.
8. Check it without writing:
   `python growth.py run subscribers ingest .scratch/substack/week-<Monday>.json`
   If it prints `"valid": false`, fix the field it names from what the page showed. Never change a number
   to make it pass: if the page does not add up, record what it shows and null the part it does not show.
9. Record it:
   `python growth.py run subscribers ingest .scratch/substack/week-<Monday>.json --write`
   It updates the North Star state line in `NOW.md` through the same code as `growth.py run northstar`
   (when that loses no newer or measured reading) and appends the week's reading to
   `lists/northstar-history.jsonl`, once. A read not taken is recorded as unknown with its code, never as
   zero. The total, the sources and the per-post rows stay in `.scratch/substack/weekly.jsonl`.
10. Commit and push only those two files, to `main`:
    `git add NOW.md lists/northstar-history.jsonl`
    `git commit -m "subscribers: weekly Substack read for the week of <Monday>"`
    `git push`
    If nothing changed, there is nothing to commit. If it cannot push, put the new ledger line in the final
    message so the next session commits it.
11. Final message, three lines: the week read; its new subscribers (all sources and organic, or why not
    counted) against the week's target and the urgency; and whether Substack shows subscribers per post or
    per Note.

## What reads it

The North Star line in `NOW.md` is what Control Center and every session read (`docs/NORTH_STAR.md`). The
Measurement engine (`jobs/measurement.md`) and the weekly report (`jobs/report.md`) read the ledger and
`.scratch/substack/weekly.jsonl`. The classification of sources into organic, unattributed and paid counts
only once Krish approves `invariants/sources.json`; until then the line carries the all-source count in its
source and says the organic count awaits his approval. The daily numbers job (`jobs/numbers.md`) still
reads this week's progress; this job reads the whole week once it has ended.
