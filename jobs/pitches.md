# Job: pitches

Kind `pitches`. Read the shared instructions and `docs/ENGINE.md`.

First, before reading any source: `python growth.py cc start --job pitches --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Read recent published pieces. Find at most three genuinely relevant shows
   or newsletters taking guests, with a recent episode or article read in
   full. Preserve the host's source and a literal excerpt, plus the MYMU
   finding offered. No invented subscriber counts or warm introductions.
2. Check partner and pitches lists. Suppress confirmed sends within 90 days
   using `growth.py relationship EVENTS.json PERSON_ID --cooldown-days 90`.
   Unsent drafts do not mean the host was pitched. Respect declines and
   pending conversations. Do not redraft the same unsent offer every week.
3. One personalised draft under 150 words, built on the direct outreach
   structure and proof hierarchy in `knowledge/COPY-DOCTRINE.md`: a precise point from their work,
   a listener problem, supported talk points, a real companion asset from
   the published finding/source list and one easy next step. No promise to
   create an unapproved editorial asset. Sign: "Krish Raja, makeyourmindup.ai,
   hello@krishraja.com". Track the listener landing and placement distinctly.
4. Prepare the offer in the local envelope, never a platform compose box.
   A Gmail draft is optional only in a separately authorised scheduled job
   with that capability; this implementation makes no such external write.
5. Record `drafted` in `lists/pitches.md`, not sent. A later human-confirmed
   event with evidence starts the cooldown. Merge the day's work, select
   within budget, check and follow `AGENTS.md`'s delivery rule.
6. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job pitches --envelope .scratch/pitches.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
