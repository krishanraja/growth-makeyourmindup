# Taste: what the routines read from Inspiration House, and what they tell it

The `make`, `plan` and `watch` routines follow this file wherever their own
file says "taste". The procedure itself lives in krishanraja/inspirationhouse
(`README.md`, `docs/TWO_WAY.md`); this file says only how this engine uses it.

Krish, 27 Oct 2026: "Make sure you're wiring into the Inspiration House
repository in a way that is incredibly robust because that's where I put in
videos or content. I put it in when I either love the production, it could be
a template for us, or I like the specific content. I'm always commenting in
detail on why I like something in there."

## Read, before you build or write (Control Center connector)

1. `get_approved_taste` with lane `production`, then lane `voice`. Follow every
   rule it returns when you fill a Canva template or write words. Empty means
   none is approved yet: never invent one.
2. `get_production_examples` for the slot's platform and format: the cards
   Krish routed to "study the style" with his own words, and his form signals
   (Ruling, Krish, 27 Oct 2026: a maker may read them as context for making,
   never a rule, never to judge). Follow the craft his words and signals
   point to (for example `graphics.visuals_carry_meaning`,
   `packaging.plain_title`, `structure.one_idea`) inside the kit and template.
   Never take a subject from them: subjects come only from the approved piece.
3. A card he routed to "make a piece" is content-engine's, never yours.
4. Either tool missing, signed out, failing or empty: carry on with the kit
   and the calendar, and count it as `taste_unavailable` in your summary.
   Taste never blocks a slot.
5. Record the card ids an asset drew on, ids only: in the Buffer draft's note
   if Buffer offers one, and in your summary. Never copy his words into this
   repository, a commit, a Buffer post or a log.

## Tell it back (`report_to_taste_engine`, exempt from the approval wall)

Krish ruled on 26 Oct 2026 that reports to his taste ledger are exempt from the
approval wall. This is the one Control Center write a routine may call.

- His exact words: anything Krish typed that this run reads (an amended
  go-live, a decline reason, an idea in Buffer Ideas). Quote it character for
  character with where and when he typed it (`kind` his words). Never a
  paraphrase.
- Observations (never counted toward a rule): "card X shaped template Y" or
  "post Z", and each such post's verdict from the measure job (works,
  neutral, fails or insufficient, with its denominator). The `watch` routine
  sends these once a day; send each fact once.
- Never report a guess as his words, and never answer a card or approve a
  rule.

## The weekly template refresh (`plan` only)

When three or more cards he routed to "study the style", each with his words,
share a form pattern for a format the kit lacks or does badly, build one new
Canva template from them (kit colours and fonts, plain English, no em
dashes), and propose it as a new-format item for his eyes, with the card ids
it rests on. At most one a week. Never publish a template.
