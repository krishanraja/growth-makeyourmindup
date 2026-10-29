# Changes Krish made to the growth engine

- 2026-10-29 (Wave 2, W2.9): the off-day lane. His brief: "First posts on
  Tuesday 10 November" and "0 off-day posts land on Monday, Wednesday or
  Friday". Asked in this session which ruling wins, the off-day weekdays or
  the 29 October flood ruling that runs the same lanes every day, Krish
  chose "Mix wins: every day".
  - No weekday ban: the meme, positive news and level-up lanes run every day.
    The brief's Monday, Wednesday and Friday test is dropped; R97's weekday
    line is superseded (`docs/PUBLISHING-AUTHORITY.md`).
  - The mid-week top-up (R118): `growth.py mix topup` gives the next free
    filler slot for one post from a fresh Buffer readback, never the series
    slot, never a day at the lower of the plan's cap and the live cap, never
    a slot taken and never inside release's 90-minute window.
  - The Sunday Off-days section: `growth.py mix offdays` gives two or three
    options a day (format, source, draft copy, share line) as data for
    content-engine's Sunday board, and says which day is short.
  - The clock facts for Control Center: `growth.py mix clock` gives
    offday_stocked (every filler slot ready by Sunday 20:00 New York) and
    offday_slots_filled.
  - Floor never 2, his words of 29 October: "nothing made up, and every
    number credited to its producer." A filler idea whose claim carries a
    figure (money, a share, a multiple, a large count) and no source is
    refused (R119).
  - `calendar/v1.json` keeps its meme rows as V1's own check; mix.json is
    what lays out which days carry which lane.
- 2026-10-29 (Wave 2, W2.8): Growth posts what he approved. From Krish's
  saved Wave 2 brief (plan of 28 October, amended 29 October): "content-engine
  writes `0 Publish/manifest.json` per piece: Drive ids, sha256, order, exact
  copy per channel, alt text, QA state and the approval digest." And for
  metrics: "Shares or sends per reach, and saves per reach, are the snackable
  lane's measures, marked as hypotheses until his own data confirms them."
  And for the engage queue, his 28 October words: "make sure everything is one
  click copiable and the click through goes precisely where i need to engage."
  - The piece manifest (R115): a go-live dispatch may name content-engine's
    manifest by a direct download link and its sha256 (`piece_manifest`). The
    handoff reads it, refuses one that is not passed QA, unapproved or not
    its sha, and holds any draft that is not exactly the manifest's post for
    its channel: words, assets in order and alt text (`manifest_differs`).
    `engine/run/piece_manifest.py`, schema in
    `specs/schema/piece-manifest.schema.json`.
  - One go-live per post: a slot marked `per_item_review` is already its own
    go-live, so a maker that marks every slot gets one decision per post,
    bound to its payload_sha256, Buffer channel id and due time. His No on
    one post before release schedules it (5 to 90 minutes ahead) is the Pull:
    only that post stays a draft. A No after it is scheduled is loud and is
    never unscheduled by the engine; unscheduling is his call.
  - Exact targets (R116): each engage tap on X, TikTok, Instagram or LinkedIn
    opens the exact post or profile, never a feed, search or short link, and
    a LinkedIn reply carries no link (`engine/engage.py`). The queue says
    when its taps run past the 10-minute queue; the daily cap stays
    intensity.json's.
  - Sends and saves per reach reach the measure report (R117), per channel
    per 1,000 reached, with the hypothesis status; a channel that shows
    none says so, never zero.
  - YouTube long-form is a route (`long-video`), unverified until its first
    real post passes as the capability check he approves on its Monday. A
    Substack article is never released (Buffer's Substack channel is his
    Notes profile): it stays a saved draft for his click.
- 2026-10-29 (late): the code renderer draws every post; Codex art-directs
  one visual idea per piece. Krish judged a blind bake-off of three makers
  (the code renderer, Codex and Canva) on the same seven images and picked the
  renderer. Of Canva he said: "Canva feels more like a powerpoint designer did
  it rather than a designer". Then: "the most stunning visual art direction
  I've seen thus far comes from the AI Passports post. I am pretty sure that
  was Codex? If so, we need to find a way of combining strengths". So each
  Saturday `artdirect.yml` has Codex invent one visual idea per piece as a
  piece kit (`render/pieces/`, house colours and fonts only), the renderer
  draws every post from it with its checks as the gate, and his concept
  approval binds the exact mock hashes. Canva is read-only reference. On the
  lane: "keep it in L0", so art direction runs in GitHub Actions though it
  runs a model.

- 2026-10-29 (evening): the prepaid credits share is read, and its spending is
  a procedure. The runner reads `credits` and spends nothing
  (`engine/credits.py`, `tests/test_credits.py`). `docs/CREDITS.md` is how a
  session with the ElevenLabs and Apify connectors spends the share through
  Control Center. Krish chose "Scheduled sessions" for every engine, but this
  repository's 29 Oct ruling allows no Claude schedules, so no schedule runs it
  here until he says which one does.
- 2026-10-29 (later): flood the four short-form channels, approve the idea
  and the mock. Krish: "For Make Your Mind Up I think the engine needs to
  strategize how to repurpose all the previous posts into carousels and
  intertwine them with the memes, positive news pieces, and the other filler
  pieces that we decided on. When it comes to Instagram, YouTube, and TikTok,
  I am more than happy to pump out three or four posts a day on all three of
  those platforms. Same with X and Twitter. I just need to be in control of
  the idea and the mocks and then I'm happy to let you let that engine just go
  for gold. The more we flood these channels right now, the faster we learn.
  Simple as."
  - Approval moves to the idea and the mock (R101). He approves each concept
    (its idea, its one claim and its mock files, bound by concept_sha256)
    once, in the week's mix plan. That yes lets release post every post made
    from it on Instagram, YouTube, TikTok and X with no per-post digest,
    through the same release gate and Buffer channel lock, only while the post
    matches its mock and claim (`engine/concepts.py`). A post that departs is
    held. His no, or a stop on a concept, stops all of its posts. LinkedIn
    stays his click; every other channel still signs post by post.
  - Volume (R102): Instagram, YouTube, TikTok and X take four posts a day with
    a floor of three (`social/channels`, `engine/social.py`). No urgency caps
    them below three; walls, spend and approvals are unchanged.
  - The weekly mix (R103): `growth.py mix plan` turns every past piece into
    carousel concepts, oldest unamplified first, and interleaves them with
    memes, positive news and level-up advice (the 28 October off-day lanes)
    at a ratio of 50, 25, 15 and 10 (`mix.json`), three or four a day per
    channel, no piece twice on a channel in a week. Its concepts go to him as
    one plan proposal; `run new --mix` carries the ready ones into the week's
    spec. `growth.py mix learn` joins each post's What-Works verdict to its
    concept and lane, and the next plan moves a lane one step (`docs/MIX.md`).
  - Review fixes, same day: a concept post also needs a passing review at its
    own payload and room under its channel's four a day across every run; an
    unmatched decline holds every concept post; the signature must name the
    week's mix plan.
  - The readback (R104), same day: in the loop's own run, right after it
    reads his decisions, his yes on the week's mix plan (or his amended
    version) writes `decision.json` `concepts`, `concept_manifest` and
    `stopped_concepts` and the spec signature (`engine/run/decision.py`,
    `growth.py run decide`; fields in `docs/CONCEPT-MANIFEST.md`). A line he
    deletes or changes stops that concept; his no stops them all, for good.
    With no go-live for the week the decision is concept-only: the approved
    plan is the go-live for posts made from its concepts, and any other post
    still needs the week's go-live. The release budget rises to 45 calls for
    about 16 posts a day plus readbacks (`docs/RUN.md`). Built and wired, not
    yet activated.
  - Review fixes to the readback, same day: his no is read before the plan
    file is trusted; an amended version that changes any plan line other
    than a concept's approves nothing; a declined check-in not yet matched
    to its plan holds every concept, and the loop now records stops and
    unmatched declines in the go-live ledger each run; a yes on another plan
    digest approves nothing; every run rewrites decision.json and fails
    closed with the reason in `concept_hold`. The plan states each channel's
    most posts a day, and release keeps under it too.

- 2026-10-29: Buffer stays. Krish: "OK, I will keep Buffer for heartside
  and makeyourmindup for now", and of Full Time: "I can add fulltime when
  ready to launch that, its a while away still". The memo he asked for
  ("it is on you to prove Buffer's ROI to me by then") applied the rule fixed
  on 27 October: Buffer is the only working route for the channels the plan
  needs (every route goes through Buffer, 28 October), the free plan holds 3
  channels against this engine's 8, and Essentials keeps every capability the
  engine uses (Team's approval workflows answered the routines, which are
  gone). Early results (10 Buffer-sent posts, 26 to 29 October) are too few to
  judge either way. The plan purchase is his click.

- 2026-10-29: No Claude routines: the make, plan and watch routines are removed
  under Krish's 29 Oct ruling ('I want zero Claude routines. No Claude
  schedules of any kind in this architecture'); GitHub Actions jobs remain the
  only schedules; making is done by sessions and the PC automations under the
  same walls; the taste procedure moves to docs/TASTE.md.

- 2026-10-29: "At U3 to U5, engines and Control Center may raise volume caps
  up to each repo's existing policy bounds without a signed week spec. This
  is volume only: walls unchanged." The engagement doctrine moves from
  "fewer good candidates beat quota fillers" to as many as clear the bar,
  batched as one copy and open ask on his list (docs/ENGAGEMENT-LOOP.md,
  jobs/radar.md). The backlog (`growth.py backlog`) and the ecosystem route
  on every run spec slot (`ecosystem_cta`) come from the same day's plan.

- 2026-10-29: no content names Krish. Krish, 28 October: "Remember, no
  content refers to Krish, ever. I still see that popping up from time to
  time. Even articles written are not authored by Krish. My face only, for
  assets and the video format." On 29 October he answered the questions it
  raised. Articles speak as "We", the publication; scripts he speaks keep
  "I". Of his personal accounts: "No, personal stays personal", so first
  person stays there, but never his name in the text. Of another person
  called Krish: "Yes, block it", so the name rule has no override.
  - content-engine owns the pattern (`no_name`, copy lint version
    2026-10-29.3, which also adds the `article_body` surface that only the
    name rule reads). This engine re-vendored it unchanged, and its reader
    knows the new surface, since an unknown one raises and holds every
    release.
  - Every public word Growth writes runs it: slot words in run lint,
    captions and alt text in social preflight, words, carried alt text and
    titles in release, drafted pack replies, autonomous audit repairs, and
    each post draft the Control Center loop would propose.
  - The publication's own lanes and proof speak as the publication ("we");
    his personal accounts speak as him ("I"), never naming him
    (`knowledge/COPY-DOCTRINE.md`, `docs/ACCOUNT-VOICE.md`). Buffer channel
    names and account handles are his to change and stay as they are.

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
  - Generic share calls to action in snackable post copy are refused where
    they open a sentence; three that a true sentence about other people does
    not contain ("share it with your team", "please share", "someone needs to
    see this") are refused anywhere. The share comes from the content, never
    a request.
    Whether text posts, articles and daily and radar drafts are refused too is
    Krish's decision (`share_cta_scope` in `social/share.json`).
  - Each snackable format names its share mechanic in its delivery checks; for
    content-engine's formats it is a proposed hook in Growth's brief, never a
    production standard Growth holds. `hooks.json` gains a share formula, a
    house hypothesis like the rest.
  - A blind send-test reader (`crew/send-test/`) sees only the post, staged
    under blind names, and must name the declared receiver and job before
    Krish sees it. Its answer is bound to that exact revision by
    `request_sha256`, so a revised post needs a fresh reader. A snackable run
    slot carries the same share block, and its review is the send test
    (`docs/RUN.md`).
  - Sends per reach and saves per reach become the snackable lane's primary
    measure in What-Works, house hypotheses until MYMU's own dated data
    confirms them.

- 2026-10-28: Krish approved the plan "Make Your Mind Up: one weekly chain
  that runs on time", and with it these rulings for this engine (his words,
  28 October; approving the plan was his yes to recording them):
  - Growth makes carousels: "take over posting as well as creating new
    assets like carousels". Growth makes derived carousels to
    content-engine's standard. This supersedes the 26 October production
    split for carousels only (`docs/ENGINE-BOUNDARY.md`).
  - Go-live: "Approve each day Monday". Approving a day on the Monday final
    board authorises scheduling exactly those posts; Growth reads them back
    and he can pull each one until its slot (`docs/PUBLISHING-AUTHORITY.md`).
  - Routes: "buffer is connected to youtube and substack". Every route goes
    through Buffer, and each route's first real post is a capability check
    he approves on that Monday. LinkedIn stays his click.
  - Never the Full Time or Heartside channels: release is pinned to this
    engine's eight Buffer channels by channelId, and the other ventures'
    channels in the same Buffer organisation are denied by id.
  - Engagement: "10 min daily queue is fine, add Instagram and LinkedIn to
    this, and make sure everything is one click copiable and the click
    through goes precisely where i need to engage." Still prepared only:
    he submits every reply.
  - Copy: "don't add stupid eyebrow text and asterisks and "generated by
    AI" and "Krish's take" verbal diahorrea like you tend to. This needs to
    feel like a world class media channel". content-engine owns the copy
    lint; this engine vendors it (`vendor/content-engine/copy-lint`) and
    run lint, social preflight and release refuse any copy that hits it.
  - The off-day lane: "I also want the Make Your Mind Up Instagram, TikTok,
    and YouTube Shorts to post on days that are not mon/weds/fri, with
    memes, positive uplifting AI news carousels, or simple valuable advice
    on how to level up with AI ... the growth repo should be accountable
    for this and this should show me quickly for approval, and when I one
    click green light it puts it in the next available slot". And: "I'm
    happy to plan the Tuesday, Thursday, Saturday, and Sunday content
    within the Sunday ideas session if you give me a few options to
    approve as you do the Mon/wed/fri".
  - Rhythm: "record the entire week on a Sunday, but it does not go live
    until the Monday after (8 days later)". Pieces go live Monday,
    Wednesday and Friday of the week after recording.
  Later the same day, on labels: "It's just the ones that
  say "Krish's read" or "illustrative" that are stupid because they add no
  value to the content." content-engine owns the patterns and added both
  (copy lint version 2026-10-29.1, `take_label` and `illustration_label`);
  this engine re-vendored that version unchanged.

- 2026-10-27 (late): the engine reads Inspiration House, robustly, both ways.
  Krish: "Make sure you're wiring into the Inspiration House repository in a
  way that is incredibly robust because that's where I put in videos or
  content. I put it in when I either love the production, it could be a
  template for us, or I like the specific content. I'm always commenting in
  detail on why I like something in there." He approved the plan in which a
  maker may read his production examples (cards he routed to study the style,
  and his form signals) as context for making, never a rule and never to
  judge. `routines/taste.md` is how the routines read his approved rules and
  examples and report back; `tests/test_taste_wiring.py` keeps every judge
  away from taste; the Control Center tool and the Inspiration House rule line
  are briefs in `docs/briefs/2026-10-28-*`.
- 2026-10-27 (evening): three rulings on what the engine may do alone.
  - Standing approval for derivatives: "Derivatives of approved pieces.
    That actually includes Instagram as well as YouTube and TikTok. Once I'm
    happy with the publish board (article, the assets and video recordings),
    you should be able to just go for gold everywhere else. I would say that
    for the first 4 weeks you need to show me before you post. However I
    think you're going to be creating new formats like carousels. The last
    one that went up on Make Your Mind Up Instagram was good but could have
    been better. It wasn't plain English and human and humble enough."
    `invariants/authority.json` holds it as data: the derivative formats
    that post on every channel once he approves a piece's publish board;
    each batch shown to him first through 2026-11-29 (W45 to W48, four
    weeks from the first signed week); carousels, memes, opinion, reactive
    posts and any other new format need his eyes item by item; carousel and
    caption copy passes the plain-English lint (`engine/run/plain.py`).
  - Keys: "Surely we can have a less fragile way of doing this than a
    session engine token ... Give me the bulletproof version of this. Same
    for the cost baseline." No session holds the engine key. Control Center
    traffic runs only from the GitHub Actions runner, which reads the key as
    a repository secret, and every run meters its own cost.
  - Lanes: "set yourself daily autonomous tasks that don't really rely on
    me. Separate your daily autonomous work ... from the things that you
    need my eyes on to just approve versus the things that you need me to
    push manually, like my personal LinkedIn posts that you've drafted."
    `lanes.json` puts every job in exactly one lane: L0 code on GitHub
    Actions (no model), L1 Claude routines (make, plan, watch), L2 his eyes
    (one press in Control Center) and L3 his hands (LinkedIn, the Buffer
    plan, one-time set-up). The nine automations keep running until the W46
    cut-over. `calendar/v1.json` is the V1 posting calendar built on those
    lanes, checked by `growth.py run calendar lint`.

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
