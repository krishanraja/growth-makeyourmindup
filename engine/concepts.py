"""Concept approval: Krish approves the idea and its mock once; every post made from it follows.

Ruling (Krish, 2026-10-29): "I just need to be in control of the idea and the
mocks and then I'm happy to let you let that engine just go for gold."

A concept is one idea, its one claim and its mock files, bound by
concept_sha256. Krish approves it once, through the week's mix plan
(engine/mix.py) whose exact payload lists every concept_sha256. That approval
reaches release as decision.json `concepts` {concept_id: concept_sha256},
written only from the readback of his decision, and the spec signature holds
`concepts_digest`, the sha256 of that map. It authorises the engine to release
every slot made from the concept on Instagram, YouTube, TikTok and X, without a
per-post digest, through the same release gate and Buffer channel lock. Every
other check still runs on each post: copy lint, share asks, the ecosystem route,
the channel lock, capability checks and the creative bar.

A slot made from a concept must not depart from its mock: its channel and
format are one of the concept's placements, its assets are only the mock's
files (a re-render is a new hash and needs a new approval), and its words carry
the concept's claim word for word. A slot that departs is held, never released.
A Purge or decline on a concept, recorded as decision.json `stopped_concepts`,
or a stop on the mix plan proposal itself, stops every post made from it,
including any that were signed one by one. LinkedIn stays his click.

Offline: nothing here reads the network, schedules or posts.
"""
import re

from .control_center import sha256_hex

# The four channels where a concept approval is enough (Krish, 2026-10-29).
CONCEPT_CHANNELS = ('instagram', 'youtube', 'tiktok', 'x')
DIGESTED = ('concept_id', 'lane', 'idea', 'claim', 'source_url', 'piece_id', 'mock_sha256', 'placements')
SHA = re.compile(r'^[0-9a-f]{64}$')
STOPPED = 'concept_stopped'
DEPARTS = 'departs_from_approved_mock'


def collapse(text):
    return ' '.join(str(text).split())


def concept_payload(concept):
    """Exactly what Krish approves for one concept; no other field moves its digest."""
    return {key: concept[key] for key in DIGESTED}


def concept_sha256(concept):
    return sha256_hex(concept_payload(concept))


def concepts_digest(approved):
    """The sha256 of decision.json's concepts map, which the spec signature records."""
    return sha256_hex(approved)


def by_id(spec):
    return {c['concept_id']: c for c in (spec.get('concepts') or []) if isinstance(c, dict) and 'concept_id' in c}


def text_only(fmt, formats=None):
    """Whether a format carries no files at all (max_assets 0, such as X text); False when unknown.

    A post in such a format is made from its concept's claim alone, so it
    carries none of the mock files and is not held for it. When the format
    records cannot be read it is not text only, so the post holds.
    """
    if formats is None:
        try:
            from .social import inventory
            formats = inventory()['format']
        except (ValueError, KeyError, OSError, TypeError):
            return False
    record = (formats or {}).get(fmt)
    return isinstance(record, dict) and record.get('max_assets') == 0


def match_errors(slot, concept, formats=None):
    """Why a slot departs from its approved concept and mock, or [].

    formats maps format id to its social record (engine/social.py); without it
    the records are read from this repository."""
    out = []
    if slot['channel'] not in CONCEPT_CHANNELS:
        out.append(slot['channel'] + ' is not one of the concept channels (' + ', '.join(CONCEPT_CHANNELS)
                   + '); its posts are signed one by one')
    if slot['publish_mode'] != 'engine':
        out.append('a concept authorises engine posts only; LinkedIn stays his click')
    if {'channel': slot['channel'], 'format': slot['format']} not in concept['placements']:
        out.append(slot['channel'] + ' ' + slot['format'] + ' is not one of the placements approved with the concept')
    mocks = set(concept['mock_sha256'])
    used = [a['sha256'] for a in slot['assets']]
    if mocks and not used and not text_only(slot['format'], formats):
        out.append('the post carries none of the approved mock files')
    if not mocks and used:
        out.append('the concept was approved with no mock files, so the post may carry none')
    strange = [h for h in used if h not in mocks]
    if strange:
        out.append(str(len(strange)) + ' asset(s) are not the approved mock files (a re-render is a new hash and needs a new approval)')
    if collapse(concept['claim']) not in collapse(slot['words']):
        out.append("the words do not carry the concept's approved claim word for word")
    return out


def concept_errors(concept):
    """Why a concept is not a complete, self-consistent concept, or []."""
    out = []
    if concept.get('concept_sha256') != concept_sha256(concept):
        out.append('concept_sha256 is computed; it does not match this concept (run new --from)')
    if any(not SHA.match(h) for h in concept['mock_sha256']):
        out.append('mock sha256 must be 64 lowercase hex characters')
    if len(set(concept['mock_sha256'])) != len(concept['mock_sha256']):
        out.append('a mock file is listed twice')
    for place in concept['placements']:
        if place['channel'] not in CONCEPT_CHANNELS:
            out.append('placement ' + place['channel'] + ' is not one of the concept channels; LinkedIn stays his click')
    return out


def stopped(decision, concept_id, stopped_proposals=(), signature=None):
    """Whether Krish stopped this concept: its own Purge, or a stop on the mix plan proposal."""
    listed = decision.get('stopped_concepts') if isinstance(decision, dict) else None
    if isinstance(listed, list) and concept_id in listed:
        return True
    plan = (signature or {}).get('concept_proposal_id')
    return bool(plan) and plan in set(stopped_proposals or ())


def plan_proposal_id(spec):
    """The mix plan proposal for the spec's week (engine/mix.py proposal_id), or None without a window."""
    from .core import ny_time
    from .mix import proposal_id
    start = (spec.get('window') or {}).get('start') if isinstance(spec.get('window'), dict) else None
    if not start:
        return None
    try:
        return proposal_id(ny_time(start).date().isoformat())
    except (ValueError, TypeError):
        return None


def authority(spec, slot, decision, stopped_proposals=(), formats=None):
    """(digest, None) when Krish's concept approval covers this slot, else (None, reason).

    The digest is the slot's own payload_sha256: the post is bound to its
    approved concept by concept_sha256 and to its exact bytes by its digest.
    """
    cid = slot.get('concept_id')
    if not cid:
        return None, 'no concept_id: the post needs its own signed digest'
    concept = by_id(spec).get(cid)
    if concept is None:
        return None, 'concept ' + cid + ' is not in this spec'
    errors = concept_errors(concept)
    if errors:
        return None, 'concept ' + cid + ': ' + '; '.join(errors)
    if stopped(decision, cid, stopped_proposals, spec.get('signature')):
        return None, STOPPED + ': Krish stopped concept ' + cid + ', so none of its posts go out'
    approved = decision.get('concepts') if isinstance(decision, dict) else None
    if not isinstance(approved, dict) or approved.get(cid) != concept['concept_sha256']:
        return None, 'concept ' + cid + ' is not approved at this concept_sha256'
    departs = match_errors(slot, concept, formats)
    if departs:
        return None, DEPARTS + ': ' + '; '.join(departs)
    return slot['payload_sha256'], None


def decision_errors(spec, decision):
    """Why the decision's concept approvals cannot be trusted for this signed spec, or None."""
    approved = decision.get('concepts')
    stops = decision.get('stopped_concepts')
    if stops is not None and not (isinstance(stops, list) and all(isinstance(x, str) for x in stops)):
        return 'decision.json stopped_concepts must be a list of concept ids'
    if approved is None:
        return None
    if not isinstance(approved, dict) or not all(isinstance(v, str) and SHA.match(v) for v in approved.values()):
        return 'decision.json concepts must map each concept_id to its 64-hex concept_sha256'
    signature = spec.get('signature') or {}
    if not approved:
        return None
    if signature.get('concepts_digest') != concepts_digest(approved):
        return 'decision.json concepts do not match the signed concepts_digest; a mismatch is never signed'
    # A no on the mix plan must be able to stop its concepts, so the signature names that plan (R101).
    expected = plan_proposal_id(spec)
    if expected is None:
        return 'a spec with approved concepts needs its window, which names the mix plan for its week'
    if signature.get('concept_proposal_id') != expected:
        return ('the signature must name concept_proposal_id ' + expected
                + ", the week's mix plan, so a stop on it stops every concept it carried")
    return None
