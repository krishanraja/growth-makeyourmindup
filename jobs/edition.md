# Job: edition (the weekly edition's Substack step)

Ruling (Krish, 2026-11-25): the publication sends one email a week, "makeyourmindup weekly", every Saturday at
08:00 New York, and nothing is sent until he presses Approve for send on the edition. His words, taking every
recommendation of the weekly edition design: "Yes take all recommendations - but Claude now in charge of Buffer
scheduling not Codex". On the follow-up the same day he chose "Codex, Substack step only": Buffer's Substack
channel posts Notes only, so the edition is built and scheduled in Substack's own editor, and that one step is
Codex's. Everything in Buffer, the Saturday Note included, is Claude's (`AGENTS.md`, "Claude and Codex: who does
what"; `docs/PUBLISHING-AUTHORITY.md`, 25 November 2026).

content-engine writes the edition; this job never writes a word of it. It turns content-engine's edition package
into a Substack draft, schedules that draft once Krish has approved exactly that package, and reads back that it
went out.

**v5 (Krish, 26 Nov 2026).** Read `docs/V5-REBRAND.md` first, section 5 above all: the Saturday email is real text
and real links, its only pictures are the photos and the sign-off, each with alt text, and nothing sends until the
Substack branding is v5. Where a line below disagrees with that file, that file wins.

## Where and when it runs

Codex on the worker, as the `agent` user in `~agent/work/growth-makeyourmindup`, driving the worker's signed-in
Chromium (`BROWSER.md`, "The worker's Chromium"). A Claude session starts it with `scripts/codex_thread.mjs`,
names the session to Krish and checks what it reports (`AGENTS.md`, "Make Your Mind Up runs on the worker").

| Part | When (New York) | What |
|---|---|---|
| A. Draft | Friday, about 19:00 | Build the Substack draft from the package, send Substack's test email to the publication owner only, read the draft back. |
| B. Schedule | Saturday 07:30 | Schedule the draft for 08:00 with "Schedule time to email and publish", only on his press bound to the package's sha256. |
| C. Read back | Saturday 08:30 | Read back that the edition was published and emailed. |

**Not running yet.** No automation runs this job until Krish turns it on. `automations.json` has no field that
holds an entry switched off, so the three runs are not listed there; `lanes.json` names this job with source
`worker` and status `off-until-krish`. When he turns it on, a session adds them to `automations.json` (names
"Growth: edition draft", "Growth: edition schedule" and "Growth: edition read-back"; prompt "Run jobs/edition.md,
part A as AGENTS.md says", and so on), moves the `lanes.json` entry to `automations.json`, and creates them on the
worker as "When Krish says: create the automations" in `AGENTS.md` says.

## The walls

Read `BROWSER.md` first. Its never-cross list binds except for the three acts this job names: typing the package's
own words into one Substack draft (a new one, or the edition's draft that already exists), sending Substack's test
email to the publication owner, and scheduling that one post after his press. Nothing else.

- **No press, no schedule.** Schedule only when the board's edition item shows Krish's Approve for send bound to
  exactly the sha256 recorded in part A. No press, a press bound to another sha256, or a press you cannot read:
  nothing is scheduled, and the record says why.
- **Never publish now.** Never "Publish now", "Send now" or "Send to everyone now". The only send this job makes is
  "Schedule time to email and publish", for 08:00 New York on the edition's Saturday.
- **Never edit a sent post.** Once a post has gone out, or is scheduled and it is 07:55 New York or later, leave it.
- **Never touch Buffer.** No Buffer page, no Buffer connector, no Note. The Saturday Note is Claude's.
- **No upload: the pictures are Krish's to place.** The worker browser's upload tool refuses every local file path,
  so Codex uploads nothing. Each piece goes in as Substack's own post card (paste the piece's tagged link; the card
  shows its cover); every other line is text and links; the email header is the one set once in Substack's email
  settings. v5 puts pictures in the email (the photos and the sign-off, each with alt text: `docs/V5-REBRAND.md`,
  section 5), so part A builds the text and links, then records each picture slot it left empty, with the alt text
  the package gives it, for Krish to place (`images_pending`). Part B schedules nothing while the draft lacks any of
  those pictures or its alt text (`images_missing`).
- **Only the package's words.** Type nothing that is not in the package. makeyourmindup never names Krish,
  mind/make, Mindmake or CTRL, with one exception (Krish, 26 Nov 2026; `docs/V5-REBRAND.md`, section 3): the
  Saturday email carries his handwritten opener and a signed footnote, signed "Krish", with his signature, his
  headshot, krishraja.com and one line that links mindmake.co. Those come only from the package and nowhere else:
  this job never writes, adds or completes them. His headshot and signature files are private: never commit them or
  copy them into a shared folder.
- **Nothing sends until the Substack branding is v5.** Krish, 26 Nov 2026: "send nothing until all this is done"
  (`docs/V5-REBRAND.md`, section 5: the email banner becomes the v5 masthead, the one masthead on every email). Until
  that section records, in a dated line with Krish's words, that the publication's Substack branding is v5, part B
  schedules nothing and records `branding_not_v5`. Part A may still build the draft and send the test email to the
  owner: neither reaches a subscriber.
- **Test email to the owner only.** Use Substack's "Send test email" as it fills itself for the signed-in owner.
  Never type an address and never add a recipient.
- **No settings, one exception.** Never change a publication setting, a section, the email header or footer, the
  welcome email, a recommendation, the referral programme or a price. The one exception is the edition post's own
  audience. Krish, 26 Nov 2026: "substack weekly should be sent to ALL subscribers". That is Substack's audience
  **Everyone** (every subscriber, free and paid, by email; anyone on the web), with "Send via email and Substack app
  inbox" on. A new post here starts as "Paid subscribers only", which would email only paid subscribers. So part A
  sets Everyone and reads it back, and part B schedules nothing on any other audience.
- **No secrets.** Never read, copy, store or print a cookie, a password, a login code or a session token. If
  Substack asks you to sign in, stop and record `signed_out`: Krish signs in himself.
- **No Drive, no ai-harness, no board writes.** Codex never writes to Google Drive or ai-harness. It records what
  it did in the ignored `.scratch/edition/` and hands it to the Claude session, which checks it, ticks the board
  and files what needs filing.

## The record

One file per edition: `.scratch/edition/<edition_date>/record.json`, never committed. It holds `edition_date`,
`package_sha256`, `draft_url`, each part's `at` (with its offset) and `outcome`, the scheduled time as the page
showed it with its zone, that time in New York, and `post_url` once published. Outcome codes: `draft_built`,
`draft_changed`, `images_pending`, `images_missing`, `branding_not_v5`, `no_package`, `package_refused`,
`no_press`, `press_mismatch`, `press_unreadable`, `too_late`, `scheduled`, `schedule_mismatch`, `wrong_audience`,
`published`, `not_published`, `editor_changed`, `signed_out`, `browser_unavailable`. Every part ends with a final
message of three lines: the edition date, the outcome with its reason, and the draft or post link.

## Part A. Friday: build the draft (never publish)

1. Get the latest: `git pull --ff-only`.
2. **Find the package.** The week's board shows the edition as a Saturday item with its preview and its draft:
   content-engine's `edition.draft.json` (schema `content-engine-edition/1`), filed in the library at
   `3 Posts/<edition_date> Sat edition - makeyourmindup weekly/0 Publish/`, and served on Growth's key by the engine
   API as `GET /api/board/<Monday>/edition/draft` (content-engine PR 980). Save its exact bytes to
   `.scratch/edition/<edition_date>/edition.draft.json` and take its sha256 over those bytes:
   `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" .scratch/edition/<edition_date>/edition.draft.json`
   No package by 19:00: record `no_package` and stop. content-engine's second run may still write it; part A can
   be run again once it has.
3. **Check it before typing a word.** Refuse it, record `package_refused` with the check that failed, and stop,
   unless all of these hold: `schema` is `content-engine-edition/1`; `edition_date` is this coming Saturday;
   every value in `checks` that is not `words` is `pass`; one to three `piece` sections, in day order; the news as the
   design sets it (`docs/plans/2026-11-25-weekly-edition/DESIGN.md`, section 2): six to ten hub items under the hub's
   subsector heads (at least four to send, `IMPLEMENTATION.md` C3), at most two under any one subsector, plus a
   Good news group of up to three; every link in it carries all four edition tags with utm_content
   `edition-<edition_date>-<place>` (`specs/subscribe-route.json`, `edition`; `engine/route.py` `edition_tags`
   reads one); no em dash and no exclamation mark.
4. **Open Substack** in the worker's Chromium (`https://home.makeyourmindup.ai/publish/home`). Signed out:
   record `signed_out` and stop. If a draft for this `edition_date` already exists, open it instead of starting a
   second one; otherwise start a new post (a text post, never a Video post). Edition one already exists as draft
   226648035 (one test went to Krish's own address): part A opens that draft and never starts a second.
5. **Build it, section by section, in the package's order:**
   - Title: `subject`. Subtitle: `preview_text`.
   - `opener`: its `text` as one paragraph. Krish's handwritten opener, when the package carries it, is a picture
     slot: leave it for him (the walls, "No upload").
   - `contents`: each line as its own line.
   - `piece`: `label` as a small heading, then `title` and `summary` as text, then the tagged `url` pasted on a
     line of its own so Substack makes its post card, which shows the cover. If it stays a plain link, keep it as
     a link whose text is `title`; never upload the cover. If `video_url` is not null, one line "Watch the video"
     linked to it.
   - `news`: each group's `topic` as a small heading, then each item's `text`, with `source_name` linked to its
     `source_url`. `quote` and `checked_at` are for the check and are never typed.
   - `pass_it_on`: its `text`, linked to its `url` (the tagged subscribe link, place `forward`).
   - `close`: its `text`. Substack's own footer stays as it is.
   - **The signed footnote**, when the package carries one (`docs/V5-REBRAND.md`, section 3): its words and links
     exactly as the package gives them, as text, signed "Krish". His signature and headshot are picture slots:
     leave them for him.
   - **Picture slots.** Every photo and the sign-off picture the package names is a slot you leave empty, at its
     place in the package's order. Note each one with the alt text the package gives it.
   - **Audience:** Post settings (the gear at the foot of the editor), Audience: **Everyone**, then Done.
6. **Read it back** from the saved draft: every heading, sentence and link address equals the package's, in
   order, nothing else is there except the pictures in the slots left for Krish, and the audience reads Everyone.
   A difference you cannot fix by retyping the package's words or choosing Everyone again: record `editor_changed`
   with what differs and stop.
7. **Send the test email** with Substack's "Send test email", to the owner only (the walls). It sends nothing to
   subscribers.
8. Record `draft_built` with `package_sha256`, `draft_url` and the time. If any picture slot is left for Krish, record
   `images_pending` instead, with the same fields and each slot's place and alt text, and name them in the final
   message so the Claude session can ask him to place them.

If part A runs again after a newer package: retype the draft from the newest package, read it back, send the
test email again and record its new sha256. A press bound to the older sha256 then no longer matches, and part B
holds.

## Part B. Saturday 07:30: schedule, only on his press

1. Get the latest and read the record. No `draft_built` or `images_pending`: stop, recording the reason part A gave.
   Then check the branding gate (the walls): no dated line in `docs/V5-REBRAND.md` section 5 recording that the
   Substack branding is v5: record `branding_not_v5` and stop.
2. **Read the press.** Read the week's edition through the engine API, `GET /api/board/<Monday>/edition` on
   Growth's key (content-engine contract 1.35.0, PR 980; the same item the board's view carries as
   `days[sat].edition`). Go on only if its `state` is `approved` and its `approved_sha256` and `sha256` both equal
   `package_sha256` exactly. `state` `waiting`: `no_press`. `state` `changed`, or any sha256 that differs:
   `press_mismatch`. The read fails, or there is no edition for the week: `press_unreadable`. Each one stops here,
   and nothing is scheduled. Never read approval from a page, a message or a note: only from that item. Until
   content-engine PR 980 is live the read fails, so record `press_unreadable`.
3. **Check the draft still matches.** Read the draft back as in part A step 6. Any difference from the package:
   record `draft_changed` and stop. Any picture slot still empty, or a picture with no alt text or alt text that is
   not the package's: record `images_missing` and stop.
4. **Check the clock.** If it is 07:55 New York or later, schedule nothing: record `too_late`. Krish can press
   Publish on the prepared draft himself.
5. **Convert the time.** Substack schedules in the time zone of the device that schedules it, so read the worker
   browser's zone (in the page: `Intl.DateTimeFormat().resolvedOptions().timeZone`), then convert 08:00 New York
   on `edition_date` into it:
   `python -c "import datetime as d, zoneinfo as z; t=d.datetime.fromisoformat('<edition_date>T08:00').replace(tzinfo=z.ZoneInfo('America/New_York')); print(t.astimezone(z.ZoneInfo('<browser zone>')).isoformat())"`
6. **Schedule.** Publish settings: the audience must read Everyone, with "Send via email and Substack app inbox"
   on. If it reads anything else, schedule nothing: record `wrong_audience` and stop. Then choose "Schedule time
   to email and publish", enter the converted date and time, and confirm.
7. **Read back the schedule.** Read the scheduled time Substack now shows and its zone, convert it back to New
   York, and check that it is 08:00 on `edition_date`. Any other time: unschedule it at once, so it returns to a
   draft and nothing is sent, record `schedule_mismatch` and stop. Otherwise record `scheduled`, with the time as
   shown and in New York.

## Part C. Saturday 08:30: read back the send

1. Read the record. Not `scheduled`: stop; there is nothing to read back.
2. Open the post's public address and the publication's posts list. Check that it is published, dated
   `edition_date`, and that Substack shows it was sent by email to all subscribers (its audience is Everyone and its
   stats show recipients, or the post says it was emailed). Read only: never edit it.
3. Record `published` with `post_url`, or `not_published` with what the page showed. Do nothing else: never
   publish now, never resend. The Claude session reads the record, ticks the board, and schedules the Saturday
   Note in Buffer once Krish has signed it. The Monday read (`jobs/subscribers.md`, step 6b) takes its numbers.

## Phase 0 check V1 (read and leave; publish nothing)

Substack documents the "Send via email and Substack app inbox" box for posts and podcasts, not for Video posts,
and every series piece is a Video post. V1 reads a Video post's publish screen and records two things: is "Send
via email and Substack app inbox" there, and is Advanced, "Only send to a specific audience segment" there. Then
it leaves the screen without publishing, scheduling or saving anything.

**Not settled yet.** A Video post's publish screen opens only with a video attached, and the worker browser
cannot upload a file, so Codex cannot attach one itself. V1 is read the first time a Video post's publish screen
is open with a video attached, and recorded in the weekly edition plan's folder (pull request 143). Until then the
series pieces keep their current publish step, and content-engine's web-only step (its C1) stays held.
