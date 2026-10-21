# Weekly live channel audit

## Accepted brief and authority

Ruling (Krish, 2026-10-21): weekly browser audits on the actual pages.
Autonomously edit existing post titles, captions, descriptions and links.
Fix broken profile links and align existing subscription links. Creative
replacement and re-upload, bio, positioning and pinned-content changes
require approval. This supersedes the older blanket read-only browser rule
only for these operations; it grants no posting, messaging, spending,
deletion, feature activation, audience or account-setting authority.

The audience is senior business leaders judging AI's commercial impact who
are themselves publicly visible on the topic. Relevant judgment and public
participation matter more than raw follower counts. Subscriber growth from
useful shared work remains the North Star; no paid boosts.

The first pass covers profiles, pinned/Featured content and the last 30 days.
Weekly passes cover new posts, verify repairs and revisit older posts still
getting attention. Checkpoint per account, only after complete pagination.
Keep an incomplete account's original window so blocked posts cannot vanish.

WHY NOW: Krish said, "Right now I feel like I'm just recording once and
posting everywhere and closing my eyes and I'm not respecting each channel
that I'm posting to. I think that's the first step."

WHAT I ALMOST GOT WRONG: adding distribution before inspecting and repairing
the channel-specific packaging of work already being published.

CLEAR WIN: actual live-page coverage with observable metadata repairs,
verified subscription destinations, concrete approval items and explicit
access gaps. A completed checklist is not evidence of subscriber growth.
Do not infer audience quality, causation or performance from public counts.

## Execution and schedule

Run jobs/channel-audit.md. The existing `conversion` weekly slot owns it;
jobs/conversion.md delegates here before its broader read-only checks.
The audit's selected local schedule is Saturday at 12:00 Europe/London.
Other job schedules and the daily human time budget stay unchanged. Count
approval/review effort in that budget; unattended inspection is not Krish's
manual work. The baseline may need multiple resumable passes.

The Codex heartbeat follows this chat and reads this repository's local
checkout. It needs this host available and a browser tool with the authorised
accounts signed in. Scheduling proves only that a wakeup exists, not access
or successful execution. Never replace a browser audit with a feed, scraper,
cached corpus, API read or synthetic fixture. Those may corroborate it.

Before the first browser action create `.scratch/channel-audit/run.lock`
with exclusive creation and keep it until the session ends (finally cleanup).
An existing lock means inspect the owning run, not delete it and start over.
Persist each repair intent before Save. Maximum one Save attempt per intent;
after timeout or interruption reopen the field and reconcile. Never issue a
second Save to find out whether the first worked. Record held coverage and
partial progress on interruption. Resume through the same job and CLI.

## Local executable guard and receipts

`growth.py audit` is a local guard and journal for the browser operator; it
does not drive a browser, authenticate or make network calls. It validates
supplied observations. It cannot prove that those observations were honest.
Use real browser readback as the independent outcome proof.

All output and state paths must be inside ignored `.scratch/`. No live data
in fixtures or Actions output. State is one canonical file:
`.scratch/channel-audit/state.json`, holding repairs and per-account coverage.

Commands, run from this checkout:

```powershell
python growth.py audit plan .scratch/channel-audit/change.json --out .scratch/channel-audit/plan.json
python growth.py audit begin .scratch/channel-audit/begin.json --out .scratch/channel-audit/intent.json
# Perform only the authorised field edit in the browser, then reload.
python growth.py audit reconcile .scratch/channel-audit/readback.json --out .scratch/channel-audit/receipt.json
python growth.py audit checkpoint .scratch/channel-audit/coverage.json --out .scratch/channel-audit/checkpoint.json
```

`plan` input: channel, exact configured account_url, target_url, surface
(`post` or `profile`), field, exact before/after strings, reason, success_check
and evidence `{method: "browser", url, excerpt, observed_at}`. Evidence must
be from this target and at most two hours old. The operator must set
owner_verified, meaning_preserved, voice_checked, claims_checked and
field_editable only after actually checking them; absent/false means held.
The before string must appear in the literal page excerpt.

For a link, add destination browser evidence with requested_url equal to the
proposed link, the final URL, excerpt, observed_at, usable and purpose_match.
Preserve working query/referral parameters and test the exact resulting URL.
An inaccessible page is not proof of a broken link. Profile subscription
alignment is limited to the verified owned /subscribe route, with
link_purpose `repair_broken` or `align_subscription`. Other profile-link
destinations need manual review; this guard deliberately holds them.

`begin` input is `{change: <plan input>, current: <fresh browser evidence>}`.
Current also includes account_url, owner_verified, field and exact value.
It must still equal before. The repair ID and payload hash bind account,
post, field and before/after. Protected fields never become autonomous
through a supplied `approved` flag. Approved creative changes use a separate
exact-payload review, outside this metadata-only command.

`reconcile` input is `{repair_id, readback}`; readback includes the browser
evidence fields plus field, exact value and reopened: true. It must follow
the recorded intent. Matching after yields verified. A mismatch stays held.
Verified repeats with unchanged after are skipped; unresolved repeats stop.

`checkpoint` input includes channel, account_url, complete,
pagination_complete, profiles_checked, pins_checked, blockers, window_start
and window_end. All completion flags must be true and blockers empty.
Window end is the captured run-start timestamp; window start is that
account's last complete checkpoint, or run start minus 30 days. Partial runs
must save coverage separately without calling checkpoint. No target URL
or hashtag quota can prove full coverage.

## Channel checks and current guidance

Check actual account features, full text and destinations before repairs.

| Channel | Inspect on live pages |
|---|---|
| YouTube | Hook/title match, full long description, matched article and subscription path, Short continuation, subtitles, thumbnail and opening/closing frames |
| Instagram | Full Reel/carousel caption, profile links, pinned posts, crop and subtitle safe areas, useful save/share payoff |
| TikTok | Full caption, opening promise, subtitle/crop fit, profile-link availability and a realistic next step |
| X | Full post and media, relevant destination, profile link, pin freshness; never delete/repost to bypass edit restrictions |
| LinkedIn | Full post before truncation, native reader value, Featured journey and subscription destination; no new comments |
| Substack | Profile/About consistency, subscribe landing, article/video crosslinks and related reading; article-body, welcome or offer rewrites need approval |

YouTube distinguishes Shorts from long video links: URLs in Shorts
descriptions/comments are not clickable; a related-video link or a channel
profile link can supply continuation. Confirm the account feature and the
exact related asset before recommending it. Adding/removing a related-video
association is not assumed to be a text-link edit and needs approval.
Source checked 2026-10-21:
https://support.google.com/youtube/answer/13748639?hl=en

YouTube says titles, thumbnails and descriptions matter more for discovery
than tags, which usually play a small role. Do not fail every post for
missing hashtags. Source checked 2026-10-21:
https://support.google.com/youtube/answer/146402?hl=en

Recheck current first-party guidance when making a platform-specific claim.
Historical knowledge/corpus audit material is preserved evidence, not live
truth or authority to apply its recommendations.

## Reporting and rollback

Return coverage per account (complete/partial/blocked), exact fixes with
before/after and readback, approval items, and what could not be inspected.
Keep the original value for rollback. Before restoring it, verify that the
current live value still equals the engine's after; otherwise hold for owner
review. No automatic reversal after a human edit.

Control Center is the unified action list, not a second implementation
target. This repository prepares its handoff only during development;
scheduled reporting uses its existing routes. Do not mislabel standing-
authority metadata fixes as newly approved go-lives or post false closing
events. Protocol changes need a downstream owner, never an ad hoc new field.
