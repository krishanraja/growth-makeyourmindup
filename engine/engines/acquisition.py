"""The Acquisition engine: routes into an audience, outreach to one recipient at a time, experiments and rules.

Review sections 1 to 3 (docs/reviews/2026-11-05-growth-engine-review.md). Every run starts with the strongest
available route into an audience, not individual conversations. A route ranks on demonstrated interest in the
story, evidence that it accepts contributions, speed, work, likelihood of credit, and whether an interested
reader can find, follow and subscribe afterward. Publisher-wide audience is never the delivered reach.

An approval binds sender, recipient, channel, subject, body and links by digest; a redirect needs a fresh
decision. The outcome ladder records each rung separately: a later rung never implies an earlier one. A decline
closes the opportunity and suppresses further asks. This module prepares and records. Krish acts.
"""
import json
import re

from engine.engines import core

KINDS = ('opportunity', 'outreach', 'experiment', 'rule')
LADDER = ('drafted', 'approved', 'sent', 'delivered', 'replied', 'declined', 'booked', 'live',
          'subscriber_attributed')
DECLINED = 'closed_declined'
STATES = {
    'opportunity': ('candidate', 'qualified', 'pitching', 'booked', 'live'),
    'outreach': ('drafted', 'awaiting_approval', 'needs_fresh_decision') + tuple(r for r in LADDER[1:]
                                                                              if r != 'declined'),
    'experiment': ('proposed', 'running'),
    'rule': ('active',),
}
CLOSED_STATES = (DECLINED,)
ROUTES = ('editorial_feature', 'newsletter_placement', 'creator_collaboration', 'community_experiment',
          'discovery_experiment')
SCORES = ('fit', 'access', 'speed', 'effort', 'credit')
PATH = ('find', 'follow', 'subscribe')
FIT_BASES = ('story_interest', 'title')
PARTS = ('intro', 'reason', 'contribution', 'ask', 'links')
HEX = re.compile(r'^[0-9a-f]{64}$')
FIND = ('Find and qualify the strongest route into an audience: an editorial feature with an identifiable '
        'intake, a newsletter placement using an existing MYMU piece, or a creator collaboration with a '
        'specific contribution. Record fit evidence, access evidence and the reader path.')


def _key(*parts):
    return core.digest('|'.join(' '.join(str(p).split()).lower() for p in parts))


def recipient_key(recipient):
    """The committed stand-in for a recipient: a digest. The address stays in the private overlay."""
    return _key(recipient)


def opportunity_key(route, outlet):
    """One key per route into one outlet or creator, so the same pitch or brief is never opened twice."""
    return _key(route, outlet)


def _closed(record):
    return core.is_closed('acquisition', record.get('state'))


# Detail checks ------------------------------------------------------------------------------------------


def _opportunity_errors(record):
    d, errors = record['detail'], []
    if d.get('route') not in ROUTES:
        errors.append('detail.route must be one of ' + ', '.join(ROUTES))
    if not (d.get('opportunity_key') == 'private' or HEX.match(str(d.get('opportunity_key')))):
        errors.append('detail.opportunity_key must be a digest or "private" (held in the overlay)')
    if record.get('opportunity_id') != record['id']:
        errors.append('an opportunity carries its own id as opportunity_id')
    for name in SCORES:
        if name in d and (type(d[name]) is not int or not 0 <= d[name] <= 3):
            errors.append('detail.' + name + ' must be 0 to 3')
    evidence = d.get('fit_evidence', [])
    if not isinstance(evidence, list) or not all(isinstance(e, dict) and e.get('basis') in FIT_BASES
                                                 and isinstance(e.get('ref'), str) and e['ref'].strip()
                                                 for e in evidence):
        errors.append('detail.fit_evidence must list {basis: ' + '|'.join(FIT_BASES) + ', ref}')
    elif d.get('fit', 0) and not evidence:
        errors.append('a fit score needs fit_evidence of demonstrated interest in the story')
    access = d.get('access_evidence', [])
    if not isinstance(access, list) or not all(isinstance(e, str) and e.strip() for e in access):
        errors.append('detail.access_evidence must be a list of refs')
    elif d.get('access', 0) and not access:
        errors.append('an access score needs access_evidence that the route accepts contributions')
    for name in ('publisher_audience', 'delivered_reach'):
        if name in d and d[name] != 'unknown' and (type(d[name]) is not int or d[name] < 0):
            errors.append('detail.' + name + ' must be a whole number or "unknown"')
    if type(d.get('publisher_audience')) is int and type(d.get('delivered_reach')) is int \
            and d['delivered_reach'] > d['publisher_audience']:
        errors.append('delivered_reach cannot exceed publisher_audience')
    path = d.get('reader_path', {})
    if not isinstance(path, dict) or set(path) - set(PATH) or not all(v in (True, False) for v in path.values()):
        errors.append('detail.reader_path must be {find, follow, subscribe: true|false}')
    if record['state'] == 'live' and not (isinstance(d.get('live_ref'), str) and has_path(record)):
        errors.append('a live placement needs live_ref and a full reader path into MYMU')
    if record['state'] == DECLINED and d.get('suppressed') is not True:
        errors.append('a declined opportunity is suppressed')
    return errors


def _rung(state):
    return 'declined' if state == DECLINED else state


def _outreach_errors(record):
    d, errors, state = record['detail'], [], record['state']
    known = HEX.match(str(d.get('recipient_key')))
    if not (known or d.get('recipient_key') == 'unknown'):
        errors.append('detail.recipient_key must be a digest or "unknown"; the address stays private')
    if known and 'opportunity_id' not in record:
        errors.append('a pitch to one recipient names its opportunity_id')
    structure = d.get('structure')
    if structure != 'unknown' and not (isinstance(structure, list) and set(structure) <= set(PARTS)):
        errors.append('detail.structure must list the parts outreach_errors found, or be "unknown"')
    outcomes = d.get('outcomes')
    if not isinstance(outcomes, dict) or set(outcomes) - set(LADDER) or not all(
            isinstance(v, dict) and core._date(v.get('at')) and isinstance(v.get('evidence_ref'), str)
            for v in outcomes.values()):
        return errors + ['detail.outcomes must map ladder rungs to {at: YYYY-MM-DD, evidence_ref}']
    approval = d.get('approval')
    if approval is not None and not (isinstance(approval, dict) and HEX.match(str(approval.get('digest')))):
        errors.append('detail.approval must be null or {digest, at, evidence_ref}')
    rung = _rung(state)
    if rung in LADDER[1:] and rung not in outcomes:
        errors.append('state ' + state + ' needs its own recorded outcome; a later rung implies nothing earlier')
    if any(r in outcomes for r in LADDER[2:] if r != 'declined') or state == 'approved':
        if not approval:
            errors.append('approved and later rungs need an approval digest')
        if not known or not isinstance(structure, list) or set(structure) != set(PARTS) \
                or d.get('channel') in (None, 'unknown'):
            errors.append('an approval binds a known recipient, channel and the full structure ' + ', '.join(PARTS))
    if state == 'needs_fresh_decision' and (approval or not d.get('redirected_from')):
        errors.append('a redirect carries redirected_from and no approval')
    return errors


def validate_detail(record):
    kind, d = record['kind'], record['detail']
    if kind == 'opportunity':
        return _opportunity_errors(record)
    if kind == 'outreach':
        return _outreach_errors(record)
    if kind == 'experiment':
        ok = all(isinstance(d.get(k), str) and d[k].strip() for k in ('hypothesis', 'judge_when'))
        return [] if ok else ['an experiment needs a hypothesis and judge_when']
    return [] if isinstance(d.get('rule'), str) and d['rule'].strip() else ['a rule states detail.rule']


# Ranking ------------------------------------------------------------------------------------------------


def has_path(record):
    """Can an interested reader find, follow and subscribe to MYMU afterward."""
    path = record['detail'].get('reader_path')
    return isinstance(path, dict) and all(path.get(k) is True for k in PATH)


def fit(record):
    """Fit counts demonstrated interest in the story. A senior title alone contributes little: at most 1."""
    d = record['detail']
    bases = {e.get('basis') for e in d.get('fit_evidence') or []}
    if not bases:
        return 0
    return d.get('fit', 0) if 'story_interest' in bases else min(d.get('fit', 0), 1)


def rank_routes(opportunities):
    """Open opportunities, strongest route first: reader path, then fit, access, speed, less work, credit and
    delivered reach. Publisher-wide audience never enters the ranking."""
    def strength(r):
        d = r['detail']
        reach = d.get('delivered_reach')
        return (has_path(r), fit(r), d.get('access', 0), d.get('speed', 0), -d.get('effort', 3),
                d.get('credit', 0), reach if type(reach) is int else -1)
    opportunities = list(opportunities)
    gone = _declined_by_pitch(opportunities)
    open_ = [r for r in opportunities if r.get('kind') == 'opportunity' and not _closed(r) and r['id'] not in gone]
    return sorted(sorted(open_, key=lambda r: r['id']), key=strength, reverse=True)


# Outreach -----------------------------------------------------------------------------------------------


def outreach_errors(draft):
    """A draft (private: exact words) needs a short introduction of Krish and MYMU with the publication link,
    a specific reason for this recipient, one useful contribution and one proportionate ask."""
    errors = ['missing ' + p for p in PARTS[:4] if not (isinstance(draft.get(p), str) and draft[p].strip())]
    links = draft.get('links')
    if not isinstance(links, list) or not any(isinstance(x, str) and 'makeyourmindup.ai' in x for x in links):
        errors.append('links must include the MYMU publication link')
    intro = draft.get('intro') if isinstance(draft.get('intro'), str) else ''
    if intro and not ('Krish' in intro and re.search(r'Make Your Mind Up|MYMU|makeyourmindup', intro)):
        errors.append('the introduction says who Krish is and what MYMU is')
    if intro and 'makeyourmindup.ai' not in intro:
        errors.append('the introduction carries a clickable publication link')
    if len(intro.split()) > 60:
        errors.append('the introduction is short: 60 words at most')
    if isinstance(draft.get('ask'), str) and draft['ask'].count('?') > 1:
        errors.append('one proportionate ask, not several')
    return errors


def approval_digest(sender, recipient, channel, subject, body, links):
    """The digest an approval binds. Any change to any of the six fields needs a fresh decision."""
    canonical = json.dumps({'sender': sender, 'recipient': recipient, 'channel': channel, 'subject': subject,
                            'body': body, 'links': list(links)},
                           sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return core.digest(canonical)


def approval_valid(record, **fields):
    """True only for the exact sender, recipient, channel, subject, body and links Krish approved."""
    approval = record['detail'].get('approval')
    return bool(approval) and record['state'] != 'needs_fresh_decision' \
        and approval['digest'] == approval_digest(**fields)


def _line(record, now, **changes):
    line = {**record, 'detail': dict(record['detail']), 'updated_at': now}
    line.update(changes)
    return line


def superseded(record):
    """Approval digests a redirect retired. None of them may approve the pitch again."""
    return [r['approval']['digest'] for r in record['detail'].get('redirects') or []
            if isinstance(r, dict) and isinstance(r.get('approval'), dict)]


def redirect(record, new_recipient, now):
    """An inbox redirected the pitch: the old approval does not carry to the new recipient. The rungs the
    earlier recipient reached (a send, a delivery) are kept under detail.redirects with that recipient."""
    d = record['detail']
    line = _line(record, now, state='needs_fresh_decision', next_owner='krish',
                 next_action='Krish decides afresh on the exact draft to the redirected recipient',
                 revisit_when='when Krish decides on the redirected draft')
    earlier = {'recipient_key': d.get('recipient_key'), 'approval': d.get('approval'),
               'outcomes': d.get('outcomes', {})}
    line['detail'].update(recipient_key=recipient_key(new_recipient), approval=None,
                          redirected_from=d.get('recipient_key'), redirects=list(d.get('redirects') or []) + [earlier],
                          outcomes={k: v for k, v in d.get('outcomes', {}).items() if k == 'drafted'})
    return line


def approve(record, digest, at, evidence_ref):
    """Krish approved the exact draft whose approval_digest is given. Only the digest is committed."""
    if digest in superseded(record):
        raise ValueError('that approval was given for an earlier recipient; a redirect needs a fresh decision')
    line = _line(record, at, state='approved', next_owner='krish',
                 next_action='Krish enacts the exact approved draft in his own session',
                 revisit_when='when Krish records the send receipt')
    line['detail']['approval'] = {'digest': digest, 'at': at, 'evidence_ref': evidence_ref}
    line['detail']['outcomes'] = {**record['detail'].get('outcomes', {}),
                                  'approved': {'at': at, 'evidence_ref': evidence_ref}}
    return line


def record_outcome(record, rung, at, evidence_ref):
    """Add one rung to an outreach's ladder. The state is the highest rung recorded; nothing is backfilled."""
    if rung not in LADDER:
        raise ValueError('rung must be one of ' + ', '.join(LADDER))
    if rung == 'approved':
        raise ValueError('record an approval with approve(), which binds its digest')
    if rung not in ('drafted', 'declined') and not record['detail'].get('approval'):
        raise ValueError(rung + ' needs an approval first; nothing goes out without one')
    line = _line(record, at)
    line['detail']['outcomes'] = {**record['detail'].get('outcomes', {}), rung: {'at': at,
                                                                                'evidence_ref': evidence_ref}}
    if rung == 'declined':
        line.update(state=DECLINED, revisit_when=None, next_owner='none', next_action=None)
    else:
        top = max(line['detail']['outcomes'], key=LADDER.index)
        current = _rung(record['state'])
        if top != 'declined' and (current not in LADDER or LADDER.index(top) > LADDER.index(current)):
            line['state'] = top
    return line


def decline(records, opportunity_id, at, evidence_ref):
    """Lines that close a declined opportunity, suppress it, and close its open pitches."""
    if opportunity_id not in records or records[opportunity_id]['kind'] != 'opportunity':
        raise ValueError('no acquisition opportunity ' + str(opportunity_id))
    opp = _line(records[opportunity_id], at, state=DECLINED, revisit_when=None, next_owner='none',
                next_action=None)
    opp['detail']['suppressed'] = True
    pitches = [record_outcome(r, 'declined', at, evidence_ref) for r in records.values()
               if r['kind'] == 'outreach' and r.get('opportunity_id') == opportunity_id and not _closed(r)]
    return [opp] + pitches


def commission_comment(record, now):
    """An outgoing comment as the first step keeps the opportunity_id and goes to Engagement to prepare.
    Returns the acquisition line and the Engagement batch that a fresh "Run Engagement" recovers."""
    line = _line(record, now, next_owner='engagement',
                 next_action='Engagement prepares the outgoing comment; Krish sees one draft and one decision',
                 revisit_when='when Engagement reports the comment ready or disposed')
    line['detail']['first_step'] = 'comment'
    batch = {'id': record['id'] + '-comment', 'engine': 'engagement', 'kind': 'batch', 'state': 'requested',
             'title': 'Outgoing comment Acquisition commissioned for ' + record['id'], 'source': record['source'],
             'next_owner': 'engagement', 'next_action': line['next_action'],
             'revisit_when': 'when the comment is ready for Krish or disposed',
             'opportunity_id': record['opportunity_id'], 'links': [record['id']], 'updated_at': now,
             'detail': {'requested': 1, 'requested_by': 'acquisition'}}
    return [line, batch]


def _declined_by_pitch(records):
    """Opportunities a declined pitch closed, even where the opportunity line itself was never closed."""
    return {r.get('opportunity_id') for r in records if r.get('kind') == 'outreach' and r.get('state') == DECLINED
            and r.get('opportunity_id')}


def suppressed(records):
    """Opportunities and recipients that take no further ask."""
    ids, keys = set(_declined_by_pitch(records.values())), set()
    for r in records.values():
        if r['kind'] == 'opportunity' and (r['state'] == DECLINED or r['detail'].get('suppressed')):
            ids.add(r['id'])
        if r['kind'] == 'outreach' and r['state'] == DECLINED and HEX.match(str(r['detail'].get('recipient_key'))):
            keys.add(r['detail']['recipient_key'])
    return {'opportunity_ids': sorted(ids), 'recipient_keys': sorted(keys)}


def admit_errors(records, record):
    """Why a record would duplicate a pitch or brief, ask a suppressed route again, reopen a decline, carry
    an approval to a changed pitch, or touch a pitch waiting at Krish's approval gate."""
    d = record.get('detail') or {}
    opp = records.get(record.get('opportunity_id'))
    errors = []
    if record.get('kind') == 'outreach' and record.get('state') == DECLINED and opp \
            and opp['kind'] == 'opportunity' and not _closed(opp):
        errors.append('record a decline with decline(), which closes and suppresses ' + opp['id'])
    if record.get('id') in records:
        return errors + _update_errors(records[record['id']], record)
    gone = suppressed(records)
    if record.get('kind') == 'opportunity' and d.get('opportunity_key') not in (None, 'private'):
        errors += ['duplicates opportunity ' + r['id'] for r in records.values() if r['kind'] == 'opportunity'
                   and r['detail'].get('opportunity_key') == d['opportunity_key']]
    if record.get('kind') == 'outreach':
        if record.get('opportunity_id') in gone['opportunity_ids']:
            errors.append('opportunity ' + record['opportunity_id'] + ' declined; follow-up is suppressed')
        if d.get('recipient_key') in gone['recipient_keys']:
            errors.append('recipient declined; follow-up is suppressed')
        errors += ['duplicates pitch ' + r['id'] for r in records.values() if r['kind'] == 'outreach'
                   and HEX.match(str(d.get('recipient_key')))
                   and (r.get('opportunity_id'), r['detail'].get('recipient_key'))
                   == (record.get('opportunity_id'), d.get('recipient_key'))]
    return errors


def _update_errors(current, line):
    cd, d, state = current['detail'], line.get('detail') or {}, line.get('state')
    if _closed(current) or cd.get('suppressed'):
        if not core.is_closed('acquisition', state) or (current['kind'] == 'opportunity'
                                                        and d.get('suppressed') is not True):
            return [current['id'] + ' is declined and suppressed; it stays closed']
        return []
    if current['kind'] != 'outreach':
        return []
    errors = []
    approval, digests = d.get('approval'), superseded(current)
    if current['state'] == 'awaiting_approval' and not (
            (state == 'approved' and approval) or state == DECLINED
            or (state == 'needs_fresh_decision' and d.get('redirected_from'))):
        errors.append(current['id'] + " waits at Krish's approval gate: only his approval, a redirect or a "
                                      'decline changes it')
    if isinstance(approval, dict) and approval.get('digest') == (cd.get('approval') or {}).get('digest') \
            and any(d.get(k) != cd.get(k) for k in ('recipient_key', 'channel', 'structure')):
        errors.append('the approval binds the recipient, channel and structure; a changed pitch needs a fresh '
                      'decision')
    if isinstance(approval, dict) and approval.get('digest') in digests:
        errors.append('that approval was given for an earlier recipient; a redirect needs a fresh decision')
    if set(digests) - set(superseded({'detail': d})):
        errors.append('detail.redirects keeps every earlier recipient and approval')
    return errors


def add(record, root=core.ROOT):
    """Refuse a duplicate or suppressed ask, then append the committed line."""
    errors = admit_errors(core.load('acquisition', root), record)
    if errors:
        raise ValueError('; '.join(errors))
    return core.append('acquisition', record, root)


# Recovery -----------------------------------------------------------------------------------------------


def _brief(r):
    return {k: r.get(k) for k in ('id', 'title', 'state', 'next_owner', 'next_action', 'revisit_when',
                                  'opportunity_id')}


def _conflicts(records):
    out, seen = [], {}
    for r in sorted(records.values(), key=lambda r: (str(r.get('updated_at')), r['id'])):
        errors = admit_errors(dict(seen), r)
        out += [r['id'] + ': ' + e for e in errors if not _closed(r)]
        seen[r['id']] = r
    out += [i + ': a pitch was declined but the opportunity is open; close it with decline()'
            for i in sorted(_declined_by_pitch(records.values())) if i in records and not _closed(records[i])]
    return out


def recover(records, all_records, now):
    """What a fresh Acquisition run recovers first (review, "How a fresh chat runs one engine")."""
    ranked = rank_routes(records.values())
    best = next((r for r in ranked if r['next_owner'] == 'acquisition'), None)
    pending = [r for r in records.values() if r['kind'] == 'outreach'
               and r['state'] in ('drafted', 'awaiting_approval', 'needs_fresh_decision')]
    if best:
        action = {**_brief(best), 'next_action': best['next_action'] or 'Qualify the route and prepare the offer'}
    else:
        action = {'id': None, 'title': 'Find the strongest route into an audience', 'state': None,
                  'next_owner': 'acquisition', 'next_action': FIND, 'revisit_when': 'every run'}
    running = sorted((r for r in records.values() if r['kind'] == 'experiment' and r['state'] == 'running'),
                     key=lambda r: (r['updated_at'], r['id']))
    return {
        'as_of': now,
        'best_opportunity': _brief(best) if best else None,
        'ranked_routes': [r['id'] for r in ranked],
        'evidence_of_access': {r['id']: r['detail'].get('access_evidence', []) for r in ranked},
        'outstanding_approvals': [{**_brief(r), 'detail': r['detail']} for r in sorted(pending, key=lambda r: r['id'])],
        'closed_routes': [_brief(r) for r in sorted(records.values(), key=lambda r: r['id'])
                          if r['kind'] == 'opportunity' and _closed(r)],
        'suppressed': suppressed(records),
        'active_experiment': _brief(running[0]) if running else None,
        'rules': [r['detail']['rule'] for r in sorted(records.values(), key=lambda r: r['id'])
                  if r['kind'] == 'rule' and r['state'] == 'active'],
        'handed_off': [_brief(r) for r in sorted(records.values(), key=lambda r: r['id'])
                       if r['next_owner'] in ('engagement', 'content-engine', 'measurement') and not _closed(r)],
        'conflicts': _conflicts(records),
        'next_action': action,
    }
