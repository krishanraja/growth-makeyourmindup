# Job: the day's distribution pack

Kind `daily`. Read `AGENTS.md`, `PLAYBOOK.md`, `BROWSER.md` and
`docs/ENGINE.md`. This job shares the day's 20-minute queue.

First, before reading any source: `python growth.py cc start --job daily --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Run `python growth.py discover --days 21` and read
   `python growth.py pieces --days 21 --full`. Inspect new, revised, late
   and missing-body records. Read the current article completely. Recovery
   includes a delayed piece from an earlier day, not just today's date.
   A catalog change does not prove a pack was prepared or a post published.
   Check local envelopes and real completion evidence before duplicating work.
2. Record a literal source excerpt for the forwardable finding, named facts,
   quote or dated call. Establish the article/video pair only from explicit
   published links or a human verification record. If unavailable, keep the
   video items blocked and recheck on the next existing job. Empty bodies
   contain no facts. Do not infer them from titles.
3. Choose distribution placements from `journeys.json`, using the reader's
   stage. Apply `knowledge/COPY-DOCTRINE.md` (lead by surface awareness,
   headline grid against `hooks.json`, proof hierarchy). Draft a small candidate set, with one next action per placement:
   - LinkedIn: a useful first-person analysis, topic early, named stake,
     sourced finding and matched article link. A document outline is an
     optional once-weekly asset chosen from pieces already published. Do
     not promise the week's final winner before Friday.
   - X: four to six short posts separated by blank lines. The opening stands
     alone, evidence pays off the hook, and the final post offers a useful
     continuation. The linter weights URLs; preview complex emoji natively.
   - YouTube: pinned comment and community question only after the long
     video is live. For Shorts, audit the related-long-video connection;
     do not promise clickable links in Shorts comments or descriptions.
   - Instagram: three or four Story frames with tension, finding, proof and
     a matched link sticker. A carousel outline is optional. Do not repeat
     the publish-board caption.
   - TikTok/Shorts: a spoken close of at most 15 words, naming makeyourmindup
     and a native continuation. A bio-link ask needs verified eligibility.
   - Spotify: only after a live show and episode URL are verified; draft a
     useful episode continuation. Audit existing notes rather than copying
     the content engine's description work.
   - Search: propose an accurate title, description and concise answer when
     the current piece actually needs them. No invented first-hand testing,
     hard character ranking rules or duplicate SEO article.
   - Partner: at most two individual source-backed kits for people with a
     reason to share. Include a faithful quote, specific benefit and distinct
     tracked placement; never invent an endorsement.
4. Optional lifecycle tasks: next-day discussion, a later relevant evergreen
   retrieval or a due dated-call review. Each gets a distinct placement,
   evidence, why now and expiry when time-sensitive. A monthly call review
   needs the original dated call and a public outcome; otherwise "not due"
   or "not verified". Editorial planning remains outside this engine.
5. Subjective breakout score out of 20 can guide effort, with rationale and
   weak dimensions. It is not measured reach or predicted performance.
6. Run the doctrine's before-handoff passes and critique rubric on each
   kept draft; fix the weakest link first. Prepare a v2 envelope, merge with today's other jobs, keep the selected
   queue only, then check again. Defer unused candidates locally. Deliver
   only under the scheduled-run rule in `AGENTS.md`. No external write in
   an interactive implementation session.
7. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job daily --envelope .scratch/daily.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
