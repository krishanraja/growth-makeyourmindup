# Job: the front door

Kind `conversion`. Read the shared instructions, `docs/ENGINE.md`,
`docs/CHANNEL_PLAYBOOK.md`, `channels.json` and `journeys.json`.

First, before reading any source: `python growth.py cc start --job conversion --deliver`.
Read the directive it prints ("Reporting to Control Center" in `AGENTS.md`).

1. Audit the actual journey on mobile and desktop, logged out where readable:
   profile or native asset, matched landing, subscribe form, confirmation,
   welcome and useful next read. Read-only means do not submit a real form,
   trigger an email, change settings or create a test subscriber. Mark the
   steps that require a human action as not verified.
2. Check every configured channel surface. Exact benefit text must be
   accessible without relying on a logo image. Confirm Monday/money,
   Wednesday/hood, Friday/gap; consistent names, pin freshness and usable
   contrast, tap targets, captions/alt text, focus and mobile layout. Verify
   the feature on this account before suggesting it as available.
3. Check each external destination, redirects, tracking completeness and
   topic match. Internal navigation must retain original acquisition.
   Respect consent; do not collect unnecessary personal identifiers. The
   website's incoming-source handoff to the subscription needs verification.
4. Inspect welcome copy only when readable. Prefer one useful first read,
   then a later reply/forward/referral ask. Audit recommendations/referrals
   without changing them. Substack-native referral codes must survive URL
   tracking. Paid conversion stays subordinate to reader value and trust.
5. Search: inspect indexability, canonical URLs, titles/descriptions, actual
   sitemap coverage, image metadata, article/video links and structured
   data. Do not claim Substack lacks its existing article sitemap/schema.
   Topic resources must add evidence from published work, not thin duplicate
   pages. Respect robots, noindex, community rules and truthful author data.
6. Judge front door copy with `knowledge/COPY-DOCTRINE.md`: Promise then
   Offer lead, the Value Equation for a free subscription, the persuasion
   chain's weakest link, proof only from published pieces. At most five
   candidate fixes: exact surface, observed defect and date,
   literal evidence, proposed copy/settings, owner, priority, estimated
   minutes, prerequisite and a success check. Access gaps are findings, not
   defects proven on a page you could not read. Queue the highest-impact
   verified blocker within the shared 20-minute budget. The voice rules
   never inform this judging.
7. Once the judging is done, write the proposed copy for each kept fix
   under Krish's approved voice rules (`.scratch/cc/voice-rules.txt`,
   "His approved voice rules" in `AGENTS.md`): how it is written only,
   never what it is about. Then prepare/check and follow `AGENTS.md`. External profile/website/settings
   changes and Control Centre UI work remain handoff items.
8. Last, report to Control Center with this run's actual file names:
   `python growth.py cc finish --job conversion --envelope .scratch/conversion.json --queue .scratch/queue.json --deliver`.
   It must print "readback digest matches" and "attempt succeeded". If it
   prints a failure code instead, name that code in the final message.
