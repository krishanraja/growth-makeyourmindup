# Post-Production Corpus: 15-Minute One-Shot YouTube Episode

## Executive summary

This corpus treats a **one-shot episode** as a 15-minute, single-camera continuous performance that should feel uninterrupted, even if post-production uses a few invisible repairs. The best workflow is not “add more edits”; it is **protect the performance, repair distractions, improve comprehension, package the promise, and learn from retention data**.

The recommended order is:

1. Secure and verify the source media.
2. Watch once without editing and mark only genuine problems.
3. Build a transcript-led content map.
4. Make the smallest structural edit that improves the promise.
5. Repair dialogue before adding music or effects.
6. Correct colour before applying a creative look.
7. Add restrained visual support without destroying the one-shot identity.
8. Create captions, chapters, title, thumbnail and end-screen assets.
9. Export a high-quality master and YouTube delivery file.
10. Run technical, editorial, accessibility, rights and platform QC.
11. Review retention after publication and feed the findings into the next episode.

YouTube explicitly recommends that the opening deliver quickly on the promise made by the title and thumbnail, while its retention tools identify intros, top moments, spikes and dips. For this format, the edit should therefore optimise the first 30 seconds, protect the strongest later moments from being buried, and remove only pauses, repetitions or faults that materially weaken attention.[^1][^2]

## Scope and assumptions

The corpus assumes:

- A solo creator or small team.
- One primary 16:9 camera angle.
- A spoken-word episode: commentary, essay, tutorial, interview response or executive briefing.
- Approximately 15 minutes after editing.
- A “natural authority” style rather than a highly cut, effects-heavy creator aesthetic.
- Editing in Premiere Pro, DaVinci Resolve or an equivalent nonlinear editor.
- Delivery in SDR/Rec.709 unless the footage was intentionally captured and managed as HDR.

There are two valid editorial modes:

| Mode | Definition | Permitted interventions | Main risk |
|---|---|---|---|
| Strict one-shot | The episode remains visibly continuous | Audio repair, colour, graphics, captions, subtle stabilisation, no visible time compression | Slow passages remain slow |
| One-shot aesthetic | The episode feels continuous but permits concealed repairs | All strict-mode work plus hidden cuts, reframes, brief inserts and masked transitions | Too many interventions destroy authenticity |

The **one-shot aesthetic** is the practical default. The governing rule is: *every intervention must solve a named viewer problem*. If an effect cannot be tied to clarity, pacing, credibility, accessibility or conversion, omit it.

## Evidence hierarchy

Use the source base in this order:

1. **Platform rules and specifications:** YouTube Help and official YouTube guidance.
2. **Tool documentation:** Adobe or Blackmagic documentation for specific workflows.
3. **Standards bodies:** EBU/ITU-derived loudness and preservation guidance.
4. **Accessibility authorities:** platform guidance and recognised accessibility organisations.
5. **Practitioner guidance:** useful for starting points, never treated as an immutable platform rule.

A crucial distinction is between **YouTube requirements** and **working targets**. For example, YouTube publishes upload encoding recommendations, but it does not publish a universal creative rule stating that every spoken-word video must be mastered to exactly -14 LUFS. Treat -14 LUFS integrated and -1 dBTP as pragmatic web-video QC targets rather than hard YouTube submission requirements; preserve natural dynamics and verify the final file with a loudness meter.[^3][^4][^5]

## Editorial principles

### Preserve the contract

The title and thumbnail establish a promise; the opening must confirm that promise immediately. YouTube advises creators to keep intros concise, get directly to value and use audience retention to evaluate viewer response.[^2]

For a 15-minute episode, the opening should normally contain:

- The problem or tension.
- The specific payoff.
- A reason to trust the speaker.
- A clean transition into the substance.

Do not begin with a long ident, biography, housekeeping sequence or generic welcome unless the format already has a loyal returning audience. A one-shot performance gains authority from presence, but presence is not permission to delay the point.

### Edit by exception

On the first pass, mark only:

- Factual errors.
- Long searches for words.
- Repeated arguments.
- Distracting coughs, bumps or interruptions.
- Dead air that changes the energy rather than creating useful emphasis.
- Statements that create legal, rights, disclosure or reputational risk.
- Moments where the argument loses its logical thread.

Do not automatically remove every breath, pause or filler word. Human cadence is part of the value proposition of a one-shot format. Transcript-based editing can speed up search, rough cutting, pause removal and caption creation, but the transcript should guide judgement rather than replace listening.[^6][^7][^8]

### Audio outranks image

For a talking-head episode, intelligibility failure is usually more damaging than modest visual imperfection. Repair dialogue before choosing music, designing graphics or applying a look. Adobe’s official workflow supports dialogue classification, noise and reverb reduction, speech enhancement, loudness matching and music ducking; it also advises reviewing repair intensity so cleaned speech remains natural.[^9][^10][^11]

### Continuity beats stimulation

One-shot video should not imitate a hyperactive multi-camera edit. Use visual changes as punctuation:

- A subtle digital push-in for a pivotal claim.
- A full-screen quotation or diagram when the viewer must inspect information.
- A lower third for identity or terminology.
- A chapter card at a genuine conceptual transition.
- A brief cutaway only when seeing the thing is more useful than watching the speaker describe it.

Avoid constant zooms, meme inserts, animated subtitles, stock footage and sound effects. They transfer attention from the argument to the edit and weaken the format’s distinguishing signal: sustained competence in real time.

## Reference structure

A useful 15-minute editorial map is:

| Time | Function | Post-production treatment |
|---|---|---|
| 00:00–00:20 | Cold open and promise | Tightest wording; no ident before value; optional subtle push-in |
| 00:20–01:15 | Context and stakes | Add one orienting title or key phrase if needed |
| 01:15–04:30 | First argument or framework | Minimal intervention; first chapter boundary around the conceptual shift |
| 04:30–08:00 | Evidence, example or demonstration | Use supporting graphic only where it reduces explanation time |
| 08:00–11:30 | Complication, objection or second-order effect | Preserve contrast in delivery; consider a restrained reframe |
| 11:30–14:20 | Resolution and practical implications | Remove repetition; bring the strongest actionable material forward |
| 14:20–15:00 | Final takeaway and next-view bridge | Close the content loop, then make one specific call to action; reserve end-screen space |

This is a diagnostic template, not a mandatory beat sheet. The final duration should serve the idea; do not stretch a 10-minute argument to 15 minutes or crush a coherent 18-minute explanation merely to hit a target.

## End-to-end workflow

### Ingest and protection

1. Copy the source camera file and separately recorded audio, if any, into a dated project folder.
2. Preserve the original card structure until verification is complete.
3. Create at least one second copy on separate storage before editing.
4. Use descriptive filenames and a simple project manifest.
5. Retain the untouched source, project file, high-quality master, delivery file, caption file, thumbnail source and final thumbnail.

The Library of Congress recommends preserving the highest-quality video, using descriptive organisation and keeping copies in different locations. The US National Archives likewise distinguishes a high-quality preservation copy from a compressed access copy and notes that checksums help detect data change over time.[^12][^13]

Suggested structure:

```text
YYYY-MM-DD_episode-slug/
  01_source/
  02_audio/
  03_project/
  04_graphics/
  05_music-licenses/
  06_captions/
  07_exports/
  08_thumbnail/
  manifest.md
```

Suggested filenames:

```text
episode-slug_camA_001.ext
episode-slug_audio_main.wav
episode-slug_edit_v001.ext
episode-slug_master_v005.ext
episode-slug_youtube_v005.mp4
episode-slug_en-GB_v003.srt
```

### Sync and technical setup

- Confirm resolution, frame rate, colour space and audio sample rate before creating the timeline.
- Match the timeline frame rate to the recorded source; YouTube recommends uploading at the native recorded frame rate rather than resampling.[^14][^3]
- If separate audio exists, sync it using waveform or timecode, then verify lip sync at the beginning, middle and end.
- Set an SDR sequence to an appropriate Rec.709 workflow unless the source and delivery are intentionally HDR.
- Do not change the working colour space after grading begins; Adobe notes that colour adjustments are colour-space-specific and can appear different if the sequence working space changes.[^15]

### First watch

Watch the full take once at normal speed with no cutting. Record timecoded notes under five headings:

- **Story:** promise, argument, evidence, conclusion.
- **Performance:** energy, confidence, pace, distracting mannerisms.
- **Technical:** focus, exposure, colour, noise, hum, clipping, sync.
- **Risk:** factual uncertainty, names, claims, rights, privacy, disclosures.
- **Packaging:** strongest quote, thumbnail expression, chapter boundaries, next-video bridge.

This pass prevents local polishing from hiding a global problem. A beautifully graded episode with a weak opening remains a weak episode.

### Transcript map

Generate a transcript, but keep the original media as the authority. Premiere can transcribe on import and supports transcript-led rough cutting, search, pause removal and caption generation. DaVinci Resolve similarly supports word-level transcription, search, selection, timeline editing and SRT export.[^7][^16][^8]

Turn the transcript into a paper edit:

- Highlight the promise in yellow.
- Highlight essential claims in green.
- Mark repetition in grey.
- Mark claims requiring verification in red.
- Mark visual-support opportunities in blue.
- Mark the final next-step bridge in purple.

Then write a one-line function beside each paragraph. If two consecutive passages perform the same function, one may be redundant.

### Structural edit

Use the least invasive option that fixes the issue:

| Problem | First choice | Escalation |
|---|---|---|
| Long opening | Trim before first valuable sentence | Rebuild opening from a later strong line |
| Brief verbal stumble | Leave it if meaning is clear | Hide an audio edit under a held frame or subtle reframe |
| Repeated point | Remove the weaker version | Join with a motivated punch-in or brief graphic |
| Long dead pause | Shorten room tone naturally | Use optical-flow/morph tools only after visual inspection |
| Factual correction | Add precise on-screen correction | Re-record a pickup or replace the section |
| Distracting visual event | Crop/reframe | Use a brief insert or graphic cover |
| Weak ending | Trim recap and strengthen final takeaway | Record a short pickup/outro |

A hidden repair should preserve blinking, hand motion, body position, room tone and sentence rhythm. Never trade a minor verbal flaw for an uncanny face morph, broken hand movement or audible ambience jump.

### Pacing pass

Review in three ways:

1. **Audio only:** Does the argument work without pictures?
2. **Muted video:** Do body language and visual interventions feel calm and intentional?
3. **At normal speed from start to finish:** Does attention sag before each major transition?

For each proposed cut, record the reason: “removes duplicate premise,” “repairs error,” “shortens search for wording,” or “moves payoff earlier.” If the reason is merely “more pace,” inspect whether the real problem is weak structure rather than insufficient cutting.

### Dialogue repair

Use a conservative chain:

1. Clip gain or level matching.
2. Remove electrical hum, clicks and obvious faults.
3. Light noise reduction or speech enhancement.
4. Corrective EQ.
5. Gentle compression or dialogue levelling.
6. Manual automation for words or phrases that remain uneven.
7. Limiter on the dialogue bus or final mix.
8. Integrated loudness and true-peak measurement on the complete programme.

Adobe advises starting with default noise and reverb repair, listening, then balancing intensity against natural sound; Enhance Speech includes a mix control for blending processed and original dialogue.[^11][^9]

Practical targets for a web-first spoken-word master:

- Dialogue consistently intelligible on laptop speakers and a phone.
- No audible clipping, pumping, metallic denoising or aggressive gating.
- Approximately -14 to -16 LUFS integrated as a pragmatic starting range.
- True peak at or below approximately -1 dBTP.
- Music clearly subordinate to speech and manually checked at every entry and exit.

These are production targets, not official YouTube acceptance rules. EBU R128 defines programme loudness and loudness range but uses a broadcast target of -23 LUFS, illustrating why standards must be applied to their intended distribution context rather than copied blindly.[^4][^17]

Capture 10–20 seconds of clean room tone during production whenever possible. In post, use it to bridge shortened pauses and concealed audio edits; generated silence often exposes the cut because the room suddenly disappears.

### Music and rights

A one-shot intellectual or commentary format often needs no continuous music. If used:

- Reserve music for the cold open, chapter transitions or outro.
- Duck it under speech rather than competing for attention.
- Avoid changing tracks merely to manufacture energy.
- Keep a copy of the licence, invoice, attribution requirement and download date in the project folder.

YouTube states that Audio Library music and sound effects are copyright-safe on YouTube, while some Creative Commons tracks require attribution. It also warns that music merely labelled “free” elsewhere can still trigger Content ID; creators should verify licence terms for longer videos.[^18][^19]

### Colour correction

Perform technical correction before a creative look:

1. Confirm source colour-space interpretation.
2. Set white balance.
3. Correct exposure and contrast using scopes, not only the computer display.
4. Protect skin tone and highlight detail.
5. Fix local issues with masks only where necessary.
6. Apply a restrained creative look.
7. Recheck skin, black level, highlights and graphics.

Adobe’s colour workflow similarly moves from basic correction through curves and colour wheels, with scopes used to analyse luminance and chroma. LUTs are colour-space-dependent; a Rec.709-designed look can behave differently in another working space.[^20][^21][^22]

For a single uninterrupted angle, prioritise stability over drama. A slowly changing exposure or white balance is more distracting than a slightly imperfect but consistent image. If correction must be keyframed, use long, smooth transitions that are invisible at normal playback.

### Reframing and stabilisation

Digital punch-ins are useful but should remain motivated. A practical visual grammar is:

- Base frame: normal argument.
- Mild push-in: key claim or emotional escalation.
- Return to base: release or transition.
- Full-screen graphic: evidence the viewer must read.

Do not alternate framings at mechanically regular intervals. When delivering 1080p from 4K source, modest crops can preserve output resolution; when source and output are both 1080p, crops trade away detail and should be subtler.

Use stabilisation only if camera movement distracts. Inspect edges, facial geometry, hand movement and background lines after stabilisation; warping is often worse than mild original movement.

### Graphics and evidence

Create an evidence ledger for every on-screen factual asset:

| Asset ID | Timecode | Claim or visual | Source URL/file | Rights status | On-screen credit | Checked by |
|---|---|---|---|---|---|---|
| G01 | 05:14 | Quoted statistic | Primary source | Cleared/fair dealing assessment | Short source label | Initials/date |

Graphics should answer one of four viewer needs:

- “Who or what is this?” — lower third.
- “What should be remembered?” — key phrase.
- “Can this claim be inspected?” — chart, source or quotation.
- “Where are we?” — chapter card or progress marker.

Avoid full sentences in lower thirds. For a long quotation, pause the speaker visually, display only the necessary excerpt and add the source in the description. Do not use decorative charts or fabricated data.

### Captions

Generate captions from the corrected final sequence, then manually review them. YouTube warns that automatic captions can misrepresent speech because of accents, pronunciation, dialects and background noise, and explicitly recommends review and correction.[^23]

Caption QA should check:

- Names, brands and technical vocabulary.
- Punctuation and sentence boundaries.
- Timing at edit points.
- Speaker identification where needed.
- Meaningful non-speech information such as `[music]` or `[laughter]`.
- No collision with important graphics.
- No orphaned one-word caption flashes.

YouTube supports uploaded, auto-synchronised and manually entered captions. Its own guidance includes adding meaningful sound cues for viewers who cannot hear them.[^24][^25]

Publish a separate caption track rather than relying only on burned-in captions. Burned-in emphasis may be added selectively, but it should not replace an editable, searchable and user-configurable caption file.

### Chapters

Add chapters when the episode contains genuine conceptual sections. YouTube requires the first timestamp to be `00:00`, at least three timestamps in ascending order and a minimum chapter duration of 10 seconds.[^26]

Example:

```text
00:00 The promise
00:42 Why the problem persists
03:18 The three-part framework
07:06 A real example
10:24 Where the framework breaks
13:12 What to do next
```

Write chapter labels as useful destinations, not vague labels such as “Part 2.” Chapters should help a returning viewer locate an idea while still making the full episode coherent.

### End screen

Reserve the final 15–20 seconds for a clean next-view bridge. YouTube permits end screens in the final 5–20 seconds and up to four elements on a standard 16:9 video; it recommends planning that space during editing and choosing elements relevant to the current video.[^27]

Use one primary next action:

- “If this helped, watch **[specific related episode]** next.”

Keep the presenter or background composition clear where the chosen video tile and subscribe element will appear. Do not stack a verbal subscribe request, newsletter request, comment request, product pitch and unrelated playlist into the same closing moment.

## Packaging workflow

### Title

Write title candidates before the final edit so the opening can fulfil the promise precisely. YouTube recommends accurate, succinct titles with important words near the beginning; branding and episode numbers belong later.[^28]

Develop three title modes:

- **Searchable:** names the problem and outcome.
- **Intriguing:** creates a credible information gap.
- **Hybrid:** clear subject plus a distinctive consequence.

Template examples:

```text
How to [Outcome] Without [Common Cost]
Why [Common Practice] Fails — and What Works Instead
The [Number]-Part System for [Outcome]
[Topic]: What Changes When [New Condition]
```

Avoid a title that promises a list, reveal or transformation the one-shot episode does not actually provide.

### Thumbnail

Design the thumbnail as the title’s visual complement, not a duplicate sentence. YouTube recommends a large, readable, uncluttered image and states that 90% of best-performing videos use custom thumbnails. Its current custom-thumbnail guidance recommends 1280 × 720, 16:9, JPG/GIF/PNG and less than 2 MB for videos.[^29][^30]

Create three variants:

- Face/emotion plus 2–4 word tension.
- Object, diagram or result plus minimal label.
- Clean editorial portrait with one strong visual contrast.

Check each at phone-feed size and in greyscale. If the central idea disappears when small, simplify it. YouTube Studio supports testing up to three title and thumbnail variants where the feature is available.[^31]

### Description

Use the first lines to explain the episode’s value, then add chapters, sources, disclosures, related links and credits. YouTube recommends unique descriptions, one or two main terms shared naturally with the title, and putting the most important information before “Show more.”[^32]

Template:

```text
[Two sentences stating the problem, audience and payoff.]

CHAPTERS
00:00 ...

SOURCES AND FURTHER READING
- [Source name]: [URL]

WATCH NEXT
- [Related episode]: [URL]

TOOLS / RESOURCES
- [Only items genuinely discussed]

DISCLOSURES
- Sponsorship, affiliate, AI, correction or music information as applicable.
```

Do not overinvest in tags. YouTube says title, thumbnail and description matter more for discovery, while tags mainly help with common misspellings.[^33]

## Export specification

For a normal SDR episode, use YouTube’s official upload guidance as the baseline:

| Setting | Recommended delivery |
|---|---|
| Container | MP4 with Fast Start / moov atom at front |
| Video codec | H.264 High Profile |
| Scan | Progressive |
| Rate control | Variable bitrate |
| Frame rate | Same as recorded source |
| Chroma | 4:2:0 |
| Colour | BT.709/Rec.709 for SDR |
| Audio | AAC-LC, stereo |
| Sample rate | 48 kHz |
| 1080p bitrate | 8 Mbps standard frame rate; 12 Mbps high frame rate |
| 1440p bitrate | 16 Mbps standard; 24 Mbps high frame rate |
| 2160p bitrate | 35–45 Mbps standard; 53–68 Mbps high frame rate |

These values come from YouTube’s recommended upload encoding settings. YouTube also advises uploading at the same frame rate used for recording and deinterlacing interlaced content before upload.[^3]

Create two outputs:

- **Master:** high-quality mezzanine file with minimal compression for archive and future derivatives.
- **YouTube delivery:** platform-ready H.264/AAC file using the settings above.

Do not upscale automatically merely because 4K delivery exists. Exporting at a higher resolution may have workflow benefits in some cases, but it does not recreate source detail. Choose the output resolution deliberately based on capture quality, graphics, processing time, archive needs and actual viewing value.

## Quality-control gates

### Editorial QC

- The first 20 seconds state or demonstrate the value.
- The title and thumbnail promise is fulfilled.
- Every section advances the argument.
- Repetition is intentional or removed.
- The strongest insight is not needlessly buried.
- The final takeaway lands before the call to action.
- One-shot authenticity remains intact.

### Audio QC

- Dialogue is intelligible on headphones, laptop and phone.
- No clipped consonants, pumping, metallic denoising or hard noise-gate tails.
- Room tone remains continuous across hidden edits.
- Music never masks speech.
- Integrated loudness and true peak have been measured on the final export.
- The final 20 seconds are not abruptly louder or quieter.

### Picture QC

- Focus is acceptable throughout.
- White balance and exposure remain stable.
- Skin looks plausible.
- No crushed blacks, clipped highlights or illegal-looking saturation.
- Reframes do not reveal soft focus or compression.
- Stabilisation introduces no warping.
- Graphics remain inside safe viewing areas and are readable on mobile.

### Caption QC

- Captions match the final export, not an earlier cut.
- Proper nouns and technical terms are correct.
- Timing is comfortable and does not anticipate key reveals.
- Relevant sound cues are included.
- Caption text does not obscure essential graphics.

### Rights and policy QC

- Music, images, clips, fonts and stock assets have documented rights.
- Sponsorship and affiliate disclosures are present where applicable.
- Realistic, meaningfully AI-altered content is disclosed in YouTube Studio where required.
- Factual corrections are on screen or in the description.
- Private information, unreleased products and confidential screens are removed.

YouTube requires disclosure where AI makes a real person appear to do or say something they did not, alters a real event or place, or generates a realistic scene that did not occur. Minor production assistance such as script ideation, captions, colour correction and clearly non-realistic material generally does not require the same disclosure.[^34][^35]

### Export QC

1. Watch the exported file from beginning to end; do not approve only from the editing timeline.
2. Check the first and last frame, sync, graphics, captions, audio channel mapping and end-screen space.
3. Scrub every concealed edit and transition frame by frame.
4. Compare file duration against the approved timeline.
5. Upload as unlisted or private.
6. Wait for HD processing and inspect the YouTube transcode on desktop and mobile.
7. Confirm chapters, captions, links, thumbnail, title and end-screen placement.
8. Only then schedule or publish.

## Analytics feedback loop

Audience retention data typically takes one to two days to process. YouTube defines:

- **Intro:** the percentage still watching after the first 30 seconds.
- **Top moments:** sections where few viewers leave.
- **Spikes:** sections rewatched or shared, though confusion can also cause rewatching.
- **Dips:** sections skipped or abandoned.[^1]

Use a simple post-publication review:

| Signal | Diagnostic question | Next-episode action |
|---|---|---|
| Early cliff | Did the opening delay or mismatch the promise? | Rewrite the first 20 seconds; remove ident or context |
| Dip at graphic | Was it unreadable, irrelevant or too long? | Simplify and shorten the visual |
| Dip at transition | Did the episode repeat or announce structure mechanically? | Enter the next idea directly |
| Spike at example | Was concrete evidence more valuable than abstraction? | Move an example earlier next time |
| Spike at confusing claim | Did viewers need to replay it? | Rewrite and visualise the explanation |
| Strong late top moment | Was the best material buried? | Bring that premise forward in the next episode |
| End-screen clicks weak | Was the next video irrelevant or the bridge vague? | Name one specific next benefit |

Compare each episode with the channel’s own recent videos of similar length rather than chasing a universal retention percentage. YouTube’s “typical retention” feature compares against the ten latest videos of similar length, making the channel’s own baseline the more useful operating benchmark.[^36][^37]

## Lean operating model

### Solo creator

A disciplined post-production allocation for a clean source might be:

| Stage | Indicative time |
|---|---:|
| Ingest, backup and project setup | 20–30 min |
| Full watch and notes | 20 min |
| Transcript and structural pass | 45–90 min |
| Dialogue repair and mix | 45–90 min |
| Colour and reframing | 30–60 min |
| Graphics, captions and chapters | 45–90 min |
| Packaging | 30–60 min |
| Export and full QC | 30–60 min plus render/upload |

The times are planning estimates, not researched industry benchmarks. Poor capture, many repairs, complex graphics or fact-heavy episodes can multiply them. The operational lesson is that post-production effort is dominated less by the nominal 15-minute runtime than by source quality, correction count and packaging complexity.

### Small team

Use explicit handoffs:

| Owner | Output |
|---|---|
| Producer | Approved promise, audience, claims and source ledger |
| Editor | Picture lock and edit decision notes |
| Audio lead/editor | Final dialogue mix and loudness report |
| Graphics | Approved titles, evidence cards and thumbnail variants |
| Reviewer | Timecoded correction list against exported file |
| Publisher | Metadata, captions, chapters, disclosures, end screen and scheduling |

Never start final captions, chapters or detailed graphics before picture lock unless the deadline justifies the rework.

## Reusable templates

### Edit decision log

```text
Episode:
Version:
Reviewer:
Date:

TIMECODE | CATEGORY | ISSUE | DECISION | OWNER | STATUS
00:00:00 | Structure | Promise arrives too late | Begin at 00:00:14 | Editor | Open
00:05:21 | Fact | Statistic needs primary source | Verify or remove | Producer | Open
00:09:42 | Audio | Chair noise masks word | Repair; re-record if needed | Editor | Open
```

### Picture-lock gate

```text
[ ] Promise approved
[ ] Factual claims verified
[ ] Structural cuts approved
[ ] Hidden edits visually and sonically clean
[ ] Duration approved
[ ] Graphic list frozen
[ ] No further dialogue changes expected
```

### Publish gate

```text
[ ] Final export watched end to end
[ ] HD YouTube transcode checked
[ ] Title and thumbnail match the opening
[ ] Description and source links checked
[ ] Chapters render correctly
[ ] Captions reviewed and published
[ ] End screen aligned with reserved composition
[ ] Rights and disclosures recorded
[ ] Video visibility and publish time correct
[ ] Analytics review date scheduled
```

### Retrospective

```text
What did the title and thumbnail promise?
Did the first 30 seconds fulfil it?
Where were the first material dip, strongest spike and best top moment?
Which moment should move earlier next time?
Which post-production intervention added the most value?
Which intervention consumed time without measurable benefit?
What capture change would eliminate the largest post-production problem?
```

## Annotated source corpus

### Platform and discovery

- **YouTube: Thumbnail & title tips** — Primary guidance on accuracy, brevity, readable composition and matching packaging to audience intent.[^30][^28]
- **YouTube: Tips for video descriptions** — Primary guidance on the first lines, unique descriptions, keywords, chapters and related links.[^32]
- **YouTube: Add tags** — Corrects the common overemphasis on tags; YouTube says they play a minimal role beyond issues such as misspellings.[^33]
- **YouTube: How search works** — Establishes that relevance considers the match among title, tags, description, video content and the query.[^38]
- **YouTube: Custom thumbnails** — Current image dimensions, format, aspect ratio and file-size recommendations.[^29]
- **YouTube: A/B test titles and thumbnails** — Operational reference for testing up to three variants where available.[^31]

### Retention and structure

- **YouTube: Measure key moments for audience retention** — Primary definitions for intro, top moments, spikes and dips, plus guidance on moving compelling material earlier.[^1]
- **YouTube: Recommendation-system performance guidance** — Connects initial promise fulfilment, ongoing value, storytelling and retention analysis.[^2]
- **YouTube: Content analytics tips** — Useful explanation of 30-second intro measurement and channel-relative typical retention.[^36]

### Chapters and conversion

- **YouTube: Video chapters** — Authoritative formatting requirements and eligibility limitations.[^26]
- **YouTube: End screens** — Timing, element limits, eligibility, layout considerations and analytics.[^27]

### Encoding and delivery

- **YouTube: Recommended upload encoding settings** — Primary technical baseline for MP4, H.264, progressive scan, frame rate, bitrate, AAC and Rec.709.[^3]
- **YouTube: Video and audio formatting specifications** — Additional guidance on native frame rate, avoiding letterboxing and uploading the highest quality available.[^14]
- **YouTube: HDR uploads** — Use only for a genuinely managed HDR workflow; includes supported containers, codecs and bit depths.[^39]

### Captions and accessibility

- **YouTube: Automatic captioning** — Explains limitations of machine captions and the requirement for human review.[^23]
- **YouTube: Add subtitles and captions** — Authoritative workflow for upload, auto-sync and manual entry, including meaningful sound labels.[^24]
- **YouTube: Edit or remove captions** — Primary reference for correcting text and timings or downloading caption files.[^25]
- **RNID: YouTube captions** — Practical accessibility-oriented instructions for files, timing and non-speech sound information.[^40]

### Editing and audio

- **Adobe: Text-Based Editing** — Official workflow for transcription-led search, rough cuts, correction and captions.[^8][^6]
- **Adobe: Enhance Speech** — Official dialogue-enhancement workflow with a mix control to avoid overprocessing.[^9]
- **Adobe: Reduce noise and reverb** — Practical guidance on starting conservatively and reviewing the result.[^11]
- **Adobe: Audio editing** — Overview of dialogue restoration, loudness matching and music ducking.[^10]
- **DaVinci Resolve transcription documentation** — Detailed reference for transcription, word-level navigation, timeline editing and SRT export.[^16]
- **EBU R128** — Standards reference for programme loudness, loudness range and the distinction between broadcast normalisation and web delivery.[^17][^4]

### Colour

- **Adobe: Colour correction workflow** — Ordered reference for basic correction, LUTs, curves, wheels and shot matching.[^20]
- **Adobe: Colour workflow overview** — Explains scopes, white balance, exposure, saturation and the sequence of correction operations.[^21]
- **Adobe: Colour management and Lumetri** — Important warning that LUTs and corrections are colour-space-specific.[^15]

### Rights and disclosure

- **YouTube: Audio Library** — Primary source on YouTube-safe music, monetisation and attribution requirements.[^18]
- **YouTube: Safe music** — Primary warning that third-party “free” labels do not prevent Content ID issues.[^19]
- **YouTube: Disclosing GenAI content** — Current disclosure triggers and Studio workflow for realistic synthetic or altered material.[^34]
- **YouTube: AI disclosure announcement** — Clarifies that production assistance, captions and minor aesthetic edits generally do not require disclosure.[^35]
- **YouTube: Advertiser-friendly content** — Review if profanity, graphic topics or other sensitive material may affect monetisation.[^41]

### Preservation

- **Library of Congress: Keeping Personal Digital Video** — Practical principles for highest-quality preservation, descriptive organisation and geographically separated copies.[^12]
- **US National Archives: Video guidance** — Useful distinction between preservation and access copies, plus backup and checksum guidance.[^13]

## Decision rules

Use these rules when time is limited:

1. **Fix sound before image.**
2. **Fix the opening before the middle.**
3. **Remove repetition before adding visual stimulation.**
4. **Use a pickup before an uncanny repair.**
5. **Use one clear graphic before three decorative graphics.**
6. **Verify every factual overlay.**
7. **Export a master before making platform derivatives.**
8. **Review the actual YouTube transcode before publication.**
9. **Treat title, thumbnail and opening as one system.**
10. **Use retention evidence to change the next episode, not to mutilate the current one after the fact.**

The signature of excellent one-shot post-production is that the viewer notices the thought, not the repair.

---

## References

1. [Measure key moments for audience retention - Computer ...](https://support.google.com/youtube/answer/9314415) - The key moments for audience retention report explains how well different moments of your video held...

2. [Understand your content performance for YouTube's ... - Google Help](https://support.google.com/youtube/answer/16559650?hl=en) - Use Analytics to measure audience retention at key moments and understand how your audience reacts.

3. [YouTube recommended upload encoding settings](https://support.google.com/youtube/answer/1722171?hl=en-GB) - Below are recommended upload encoding settings for your videos on YouTube. Container: MP4 No Edit Li...

4. [[PDF] EBU R 128](https://tech.ebu.ch/docs/events/ibc10/presentations/ebu_ibc10_r128.pdf) - (LRA; see point 4) and the Target Level: -23 LUFS (Loudness Units referenced to Full Scale; see also...

5. [Loudness Analyzer & Normalizer - EditingTools.io](https://editingtools.io/loudness/) - In Europe, EBU R128 has a permitted tolerance of ±1 LU which means that a deviation of up to 1 LUFS ...

6. [helpx.adobe.com › premiere › desktopEdit transcripts with Text-Based Editing in Premiere | Premiere](https://helpx.adobe.com/premiere/desktop/edit-projects/edit-video-using-text-based-editing/edit-transcripts-using-text-based-editing.html) - After transcribing the source clip using the Text panel, select the icon and then Export > Export to...

7. [Transcribe video to text with AI - Adobe](https://www.adobe.com/products/premiere/speech-to-text.html) - You can then transcribe audio from your video clips or import an existing transcript file.

8. [Transcribe videos using Text-Based Editing in Premiere](https://helpx.adobe.com/premiere/desktop/edit-projects/edit-video-using-text-based-editing/transcribe-video.html) - Under the Import settings panel in the upper right corner, enable Automatic transcription and set th...

9. [Enhance speech in Premiere](https://helpx.adobe.com/premiere/desktop/add-audio-effects/adjust-volume-and-levels/enhance-speech.html) - Select an audio clip containing dialogue on the timeline.
Open the Essential Sound panel and select ...

10. [Video Audio](https://www.adobe.com/products/premiere/edit-audio.html) - Yes, use our new AI-powered Enhance Speech tool to help remove background noise in dialogue, or try ...

11. [Reduce noise and reverb - Premiere - Adobe Help Center](https://helpx.adobe.com/ph_fil/premiere-pro/how-to/reduce-noise-and-reverberation.html) - To assign the Dialogue audio type, select clips in the current sequence and click the Dialogue optio...

12. [Video - Personal Archiving | Digital Preservation - Library ...](https://digitalpreservation.gov/personalarchiving/video) - - One copy can stay on your computer or laptop; put other copies on separate media such as DVDs, CDs...

13. [Video Guidance: Playback and Digitization of Materials](https://www.archives.gov/preservation/formats/video-playback-digitize.html) - Files may be delivered on hard drive, flash drive or optical disk; whichever method you select you s...

14. [Video and audio formatting specifications - YouTube Help](https://support.google.com/youtube/answer/4603579?hl=en-GB) - - **Video codec:** H.264
- **Audio codec:** AAC

15. [Color Management and Lumetri Color - Adobe Help Center](https://helpx.adobe.com/premiere/desktop/correct-color/set-up-color-management/lumetri-enhancements.html) - The adjustments you make using the Lumetri Color panel will still be color space specific, and adjus...

16. [Ch. 47 Text Based Editing - docs.imaster.org](https://docs.imaster.org/davinci-resolve-21-manual/part-6-edit/ch.-47-text-based-editing) - After a Transcribe command has been applied, DaVinci Resolve now knows the exact timecode position o...

17. [r128 - EBU](https://tech.ebu.ch/docs/r/r128v4_0.pdf) - that the Programme Loudness Level shall be normalised to a Target Level of 
−23.0 LUFS.

18. [Use music and sound effects from the Audio Library](https://support.google.com/youtube/answer/3376882?hl=en-GB) - In the Audio Library in YouTube Studio, you can find royalty-free production music and sound effects...

19. [Tips to find safe music - YouTube Help](https://support.google.com/youtube/answer/15577610?hl=en) - - “Safe” music is music that is **in the public domain** or music that **you have received permissio...

20. [Color correction workflow - Adobe Help Center](https://helpx.adobe.com/ae_ar/premiere/desktop/correct-color/color-correction-fundamentals/color-correction-workflow.html) - Adjust tone and color in the Basic Correction section of the Lumetri Color panel using sliders for w...

21. [Overview: Color grading workflows in Premiere Pro](https://helpx.adobe.com/my_en/premiere-pro/using/color-workflows.html) - Select Window > Workspace > Color, or choose Color from the workspace switcher.

22. [Color correction effects](https://helpx.adobe.com/hk_zh/premiere-pro/using/color-correction-adjustment.html) - Lumetri Color provides you professional-quality color grading and color correction tools that let yo...

23. [Use automatic captioning - YouTube Help](https://support.google.com/youtube/answer/6373554?hl=en-GB) - 3. Click the video that you want to add captions or subtitles to.

24. [Add subtitles and captions - YouTube Help](https://support.google.com/youtube/answer/2734796?hl=en-GB) - 3. Select the video that you'd like to edit.
...
5. Under 'Subtitles', click **Add**

25. [Edit or remove captions - YouTube Help](https://support.google.com/youtube/answer/2734705?hl=en) - 6. Click inside any line in the caption track panel and edit the text.

26. [Video chapters - YouTube Help](https://support.google.com/youtube/answer/9884579?hl=en-GB) - 4. Click **SHOW MORE** and under **Automatic chapters** select **'Allow automatic chapters'**.

27. [Add end screens to videos - YouTube Help](https://support.google.com/youtube/answer/6388789?hl=en-GB) - You can use them to promote other videos, encourage viewers to subscribe and more.

28. [Thumbnail & title tips - YouTube Help](https://support.google.com/youtube/answer/12340300?hl=en-GB) - Viewers may only see part of your title.
So aim to keep it short and put the most important words ne...

29. [Add video thumbnails - YouTube Help](https://support.google.com/youtube/answer/72431?hl=en-gb) - - Have a resolution of 1,280 x 720 (with a minimum width of 640 pixels)

30. [Thumbnail & title tips - YouTube Help](https://support.google.com/youtube/answer/12340300?hl=en) - Design thumbnails that stand out. Who is your video targeting? Content targeting your subscribers mi...

31. [A/B test titles and thumbnails - YouTube Help](https://support.google.com/youtube/answer/16391400?hl=en-GB) - If the resolution of any thumbnail is lower than 720p (1280 x 720), all experiment thumbnails will b...

32. [Tips for video descriptions - YouTube Help](https://support.google.com/youtube/answer/12948449?hl=en-GB) - - Identify **one or two main words** that describe your video and feature them prominently in both y...

33. [Add tags to your YouTube videos - Google Help](https://support.google.com/youtube/answer/146402?hl=en-GB) - Your video's title, thumbnail and description are more important pieces of metadata for your video's...

34. [Disclosing use of GenAI content - Android - YouTube Help](https://support.google.com/youtube/answer/14328491?hl=en) - We require creators to disclose AI-generated or altered content that seems realistic.

35. [How we're helping creators disclose altered or synthetic content](https://blog.youtube/news-and-events/disclosing-ai-generated-content/) - That’s why today, we're introducing a new tool in Creator Studio requiring creators to disclose to v...

36. [Content tab analytics tips - Video - YouTube Help](https://support.google.com/youtube/answer/12942217?hl=en&co=YOUTUBE._YTVideoType=video) - Top moments are moments in your video where almost no one left the video while watching.

37. [Understand your YouTube engagement - Computer](https://support.google.com/youtube/answer/9313698?hl=en-tw&co=GENIE.Platform=Desktop) - The key moments for audience retention report shows how well different moments of your video held vi...

38. [How YouTube search works](https://support.google.com/youtube/answer/16090438?hl=en) - To estimate relevance we look into many factors, such as how well the title, tags, description, and ...

39. [Upload high dynamic range (HDR) videos - YouTube Help](https://support.google.com/youtube/answer/7126552?hl=en-GB) - These codecs are recommended, as they support 10-bit encoding with HDR metadata and deliver high qua...

40. [How to use video captions on YouTube](https://rnid.org.uk/information-and-support/technology-and-products/social-media-captions/youtube/) - You can customise:
...
- Window colour and opacity
...
3. Select ‘Captions’

41. [Advertiser-friendly content guidelines - YouTube Help](https://support.google.com/youtube/answer/6162278?hl=en) - Content that contains profanity or vulgarity at the start or throughout the majority of the video m

