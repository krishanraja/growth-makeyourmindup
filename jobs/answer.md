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

1. **Find the real question.** Read this week's public questions about
   makeyourmindup's pieces: Substack and YouTube comments, LinkedIn and X
   replies, and, when one ran, the AEO-Engine result in Control Center
   (the buyer questions makeyourmindup is missing from). Search Console
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
   and that are still unverified. Do not check them by changing anything.
   Then one line, `AEO question: <the question, exactly>`, for AEO-Engine's
   question set (AGENTS.md, "Open setup").
8. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job daily --envelope .scratch/answer.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
