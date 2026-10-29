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
| Covers and share cards sit on deep ink. Number cards and chapter cards sit on ink. | Observed: sampled from the pixels, the 26 October cover, share card and square post are exactly deep ink, and the 19 October number cards and 26 October chapter cards are exactly ink. |
| Evidence cards sit on deep ink. | Interpreted. The 19 October evidence cards use a very dark green that is not a kit colour; deep ink is the nearest kit colour. |
| Muted text and hairlines are a kit colour turned down (lower opacity), never a new grey. | Interpreted. The artwork has soft greys; the kit has none, so the templates fade cream or mint instead. |
| Headlines in Anton, labels in IBM Plex Mono, names and body lines in Archivo, Fraunces kept for subheads. | Observed for Anton, Plex Mono and Archivo on both boards. Fraunces is the kit's own and does not appear on either board. |
| No em dashes anywhere. | House rule. The renderer refuses a field that holds one. |

## The wordmark

| Rule | Source |
| --- | --- |
| "MAKE YOUR MIND/" in cream condensed capitals, then "UP" in mint, with a small mark of three green bars on the left. | Observed on the 26 October vertical cover, share card and square post, and on the 19 October evidence cards. |
| The middle bar is tallest and has cut corners; the bars fade from mint at the top to green at the bottom. | Observed on the 26 October vertical cover, close up. |
| "UP" is wider and heavier than the rest, with a speech-bubble tail under it. | Observed. The templates build it from Archivo at full weight and full width, with a green tail drawn in CSS. The artwork's own letters are rounder; see "What does not match yet". |
| On covers the wordmark sits right above the headline, centred. On evidence cards it sits top left, with the series name in mono on the right and a green hairline under both. | Observed: centred on the 26 October vertical cover and square post; top left on the 19 October evidence cards. |
| Quote, receipt and meme cards use the evidence-card band (wordmark left, series right, hairline). | Interpreted. These pages were not on either board. |

## Headlines

| Rule | Source |
| --- | --- |
| Heavy condensed capitals, tightly leaded. | Observed on the 26 October vertical cover, share card and chapter cards. |
| Two tones: cream lines first, then one accent line. The accent line may wrap. | Observed: cream then butter on the 26 October cover and share card; cream then mint on every 26 October chapter card. |
| The accent is butter, mint or coral, set per piece with the `tone` field. Covers default to butter, chapter cards to mint. | Butter and mint observed. Coral is interpreted: it is a kit colour that neither board used for a headline. |
| A quote card keeps one colour. | Interpreted. A quote is word for word, so colouring part of it would edit it. |

## Versus rows (versus-card, versus-card-tall)

| Rule | Source |
| --- | --- |
| Dark rows with a thin border, the name on the left, a solid colour chip on the right. | Observed on the 26 October vertical cover, share card and square post. |
| The chip text is mono, dark on the chip. Chips go butter, then mint, then lilac. | Butter then mint observed on the 26 October cover. Lilac third is interpreted from the kit. |
| A row with no value is a quiet centred strip of names. | Observed: the third row on the 26 October cover is a strip of small logos with no chip. The template writes names, not logos. |
| The wide card puts the wordmark and headline on the left and the rows on the right. | Interpreted. The 26 October share card has a headshot on the left; that is left out (see below), and the rows take its place. |

## Number cards (number-card, number-card-tall)

| Rule | Source |
| --- | --- |
| A thin accent rule across the top, inset from the edges. | Observed on all three 19 October number cards. |
| A mono eyebrow in the accent colour, such as a series name and a number. | Observed on the 19 October number cards. |
| A mixed-case condensed title in cream, not capitals. | Observed on the 19 October number cards. |
| An optional mono context line in the accent colour, such as a date. | Observed on the 19 October number cards. |
| Each row: an Archivo label, a quieter sub-label under it, and giant condensed numerals in butter on the right, with an arrow for a change ("$2 → $4"). | Observed on the 19 October number cards. The arrow is drawn in CSS so every font shows it the same. |
| Hairlines between rows, an optional closing line in condensed type, and a quiet mono source line at the foot. | Observed on the 19 October number cards. |
| `tone` can turn the rule, eyebrow and numerals mint or coral. | Interpreted. Every number card on the board was butter. |

## Chapter cards (chapter-card, chapter-card-vertical)

| Rule | Source |
| --- | --- |
| A spaced-out butter mono eyebrow, such as "CHAPTER 6 OF 6 · WHAT I'D DO". | Observed on the 26 October chapter cards. |
| A cream headline with a mint second line, left aligned, with the entity name in bold Archivo under it. | Observed on the 26 October chapter cards, which show the company's logo there. The template writes the name in type. |
| No wordmark and no footer on a chapter card. | Observed on the 26 October chapter cards. |
| The vertical size keeps the same layout inside the story safe zones. | Interpreted. Only wide chapter cards were on the board. |

## Evidence cards (evidence-card)

| Rule | Source |
| --- | --- |
| Framed panels. What came in is a cream card with a mono label, the words in bold Archivo and a mono tag, on a green shadow. | Observed on the 19 October evidence card about an inbox test. |
| An arrow from what came in to the first actor. | Observed on the same card. |
| Each actor is a panel with a coloured bar on the left (mint first, lilac second), the name in condensed capitals and a mono status on the right, such as "FLAGGED · SKIPPED". | Observed on the 19 October evidence cards. |
| The first actor's finding is a quoted line in condensed type, with one plain line under it. | Observed on the 19 October inbox card. |
| The second actor's words sit in a cream box with a lilac tag, such as "ACTUAL DRAFT · REDACTED". | Observed in shape on the 19 October cards, where the box holds a screenshot. The template holds typed words instead. |
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
