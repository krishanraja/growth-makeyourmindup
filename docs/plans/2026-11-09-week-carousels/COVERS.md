# Codex brief: the three cover scenes

Content-engine `docs/CAROUSEL-STANDARD.md`, "The cover card is a scene, not a slide": card 1 is a full-bleed picture of
one funny, specific scene that carries the story's idea at a glance. A generated cover shows the house robot or no robot
at all. Real people are left out. No words, letters or logos in the picture (one prop word at most). House tones: ink
shadows, with the piece's series colour as the light. Composition: the scene lives in the TOP HALF; the lower half is
dark, quiet, near-black green-ink (#0C1512), so a headline can sit over it. Nothing important below the middle.
Photographic, tactile, editorial still life; not a cartoon, not glossy 3D render, not a stock photo.

Make each with your image generation tool, portrait 4:5 (1080 x 1350 or larger at that ratio), and save as PNG:

1. `mon/devices/cover.png`. A smartphone standing upright alone on a small wooden auction block on an
   empty stage, a paper lot tag tied to it with string, one hard spotlight from above in warm butter-yellow (#FFD84D)
   light, a few speech-bubble shapes made of paper fallen on the floor around the block like confetti after the party.
   The phone screen is dark. Mood: the sale of what's left. Top half only; lower half fades to dark ink.
2. `wed/devices/cover.png` (the house robot). Use the two reference photos `kit/robot-standing.png` and
   `kit/robot-theatre.png` as the robot: the same hand-sewn cream felt robot with grey patches, blank dark visor, the
   unpicked seam and its three hanging threads. Do not invent a different robot. Scene: a small club stage seen from
   the side, a glamorous singer seen only as a silhouette from behind at the microphone in a lilac (#B7A6FF)
   spotlight; tucked under the stage lip, half hidden, the little felt robot is humming into its own tiny microphone.
   Funny and warm. Top half only; lower half fades to dark ink.
3. `fri/devices/cover.png`. A three-step corporate winners' podium on an office carpet under a coral
   (#FF6A4D) spotlight; on the top step stands a small grey toy rat, proud, with no tail; on the floor in front of the
   podium, a neat pile of loose cut-off toy rat tails like spent tickets. Deadpan, a little absurd, not gory. Top half
   only; lower half fades to dark ink.

Also write `covers.json`: for each cover, the prompt you used, the reference image paths (wed only), the model or tool
name and the output file's sha256. Never: touch any other file, use the network beyond your image tool, run git, publish.
