#!/usr/bin/env python3
"""PreToolUse hook: refuse a Buffer create_post or edit_post on this engine's channels that carries no subscribe
route (engine/subscribe_gate.py; Ruling, Krish, 2026-11-12), and any on a channel another engine owns, Krish's
personal LinkedIn (Ruling, Krish, 2026-11-13). An edit names only its post, so it goes by the channel the post
was read on (engine/post_channels.py, recorded by .claude/hooks/buffer-post-channels.py); an edit of a post not
yet read is refused until it is read. Silent when the call passes; a call it cannot check is refused (exit 2), so
it fails closed."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get('CLAUDE_PROJECT_DIR') or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT))


def main():
    # Fails closed: a call the gate cannot read, or a gate that breaks, is refused (exit 2 blocks the tool call
    # and shows the reason). Before 13 November an unreadable call passed, so a broken gate let posts through.
    try:
        call = json.load(sys.stdin)
        if not isinstance(call, dict):
            raise ValueError('the hook input is not an object')
        from engine import subscribe_gate
        name, tool_input = call.get('tool_name'), call.get('tool_input')
        if not isinstance(name, str):
            raise ValueError('the hook input names no tool')
        if name.endswith(subscribe_gate.TOOLS) and tool_input is not None and not isinstance(tool_input, dict):
            raise ValueError('the tool input is not an object')
        problems = subscribe_gate.errors(name, tool_input or {}, root=ROOT)
    except Exception as e:  # noqa: BLE001 - any failure to check is a refusal, never a pass
        print('subscribe gate could not check this call, so it is refused: ' + type(e).__name__, file=sys.stderr)
        return 2
    if problems:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': ' | '.join(problems)}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
