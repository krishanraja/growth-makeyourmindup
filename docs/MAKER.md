# The maker: tomorrow's drafts from the ideas and mocks Krish approved

The maker is a GitHub Actions job in lane L0 (`.github/workflows/maker.yml`,
`engine/run/maker.py`, `growth.py run maker`). Every day at 04:30 UTC, just
before or just after midnight in New York, it makes the next New York day's
posts from the ideas and mocks Krish approved in the week's mix plan
(`docs/MIX.md`), saves each one in Buffer as a draft, and hands it off with
its review. Release (`release.yml`) then schedules each post about an hour
before it is due, only while every gate still passes
(`docs/CONCEPT-MANIFEST.md`). Without the maker, nothing turned an approved
idea into a post unless a session did it.

It moves the North Star by keeping Instagram, YouTube Shorts, TikTok and X
at three or four posts a day from the moment Krish says yes, with no session
and no PC.

## What it does, in order

1. **Reads his authority from Control Center.** His decisions, the plan in
   force and each part's ideas, read back by digest with the same code
   release uses (`autorelease.week_state`). His no on the week makes
   nothing. A plan he has not answered, or one that cannot be trusted, makes
   nothing.
2. **Reads the week's slots.** Which idea goes on which channel at which
   time, from the slots record the handoff keeps beside the plan (below).
   They are checked against what he approved before they are used: every
   idea's channels must be exactly the channels he approved for it, and the
   plan lines he read (how many slots a day, which lanes, how many have a
   ready idea) must be the lines these slots make. Anything else holds the
   whole day loudly as `slots_differ_from_plan`.
3. **Picks the next New York day's slots** on Instagram, YouTube, TikTok
   and X. Never LinkedIn. An idea he did not approve, or stopped, holds. An
   idea already made on that channel this week (in the week's index, or a
   post in Buffer that carries its claim) is `already_made`, so a second run
   makes nothing new.
4. **Fetches the mock files.** Only the exact files he approved, found by
   their hash in the week's mock manifest and downloaded from Google Drive.
   A file whose bytes do not hash to its approved sha256 holds as
   `mock_hash_mismatch`; a file the manifest does not name holds as
   `mock_file_missing`. A post takes the files its format takes: every
   picture for a carousel, the video for YouTube (never a still), the first
   picture (the cover) for a single image, none for a text post.
5. **Writes the words** with the Anthropic API (model `claude-sonnet-5-5`),
   from the idea and its claim only, in the account's own voice
   (`docs/ACCOUNT-VOICE.md`: personal on X and TikTok, the publication on
   Instagram and YouTube). The words must carry the claim word for word,
   pass content-engine's copy lint (no names of Krish, no em dashes), never
   ask for the share, and declare who would send the post to whom and why.
   A draft that fails is rewritten once with the reasons, then held.
6. **Reviews the words blind.** A separate Anthropic call sees only the
   post's format, its words and its files' blind names, under the blind send
   test lens (`social/share.json`). Its answer must name the receiver and the
   job the post declares, and is judged again at the draft's own digest by
   `spec.review_reason`, the judge release uses. This review is
   maker-attested: the engine reviews its own words with a second, blind
   call. It is not an independent judge.
7. **Saves the draft and hands it off.** The post is saved in Buffer as a
   draft (`saveToDraft: true`, no due time), read back and rebuilt from
   Buffer exactly as release rebuilds it, then recorded in Control Center by
   the handoff's own code, in the same run: its review at the post's own
   hash and the day's index that release reads.

Run by hand (`workflow_dispatch`), it is a dry run unless deliver is ticked:
it reads, writes and reviews the words, and saves nothing and records
nothing. By hand it may also name the New York day to make, but only today
or tomorrow there, so a yes given after the night's run can still be made
that morning.

## What it never does

- Schedule, publish, queue or delete a post. Only release schedules, and
  only what passes every gate.
- Touch LinkedIn, or any channel but this engine's pinned Instagram, YouTube,
  TikTok and X channels (`engine/buffer_channels.py`).
- Use a mock file that is not one he approved, byte for byte.
- Make a second draft of one idea on one channel in a week.
- Change the words or digest of anything he approved. The slots and the mock
  manifest are records of their own, kept beside the plan.
- Write words, ids, links or keys to the log. The log is counts and reason
  codes only; nothing is uploaded.

## What it reads

- **Control Center:** his decisions; the plan in force
  (`makeyourmindup:mixplan:<week>:<n>`) and each part's report; the week's
  slots record (`makeyourmindup:mixslots:<week>:<plan key>:<i>`); the week's
  mock manifest (`makeyourmindup:mocks:<week>:<plan key>:<i>`); the week's
  derived index (`makeyourmindup:derived:<day>:<n>`). The plan key is the
  first 12 characters of the hash of the plan's part digests, so both
  records belong to exactly the plan he decided on (`engine/run/cc_records.py`).
- **Google Drive:** each approved mock file, by its file id, from
  `https://drive.usercontent.google.com/download?id=<FILE_ID>&export=download`.
  The week's files sit in the shared `mocks/<ISO week>/` folder, each named
  `<sha256>.<ext>`. Buffer is given the same link, so release downloads and
  hashes the same bytes when it rebuilds the post.
- **Buffer:** this engine's channels, to find what is already made, and each
  new draft, read back.
- **The repository:** `mix.json`, the social records (formats, channels,
  copy lint, share rules) and nothing on Krish's PC.

## Where the slots and the mock manifest come from

The handoff writes both when the week's mix plan is dispatched
(`growth-mix-plan`, `engine/run/handoff.py`). The slots come from the plan
itself. The mock manifest comes from the dispatch's optional `mock_files`
field, `{sha256: Drive file id}`, sent by whoever puts the mocks in Drive.
Every key must be one of the plan's own mock hashes; an idea with a mock
file it does not name is counted as `mock_file_missing`, and the maker holds
it.

A plan dispatched before these records existed gains them by being sent
again, unchanged, with `mock_files` and `"records_only": true`. The runner
then writes the slots and mock records and nothing else, and refuses
(`records_only_plan_not_in_force`) unless every part and the version it
rebuilds are already the plan in force in Control Center, so no new version
can withdraw his yes and his digests never move. Run by hand as a dry run
with `records_only`, it reads Control Center and says whether the plan is in
force without writing anything.

## Its secrets

GitHub repository secrets, read only on the runner:

- `CONTROL_CENTER_ENGINE_TOKEN`: reads his decisions and the week's records,
  and records each draft's review through the handoff.
- `BUFFER_API_KEY`: reads this engine's channels and saves each draft.
- `ANTHROPIC_API_KEY`: writes the words and runs the blind review. Without
  it the job holds loudly as `anthropic_key_missing` and makes nothing.

## When it holds

Every hold has a code in the run's summary. A hold that means a person must
look (a slots record that does not match the plan, a missing mock manifest,
a draft saved but not handed off, a draft whose files Buffer changed) fails
the run, so GitHub emails Krish. A hold on one post (its words, its review,
one mock file) leaves the rest of the day to be made.
