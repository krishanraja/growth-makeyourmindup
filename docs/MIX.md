# The weekly mix

Ruling (Krish, 2026-10-29): repurpose every past piece into carousels,
interleave them with memes, positive news and the other filler lanes, three or
four posts a day on Instagram, YouTube, TikTok and X, and he approves each idea
and its mock once (`CHANGES.md`, R101 to R103). "The more we flood these
channels right now, the faster we learn."

## What the planner does

`python growth.py mix plan --week-of YYYY-MM-DD` (the Monday) reads:

- the backlog inventory (`growth.py backlog`, `.scratch/backlog/inventory.json`):
  every published piece, oldest unamplified first, then partly amplified, with
  the channel formats still open;
- the lanes in `mix.json`, which only an interactive session changes;
- `--ideas FILE`: this week's filler ideas, each with `idea_id`, `lane`,
  `idea`, `claim`, `source_url` and `source_date`;
- `--mocks FILE`: `{concept_id: {claim, mock_sha256}}` once the mocks exist;
- `--learn FILE`: last week's `mix learn` output.

It lays out every day on each of the four channels. A channel's daily target
is four; on Monday, Wednesday and Friday the piece's own cut takes one slot, so
the mix fills three there and four on the other days, never under the floor of
three (`daily_posts_target` and `daily_posts_floor` in `social/channels`).
Times are New York: 08:30, 12:30, 17:30 and 20:30, the series slot at 12:30.

## The lanes and the ratio

| Lane | Default weight | Bounds | Source | Placement |
|---|---|---|---|---|
| Repurposed carousels | 50 | 30 to 70 | the backlog | IG and TikTok carousel, a Shorts slideshow, an X cover card |
| Memes | 25 | 10 to 40 | ideas | meme on all four |
| Positive news | 15 | 5 to 30 | ideas, primary source dated within 7 days | as the carousel lane |
| Level-up advice | 10 | 5 to 25 | ideas | carousel, Shorts, X text |

The lanes are the 28 October off-day lanes (`docs/ENGINE-BOUNDARY.md`) plus
the derived carousels, now on every day. Weights become whole slots by largest
remainder (25 a week per channel: 13, 6, 4 and 2 by default) and are spread
through the week by smooth weighted round robin, so lanes interleave and every
day carries a repurposed carousel. A piece or idea runs at most once per
channel in a week, and never in a format already made on that channel. A slot
with nothing approvable is a shortfall, never filled with unapproved creative.

## One press: the idea and the mock

A concept is one idea, its one claim and its mock files, bound by
`concept_sha256` (`engine/concepts.py`). The planner's output carries one
proposal: stage `plan` behind `strategy`, its exact payload the mix and each
ready concept with its hash. The Sunday report job carries it when
`.scratch/mix/plan-<Monday>.json` exists (`engine/cc_loop.py`, `mix_proposal`).
His yes approves each ready concept; deleting a concept's line in his amended
version leaves it out (`mix.approved_map`); his no approves none.

Then `growth.py run new --start <Monday> --mix <plan file>` puts the ready
concepts in the week's spec. decision.json carries `concepts`
{concept_id: concept_sha256} from his decision's readback, never by hand, and
the signature records `concepts_digest` and `concept_proposal_id`. Each post
made from a concept names it in `concept_id`. Release posts it with no digest
of its own while it matches the concept: one of its placements, only its mock
files, its claim word for word. Anything else holds as
`departs_from_approved_mock`. A concept in `stopped_concepts`, or a stop on the
mix plan proposal in the loop's go-live ledger, holds every post from it.
Copy lint, share asks, the ecosystem route, the channel lock and route
capability checks still run on every post. LinkedIn stays his click.

## Learning

Each post's What-Works verdict lands at `verdict/<slot>.json` in its run
folder (docs/RUN.md). `python growth.py mix learn SPEC [SPEC ...]` joins each
verdict to the post's concept and lane, by lane and by channel; the release
ledger records each post's concept too. The next `mix plan --learn` moves a
lane by 5 when it has at least 3 judged posts and works minus fails is at least
a third of them (down by 5 at minus a third), inside its bounds. Insufficient
verdicts never count, and a lane with too few judged posts keeps its weight.
Association, not cause.
