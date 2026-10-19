# Job: partners

Kind `partners`. Read the shared instructions and `docs/ENGINE.md`. Map
quality matters more than a quota. This work shares the day's budget.

First, before reading any source: `python growth.py cc start --job partners --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read `lists/partners.md`. Build towards the source playbook's 100-account
   map as relevant evidence allows: peers, leaders, adjacent creators,
   podcasts, editors, communities, researchers, institutions and events.
   Add only genuinely researched accounts, with recent-work URL/excerpt,
   audience overlap, a useful offer and a real warm route if one exists.
2. Choose at most three candidates whose next step is useful and due.
   The warmth ladder is useful public engagement, private insight, small
   ask, co-made asset, recommendation, recurring partnership. Actual inbound
   interest can justify a later relevant step. Never invent prior contact.
3. Check real events, not draft dates. `growth.py relationship` evaluates
   confirmed interactions. Drafts do not start cooldowns, advance stages or
   count as collaborations. A decline suppresses future asks. Krish must
   confirm sent/replied/booked/published events with an evidence URL.
4. Write with the direct outreach structure and proof hierarchy in
   `knowledge/COPY-DOCTRINE.md`. Each draft names the recent work, the shared reader, the precise benefit
   and one proportionate ask, under 120 words. A partner kit has its own
   tracked placement; no implied endorsement or guaranteed audience.
5. Update the list with a stable person ID, sourced facts and `drafted`
   status only. Commit actual list changes under `AGENTS.md`. Prepare a v2
   envelope, merge today's queue, then apply the delivery boundary.
6. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job partners --envelope .scratch/partners.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
