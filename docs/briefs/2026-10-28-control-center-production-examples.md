# Brief for Control Center: give makers Krish's production examples from Inspiration House

This brief comes from the makeyourmindup growth engine, written on 27 October 2026. Krish asked for this on 27 October: "Make sure you're wiring into the Inspiration House repository in a way that is incredibly robust because that's where I put in videos or content. I put it in when I either love the production, it could be a template for us, or I like the specific content. I'm always commenting in detail on why I like something in there."

Krish approved the growth engine's plan the same day. Under it, growth may read his `study_style` cards and his form signals as examples for making. They are context, never rules, and never used to judge.

Ruling (Krish, 2026-10-27): a maker may read his production examples (his study_style cards and his form signals) as context for making; never a rule, never to judge.

Control Center rule 7 applies, so this repository changes nothing in Control Center. A Control Center session applies this brief, or Krish lifts rule 7 for it, as he did for the GA4 read.

## What exists (read on 27 Oct)

- **The two taste tools.** `api/harness/_taste-mcp.ts` holds `get_approved_taste` and `report_to_taste_engine`. The reader reads `taste_profile_form` by lane. No rule is approved yet, so the reader returns nothing.
- **Cards.** These live in Inspiration House's store, content-engine's `public.inspiration_items`. Each card has `route` and `routes` (`study_style`, `make_piece`, `visibility` or `taste_only`), `kind`, `facets` (platform, format, link, `part_of`), and his answers (`why_here`, `why_like` with `why_like_source`, `would_do`), along with `answered_by` and `answered_at`.
- **Signals.** This stage is new, at inspirationhouse `7d35388`, migration `20261115090000_taste_signals.sql`. The views are `taste_signal_patterns` and `taste_signal_patterns_by_context`, split by lane, platform, format and kind. Each signal has a dimension (form layers, `subject` or `workflow`), a slug, polarity, strength and support. It carries his phrase only when that phrase is his words verbatim (origin `krish`).

## The change: one read tool, beside the other two, in the same file and on the same store pattern

Add `get_production_examples` with these inputs, all optional:
- `platform` (`instagram`, `tiktok`, `youtube`, `x`, `threads`, `substack`, `facebook`, `linkedin`);
- `format` (free text matched against card and signal facets);
- `limit` (default 12, maximum 30).

It returns two lists.

**1. `cards`:** cards Krish answered himself (`answered_by = 'Krish'`) whose route includes `study_style`.
- Leave out cards that are `dismissed_at`, cards of kind `feed`, and slides (`part_of`).
- Newest answer first, filtered by platform or format when given.
- Each card returns: `card_id`, `kind`, `platform`, `format`, `answered_at`, a link to the media (the Drive file link or `facets.link.url`), and his words.
- His words are `why_like` only when `why_like_source = 'typed'`, plus `why_here` and `would_do`. Return them whole (`meta.full_text` where an excerpt was cut), and only while the answer stands. Use Inspiration House's quote-hold rule: read through whatever view already gates it, or gate the same way.

**2. `patterns`:** rows of `taste_signal_patterns_by_context` whose dimension is a form layer.
- Never include `subject` or `workflow`; that is the anti-echo rule.
- Filtered by platform or format when given, ordered by his support.
- Each row returns: dimension, slug, polarity, support (his answers only), strength, the trend (last 90 days against the 90 before), and up to three of his phrases where the origin is `krish`.

**The note on every answer:**
> "These are examples Krish saved and why, for making only: how things look, are structured and are cut. Never use them to choose a subject, and never to judge, score or rank work. Empty is a valid answer."

**When the read fails,** return isError with "Production examples could not be read. Make as you would without them." Never guess.

## Tests (beside `tests/api/tasteMcp.test.ts`)

- **Who answered.** A card answered by the engine, or holding only a tapped `why_like`, returns no words.
- **Withdrawn answers.** A card whose answer was withdrawn returns no words.
- **Filters.** `subject` and `workflow` signals never appear, and nor do `make_piece`-only cards.
- **Empty store.** It returns an empty, well-formed answer.
- **Read-only.** The tool cannot write.
- **Logs.** They carry counts only.

## How growth-makeyourmindup uses it (already wired on its side, inert until the tool exists)

- The daily `make` routine reads examples for each platform and format before filling a Canva template.
- The Sunday `plan` routine proposes at most one new template a week, built from three or more of his `study_style` cards for a format. It goes to his list as a new-format item, with his words beside it.
- Each asset records the card ids it drew on.
- `report_to_taste_engine` gets an observation of which card shaped which template or post, and how that post did.
- The engine's judging code never reads this tool; a test in growth-makeyourmindup checks that.
