# Format delivery contracts

The JSON profiles in `../formats/` declare channel fit, accepted media counts,
delivery checks and measurement. Counts describe the edition, not a platform's
maximum. Read the selected profile rather than this entire format catalogue.

For a carousel, Growth decides why the source deserves a swipe sequence and
which destination/continuation it serves. Content-engine creates and judges the
cover, newcomer comprehension, narrative arc and visually distinct ending under
its production standard. Growth verifies the received ordered assets and native
fit; it does not prescribe every future carousel as eight cards or a scorecard.
An Instagram photo carousel, TikTok photo post, LinkedIn PDF and video adaptation
each need a separately verified delivery route. Never silently convert between
them or claim a document post from an image upload.

For single images, choose an accepted visual that is useful in isolation and
give it a native context wrapper. For Shorts, request the approved video edition
and confirm exact matching long-video continuation. Text editions need native
copy and sourced claims. Article work retains the separate body/paid-offer gates.

Notes and memes are the Canva lane (`canva.md`, Krish's ruling of 27 October
2026): their `production_owner` is `growth-canva`, not content-engine. A Note
is native Notes copy with at most one approved image. A meme is one approved
export per channel, built from Krish's idea and shown to him before it queues;
on YouTube it must be a real video. Preflight refuses a package whose
production owner differs from its format's owner.

The exact posting package binds account, context, caption, source, ordered asset
hashes/alt text, format, tool and proposed time. Every meaning-changing revision
needs the corresponding approval; a native draft ID alone identifies no approval.
Local schema validation cannot certify taste or grant external action authority.

## Built to be sent (Krish, 28 October 2026)

Krish: "ensuring all the produced snackable content is likelier to be shared
for a specific reason", from one person to another in a "you will like this"
way, never by asking for the share. A format whose profile says
`"snackable": true` (meme, carousel, single image, short video, Story, Note)
needs a `share` block in its package, checked by `social preflight` against
`../share.json`:

| Field | What it holds |
|---|---|
| `sender`, `receiver` | Specific people by role or relationship, named before any clause or place: "a head of marketing" to "her CEO", never "your network", "a colleague", "a friend at work" or "someone you know" |
| `job` | One of `in_the_know`, `helps_them`, `so_us`, `settles_it`, `warns_them`, `laugh_or_awe` |
| `dm_line` | The exact message the sender would type, in plain words, under 120 characters, never a generic call to action |
| `moment` | The everyday situation that brings the post to mind |
| `standalone` | True only if it works with no context; a snackable post must |

Each snackable profile names its share mechanic in its delivery checks. For
Growth's Canva lane (meme, Note) the mechanic is Growth's own to build. For
content-engine's formats (carousel, single image, short video, Story) it is a
proposed hook in Growth's distribution brief, beside the share block; it
becomes a production standard only when content-engine adopts it through its
own route (content-engine `docs/GROWTH-HANDOFF.md`).

| Format | What would make it worth sending |
|---|---|
| Meme | Recognition of one specific situation the receiver is in |
| Note | One line a reader would quote or forward to a named person |
| News carousel (proposed) | One quotable, sourced number or fact a person will repeat |
| Advice (proposed) | One move someone forwards to a named colleague, complete on its own |
| Short or clip (proposed) | One moment that lands with no context in the first seconds |

Before Krish sees a snackable package: the copy carries no generic share call
to action (the patterns in `../share.json`; preflight refuses "share this",
"tag a friend", "send this to someone who" and the rest where they open a
sentence, so a fact such as "banks tag them as high risk" stays), and a blind
reader (`crew/send-test/`) names the declared receiver and job.
`python growth.py social send-test PACKAGE.json --stage FOLDER` copies the
assets under blind names into a new folder with `request.json`, the only
things the reader is given; `--answer ANSWER.json` compares the reply, which
must carry the request's `request_sha256`, so an answer to an earlier revision
never counts. A mismatch goes back for revision with the reader's words; on
content-engine's artwork it goes back as creative feedback through the brief.
On a board or in a run spec's `forward_line`, `engine.share.share_line`
renders the block as one line (a snackable run slot carries the same `share`
block, `docs/RUN.md`). Whether share asks are refused beyond snackable posts
is Krish's decision (`share_cta_scope` in `../share.json`).

The jobs, mechanics and moments are house hypotheses until MYMU's own sends per
reach and saves per reach confirm them (lesson `share-rate-measure`). They lean
on published background, not a measured MYMU result: Berger and Milkman (2012),
"What Makes Online Content Viral?", Journal of Marketing Research 49(2), found
that New York Times articles evoking high-arousal emotions such as awe, anger
or anxiety made the most-emailed list more often, and sadness less, alongside
practical usefulness; Berger's Contagious: Why Things Catch On names six
drivers of sharing (social currency, triggers, emotion, public, practical value
and stories). The `warns_them` job stays calm and sourced: no fear framing
(`knowledge/COPY-DOCTRINE.md`, override 7).
