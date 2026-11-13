# Test: comment a keyword, get the three things in a DM (Instagram), drafted 13 November 2026

Krish asked for this test on 13 November 2026, after the @adilet.fndr teardown (`docs/research/2026-11-12-adilet-fndr-teardown.md`). It is planned, not started: `experiments.json` holds it as `keyword-dm`, so the engine puts "Decide whether to start the keyword-dm experiment" on his list in Control Center. Nothing here posts, sends, spends or changes an account.

## Why

Instagram Reels cannot carry a clickable link, so today a Reel can only say "link in bio". That is two extra steps between a viewer and the subscribe page, and the week of 2 November brought 1 new subscriber against 86. The teardown's one mechanic that turns views into subscribers, not just followers, is: ask viewers to comment one word, and reply to each with a DM that carries the link. The comments also tell Instagram the Reel is worth showing.

## Hypothesis

On @makeyourmind.up Reels, a "Comment BRIEF" call to action that replies with a DM carrying the piece's "3 things you can do tomorrow" and the tagged subscribe link brings at least twice the new subscribers per 1,000 views of the "link in bio" call to action, with no rise in unsubscribes or reports.

## First, a ruling only Krish can make

`research.md`, hard rule 5: "No mass outreach, no automated DMs and no auto-follow." This test sends an automated DM, but only to a person who commented the keyword, once, as a reply. That is how Meta's own messaging rules allow comment replies through its approved tools. It is still an automated DM, so the test needs his ruling, recorded in the commit that starts it:

> Ruling (Krish, YYYY-MM-DD): a single DM reply to someone who commented the keyword on that post is allowed; every other automated DM stays forbidden.

Without that ruling, the test does not start.

## The two arms

| | Keyword arm | Bio arm (today) |
|---|---|---|
| Caption ends with | "Want the three things to do about this tomorrow? Comment BRIEF and we'll send them to you." | "Get the next one in your inbox: link in bio." |
| What follows | One DM to each person who comments BRIEF (below) | Nothing |
| Link | In the DM: `utm_source=instagram&utm_medium=dm&utm_content=dm-brief-<piece id>` | Profile link: `utm_source=instagram&utm_medium=social&utm_content=bio` |

The DM, from @makeyourmind.up, in the publication's "we" voice, never naming Krish (`docs/ACCOUNT-VOICE.md`):

> Here are the three things to do tomorrow, from this week's piece: {article link, tagged as above}
>
> Want the next one in your inbox? {subscribe link, tagged as above}

The "three things" are the closing section every article already carries (content-engine rule 11), so no new asset is made. Both lines pass the vendored copy lint (`channel_copy`) as drafted. Each real DM is checked again with the piece's own link before it goes live.

## Design

- **Channel:** Instagram @makeyourmind.up Reels only. TikTok has no approved comment-to-DM route for this account, and LinkedIn stays his own click.
- **Length:** two weeks, starting the Monday after his yes.
- **Assignment:** alternate the arms Reel by Reel within the same series and format, so neither arm gets all the strong pieces. At least 6 Reels in each arm, the floor every experiment here keeps (`minimum_observations`).
- **One change only:** the hook, the edit, the posting time and the cover follow the normal pipeline in both arms. Only the caption's last line and the DM differ.

## Measurement

- **Subscribers by arm:** GA4 `sign_up` on each `utm_content` (judged by subscribers, `measure.judge_subscribers`), and the sources in Substack's new-subscriber emails, which Control Center now counts for the North Star (control-center `api/_substackNotices.ts`).
- **Per 1,000 views:** subscribers, comments, DMs sent (from the DM tool's own count) and link clicks.
- **Guardrails:** unsubscribes within 14 days from DM subscribers, Instagram reports or restrictions on the account, and unfollows on keyword Reels.
- **Readout:** a report in Control Center at the end of week 2, with numbers by arm and the decision rule applied.

## Decision rule

Keep the keyword arm only if it brings at least twice the subscribers per 1,000 views of the bio arm, with no rise in unsubscribes, reports or account restrictions. Otherwise stop and keep "link in bio". With 6 Reels in each arm this is a review floor, not statistical proof: say so in the readout.

## Guardrails that never move

- A DM goes only to someone who commented the keyword on that Reel, once per person per Reel, with no follow-up and no second message.
- No DM asks for an email or a reply, and none carries anything but the two lines above.
- No auto-follow, no DMs to non-commenters, no buying comments or engagement pods.
- Stakes without fear, as on every surface: the hooks are unchanged by this test.

## What needs his yes, one action at a time

1. **The ruling on rule 5**, above.
2. **The DM tool.** Instagram's own automated responses in Meta Business Suite, if this account offers keyword replies to comments (to check in the account first), else a third-party tool approved by Meta for Instagram messaging, such as ManyChat, whose current plan and price are confirmed at signup. A paid plan is spend: his approval of the exact plan and amount.
3. **Connecting @makeyourmind.up to that tool.** An account permission change: his click, in his browser.
4. **The exact DM words and each keyword caption**, through the week's mix plan and go-live as for every post (`docs/PUBLISHING-AUTHORITY.md`).

## What the engine builds once he says yes

- The keyword caption variant for the keyword arm, in place of content-engine's "link in bio" line for those Reels, recorded per Reel so the arms can be told apart.
- The DM payload per piece: the article's link and the subscribe link, each tagged with the piece id, and the three things read from the published article.
- An arms ledger (Reel, arm, date, views) and the week-2 readout in Control Center.
