# AI-tips carousel: the brief for every future edition

First posted Thursday 5 November 2026, in place of an off-day video that did not
render. Krish, 5 Nov 2026: "Can you encode to an engine that future AI tip
carousels can follow without being too literal with imagery and screenshots?
More so, the visual standard, theming, expectations, and standards".

**Who owns what.** This is Growth's brief: what the format is, how its jobs
are chosen and checked, and the look Krish approved for it. Production
standards stay with content-engine (`docs/ENGINE-BOUNDARY.md`, 26 and 28 Oct):
its CAROUSEL-STANDARD, rejection floor and copy lint apply first. A request for
content-engine to adopt the visual section below is queued as a task. Until it
lands, a conflict goes to content-engine's standard, not to this page.

**The engine:**
- **Kit:** `render/pieces/ai-tips-screen/`.
- **Builder and checks:** `scripts/ai_tips_deck.py`.
- **Week files:** `calendar/ai-tips/YYYY-MM-DD.json`.
- **Tests:** `tests/test_ai_tips_deck.py`.

## What it is

- **What the reader gets:** five to ten jobs AI does well right now, one per card. Each card shows the tools
  that do the job, a real image of it being done, one prompt to paste and three steps.
- **The goal:** a post people save and send to a colleague. That serves the North Star's "posts people share
  because they are useful".
- **The cards:** a 1080x1350 Instagram carousel. A cover, the job cards, then a close.
- **When:** off days. Krish, 5 Nov 2026: "off-day stuff is fluid". It can fill a gap, as it did on 5 Nov, or
  run on a planned day. Never on Saturday, which is the good-news carousel, or on Sunday, the rest day
  (ruling of 2 Nov).

## Choosing the jobs

1. **Start from a job a worker has, never from a product launch.** "Catch up on a long thread" is right.
   "Copilot's new feature" is wrong. Krish, 5 Nov 2026: "there are loads of other tools that can do the
   same thing and we should acknowledge those … we should be able to inspire a bit more generally and show
   more practical examples."
2. **Where to find candidates:**
   - the Instagram inspo sheet's new rows;
   - what Krish does himself. He named voice notes into his AI tools, and the notebook audio brief.
   - Leave out launches, funding, research and anything only coders can use.
3. **Two to four tools per job.**
   - Each tool needs its own vendor help page or docs, read this week, with the date recorded.
   - Drop any tool or job that has no such page.
   - Say so in the caption when a tool is a beta, needs a paid plan or a licence, or works in one country
     only.
4. **Order:**
   - The quick daily wins come first (threads, meetings).
   - Bigger set-ups follow (dashboards, agents).
   - The most personal job goes near the end.
5. **No repeats within four weeks.** Neither the job nor its lead tool may repeat.

## The visual standard (approved 5 Nov 2026)

The look is fixed. The words and pictures change each week.

- **Ground and colour.**
  - Every card is ink.
  - Cream carries the words.
  - Mint marks the second headline line, the quote mark, the step numbers and the image frame.
  - Green draws the thin rules.
  - No butter, lilac or coral, and no series name or pill. Krish, 5 Nov: "There is no colour palette for off-day carousels."
- **Type.**
  - Headlines are Anton capitals, centred, in two lines: the job, then the payoff in mint. Krish, 5 Nov:
    "I prefer Anton capitals."
  - The prompt is set in Archivo.
  - Numbers and labels are set in IBM Plex Mono.
- **Card anatomy, top to bottom:**
  - the count and the tool logos;
  - the headline;
  - the image in a mint frame with a soft green glow;
  - a large mint quote mark and the prompt;
  - three steps in columns split by thin green rules.
  - The house mark sits small in the bottom right corner.
  - Nothing overlaps a headline.
- **Premium, not boxed.** No filled boxes under the prompt or steps. Krish, 5 Nov: "make sure the text and
  the boxes beneath feel premium, which they don't right now." Air, rules and type do the work.
- **The cover is a scene.**
  - It is one full-bleed image that would stop a thumb, dark at the foot, with the words on the dark part.
  - Use the house robot or no robot. Krish, 5 Nov: "Either we keep to brand and have my brand robot … or
    you're welcome to be more creative."
  - It may lay real crops of one job across the scene, from first click to result, each with a short label.
    On 5 Nov that was a search, then 22 sources, then an AI podcast.
  - Record the job id, model and prompt for every generation.
  - Ask Krish first, with the image count and credits.
- **The close.** Two lines and one note saying the links are in the caption. No sources, dates or credits on
  any card.

## Images: real, matched, and not too literal

Krish, 5 Nov 2026: "Make sure there is synchronicity between the image and the quote at all times."

- **What the image shows.**
  - The job being done, or its result.
  - Crop to the moment that proves it.
  - It does not have to show the first logo's app. Any of the job's tools will do, and the caption then leads
    with that tool's link.
- **Where images come from, best first:**
  1. Krish's own screenshots. They are the most current and most relatable, and they are safe to post.
  2. Product shots from the vendor's own help page, credited.
  3. A crop of a real result.
  - Never use a title card, a logo slide or a wall of text. That rejected option C's first images.
- **The prompt asks for what the image shows.**
  - If the image changes, change the prompt, and the other way round.
  - The builder fails a card when the image's description and the prompt share no word.
- **Blur before use.** Blur names, email addresses, money, client and venture names, and anything private.
  Krish, 5 Nov: "blur whats necessary".
- **Keep images out of the repository.** It is public. Keep them in a local assets folder, and Drive once
  Krish says so.
- **Ask Krish early.** When the best image is one only Krish can capture, name the exact screen and moment
  to grab. Use a placeholder until it arrives.

## Words

- Plain English at reading age 12.
- No em dash.
- No "Not X, Y" turn.
- No sticker or badge copy.
- Headlines say the job and the payoff, under about six words a line.
- Steps say where to click, under about six words each.
- The prompt is one real sentence a reader can paste.

## Caption

- An intro of two short lines. One of them names who to send it to.
- Then one line per job: the lead tool and its vendor page, then the other tools by name.
- Then the "checked" date, the plan or licence note, and which cards use vendor images.
- At most 2,200 characters (Instagram's limit), and it must pass content-engine's channel copy lint.
- The builder writes the caption from the week file.

## Making one

1. Write `calendar/ai-tips/<date>.json`, copying the last one.
2. Put the logos (from Brandfetch), the screenshots and the cover scene in an assets folder outside the repo.
   Use `logos/<name>.png` for logos, and image paths relative to the folder.
3. Run `python3 scripts/ai_tips_deck.py calendar/ai-tips/<date>.json --assets <folder> --out <folder>`.
   - It checks the week, renders twice to identical bytes, checks the fit, the colours and the fonts, and
     writes the cards, `manifest.json` and `caption.txt`.
   - It exits non-zero on any failure.
4. Look at every card at full size, then have an independent reviewer do the same.
5. Then show Krish. He approves the final deck and caption before anything is scheduled.
   - Sending, publishing, filing to Drive, the board or Buffer, and any spend each need his yes, immediately
     before the step.

## What it is not

- **The Saturday good news.** That is real stories of people AI helped, and it leaves the reader with a
  feeling. This one leaves the reader with an action: where to click.
- **A product review or a ranking of vendors.** Every job names more than one tool.
