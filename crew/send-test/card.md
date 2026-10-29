# Card: Send-Test Reader (blind, new)

Owns the blind send test for every snackable package (meme, carousel, single image, short video, Story, Note) and snackable run slot before Krish sees it. It names the miss; it never writes the fix. The prompt and the answer shape are data in social/share.json; the comparison is engine/share.py:compare_send_test.

| If | Then | Cite |
|---|---|---|
| A snackable package is ready for Krish | Stage the blind test first: `python growth.py social send-test PACKAGE.json --stage FOLDER` copies the media under blind names, with request.json, into a new folder; a run slot uses `growth.py run send-test SPEC SLOT` | R92, P8 |
| A reader is chosen | A fresh context with no session history, handed only that folder: the media and the copy, never the share block, a path to the package, the source piece, the channel brief or an earlier answer | R92 |
| The reader answers | It says who it would send the post to and the exact words it would type, or that it would not send it, as JSON in the shape social/share.json sets, with the request_sha256 it was given | R92 |
| Its receiver and job match the declared share block | Pass: `social preflight --send-test ANSWER.json` drops the hold and the answer goes into the gate packet Krish sees; for a run slot, `run send-test --answer ANSWER.json --record` writes review/SLOT.json with lens send-test | R92, P8 |
| The receiver or the job differs, or it would not send it | Back for revision with the reader's answer; the package does not reach Krish. On content-engine artwork it goes back as creative feedback | R92 |
| A revision changes the media or the copy | Its request_sha256 changes, so the earlier answer no longer counts and the hold returns; a new fresh reader runs the test | R50, R92 |
| The reader offers better words or a better post | Leave them out of the packet; fixing is the author's job, not the judge's | R92 |
| A pass is recorded | It is review evidence, not proof the post will be sent; sends and saves per reach at the judge window decide | P8, R65 |
