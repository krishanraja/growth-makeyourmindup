---
card: offday-kits-2026-11-02
kind: piece_kit
model: gpt-6.1-sol
effort: medium
max_minutes: 90
max_calls: 120
spend_id: ad5ecb69-73f6-411a-a2ce-ca4c76fe3498
write_allow: [render/pieces/off-tue-translator/**, render/pieces/off-tue-claudejobs/**, render/pieces/off-thu-nospend/**, render/pieces/off-sat-sovereign/**, render/pieces/off-sat-goodnews/**]
read: render/ARTDIRECT_PROMPT.md, render/KIT.md, render/kit.css, render/templates.json, render/templates/**, render/fit.js, render/pieces/synthetic-receipt-tape/**
never: NOW.md, docs/**, calendar/**, engine/**, git commands, network, MCP tools, publishing, new dependencies, edits outside write_allow, any existing piece kit, the passports idea
---

# Piece kits for the 2 Nov week's off days

## Goal
Krish, 2 Nov 2026: "Can you get Codex to produce a mockup of tomorrow's meme video for production as well?" and "let's get the rest of the week's ideas produced as well".

Build five piece kits, one per piece below, following `render/ARTDIRECT_PROMPT.md` exactly (it is your brief; its rules are the gate) and `render/KIT.md`, "Piece kits". One visual idea per piece, true to that piece's story and no other, used on every template in its kit. Examples stay placeholders that describe their slot; the real words are filled in later.

1. `off-tue-translator` (meme video, Tue 3 Nov). Story: two identical AI agents across a table, each sure the other is the translator, forty minutes to agree a refund nobody asked for, one human waiting in the corner. Templates: a 1080x1920 storyboard frame used for 4 to 6 beats, with a fixed caption band ABOVE the scene for a one-line quote of up to 80 characters (field `caption`, required), a subtitle line, and a beat label; plus a 1080x1920 cover. No animation: each frame is a still beat of the video.
2. `off-tue-claudejobs` (meme carousel, Tue 3 Nov). Story: the junior rungs of the career ladder are the ones AI does first; who trains the seniors of 2030. Templates: 1080x1350 cover with a huge headline, body card, close card. Its visual quality must not dip beneath the video production quality (his words).
3. `off-thu-nospend` (to-camera short, Thu 5 Nov, plates around his recording). Story: a personal AI that spends and sends without asking, fenced by one rule, "no spending, no sending". Templates at 1080x1920: a two-line title card; a simulated chat with a reply bubble (made-up names only); a simulated order confirmation; a simulated email "reply all" banner; a "BLOCKED" stamp state for each fail (an `options` field). Funny and clearly made up. No logo: company names in type only.
4. `off-sat-sovereign` (meme carousel, Sat 7 Nov). Story: a deadpan duty-free shopping guide to buying AI by its rules, joking at the buyer's shopping logic and each place's AI rules, never at people. Templates: 1080x1350 cover, shelf card (a product box with a label field), close card with one empty shelf space.
5. `off-sat-goodnews` (carousel, Sat 7 Nov). Story: three good things AI did this week, each card a real news item with its source and date. Templates: 1080x1350 cover, item card with `headline`, `why_good`, `source` and `date` fields, close card.

## Contract
Everything in `render/ARTDIRECT_PROMPT.md`, "The rules the renderer checks", for every kit: house sizes and safe areas, the eight kit colours as `var()` only, the four kit fonts, no pictures, no person, no remote anything, no animation, the house wordmark markup if used, plain words, no em dashes, no percentages, placeholder examples. Five different ideas; none may copy another, a house template or an existing kit.

## Acceptance (every command must exit 0 inside your sandbox)
python3 growth.py run artdirect check render/pieces/off-tue-translator
python3 growth.py run artdirect check render/pieces/off-tue-claudejobs
python3 growth.py run artdirect check render/pieces/off-thu-nospend
python3 growth.py run artdirect check render/pieces/off-sat-sovereign
python3 growth.py run artdirect check render/pieces/off-sat-goodnews

## Return
Your final message is only JSON matching content-engine's config/ve/task-result.schema.json:
{"card": "offday-kits-2026-11-02", "files_changed": [...], "commands": [{"cmd": "...", "exit_code": 0}], "open_questions": [...]}
Stop after two failed attempts at the same acceptance command and report the failure in open_questions.
