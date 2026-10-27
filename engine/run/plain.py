"""The plain-English lint for carousels and captions (Krish, 27 Oct 2026, rule R92).

His words on the last Make Your Mind Up carousel: "It wasn't plain English and
human and humble enough." Offline only; returns error codes, never rewrites.
"""
import argparse
import json
from pathlib import Path
import re

MAX_AVERAGE, MAX_SENTENCE = 16, 25
CAROUSEL_CARDS = (6, 8)
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


def lint_carousel(cards, caption=''):
    """Every card and the caption pass lint_text; 6 to 8 cards; at least one humble, human line."""
    out = []
    if not isinstance(cards, list) or not all(isinstance(c, str) for c in cards):
        return [finding('bad_input', '$.cards', 'cards is a list of strings')]
    if not CAROUSEL_CARDS[0] <= len(cards) <= CAROUSEL_CARDS[1]:
        out.append(finding('card_count', '$.cards', '%d cards, not %d to %d' % ((len(cards),) + CAROUSEL_CARDS)))
    for i, card in enumerate(cards):
        out += lint_text(card, '$.cards[%d]' % i)
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
