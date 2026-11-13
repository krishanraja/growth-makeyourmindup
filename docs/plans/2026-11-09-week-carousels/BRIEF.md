# Codex brief: the pictures for three derived carousels (week of 9 November 2026)

Krish, 13 Nov 2026: "build those 3 carousels to world class branded standards using the codex plug in". His standard
for every carousel (content-engine `docs/CAROUSEL-STANDARD.md`, "The ten-second swipe"): "a complete layperson is
swiping through these cards at light speed and needs to be able to follow the story within 10 seconds". Every card
after the cover shows its point as a picture: bars to scale, the thing jammed, the people, the hand-off.

The words are locked. They are in `mon/deck.json`, `wed/deck.json` and `fri/deck.json` (each card's `headline`,
`line` and `picture`). Do not change any deck. Your job is one picture per card, from card 2 to the last card, as
the card's `picture` field describes it.

## What you make

For each day folder (`mon`, `wed`, `fri`) and each card N from 2 to the last: `<day>/devices/card-N.svg`.

- One `<svg>` element, `viewBox="0 0 920 620"`, `width="920" height="620"` (the last card: `viewBox="0 0 920 520"`).
  It is pasted inline into the card page, below the headline and line, above the wordmark. Leave transparent
  ground; the card is ink.
- Colours, only these, as hex: ink `#0C1512`, deep ink `#070D0B`, cream `#F4EFE4`, green `#2F6B5C`, mint
  `#7EF0C0`, and the day's series colour: mon `#FFD84D`, wed `#B7A6FF`, fri `#FF6A4D`. Cream may be faded with
  `opacity` / `fill-opacity`; no other colour, no gradients except ink-to-transparent or green glow.
- Fonts, only these family names (the page loads them): `Anton` (big numbers, labels in capitals), `Archivo`
  (short words), `Plex` (IBM Plex Mono, tiny tags). Words inside a picture are few: a label, a number, a name. At
  least 26px so they read at phone size. No sentence that repeats the headline or line.
- Real logos, where a company is named, as `<image href="../devices/<file>.svg" .../>` from the files already in
  that day's `devices/` folder (mon: Disney, Character.AI, Google, OpenAI, Netflix, Warner Music; wed: Suno,
  Deezer, Grammys; fri: Meta, Amazon, Duolingo, Shopify). Never redraw or set a logo as type. A dark logo sits on a
  cream tile. Never draw a tacky outline box around a logo.
- Numbers to scale: a bar for 50% is exactly half the bar for 100%; 1 to 3% is a sliver. Every number shown must be
  in the deck's line or picture field, nothing else.
- The look: flat, bold, editorial, like a Bloomberg or FT explainer drawn for a phone. Thick shapes, generous space,
  one focal object per card, the series colour on the one thing the eye should land on, mint for the answer, green
  for structure. Real objects drawn simply (a box, a door, a form, a gauge, a leaderboard). No clipart, no stock
  icons, no emoji, no cartoon faces, no people with faces (simple silhouettes are fine), no robots, no gimmicks.
- No card numbers, no "1/8", no page dots, no URL, no source strip, no small print, no em dashes anywhere.
- The last card's picture is calm and centred: one object, centred on x = 460.

## The per-card pictures (the deck's `picture` field, made concrete)

**mon (follow.the.money, butter #FFD84D)**
2. A horizontal timeline: "AUG 2024" on the left with the Google logo and three small silhouettes walking off the line
   towards it, labelled "FOUNDERS"; "OCT 2026" on the right with the Character.AI logo and a butter stamp "BUST".
3. The Disney logo on a cream tile, a thick line to the OpenAI logo labelled "SORA" in a phone shape, the phone dark with
   a butter "CLOSED" sign hung across it; "$1B DEAL" over the line, struck through.
4. 66 small cream silhouettes (count them: 66) in a grid flowing right towards the Disney logo; left behind on the
   floor, a butter pile of folders labelled "LAWSUITS" beside the Character.AI logo.
5. Two columns: "RENT" (faded) and "OWN" (butter). Under OWN, the Disney, Netflix and Warner Music logos on cream
   tiles, each with a small butter "BOUGHT" tag; an arrow from RENT to OWN.
6. A large open box, empty inside, drawn in cream line and ink, one faint chat bubble drifting up out of it.
7. A checklist on a cream card: four rows with empty tick boxes: "FOUNDERS STILL THERE?", "YOUR TOOL ITS MAIN
   PRODUCT?", "SHORT OF CASH?", "COLLECTING LAWSUITS?".
8. (last, 520 tall) One key on a hook, centred, the key's bow in butter, a small tag on it reading "PLAN B".

**wed (under.the.hood, lilac #B7A6FF)**
2. Four stacked horizontal layers like a cake slice, bottom to top: "HER WORDS", "AI APP'S FIRST SONG" (no logo: the piece could not confirm whether Suno or Udio made it), "DJ'S REBUILD", "SINGER'S VOICE" (lilac); a thin dashed lilac thread running from the AI layer up through
   the top one, labelled "AI VOICE, STILL UNDER".
3. A tall closed studio door labelled "STUDIO" with a lock; under its gap a demo (a cassette or a phone waveform) in
   lilac slides through to the near side.
4. Two bars to scale from the same baseline: "NEW UPLOADS" at a bit over 50% filled lilac "50%+"; "LISTENING" at a
   sliver "1 TO 3%"; the Deezer logo above.
5. A slide deck seen at an angle, three layers peeled apart: "IDEA" (cream), "AI DRAFT" (lilac), "FINISHED BY
   PEOPLE" (mint).
6. Three labelled rows on a cream form: "IDEA:", "DRAFTED BY:", "CHECKED AND SIGNED BY:" with blank lines.
7. (last, 520 tall) A sign-off form, centred, its three lines filled with simple scribbles and a mint tick by the
   signature line.

**fri (mind.the.gap, coral #FF6A4D)**
2. A leaderboard panel with three rows; top row "TOKEN LEGEND" with a coral bar overflowing the panel; a token
   counter reading "60 TRILLION" (Meta's 30-day total); the Meta and Amazon logos at the top.
3. A one-cent coin, a stack of rat tails tied with string, and beside it one simple rat silhouette with no tail,
   walking away. "1902" in Plex. Simple, a little funny, not gory.
4. Two bars from one baseline: "AI QUERIES" falling (an arrow down, "-30%") and "SALES" rising coral ("+7%"); a small
   strip of struck-through blocks labelled "JUNK" falling out of the queries bar.
5. Three U-turn arrows side by side, each with a logo above: Meta, Amazon, Duolingo; under them "USAGE SCORES"
   struck through.
6. A cream review form with lines; the line "AI USAGE" crossed out with a thick coral stroke.
7. (last, 520 tall) One round gauge, centred, labelled "RESULTS", its needle in mint pointing up and right.

## Checks before you stop (every one must pass)

    python3 check_devices.py

It confirms each file exists, parses, uses only the listed colours and fonts, references only existing logo files and
holds no em dash. Then run `python3 render.py mon && python3 render.py wed && python3 render.py fri` and
`node shoot.mjs mon` (and wed, fri), open every `*/cards/card-N.png` you made and look at it: nothing overlaps the
headline, the line or the wordmark, nothing is cut off, every word reads at phone size.

## Never

Touch the decks, the style files, `render.py`, `shoot.mjs`, the kit folder or anything outside this folder; use the
network; run git; publish, post or upload anything.

## Return

A short list: each file you made, and anything you could not do.
