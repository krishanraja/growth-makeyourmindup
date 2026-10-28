# Changes Krish made to the growth engine

- 2026-10-28: built to be sent. Krish: "for the growth repo, think about
  virality in the content, I dont think there is enough of it at the moment.
  that comes from the shareability from one human to another in a "you will
  like this" kind of way. I am not talking about just saying "share this with
  your friends" in the comments, I am talking about ensuring all the produced
  snackable content is likelier to be shared for a specific reason."
  - Every snackable package (meme, carousel, single image, short video, Story,
    Note) declares a share block: a specific sender and receiver, one job from
    a fixed list, the exact DM line the sender would type, the everyday moment
    that brings it to mind and a standalone check
    (`social/schemas/package.schema.json`, `social/share.json`).
  - Generic share calls to action in post copy are refused; the share comes
    from the content, never a request.
  - Each snackable format names its share mechanic in its delivery checks, and
    `hooks.json` gains a share formula, a house hypothesis like the rest.
  - A blind send-test reader (`crew/send-test/`) sees only the post and must
    name the declared receiver and job before Krish sees it.
  - Sends per reach and saves per reach become the snackable lane's primary
    measure in What-Works, house hypotheses until MYMU's own dated data
    confirms them.

- 2026-10-27 (later still): "apply the Control Center change yourself". For
  this one change only, rule 7 (stay in this repository) is lifted: the
  session implements the GA4 brief in krishanraja/control-center on branch
  `claude/growth-mymu-ga4-engine` (a utm_content and event breakdown in the
  mymu snapshot, and `web_analytics` in this engine's directive, protocol
  1.10.0). Every other Control Center rule still holds.

- 2026-10-27 (later): three more rulings.
  - Google Analytics: "just get google analytics from control center, might
    be easier." Control Center already reads GA4 property mymu
    (G-VC5V9LDE17) daily but does not pass it to engines or break it down by
    `utm_content`. The exact change is briefed in
    `docs/briefs/2026-10-27-control-center-ga4-read.md` (primary route). The
    direct reader stays as an unused fallback with no credentials set.
  - Substack handle: "substack handle should be mindmake". Checked 27 Oct:
    @mindmake already belongs to a Substack profile named Mindmake that is
    neither of the two profiles tied to makeyourmindup (mindmakerlive, the
    owner, and krishraja1). The rename waits until Krish confirms that
    profile is his and frees the handle, or names another.
  - Audit authority: "yes extend". The 2026-10-21 existing-field audit
    authority (titles, captions, descriptions, links, broken profile links,
    subscription-link alignment) now also covers the Facebook Page and
    Threads. LinkedIn stays his own: the engine never edits it. Bio,
    positioning, pins, creative and re-uploads still need his approval.

- 2026-10-27: Krish adopted the reference architecture for this engine
  (`docs/plans/2026-10-27-engine-architecture.md`) and ruled, in one
  question batch and three messages:
  - Channels: he chose to add **Substack Notes** and **Threads**. This
    supersedes the 2026-10-14 "I don't think I need Substack notes" ruling
    and the 2026-10-26 line that Threads is not in scope merely because
    Buffer connects it.
  - Go-live: "Sign the week, but I am likely to want to add in meme style
    instagram and youtube and tiktok posts randomly too, so these need to be
    queued properly even at short notice - I'll have an idea, send it
    through, then the engine will build, show me for approval, and then
    queue and post autonomously. content.krishraja.com can be expanded to
    help me manage all of this stably and reliably with minimal copy
    pasting or manual asking". LinkedIn stays his own final click.
  - Canva: "yes its important you create a FULL brand kit in Canva for
    use, You choose whatever the content-engine is not covering, and gives
    maximum amplification and speed". For that Canva lane only, this
    supersedes `docs/ENGINE-BOUNDARY.md`'s no-parallel-production line;
    content-engine keeps its formats and standards.
  - "you can create the brand kit in Canva with computer use on my PC -
    assets are all in H drive in Ventures folder. you can spin up a cowork
    prompt to do it and I can open the right H Drive folder and log in to
    Canva" (prompt: `docs/briefs/2026-10-27-canva-brand-kit-cowork.md`).
  - Targets: he chose secondary targets (daily followers per channel,
    weekly paid subscribers), proposed after two weeks of measured
    baseline; the North Star stays the one number.
  - "knowing what works and what doesnt is CRITICAL, make someone an owner
    of that, or build a specialist for it in the engine if there is not
    already one": the What-Works Analyst owns it.
  - His aim for the engine: "obsessed with getting this media channel as
    many subscribers on every channel possible, paid subscribers to my
    substack and be my world class social media manager ensuring my use of
    every social media platform is autonomously able to drive up followers
    every single day".
  Nothing in these rulings authorises a new connection, spend or
  automation by itself; those stay his at the time (plan, "Decisions").
  Later the same day: "You have Google Analytics installed already and
  Control Centre can see that. Make sure this is a part of your
  Measurement Specialist." GA4 property G-VC5V9LDE17 runs on
  home.makeyourmindup.ai through Substack's native integration. It is now
  the Measurement Specialist's per-post attribution source, joined on
  `utm_content`; Substack Growth sources remain the North Star source.
  He then offered: "Happy to let you read Google Analytics directly if you
  prefer." The engine reads GA4 directly with a read-only service account
  (Viewer on that one property); the Control Center brief
  (`docs/briefs/2026-10-27-control-center-ga4-read.md`) is kept as the fallback.
  Also that day he connected Substack in Buffer and added the existing
  engine key to the cloud environment for scheduled cloud runs.

- 2026-10-26: Control Center's daily directive (protocol 1.5.0, control-center
  PR #561) now carries `taste`: the voice rules Krish approved or reworded in
  Control Center. `growth.py cc start` prints them as a block headed
  "KRISH'S APPROVED VOICE RULES" and keeps it in `.scratch/cc/voice-rules.txt`.
  The drafting steps of every job (`AGENTS.md`, "His approved voice rules")
  follow them for how a draft is written, never to choose what it is about.
  They never feed `growth.py check`, a rubric, the breakout score, the queue
  or the report. An empty list means none is approved yet and none is
  invented; absent means they could not be read. The engine accepts any 1.x
  directive; the report stays at 1.0.0.

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

- 2026-10-21: Krish approved making the two named recent articles free,
  correcting the About schedule and linking the Muse and Suno Shorts to
  their matching full videos. He then ruled: "disable for now but as we get
  more followers we are going to need to implement a paid benefits strategy".
  Disable automatic archive paywalling for now; retain paid benefits as a
  future owner decision. These exact approvals do not broaden the standing
  weekly repair authority or authorise changing subscription prices.
  Saved YouTube descriptions can be read back in the reopened native-ID
  Studio editor because public watch pages truncate visible link text.

- 2026-10-21: Krish: "I signed in through your browser. Can you use those
  existing sessions so we can get on with the audit?" Reuse the existing
  Codex in-app browser tabs. Do not infer their authentication from a
  separate cloud session or require another login. YouTube Studio native-ID
  matching now joins the public post to its real editor. A proved no-op save
  can retry once after readback; unknown writes still cannot retry.

- 2026-10-21: Krish agreed: "Fix broken profile links and align subscription
  links autonomously, but bring bio, positioning and pinned-content changes
  to me for approval. Let's get going." He also authorised existing post
  titles, captions, descriptions and links, with creative replacements and
  re-uploads held for approval. Weekly audits must inspect actual pages in
  browser. Start with profiles, pins and 30 days; then new posts and older
  ones still getting attention. Target senior business leaders who are
  themselves publicly visible on AI. This narrow ruling supersedes earlier
  blanket browser read-only text, without changing unrelated authority.
  jobs/channel-audit.md uses the conversion slot; growth.py audit checks
  scope, private receipts, interrupted writes and complete-channel windows.

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
