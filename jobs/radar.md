# Job: conversation radar

Kind `radar`. Read the shared instructions and `docs/ENGINE.md`. The radar
shares the global daily budget; there is no comment-volume target.

First, before reading any source: `python growth.py cc start --job radar --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read published pieces from the last 21 days and the partner lists. Use
   the signed-in browser read-only when available. Find a few live threads
   less than 12 hours old where a particular sourced finding answers the
   actual question. Check LinkedIn, X, relevant YouTube/Substack discussions
   and communities whose rules permit the contribution. Skip blocked access.
2. Save the thread URL, author, creation time, literal excerpt, observation
   time and any community rule. Cite the published piece as well when adding
   its facts. Never use follower estimates as evidence of quality. Rank by
   fit, usefulness, freshness and a genuine partner relationship.
3. Draft at most five candidates, each at most 60 words. Add something
   specific. No flattery-only replies, invented experience or unwanted tags.
   LinkedIn comments have no links, even when `kind_hint` is absent. On
   Reddit, disclose authorship if linking and follow the particular rules.
4. Set `kind_hint: comment` for LinkedIn. Give every candidate `expires_at`
   no later than 12 hours after the thread's creation, with thread evidence,
   source evidence and a success check. If already expired, do not queue it.
   A fresh replacement requires rereading the conversation for context.
5. Prepare, merge all today's work and select within 20 minutes. A drafted
   reply does not advance a partner relationship; a later real action needs
   Krish confirmation and evidence. Follow the delivery rule in `AGENTS.md`.
6. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job radar --envelope .scratch/radar.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
