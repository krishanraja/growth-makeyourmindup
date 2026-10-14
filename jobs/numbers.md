# Job: numbers (every day)

Kind `numbers`. Engine 7 in `PLAYBOOK.md`. No drafts: one row per platform in
`numbers`.

1. Using the signed-in browser (`BROWSER.md`), read each dashboard for
   **yesterday** (New York) and write down only what it shows:

   | Platform | `followers` | `new_this_week` | `reach` | `visits` | `new_free` | `new_paid` | `unsubscribes` | `top_source` |
   |---|---|---|---|---|---|---|---|---|
   | Substack | total subscribers | yes | | post views | yes | yes | yes | biggest source of new subscribers |
   | YouTube | subscribers | yes | views | | | | | top video by subscribers gained |
   | Instagram | followers | yes | accounts reached | profile visits | | | | top Reel |
   | TikTok | followers | yes | views | profile views | | | | top post |
   | X | followers | yes | impressions | profile visits | | | | top post |
   | LinkedIn | followers | yes | impressions | profile views | | | | top post |
   | Spotify | followers | yes | plays | | | | | |

   Leave a field out, or `followers: null`, when the page doesn't show it.
   `note` says where you read it, and anything odd. If no signed-in browser
   is available, use the public pages and say so in `note`:
   - home.makeyourmindup.ai
   - youtube.com/@makeyourmind-up
   - instagram.com/makeyourmind.up
   - tiktok.com/@therealkrisho
   - x.com/therealkrisho
   - linkedin.com/in/krish-raja
2. Substack's subscribers by source are the most important numbers: put the
   biggest three sources and their counts in Substack's `note`.
3. Compare with yesterday's pack (`python3 growth.py read --days 2 --kind
   numbers`). Headline: the one change that matters, in plain words, for
   example "Substack +18 yesterday, 11 from Recommendations; YouTube +3". No
   percentages. Post.
