"""Krish's voice profile, read live from ai-harness for the maker's briefs.

Krish, 2026-10-31: "I want one clear voice profile that I can use as an anchor and add to over time",
then "yes do it all". The profile lives once, in ai-harness (skills/krish-voice/references/voice-profile.md);
this module reads it at run time and keeps no copy. The account rules (docs/ACCOUNT-VOICE.md, the maker's
VOICE) still decide who speaks; the profile only adds how Krish actually writes for that account.

read() returns {'personal': text, 'publication': text} or None when the profile cannot be read. A run
without it still makes drafts from the account rules alone and reports `voice_profile_unavailable`.
"""
import re
import urllib.request

URL = 'https://raw.githubusercontent.com/krishanraja/ai-harness/main/skills/krish-voice/references/voice-profile.md'
# Which branch of the profile's channel table speaks for each account voice.
BRANCH = {'personal': 'LinkedIn', 'publication': 'Make Your Mind Up articles'}
MAX_CHARS = 1600
# The profile describes his style; it never loosens the writer's own rules (no added fact, experience, name,
# emoji, link or hashtag, nothing that names him), which win wherever the two differ.
PRECEDENCE = (' This is style only: wherever it differs from the rules above, the rules win, so add no fact,'
              ' experience, name, emoji or link the idea and claim do not carry.')


def _section(md, heading):
    m = re.search(r'^## ' + re.escape(heading) + r'.*?$(.*?)(?=^## |\Z)', md, re.M | re.S)
    return m.group(1) if m else ''


def _habits(md):
    """The bold headline of each Core habit, without the quoted evidence after it."""
    return [h.strip() for h in re.findall(r'^\d+\.\s+\*\*(.+?)\*\*', _section(md, 'Core'), re.M)]


def _branch(md, name):
    """The 'what changes from the baseline' cell of one channel row."""
    for line in _section(md, 'Channels').splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3 and cells[0].strip('* ').startswith(name):
            return cells[2]
    return ''


def lines(md):
    """{'personal', 'publication'} brief lines from the profile's text, or None when it does not parse."""
    habits, out = _habits(md), {}
    for voice, name in BRANCH.items():
        branch = _branch(md, name)
        if not branch:
            return None
        text = 'From the voice profile, for this account: ' + branch
        if voice == 'personal' and habits:
            # The publication keeps his personal habits out (ruling 5), so only the personal account gets them.
            text += ' How he writes everywhere: ' + ' '.join(habits)
        out[voice] = text[:MAX_CHARS - len(PRECEDENCE)] + PRECEDENCE
    return out


def read(fetch_text=None):
    try:
        md = (fetch_text or _fetch)(URL)
    except Exception:  # noqa: BLE001 - any failure to read is the same answer: run on the account rules alone
        return None
    return lines(md) if isinstance(md, str) else None


def _fetch(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.read().decode('utf-8')
