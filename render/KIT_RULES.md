# The rules for a piece kit Codex builds from a card

Since the ruling of 13 November 2026, every carousel is made in a Claude session, with the Codex plugin building it,
as in the other usual workflows; memes and Notes images go the same way (content-engine's docs/CAROUSEL-STANDARD.md, "How a
carousel is made"). A Claude session writes the words and the direction, then a Codex card (content-engine's
`ve card`, kind carousel, meme or notes_image) that points here. This is the card's brief for the kit itself: Make Your
Mind Up is a publication that takes one AI story apart three times a week (who gets paid, what is real, and where it
leads), and the kit is ONE visual idea for the piece the card names, built as a few HTML templates that the code
renderer (`scripts/render_mocks.mjs`) turns into the post's images. The card names the piece, its folder, the brand
palette for its day and the inspiration cards ticked for it; it never carries the real words.

## The bar

The best art direction this publication has had so far came from a piece on why every country wants
its own AI. It treated each country's AI as a passport. Passport cards carried fields for the
country, where the model was built and where it runs, and that one object travelled through every
card, every storyboard frame and every screenshot. One metaphor, true to that story and to no other,
used everywhere in the piece. That is the bar for ambition.

Do not use passports, travel documents or anything close to them. That idea belongs to that piece
alone and is never reused. Invent the idea that belongs to this piece: an everyday object, place or
system that a reader recognises in a second and that makes this story's argument visible. Use it on
every template in the kit.

## What you build

You are working in the folder the card names, `render/pieces/<piece_id>/`. Write exactly these files and
nothing else:

1. `idea.md`: one paragraph in plain English that names the visual idea and how each template uses
   it. Short sentences, under 20 words each. No heading.
2. `piece.css`: the look of the idea, built only from the house kit's tokens.
3. `templates/<template-id>.html`: two to four templates, each a page of the same idea at one size.
   No template is a closing slide: every carousel ends on the house close
   (`../../templates/carousel-close.html`: the piece's takeaway, Subscribe free and the wordmark small in
   the bottom right), so no template id names a close, ending, outro, takeaway or call to action.
4. `templates.json`: the list of templates, in the same shape as `../../templates.json`.

Read these first, and copy their patterns: `../../kit.css` (the house tokens), `../../templates.json`
(the shape of a template entry), `../../templates/carousel-cover.html` and
`../../templates/story-frame.html` (how a template is built), and `../../KIT.md` (the house look).
Never change any file outside your folder.

## The cover, the body cards and the tall meme (the ruling of 15 Nov 2026)

The ruling's words: "the front cover card does not look like a front cover. It looks like all the rest of the cards", the cards
"assume that people have a working knowledge", "use too few words" and "aren't using the page space centrally or
correctly. They look too bland and too plain", and "The POV computer meme, it's not centralized on the screen".
content-engine's `docs/CAROUSEL-STANDARD.md` and `docs/COVER-STANDARD.md` own the standard; these are the kit's rules
for meeting it.

- **The cover is its own template, and it looks like a front cover.** A carousel kit has exactly one cover template
  (an id ending in `cover`), drawn unlike every body template: its own ground or field, its own layout, a headline
  larger than any body card's. Never the body card with bigger words, and never a full scene on every card, which
  is how a cover stops looking like one. The house cover (`../../templates/carousel-cover.html`) shows the pattern: a
  full field in the tone colour, a masthead, the deck's biggest headline and an ink band that says swipe.
- **A body card carries one full plain sentence of up to 20 words a stranger can follow**, with its subject, its unit
  and what it is compared with on the card itself, never leaning on another card (no So, But, This or It to open,
  no "12x"). `growth.py run carousel lint` holds the words to it.
- **A body card uses the page, centred.** The sentence is set centred in the safe area under a substantial visual
  anchor (a framed figure, an object drawn in boxes, a real photo), never plain ground and never a column pushed to
  one side. Mark centred blocks with `data-centred`; the renderer reports every line and the check refuses a
  centred line more than 16 px off the centre line, and any word or mark outside the 80 px margin.
- **A tall meme is built on `../../templates/meme-tall.html`**, never by hand: the headline centred above a fixed
  clip window (x 200 to 880, y 600 to 1240), the wordmark and credit centred under it. `growth.py run meme compose`
  puts the clip into the window, fitted and centred. A media slot (`data-slot`) more than 4 px across or 48 px down
  from the centre is refused.

## The rules the renderer checks

A kit that breaks any of these fails the card's acceptance (`python growth.py run kit check`, then the two renders
and `python growth.py run kit painted`) and is not used.

- `templates.json` is `{"schema_version": 1, "kind": "piece_kit", "piece_id": "<piece_id>",
  "about": "...", "templates": {...}}`. Each template entry has `file`, `width`, `height`, `fields`,
  `required` and `example`, and may have `choices`, `note` and `safe`, exactly as in the house file.
  A field is `text`, `rows`, `options` or `photo`, and each one appears in the template as `{{name}}`,
  `{{rows:name}}`, `{{options:name}}` or `{{photo:name}}`.
- Sizes: only the house sizes: 1080 by 1350, 1080 by 1080, 1080 by 1920, 1200 by 675, 1314 by 1080,
  1600 by 900, 1920 by 1080 or 1280 by 820. A 1080 by 1920 template has
  `"safe": {"top": 270, "bottom": 600}` and sets `--top: 270px; --bottom: 600px; --side: 200px;`: everything
  that must be read sits in the clear box every channel leaves, y 270 to 1320 and x 200 to 880 (content-engine
  `config/channel-safe-zones.json`; the old bottom of 340 ran words into Instagram's caption from y 1320).
- Each template starts `<!doctype html>`, sets `--w` and `--h` to its size in a `:root` rule, links
  `../../../kit.css` then `../piece.css`, ends with `<script src="../../../fit.js"></script>`, and
  has one element with `class="frame"`. Text that can grow sits in a `data-fit` box with
  `data-max` and `data-min` font sizes, as in the house templates.
- Colours: only the eight kit colours, always written as `var(--ink)`, `var(--ink-deep)`,
  `var(--cream)`, `var(--green)`, `var(--mint)`, `var(--butter)`, `var(--coral)` or `var(--lilac)`,
  plus `transparent` and `currentColor`. No hex codes, no colour names, no `rgb()`, `hsl()` or
  `color-mix()`. Turn a colour down with `opacity`, never with a new colour. No `filter` and no blend
  modes. Never redefine a kit token.
- Fonts: only `var(--heading)` (Anton), `var(--sub)` (Fraunces), `var(--body)` (Archivo) and
  `var(--mono)` (IBM Plex Mono). They load from the house kit. No `@font-face`, no `@import`, no
  at-rules of any kind.
- No pictures: no `<img>`, `<svg>`, `<canvas>`, `<picture>`, `<video>` or `<iframe>`, and no
  `url()`. Draw the idea with HTML boxes, borders, gradients and `clip-path`.
  The one exception is a `photo` field (`{{photo:name}}`): an empty slot the renderer fills at render time with a
  real picture of the story from a local file: a photograph, never a screenshot of text. The kit never holds
  the picture itself. Whose picture it is travels with the render job and goes in the post's description, never
  on the card.
- No person: never draw, describe or name a real person. Never name the publication's founder.
  Write company and product names in type, never as a logo.
- No remote anything: no `http`, `https`, `data:` or `//` address anywhere, and no other script.
- The brand mark is the official logo file, never type (ruling of 2026-11-03: a logo set as type is a fabricated logo).
  Use exactly `<div class="brandmark"></div>` and only size or place it. On a carousel it is
  `<div class="brandmark corner"></div>`, small in the bottom corner of every card, never at the top.
- Words: plain English that a 12 year old can follow. No em dashes. No percentages. No hype.
- The `example` values are placeholders that describe their slot, such as "The first payee" or
  "series.label". Never put the piece's title, its claims or any real figure in the kit: the real
  words are filled in later, outside this repository.
- Every template must render the same pixels every time: no randomness, no clock, no animation.
- Layout: every line of text and the mark inside the safe box for its size (above), centred blocks on the centre
  line, a media slot centred, and a carousel kit's cover drawn unlike its body cards. `python growth.py run kit
  painted` reads the renderer's report and refuses each miss by name.

When you are done, reply as the card's Return section says, and put the idea in under 15 words in it.
