# Correction: the makeyourmindup brand kit (11 November 2026, final)

Read this if you were briefed on the brand kit earlier on 11 November 2026. Some of
those instructions are now wrong. Where they disagree with this file, this file wins.

## The rule now

There is **one** brand folder in Drive: `makeyourmindup > 1 Brand kit (permanent)`
(id `1kOCNq1F-MD3u2SGvF8hoqUKo4DPnyuNi`). Everything brand lives there, licensed music
included. There is no other brand folder.

Find any asset through `social/brand/library.json` in krishanraja/growth-makeyourmindup
(Drive ids), or content-engine's `docs/DRIVE.md`, "The brand kit". The Drive index is
`00 START HERE - the brand kit index.txt` at the top of the kit
(id `1UFKDBBpqRHlpsFVxNNeBjl-3d9oul_qd`).

## What changed since the earlier instructions

| Earlier instruction | Now |
|---|---|
| Music lives in `00_Brand-Assets/07_Music` (id `1pmPWx8vTOZuUXkp-WjhLlCTvof8MrRxK`); do not move it | **Wrong.** `00_Brand-Assets` is deleted. Music lives in `1 Brand kit (permanent)/Music` (id `1oHyJ9A5et5_uKW7QTq1VHX0NuGwwQVri`). File new tracks there. |
| `1 Brand kit (permanent)/Music` is a mirror; never file a track there by hand | **Wrong.** It is now the one music home. content-engine reads it as `runtime.music_root` (`config/studio.json`) and `config/music-library.json` (krishanraja/content-engine#539). |
| `00_Brand-Assets` holds only music; never take brand from it | **Gone.** The folder is in the Drive bin. Never recreate it. |
| Old copies sit in `_Archive/PREVIOUS VERSIONS.../2026-11-11 brand kit cleanup` (id `1rBsiOrLfT_VZBy8oVb8uuwI9603TUcAO`) | **Deleted** to the Drive bin with everything in it: the duplicate kit v1.5, old channel art, launch exports, old Canva links, the frozen 28 Oct video formats and old index drafts. There is nothing old to read. |
| Drive index ids `1pRypOHEj5ELjd2ybPhBB3pg-22T_JE_L` or `1h16heWQZWcuF6KxciQeUctQeggnA7LPF` | Superseded and deleted. Use `1UFKDBBpqRHlpsFVxNNeBjl-3d9oul_qd`. |

## Still true

- `1 Brand kit (permanent)/Style references` (id `1J4cWCWaAtdUMEEsUs27pdWm3H50jGSPC`) is a
  mirror of `Ventures > Inspiration > Production Inspo` that content-engine fills. Never file
  a clip there by hand, never publish one.
- Do not move or rename: `Intro sting`, `character`, `fonts` and `Music` inside the kit.
  content-engine reads them by exact path.
- The 43-page component book of 27 Oct (`guidelines/makeyourmindup-Brand-Book.pdf`) swaps
  Monday and Wednesday on page 4. follow.the.money is Monday, under.the.hood Wednesday,
  mind.the.gap Friday.
- Where the kit and krishanraja/makeyourmindup disagree, that repository wins.
- The Canva kit is `kAHZOJ-K6I8` (`social/brand/kit.json`).

## One action outstanding

Each home computer pulls content-engine main before its next music pass, so
`runtime.music_root` points at the kit's `Music` folder. Until it does, its music step fails
loudly in Control Center; it does not pick a wrong track.

## Do not

- Do not create a second brand folder or an archive of brand copies.
- Do not take brand from the other ventures' `00_Brand-Assets` folders (Heartside, Mindmake,
  Legibility); they are not makeyourmindup's.
