Status: Every Buffer post on the engine's pinned channels must carry the tagged subscribe route at U4 and U5 (Ruling, Krish, 2026-11-12). A PreToolUse hook on the Buffer connector's create_post and edit_post runs `engine/subscribe_gate.py` and refuses a post without it (`subscribe_route_missing`), so hand-run session drafts are held to the same rule as release and preflight. Tests: `tests/test_subscribe_gate.py`.
Next: Align each channel's profile link to the tagged subscribe page (docs/CHANNEL-AUDIT.md subscription-link alignment), once Krish approves that outward change.
Changed: 58 posts went out through Buffer from 2 to 11 November with no subscribe ask, because hand-run drafts skipped preflight; the gate now sits on the path they took.
North Star check (2026-11-12): holds.
