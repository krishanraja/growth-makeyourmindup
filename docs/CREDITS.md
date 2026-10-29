# Spending the publication's prepaid credits

This is a procedure, not a schedule. Krish ruled on 29 Oct 2026 that this
repository has "zero Claude routines. No Claude schedules of any kind"
(docs/LANES.md). The GitHub runner holds no ElevenLabs or Apify keys and
spends nothing. So the credits are spent only when an interactive session runs
this procedure with the Control Center, ElevenLabs and Apify connectors
attached. Krish starts that session himself, or a later ruling names another
runner.

The authority is his ruling of 2026-10-29: this engine may spend up to its
share of each prepaid pool with no proposal. Each spend is recorded through
Control Center. The spec is `docs/CONTROL-CENTER-BRIEF.md`, "Prepaid credits".

Read `AGENTS.md` and `PLAYBOOK.md` first. The approved voice rules and the
copy doctrine apply to every word you make.

1. **Read the share.** Call `get_engine_credits` with `engine: makeyourmindup`.
   - If it says `held: true`, or `credits` is null, stop. Null means unknown,
     never a share of zero.
   - Otherwise note each pool's `remaining_for_you`, `use_by` and `days_left`.
2. **Pace it.** Today's budget for a pool is `remaining_for_you / days_left`.
   Inside the last three days before `use_by`, the budget is everything left.
   Credits serve `new_subscribers`. Never invent work just to use them up.
3. **Pick the work.** Take it from what this engine already needs, best first:
   - **ElevenLabs:** narration drafts of approved scripts or published
     pieces, for a Short, an audio version or a trailer. Anything in Krish's
     cloned voice is a draft that waits for his yes before it is published.
     Make one take, listen, and only then make the rest.
   - **Apify:** audience and source research for `new_subscribers`. That
     covers who shares and comments on pieces like ours, the threads where
     readers ask the questions our pieces answer, and the radar's sources.
     Use an existing actor with a capped run.
4. **Spend it, one generation at a time.**
   1. `reserve_credit_spend` with the pool, the expected cost (from the tool's
      own quote or the block's `unit_costs`), the asset in words (for example
      `narration draft of "<piece title>", take 1`) and `objective_key:
      new_subscribers`. If it refuses (`over_share`, `held`, `unknown`,
      `open_reservation`), stop that pool.
   2. Run the generation.
   3. `settle_credit_spend` with the actual cost the provider charged and
      its job or run ids in `receipt`. Pass `amount: 0` if it failed or
      nothing was charged.
5. **Keep what you made private.** Audio drafts stay in the ElevenLabs
   library. Research that names people goes under `.scratch/` or in Control
   Center, never in a commit. This repository is public.
6. **Finish with one line:** what was made, the credits spent per pool, and
   what is left of each share.

**The walls.**
- Never past `remaining_for_you`.
- Never a top-up, a plan change or new money. Apify usage past the included
  $29 is new money.
- Never publish, post or send anything you made. Publishing goes through
  the go-live, or an approved concept.
- A spend recorded here is never reported again in a runner report's
  `credits_spent`. Control Center already counts it.
