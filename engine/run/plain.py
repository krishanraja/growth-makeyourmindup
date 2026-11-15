"""The plain-English lint for carousels and captions (Krish, 27 Oct 2026, rule R105).

His words on the last Make Your Mind Up carousel: "It wasn't plain English and
human and humble enough." Offline only; returns error codes, never rewrites.
"""
import argparse
import json
from pathlib import Path
import re

MAX_AVERAGE, MAX_SENTENCE = 16, 25
CAROUSEL_CARDS = (6, 8)
# A body card (every card between the cover and the close) carries one full plain sentence a stranger can follow on its
# own (Ruling, Krish, 2026-11-15: cards "assume that people have a working knowledge" and "use too few words"; one full
# plain sentence of up to 20 words). The floor of 8 words keeps a card from being a fragment; content-engine's
# docs/CAROUSEL-STANDARD.md owns the standard and its card check, and this is Growth's copy of the rule for its own
# decks, never a looser one.
BODY_WORDS = (8, 20)
# A card that opens on a joining word or a bare pointer leans on a card the reader may not have seen.
LEANS = re.compile(r"^\W*(?:so|but|and|then|or|because|also|this|that|these|those|it|they|he|she|here)\b", re.I)
# "12x" is shorthand a stranger has to decode: write "12 times".
MULTIPLIER = re.compile(r"\b\d+(?:\.\d+)?\s?[x×](?![A-Za-z0-9])")
END = re.compile(r"[.!?…][\"”’)\]]*\s*$")
JARGON = (('leverage', r'leverag(?:e|es|ed|ing)'), ('paradigm', r'paradigms?'), ('synergy', r'synerg(?:y|ies|istic)'),
          ('unlock', r'unlock(?:s|ed|ing)?'), ('game-changer', r'game[- ]changers?|game[- ]changing'),
          ('delve', r'delv(?:e|es|ed|ing)'), ('landscape', r'landscapes?'), ('robust', r'robust(?:ly|ness)?'),
          ('cutting-edge', r'cutting[- ]edge'), ('ecosystem', r'ecosystems?'), ("in today's", r"in today[’']s"))
JARGON_RE = [(name, re.compile(r'(?<![\w-])(?:' + pattern + r')(?![\w-])', re.I)) for name, pattern in JARGON]
EM_DASH = re.compile('—')
SENTENCE_END = re.compile(r'(?<=[.!?…])["”’)\]]*\s+|\n+')
WORD = re.compile(r"[A-Za-z0-9À-ɏ]+(?:['’.,-][A-Za-z0-9À-ɏ]+)*")
FIRST_PERSON = re.compile(r"\b(?:i|i'm|i've|i'd|i'll|me|my|we|we're|we've|we'd|us|our)\b", re.I)
HUMBLE = re.compile(r"\b(?:i|we)\s+(?:\w+\s+){0,2}(?:think|thought|believe|guess|suspect|might|may|could be wrong|"
                    r"was wrong|were wrong|got (?:it|this|that) wrong|learned|learnt|am learning|are learning|"
                    r"am not sure|are not sure|don't know|do not know|wonder)\b|\bthanks?\b|\bthank you\b|"
                    r"\bgrateful\b|\bnot sure\b|\bi was wrong\b|\bi'm not sure\b", re.I)


def finding(code, at, detail):
    return {'code': code, 'at': at, 'detail': detail}


def sentences(text):
    """Sentences of one block of copy; a line break also ends one (a card line is a sentence)."""
    return [s.strip() for s in SENTENCE_END.split(text.replace('\r\n', '\n')) if s and WORD.search(s)]


def words(sentence):
    return WORD.findall(sentence)


def humble(text):
    """A first-person, humble, human line: I or we with a hedge or a thanks, in one sentence."""
    return any(FIRST_PERSON.search(s) and HUMBLE.search(s) for s in sentences(text))


def lint_text(text, at='$'):
    """Error codes for one caption or card: sentence length, jargon, em dashes, stacked fragments."""
    out = []
    parts = sentences(text)
    lengths = [len(words(s)) for s in parts]
    for i, (sentence, n) in enumerate(zip(parts, lengths)):
        if n > MAX_SENTENCE:
            out.append(finding('sentence_too_long', at, '%d words: %s' % (n, sentence[:60])))
    if lengths and sum(lengths) / len(lengths) > MAX_AVERAGE:
        out.append(finding('average_too_long', at, 'average %.1f words a sentence' % (sum(lengths) / len(lengths))))
    for name, pattern in JARGON_RE:
        if pattern.search(text):
            out.append(finding('jargon', at, name))
    if EM_DASH.search(text):
        out.append(finding('em_dash', at, 'an em dash'))
    run = 0
    for n in lengths + [99]:
        if n <= 2:
            run += 1
            continue
        if run >= 2:
            out.append(finding('stacked_fragments', at, '%d short fragments in a row' % run))
        run = 0
    return out


def body_card_errors(card, at):
    """One body card: one full sentence of 8 to 20 words that stands on its own, with no shorthand."""
    out = []
    parts = sentences(card)
    n = sum(len(words(p)) for p in parts)
    if len(parts) != 1 or not END.search(card.strip()):
        out.append(finding('body_not_one_sentence', at, '%d sentences; a body card is one full sentence' % len(parts)))
    if n > BODY_WORDS[1]:
        out.append(finding('body_too_long', at, '%d words, at most %d' % (n, BODY_WORDS[1])))
    if n < BODY_WORDS[0]:
        out.append(finding('body_too_short', at, '%d words; say it in a full sentence a stranger can follow' % n))
    if LEANS.search(card):
        out.append(finding('body_leans_on_another_card', at, 'opens on a joining word or a pointer: ' + card[:40]))
    if MULTIPLIER.search(card):
        out.append(finding('multiplier_shorthand', at, 'write the multiple out, such as 12 times'))
    return out


def lint_carousel(cards, caption=''):
    """Every card and the caption pass lint_text; 6 to 8 cards; at least one humble, human line; every body card is
    one full plain sentence a stranger can follow (body_card_errors). The first card is the cover and the last the
    close, which keep their own forms."""
    out = []
    if not isinstance(cards, list) or not all(isinstance(c, str) for c in cards):
        return [finding('bad_input', '$.cards', 'cards is a list of strings')]
    if not CAROUSEL_CARDS[0] <= len(cards) <= CAROUSEL_CARDS[1]:
        out.append(finding('card_count', '$.cards', '%d cards, not %d to %d' % ((len(cards),) + CAROUSEL_CARDS)))
    for i, card in enumerate(cards):
        out += lint_text(card, '$.cards[%d]' % i)
        if 0 < i < len(cards) - 1:
            out += body_card_errors(card, '$.cards[%d]' % i)
    if caption:
        out += lint_text(caption, '$.caption')
    if not any(humble(text) for text in cards + [caption or '']):
        out.append(finding('no_humble_line', '$', 'no first-person line with a hedge or a thanks, such as "I think"'))
    return out


def codes(findings):
    return sorted({f['code'] for f in findings})


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run carousel|plain',
                                     description='Lint a carousel ({"cards": [...], "caption": "..."}) or a caption.')
    parser.add_argument('command', choices=['carousel', 'plain'])
    parser.add_argument('action', choices=['lint'])
    parser.add_argument('file')
    args = parser.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding='utf-8-sig')
        data = json.loads(text) if args.command == 'carousel' else text
    except (OSError, ValueError) as exc:
        print(json.dumps({'valid': False, 'findings': [finding('read', '$', str(exc))]}))
        return 1
    if args.command == 'carousel':
        found = (lint_carousel(data.get('cards'), data.get('caption') or '') if isinstance(data, dict)
                 else [finding('bad_input', '$', 'a carousel file is {"cards": [...], "caption": "..."}')])
    else:
        found = lint_text(data)
    print(json.dumps({'valid': not found, 'codes': codes(found), 'findings': found}, indent=1))
    return 0 if not found else 1
