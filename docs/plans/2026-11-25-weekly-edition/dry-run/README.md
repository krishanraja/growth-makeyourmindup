# Edition one, dry run (25 Nov 2026)

What edition one of makeyourmindup weekly would have been on Saturday 14 November 2026, made from the last week whose
three pieces all went live (9 to 13 November). For Krish's approval of the shape and the words. Nothing has been sent,
scheduled or put into Substack.

- `edition-2026-11-14.draft.json`: the package, in the contract's shape (`content-engine-edition/1`), keys sorted.
- `edition-2026-11-14.preview.html`: the page it renders to. Structure only: the v5 look comes from the Library's
  `newsletter-weekly-edition` template once Krish approves the Library.
- `render_edition.py`: the renderer and checks used here, until content-engine's `scripts/edition/edition.py` replaces it.

## What was checked

| Check | Result |
|---|---|
| Section order, sizes (opener up to 60 words, summaries 50 to 80, 4 to 10 news items) | pass; 624 words in all |
| Every link carries the four edition tags (`utm_source=newsletter`, `utm_medium=email`, `utm_campaign=weekly`, `utm_content=edition-2026-11-14-<place>`) | pass |
| No em dash, no exclamation mark, never names Krish, mind/make or CTRL | pass |
| Control Center `check_voice` (channel substack) on every line | pass, after one rewrite: Adobe's partner title carried "innovation", which is on the kill list |
| Each piece summary against the live piece | read in full from the publication's feed; the predictions the old pieces carried are left out (no predictions: rulings of 17, 18 and 24 Nov) |
| Each news item against its primary source | all nine re-read by this session: the court filings (CourtListener and the RECAP mirror; the research pass had the two 6 November complaints' links the wrong way round, corrected here), Adobe's newsroom twice, Ogilvy, Suno's blog, and the Paramount Skydance and WEBTOON shareholder letters on SEC EDGAR, both dated 9 November |

## How this differs from a live edition

- The covers are the pieces' real covers from before v5; a live edition uses each piece's v5 cover.
- In Substack each piece goes in as Substack's own post card (the edition needs no upload; IMPLEMENTATION.md, V1).
- The opener's "switch it on in your email settings" needs the opt-in section (K1) to exist before edition one sends.
- No good-news group: the good-news run did not run for that week. A live edition adds up to three.
- Four research candidates were left out as weaker or off the beat: NVentures' subpoena fight in the labels' case
  against Suno, Weta FX in Taiwan (its source only on a wire service), OpenAI and Upwork's freelance study (only partly
  about creative work) and Rumble's AI computing revenue. The research pass dropped more for no primary source or a date
  outside the window.
