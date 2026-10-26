# Job: recommendations

Kind `swaps`. Read the shared instructions and `docs/ENGINE.md`.
Recommendations are a fit hypothesis to measure, not a guaranteed source.

First, before reading any source: `python growth.py cc start --job swaps --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read swaps/partner lists and confirm actual sent/replied events. Use the
   60-day cooldown for confirmed asks, not for unsent drafts. Respect a
   decline and avoid duplicating an unresolved conversation.
2. Research up to three publications across peers, category leaders and
   adjacent bridges. Read one recent post in full. Record writer, source
   URL, literal excerpt, overlap and observed date; audience size only when
   actually shown. Skip low-fit accounts even when a quota is unfilled.
3. Write it under Krish's approved voice rules (`.scratch/cc/voice-rules.txt`, "His approved voice rules" in `AGENTS.md`): how it is written only, never what it is about, and never in a score or review.
   Draft under 90 words per named writer, using the direct outreach
   structure in `knowledge/COPY-DOCTRINE.md`: one specific point from their
   piece, what MYMU does for the same reader, a real useful offer and one
   question about serving their audience. No reciprocal recommendation
   obligation or invented prior relationship.
4. Optionally recommend a publication Krish should read/recommend on its
   merits, with an accurate blurb as a separate configuration draft. Never
   change recommendations or imply a recommendation has gone live.
5. Update researched list rows as `drafted`. No change of relationship stage
   until a real event is confirmed. Gmail is optional only under separate
   scheduled-job authorisation. Prepare evidence, merge the global queue,
   check, then use the delivery boundary in `AGENTS.md`.
6. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job swaps --envelope .scratch/swaps.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
