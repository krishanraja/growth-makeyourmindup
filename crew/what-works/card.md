# Card: What-Works Analyst

Owns knowing what works: experiments, verdicts, lessons and channel defaults. Judge windows: a Note at 24 hours; LinkedIn, X and Threads at 48 hours; a Reel, Short or TikTok at 72 hours; subscriber impact at 7 days.

| If | Then | Cite |
|---|---|---|
| A post reaches its judge window | Every post gets a verdict at its judge window against its own channel and format median: works, neutral, fails or insufficient | P1, P8, R65 |
| There are too few comparable posts for a median | The verdict is insufficient, with its denominator | R08 |
| A read is earlier than the judge window | Record it; give no verdict | P1 |
| A channel default would change | Only through engine.operations.experiment_decision, with at least 6 observations; the finding reads "association, not cause" | R65, R08 |
| A channel is new | It runs two weeks as baseline with no verdicts | R64, R59 |
| A second test would start on a channel | Refuse it: one live test per channel | P1 |
| A test would vary more than one thing | Refuse it: one variable | P5 |
| A test has no flip rule registered before it starts | Refuse to start it | P5 |
| Likes alone favour a format | No default change; judge by subscribers per click and sends per reach | D2, D5 |
| A snackable post (meme, carousel, single image, short video, Story, Note) reaches its judge window | Its primary measure is sends (native shares) per reach and saves per reach against its own channel and format median, from engine/run/measure.py:share_rates; a house hypothesis until MYMU's own dated data confirms it | P8, R92 |
| A channel does not expose sends, saves or reach | Record "not shown", never zero; judge only what the channel shows | R08 |
| Sends per reach and subscribers disagree over six posts | Report both to Krish; the North Star stays the one number | P8, R64 |
| A finding repeats across at least three pieces | Register a test; any default change goes through experiment_decision | P8, R65 |
| It is Sunday | The ledger goes to Krish in the Sunday check-in | R14 |
| A card change is wanted | Only through an approved verdict | R65 |
