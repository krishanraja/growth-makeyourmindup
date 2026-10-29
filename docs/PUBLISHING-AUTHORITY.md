# Publishing authority

Rulings: Krish, 26 October 2026. The latest X/TikTok clarification supersedes
this day's earlier personal-drafts-only instruction for those two accounts.

## Approved content: delegated packaging and cadence

After Krish has seen and approved the content, Growth may choose faithful
platform packaging and schedule/publish to the verified makeyourmindup
Instagram, Facebook and YouTube accounts, and Krish's scoped X and TikTok.
Aim for one useful daily post per channel where an approved native edition
exists. Substack retains its approved editorial rhythm. Record missing
supply/capability; never fill a slot with unapproved creative or duplicates.
New creative, claims or meaning-changing replacements require approval.

X and TikTok remain personal identities for voice and reputation. Their
explicit cadence permission does not turn them into publication accounts.
Read ACCOUNT-VOICE.md. LinkedIn is the separate human-final-publication route.

Record creative approval, ordered immutable assets, exact account/payload,
standing permission, time, attempt budget and independent native readback.
Scheduling proves only a scheduled post. Actual publication needs the native
URL/content/account and a dated readback. Preserve uncertain outcomes.

## LinkedIn and unscoped personal identities

Krish's LinkedIn is unscheduled drafts only. Never queue, schedule, publish,
submit comments, like, follow or message. He reviews and makes the final click.
Do not edit live LinkedIn posts or profile fields. This latest boundary also
applies to the older existing-field audit permission.
There is no daily LinkedIn quota. Its confirmed North Star is trusted
commercial-AI judgment and relevant professional relationships first; reach
and publication subscribers are secondary. Other personal identities, such as
Threads, are not in scope merely because Buffer connects them.

## Meta coordination and Stories

Treat branded Instagram and Facebook as paired distribution of an approved
package, with channel-specific packaging and matched timing. Verify both
outputs independently and deduplicate against native cross-sharing. Do not
claim automatic cross-sharing is enabled unless actually verified.
Plan Stories as a native continuation: hook, useful proof, practical action,
and a real route to the full piece/feed. Native 9:16 editions come from
Content Engine and require creative approval. Test actual Story capabilities;
never draw fake interactive controls or invent poll/link-sticker support.

## Public copy and production ownership

Never add illustration-generation boilerplate to public art, captions or
descriptions. Keep source/provenance privately and use appropriate native
platform metadata where supported. This rule does not remove factual limits
needed to understand a test. Content Engine owns all production standards;
Growth owns amplification ideas, channel best practice, delivery and learning.

No spending, new connections, deletion, engagement submission or live paid-offer
change follows from this publishing permission. Existing audit authority is
separate. Never Stripe, Skyvern, external Chrome or cookie export.

## Structured enforcement

Channel profiles separate account_context (voice) from publication_mode
(authority). X/TikTok alone have approved_content_cadence; branded accounts
have approved_brand_content; LinkedIn has human_publish_only. Inventory
rejects any other personal publishing expansion. Preflight holds LinkedIn
publication, verifies package hashes, rejects public illustration boilerplate
and always requires live identity/schema/authority checks. Offline validation
never authenticates approval or performs an external action.

## 27 October 2026: Notes, Threads and express posts

Rulings: Krish, 27 October 2026 (`CHANGES.md`). They add to the 26 October
rulings above; everything else above stands.

- Substack Notes and Threads are added. Notes post as the publication under
  approved brand content, at the cadence he signs. Threads has delegated cadence
  for approved content, like X and TikTok, and keeps Krish's personal voice;
  read ACCOUNT-VOICE.md. It stays a personal identity, not a publication.
- The line above that other personal identities, "such as Threads, are not
  in scope merely because Buffer connects them", is superseded for Threads
  only. It still holds for every other personal identity. The structured
  enforcement line "X/TikTok alone have approved_content_cadence" now reads
  as X, TikTok and Threads.
- LinkedIn is unchanged: unscheduled drafts, and his final click.
- Signed exact payloads post autonomously only through the go-live step
  (AGENTS.md, Autonomy), with the readback rules above.
- Ad-hoc meme ideas are built, shown to him, then queued and posted only on
  his approval of the exact payload.
- Substack articles keep their approved editorial rhythm; no daily target.
- No spending, new connections (including connecting Substack in Buffer),
  new automation or engagement submission follows from these rulings.
  Those stay his decisions at the time.

Correction, 27 October 2026 (later the same day). Substack Notes post from a
person's profile, not the publication. Krish connected Substack in Buffer as
the profile named Krish, the publication owner, whose handle is mindmakerlive
(lesson `substack-notes-identity`). Notes therefore keep his personal voice
and take the same delegated cadence as X, TikTok and Threads, at up to two a
day as signed. The bullet above saying Notes "post as the publication under
approved brand content" is superseded by this paragraph. Renaming the
retired mindmakerlive handle is a profile change held for him.

## 28 October 2026: approve each day on Monday

Rulings: Krish, 28 October 2026 (`CHANGES.md`), from the plan he approved
that day. They add to the rulings above; everything above stands unless a
line here says otherwise.

- **Go-live is "Approve each day Monday".** Approving a day on the Monday
  final board authorises scheduling exactly that day's posts, nothing more.
  Each approved post reaches this engine as a Control Center go-live
  decision bound to its payload sha256, its Buffer channel and its slot,
  read in the engine's own run (AGENTS.md, Autonomy). Growth schedules it,
  reads it back from Buffer and checks the sha. He can pull any post until
  its slot, and a pulled post is never scheduled again without a new
  approval. Reading one decision per post, and the pull, are Wave 2 work
  (plan W5); until they land, release reads the signed `decision.json` as
  `docs/RUN.md` says, and nothing in this repository pulls a scheduled post.
- **Routes all go through Buffer:** "buffer is connected to youtube and
  substack". That covers Instagram Reels and carousels, TikTok, X, YouTube
  Shorts and long-form, and Substack. Each route's first real post is a
  capability check he approves on that Monday; until a route has passed
  it, the route holds. Release enforces this: on a route that
  `social/tools/buffer.json` does not show as verified and fresh, it
  schedules only the run's earliest approved post, marked
  `capability_check`, and holds the rest as `route_not_verified`. A check
  already released in any run's ledger is the route's one check, so a later
  run holds that route as `route_capability_check_pending` rather than
  sending a second one. When that
  post's live readback passes, a reviewed change records the route there as
  verified, with the date and the tested operation, and the rest release.
  If Buffer's Substack channel carries only Notes (it
  is his personal profile today), the article falls back to a saved draft
  with a deep link, and he clicks publish. Release does not post articles
  or YouTube today: YouTube waits on a signed title and category in the
  slot, and both routes wait on their capability checks.
- **LinkedIn stays click-only.** Unchanged: unscheduled drafts and his
  final click.
- **Only this engine's eight Buffer channels.** The Buffer organisation is
  shared with other ventures. Release acts only on a channel whose
  service, name and channelId all match its pinned entry, and refuses the
  fulltime.fm TikTok, the Heartside Facebook Page and both yourdoghasnotes
  channels by id, wherever they appear (`engine/run/release.py`).
- **Copy.** Every post's words pass content-engine's copy lint before
  release: "don't add stupid eyebrow text and asterisks and "generated by
  AI" and "Krish's take" verbal diahorrea like you tend to. This needs to
  feel like a world class media channel". A post that hits it is held.
- **The off-day lane.** Tuesday, Thursday, Saturday and Sunday posts on the
  makeyourmindup Instagram, TikTok and YouTube Shorts are Growth's
  (`docs/ENGINE-BOUNDARY.md`). Each is approved with one press, on the
  Sunday ideas board or as a mid-week green light. That press writes a
  go-live decision bound to the payload sha256; Growth puts the post in the
  next free off-day slot on each chosen channel, never on Monday,
  Wednesday or Friday and never over a daily cap, and reads it back.
- **Engagement stays prepared only.** The daily queue is drafted here and
  he submits every reply himself; following and liking stay his.

No spending, new connection, automation or account-setting change follows
from these rulings. The Buffer plan (due 31 October) is his decision.

## 29 October 2026: approve the idea and the mock

Ruling (Krish, 2026-10-29): approval moves to the idea and the mock on
Instagram, YouTube, TikTok and X, three or four posts a day each (`CHANGES.md`;
`docs/MIX.md`). "I just need to be in control of the idea and the mocks and
then I'm happy to let you let that engine just go for gold." It adds to the
rulings above; everything above stands unless a line here says otherwise.

- **The concept is what he approves.** A concept is one idea, its one claim
  and its mock files, bound by `concept_sha256`. He approves each concept
  once, in the week's mix plan proposal (stage plan, behind strategy), whose
  exact payload lists every concept hash. That yes is to reach release as
  decision.json `concepts`, written only from the readback of his decision,
  bound by the spec signature's `concepts_digest` and `concept_proposal_id`
  (`engine/run/decision.py`, fields in `docs/CONCEPT-MANIFEST.md`).
- **It authorises every post made from it.** On those four channels the
  engine makes, schedules and publishes each post derived from an approved
  concept with no per-post approval, through `growth.py run release`, the
  Buffer channel lock and every check above (copy lint, share asks, the
  ecosystem route, route capability checks, the creative bar). For these
  posts this supersedes "Approve each day Monday" and "New creative ...
  require approval" above: the approved mock is the creative.
- **A post that departs from its mock is held, never published.** It must be
  one of the concept's approved placements, carry only its mock files (a
  re-render is a new hash and a new approval) and carry its claim word for
  word. Release holds anything else as `departs_from_approved_mock`.
- **His no stops it.** A decline of the mix plan, on any digest, approves
  nothing and is read before anything else about the plan; a concept he
  deletes or changes in his amended payload is stopped; any other line he
  changes approves nothing until a plan carrying his change is approved; a concept he purges
  later (`stopped_concepts`), or a stop on the mix plan in the loop's go-live
  ledger, holds every post made from it, including any signed one by one.
- **Each post still clears the bar and the cap.** With no signature of his
  on each post, release holds one with no passing review at its own payload,
  one past the lower of its channel's live cap and the cap the plan states
  (four a day) across every run, and every concept post while a decline is
  unmatched to its plan; the loop records stops and unmatched declines in
  the go-live ledger each run.
- **The mix plan is the go-live for its concepts.** The loop's own run
  writes his decision into `decision.json` (R104). With no go-live for the
  week the decision is concept-only, and only posts made from an approved
  concept can release; any other post still needs the week's go-live.
  Every loop run checks the approval again and fails closed: a plan file
  that no longer rebuilds, a yes on another plan digest or an unmatched
  decline leaves no concept approved (`concept_hold`).
  Built and wired, not yet activated: nothing has gone out this way.
- **Volume.** Instagram, YouTube, TikTok and X take four scheduled posts a
  day with a floor of three. Every other channel keeps its bound.
- **LinkedIn stays his click.** Unchanged: unscheduled drafts, and his final
  click. Threads, Substack Notes and Facebook still sign post by post.

No spending, new connection, automation or account-setting change follows
from this ruling. Engagement stays prepared only.
