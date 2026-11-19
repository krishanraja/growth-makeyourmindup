# ManyChat build sheet: the keyword-DM test (19 Nov 2026)

For `docs/plans/2026-11-13-keyword-dm-test.md`, step 4 of its "Setup", and `docs/GET-GOING.md` Step 0.4. Krish asked on
19 Nov 2026 to "get moving" on it. This sheet is what Codex builds in ManyChat's own builder in the worker's Chromium,
or what Krish builds by hand from it. Nothing here goes live on its own: each automation is switched on only with its
Reel's approved go-live, and the trial's paid plan is his yes on the exact amount (`wall: spend`).

## Before building (each a read, or his click)

1. ManyChat workspace for @makeyourmind.up exists and Instagram is connected **as makeyourmind.up**. Connecting it is an
   account permission change: his click.
2. Instagram, Settings > Messages and story replies > Message controls > Connected tools: "Allow access to messages" on.
   A setting change: his click.
3. The plan in use allows an Instagram comment keyword trigger. The trial's end date and the following plan's monthly
   price are read and put on his list before the trial ends.

## One automation per keyword-arm Reel

| Field | Value |
|---|---|
| Name | `BRIEF <piece id> <Reel date YYYY-MM-DD>` |
| Trigger | Instagram: user comments on a post or Reel. **Specific post: this Reel only** (never "any post") |
| Keyword | Comment contains `BRIEF` (any case). No other keyword |
| Public comment reply | **Off** |
| Message 1 (DM, from @makeyourmind.up) | `Here are the three things to do tomorrow, from this week's piece: {ARTICLE_LINK}` |
| Message 2 (same DM) | `Want the next one in your inbox? {SUBSCRIBE_LINK}` |
| Follow-ups, sequences, delays, buttons asking for email, tags that start other flows | **None** |
| Status | Draft until the Reel's go-live; then Active |

`{ARTICLE_LINK}` is the Reel's own piece, built with `growth.py link` and tagged
`utm_source=instagram&utm_medium=dm&utm_content=dm-brief-<piece id>`. `{SUBSCRIBE_LINK}` is
`https://home.makeyourmindup.ai/subscribe?utm_source=instagram&utm_medium=dm&utm_content=dm-brief-<piece id>`.
Never one shared link across Reels: an older Reel's commenters never get a newer piece.

The keyword-arm caption ends with the approved line "Want the three things to do about this tomorrow? Comment BRIEF and
we'll send them to you." in place of "link in bio", set at go-live. Bio-arm Reels keep the newsletter line.

## Proof before day one

Comment `BRIEF` on the first keyword Reel from Krish's own account; read the DM back word for word, open both links and
confirm they land with their UTMs. Record it in `.scratch/ig/` and tick Step 0.4 only then. The two-week clock starts
the Monday after.

## The arms ledger (one row per Reel)

piece id, arm (keyword or bio), posted time, views (organic, Ad label excluded), comments with BRIEF, DMs sent (ManyChat's
own count), link clicks, tagged subscribers (GA4 `sign_up` on its `utm_content`, and Substack's new-subscriber emails).
