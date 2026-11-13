---
card: sat-goodnews-v3-2026-11-07
kind: piece_kit
model: gpt-6.1-sol
effort: medium
max_minutes: 45
max_calls: 60
spend_id: f2bfdae8-1fcd-4698-9bdc-47d50afc3fa4
write_allow: [render/pieces/off-sat-goodnews/**]
read: render/ARTDIRECT_PROMPT.md, render/KIT.md, render/kit.css, render/templates.json, render/templates/**, render/fit.js, render/pieces/off-sat-goodnews/**, scripts/render_mocks.mjs
never: NOW.md, docs/**, calendar/**, engine/**, scripts/**, git commands, network, MCP tools, publishing, new dependencies, edits outside write_allow, any other piece kit
---

# Saturday good news, round 3: no numbers, a light branded skin

## Goal
Krish, 2 Nov 2026, on round 2: "use Anwita on the cover, then approve once you get rid of the numbers in the top left. and give it a light branded skin of some sort". He approves round 2 once these are done, so change nothing else: the photos, the centred headline and one line, the full-bleed cover and the close all stay exactly as they are.

1. Remove the number tab from `item` entirely: the mint box, its markup, its CSS and the `number` field (templates.json fields, required, example and choices).
2. A light branded skin on every card (cover, item, close), from the house kit only, as `render/KIT.md` "The wordmark" describes:
   - the house wordmark (the exact house markup, `render/ARTDIRECT_PROMPT.md`), small: on the cover centred just above the headline; on item and close centred at the top of the text panel, above the headline;
   - one thin `var(--mint)` hairline (2 to 3 px) across the top edge of the text panel on item cards, where the photo meets the panel, and the same line under the wordmark on the close;
   - no series tag anywhere: this off-day post belongs to no series.
   - Light means light: the wordmark no wider than 360 px, nothing else added, the photo and the headline stay the heroes.

## Contract
Everything in `render/ARTDIRECT_PROMPT.md`, "The rules the renderer checks". The eight kit colours as `var()` only, the four kit fonts, the wordmark is the house markup exactly (size and place it only), no remote anything.

## Acceptance (every command must exit 0 inside your sandbox)
python3 growth.py run artdirect check render/pieces/off-sat-goodnews
python3 -m unittest tests.test_photo_field tests.test_piece_kits

## Return
Your final message is only JSON matching content-engine's config/ve/task-result.schema.json:
{"card": "sat-goodnews-v3-2026-11-07", "files_changed": [...], "commands": [{"cmd": "...", "exit_code": 0}], "open_questions": [...]}
Stop after two failed attempts at the same acceptance command and report the failure in open_questions.
