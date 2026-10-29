# Brief for Inspiration House: a maker may read his production examples

This brief comes from the makeyourmindup growth engine, written on 27 October 2026. Inspiration House keeps the one procedure for taste, so the rule change belongs in its README and `docs/TWO_WAY.md`, not in a copy here.

Ruling (Krish, 2026-10-27): a maker may read his production examples (his study_style cards and his form signals) as context for making; never a rule, never to judge.

Krish asked for this on 27 October: "Make sure you're wiring into the Inspiration House repository in a way that is incredibly robust because that's where I put in videos or content. I put it in when I either love the production, it could be a template for us, or I like the specific content." He approved the growth engine's plan the same day.

## The change

1. **README, "Rules it keeps".** Next to "Taste shapes form, never subject. Readers only see `taste_profile_form`", add:
   > A maker may also read his production examples (cards he routed to study the style, and form signals) through Control Center's `get_production_examples`, as context for making, never as a rule and never to judge. Subject and workflow signals never reach it.
2. **README, "What it knows about his taste".** In the line "Signals are the pattern store; claims are the decisions. A signal never decides anything and never reaches a reader of approved taste", add that signals may reach `get_production_examples` as examples.
3. **`docs/TWO_WAY.md`, Progress.** Add one line: "Production examples (2026-10-28): makers read study_style cards and form signals through Control Center's get_production_examples. Proved by Control Center's tests; growth-makeyourmindup reports back which card shaped which post as an observation."
4. **Nothing else changes.**
   - His words are still kept only verbatim.
   - Withdrawn answers still drop out.
   - Observations still never count toward a claim.
   - Only he answers cards and approves rules.

The growth engine's reports through `report_to_taste_engine` are observations ("card X shaped post Y; it did works, neutral, fails or not enough data, with the denominator"). They are context for the explain stage only, and never support for a claim.
