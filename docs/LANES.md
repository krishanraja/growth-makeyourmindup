# Lanes: what runs alone, what needs Krish

Every piece of work in this engine sits in one of three lanes: L0, L2
and L3. The lanes say who has to do something before it happens. The machine-checked list
is `lanes.json`; this page is the plain summary, and where the two differ,
`lanes.json` wins.

## Times

London and UTC are the same clock from 25 October 2026 to 28 March 2027.
In British Summer Time (from 28 March 2027) London is one hour ahead, so
every London time below moves one hour later.

## L0: runs alone, as code in GitHub Actions

Nobody has to be awake or online for these.

| What | When (UTC) | When (London, winter) |
|---|---|---|
| The Control Center runner (`control-center.yml`): reads the day's instructions, checks the engine, sends the report, reads Krish's answers | every day 05:10, when Control Center wakes it; a backup at 05:40 runs only if that run has not worked today | 05:10, backup 05:40 |
| The key check (`keys.yml`): checks that both keys still work. A refused or missing key fails the run, so GitHub emails Krish | every day 06:50 | 06:50 |
| Release (`release.yml`): puts in Buffer's schedule exactly the posts Krish approved, checked byte for byte and on his own Buffer account, each about an hour before it is due (until then a No stops it). That is each day's go-live he approved (a go-live naming more than one New York day holds), and each post made from an idea and mock he approved in the week's mix plan, read back from Control Center (below). A post still scheduled after a No fails the run, so GitHub emails Krish. It holds a post whose words fail the copy lint or ask for the share, and every post on a Buffer route not yet recorded as passed: that route's one capability check goes through `run release` first. Never LinkedIn | every 30 minutes | every 30 minutes |
| Measure (`measure.yml`): checks the keys, then reads how each post did and reports it to Control Center | every day 07:00, 13:00, 19:00 | 07:00, 13:00, 19:00 |
| The handoff (`handoff.yml`): turns the Buffer drafts, week packet or week's mix plan a session or PC automation saved into one ask on Krish's list, after checking each draft against its hash, and records the review of each post made from an approved idea | when that maker wakes it | when that maker wakes it |
| The test suite (`check.yml`) | on every push and pull request | on every push and pull request |
| Art direction (`artdirect.yml`): Codex invents one visual idea for each piece of the coming week and builds it as a piece kit (`render/KIT.md`, "Piece kits"), with no network, only in that piece's own folder, and on at most three pieces a run. The renderer's checks are the gate: a kit that fails is removed and that piece uses the house kit. The kits that pass come to Krish as one pull request, "Piece kits for week W", which the workflow never merges. Its log carries counts and codes only | Saturdays 07:00 | 07:00 |

Only this lane holds the Control Center engine key. It is a GitHub
repository secret. No chat session holds it.

Art direction is the one L0 job that runs a model. Codex makes there under
the same walls as every maker: it writes only a piece kit, which reaches the
repository only through a pull request Krish merges, and it never posts,
sends, schedules or spends beyond its capped run. Its key is the repository
secret `OPEN_AI_API_KEY`, given to that one step and to no other job.

### How release reads what Krish approved

Release trusts only what it reads back from Control Center, each record by
its exact address and digest, and Buffer itself. It never trusts a file on
the runner, a dispatch payload or anything on Krish's PC.

- **A go-live.** His decision, then the go-live and its plan read back from
  their own reports by the digest he decided on.
- **The week's mix plan** (Krish, 29 Oct 2026: approve the idea and the
  mock). The handoff reports the plan as one ask, or in parts in order when
  a week passes 8,000 characters, each part with its ideas, claims and mock
  hashes, plus a record of which version is in force. Release reads them
  back, rebuilds every idea's hash, and applies his yes, his changed version
  or his No with the same code the Control Center runner uses. His No on any
  part stops the week; a newer plan he has not answered withdraws an older
  yes.
- **A post made from an approved idea.** The handoff records its review
  under the post's own hash. Release reads that record back by the exact
  hash, rebuilds the post from its Buffer draft, and schedules it only when
  it matches its idea (one of its channels and formats, only its mock files,
  its claim word for word), its review passes at that exact hash, and the
  channel's New York day still has room (four a day on Instagram, YouTube,
  TikTok and X, counting every post already scheduled in Buffer and each
  post he signed for that day). While the plan cannot be trusted or a No
  cannot be matched to its plan, every such post holds and the run fails,
  so GitHub emails Krish.
- **What it already did.** When every post of a go-live is done, release
  records that in Control Center, so the next run, on a clean machine, never
  acts on it again; it only checks that what is scheduled is still what he
  approved.

The North Star line in `NOW.md` is not made here. The "Growth: numbers"
automation on Krish's PC reads the Substack Growth sources page in his
browser, and `growth.py run northstar` turns that capture into the line.
GitHub Actions never reads Substack.

## There are no Claude routines (Krish, 29 Oct 2026)

Krish: "I want zero Claude routines. No Claude schedules of any kind in
this architecture". There is no L1 lane. A new schedule is a GitHub
Actions job in L0, never a Claude routine. The existing Codex automations on
Krish's PC (below) are kept as they are.

## Who makes

Making is not a lane of its own. Canva assets, words, Buffer drafts and the
week's packet are made by interactive sessions and by the existing jobs on
Krish's PC, and each piece's visual idea by Codex in the art direction job
(L0, above), under the same walls:

- Making leaves drafts and proposals only: it never publishes, schedules,
  sends, deletes or spends. A Buffer post is saved with `saveToDraft: true`
  and no due time; only `release.yml` schedules, and only what Krish
  approved. The weekly audit's scoped repairs are in `AGENTS.md`.
- No session holds the Control Center engine key. A maker reads Control
  Center through its connector, and calls no Control Center write tool but
  `report_to_taste_engine` (`docs/TASTE.md`). Every taste read follows
  `docs/TASTE.md`.
- No figures, words or ids in this public repository.
- To propose what it saved, a maker wakes the handoff with a
  `repository_dispatch` (`growth-go-live-manifest`, `growth-week-packet`,
  `growth-make-piece` or `growth-mix-plan`; the payloads are in
  `engine/run/handoff.py`). The runner checks every draft against its hash
  before Krish sees it. A post made from an approved idea goes in the
  go-live manifest with its idea and its review; it is never asked again.

The jobs on Krish's PC run only while his PC is on: the nine automations in
`automations.json` (their times are in `README.md`; the channel audit is
Saturday 12:00 London) and the 09:00 London daily heartbeat. They are kept
until W46; `lanes.json` names the L0 job that takes over each one, where
there is one.

## L2: waits for Krish's eyes (one press in Control Center)

These wait on his one list in Control Center. Each is one press: yes, change
it first, or no. They wait until he opens the list.

- **The Sunday sign-off.** The week's packet, from whoever plans the week.
- **A piece's publish board.** The article, its pictures and its video
  recordings. Once he approves the board, the smaller posts made from that
  piece (Substack Notes, Threads, X, Instagram, Facebook, YouTube, TikTok,
  Stories) go out without asking him post by post (Ruling, Krish, 27 Oct
  2026). For the first four weeks, until 29 November 2026, each batch of
  those posts is still shown to him first.
- **New kinds of post.** Carousels, memes and any kind he has not approved
  before. He sees each one. Their words are plain English, human and humble.
- **A quick idea.** Each idea he drops in Buffer Ideas comes back as a
  preview for one press.

## L3: waits for Krish's hands

Only he can do these. Nothing in L0 or L2, and no session, does them for him.

- **LinkedIn.** The engine leaves LinkedIn posts as drafts in Buffer. He
  presses publish himself.
- **The Buffer plan.** Buying, keeping or stopping a paid Buffer plan is
  spending, so it is his.
- **One-time set-up.** Keys, step by step in
  [SETUP-ONCE.md](SETUP-ONCE.md).
