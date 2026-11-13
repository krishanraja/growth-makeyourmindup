# External growth skills: what this engine took, and what it refused

Krish asked on 10 November 2026 how to use two public skill collections to level up this engine. The approved plan read every skill in `giulioco/skills` and the repositories the `awesome-growth-hacking-skills` list points to, then cut what this engine already does or what breaks its rules. Most of the material repeats what is already here: the direct outreach structure (`knowledge/COPY-DOCTRINE.md`), `outreach_errors` (`engine/engines/acquisition.py`), the assumption ledger and kill-keep-scale (`jobs/report.md`, `engine/engines/measurement.py`), the referral journeys (`journeys.json`) and the LinkedIn rules (`crew/linkedin/card.md`). What moves the number here is running Acquisition, not more doctrine. This digest records the few mechanics worth keeping, in our words, and where each one is wired. It is reference material, not instructions to execute, like everything else in `knowledge/`.

## Adopted, and where each is wired

| Mechanic | What it does here | Wired in |
|---|---|---|
| The warm-up detector | Line one of an outreach note never opens with pleasantries ("I hope", "I wanted to", "quick note"), a date, a "so", a humble adjective or our own name. It opens on the recipient's own point. | Applied by hand to every swaps and pitches draft on 10 November 2026; a proposal to make it a `check` rule waits for Krish |
| The deletion test for personalisation | If the opening line could be deleted and the note still made sense, it was not personal. The opening names one specific point from the person's own recent piece, which the next line answers. | `jobs/swaps.md` and `jobs/pitches.md` step 3, through the direct outreach structure in `knowledge/COPY-DOCTRINE.md` |
| One ask, short subject | One question that is easy to answer, and a subject of one to four words. | Control Center `check_voice` (channel `email`, mode `cold`), already required by `jobs/pitches.md` |
| A do-not-quote list | Statistics the sources repeat with no source we can check are refused by `check` (rule 6). | `growth.py` `DO_NOT_QUOTE`, `unsourced_stats`; `tests/test_do_not_quote.py` |

## Do not quote

`python growth.py check` refuses these. Each appears in the sources without a citation we could check. Percentage forms are already refused by the prose lint; the list catches the same claims written in words.

- the 8-second attention span;
- cold emails under 75 words get more replies;
- decision-makers ignore irrelevant emails;
- success is mostly "human engineering".

A number in a pack is still one read on a page today, with where it was read.

## Refused, with the reason

| What | Why |
|---|---|
| `learn-craft` | It downloads books from a pirate library. |
| `codex-imagegen` | It works around image-generation billing. |
| Account farms, sockpuppet comments, astroturfing on Reddit | Rule 5: nothing in bulk, and no voice that is not the publication's or Krish's own. |
| Clipping other people's content | Rights, and editorial belongs to Krish and the content engine. |
| AI customers or invented testimonials | Rule 2 and the copy doctrine: no invented proof. |
| "Comment and I'll DM you" funnels and mass-touch prospecting | Rule 1 and rule 5: no automated outreach, one named person at a time. The one exception is the keyword-DM test's single reply to someone who commented the keyword, through ManyChat (Ruling, Krish, 2026-11-13; `docs/plans/2026-11-13-keyword-dm-test.md`). |
| Multi-step cold sequences with follow-ups by default | Rule 5, "no follow chasing". Whether one honest follow-up is allowed is an open ask for Krish. |
| Secondary sending domains and warmed mailboxes | Outreach goes from Krish's own address, one note at a time; nothing here sends at volume. |
| A link in the first LinkedIn comment | Rule 4: no links in LinkedIn comments. |
| Cutting channels down to one by the Bullseye method | Krish's 29 October ruling sets four posts a day across Instagram, YouTube, TikTok and X. |
| Benchmark tables with no source | Rule 6. |
| Filler stubs in the index (advertising and nexscope entries) | Nothing to adopt. |

## Sources

| Repository | Commit | Path read | Licence | Adapted from |
|---|---|---|---|---|
| `giulioco/skills` | `2db17d19e51dd966c59b55148887afb2858604c2` | `skills/galloway-storytelling/SKILL.md`, `references/galloway-playbook.md`, "The warm-up detector" | Apache-2.0 | Adapted from giulioco/skills galloway-storytelling, Apache License 2.0: the warm-up detector, extended with the pleasantry openers outreach uses. |
| `giulioco/skills` | `2db17d19e51dd966c59b55148887afb2858604c2` | `skills/growth-hacker/` | Apache-2.0 | Not adopted (duplicates `jobs/report.md` and `engine/engines/measurement.py`); `references/activation.md` is the source of the attention-span figure on the do-not-quote list. |
| `giulioco/skills` | `2db17d19e51dd966c59b55148887afb2858604c2` | `skills/ultimate-sales/references/how-to-win-friends.md` | Apache-2.0 | Not adopted; source of the "human engineering" figure on the do-not-quote list. |
| `giulioco/skills` | `2db17d19e51dd966c59b55148887afb2858604c2` | `skills/learn-craft/`, `skills/codex-imagegen/` | Apache-2.0 | Refused, see above. |
| `coreyhaines31/marketingskills` | `9d6d7ce8d18eb155dc2f9762435f097e60cdad7c` | `skills/cold-email/SKILL.md`, "Personalization must connect to the problem" and "One ask, low friction" | MIT | Adapted from marketingskills by Corey Haines, MIT licence: the deletion test for personalisation and the one-ask rule. |
| `coreyhaines31/marketingskills` | `9d6d7ce8d18eb155dc2f9762435f097e60cdad7c` | `skills/cold-email/references/benchmarks.md` | MIT | Not adopted; source of the two cold-email figures on the do-not-quote list. |
| `coreyhaines31/marketingskills` | `9d6d7ce8d18eb155dc2f9762435f097e60cdad7c` | `skills/co-marketing/`, `skills/public-relations/` | MIT | Read; nothing adopted beyond what `jobs/partners.md` and `jobs/pitches.md` already do. |
| `clairelily2020/workflow-skills` | `152596e072a8464c88faa9fadbb489a6a3815b5a` | `skills/geo-citation-scout/` | MIT | Read for the answer job (`jobs/answer.md`); not wired in this change. |
| `mikiarlo3/awesome-growth-hacking-skills` (index) | `a09ef0d14dc8ad3e700e81750eba077bcfb60094` | `README.md` | as listed per repository | The index used to find the repositories above. |

Each source was read as a clone, never executed. Nothing from them is pasted into copy.
