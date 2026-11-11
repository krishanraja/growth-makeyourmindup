# The brand kit: one home, one index

Krish, 11 November 2026: "We need a canonical Brand Kit for maximum consistency.
Then, when we've cleaned this up, the engine needs to know where to go to get
whatever it needs at any time."

## The rule

The canonical makeyourmindup brand kit is the Drive folder
**`makeyourmindup / 1 Brand kit (permanent)`** (id `1kOCNq1F-MD3u2SGvF8hoqUKo4DPnyuNi`).
Every logo, colour, font, token, photo, template, sting and character pose comes
from there. The one exception is music, which stays in `00_Brand-Assets/07_Music`
because content-engine reads that exact folder.

**To find any asset, read `social/brand/library.json`.** It names each asset, its
Drive id, its path and what it is for. Fetch by id where you can: ids survive
moves, paths do not. The Canva kit and its templates are in `social/brand/kit.json`;
the same colours and fonts as code are in `render/kit.css`.

Where the kit and the makeyourmindup repository (`apps/cover`, `docs/brandbooknew`)
disagree, the repository wins.

## What changed on 11 November 2026

There were two brand folders. `1 Brand kit (permanent)` is the one the engine writes
to and content-engine reads from. `00_Brand-Assets` had been an older copy of the kit
from 7 October. Nothing was deleted. Everything was moved:

| From | To | Why |
|---|---|---|
| `00_Brand-Assets/makeyourmindup-Brand-Book.pdf` (27 Oct, 43 pages) | `1 Brand kit/guidelines/` | The fullest component and token reference |
| `00_Brand-Assets/06_Claude-Design-System` | `1 Brand kit/` | The design system package and its tokens |
| Three editable `.pptx` starters (social post, ad, deck) | `1 Brand kit/templates/` (new) | Brand templates belong in the kit |
| `00_Brand-Assets/01_Identity` (a second copy of kit v1.5) | Archive | Duplicate |
| `00_Brand-Assets/03_Social-and-Ads` (older channel art, launch exports) | Archive | Superseded by `2 Channel art` and `3 Posts` |
| `00_Brand-Assets/04_Decks` (now empty), `05_Historical-and-Source` | Archive | History |
| `00_Brand-Assets/CANVA-SOURCES.md`, `START-HERE.txt` | Archive | Old Canva concepts; the live Canva kit is `kAHZOJ-K6I8` |
| `06_Claude-Design-System/Video formats (frozen 28 Oct 2026)` | Archive | Superseded video design proof |
| `1 Brand kit/Music` | Archive | Byte-for-byte copy of `07_Music`, which the engine reads |
| `1 Brand kit/Style references` | Archive | A copy of `Ventures > Inspiration > Production Inspo`; inspiration is never brand |

Archive: `_Archive/PREVIOUS VERSIONS - archive, not current, do not use/2026-11-11 brand kit cleanup`
(id `1rBsiOrLfT_VZBy8oVb8uuwI9603TUcAO`). Never read it for current brand.

## Known conflict

The 27 October component book says Monday is under.the.hood and Wednesday is
follow.the.money (its page 4). That is wrong. follow.the.money is Monday,
under.the.hood Wednesday, mind.the.gap Friday, as the v1.5 brand book, the
Instagram highlights and every post folder say. Its colours are right.

## Do not move

These are read by exact path from another engine: `1 Brand kit (permanent)/Intro sting`
(content-engine `config/intro-sting.json`), `1 Brand kit (permanent)/character`
(`config/ve/character.json`) and `00_Brand-Assets/07_Music` (`config/music-library.json`).
The top-level folder names in `READ ME FIRST.txt` are found by path on the home computers.
