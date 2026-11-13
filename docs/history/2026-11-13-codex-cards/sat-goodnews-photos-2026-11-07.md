---
card: sat-goodnews-photos-2026-11-07
kind: piece_kit
model: gpt-6.1-sol
effort: medium
max_minutes: 60
max_calls: 80
spend_id: f2bfdae8-1fcd-4698-9bdc-47d50afc3fa4
write_allow: [render/pieces/off-sat-goodnews/**]
read: render/ARTDIRECT_PROMPT.md, render/KIT.md, render/kit.css, render/templates.json, render/templates/**, render/fit.js, render/pieces/off-sat-goodnews/**, scripts/render_mocks.mjs, tests/test_photo_field.py
never: NOW.md, docs/**, calendar/**, engine/**, scripts/**, git commands, network, MCP tools, publishing, new dependencies, edits outside write_allow, any other piece kit
---

# Saturday 7 Nov good news: five real stories, each with its real picture

## Goal
Krish, 2 Nov 2026: "take the five stories, and build out the carousel with real life imagery or screenshots". His standard for every Saturday (content-engine docs/CAROUSEL-STANDARD.md, "Saturday good-news carousel"): exactly five stories of real people who benefited from AI, each with its source and date.

Rework the existing kit `render/pieces/off-sat-goodnews/` (the desk tray of dated news clippings stays the idea). The renderer now has a `photo` field (`{{photo:name}}`, ARTDIRECT_PROMPT.md "No pictures"): an empty slot filled at render time with a real press photo or a screenshot of the source, never held in the kit, always with a required `credit` text field.

1. `item`: the clipping now carries the real picture. A large photo slot (`photo`, at least 960 px wide and 640 px tall, `object-fit: cover`, top-anchored so a screenshot's headline stays in view) pinned to the clipping like a news photo; under it `headline`, `why_good`, then a source line with `source`, `date` and `credit` in the mono face. The slot works for a portrait photo and for a wide screenshot. Required: photo, credit, headline, why_good, source, date. Add a `number` text field (1 to 5) shown as the clipping's tab.
2. `cover`: the tray holds five folded slips (it holds three today). Fields stay headline, date, intro.
3. `close`: files the stack of five. Fields stay.
4. `idea.md` and `templates.json`: say five, describe the photo slot; examples stay placeholders.

## Contract
Everything in `render/ARTDIRECT_PROMPT.md`, "The rules the renderer checks": house sizes (1080x1350), the eight kit colours as `var()` only, the four kit fonts, no picture except the photo slot, no remote anything, plain words, placeholder examples. The photo element gets its look from `piece.css` through `.photo` (the class the renderer gives the filled `<img>`).

## Acceptance (every command must exit 0 inside your sandbox)
python3 growth.py run artdirect check render/pieces/off-sat-goodnews
python3 -m unittest tests.test_photo_field tests.test_piece_kits

## Return
Your final message is only JSON matching content-engine's config/ve/task-result.schema.json:
{"card": "sat-goodnews-photos-2026-11-07", "files_changed": [...], "commands": [{"cmd": "...", "exit_code": 0}], "open_questions": [...]}
Stop after two failed attempts at the same acceptance command and report the failure in open_questions.
