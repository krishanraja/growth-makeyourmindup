#!/usr/bin/env python3
"""PostToolUse hook: after a Buffer get_post, list_posts or create_post, record each post id with its channel id
in the ignored .scratch/buffer/post-channels.json (engine/post_channels.py), so the subscribe gate knows which
channel an edit_post, which names only its post, lands on (Ruling, Krish, 2026-11-13: Krish's personal LinkedIn
is growth-mindmake's). Ids only, never words. Silent, and never blocks a call."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get('CLAUDE_PROJECT_DIR') or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT))


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(call, dict):
        return 0
    from engine import post_channels
    try:
        post_channels.record(ROOT, post_channels.from_call(call.get('tool_name', ''), call.get('tool_input') or {},
                                                           call.get('tool_response')))
    except OSError:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
