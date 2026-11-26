# Taste: what a session reads from Inspiration House, and what it tells it

**Since 26 November 2026 this engine makes no asset and writes no caption** (Ruling, Krish, 2026-11-26: content-engine makes every asset):
taste for production is content-engine's to read. What follows applies to the words this engine still writes
(engagement replies, outreach and reports) and to the Buffer drafts it builds from content-engine's assets.

Any session or PC automation that writes for this engine (engagement replies, outreach, Buffer drafts of
content-engine's assets), the four engine sessions included
(`docs/LANES.md`), follows this file before it builds. There are
no Claude routines (Krish, 29 Oct 2026); whoever makes, makes under the same
walls (`docs/LANES.md`). The procedure itself lives in
krishanraja/inspirationhouse (its README.md and docs/TWO_WAY.md); this file
says only how this engine uses it.

Krish, 27 Oct 2026: "Make sure you're wiring into the Inspiration House
repository in a way that is incredibly robust because that's where I put in
videos or content. I put it in when I either love the production, it could be
a template for us, or I like the specific content. I'm always commenting in
detail on why I like something in there."

## Read, before you build or write (Control Center connector)

1. `get_approved_taste` with lane `production`, then lane `voice`. Follow every
   rule it returns when you write words. Empty means
   none is approved yet: never invent one. Never take a subject from them:
   subjects come only from the approved piece.
2. A card he routed to "make a piece" is content-engine's, never yours.
3. The tool missing, signed out, failing or empty: carry on with the kit
   and the calendar, and count it as `taste_unavailable` in your summary.
   Taste never blocks a slot.
4. The headless maker (`maker.yml`) writes no words since 26 November 2026: it posts content-engine's
   captions word for word, so it reads no taste. Judges never read taste: its blind reviewer does not
   either.
5. Record the card ids an asset drew on, ids only: in the Buffer draft's note
   if Buffer offers one, and in your summary. Never copy his words into this
   repository, a commit, a Buffer post or a log.

## Tell it back (`report_to_taste_engine`, exempt from the approval wall)

Krish ruled on 26 Oct 2026 that reports to his taste ledger are exempt from the
approval wall. Call no Control Center write tool but `report_to_taste_engine`:
it is the one Control Center write a maker may call.

- His exact words: anything Krish typed that you read (an amended go-live, a
  decline reason, an idea in Buffer Ideas). Quote it character for character
  with where and when he typed it (`kind` his words). Never a paraphrase.
- Observations (never counted toward a rule): "card X shaped template Y" or
  "post Z", and each such post's verdict from the measure job (works,
  neutral, fails or insufficient, with its denominator). Send each fact
  once, whoever made the post.
- Never report a guess as his words, and never answer a card or approve a
  rule.

## The weekly template refresh (whoever plans the week)

Whoever plans the week proposes no template: a new template is content-engine's to make (its v5
Library, through the Divergence engine and Krish's eyes), and since 26 November 2026 this engine builds
none. When three or more cards he routed to "study the style" share a form pattern for a format the
Library lacks, say so to content-engine, with the card ids it rests on, at most one a week.
