"""Every post this engine makes or releases passes Control Center's one voice check.

Krish, 2026-11-09: "we need to make sure everything goes through the same
voice system. Absolutely everything." The rules are krish-voice's kill list in
ai-harness (and, for the publication, Make Your Mind Up's own canon on top),
applied by Control Center; this engine keeps no list of its own and asks
`POST voice-check` through its protocol client (engine/control_center.py).

Each Buffer channel speaks as one account (social/channels/*.json,
account_context): Krish's personal accounts take his social channels, the
publication's take its caption and Substack channels.
"""

from engine.control_center import ProtocolError

# This engine's channel -> the voice check's channel, by whose account it is.
CHANNEL = {
    # Krish's personal accounts
    'linkedin': 'linkedin', 'x': 'x', 'threads': 'threads', 'substack-notes': 'substack_note', 'tiktok': 'instagram',
    # The publication's accounts
    'instagram': 'caption', 'facebook': 'caption', 'youtube': 'caption', 'substack': 'substack',
}


def voice_reasons(cc, channel, words):
    """The hard voice rules these words break, as refusals. [] when they pass or carry no words. None when the
    check cannot give a verdict (Control Center without the route, or unreachable): the caller counts it, and Control
    Center's own gates still stand; a broken rule is never waved through on a verdict that was read."""
    if cc is None or not hasattr(cc, 'voice_check') or channel not in CHANNEL or not (words or '').strip():
        return []
    try:
        verdict = cc.voice_check(words, CHANNEL[channel])
    except ProtocolError:
        return None
    hard = verdict.get('hard') if isinstance(verdict.get('hard'), list) else []
    return sorted({h.get('message') for h in hard if isinstance(h, dict) and isinstance(h.get('message'), str)})
