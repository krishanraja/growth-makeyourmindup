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
the signature records `concepts_digest` and `concept_proposal_id`, which must
name the week's mix plan (`makeyourmindup:mix:<ISO week>`) or the run is
refused, so his no on the plan can always stop its concepts. Each post made
from a concept names it in `concept_id`. Release posts it with no digest of
its own while it matches the concept: one of its placements, only its mock
files, its claim word for word. A text-only placement (X text, no files) is
made from the claim alone and carries no mock file. Anything else holds as
`departs_from_approved_mock`.

Because no signature of his covers each such post, release holds it unless:

- `review/<slot>.json` passes it at its own `payload_sha256` (the blind send
  test for a snackable format), so words added after the claim are reviewed
  too (`concept_post_not_reviewed`);
- its channel's New York day has room under the daily cap (four on these
  channels, `engine/intensity.py`), counted over this run's ledger, every
  other run's scheduled releases and the posts he signed one by one in the
  spec, which keep their place (`concept_daily_cap_reached`; an unreadable cap
  holds as `concept_daily_cap_unknown`);
- no decline in the loop's go-live ledger is still unmatched to its plan
  (`unresolved`): any of them may be his no on the mix plan, so every concept
  post holds (`concept_stop_unresolved`).

A concept in `stopped_concepts`, or a stop on the mix plan proposal in the
loop's go-live ledger, holds every post from it. Copy lint, share asks, the
ecosystem route, the channel lock and route capability checks still run on
every post. LinkedIn stays his click.

`run lint` checks concept slots too: a slot off its concept's placement, mock
or claim is `concept_mismatch`, one naming a concept not in the spec is
`unknown_concept`, and signing the concept approves its mock files for the
posts made from it (no separate `creative_approval_ref`).

## Not live yet: the readback

Release reads concept approvals only from `decision.json` `concepts` and the
signature's `concepts_digest` and `concept_proposal_id`. Nothing in this
repository writes those yet from the readback of his decision on the mix plan
(`mix.approved_map` is ready for it but nothing calls it), and release still
needs the week's approved go-live decision (`docs/RUN.md`). A hand-edited
`decision.json` is forbidden. So until that readback lands, in its own change
with its tests, no post releases on a concept approval alone: concept posts
hold, and every post still goes out only on his signed go-live as before.

When it lands, a release session posts up to 16 a day on these channels plus
their readbacks, above the provisional 25-call release budget in
`docs/RUN.md`; that budget moves in the same change, after the Phase 0
baseline.

## Learning

Each post's What-Works verdict lands at `verdict/<slot>.json` in its run
folder (docs/RUN.md). `python growth.py mix learn SPEC [SPEC ...]` joins each
verdict to the post's concept and lane, by lane and by channel; the release
ledger records each post's concept too. The next `mix plan --learn` moves a
lane by 5 when it has at least 3 judged posts and works minus fails is at least
a third of them (down by 5 at minus a third), inside its bounds. Insufficient
verdicts never count, and a lane with too few judged posts keeps its weight.
Association, not cause.
