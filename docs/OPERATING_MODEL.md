# Make Your Mind Up: one pipeline, one owner, one ledger

Status: Decided by Krish, 31 October 2026 (his answers are in section 0). First drafted on 31 October 2026. Written after his message of
31 October asking that the sprawl be brought into one standard process, with
this repository in charge of the schedule and of posting.

North Star part this moves: "posts people share because they are useful". The
ideas are the product. A week of homework-style pitches gets no shares. A week of
stories people forward does, and the process below is built to produce them.


## 0. What Krish decided (31 October 2026)

- **The channel is smart entertainment.** It covers the weird, funny and
  quietly huge AI stories of the week, explained in one listen and ending
  on our opinion, never a to-do list.
- **The reaction it aims for** is the one people leave on Hannah Fry's
  shorts, which he shared on 31 Oct:
  - "Imagine if this was your school teacher. You couldn't wait to get to
    class"
  - "Her curiosity and passion for learning new things is infectious"
  - "You get hooked and can't scroll away"
- **The week has 3 heroes and 4 off days.**
  - Mon, Wed and Fri: video plus article.
  - Tue, Thu, Sat and Sun: one lighter post each, made by Growth.
- **Ideas come half and half.** Each day gets at least one option from his
  Inspiration asks and one from engine research. Every ask is used,
  combined or declined with a reason.
- **Every idea on the board is a full story pitch**:
  - headline;
  - hook;
  - real examples;
  - what's going on;
  - where we land;
  - date and format;
  - source card.

  Carousels show every card.
- **The publish board is his one daily surface.** It shows one status per
  day and no checklists. Growth keeps the ledger behind it.
- **He approves five things:**
  1. the Sunday ideas;
  2. the creative mocks;
  3. the scripts;
  4. the finished cuts;
  5. each post's mock, once.

  Growth then schedules and posts it automatically, and holds anything that
  drifts from the mock.
- **Frequent audits of recent posts.** They check for anything technically
  wrong. Where nothing is wrong, they give a short, objective reflection on
  what could be better next time. A rule change it suggests waits for his
  yes.
- **Fixes run in this order:**
  1. ideas quality and his asks;
  2. the board clean-up;
  3. the ledger and posting;
  4. Substack pictures.
- **Done on 31 Oct:**
  - The 9 Nov board was re-pitched and republished (build `c0e8568c`).
  - The 2 Nov off-day options were written to content-engine
    `docs/plans/2026-11-02-week/offdays-growth.json`, for that board's next
    build.

---

## 1. Why Krish is saying what he is saying

Every complaint in his 31 October message comes from one of five causes. Each
cause is traced to code or data, so the evidence is listed.

### R1. Nobody owns the whole week, so nothing is in one place

- About twenty sessions touched the next two weeks between 28 and 31 October.
  Each owned a slice. None owned the week.
- State lives in four places that disagree:
  - content-engine's boards (content.krishraja.com);
  - the `content_ideas` table;
  - Growth's ignored `.scratch/` runs;
  - two NOW.md files, each telling its own story.
- Growth has no file that says, for each coming day: what posts, its title,
  where its assets are, and what is left to do. (`calendar/v1.json` is an
  undated template.)
- Result: "not up to date with where everything is at", and "everything's kind
  of everywhere".

### R2. The ideas engine writes to a formula, so every idea reads like homework

- Every option on the 9 Nov Ideas tab has the same shape: *a fact, then a colon,
  then "before you renew/sign/buy, check X".* Two examples:
  - "...if your company tracks AI usage as a target, switch to tracking what the
    work produced".
  - "...ask for them in writing at your next outsourcing renewal".
- The house rule "close on the one thing he would do" was meant for the end of a
  script. It was applied to the pitch itself, so each idea arrives already
  reduced to an action item.
- That is why the Amazon idea, the Saturday option and the Sunday option read as
  "so boring". Every option offers a compliance tip, and none offers a story.

### R3. His Inspiration asks are filtered out before the ideas run sees them

Evidence: `content-engine/apps/control-plane/api/_inspirationSources.ts:136-187`,
plus a live read of `inspiration_items` on 31 Oct.

- **Dismissed cards vanish for good.** The Claude safety-test card (the Rundown
  AI post about Claude and the grandmother on the train tracks, card `a397253e`)
  carries his words: *"the headline makes you want to know more but the topic is
  actually about AI ethics, which is, on paper, one of the most boring topics out
  there... we could pump out carousels kind of like this in my branding."* It was
  dismissed on 26 Oct, so the Sunday run never saw it.
- **"Study the style" cards are never topics.** The "Anthropic just replaced Git"
  card (`45e0ead0`) went in as a style reference. The run is told never to use
  such a card as a topic, so his GitHub-competitor ask never reached Wednesday.
  The engine then found the former head of GitHub's agent-first code store on
  its own and pitched it without his framing.
- **The run reads 50 cards at once, and most are old.** Thirty-plus of the 50
  "fresh" cards are untagged 22 Oct imports. Nothing ranks his typed *why* above
  a bare file.
- Result: "full of stories, and not really pulling in any of my asks".

### R4. The board was built for a Krish who ticks boxes

Evidence: `content-engine/scripts/post-pack/week_board.py`.

- **Two title fields, never reconciled.** The board shows `content_ideas.idea`,
  the original Sunday pitch sentence, unless a made publish page overrides it.
  When he picks a title nothing writes it back. Live on 31 Oct:

  | Day | What the record still says | What he chose |
  |---|---|---|
  | Mon 2 Nov | "Anthropic's Own Hiring Data Is the Most Honest Labour Market Report Published This Year" | "Claude's AI is eating the jobs of its own humans. What does that signal for the rest of us?" |
  | Mon 9 Nov | "When an AI app millions of people loved goes bust, who walks away with the money?" | "Why is Disney eating the scraps of bankrupt Character.AI?" |

- **Checklists everywhere.** He no longer ticks, but each made day still draws
  publish-step tabs, a checklist meter, per-channel ticks and record ticks
  (`week_board.py:1996, 2301, 2419, 538`).
- **Off-day options have no date and no comment box.** An off-day card carries
  only a weekday key (`week_board.py:1630-1676`). A meme gets no control of its
  own, and the recorded Tuesday option has Approve and Skip but nowhere to type.
- **No duplicate-topic check.** Tue 10 (the three-question lock-down video) and
  Thu 12 (the "three keys" carousel) both come from the same "Reading is free"
  idea through two different card ids. The three-week no-repeat rule is prose in
  the skill, not code.
- **The 2 Nov week has no filler options.** The off-day lane started on 28-29
  Oct, after that week's ideas were written, and the first Sunday run targeted
  9 Nov. Nothing ever proposed Tue 3, Thu 5, Sat 7 or Sun 8.

### R5. Substack articles lost their pictures (suspected cause; not yet proven)

- Monday 9 Nov's article on the board has six headings and zero pictures.
- The publish-page manifest lists only covers. Article pictures need
  `after_heading` entries (`content-engine/scripts/post-pack/publish_manager.py:63-79, 282-289`),
  and nothing fails when an article has none.
- The figures planned in the creative direction never reach the manifest.
- A second suspect: Substack dropping pasted `data:` images.
- Neither is proven. This stays "suspected" until a test reproduces it.

---

## 2. What the channel is (a draft for Krish to correct)

These are his own words from the last two weeks:

- "turn boring topics into something really entertaining"
- "the headline is so random it makes you need to know more"
- Hannah Fry: "a real intellectual but she comes across as really relatable,
  honest, and sincere"
- "a positive ray of sunshine"
- "a hilarious video meme"
- "fun and real-world"
- "makeyourmindup more like a professional media channel"
- "a slow, non-technical listener... feel like they get a really complex topic
  in a short amount of time"
- "the last paragraph... sounds a bit bossy and preachy"

**Draft one line.** *Make Your Mind Up takes the strangest, funniest and quietly
biggest things AI did this week and makes them make sense to a busy leader in
one listen, so they walk into Monday with an opinion of their own.*

The name is the promise: you leave having made your mind up. That means an
opinion, not a to-do list.

**Four tests every idea must pass before it reaches the board:**

1. **The "wait, what?" test.** The headline is a true thing that sounds
   absurd, and a stranger would tap it. "Claude would rather let a grandmother
   die than leak song lyrics" passes. "Check your contract before your AI
   supplier fails" does not.
2. **The pub test.** It rests on a real-world example people already know (a
   song, a brand, a famous fail), not on a report.
3. **The one-mechanism test.** It explains one thing about how AI actually works
   that the listener did not know. That is the "complex topic in a short
   amount of time".
4. **The make-your-mind-up test.** It ends on our take: what this means, good
   and worrying, and the one line we believe. It never ends on a list of orders.

The three series stay as they are:
- **follow.the.money:** who pays and who wins.
- **under.the.hood:** how it actually works.
- **mind.the.gap:** how people think and what they expect.

The tone across all three moves from an advisory brief to a show.

**The pitch format.** Every option on every board is written in this shape,
never as a one-sentence "fact: do X":

- **Headline:** the "wait, what?" line.
- **Hook:** the first 10 seconds as he would say them.
- **The real-world examples:** two or three.
- **What's actually going on:** the one mechanism.
- **Our take:** one line.
- **Format and day:** a dated slot.
- **Built from:** which of his Inspiration cards, quoted.

---

## 3. The one pipeline

There is one owner per stage and one place each stage's output lives. The
**ledger** (section 4) shows every stage's state for every day.

| # | Stage | What happens | Who does it | Where it lives | Krish's touch | Done when |
|---|---|---|---|---|---|---|
| 1 | **Inspired** | He saves a post, clip or screenshot and types why. A card with his words is an **ask**. | Inspiration House (inspirationhouse repo) | `inspiration_items` | Save, and type why | The card is on the ledger's asks list |
| 2 | **Ideate** | Saturday's run writes three options per publishing day and two per off day, in the pitch format. Every day has at least one option built from his asks. Options may combine asks. No topic repeats within three weeks (checked in code). | content-engine `plan-week`, in GitHub Actions | the week's Ideas tab | none | Every ask is used, merged or declined with a stated reason |
| 3 | **Agree** | On each option, including off days and carousels: Pick, Combine, Comment inline, or Reject with a reason. Every option shows its date. Carousels show card-by-card words and pictures. | Krish, on the board | board presses | **Sunday: one sitting** | Every slot has a pick or an empty-on-purpose |
| 4 | **Flesh out** | Narrative lock. **One title of record**, written to the piece, then the board, YouTube, Substack and Buffer all read it. Scripts to the listening rule. Teleprompter. | content-engine `make-piece` | the piece record | Sign the lock, approve the scripts | Scripts are in Teleprompter |
| 5 | **Produce** | He records. The article is written with its inline figures, and an article with zero figures fails. Off-day assets are made from approved mocks. | Krish records; content-engine makes the hero assets; Growth makes the derived posts | Drive post folder | Record | All assets are filed |
| 6 | **Post-produce** | Cuts, thumbnails and covers; independent review; Approve for publish; sealed manifest. | content-engine (ve / quick-edit) | `0 Publish/manifest.json` | Watch it, then one Approve | Manifest sealed |
| 7 | **Post** | Schedule, post, tick, measure and learn. Autonomous inside what he approved; LinkedIn stays his click. | **Growth (this repo)** | Buffer and the ledger | none | Posted, measured, recorded on the ledger |

**Ruling (Krish, 2026-10-31):** this repository is responsible for automatically
scheduling and posting everything, and for staying on top of what's what, where
everything is, and what needs to be done every day.

- content-engine keeps making the hero assets and keeps the board as Krish's
  pressing surface.
- Growth holds the calendar and the posting, and is the one place that answers
  "what is happening on day X".

---

## 4. The ledger: one place for what's what

`calendar/ledger.json` in this repository has one row per day per slot. It is
rebuilt every morning by a workflow from the engine API, Buffer and
`inspiration_items`. Each row holds:

- date, slot (hero or off-day), series and format;
- piece id and **title of record**;
- the stage it is in (1 to 7);
- links to its assets (Drive, board tab, manifest);
- the next action, who owns it, and when it is due;
- whether it is posted, with its URLs.

The board's Today view reads the ledger. Checklists come off Krish's view (the
records stay underneath). In their place he sees one status per day and only the
asks that need him.

### Snapshot, 31 October 2026 (hand-read; the daily rebuild is not built yet)

| Date | Slot | Piece | Title of record | Stage | Next action (owner) |
|---|---|---|---|---|---|
| Mon 2 Nov | hero, follow.the.money | `9a0c97af` | Claude's AI is eating the jobs of its own humans. What does that signal for the rest of us? | 6, cuts in a fourth review round | Pass review, build the board tab (video session); Krish watches and approves |
| Tue 3 Nov | off-day | none | none | 2 | Options needed (section 5) |
| Wed 4 Nov | hero, under.the.hood | `b63d2507` | AI used to reply. Now it acts first. Claude Duet is the start. | 6, final polish | As Monday |
| Thu 5 Nov | off-day | none | none | 2 | Options needed |
| Fri 6 Nov | hero, mind.the.gap | `7083d6ad` | Why every country wants its own AI, and what that means for your business | 6, approved and sealed | Growth schedules it once `BUFFER_API_KEY` is set |
| Sat 7, Sun 8 | off-day | none | none | 2 | Options needed |
| Mon 9 Nov | hero, follow.the.money | `b358e788` | Why is Disney eating the scraps of bankrupt Character.AI? | 6, waiting on Approve for publish; **article has no pictures** | Restore the figures (R5); Krish approves |
| Wed 11 Nov | hero, under.the.hood | not picked | none | 3 | Krish picks (section 5) |
| Fri 13 Nov | hero, mind.the.gap | not picked | none | 3 | Krish picks (section 5) |
| Tue 10 to Sun 15 | off-days | options on board | none | 3 | Krish picks |
| unscheduled | under.the.hood | `36886e0b` (AI in music, his ask of 31 Oct) | none | 2 | Offer for a Wednesday; two clips routed with sound on |

---

## 5. The 9 November week, re-pitched in the format above

These are proposals. Nothing is on the board until he says yes. Every figure is
from his Inspiration cards or the 30 Oct run's sources, and goes through the
fact gate before it is used.

### Fri 13, mind.the.gap: the big piece he asked for (combines three ideas)

- **Headline:** *Claude would rather let Grandma die than break copyright.*
- **Hook:** "Put an AI at the lever of the trolley problem. Grandma on one track,
  a copyrighted song lyric on the other. It saves the lyric. Then a coin toss
  told an AI what to think, and 86% of analysts went along with it."
- **The real-world examples:**
  - his Rundown AI card (`a397253e`; the facts are to be checked against the
    primary source before use);
  - Anthropic's own trial, in which analysts sided with a coin-toss agent 86% of
    the time;
  - AI paired with a strict checker found a mistake that had sat in a maths
    proof since 1986, and a year's worth of security bugs in a PDF reader in one
    week.
- **What's actually going on:** an AI's "judgment" is a set of trained rules.
  It is rigid where it was drilled hard (copyright) and pliable where it wasn't
  (your decision). On its own it is a poor judge. Paired with a strict checker it
  is the best error-finder we have ever had.
- **Our take:** don't trust an AI's conscience; trust its checker.
- **Built from:** cards `a397253e` and `c00cd4e0`, and the 30 Oct option `56bb9c22`.
- **Carousel cut:** the "random headline" carousel he asked for on card `a397253e`.

### Wed 11, under.the.hood: who is software being built for now?

- **Headline:** *Anthropic got so big it broke Git. Now software is being
  rebuilt for robots.*
- **Hook:** "In May, Anthropic merged about 2,500 code changes a day. By
  September, 30,000. The tool every developer on earth uses just couldn't
  keep up."
- **The real-world examples:**
  - his "Anthropic just replaced Git" card (`45e0ead0`; the figures are from its
    transcript, to be checked);
  - the former head of GitHub's new code store, built for AI agents first
    (`b38fa06d`);
  - Home Depot having one company's AI grade another's (`054159ab`).
- **What's actually going on:** when most code is written by agents, the tools
  are redesigned for agents as the main reader and humans as reviewers.
- **Our take:** the next software you buy was designed for an AI to use and a
  human to check, so ask who it was built for.
- **The fun part:** an animated "day in the life" of a 2027 codebase in which
  the humans are the slowest thing in the building.

### Amazon tokenmaxxing, re-pitched (a wildcard for Wed 11 or a later Monday)

- **Headline:** *Companies started ranking staff by how much AI they burn. You
  can guess what happened next.*
- **Hook:** "Pay people per dead cobra, and they breed cobras. Rank engineers by
  AI used, and they burn AI."
- **The real-world examples:**
  - the colonial cobra bounty;
  - lines-of-code targets;
  - Amazon's own memo that "tokenmaxxing is at odds with frugality" (`f3fcd5e1`).
- **Our take:** whatever you measure, people will game; so measure what got
  done.

### Off days

The Tue 10 / Thu 12 duplicate is fixed, every item is dated, and the carousels
are spelled out card by card.

**Tue 10: "Lock down your AI tools" (to camera).**
- Recorded option, kept as is.
- It now takes inline comments; that waits on the board change.

**Thu 12: the AI-to-AI meme, now dated.**
- Replaces the "three keys" carousel, which repeated Tuesday.
- *"When your AI agent and your customer's AI agent spend forty minutes politely
  agreeing on a refund nobody asked for."*
- Made fresh in the brand kit from the format of his saved clip (`2b582f5a`),
  with the format credited.

**Sat 14, carousel 1: "Good things AI did this week".**
- His "positive ray of sunshine" card (`87a82f7f`), in the infographic style he
  saved (`501c4fd1`).
- Seven cards, 4:5, house palette:

  | Card | Words | Picture |
  |---|---|---|
  | 1 | GOOD THINGS AI DID THIS WEEK (date range) | A big sun-yellow headline on the dark house ground; a small hand-drawn sun |
  | 2 to 6 | One story each: a five-word headline, one line on what happened, one line on why it matters, source and date in small type | A real photo or screenshot of the thing, cropped tight, with a yellow number badge 1 to 5 |
  | 7 | "Which one surprised you? Follow for one of these every Saturday." | Five small thumbnails of cards 2 to 6 in a row |

- The five stories are chosen on Friday 13 from that week's news, each checked
  against its primary source the same day.

**Sat 14, carousel 2: "Spot the AI".**
- Replaces the "checklist" level-up move.
- A quiz carousel teasing his AI-in-music piece (`36886e0b`).

  | Card | Words | Picture |
  |---|---|---|
  | 1 | ONE OF THESE HITS STARTED AS AN AI DEMO. WHICH? | Three record sleeves in a row, house style |
  | 2 to 4 | One song each, with one clue | That song's sleeve |
  | 5 | The answer: "Movin' To The Sun" began as a Suno demo and reached UK No. 2 | The sleeve with a yellow ring |
  | 6 | "The full story drops Wednesday" | The episode cover |

- This only runs if the music piece is scheduled; otherwise it moves with it.

**Sun 15: "AI is a puppy" (clean to camera, 1-2-3).**
- Replaces the "cheaper model" level-up move.
- Built from his two puppy-analogy cards (`7f43c6b5`, `8685d47b`).
- Three beats:
  1. It wants to please you.
  2. So it says what you want to hear.
  3. So ask it for the case against.
- It links back to Friday's piece.

### Filler for the 2 November week (none was ever proposed)

- **Tue 3:** a meme on Monday's title, "Claude's AI is eating its own jobs".
- **Thu 5:** a three-panel "AI used to reply / now it acts first" from
  Wednesday's piece.
- **Sat 7:** "Good things AI did this week", as Sat 14 above.
- **Sun 8:** a 30-second short from Friday's "where your AI was built decides
  what it refuses" piece.

Growth makes all four from approved mocks once he says yes.

---

## 6. What changes in code, and who does it

Each item is a separate session, so none collides with the video session that
is finishing Mon 2 and Wed 4.

1. **content-engine, the board:**
   - one title of record (`content_ideas` gains `title`; every surface reads it);
   - checklists hidden from Krish's view behind a layout flag;
   - every off-day option dated and given a comment box;
   - a duplicate-topic check in code;
   - carousel options rendered card by card.
2. **content-engine, ideation:**
   - asks are never dropped: a dismissed card or a style-only card still
     counts as an ask whenever his typed *why* names a topic;
   - his typed cards are ranked first;
   - the pitch format in section 2 replaces the "fact: do X" `so_what`;
   - every ask must be accounted for on the board.
3. **content-engine, Substack figures:**
   - reproduce the missing pictures on Mon 9 Nov;
   - make an article with zero figures fail the publish check;
   - restore the planned figures.
4. **Growth (this repository), the ledger:**
   - `calendar/ledger.json` and a daily workflow that rebuilds it;
   - the board's Today view reads it;
   - the `/posted` tick accepts off days.

Krish's own setup, needed before anything posts by itself (`docs/SETUP-ONCE.md`):

- `BUFFER_API_KEY`
- `GROWTH_WRITEBACK_TOKEN`
- the Buffer plan, before the trial ends on 7 Nov
- the first post on each route
