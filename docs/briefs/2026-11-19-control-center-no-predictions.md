# Brief to Control Center: retire the prediction format (19 Nov 2026)

From growth-makeyourmindup, for a Control Center session (this engine never edits Control Center; Krish, 2026-10-17:
"you are not to do any actual work in control-center, only pass me a brief once you have completed your work").

Ruling (Krish, 2026-11-18): "i have abandoned the prediction format, it feels lame".
Ruling (Krish, 2026-11-17): "I don't do dated-and-scored make-your-mind-up pieces because it felt quite tacky and
gimmicky. I don't really have the clout such that my opinion can hold up in official scores."

## What is already done (18 to 19 Nov)

- makeyourmindup.ai: the scoreboard and FlapCounter are gone (makeyourmindup PR 48).
- growth-makeyourmindup: copy doctrine, channel playbook, daily pack, series table and hook families (PR 134, merged).
- makeyourmindup: the brand-kit builder's copy (PR 50).
- ai-harness: content-corpus's editorial channels reference now marks the architecture canon's section 0a.1
  "One prediction" clause superseded (PR 293), and its judge panel asked for the canon itself to record the ruling.
- content-engine: the publish checks CALL, CALL_HORIZON and CLEAR_STANCE, the house rules that demand
  "## OUR PREDICTION", the judges, the call card and the channel-kit copy (its own PR).
- The design system artifact, the Drive brand kit READMEs and Krish's taste engine (his words filed 18 Nov).

## What only Control Center can do

1. docs/MINDMAKE_OS_ARCHITECTURE.md: add the ruling under `## 0a` and close section 0a.1's "One prediction" clause
   (each piece ends with one dated, checkable prediction, and only Krish sets the confidence number) as superseded on
   2026-11-18. Keep 0a.1's "Not us" clause as it is.
2. Mindmaker OS `venture_formats.mandate` for the publication's subchannels: read mind.the.gap's mandate (and the other
   two) and remove any dated call, prediction, confidence or scorecard requirement; mind.the.gap names a pattern and
   says where it leads.
3. The taste engine: the standard recorded as 5941fd45 ("always commit to a bold, near-term call with a confidence
   level") contradicts both rulings; retire it against Krish's words filed on 18 Nov (report
   bbeb0924-10d5-4277-8004-5d2bfd365974, lane strategy, venture publication).
4. Anything in Control Center's own code, prompts or board copy that asks a piece for a prediction, a call or a
   confidence (grep for "prediction", "OUR PREDICTION", "dated call", "confidence", "scorecard").

Done when: the architecture doc records the ruling, no mandate or taste standard asks for a prediction, and a grep of
Control Center finds no live requirement for one.
