# Card: Send-Test Reader (blind, new)

Owns the blind send test for every snackable package (meme, carousel, single image, short video, Story, Note) before Krish sees it. It names the miss; it never writes the fix. The prompt and the answer shape are data in social/share.json; the comparison is engine/share.py:compare_send_test.

| If | Then | Cite |
|---|---|---|
| A snackable package is ready for Krish | Run the blind send test first: `python growth.py social send-test PACKAGE.json` prints the only request the reader may see | R92, P8 |
| A reader is chosen | A fresh context with no session history: it sees only the media and the copy, never the share block, the source piece, the channel brief or an earlier answer | R92 |
| The reader answers | It says who it would send the post to and the exact words it would type, or that it would not send it, as JSON in the shape social/share.json sets | R92 |
| Its receiver and job match the declared share block | Pass: `social preflight --send-test ANSWER.json` drops the hold and the answer goes into the gate packet Krish sees | R92, P8 |
| The receiver or the job differs, or it would not send it | Back for revision with the reader's answer; the package does not reach Krish | R92 |
| A revision changes the media or the copy | A new fresh reader runs the test again; an earlier answer never carries over | R50, R92 |
| The reader offers better words or a better post | Leave them out of the packet; fixing is the author's job, not the judge's | R92 |
| A pass is recorded | It is review evidence, not proof the post will be sent; sends and saves per reach at the judge window decide | P8, R65 |
