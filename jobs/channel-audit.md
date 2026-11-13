# Job: weekly live channel audit and repair

Kind `conversion`. This is the first priority for the weekly front-door slot.
Read AGENTS.md, BROWSER.md, docs/CHANNEL-AUDIT.md, docs/NORTH_STAR.md,
docs/CHANNEL_PLAYBOOK.md and knowledge/COPY-DOCTRINE.md. The scoped ruling
of 2026-10-21 supersedes older blanket read-only rules for this job only.

1. Reuse the user's already-open signed-in Codex in-app browser tabs when
   present. Discover them with the in-app browser tool and bind the actual
   tabs; a separate Skyvern cloud session does not share their sign-ins.
   Do not ask for another login based on a different browser's state.
   Skyvern is excluded entirely under the 2026-10-24 ruling. Never create
   a separate cloud session. If the current tool routing prevents using
   the Codex browser, preserve coverage and report that exact hold.
   Verify the active account and ownership in the edit UI. Public
   viewing is not edit access. A login wall, connection error, missing
   permission or unsupported editor is a hold, not an empty successful audit.
   Never request passwords or keys in chat. Never copy browser credentials.
2. Inventory YouTube, Instagram, TikTok, X, LinkedIn and Substack from
   channels.json; follow the website's social directory for corroboration.
   Spotify needs an observed official show URL before it joins the audit;
   do not guess a show by name. Website subscription paths are read-only
   journey checks. Reddit/email/partners are not additional social accounts.
   Added 27 Oct 2026: Facebook and Threads are also inventoried and observed
   from channels.json. Krish extended the 21 Oct audit authority to them the
   same day ("yes extend"), so existing titles, captions, descriptions and
   links there follow the same rules as the other accounts; bio, positioning,
   pins and creative still need his approval. LinkedIn edits are krish_only:
   the engine never saves them, not even after approval (`audit begin`
   refuses them). Since 13 November 2026 LinkedIn is growth-mindmake's
   (Ruling, Krish, 2026-11-13): read it only, and name any LinkedIn finding
   in the final message for growth-mindmake, never as a proposal from here.
   Substack Notes have no audit targets yet.
3. Capture the run start in UTC, display dates in Europe/London. Pass this
   fixed timestamp as `--now` only to `audit checkpoint`. For each
   account inspect its profile, every pin/Featured placement and all posts
   since its last complete checkpoint, or the preceding 30 days on baseline.
   Paginate until the boundary is proved; pinned dates do not end pagination.
   Include open repairs and older posts with dated evidence of continuing
   attention. Unknown post dates stay in scope. Deduplicate by native post
   identity. If capped or blocked, list the unaudited range and keep that
   account's old checkpoint. Never advance every account from one success.
4. Inspect each post itself, expand the full caption/description, follow its
   destination, and watch representative opening/CTA frames. Check title,
   caption, description, links, tags/hashtags, subtitles, overlays/cropping,
   thumbnail, CTA and channel-native continuation. Apply current first-party
   guidance only where relevant. No universal hashtag or length quota.
   Unwatched frames and private analytics stay unverified. Do not submit a
   signup, start an email, like, follow, comment, pin or buy anything.
5. Prepare each exact before/after with source URL, literal excerpt, browser
   observation time, defect, subscriber benefit and a falsifiable success
   check. Preserve facts, voice, topic, functional URL parameters, referral
   codes and visibility. Use krish-content-marketer for conversion diagnosis,
   krish-voice for wording, krish-design for visual diagnosis. Source claims
   from the published piece; flag media defects to its production owner.
6. Run `python growth.py audit plan INPUT --out .scratch/channel-audit/plan.json`.
   For an autonomous repair, re-read the exact field and signed-in owner,
   then run `audit begin` BEFORE Save to persist intent. Make just that
   change in browser. Reload or reopen the saved page and run `audit
   reconcile` with the independently read field. A button click or toast
   never proves success. Pending/uncertain writes require readback before
   any retry. A proved unchanged original may retry once after reconciliation,
   with its persisted total attempt budget. A changed original value means
   re-audit, never overwrite. Wait for save completion before reloading.
7. Creative replacement/re-upload, bios, positioning, pins and unknown
   actions go to approval with exact proposed assets/copy and the expected
   consequence. Existing approval is scoped to an exact replacement, not
   future replacements. Do not use this job to post, send, delete, change
   prices/settings or enable features. Per-post edit controls may expose a
   Publish button: use it only when it saves solely the authorised existing
   field, with no new publication or audience change.
8. Save private input/evidence/receipts and coverage under ignored
   .scratch/channel-audit. `audit checkpoint` accepts only fully covered
   accounts. Keep concurrent runs out with the session lock described in
   docs/CHANNEL-AUDIT.md. Report verified fixes, approval items and access
   holds separately, with exact pages. Never commit real records, metrics,
   account screenshots or drafts to this public repository.
9. A scheduled run may use the existing conversion protocol routes, but
   missing Control Center credentials must not suppress the browser audit
   or cause a second write path. Preserve its private report and name the
   reporting hold. Interactive runs make no Control Center writes. Do not
   claim approval items landed on his list without a digest readback.

Stay quiet when nothing changed and no action is needed. Notify Krish of
verified repairs, approval requests, meaningful findings, or an access blocker
when it first appears or changes. One unresolved login is not a weekly alert
loop. The weekly execution is still required even when the summary is quiet.

## Approved: every profile link points to the tagged subscribe page (Krish, 12 Nov 2026; resumed 13 Nov)

Krish, 12 Nov 2026: "Happy with your recommendations and yes go for the profile links as well." At the next audit, and every audit after it, each account's
profile link is set to its tagged subscribe page below, with `link_purpose: align_subscription`
through `audit begin` and `audit reconcile` as usual: fresh browser evidence of the before value,
the destination opened at the exact URL, and the page reopened after Save to prove it. A profile
that already carries exactly this link is skipped. Nothing else on a profile changes (bio,
positioning and pins still need his approval).

| Account | Profile link |
|---|---|
| instagram | `https://home.makeyourmindup.ai/subscribe?utm_source=instagram&utm_medium=social&utm_content=bio` |
| tiktok | `https://home.makeyourmindup.ai/subscribe?utm_source=tiktok&utm_medium=social&utm_content=bio` |
| x | `https://home.makeyourmindup.ai/subscribe?utm_source=x&utm_medium=social&utm_content=bio` |
| threads | `https://home.makeyourmindup.ai/subscribe?utm_source=threads&utm_medium=social&utm_content=bio` |
| facebook | `https://home.makeyourmindup.ai/subscribe?utm_source=facebook&utm_medium=social&utm_content=bio` |
| youtube | `https://home.makeyourmindup.ai/subscribe?utm_source=youtube&utm_medium=social&utm_content=bio` |

The resumed exact-link instruction uses `social/bio` for the six accounts above. Threads always targets @makeyourmind.up; use its verified branded Buffer connection (13 November 2026).

LinkedIn is Krish's alone (`KRISH_ONLY`): the engine never saves it, and it keeps the profile as it is. Krish, 13 November
2026: "LinkedIn won't let me add that link as a feature, so I'm just going to keep it as it is." Never list a LinkedIn
profile link for him again, and never report its missing link as an alignment problem.
Substack has no profile link target: its subscribe button is the publication's own.
