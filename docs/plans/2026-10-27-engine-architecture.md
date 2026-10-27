# growth-makeyourmindup: bulletproof growth-engine architecture (plan for Krish's approval)

Status: building (27 Oct 2026). Krish ended plan mode on this plan, which the session took as his approval to build on branch `claude/sweet-goodall-opribv`. Every decision listed at the end stays his, at the time of each action. Linked from `docs/GET-GOING.md`.

## Context

**Why.** On 27 Oct Krish asked every growth engine to adopt the six-rule reference architecture. It came out of the content-engine `ve` diagnosis: about 253M tokens spent on four rejected videos. Doc rules never held, and every pass was self-certified.

**North Star and what this moves.**
- **The number:** new publication subscribers a week from organic posts and shares, zero paid. The ladder is 25 (w/c 26 Oct), 86, 162, 271 (16 Nov), and on to 2,500 (28 Dec).
- **Now:** 0 of 25, U4, far behind (NOW.md, read live through Control Center).
- **This plan moves three things:**
  1. Measurement. Today the number is read by hand, reported to Control Center summed across all sources, and its NOW.md line is hand-written. A run with no measured outcome cannot steer.
  2. A daily floor on two new surfaces, Notes and Threads, starting W45.
  3. Cost and time per verified post, so daily posting on nine surfaces fits Krish's 20/30-minute review budget.

**Honest arithmetic.** At the 2026 Notes median (0.93 subscribers per 100 clicks), the ladder's 2,500 a week would need about 270k Notes clicks a week. The floor will not reach the ladder alone. The engine needs breakouts:
- **P8 breakout amplification:** owned here.
- **P2 Recommendations and P3 cross-posts:** these are outreach, which belongs to Control Center's People and Visibility tabs (21 Oct ruling). This engine drafts each ask and holds it for them.

**Krish's rulings today (27 Oct 2026; recorded in `CHANGES.md` in Phase 1, with supersession notes and nothing deleted):**
1. **Add Substack Notes and Threads.**
   - This supersedes the 14 Oct "no Notes" ruling and the 26 Oct "Threads not in scope" line.
   - The supersession notes go in: `AGENTS.md` ("Why it works", "Growth ownership"), `knowledge/README.md` override 1, `docs/PUBLISHING-AUTHORITY.md` and `docs/ENGINE-BOUNDARY.md`.
2. **Sign the week.** Signed exact payloads post autonomously; LinkedIn stays his click.
   - **Ad-hoc meme ideas for Instagram, YouTube and TikTok** at short notice: the engine builds, shows him, then queues and posts on his approval.
   - **content.krishraja.com is to be expanded** so he can manage this without copy-paste.
3. **A full makeyourmindup brand kit in Canva.** Growth produces whatever content-engine does not cover, for amplification and speed.
   - This supersedes `ENGINE-BOUNDARY.md`'s "no parallel production" line and `jobs/daily-growth.md`'s "do not create another orchestrator" line, for the Canva lane only.
   - The Canva lane applies content-engine's standards by reference.
4. **The brand kit is built by Cowork computer use on his PC,** from the H: drive Ventures folder.
5. **Secondary targets:** daily followers per channel and weekly paid subscribers. I propose the numbers after two weeks of measured baseline; the North Star stays the one number.
6. **Knowing what works is critical.** It gets a dedicated owner: the What-Works Analyst.

**What exists (all of it is kept):**
- **Code.** `growth.py` plus `engine/` (catalog, packs, operations, control_center, cc_loop, channel_audit, social).
- **Tests.** 168, with CI on ubuntu/windows × Python 3.9/3.12.
- **Social records.** 7 channel profiles, 6 format contracts, the Buffer profile and 17 lessons.
- **Scheduled jobs.** 9 in `automations.json`, the `daily-growth.md` heartbeat and the GitHub `control-center.yml` runner.
- **Control Center protocol 1.5.0.**
- **The 26 Oct live pilot.**
- **Private receipts** in `.scratch/` and `fresh-owner/` on his PC.
- **The failure register:** 54 past fixes or learnings (F01 to F54, appendix). About 25 are doc-only.
- **The 27 Oct asset-storage ruling** (`docs/ASSET-STORAGE.md`): the Drive 4 Growth library, private evidence kept local, and a closeout routine every session.

**Gaps in code (each gets a fix plus a test):**
- **G1.** `channel_audit.py:18-22` allows autonomous LinkedIn edits, against the 26 Oct ruling.
- **G2.** `post --deliver` still sends pitches/partners/swaps packs.
- **G3.** Facebook is missing from `core.PLATFORMS`, the audit's `ACCOUNTS` and `channels.json`.
- **G4.** The North Star objective sums every source.
- **G5.** The "Validated N observations" message overstates what was checked.
- **G6.** `amended_sha256` is documented, not coded.
- **G7.** Stale "eight automations" strings remain.
- **G8.** `substack.json` sets a daily target that conflicts with "editorial rhythm".
- **G9.** The autonomy loop (GET-GOING Step 1) is not coded: proposal `stage`, `parent_proposal_id`, the go-live step, amendments. `SCHEMA_VERSION` is still `1.0.0`.

**Live facts (read today):**
- **Buffer** has 7 channels: YouTube, the Facebook Page, X, TikTok, LinkedIn, Threads (krishraja1) and Instagram. **There is no Substack channel.** Its schema supports `substack` and `threads`, `freeSubscriptions`/`paidSubscriptions` post metrics, and Ideas.
- **Canva** has no makeyourmindup kit or templates, and no MCP tool that creates a kit.
- **The repo is public.** No drafts, receipts or business figures go in it; synthetic fixtures only.
- **Control Center shows one ask per engine at a time.** `exact_payload` is capped at 8,000 characters (`control_center.py:244`).
- **Codex is at its weekly limit until about 2 Nov.**

## 1. The run spec: what Krish signs

- **Schema:** `specs/schema/run-spec.schema.json` (`growth-run-spec/1`), closed, validated by `social.validate` (`engine/social.py:17`).
- **Kinds:** `week` and `piece` (one published piece's wave, day 0 to day 7), plus `express` (one idea).
- **Typed fields only.** Rules live in `invariants/`, never in the spec.

```json
{
 "schema": "growth-run-spec/1", "run_id": "makeyourmindup:2026-W45:week", "kind": "week", "parent_run_id": null,
 "window": {"start": "...", "end": "...", "tz": "America/New_York"},
 "north_star": {"week_target": 86},
 "secondary_targets": [{"metric": "followers_net", "channel": "threads", "per": "day", "target": null, "status": "baseline_pending"}],
 "inputs": [{"package_id": "...", "origin": "content-engine|canva-lane|krish-idea", "piece_url": "...", "creative_approval_ref": "..."}],
 "slots": [{"slot_id": "...", "channel": "substack_notes", "format": "note", "play": "P1", "due_at": "...",
            "words": "...", "assets": [{"sha256": "...", "url": "..."}], "link_placement": "...", "cta": true,
            "forward_line": "Who sends this to whom, and why", "experiment_arm": null, "publish_mode": "engine|krish_click",
            "buffer_draft_id": "...", "payload_sha256": "..."}],
 "experiments": [{"id": "...", "channel": "x", "variable": "link_placement", "arms": ["in_post", "first_reply"]}],
 "budgets": {"krish_min": {"weekday": 20, "sunday": 30}, "spend_usd": 0},
 "signature": {"go_live_proposal_id": "...", "decision_digest": "...", "signed_at": "..."}
}
```

Hand edits to the computed fields (`week_target`, each `payload_sha256`) are refused by `run lint`.

**How signing works inside the existing Control Center protocol** (one ask at a time; 8,000-character payloads):
1. **One standing plan, approved once.** Krish approves a `plan` proposal (wall `strategy`) for W45 to W52: channels, cadence and the gate rhythm. Every go-live names it as `parent_proposal_id`.
2. **G-A, Sunday (≤15 min).** A `go_live` for the week's Notes, Threads and evergreen slots. The payload is an editable manifest of 8,000 characters or less (slot, channel, words, asset hashes, link). A larger week splits into go-lives that come forward one after another.
3. **G-B, Mon/Wed/Fri (≤5 min each).** A `go_live` for that piece's batch across every channel, once content-engine's package arrives.
4. **G-X, express (≤2 min).** An approved idea joins the waiting go-live, which is updated in place under the same `proposal_id`. If nothing waits, it gets its own go-live. Express is capped at one a day until review time is measured.
5. **Check-ins** on Sunday (with the What-Works ledger) and Wednesday, as the protocol requires.
6. **Amendments.** If he amends, `amended_sha256` is recomputed and his version is what posts.

Per run there are two gates: a go-live and a check-in. LinkedIn stays his own click.

**Where unpublished words live.** They never go into git. This follows `docs/ASSET-STORAGE.md` (Krish, 27 Oct 2026).
- **Approved delivery assets and exact copy** go in the existing Drive **4 Growth** library, one `YYYY-MM-DD - Topic - Channel` folder per campaign, each with its checksum manifest. The manifest shape is the one the 27 Oct shopping-agent package already uses: `revision`, `approval_scope`, `publication_status`, `source_article`, `next_read` and `files[{name, bytes, sha256}]`. Slot `assets` point at those entries.
- **Buffer drafts** (`saveToDraft`, already authorised) hold the queued words and media.
- **Control Center** holds the decisions and the reported numbers.
- **Private evidence** (raw readbacks, journals, account inventories) stays in local `.scratch/` on Krish's PC. It never goes in 4 Growth, which anyone with the link can edit.
- **No other Growth root** is created.

Because 4 Growth is link-editable, release checks each slot's bytes at release time against the sha256 in the signed manifest line. It never trusts the file just because of where it lives.

## 2. Repo structure (additive)

```
docs/plans/2026-10-27-engine-architecture.md   this plan, with the F01-F54 / G1-G9 register appendix
docs/RUN.md                     ≤8 KB: the only standing doc a run session reads
specs/schema/                   run-spec, gate, verdict, card, ve-package schemas
crew/registry.json              specialist -> spec section, lint fn, check fn, card, lens
crew/<id>/card.md (≤3 KB), crew/<id>/lens.md (≤1 KB)
invariants/rules.json           each rule with its verbatim source quote + file; a test fails if the quote drifts
invariants/failures.json        F01-F54, G1-G9 -> guard + test; CI fails if a guard or test disappears
invariants/sources.json         Substack source -> organic | unattributed (Krish approves at G-A)
invariants/boundary.json        format -> production owner (content-engine | canva-lane)
engine/run/spec.py              schema, lint, computed status
engine/run/measure.py           attribution, measured checks, verdicts, cost meter
engine/run/release.py           Buffer adapter, gate manifests, readback
engine/run/canva.py             template autofill, resize, export, brand checks
engine/run/pack.py              ≤36 KB session pack
engine/run/intake.py            ve package intake and express ideas
tasks/cards/                    Codex task-card spec (dispatch built only when the allowance allows)
social/channels/threads.json, social/formats/note.json, social/formats/meme.json
tests/test_run_*.py             synthetic fixtures only
```

**CLI.** The new commands are `growth.py run new|lint|status|pack|gate|release|measure|verdict|northstar|cost|card`. Every existing command and job stays unchanged.

**Reused, not rewritten:**
- From `core.py`: `identity`, `tracked`, `write_json` and `locked`.
- From `packs.py`: `prose_errors` and `seal`.
- From `operations.py`: `validate_observation`, `aggregate`, `yield_per_thousand`, `daily_queue` and `experiment_decision`.
- From `control_center.py`: `payload_digest`, `schema_errors`, `proposal`, `Client` and `match_decisions`.
- From `cc_loop.py`: `Loop` (every run journals with `cc start` and `cc finish`) and the voice-rules isolation.
- From `social.py`: `route` and `preflight` (byte-hash binding).
- All of `channel_audit.py`.

**Threads code changes:**
- `social.py:104` gains `threads` in the delegated-cadence set, with a test citing the 27 Oct ruling.
- Threads is added to `PLATFORMS`, the audit's `ACCOUNTS`, `channels.json`, `buffer.json` capabilities (unverified until checked), and `KINDS` for the new run kinds.

## 3. The crew

Every specialist has four parts:
- a **lint**: code, run before acting, at zero tokens;
- a **measured check**: code over real captured data at the corpus judge windows;
- a **card** (≤3 KB): a decision table;
- a **lens** (≤1 KB): one question for an independent reviewer.

Cards load only for the crew in play. **W45 loads only rows 1, 6, 10, 11 and the Release Gate.**

| # | Specialist | Owns | Lint before acting | Measured check after | Lens |
|---|---|---|---|---|---|
| 1 | Substack (Home + Notes) | Notes, P1, P9 | Notes per day as signed; promotion between one in ten and one in two Notes a week; no outside link in reach Notes; any question at the end; subscribe path verified; paywall and offer untouched | 24h: clicks, free subscribers (Buffer `freeSubscriptions` and Note stats); 7d: Growth sources | Would a leader forward this, and does it name the work rather than link out? |
| 2 | Meta (IG + FB, paired) | feed, carousel, Reels, Stories, memes | `social.preflight`; pair dedupe; Story only after the feed readback; no link-sticker claim; AI label where realistic synthetic media is present | 72h: reach, sends, saves, follows vs own median (Reels by Insights read) | Would someone send this to a colleague? |
| 3 | YouTube | Shorts, video memes | real video only (no still posing as video); Related video = verified matching full video; description opens "Read it free" + tagged link | 72h: views, view duration, Short-to-long clicks, subscribers | Does it make someone want the full video? |
| 4 | TikTok (personal) | photo, video, memes | personal voice reviewed; photo posts never set the AI flag; caption leads with the searchable phrase; no foreign watermark | 72h: watch time, profile visits, follows | Would a stranger watch to the end? |
| 5 | X (personal) | receipt posts | weighted length; native image + claim; link placement only per a registered experiment | 48h: replies, profile clicks, link clicks, follows | Is the claim concrete and sourced? |
| 6 | Threads (personal, new) | posts | personal voice; length limit; link last | 48h: replies, follows, link clicks | Does it start a real conversation? |
| 7 | LinkedIn (personal) | unscheduled drafts | no `dueAt`; no body link; document route held | 48h after his click: profile visits, Featured clicks, comments from target titles | Sincere, warm, humble and useful? |
| 8 | Canva Studio (new) | brand kit custody; memes, Note images, receipt/quote cards, scorecards, poll results, profile art, resizes | kit tokens only; approved template; every quote a literal match to the published piece; channel dimensions; clean export; AI-image label; boilerplate guard; `boundary.json` owner is canva-lane | Gate outcome (approve, amend, decline) and downstream verdicts | On-brand, true to the piece, scroll-stopping? |
| 9 | Engagement Preparer | Krish's reply list | drafts only; thread under 12h; one named person; no links in LinkedIn comments | replies he confirms; reply-to-follow | Does this say something real to this thread? |
| 10 | **Measurement Specialist** (attribution, ladder, Google Analytics) | North Star, sources, links, GA4 | every own link carries the four UTMs with `utm_content` = its placement identity (the GA4 join key); sources classified per the approved `sources.json`; zero paid | Weekly all-source and organic counts vs the ladder, from Substack Growth sources (the North Star source). Per-post and per-channel free sign-ups and paid subscriptions from GA4 by `utm_content`, `utm_source` and campaign, reconciled each week with Substack sources (the more conservative reading wins and the gap is logged). Urgency computed; the all-source count cross-checked with Control Center. Feeds the What-Works Analyst every subscriber number it judges by | Is every number read today, with its source and denominator, and do GA4 and Substack agree? |
| 11 | **What-Works Analyst** (owns "what works") | experiments, verdicts, lessons, channel defaults | one live test per channel; one variable; flip rule registered before the test | Each post gets `works`, `neutral`, `fails` or `insufficient` at its window vs its own median. Defaults change only through `experiment_decision` (at least 6 observations, "association, not cause"). New channels run 2 weeks as baseline with no verdicts. The weekly ledger goes into the Sunday check-in, and cards change only through approved verdicts | Is this verdict from measured data, with a denominator and enough observations? |
| 12 | Channel Auditor | Saturday audit (existing) | existing allowlist plus G1 | saved page matches the record | Does the saved page match the record? |
| - | Release Gate (code) | every publish | slot bytes equal the signed manifest line; decision digest matches (amended version wins); frequency caps | Buffer "sent" plus native URL readback per destination; uncertain means held, never blindly retried | Did exactly the signed thing go out, once? |

**Readiness is computed.** `run status` derives each slot's stage from evidence:

`drafted → linted → reviewed → signed → queued → live → measured → verdict`

No session writes a stage.

**Review.** One fresh-context reviewer per gate packet sees only the lens and the artefact. Its verdict is attached to the packet Krish sees. It is review evidence, not proof of independence.

**New rules proposed from the corpus, not imposed.** LinkedIn at most four a week; at most five hashtags on Meta. Both are proposed at G-A with their citations.

## 4. Checks mapped to the failure history

- **Kept:** all 168 existing tests, each registered in `failures.json`.
- **New behavioural tests:** every doc-only item gets one; the appendix maps each F and G item.
- **Lessons into code.** `release.py` builds the exact Buffer MCP arguments from doc-only lessons. The session passes them verbatim; code checks the readback. The tests are:
  - `test_edit_sends_complete_payload` (F01)
  - `test_tiktok_photo_never_sets_ai_flag` (F02)
  - `test_preview_clear_uses_mutation_not_null` (F03)
  - `test_scheduled_is_not_sent` and `test_live_needs_native_url_per_destination` (F07, F08)
  - `test_link_sticker_never_claimed_automatic` (F09)
  - `test_draft_save_sets_saveToDraft_without_dueAt` (F13)
  - `test_story_one_frame_per_post_dedupe_by_media_url` (F14)
  - `test_imported_posts_not_engine_publications` (F17)
- **Route tests.** `test_route_refuses_os_dialogs_and_excluded_browsers` (F04, F22) and `test_spec_cannot_touch_paywall_or_offer_without_decision` (F34).
- **Measurement tests.** `test_status_never_counts_drafts_as_outcomes` (F51) and `test_doc_links_resolve` (F43).
- **Marker tests** keep running, each with a behavioural twin.
- **`rules.json` stores each rule's verbatim source quote.** A test fails if the quote drifts from its document. That is how a run can skip the 40+ KB of standing docs safely.

## 5. Session protocol

- **Run sessions.** Release is one short session per signed go-live. It creates every slot in Buffer with an exact `dueAt` from the manifest, then reads back "scheduled". Buffer does the posting.
- **Daily measure session.** Reads back "sent" and the native URL, captures metrics at their windows, writes verdicts and checks the express intake.
- **Browser-only reads** (Substack Growth sources, Note stats, Reels and TikTok Studio, the Saturday audit) stay in Codex on his PC, the in-app browser he mandates.
- **Pack ≤36 KB.** `run pack` compiles:
  - `docs/RUN.md` (≤8 KB);
  - the spec slice (≤10 KB);
  - the cards in play (≤12 KB);
  - findings, gate status and the directive (≤6 KB).

  Code refuses a larger pack.
- **Budgets.** These are provisional; Phase 0 replaces them with baseline divided by 20.
  - Release: ≤25 calls, ≤0.6M tokens, ≤15 engine minutes.
  - Measure: ≤20 calls, ≤0.5M tokens.
  - Express: ≤15 calls, ≤0.5M tokens.
  - `run cost` meters each session from its own log (Claude `list_events` usage, Codex rollout JSONL). Engine time, waiting for Krish, and his review minutes are kept as separate clocks.
  - A session over budget ends at a gate packet. It never loops.
- **No mid-turn questions.** Every question becomes a gate packet, and the session ends.
- **No engine building in a run.** Run sessions commit nothing to `engine/`; CI on the branch refuses it.
- **Express intake.**
  - **Now:** Krish adds an idea in **Buffer Ideas** on his phone. The measure session checks three times a day and builds from it.
  - **Later:** the content.krishraja.com board fires a trigger the moment he submits.
  - **Promise:** a 1-hour turnaround is promised only for formats re-verified in Buffer. IG single image, IG Reels and YouTube video are unverified today, and the verified routes expire 2 to 3 Nov.
- **Krish's minutes.** Gates come first. Engagement gets whatever remains of the 20 (30 on Sunday). Measured from gate timestamps.

## 6. Codex task cards

- **Card spec.** `tasks/cards/<id>.json` (≤6 KB) holds:
  - pinned `model: gpt-6.1-sol` and `effort: medium`;
  - maximum minutes and calls;
  - the worktree `../growth-wt/<id>` on branch `codex/<id>`;
  - `write_allow` globs and at most 5 read files;
  - the never-list: no git, network, MCP, publishing, new dependencies, or writes outside `write_allow`;
  - the interface verbatim, acceptance commands that must exit 0, and the JSON return.
- **Lint.** `run card lint` enforces it.
- **Dispatch.** On Krish's PC: `node <plugin>/scripts/codex-companion.mjs task --background --fresh --write --model <pinned> --effort <pinned> --cwd <worktree> --prompt-file <card>`, then `status --wait` and `result`. Never codex-rescue.
- **Allowance guard.** It reads Control Center's `get_service_economics_snapshot` if that carries Codex usage; otherwise a dated reading Krish confirms. It refuses above four fifths of the weekly allowance, or with no reading, unless a Krish decision id is passed.
- **Verification.** Claude reruns the acceptance commands outside the sandbox and checks the diff stays inside `write_allow`.
- **Now.** The allowance is spent until about 2 Nov, so **Phases 0 to 3 are built by Claude at zero Codex spend.** The dispatch tooling is deferred; the card spec ships.

## 7. Tool routing (Control Center placements of 26 Oct, verified today)

| Job | Route | Fallback | Notes |
|---|---|---|---|
| Queue, publish and read back: IG, FB, YT, TikTok, X, Threads, Notes; LinkedIn drafts | Buffer MCP through `release.py` | Codex in-app browser | Team trial decision due **31 Oct** |
| Brand kit (one-off) | Cowork computer use on Krish's PC (Canva UI, H: drive Ventures assets) | none | No MCP kit tool exists |
| Amplification assets | Canva MCP: `create-brand-template-draft`, `publish-brand-template`, `autofill-design`, `resize-design`, `export-design` | none | Direction via krish-design; never publish from Canva |
| Express intake | Buffer Ideas, then the content.krishraja.com trigger | Control Center list | |
| Note subscriber metrics | Buffer `freeSubscriptions` and `paidSubscriptions` | Note stats via the Codex browser | |
| Off-platform attribution: sessions, free sign-ups and paid subscriptions per post and channel | **Google Analytics 4** property mymu (`G-VC5V9LDE17`, home.makeyourmindup.ai), **through Control Center** (Krish, 27 Oct: "just get google analytics from control center"). Control Center already reads it daily (`api/growth/snapshot.ts` into `web_analytics_daily`); the brief `docs/briefs/2026-10-27-control-center-ga4-read.md` asks it to add a `utm_content` breakdown and a `web_analytics` block in this engine's directive | `engine/run/ga4.py` direct read, unused unless credentials are set; Substack Growth sources | Event names are confirmed from Control Center's event list before use, never guessed. Numbers go to the Control Center report, never into the public repo |
| North Star sources, Reels and TikTok analytics, audit | Codex in-app browser | none | Never Skyvern, Chrome, Stripe or cookie export |
| Gates and decisions | Control Center protocol; the board later | Control Center list | |
| Deferred (spend) | Apify radar runs | manual read | |
| Not used | HeyGen and ElevenLabs (backup, 27 Oct); Higgsfield and Runway (Heartside and Full Time); retired: Instantly, Apollo, Fireflies, Descript | | |

## 8. Phased build and acceptance

**Cutover (lose nothing).**
- Notes and Threads have no current route, so **they prove the new route in W45.**
- Meta, YouTube, TikTok and X move in W46, after W45 has zero release defects and every readback verified.
- The 9 automations, the heartbeat and `post --deliver` keep running until then.
- Nothing is deleted.

**Phase 0: Baseline (by Wed 28 Oct).**
- `growth.py run cost --baseline` runs on Krish's PC (one PowerShell command). It reads the Codex rollout logs for this repo, read-only.
- It writes aggregates only (tokens, calls, mean context, engine time and wait time per job kind and for the 26 Oct pilot) and pushes on a branch.
- *Accept:* tokens and engine minutes per verified post for carousel, X, TikTok and Stories.

**Phase 1: Attribution, safety gaps, autonomy loop (by Thu 29 Oct).**
- `measure.py` with a structured Growth-sources capture. It reports **both** all-source and organic counts; `sources.json` waits for Krish's approval at G-A.
- `run northstar` writes the NOW.md state line (a new ruling: scheduled runs may commit `lists/` and that one line).
- Daily followers per channel; weekly paid subscribers.
- **GA4 attribution (Krish, 27 Oct: "Make sure this is a part of your Measurement Specialist").** A `ga4_report` capture: property, date range, rows by session source, medium, campaign and content, with sessions, sign-ups and paid subscriptions. It joins on `utm_content` = slot placement identity, giving per-post subscriber attribution off Substack. `invariants/ga4.json` holds the event names, marked unverified until read from the live Events report. A weekly reconciliation against Substack Growth sources logs any disagreement.
- G1 to G8 fixed.
- **G9 autonomy loop:** stages, `parent_proposal_id`, amendments, and the protocol schema version Control Center accepts.
- *Accept:*
  - A synthetic fixture produces the expected counts.
  - A synthetic GA4 report joins to the right slots by `utm_content`, and an unverified event name is refused.
  - The real W44 all-source count equals Control Center's figure and an independent page read.
  - G9 passes the four GET-GOING Step 1 tests against the existing Control Center stand-in (`tests/test_control_center.py:36`).
  - CI passes on ubuntu/windows × 3.9/3.12.

**Phase 2: Spec, invariants, release (by Sat 31 Oct).**
- `spec.py`, `release.py`, `rules.json` (quote-anchored), `failures.json` and `boundary.json`.
- The Threads code changes and the W45 cards (rows 1, 6, 10, 11 and the Release Gate).
- `run pack`.
- *Accept:*
  - Every F and G item has a passing guard.
  - A seeded bad spec fails with the right ids.
  - The pack is 36 KB or less.
  - A fixture manifest releases to a Buffer stand-in and refuses one changed byte.

**Phase 3: Brand kit and templates (Wed 28 to Sat 31 Oct, in parallel).**
- **The Cowork prompt.** I write it at `docs/briefs/2026-10-27-canva-brand-kit-cowork.md`. Krish opens the H: drive Ventures folder, logs in to Canva and starts it; his time is about 5 minutes. Its scope:
  - read-only on the makeyourmindup assets;
  - writes only a new "makeyourmindup" kit (logos, colours, fonts) and folder;
  - where content-engine's approved house style (`makeyourmindup-video-v1`) disagrees with an asset, the house style wins, and the conflict is reported;
  - never: publishing, sharing, deleting, upgrading or other apps;
  - it ends by reporting the `brand_kit_id`.
- **Templates.** I then build about 6 templates by Canva MCP: Note image, receipt/quote card, scorecard, poll result, meme frames and profile art.
- *Accept:* Krish approves the kit and templates in the W45 G-A.

**Phase 4: Remaining crew, express lane, ve intake (2 to 6 Nov, ready for W46).**
- Cards 2 to 5, 7 to 9 and 12; `canva.py`; the express lane; `intake.py`.
- The `ve` package contract: `package_id`, `piece_url`, format, editions per channel, and files (`sha256`, public `url`, `alt_text`, dimensions, duration). `creative_approval_ref` resolves to Krish's recorded decision. The delivered signal opens G-B.
- Brief to content-engine at `docs/briefs/2026-11-ve-growth-package.md`.
- *Accept:* a synthetic ve package lints, and a mismatched hash is refused.

**Phase 5: Board contract (by 6 Nov).**
- This repo publishes the JSON contract: queue, ideas, gate packets, results.
- Two briefs: content-engine for the Growth tab on content.krishraja.com, and Control Center for writing decisions from the board. Rule 7 holds: this session writes neither repo. W45 and W46 use the Control Center list.
- Its acceptance belongs to those repos.

**Phase 6: Measure the 20x target.**
- On W46, against Phase 0, on **matched formats** (carousel, X, TikTok, Stories): tokens per verified post and engine minutes per verified post, each at most the baseline divided by 20.
- Notes and Threads are reported separately.
- Krish's measured review stays at or under 20 minutes a day (30 on Sunday).
- A run with no measured outcome is not done. Actual ratios are reported as measured.

**The rest of GET-GOING, mapped:**
- Live baseline: Phase 0/1.
- Step 0 (Control Center brief line): Phase 1.
- Step 0.5 (HeyGen): stays open, his call; HeyGen is on backup.
- Step 1: G9.
- Step 2 (loud token failures): Phase 2.
- Step 3 (acting on experiments): What-Works.
- Step 4 (`paid_boosts_usd`): Phase 1, as the zero-paid invariant.
- Step 5 (daily best recommendation): Phase 4 pack.
- AGENTS "Open setup": the ninth automation stays a hold until a Codex session can schedule it; the AEO line is unchanged.

## Decisions that stay Krish's, at the time (approving this plan grants none of them)

1. **Today: connect Substack in Buffer** (a new connection). Until then, W45 Notes are drafted for him to post by hand.
2. **Codex.** The existing automations may be drawing paid credits until about 2 Nov.
   - **My recommendation:** keep numbers and the 09:00 heartbeat; pause pitches, partners and swaps (they only produce holds), plus radar and answer, until the reset.
3. **Cloud run access.** Place the **existing** engine token (not regenerated) as a Claude environment secret, and allow controlcenter.krishraja.com in the network policy. Cloud runs keep no private evidence; anything private is produced only by PC sessions, in `.scratch/`.
4. **The standing W45 to W52 plan, `sources.json`, and each G-A, G-B and G-X:** posting.
5. **Buffer's Team plan by 31 Oct:** spend.
6. **New Claude cloud scheduled tasks** (release, measure): new automations.

## Verification

- **CI on every phase:** `python growth.py --self-test`, `doctor --offline`, `dry-run`, `run lint`, `run card lint` and the quote-drift test, on ubuntu/windows × 3.9/3.12.
- **Attribution:** the W44 all-source count equals Control Center's figure and a fresh read of the Substack page. The NOW.md line equals `get_venture_state`'s live urgency.
- **Release (W45):** for every Notes and Threads slot, Buffer shows "sent", the native URL is reopened, and the slot bytes equal the signed manifest. Zero unsigned posts.
- **What works:** each W45 post gets a verdict or "insufficient" with its denominator. The first ledger comes in the 8 Nov check-in.
- **Close-out:** a verification-loop pass with observable evidence, and NOW.md notes what moved.

## Appendix: failure register (F01-F54 from inventory, G1-G9 from code)

**Buffer and native delivery**
- **New tests:** F01 scheduling-only edit rejected; F02 TikTok photo AI flag; F03 null link attachment; F04 file chooser and OS dialogs; F06 draft id reused as approval identity (partly tested already); F07 Facebook reopen timeout; F08 scheduled shown before sent; F09 Instagram link sticker; F10 Facebook AI overlay (open; flag to production); F11 Story frame overlap; F13 default queue mode; F14 Story composer quirks; F15 Buffer connector instability (fallback in pack); F16 TikTok URL redirect; F17 imported posts misread; F18 uncertain saves (Buffer side).
- **Already tested:** F05 PNG success read as document support; F12 illustration boilerplate; F19 stale capability evidence; F20 authority creep (gets a negative test); F21 package integrity.

**Browser and audit**
- **New tests:** F22 Skyvern and external browsers; F30 X profile link limit; F34 automatic paywalling.
- **Invariant only:** F23 re-login.
- **Already tested:** F24 YouTube truncation; F25 no-op save; F26 a Save toast is not persistence; F27 stale value overwrites an edit; F28 partial coverage; F29 unverified link destinations; F30 YouTube title limit; F31 protected fields, stale evidence and missing timestamp.
- **Kept as process:** F32 the weekly audit.
- **Open audit items:** F33 "Iput"; F35 the About series order.

**Engine, Control Center and CI**
- **Already tested:** F36 pre-correction write (partly); F37 percent-encoded URLs; F38 409 handling; F39 token and redirect leakage; F40 unknown reported as zero; F41 duplicate outreach (plus G2); F42 voice rules; F45 attribution labels; F48 untracked own links; F49 corpus line endings; F50 feed and measurement rules.
- **New tests:** F43 broken doc link; F51 drafts read as ROI.
- **Workflow config:** F44 CI Python 3.9.
- **Doc only, with the Windows timezone tested:** F46 Mac commands on Windows.
- **Config tested:** F47 the ninth automation; scheduling it stays open.

**Added by the 27 Oct closeout session (main, `ab1c852`):**
- F52 `buffer-document-preview-hold` (supersedes `document-upload-unverified`): Buffer loses a saved PDF preview. Hold, never blind retry.
- F53 `linkedin-reader-continuation`: the reader journey is validated end to end; no raw URL on a card.
- F54 `substack-filter-settle`: a Growth-sources read counts only once the selected window label and the values have settled together. The Phase 1 capture schema records both.

**Code gaps:** G1 to G9, as listed in Context, each with a fix plus a test.
