# The daily credits session

This is the brief for the one Claude scheduled session this repository
allows, "Spend Make Your Mind Up's prepaid credit share". There are no Claude
routines here (Krish, 29 Oct 2026), and this session is the one exception
(Krish, 2026-10-29: "make an exception for makeyourmindup"; `docs/LANES.md`,
`lanes.json` `claude_sessions`). It runs once a day with the Control Center,
ElevenLabs and Apify connectors. The GitHub runner holds no ElevenLabs or
Apify keys and spends nothing.

The authority is his ruling of 2026-10-29: this engine may spend up to its
share of each prepaid pool with no proposal. Each spend is recorded through
Control Center. The spec is `docs/CONTROL-CENTER-BRIEF.md`, "Prepaid credits".

Read `AGENTS.md` and `PLAYBOOK.md` first. The approved voice rules and the
copy doctrine apply to every word you make.

## Each run

1. **Read the share.** Call `get_engine_credits` with `engine: makeyourmindup`.
   - If it says `held: true`, or `credits` is null, stop and say so in one
     line. Null means unknown, never a share of zero.
   - If the Control Center, ElevenLabs or Apify connector is missing, stop
     and name it.
   - Otherwise note each pool's `mode`, `remaining_for_you`, `use_by` and
     `days_left`.
2. **ElevenLabs** (`mode: use_it`: prepaid, renews on the 10th, unused
   credits roll over two months, then they are wiped).
   - Today's budget is `remaining_for_you / days_left`. Inside the last three
     days before `use_by`, the budget is everything left.
   - The work: narration drafts of approved scripts and published pieces for
     the publication, for a Short, an audio version or a trailer. Make one
     take, listen, and only then make the rest.
   - Anything in Krish's cloned voice is a draft that waits for his yes
     before it is published. Never for the cut gates ("do not use eleven labs
     for this", CHANGES.md).
3. **Apify** (`mode: ceiling`: pay as you go; Ruling, Krish, 2026-10-29).
   - The share is the most this engine may spend in a cycle, never a target.
     There is no pace and no "use it up" rule: a quiet day spends nothing.
   - Run only what a decision for `new_subscribers` needs: who shares and
     comments on pieces like ours, threads where readers ask what our pieces
     answer, the radar's sources.
   - Before a run, call `get_apify_learnings`. Prefer an actor with verdict
     `keep` for the job. Give a new actor one `trial`, with the smallest
     `maxItems` that answers the question. Never rerun a `drop` actor.
   - Settle every run with `actor`, `job` (one short slug you reuse, for
     example `piece_sharers`), `items` (results returned) and `used`
     (results you kept). Counts only, never names.
4. **Every spend, in this order.**
   1. `reserve_credit_spend` with the pool, the expected cost (the tool's own
      quote or the block's `unit_costs`), the asset in words (for example
      `narration draft of "<piece title>", take 1`) and `objective_key:
      new_subscribers`. A refusal (`over_share`, `held`, `no_pool`,
      `unknown`, `open_reservation`) stops that pool.
   2. Run it.
   3. `settle_credit_spend` with the actual cost the provider charged and its
      job or run ids in `receipt`. Pass `amount: 0` if it failed or nothing
      was charged, which voids the reservation.
5. **Keep what you made private.** Audio drafts stay in the ElevenLabs
   library. Research that names people goes to Control Center or stays under
   `.scratch/`, never in a commit. This repository is public.
6. **Finish with one line per pool:** what was made, the amount spent and
   what is left of the share.

## The walls

- Never past `remaining_for_you`.
- Never a top-up, a plan change or new money.
- Never publish, post or send anything you made. Publishing goes through the
  go-live, or an approved concept.
- Never change this repository.
- A spend recorded here is never reported again in a runner report's
  `credits_spent`. Control Center already counts it.
