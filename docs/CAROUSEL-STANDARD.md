# Carousel production: content-engine's, a pointer

**Current (26 November 2026).** Ruling, Krish: "I believe that growth should move all asset production to Content
Engine." Content-engine makes every carousel, with its captions, from content-engine's v5 Library (`python scripts/covers/make_covers.py <piece> --out <folder>` for covers and thumbnails, `python scripts/library/make_piece.py <piece> --set <set>` for carousels). Its rules are
content-engine's `docs/ve/cards/library/` (`CAROUSEL-FORMAT.md` above all) and
[content-engine/docs/CAROUSEL-STANDARD.md](https://github.com/krishanraja/content-engine/blob/main/docs/CAROUSEL-STANDARD.md).
This file holds no production rule, and Growth makes no carousel.

Growth plans where and when carousels go (`mix.json`, `docs/MIX.md`), posts the finished ones with content-engine's
captions (`docs/MAKER.md`) and measures them. See [ENGINE-BOUNDARY.md](ENGINE-BOUNDARY.md), "26 November 2026".

## History

- 26 October 2026: production standards moved to content-engine; this file became a pointer.
- 28 October 2026: Growth made derived carousels to content-engine's standard ("take over posting as well as
  creating new assets like carousels"). Superseded on 26 November 2026.
- 13 November 2026: every carousel, meme and Notes image was made in a Claude session with the Codex plugin, from
  piece kits in this repository. Superseded on 26 November 2026: the kits and `render/` are deleted.
