"""Prepaid credits, protocol 1.16.0 (docs/CONTROL-CENTER-BRIEF.md, "Prepaid credits").

Ruling (Krish, 2026-10-29): this engine may spend up to its share of each
prepaid pool placed on the publication (ElevenLabs, Apify) with no proposal.
The directive carries the share as `credits`; no block means unknown, so
nothing is spent. The GitHub runner holds no generator keys and spends
nothing: a session with the connectors spends it by docs/CREDITS.md and
records each spend through the Control Center connector (no Claude schedule
runs it: Krish, 29 Oct 2026, docs/LANES.md). This module
reads the block for the runner's report and guards any spend made in this
process, which then goes in the report's `credits_spent`.
"""

import re

MAX_SPENT = 40
POOL = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[a-z]{2,}', re.I)


class CreditRefused(ValueError):
    """A spend the share does not cover, or a block that is unknown."""


def credits_block(directive):
    """The `credits` block beside the directive or inside it, else None (unknown)."""
    if not isinstance(directive, dict):
        return None
    block = directive.get('credits')
    if not isinstance(block, dict) and isinstance(directive.get('directive'), dict):
        block = directive['directive'].get('credits')
    if not isinstance(block, dict) or not isinstance(block.get('pools'), list):
        return None
    pools = [p for p in block['pools'] if isinstance(p, dict) and isinstance(p.get('pool'), str)
             and isinstance(p.get('remaining_for_you'), (int, float))]
    return {'rule': block.get('rule'), 'pools': pools}


def _amount(value, unit):
    return '$%.2f' % value if unit == 'usd' else '{:,}'.format(int(round(value))) + ' ' + (unit or 'credits')


def credits_lines(block):
    """One activity line per pool; one line saying so when the block is unknown."""
    if block is None:
        return ['Prepaid credits: not in the directive, so unknown; nothing spent']
    if not block['pools']:
        return ['Prepaid credits: no pool is placed on the publication']
    return ['Prepaid credits: ' + str(p.get('tool') or p['pool']) + ' ' + _amount(p['remaining_for_you'], p.get('unit'))
            + ' left for this engine, use by ' + str(p.get('use_by')) + '; nothing spent on the runner (docs/CREDITS.md)'
            for p in block['pools']]


class Guard:
    """Spends made in this process, never past what is left of the share."""

    def __init__(self, block):
        self.block = block
        self.spent = []

    def left(self, pool):
        if self.block is None:
            raise CreditRefused('credits unknown: the directive carried no block')
        match = [p for p in self.block['pools'] if p['pool'] == pool]
        if not match:
            raise CreditRefused('no share of ' + pool)
        used = sum(s['amount'] for s in self.spent if s['pool'] == pool)
        return max(0.0, float(match[0]['remaining_for_you']) - used)

    def reserve(self, pool, amount, asset, objective_key='new_subscribers'):
        if not (isinstance(amount, (int, float)) and amount > 0):
            raise CreditRefused('a spend is a positive amount')
        if amount > self.left(pool) + 1e-9:
            raise CreditRefused('over the share: ' + pool + ' has ' + str(round(self.left(pool), 2)) + ' left')
        if len(self.spent) >= MAX_SPENT:
            raise CreditRefused('at most ' + str(MAX_SPENT) + ' spends a report')
        entry = {'pool': pool, 'amount': amount, 'asset': str(asset)[:200], 'objective_key': objective_key}
        self.spent.append(entry)
        return entry


def spent_errors(items):
    """What Control Center's parseCreditsSpent would refuse in credits_spent."""
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_SPENT:
        return ['credits_spent is a list of 1 to ' + str(MAX_SPENT)]
    errors = []
    for i, item in enumerate(items):
        where = 'credits_spent[' + str(i) + ']'
        if not isinstance(item, dict) or set(item) != {'pool', 'amount', 'asset', 'objective_key'}:
            errors.append(where + ' is pool, amount, asset and objective_key')
            continue
        if not isinstance(item['pool'], str) or not POOL.match(item['pool']):
            errors.append(where + ' names a pool key')
        if isinstance(item['amount'], bool) or not isinstance(item['amount'], (int, float)) or item['amount'] <= 0:
            errors.append(where + ' has a positive amount')
        if not isinstance(item['asset'], str) or not item['asset'].strip() or EMAIL.search(item['asset']):
            errors.append(where + ' says what was made in words, never an address')
        if item['objective_key'] is not None and not isinstance(item['objective_key'], str):
            errors.append(where + ' objective_key is text or null')
    return errors
