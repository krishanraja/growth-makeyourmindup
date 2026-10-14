# Job: the day's pack (Mon, Wed, Fri, after the piece is out)

Kind `daily`. Time for Krish: about 10 minutes.

1. `python3 growth.py pieces --days 2 --full`. Take today's
   article (not the "VIDEO:" post; that is the same story). If nothing is out
   today yet, post a pack with headline "No piece out yet today: nothing to
   draft" and no items, and stop.
2. Read the whole article. Find the one finding: the sentence a stranger
   would forward. Find the two or three most surprising named facts.
3. Draft, each one checked against the rules in `AGENTS.md`:
   - **LinkedIn post** (`platform: linkedin`, `target_url`: the article URL).
     Line one: first person and a specific moment or number, with the topic
     word in it (see `hooks.json` > linkedin). Then 5 to 9 short lines that
     give the finding and why it matters to someone who runs a business. End
     with one honest question. The article link goes at the end of the post.
     Under 1,300 characters.
   - **X thread** (`platform: x`). 4 to 6 posts, each under 280 characters,
     separated by a blank line. Post 1 must stand alone. The link goes in
     the last post.
   - **Search fixes** (`platform: seo`, `target_url`: the article URL), two
     items: (a) an SEO title of 51 to 60 characters that matches the
     article's title and puts the main search words first, and a meta
     description under 155 characters that states the finding; (b) a
     two-sentence answer to the question the article answers, for Krish to
     paste at the top, so AI answer engines can quote it.
   - **YouTube description** only if the "VIDEO:" post is out
     (`platform: youtube`): first two lines say what the video finds and
     carry the main search words; then the article link and
     hello@krishraja.com for business.
4. On the last Friday of the month, add a **calls record** draft
   (`platform: linkedin`): which of his dated calls (the predictions at the
   end of the mind.the.gap articles) fell due, and whether each came true,
   only if you can show it from a public source; otherwise "not due yet"
   and what is coming.
5. Headline: the day and what is in it, e.g. "Wednesday: LinkedIn post, X
   thread and 2 search fixes for the Muse piece". Check, then post.
