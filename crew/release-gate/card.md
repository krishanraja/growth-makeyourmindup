# Card: Release Gate (code)

Owns every release. It checks; it does not judge creative.

| If | Then | Cite |
|---|---|---|
| A slot reaches release | Its bytes must equal the sha256 in the signed manifest line, or it is refused | R50, R49 |
| The decision digest does not match the slot | Refuse it | R12 |
| Krish amended the go-live | His version is what goes out, bound by its recomputed digest | R13 |
| A slot has no signed go-live | Refuse it; a plan or a session never releases | R12, R60 |
| A slot was already released | Refuse a second release | R12 |
| A slot is for LinkedIn | Save an unscheduled draft only; Krish clicks | R39, R62 |
| A slot is a Buffer draft save | saveToDraft with no due time | R03, R30 |
| A slot would pass its signed frequency (Notes per day as signed) | Hold the slot | P1, R60 |
| Buffer shows the post as scheduled | It is not live | R38 |
| A post is to be counted as live | Buffer sent plus the native URL read back for each destination | R38 |
| The outcome of a call is uncertain | Hold it; never retry blindly | R31 |
| A Story frame is released | One frame per post, deduplicated by media URL | R41, P6 |
| A slot carries a link sticker claim | Refuse the claim; it is never automatic | R42 |
| A slot breaks out at 24 hours | Pass it to P8 through the What-Works Analyst | P8 |
