#!/usr/bin/env python3
"""PreToolUse hook: refuse a Buffer create_post or edit_post on this engine's channels that carries no subscribe
route (engine/subscribe_gate.py; Ruling, Krish, 2026-11-12). Silent when the call passes."""
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
    from engine import subscribe_gate
    problems = subscribe_gate.errors(call.get('tool_name', ''), call.get('tool_input') or {}, root=ROOT)
    if problems:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': ' | '.join(problems)}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
