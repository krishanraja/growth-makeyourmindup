# The weekly edition: Krish's decisions, one at a time (25 Nov 2026)

Each question is put to Krish on its own, in this order, with a recommendation. His answer is recorded here in his own
words, with the date, and the design and the plan follow it. Nothing is built until the question it depends on is
answered. Background: [`DESIGN.md`](DESIGN.md).

| # | Question | Recommended | Depends on | His answer |
|---|---|---|---|---|
| 1 | Do the three pieces stop emailing, so the weekly edition is the one email a week? | Yes: the pieces publish to the web and the app only; the edition is the one email. First, a draft Video post's publish screen is read to confirm Substack offers the web-only box there (it is documented for posts and podcasts, not for Video posts). | | open |
| 2 | Can a reader still choose to get every piece by email? | Yes, as an opt-in, off for everyone by default (a Substack section), offered once in edition one and in email preferences. | 1, and Substack's documented sections | open |
| 3 | Which day and time does the edition send? | Saturday 08:00 New York (13:00 London). | 1 | open |
| 4 | What is the edition called? | "makeyourmindup weekly", with each subject line led by the week's strongest story. | 1 | open |
| 5 | Are the edition's sections right, with the job board replaced by "Pass it on" and an unsigned opener? | Yes, as in DESIGN.md section 2. | 1 | open |
| 6 | What does "Also this week" cover? | The creative beat only (content-engine `config/beat.json`), six to ten items, each checked against its primary source. | 5 | open |
| 7 | Where is the one press, and what happens after it? | Approve for send on the Saturday card in Control Center's Content tab; Codex on the worker then schedules the Substack post and reads it back. | 1 | open |
| 8 | What does every channel's subscribe line now promise? | "Get the week's pieces and the news that matters, in one email every Saturday:" then the tagged route (wording through the voice check). | 3, 4 | open |
| 9 | Which bars judge the edition after four sends? | Open rate above 35%; unsubscribes a week below the three-send baseline; clicks into the pieces at least what their own emails drew; one subscriber a week from forwards. | 1 | open |
| 10 | When does edition one send, and from which week? | Dry run now from the last fully published week (9 to 13 Nov); first live edition on the first Saturday after the plan's pull requests merge and the Library is approved, from that week's live pieces. | all above | open |
| 11 | Does the "still want this?" email to silent imported subscribers go, and when? | Yes, two weeks after edition one, to imported subscribers who opened nothing in 60 days; those who do not answer are removed a week later, on his yes for the removal. | 1, 10 | open |

Questions 1 to 10 make the design. Question 11 is a list decision that the design makes easier and does not need.
