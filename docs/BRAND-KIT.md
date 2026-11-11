# The brand kit: one home, one index

Krish, 11 November 2026: "We need a canonical Brand Kit for maximum consistency.
Then, when we've cleaned this up, the engine needs to know where to go to get
whatever it needs at any time."

## The rule

There is one brand folder: **`makeyourmindup / 1 Brand kit (permanent)`**
(id `1kOCNq1F-MD3u2SGvF8hoqUKo4DPnyuNi`). Every logo, colour, font, token, photo,
template, sting, character pose and licensed music track lives there. Music is in its
`Music` folder, which content-engine reads as its music root.

**To find any asset, read `social/brand/library.json`.** It names each asset, its Drive
id, its path and what it is for. Fetch by id where you can. The Canva kit is in
`social/brand/kit.json`; the same colours and fonts as code are in `render/kit.css`.
content-engine's map is its `docs/DRIVE.md`, "The brand kit".

Where the kit and the makeyourmindup repository (`apps/cover`, `docs/brandbooknew`)
disagree, the repository wins.

## What changed on 11 November 2026

There were two brand folders, `1 Brand kit (permanent)` and `00_Brand-Assets`. Krish:
"you need to delete one of these top level folders and ensure old shit is not left anywhere,
and that stuff in currently use is not trashed."

- Kept and moved into the kit: the 43-page component book of 27 Oct (`guidelines`), the
  Claude design system package, and three PowerPoint starters (`templates`).
- Music: `00_Brand-Assets/07_Music` held the same six tracks as the kit's `Music`, byte for
  byte. content-engine now reads the kit's `Music` (krishanraja/content-engine#539).
- Deleted to the Drive bin (recoverable for 30 days): `00_Brand-Assets`, and every old copy:
  a duplicate of kit v1.5, old channel art and launch exports, launch HTML, old Canva concept
  links, the frozen 28 Oct video formats and a superseded index.
- `Style references` stays in the kit: a mirror of `Production Inspo` that content-engine
  fills; never file a clip there by hand.

## Known conflict

The 27 October component book says Monday is under.the.hood and Wednesday is
follow.the.money (its page 4). That is wrong. follow.the.money is Monday, under.the.hood
Wednesday, mind.the.gap Friday. Its colours are right.

## Do not move

content-engine reads these by exact path: `1 Brand kit (permanent)/Intro sting`,
`/character`, `/fonts` and `/Music`. The top-level folder names in `READ ME FIRST.txt` are
found by path on the home computers.
