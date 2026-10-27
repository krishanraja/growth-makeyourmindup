# Lanes: what runs alone, what needs Krish

Every piece of work in this engine sits in one of four lanes. The lanes
say who has to do something before it happens. The machine-checked list
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
| Release (`release.yml`): puts in Buffer's schedule exactly the posts Krish approved, checked byte for byte and on his own Buffer account, each about an hour before it is due (until then a No stops it). A post still scheduled after a No fails the run, so GitHub emails Krish. Never LinkedIn | every 30 minutes | every 30 minutes |
| Measure (`measure.yml`): checks the keys, then reads how each post did and reports it to Control Center | every day 07:00, 13:00, 19:00 | 07:00, 13:00, 19:00 |
| The handoff (`handoff.yml`): turns a routine's Buffer drafts or week packet into one ask on Krish's list, after checking each draft against its hash | when a routine wakes it | when a routine wakes it |
| The test suite (`check.yml`) | on every push and pull request | on every push and pull request |

Only this lane holds the Control Center engine key. It is a GitHub
repository secret. No chat session holds it.

The North Star line in `NOW.md` is not made here. The "Growth: numbers"
automation on Krish's PC reads the Substack Growth sources page in his
browser, and `growth.py run northstar` turns that capture into the line.
GitHub Actions never reads Substack.

## L1: runs alone, as Claude cloud routines

Each routine opens a fresh session, follows one file in `routines/` and
ends. It makes drafts and proposals only. It never publishes, schedules,
sends, deletes or spends.

| Routine | What it does | When (UTC) | When (London, winter) |
|---|---|---|---|
| `make` | builds today's posts in Canva and saves them as Buffer drafts | every day 06:00 | 06:00 |
| `plan` | builds next week's packet for Krish's Sunday sign-off | Sundays 05:30 | 05:30 |
| `watch` | builds Krish's quick ideas from Buffer Ideas, starts `make` for newly approved pieces, reports what is held | every day 07:30, 12:30, 17:30 | 07:30, 12:30, 17:30 |

Jobs on Krish's PC also run on their own, but only while his PC is on:
the nine automations in `automations.json` (their times are in `README.md`;
the channel audit is Saturday 12:00 London) and the 09:00 London daily
heartbeat. They are kept until W46; `lanes.json` names the routine or job
that takes over each one, where there is one.

## L2: waits for Krish's eyes (one press in Control Center)

These wait on his one list in Control Center. Each is one press: yes, change
it first, or no. They wait until he opens the list.

- **The Sunday sign-off.** The week's packet from `plan`.
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

Only he can do these. Nothing in L0, L1 or L2 does them for him.

- **LinkedIn.** The engine leaves LinkedIn posts as drafts in Buffer. He
  presses publish himself.
- **The Buffer plan.** Buying, keeping or stopping a paid Buffer plan is
  spending, so it is his.
- **One-time set-up.** Keys and routines, step by step in
  [SETUP-ONCE.md](SETUP-ONCE.md).
