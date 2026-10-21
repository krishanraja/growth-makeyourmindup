# Changes Krish made to the growth engine

- 2026-10-21 (later): Krish: "surely you can leave notes in the growth
  repos for those engines, do the makeyourmindup one yourself". The setup
  he would otherwise do by hand is now an "Open setup" list at the top of
  `AGENTS.md` for whichever session can do it: scheduling the ninth job,
  and carrying each answer piece's question to AEO-Engine (the `answer`
  job now prints it). The website half of the host checklist was applied
  on www.makeyourmindup.ai in krishanraja/makeyourmindup#23; its status
  is recorded in `docs/CHANNEL_PLAYBOOK.md`.

- 2026-10-21: Krish asked, across his repositories, for a favicon, social
  cards, a GEO and AEO strategy, AI crawler access and a recurring AEO
  "blog" strategy visible to Google and AI (his request as relayed to this
  session). This repository has no website, so the strategy and a host
  checklist he applies himself went into `docs/CHANNEL_PLAYBOOK.md`
  ("Search and AI answers: GEO and AEO"), with a pointer in `PLAYBOOK.md`.
  A ninth job, `jobs/answer.md` (Saturday 09:00, kind `daily`), drafts one
  answer-first piece a week from a real reader question and a published
  piece; `check` enforces its shape and evidence. A planned
  `answer-first-pieces` experiment and an `answer_piece` hook surface were
  added. Nothing is published; the new scheduled task exists only after he
  says "create the automations" again.

- 2026-10-19: Krish: "all of these growth engines need to be imbued with this
  knowledge". Preserved The Copywriting, Offers and Demand Corpus and its
  summary byte for byte under `knowledge/corpus/`, added both to the
  manifest, and added a test that checks every manifest file's bytes and
  SHA-256. `knowledge/COPY-DOCTRINE.md` applies the corpus to makeyourmindup
  and lists where his rules override it. `PLAYBOOK.md` and the drafting jobs
  (daily, radar, pitches, partners, swaps, conversion, report) read it at
  the drafting or review step. Schedules, automations, the envelope and the
  Control Center protocol are unchanged.

- 2026-10-19: Krish: "make each engine adopt its brief now". The engine
  reports through the Control Center growth engine protocol
  (`docs/CONTROL-CENTER-BRIEF.md`): every scheduled job starts with
  `growth.py cc start` and ends with `growth.py cc finish`, and
  `.github/workflows/control-center.yml` answers the morning
  `cc-growth-directive` dispatch with an offline check and an honest report.
  Development sessions still make no Control Center writes. Posts, pitches
  and asks go to Krish as proposals with their exact words; nothing sends.

- 2026-10-18: Krish: "Make sure the corpus I gave you is stored inside the
  repo as well for future reference if needed." Preserved the three uploaded
  Markdown originals under `knowledge/corpus/` and indexed all four uploads
  in `knowledge/README.md`. The uploaded Word document is byte-identical to
  the existing `knowledge/10k-operating-system.docx`; retained that canonical
  original. The manifest records paths and checksums. Archiving source
  instructions does not activate them or change the operating rules.

- 2026-10-14: no Substack Notes or WhatsApp. Krish: "I don't think I need
  Substack notes or WhatsApp to be honest, right now." (`research.md` still
  describes a Notes pack; it does not run.)
- 2026-10-14: the engine runs from Codex, apart from the content engine.
  Krish: "I'm going to run the growth engines from codex, so ensure the
  growth pack is set up to be fully self contained and a completely
  different system. Content Engine needs nothing to do with it, but Control
  Center certainly does."
- 2026-10-14: the 10K operating system becomes the engine's doctrine.
  Krish: "store as well as properly propogate this knowledge through the
  growth-maeyourmindup repo engine so it is ready to do its job 10/10 from
  day one with browser access to each channel". Stored in `knowledge/`,
  applied in `PLAYBOOK.md`, browser rules in `BROWSER.md`. New jobs:
  partners (the 100-account map and ask ladder) and the front door
  (conversion). Numbers run daily from the dashboards. Every own link is
  tracked. Notes stay off (his 14 Oct ruling).

- 2026-10-15: The AI-visibility check (AEO-Engine) goes fortnightly and is named in AGENTS.md as this engine's visibility measure, read from Control Center. Krish: "happy with the fortnightly AI visiblity check, but I think stuff like that needs to move to the growth-makeyourmindup repo? That is now the dedicated growth engine?" The machine stays in its own repo because it holds model keys and spends; this engine owns reading it.

- 2026-10-17: Krish: "you are not to do any actual work in control-center,
  only pass me a brief once you have completed your work". Complete and
  verify growth-repository changes locally, then provide the handoff.
  This task makes no Control Center writes and no changes to other repos.
  V2 adds evidence records, asset and placement identity, late-publication
  recovery, honest metric windows, relationship events, experiments and a
  shared daily queue. Existing eight schedules remain unchanged.
