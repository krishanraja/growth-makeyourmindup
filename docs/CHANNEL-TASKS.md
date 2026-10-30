# Channel tasks: who runs which, and the weekly loop

Owner: Growth. The seven tasks are defined once in krishanraja/ai-harness
`contract/channel-tasks.md` (Krish, 2026-10-30); this file keeps only the
mapping and this engine's loop. `crew/registry.json` carries each specialist's
`tasks` with what each accomplishes here, and `engine/run/invariants.py`
(`load_registry`) refuses an unknown task, an outcome under a sentence, or a reel
script on a specialist that makes no short video.

The tasks serve the publication North Star (new subscribers a week from organic
posts and shares, zero paid), never follower counts. Every idea, hook, caption,
test and plan names the leading signal it moves.

## Who runs which

The seven are a starting set, not a template. `crew/registry.json` says, for
each specialist and each task it runs, what that task accomplishes on that
channel for this publication; `tests/test_crew.py` refuses a vague outcome or the
same words on two specialists. Read the registry for the full sentences; this
table is the summary.

| Specialist | Channels | Runs | Leading signal |
|---|---|---|---|
| meta | Instagram, Facebook | all but profile-audit | Sends per reach, then profile visits to the subscribe link |
| youtube | YouTube Shorts | all but trend-scan and profile-audit | Short-to-long clicks, then subscribers |
| tiktok | TikTok (personal) | all but profile-audit | Watch time, then profile visits |
| x | X (personal) | platform-truth, idea-bank (receipts), caption-set, trend-scan, channel-plan | Profile and link clicks at 48 hours |
| threads | Threads (personal) | platform-truth, idea-bank, caption-set, channel-plan | Replies and follows, baseline for two weeks |
| linkedin | LinkedIn (his click) | platform-truth, idea-bank, caption-set, channel-plan | Featured clicks and comments from target titles |
| substack | Substack Notes | platform-truth, idea-bank, caption-set, channel-plan | Subscribes attributed to a Note |
| channel-auditor | all eight accounts | profile-audit | Every account points to the subscribe path |

Dropped on purpose:
- trend-scan on YouTube, because Shorts are cut from the week's full videos;
- trend-scan on Threads, because its first two weeks are a baseline;
- trend-scan on LinkedIn, because those posts are his own click with no quota;
- trend-scan on Substack, because Notes name published work.

Ideas here come from published pieces, because every claim must come from one.
They never come from trends alone.

The channel auditor already owns every profile pass (docs/CHANNEL-AUDIT.md), so
profile-audit stays with it. The canva-studio lane, the engagement lane, the
What-Works Analyst and the Send-Test Reader keep their jobs: Canva makes what a
task drafts, the Send-Test Reader judges the picked hook and caption blind, and
What-Works reads the results.

Where they run:

- trend-scan and idea-bank: jobs/radar.md, weekly.
- reel-script and caption-set: inside daily-pack production. The 5 hooks and 5
  captions are the alternatives the creative review records before a go-live.
- platform-truth and channel-plan: jobs/report.md, weekly. Any card rule change
  goes to Krish as a proposal.
- profile-audit: jobs/channel-audit.md, Saturdays.

## The weekly loop

1. **Gap.** Open with `X of Y, U-n, short by Z` against this week's ladder
   (25 for the week of 26 October, 86 for 2 November, 162 for 9 November, 271
   for 16 November). An unread Substack source report means not measured, U4,
   and reading it comes first.
2. **Contribution.** Split the gap across channels by last week's subscribes
   attributed to each source. While attribution reads zero everywhere, split
   evenly and say so.
3. **Leading signal.** Use the column above.
4. **Tasks.** Choose the week's mix so each channel's signal moves. At U3 and
   above, volume rises to `intensity.json` bounds, inside every wall.
5. **Review.** Read at 24 hours, 72 hours and 7 days against the channel's own
   median, keep or kill through What-Works, and record his declines where the
   next draft reads them. The check-in asks whether the plan is on track.

Nothing here posts, sends, spends or changes a profile. Publishing authority is
docs/PUBLISHING-AUTHORITY.md, unchanged.
