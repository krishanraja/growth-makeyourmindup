"""The engagement engine: incoming and outgoing interactions, requested batches and recurring questions.

Review sections 4 and 5 (docs/reviews/2026-11-05-growth-engine-review.md). An outgoing draft is ready only
when its full text survived the editor readback; incoming items never count toward an outgoing batch; a weak
candidate goes back to the researcher instead of padding a batch. Committed records carry digests. The post
URL, the exact words and the recovery copy live in the private overlay (.scratch/engines/engagement.jsonl).
Nothing here posts, comments, sends or writes to Control Center: Krish makes the final click.
"""
import re

from engine import owners
from engine.engines import core

KINDS = ('interaction', 'batch', 'question')
INTERACTION_STATES = ('candidate', 'drafted', 'ready', 'awaiting_krish', 'handled', 'skipped', 'posted_by_krish',
                      'returned_to_researcher')
STATES = {'interaction': INTERACTION_STATES, 'batch': ('requested', 'awaiting_krish'),
          'question': ('open', 'handed_off')}
CLOSED_STATES = ('handled', 'skipped', 'posted_by_krish', 'returned_to_researcher')
DIRECTIONS = ('incoming', 'outgoing')
# Krish's named accounts this engine engages from (AGENTS.md, social/channels/). His personal LinkedIn is
# growth-mindmake's since 13 Nov 2026 (Ruling, Krish, 2026-11-13; engine/owners.py), replies included.
ACCOUNTS = ('x', 'tiktok', 'instagram', 'threads', 'substack-notes', 'youtube', 'facebook')
# What Krish adds after reading the post (review section 5). Personal encouragement alone is not a reason.
CONTRIBUTIONS = ('firsthand_observation', 'practical_test', 'real_question')
EDITOR_STEPS = ('opened_actual_post', 'filled_native_editor', 'switched_away', 'returned', 'full_text_verified',
                'tab_left_open', 'recovery_copy_with_url')
# Typing into a native comment box was permitted only for LinkedIn preparation (BROWSER.md, 2026-10-24).
# LinkedIn left this engine on 13 Nov 2026 (Ruling, Krish, 2026-11-13), so no account here is prefilled:
# the exact copy sits beside the open post and the prefill-only editor steps never apply.
NATIVE_PREFILL = ()
PREFILL_ONLY_STEPS = ('filled_native_editor', 'switched_away', 'returned')
NEEDS_CONTRIBUTION = ('drafted', 'ready', 'awaiting_krish', 'posted_by_krish')
NEEDS_IDENTITY = ('ready', 'awaiting_krish')
REQUESTERS = ('krish', 'acquisition')
QUESTION_OWNERS = ('acquisition', 'content-engine')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
URL = re.compile(r'https?://', re.I)
PAGE = re.compile(r'https?://[^\s<>"]+', re.I)


def _key(value):
    return isinstance(value, str) and bool(SHA256.match(value))


def required_steps(account):
    """The editor_verification steps an outgoing item on this account must pass to count as ready."""
    if account in NATIVE_PREFILL:
        return EDITOR_STEPS
    return tuple(s for s in EDITOR_STEPS if s not in PREFILL_ONLY_STEPS)


def copy_page(detail):
    """The post URL an interaction's recovery copy carries, or None. The copy is Krish's exact words kept with
    the post URL (jobs/engagement.md), so it is the URL in the copy equal to post_url when there is one, else the
    last URL on the copy's last line. A link inside his words is what he says, not the page the item opens."""
    copy = detail.get('recovery_copy')
    if not isinstance(copy, str):
        return None
    post = detail.get('post_url')
    if isinstance(post, str) and post.strip() and post.strip() in PAGE.findall(copy):
        return post.strip()
    lines = [line for line in copy.splitlines() if line.strip()]
    found = PAGE.findall(lines[-1]) if lines else []
    return found[-1] if found else None


def opened(detail):
    """[(field, page)] for each page an interaction opens: its private post_url and the post URL its recovery copy
    carries (copy_page). Only the merged record (the private overlay over the committed line) carries them."""
    out = [('post_url', detail['post_url'])] if isinstance(detail.get('post_url'), str) else []
    page = copy_page(detail)
    return out + ([('recovery_copy', page)] if page is not None else [])


def pages(detail):
    """Every page an interaction opens (opened), never a link inside Krish's own words."""
    return [page for _, page in opened(detail)]


def owner_error(detail):
    """Why an interaction is another engine's, naming the field that made it so (its account, or the page its
    post_url or recovery copy opens), or ''."""
    if owners.owner(detail.get('account')):
        return 'detail.account: ' + owners.refusal(detail.get('account'))
    for field, page in opened(detail):
        why = owners.page_refusal(None, page)
        if why:
            return 'detail.' + field + ': ' + why
    return ''


def validate_detail(record):
    kind, d, state = record['kind'], record['detail'], record['state']
    errors = []
    if kind == 'interaction':
        if d.get('direction') not in DIRECTIONS:
            errors.append('detail.direction must be incoming or outgoing')
        if not _key(d.get('parent_post_key')):
            errors.append('detail.parent_post_key must be the sha256 of the post URL (the URL stays private)')
        handed = owner_error(d)
        if handed:
            errors.append(handed)
        elif d.get('account') not in ACCOUNTS:
            errors.append('detail.account must be one of ' + ', '.join(ACCOUNTS))
        for name in ('author_key', 'draft_digest', 'verified_digest'):
            if d.get(name) is not None and not _key(d[name]):
                errors.append('detail.' + name + ' must be a sha256 or null')
        steps = d.get('editor_verification', {})
        if not isinstance(steps, dict) or set(steps) - set(EDITOR_STEPS) \
                or not all(isinstance(v, bool) for v in steps.values()):
            errors.append('detail.editor_verification maps ' + ', '.join(EDITOR_STEPS) + ' to true or false')
        elif d.get('account') not in NATIVE_PREFILL and any(steps.get(s) for s in PREFILL_ONLY_STEPS):
            errors.append('no comment is prepared in a native editor here: only LinkedIn ever was (BROWSER.md,'
                          ' 2026-10-24), and it is growth-mindmake\'s since 13 Nov 2026')
        if not isinstance(d.get('identity_checked', False), bool):
            errors.append('detail.identity_checked must be true or false')
        elif d.get('direction') == 'outgoing' and state in NEEDS_IDENTITY and d.get('identity_checked') is not True:
            errors.append('an outgoing ' + state + ' item needs the account identity checked')
        # Post URLs stay private: only the overlay's private keys (post_url, recovery_copy) may hold one.
        errors += ['detail.' + k + ': a URL; commit parent_post_key and keep the URL in .scratch/engines/'
                   for k, v in d.items() if k not in core.PRIVATE_KEYS and isinstance(v, str) and URL.search(v)]
        contribution = d.get('contribution')
        if contribution == 'personal_encouragement':
            errors.append('personal encouragement alone is not a reason to comment')
        elif contribution is not None and contribution not in CONTRIBUTIONS:
            errors.append('detail.contribution must be one of ' + ', '.join(CONTRIBUTIONS))
        elif d.get('direction') == 'outgoing' and state in NEEDS_CONTRIBUTION and contribution is None:
            errors.append('an outgoing ' + state + ' item names what Krish contributes after reading the post')
        if d.get('direction') == 'incoming' and state == 'returned_to_researcher':
            errors.append('only an outgoing candidate goes back to the researcher')
    elif kind == 'batch':
        requested = d.get('requested')
        if not isinstance(requested, int) or isinstance(requested, bool) or requested < 1:
            errors.append('detail.requested must be a positive whole number of outgoing items')
        if d.get('requested_by') not in REQUESTERS:
            errors.append('detail.requested_by must be krish or acquisition')
        elif d['requested_by'] == 'acquisition' and not record.get('opportunity_id'):
            errors.append('a batch Acquisition commissions keeps its opportunity_id')
        excluded = d.get('excluded_keys', [])
        if not isinstance(excluded, list) or not all(_key(k) for k in excluded):
            errors.append('detail.excluded_keys must be sha256 keys of excluded posts or authors')
    elif kind == 'question':
        seen = d.get('times_seen')
        if not isinstance(seen, int) or isinstance(seen, bool) or seen < 2:
            errors.append('detail.times_seen must be 2 or more: a question is recurring')
        if state == 'handed_off' and (record.get('next_owner') not in QUESTION_OWNERS
                                      or sorted(d.get('hand_to') or []) != sorted(QUESTION_OWNERS)):
            errors.append('a handed-off question goes to both acquisition and content-engine (detail.hand_to), '
                          'with one of them as next_owner')
    return errors


# Domain rules -------------------------------------------------------------------------------------------


def _outgoing(item):
    return item['detail'].get('direction') == 'outgoing'


def _editor_verified(item):
    """Every editor step the account needs passed and the text read back from the editor is the draft."""
    d = item['detail']
    steps = d.get('editor_verification') or {}
    return all(steps.get(s) is True for s in required_steps(d.get('account'))) \
        and _key(d.get('draft_digest')) and d.get('verified_digest') == d.get('draft_digest')


def is_ready(item):
    """True when an open outgoing draft is ready in the correct editor: the account identity was checked,
    Krish's contribution is named and the draft survived the editor. A cleared editor is not ready, and nor is
    an item on a channel another engine owns, by its account or by the page it opens (owner_error, the same
    owners.page_refusal check): Krish's personal LinkedIn is growth-mindmake's (Ruling, Krish, 2026-11-13)."""
    d = item['detail']
    return _outgoing(item) and item['state'] not in CLOSED_STATES and d.get('identity_checked') is True \
        and d.get('contribution') in CONTRIBUTIONS and _editor_verified(item) and not owner_error(d)


def ready_count(items, blocked=()):
    """Incoming and outgoing counted apart, and how many outgoing drafts are actually ready for review.
    An item in blocked (privately excluded or already handled) is never ready."""
    items = list(items)
    ready = sorted(i['id'] for i in items if is_ready(i) and i['id'] not in blocked)
    return {'incoming': sum(1 for i in items if not _outgoing(i)),
            'outgoing': sum(1 for i in items if _outgoing(i)), 'ready': len(ready), 'ready_ids': ready}


def excluded_keys(records):
    """Private exclusions (batch detail.excluded_keys, kept in the overlay) as a set of keys."""
    return {k for r in records.values() if r['kind'] == 'batch' for k in r['detail'].get('excluded_keys', [])}


def handled_keys(records, but=None):
    """Parent posts an interaction already closed: handled, skipped, posted or returned. They cannot re-enter."""
    return {r['detail'].get('parent_post_key') for r in records.values()
            if r['kind'] == 'interaction' and r['state'] in CLOSED_STATES and r['id'] != but}


def _blocked(item, records):
    """Why an item's post or author cannot be worked: privately excluded, already handled, or neither."""
    d, reasons = item['detail'], []
    keys = {d.get('parent_post_key'), d.get('author_key')} - {None}
    if keys & excluded_keys(records):
        reasons.append('privately excluded')
    if keys & handled_keys(records, but=item['id']):
        reasons.append('already handled')
    return reasons


def blocked_ids(items, records):
    """Open outgoing items on a privately excluded or already handled post or author."""
    return sorted(i['id'] for i in items if _outgoing(i) and i['state'] not in CLOSED_STATES
                  and _blocked(i, records))


def replacement_errors(item, records):
    """Why an outgoing item cannot replace a dropped one. Empty means it qualifies: the post was opened, the
    contribution named, the account identity checked and the retained text verified, and it is neither
    excluded nor already handled."""
    d, errors = item['detail'], []
    if not _outgoing(item):
        return ['an incoming item never fills an outgoing batch']
    steps = d.get('editor_verification') or {}
    if not steps.get('opened_actual_post'):
        errors.append('the actual post was not opened')
    if d.get('contribution') not in CONTRIBUTIONS:
        errors.append('no contribution from Krish is identified')
    if d.get('identity_checked') is not True:
        errors.append('the account identity was not checked')
    if not _editor_verified(item):
        errors.append('the retained text was not verified in the editor')
    return errors + _blocked(item, records)


def qualifies_as_replacement(item, records):
    return not replacement_errors(item, records)


def return_to_researcher(item, now):
    """The next line for a weak candidate: back to the researcher, never padded into the batch."""
    return dict(item, state='returned_to_researcher', next_owner='none', next_action=None,
                revisit_when=None, updated_at=now)


def batch_items(batch_id, records):
    return [r for r in records.values() if r['kind'] == 'interaction' and batch_id in r.get('links', [])]


def decision_conflicts(records):
    """Opportunities with more than one open outgoing draft: Krish sees one draft and one decision."""
    open_by = {}
    for r in records.values():
        if r['kind'] == 'interaction' and _outgoing(r) and r['state'] not in CLOSED_STATES \
                and r.get('opportunity_id'):
            open_by.setdefault(r['opportunity_id'], []).append(r['id'])
    return {k: sorted(v) for k, v in sorted(open_by.items()) if len(v) > 1}


def recover(records, all_records, now):
    """Run Engagement: unanswered incoming items, any requested outgoing batch, correct identities, handled
    exclusions and the count of drafts actually ready for review."""
    interactions = [r for r in records.values() if r['kind'] == 'interaction']
    live = [r for r in interactions if r['state'] not in CLOSED_STATES]
    blocked = blocked_ids(live, records)
    batches = []
    for b in sorted((r for r in records.values() if r['kind'] == 'batch' and r['state'] != 'closed'),
                    key=lambda r: r['id']):
        open_items = [i for i in batch_items(b['id'], records) if i['state'] not in CLOSED_STATES]
        counts = ready_count(open_items, blocked)
        batches.append(dict({'id': b['id'], 'state': b['state'], 'requested': b['detail'].get('requested'),
                             'opportunity_id': b.get('opportunity_id'),
                             'short': max(0, b['detail'].get('requested', 0) - counts['ready'])}, **counts))
    outgoing = [r for r in live if _outgoing(r)]
    return {
        'unanswered_incoming': sorted(r['id'] for r in live if not _outgoing(r)),
        'batches': batches,
        'identities': {'unchecked': sorted(r['id'] for r in outgoing if r['detail'].get('identity_checked')
                                           is not True),
                       'by_account': {a: sum(1 for r in outgoing if r['detail'].get('account') == a)
                                      for a in ACCOUNTS if any(r['detail'].get('account') == a for r in outgoing)}},
        'exclusions': {'excluded': len(excluded_keys(records)), 'handled': len(handled_keys(records) - {None})},
        'blocked': blocked,
        'ready_for_review': ready_count(outgoing, blocked),
        'stale_ready': sorted(r['id'] for r in outgoing if r['state'] == 'ready' and not is_ready(r)),
        'returned_to_researcher': sorted(r['id'] for r in interactions if r['state'] == 'returned_to_researcher'),
        'questions': sorted(r['id'] for r in records.values() if r['kind'] == 'question' and r['state'] != 'closed'),
        'decision_conflicts': decision_conflicts(records),
    }
