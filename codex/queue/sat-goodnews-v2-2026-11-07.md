---
card: sat-goodnews-v2-2026-11-07
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

# Saturday good news, round 2: photo-led cards with almost no words

## Goal
Krish's words on the first render (2 Nov 2026), every one of them the brief:
"the cover page needs to feature a real world image which will generate immediate visual interest. For all cards, there is WAY too much text - all sources should go in the carousel post description. The images should be visual imagery, not screenshots of text. The text should be center aligned on the story cards"

Rework `render/pieces/off-sat-goodnews/` (five stories, 1080x1350):

1. `cover`: a real photograph fills the whole card edge to edge (`photo`, full bleed, `object-fit: cover`, centred). The headline sits on it, centred, large, in Anton, readable over any photo: lay a soft ink gradient (from `var(--ink)` at the bottom to `transparent`) under the words. A small `date` in the mono face. No intro, no other words. Fields: photo, headline, date.
2. `item`: the photo leads. It fills at least the top 62% of the card, edge to edge (no paper frame around it), `object-fit: cover` with `object-position: center 30%` so faces stay in. Below it, all centred: the `headline` (Anton, large, at most three lines) and one short `line` (Archivo, at most two lines). The mint clipping tab with the `number` stays (choices 1 to 5). Remove the source, date and credit fields entirely: they go in the post's description. Fields: number, photo, headline, line.
3. `close`: centred. `headline` and `takeaway` only (for example, that the sources are in the caption). Drop the date.
4. `idea.md` and `templates.json`: describe the photo-led cards; examples stay placeholders; a photo's credit is never a field.

## Contract
Everything in `render/ARTDIRECT_PROMPT.md`, "The rules the renderer checks". Text that can grow sits in `data-fit` boxes with `data-max` and `data-min`. The filled `<img>` has class `photo`; style it in `piece.css`. The eight kit colours as `var()` only, the four kit fonts, no remote anything, no em dashes, no percentages.

## Acceptance (every command must exit 0 inside your sandbox)
python3 growth.py run artdirect check render/pieces/off-sat-goodnews
python3 -m unittest tests.test_photo_field tests.test_piece_kits

## Return
Your final message is only JSON matching content-engine's config/ve/task-result.schema.json:
{"card": "sat-goodnews-v2-2026-11-07", "files_changed": [...], "commands": [{"cmd": "...", "exit_code": 0}], "open_questions": [...]}
Stop after two failed attempts at the same acceptance command and report the failure in open_questions.
