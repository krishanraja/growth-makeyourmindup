# Job: the weekly answer piece

Kind `daily` (it is a distribution draft from a published piece, so it uses
the existing kind, wall and close event; Saturday has no day pack, so its
run id never collides). Platform `substack`, placement `answer-piece`.
Read `AGENTS.md`, `PLAYBOOK.md`, `BROWSER.md`, `docs/ENGINE.md` and
`docs/CHANNEL_PLAYBOOK.md`, "Search and AI answers". This job shares the
day's 20-minute queue with the front door.

What it makes: at most one answer-first draft a week. It takes one real
question a reader asked, answers it in the first lines from a piece Krish
has already published, and links back to that piece. Search engines and AI
assistants quote pages that answer a question plainly near the top; readers
who ask the question want the same thing. The draft goes to Krish behind
the `post` wall with its exact words. He decides whether and where it is
published (a Substack post, or a section on makeyourmindup.ai). The engine
never publishes it.

First, before reading any source: `python growth.py cc start --job daily --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

AEO-Engine is the one AI-answers specialist (Ruling, Krish, 2026-11-12):
it asks the AI assistants, never this engine. The runner reads the
publication's standing from the directive (`ai_answers`, `engine/ai_answers.py`)
and asks AEO to track the real reader questions on file in
`config/ai-answer-questions.json`. The engine also proposes its questions to
Krish (Ruling, Krish, 2026-11-13): the set in
`config/ai-answer-questions-proposed.json` goes to his list once, as one
strategy ask whose exact words are the questions, with its evidence in
`docs/ai-answers/`; on his yes the runner writes exactly his version into
`config/ai-answer-questions.json` (marked `krish_approved`) and asks AEO for
them. Never add an unapproved question to the proposed set's file once it is
sent: a new set is a new file and a new `proposal_id`.

AEO's win kits reach Krish through this engine (Ruling, Krish, 2026-11-13).
Once Control Center serves them (`features.ai_answers_detail`), `cc start`
writes the ignored `.scratch/cc/ai-answers.txt`: up to five kits, highest
priority first (AEO's priority: a higher number matters more), each a
question AEO says the publication can win, with its title, target page,
capsule rules, H2s, the hosts of the pages to beat, its site fixes and its
off-site moves, then the misses and moves. The kit words stay in that file
and in this session: never in a committed file, a report line or a public
log. A site fix or off-site move that would put author, Person or E-E-A-T
work under Krish's name is already left out (R100: no content refers to him,
and no article is authored by him); never add one back. Until the detail is
served the file says so, and step 1 reads the misses and moves as before.

1. **Find the real question.** Read `.scratch/cc/ai-answers.txt` first: a
   kit's question is a real buyer question AEO measured, so it comes before
   every other source, the first kit in the file first. A kit is a brief, not a draft:
   its capsule rules and H2s shape the answer, its pages to beat say whom
   the answer must outdo, and its site fixes go to the final message as host
   checklist items for Krish (step 7). Every fact still comes only from his
   published pieces (step 2); a kit's words are never copied into the draft.
   With no kit, read this week's public questions about
   makeyourmindup's pieces: Substack and YouTube comments, LinkedIn and X
   replies, and AEO-Engine's reading of the publication in the directive's
   `ai_answers` (`misses_and_moves`: AEO's kits first, then the questions
   another site is cited first on, then AEO's moves). When you find a real reader question, add it
   to `config/ai-answer-questions.json`, word for word, so AEO tracks it. Search Console
   queries count when Krish has shared a reading. Save the question as
   evidence: kind `source_thread` with its real `created_at` for a public
   comment, `dashboard` for an AEO or Search Console reading, `audit` for
   a question a human verified. Keep the reader's words; never invent,
   merge or "tidy" a question into one nobody asked. Private messages stay
   out of evidence and out of git. If there is no real question this week,
   draft nothing: prepare an envelope with no items and go to step 8, so
   the report holds "Nothing was prepared this run", and say in the final
   message that no real question was found. An empty week is a correct
   result.
2. **Match it to a published answer.** Run `python growth.py discover --days 21`
   and `python growth.py pieces --days 21 --full`. The answer must already
   be in a piece Krish published; record the literal excerpt as a
   `published_piece` evidence. A question the pieces do not answer is a
   topic for Krish, written in the final message, not a draft.
3. **Skip duplicates.** Read the local envelopes from earlier weeks. If the
   same question already has an answer piece, propose an update to it only
   when the source changed; never a second page for the same question.
4. **Draft answer-first** (the shape `check` enforces):
   - Line 1: the reader's question, as they would type it, ending in `?`.
   - Then a blank line and the answer in at most 60 words, plain enough to
     be quoted alone, in Krish's voice and only from the excerpt.
   - Then the why: the evidence from the piece, named sources and dates,
     each claim next to its proof. Subheads, when used, are the follow-up
     questions a reader would ask next.
   - Where it leads: the piece's dated call, if it made one, word for word.
   - What I don't know yet, when the piece says so.
   - The full piece: one link from
     `python growth.py link <piece URL> substack daily --asset <asset_id> --placement answer-piece --variant a`.
   Write it under Krish's approved voice rules (`.scratch/cc/voice-rules.txt`, "His approved voice rules" in `AGENTS.md`): how it is written only, never what it is about, and never in a score or review.
   Apply `knowledge/COPY-DOCTRINE.md` and the house rules. No percentages,
   no em dashes, no invented numbers or first-hand testing the piece does
   not show. The draft is new useful text that answers one question; it is
   never a copy or a rewrite of the article, and never a page written for
   machines. The same words are what every reader and every crawler sees.
5. **Review before the queue.** Read the draft against the source excerpt,
   claim by claim. Make at least one alternative opening answer and keep the
   one a reader could quote without the rest of the page. Note in the
   envelope's `why_now` which question it answers and where it was asked.
   Give it priority 2 (a live conversion blocker from the front door
   outranks it), about 8 minutes, and a `success_check` such as "the opening
   answer stands alone and every claim matches the cited excerpt".
6. Prepare a v2 envelope (`.scratch/answer.json`), merge it with today's
   other envelopes in one queue, keep the selected work only and check
   again. Defer the draft with its reason if the budget is spent. Deliver
   only under the scheduled-run rule in `AGENTS.md`. No external write in
   an interactive implementation session.
7. In the final message, list the host checklist items from
   `docs/CHANNEL_PLAYBOOK.md` ("Host checklist") that this draft depends on
   and that are still unverified, and the site fixes of the kit the draft
   answers, each as an item for Krish to apply. Do not check them by
   changing anything. Then one line, `AEO question: <the question, exactly>`,
   for AEO-Engine's question set (AGENTS.md, "Open setup").
8. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job daily --envelope .scratch/answer.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.

**Recording a published answer piece.** Krish publishes an answer piece
himself; the engine never does. When a run finds one of an earlier week's
drafts live (read the page itself, logged out, on `home.makeyourmindup.ai` or
`makeyourmindup.ai`), mark its question shipped in
`config/ai-answer-questions.json`, so AEO-Engine checks whether it is cited:

    {"question": "<the question, exactly as on file>", "shipped": {"url": "https://home.makeyourmindup.ai/p/<slug>", "shipped_at": "YYYY-MM-DD"}}

Add the question first, word for word, if it is not on file. The url is the
live page's own https address on one of the file's `domains`; `shipped_at`
is the day it went out, as the page shows it. Only a page you read today is
marked, never one you expect or one Krish described; a mark is never
invented, never moved to another question and never set by the engine.
`python growth.py --self-test` checks the file's shape
(`engine/ai_answers.py:problems`). Commit the file with a message naming the
job and date. Once Control Center serves the detail, the runner tells AEO of
the shipped pieces with its next request, and on their own (`mode: append`)
once each time the list changes, recorded in the file as `shipped_sent`.
