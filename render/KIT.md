# The mock kit, and where its look comes from

The templates in `render/templates/` are drawn to match the artwork already published by
Make Your Mind Up, which Krish called "really nice". This file says where each rule came from.

- **Observed** means the rule can be seen in a published image. Each one names the board it was on
  and what the image shows.
- **Interpreted** means the rule is read into the artwork, or fills a gap the artwork does not
  cover. It is a proposal, and Krish can overrule it.

The reference images are private. They are never copied into this repository.

## The two boards

- **Board of 26 October 2026**: a tall vertical cover for one story, the same story as a wide
  share card and as a square post, and seven video chapter cards for it.
- **Board of 19 October 2026**: three number cards from a series about AI prices, and several
  evidence cards from a series about how AI tools behaved in tests.

## Colours and fonts

| Rule | Source |
| --- | --- |
| Only the eight kit colours: ink, deep ink, cream, green, mint, butter, coral and lilac. | Observed on both boards. Every colour in the artwork is one of them or a muted mix of them. |
| Butter, lilac and coral are the three series' colours (follow.the.money, under.the.hood, mind.the.gap). They belong to content-engine's one weekly piece of each series, so no Growth asset wears them or names a series, on any day (R125). Ink, deep ink, cream, green and mint carry everything Growth makes. | Ruling, Krish, 2026-11-04: "I should be allowed to post random stuff on any day but it doesn't take on the brand colours of Follow the Money, Mind the Gap, or Under the Hood." The renderer, the art-direction gate and the Canva lint refuse a series colour or name. |
| Covers and share cards sit on deep ink. Number cards and chapter cards sit on ink. | Observed: sampled from the pixels, the 26 October cover, share card and square post are exactly deep ink, and the 19 October number cards and 26 October chapter cards are exactly ink. |
| Evidence cards sit on deep ink. | Interpreted. The 19 October evidence cards use a very dark green that is not a kit colour; deep ink is the nearest kit colour. |
| Muted text and hairlines are a kit colour turned down (lower opacity), never a new grey. | Interpreted. The artwork has soft greys; the kit has none, so the templates fade cream or mint instead. |
| Headlines in Anton, labels in IBM Plex Mono, names and body lines in Archivo, Fraunces kept for subheads. | Observed for Anton, Plex Mono and Archivo on both boards. Fraunces is the kit's own and does not appear on either board. |
| No em dashes anywhere. | House rule. The renderer refuses a field that holds one. |

## The brand mark

| Rule | Source |
| --- | --- |
| The brand mark is the official logo file, `render/brand/makeyourmindup-horizontal.png` (with `-mark` and `-stacked` beside it), copied from the Control Center repository with the sha256 content-engine's `config/studio.json` records. It is never set as type or redrawn. Templates place it with `<div class="brandmark"></div>`; `kit.css` paints it. | The 2026-11-03 ruling on the Saturday carousel: a wordmark set as type is a fabricated logo. |
| On every carousel card it sits small and subtle in a bottom corner, never at the top: in the footer's right corner on the house carousel pages, `<div class="brandmark corner"></div>` on a piece kit's cards. | The same ruling, for all carousels of this nature. |
| On a meme it is the only brand: small and subtle in the bottom-right corner (`<div class="brandmark corner"></div>`, just above the safe zone on the vertical), with no masthead, series label or URL footer. A Canva meme records where it sits (`mark.box`) and the lint refuses one without it. | Ruling, Krish, 2026-11-04: "The Tuesday meme is likely to be more random but needs to be lightly subtly skinned in the bottom right corner." |
| Elsewhere (quote, receipt, versus, story and evidence cards) it takes the place the drawn wordmark had. | Carried over; only the drawing was replaced. |

## The Saturday carousel

| Rule | Source |
| --- | --- |
| Every Saturday carousel keeps the standard of the first, the 7 November 2026 good news, `render/pieces/off-sat-goodnews/`: a full-bleed photo cover, one photo-led card for each of five stories, a centred close, all 1080x1350, the house mark small in a bottom corner of every card, no series colour or name. Its look is its own, never the house templates'. | Ruling, Krish, 2026-11-04: "Saturday's carousel should have the standards of the first one that's coming up this Saturday." Five stories: content-engine's docs/CAROUSEL-STANDARD.md and its `week_board.py` `STORY_COUNT`. |

## Headlines

| Rule | Source |
| --- | --- |
| Heavy condensed capitals, tightly leaded. | Observed on the 26 October vertical cover, share card and chapter cards. |
| Two tones: cream lines first, then one accent line. The accent line may wrap. | Observed: cream then butter on the 26 October cover and share card; cream then mint on every 26 October chapter card. |
| The accent is the house mint (`tone` takes `mint` only). | Mint observed. Butter, coral and lilac left the kit's accents on 4 November 2026 (R125, above). |
| A quote card keeps one colour. | Interpreted. A quote is word for word, so colouring part of it would edit it. |

## Versus rows (versus-card, versus-card-tall)

| Rule | Source |
| --- | --- |
| Dark rows with a thin border, the name on the left, a solid colour chip on the right. | Observed on the 26 October vertical cover, share card and square post. |
| The chip text is mono, dark on the chip. Chips go mint, then cream. | Butter then mint observed on the 26 October cover; butter left the kit's accents on 4 November 2026 (R125). |
| A row with no value is a quiet centred strip of names. | Observed: the third row on the 26 October cover is a strip of small logos with no chip. The template writes names, not logos. |
| The wide card puts the wordmark and headline on the left and the rows on the right. | Interpreted. The 26 October share card has a headshot on the left; that is left out (see below), and the rows take its place. |

## Number cards (number-card, number-card-tall)

| Rule | Source |
| --- | --- |
| A thin accent rule across the top, inset from the edges. | Observed on all three 19 October number cards. |
| A mono eyebrow in the accent colour, such as a series name and a number. | Observed on the 19 October number cards. |
| A mixed-case condensed title in cream, not capitals. | Observed on the 19 October number cards. |
| An optional mono context line in the accent colour, such as a date. | Observed on the 19 October number cards. |
| Each row: an Archivo label, a quieter sub-label under it, and giant condensed numerals in mint on the right, with an arrow for a change ("$2 → $4"). | Observed on the 19 October number cards. The arrow is drawn in CSS so every font shows it the same. |
| Hairlines between rows, an optional closing line in condensed type, and a quiet mono source line at the foot. | Observed on the 19 October number cards. |
| The rule, eyebrow and numerals are mint. | Every number card on the board was butter; butter left the kit's accents on 4 November 2026 (R125). |

## Chapter cards (chapter-card, chapter-card-vertical)

| Rule | Source |
| --- | --- |
| A spaced-out cream mono eyebrow, such as "CHAPTER 6 OF 6 · WHAT I'D DO". | Observed in butter on the 26 October chapter cards; cream since 4 November 2026 (R125). |
| A cream headline with a mint second line, left aligned, with the entity name in bold Archivo under it. | Observed on the 26 October chapter cards, which show the company's logo there. The template writes the name in type. |
| No wordmark and no footer on a chapter card. | Observed on the 26 October chapter cards. |
| The vertical size keeps the same layout inside the story safe zones. | Interpreted. Only wide chapter cards were on the board. |

## Evidence cards (evidence-card)

| Rule | Source |
| --- | --- |
| Framed panels. What came in is a cream card with a mono label, the words in bold Archivo and a mono tag, on a green shadow. | Observed on the 19 October evidence card about an inbox test. |
| An arrow from what came in to the first actor. | Observed on the same card. |
| Each actor is a panel with a coloured bar on the left (mint first, cream second), the name in condensed capitals and a mono status on the right, such as "FLAGGED · SKIPPED". | Observed on the 19 October evidence cards, mint then lilac; cream since 4 November 2026 (R125). |
| The first actor's finding is a quoted line in condensed type, with one plain line under it. | Observed on the 19 October inbox card. |
| The second actor's words sit in a cream box with a mint tag, such as "ACTUAL DRAFT · REDACTED". | Observed in shape on the 19 October cards, where the box holds a screenshot. The template holds typed words instead. |
| Mono footer lines left and right, such as "20 OCT · NOTHING SENT". | Observed on the 19 October evidence cards. |
| Each actor gets a square tile with its first letter. | Interpreted. The artwork shows each tool's app icon, which the kit does not carry. |

## Left out on purpose

- **The passports motif** from the piece on why every country wants its own AI. Krish ruled that it
  must not become a template. None of its images was used.
- **The headshot and any photo of a person.** Growth posts speak as the publication, so no template
  holds a photo or names him. The 26 October cover, share card and square post each have a round
  headshot; the templates leave that space to the headline and rows.
- **Company logos.** The artwork shows real logos. The templates write names in type instead.

## What does not match yet

- The "UP" in the artwork is a rounder, heavier face than anything in the kit. Archivo at full
  weight and width is the closest the kit has.
- The chip text in the artwork is bold mono. The kit vendors IBM Plex Mono Regular and Medium only,
  so the chips use Medium with a thin outline to thicken it.
- The headline on the 26 October share card and square post looks wider than Anton. The templates
  keep Anton, as on the vertical cover and chapter cards.
- The 19 October number card that compares three companies in two columns (read and write prices)
  is not a template yet. The number card takes one value per row.
- Screenshots, logos and app icons are not reproduced; typed words and letter tiles stand in for them.

## Piece kits

Krish ruled on 29 October 2026 that the code renderer makes every post, that Codex art-directs one
visual idea for each piece, and that Canva is for reference only. The bar is the piece about why
every country wants its own AI, where one object from that story ran through every card and frame.
A piece kit is one such idea, written as code the renderer can use.

### What a piece kit holds

`render/pieces/<piece_id>/` holds these files and nothing else:

- `idea.md`: one plain paragraph that names the visual idea.
- `piece.css`: the look of the idea, built only from the house tokens in `kit.css`.
- `templates/*.html`: the idea at each size. Each page links `kit.css`, then `piece.css`, and ends
  with `fit.js`, so fitting and fonts work as on every house page.
- `templates.json`: the templates, in the same shape as `render/templates.json`, with the kind
  `piece_kit` and the piece's id.

A render job names a piece template as `piece:<piece_id>/<template>`. The synthetic example is
`render/pieces/synthetic-receipt-tape/`: a made-up money story told as one long till receipt.

### What Codex may do

- Invent one idea for one piece, true to that story and no other, and use it on every template.
- Arrange the eight kit colours, the four kit fonts and the brand mark however the idea needs, with
  boxes, borders, gradients, shapes and opacity.
- Write in the piece's own folder only, with no network. `render/ARTDIRECT_PROMPT.md` is its brief.

### What Codex may not do

- Use a colour or font outside the kit, a filter or a blend mode, or change a kit token.
- Use a picture of any kind (an image, a drawing file, a canvas or a video), or draw, describe or
  name a person.
- Reach anything outside `render/`: no web address and no `url()`. Fonts come only from
  `render/fonts`, through `kit.css`.
- Restyle the brand mark. It may only size and place it.
- Reuse an idea. The passports idea belongs to its one piece, so no kit may use it, and no kit may
  copy a house template or another piece's kit.
- Put the piece's title, its claims or a real figure in the kit. Examples are placeholders, as in
  the house file, and the real words are filled in outside this repository.
- Use an em dash, or words a 12 year old could not follow.

### The renderer's checks are the gate

- The static checks: `python growth.py run artdirect check render/pieces/<piece_id>`.
- Two renders of every template that give the same bytes (`--verify`), and the colours and fonts
  the page really painted, held to the kit. A page that asks for anything the renderer refuses, such
  as a remote font or a missing picture, is refused itself.
- A kit that fails any check is removed, and that piece goes out in the house kit (code
  `piece_kit_refused`). `tests/test_piece_kits.py` runs the same checks on every kit here, and shows
  each one failing on a planted colour outside the kit, a remote font and an image.
- Codex works on three pieces a run at most (the scheduled run is on Saturdays) unless a run by
  hand is given another cap, and the run's summary counts the tokens it used. Its log holds counts
  and codes only.

### What his approval binds

- Kits reach this repository only through the pull request "Piece kits for week W", which the
  workflow (`.github/workflows/artdirect.yml`) never merges.
- His approval of a concept in the week's mix plan binds the exact mock hashes: the images rendered
  from these templates with that concept's words. A kit changed after that makes new mocks, and the
  concept needs his approval again.
