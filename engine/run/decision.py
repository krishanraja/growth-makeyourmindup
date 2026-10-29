"""Concept approval goes live: Krish's decision on the week's mix plan becomes decision.json.

Ruling (Krish, 2026-10-29): "I just need to be in control of the idea and the
mocks and then I'm happy to let you let that engine just go for gold."

Two steps, both local and offline; nothing here calls Control Center, Buffer
or any network, and nothing schedules or posts.

1. readback: in the Control Center loop's own run (engine/cc_loop.py, right
   after it reads and matches decisions), Krish's stops are first recorded in
   the go-live ledger (cc_loop.record_stops). Then each week's mix plan file
   (.scratch/mix/plan-<Monday>.json) is read against his decisions. His no on
   the plan (any digest, any time) or a stop on it in the ledger is read
   first and stops every concept. Otherwise the plan file must rebuild and
   match the proposal the loop reported; his approval on its exact
   payload_sha256, or his amended version when amended_sha256 recomputes,
   approves each ready concept whose line stands in that text exactly
   (engine/mix.py approved_map), and a concept whose line he deleted or
   changed is stopped. If his version changes any other plan line, the
   record is held and approves nothing. The result is kept in
   .scratch/mix/decision-<Monday>.json, and a stop there never lifts.
2. apply: for each run spec of that week, decision.json gains `concepts`
   {concept_id: concept_sha256}, `concept_proposal_id`, `concept_decision`,
   `concept_hold`, `concept_manifest` (each approved concept in full, so a
   reader can recompute its hash), `concept_daily_caps` (the most a day the
   approved plan states) and `stopped_concepts`, and the spec signature gains
   `concepts_digest` and `concept_proposal_id`. Every run checks again and
   fails closed: a plan file that no longer rebuilds, a yes on another plan
   digest, an unmatched decline or an unreadable ledger writes no concept,
   with the reason in `concept_hold`. The week's go-live part (`proposal_id`,
   `slots`, `amended`) is kept as it is, and must still match its own
   signature. With no go-live, the decision is concept-only: `proposal_id`
   and `decision` null, `slots` {}, and the approved mix plan is the go-live
   authority for posts made from its concepts, each still checked by release
   (engine/concepts.py, R101).

docs/CONCEPT-MANIFEST.md is the contract a release executor reads.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys

from engine import concepts as concept_rules
from engine import intensity, mix as mix_rules
from engine.control_center import _latest, _stops, amendment_ok, payload_digest, sha256_hex
from engine.core import instant, locked, read_json, write_json
from engine.social import validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / 'specs' / 'schema' / 'decision.schema.json'
SPEC_SCHEMA = ROOT / 'specs' / 'schema' / 'run-spec.schema.json'
MIX_DIR = Path('.scratch') / 'mix'
RUNS = Path('.scratch') / 'runs'
RECORD = 'growth-mix-decision/1'
EMPTY_DIGEST = sha256_hex({})
SHA_HEX = re.compile('^[0-9a-f]{64}$')
# Hold codes in concept_hold (docs/CONCEPT-MANIFEST.md): each approves no concept.
HOLD_UNRESOLVED = 'stop_unresolved'
HOLD_TERMS = 'amended_plan_terms'
STALE = 'stale_approval'
UNTRUSTED = 'plan_untrusted'


def iso(value):
    return instant(value).isoformat()


# 1. The readback -------------------------------------------------------------

def plan_errors(mix_doc, cfg):
    """Why this week's plan file cannot be trusted as the plan he was shown, or None.

    It must carry its own plan proposal, its words must rebuild from the file
    and today's config exactly, and its payload_sha256 must recompute."""
    pid = mix_rules.proposal_id(mix_doc['week_of'])
    item = mix_doc.get('proposal')
    if not isinstance(item, dict) or item.get('proposal_id') != pid:
        return 'the mix plan for ' + mix_doc['week_of'] + ' carries no plan proposal ' + pid
    rebuilt = mix_rules.payload_text(mix_doc, cfg)
    own = payload_digest(item.get('wall'), item.get('channel'), item.get('exact_payload'), item.get('target'),
                         item.get('amount_usd'))
    if item.get('exact_payload') != rebuilt or own != item.get('payload_sha256'):
        return 'the mix plan file changed after its proposal was built; nothing in it is approved'
    return None


def _declined(pid, decisions, stops):
    """True when Krish declined this plan, on any digest at any time, or the ledger holds it stopped."""
    if pid in stops:
        return True
    return any(isinstance(d, dict) and d.get('proposal_id') == pid and d.get('decision') == 'declined'
               for d in decisions or [])


def readback(mix_doc, cfg, proposals, decisions, ledger=None, now=None):
    """(record, None) for his decision on this week's mix plan, or (None, why nothing is recorded yet).

    proposals are the staged proposals the loop reported (cc_loop
    remembered_proposals); decisions are the matched decisions it read, which
    keep his amended version and each decision's stage; ledger is the loop's
    go-live ledger. Pure. A decline or a stop is read first, before anything
    about the plan file is trusted, because stopping is always safe. Raises
    ValueError when the plan file cannot be trusted and he did not decline it.
    """
    pid = mix_rules.proposal_id(mix_doc['week_of'])
    item = mix_doc.get('proposal') if isinstance(mix_doc.get('proposal'), dict) else {}
    reported = {p.get('proposal_id'): p for p in proposals or [] if isinstance(p, dict)}
    stops, unresolved = _stops(list(reported.values()), decisions, ledger)
    latest, undated = _latest(decisions)
    decision = latest.get(pid)
    every = sorted(c['concept_id'] for c in mix_doc.get('concepts') or []
                   if isinstance(c, dict) and isinstance(c.get('concept_id'), str))
    sha = item.get('payload_sha256')
    record = {'schema': RECORD, 'proposal_id': pid, 'week_of': mix_doc['week_of'],
              'plan_payload_sha256': sha if isinstance(sha, str) and SHA_HEX.match(sha) else None,
              'read_at': iso(now), 'decided_at': (decision or {}).get('decided_at'), 'amended': False,
              'amended_sha256': None, 'approved': {}, 'stopped_concepts': [], 'changed_concepts': [],
              'plan_lines_changed': 0, 'hold': None}
    if _declined(pid, decisions, stops):
        record.update(decision='declined', stopped_concepts=every)
        return record, None
    if pid in undated:
        return None, 'a decision on ' + pid + ' has no readable time, so it is held, never guessed'
    if unresolved:
        return None, (HOLD_UNRESOLVED + ': ' + str(len(unresolved)) + ' declined check-in(s) not yet matched to'
                      ' their plan; any of them may stop ' + pid)
    problem = plan_errors(mix_doc, cfg)
    if problem:
        raise ValueError(problem)
    if pid not in reported:
        return None, 'the mix plan ' + pid + ' has not been reported to Control Center'
    if reported[pid].get('payload_sha256') != item['payload_sha256']:
        raise ValueError('the plan reported as ' + pid + ' is not this plan file; nothing in it is approved')
    if decision is None:
        return None, 'no decision on ' + pid + ' yet'
    if decision.get('decision') != 'approved':
        return None, 'the latest decision on ' + pid + ' is ' + str(decision.get('decision'))
    if decision.get('payload_sha256') != item['payload_sha256']:
        return None, 'stale_approval: his yes on ' + pid + ' was on another payload'
    text = item['exact_payload']
    if decision.get('amended') is True:
        if not amendment_ok(decision):
            return None, 'amended_digest_mismatch: his amended version of ' + pid + ' does not recompute'
        if decision.get('amount_usd') not in (None, 0):
            return None, 'no_spend_authority: the mix plan spends nothing'
        text = decision['exact_payload']
        record.update(amended=True, amended_sha256=decision['amended_sha256'])
    deleted, changed = mix_rules.amended_out(mix_doc, text)
    lines = mix_rules.plan_lines_changed(mix_doc, cfg, text)
    record.update(stopped_concepts=sorted(set(deleted) | set(changed)), changed_concepts=changed,
                  plan_lines_changed=lines)
    if lines:
        # His changed terms (a cap, a channel, the slots) cannot be enforced from the engine's plan, and
        # approving the concepts under the engine's terms would act on the engine's version, not his.
        record.update(decision='held', hold=(HOLD_TERMS + ': he changed ' + str(lines) + ' plan line(s); no'
                                             ' concept is approved until a plan carrying his terms is approved'))
        return record, None
    record.update(decision='approved', approved=mix_rules.approved_map(mix_doc, text))
    return record, None


def sticky(old, new):
    """A stop never lifts: a declined week stays declined, and a stopped concept stays stopped.

    With nothing new read (decisions arrive once), the old record stands; apply
    still checks it against the week's current plan on every run, so a yes on a
    plan that has since changed approves nothing. A held record replaces an
    approval, because his latest word on the plan is not a plain yes."""
    if not old:
        return new
    if not new or old.get('decision') == 'declined':
        return old
    stopped = sorted(set(old.get('stopped_concepts') or []) | set(new.get('stopped_concepts') or []))
    out = dict(new, stopped_concepts=stopped)
    out['approved'] = {cid: sha for cid, sha in (new.get('approved') or {}).items() if cid not in stopped}
    return out


def record_path(root, week_of):
    return Path(root) / MIX_DIR / ('decision-' + week_of + '.json')


def plan_path(root, week_of):
    return Path(root) / MIX_DIR / ('plan-' + week_of + '.json')


# 2. Apply to a run ---------------------------------------------------------------

def _go_live_part(spec, existing):
    """The week's go-live part of an existing decision.json, checked against its signature, or None."""
    if not existing or existing.get('proposal_id') is None:
        return None
    if existing.get('run_id') != spec['run_id']:
        raise ValueError('decision.json belongs to another run')
    signature = spec.get('signature') or {}
    if existing.get('decision') != 'approved' or signature.get('go_live_proposal_id') != existing['proposal_id'] \
            or signature.get('decision_digest') != sha256_hex(existing.get('slots')):
        raise ValueError("decision.json's go-live part does not match the spec signature; it is never re-signed here")
    part = {k: existing[k] for k in ('run_id', 'proposal_id', 'decision', 'decided_at', 'slots') if k in existing}
    if existing.get('amended') is not None:
        part['amended'] = existing['amended']
    return part


def apply(spec, record, existing=None, ceilings=None, plan_sha=None, hold=None, now=None):
    """(decision, signature) for this run from the week's mix decision record. Pure; raises ValueError.

    ceilings is channel -> the most posts a day the approved plan states
    (engine/mix.py ceiling); plan_sha is the payload_sha256 of the week's plan
    proposal as it stands now. A record approved on another plan, or any hold
    (a reason string), approves nothing and writes concept_hold, so a stale or
    unenforceable yes never keeps posts going."""
    pid = concept_rules.plan_proposal_id(spec)
    if pid is None or (record is not None and pid != record.get('proposal_id')):
        raise ValueError('the spec week does not match the mix plan ' + str((record or {}).get('proposal_id')))
    known = concept_rules.by_id(spec)
    if not known:
        raise ValueError('the spec carries no concepts (run new --mix)')
    record = record or {}
    stopped = set(record.get('stopped_concepts') or []) | set((existing or {}).get('stopped_concepts') or [])
    if record.get('decision') == 'declined':
        stopped |= set(known)
    if hold is None and record.get('decision') == 'held':
        hold = record.get('hold') or HOLD_TERMS
    if hold is None and record.get('decision') == 'approved' and record.get('plan_payload_sha256') != plan_sha:
        hold = STALE + ': his yes was on plan ' + str(record.get('plan_payload_sha256')) + ', not the plan in force'
    approved = {}
    for cid, sha in sorted((record.get('approved') or {}).items()) if hold is None else ():
        concept = known.get(cid)
        if record.get('decision') != 'approved' or cid in stopped or concept is None \
                or concept.get('concept_sha256') != sha or concept_rules.concept_errors(concept):
            continue
        approved[cid] = sha
    part = _go_live_part(spec, existing)
    decision = part or {'run_id': spec['run_id'], 'proposal_id': None, 'decision': None, 'decided_at': None,
                        'slots': {}}
    ceilings = ceilings or {}
    channels = sorted({p['channel'] for cid in approved for p in known[cid]['placements']})
    seen = {k: record.get(k) for k in ('decision', 'decided_at', 'plan_payload_sha256', 'amended', 'amended_sha256',
                                       'read_at')}
    decision.update(
        concepts=approved, concept_proposal_id=pid,
        concept_decision=seen if record.get('decision') else None,
        concept_hold=hold,
        concept_manifest=[dict(concept_rules.concept_payload(known[cid]), concept_sha256=approved[cid])
                          for cid in approved],
        concept_daily_caps={c: ceilings.get(c) for c in channels},
        stopped_concepts=sorted(stopped), changed_concepts=sorted(record.get('changed_concepts') or []))
    if any(not isinstance(v, int) or isinstance(v, bool) for v in decision['concept_daily_caps'].values()):
        raise ValueError('a concept channel has no daily cap in the approved plan, so no concept is applied')
    signature = dict(spec.get('signature') or {})
    if part is None:
        signature.update(go_live_proposal_id=None, decision_digest=EMPTY_DIGEST)
    signature.update(concepts_digest=concept_rules.concepts_digest(approved), concept_proposal_id=pid,
                     signed_at=iso(now))
    validate(decision, read_json(SCHEMA))
    validate(dict(spec, signature=signature), read_json(SPEC_SCHEMA))
    problem = concept_rules.decision_errors(dict(spec, signature=signature), decision)
    if problem:
        raise ValueError(problem)
    return decision, signature


def _plan_in_force(root, week_of, cfg):
    """(mix_doc, None) for the week's plan file when it can be trusted, else (None, the hold reason)."""
    path = plan_path(root, week_of)
    if not path.exists():
        return None, UNTRUSTED + ': no plan file for the week of ' + week_of
    try:
        mix_doc = read_json(path)
        problem = plan_errors(mix_doc, cfg)
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        problem = str(exc)
    return (None, UNTRUSTED + ': ' + problem) if problem else (mix_doc, None)


def write_run(root, spec_path, now=None):
    """Write decision.json and the spec signature for one run from its week's record. Returns a summary line.

    Every hold is checked again on every run and fails closed: an untrusted or
    changed plan file, a yes on another plan, a stop in the go-live ledger, a
    decline not yet matched to its plan, or a ledger that cannot be read writes
    decision.json with no concept approved and the reason in concept_hold."""
    spec_path = Path(spec_path)
    spec = read_json(spec_path)
    pid = concept_rules.plan_proposal_id(spec)
    if pid is None:
        raise ValueError('the spec has no window, so no mix plan names its week')
    week_of = _monday(spec)
    path = record_path(root, week_of)
    if not path.exists():
        return spec['run_id'] + ': no decision on ' + pid + ' has been read yet; nothing written'
    from engine.run import release
    from engine.run.spec import run_dir
    record = read_json(path)
    hold, plan_sha, ceilings = None, None, {}
    try:
        cfg = mix_rules.load(root)
        plan, hold = _plan_in_force(root, week_of, cfg)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        plan, hold = None, UNTRUSTED + ': ' + str(exc)
    if plan is not None:
        plan_sha = plan['proposal']['payload_sha256']
        ceilings = {c: mix_rules.ceiling(plan, c) for c in cfg['channels']}
    try:
        if pid in release.stopped_plans(root):
            record = dict(record, decision='declined')
        elif hold is None and release.unresolved_stops(root):
            hold = HOLD_UNRESOLVED + ': a declined check-in in the go-live ledger is not yet matched to its plan'
    except ValueError as exc:
        hold = hold or HOLD_UNRESOLVED + ': ' + str(exc)
    target = run_dir(spec, None, root) / 'decision.json'
    with locked(target):
        existing = read_json(target) if target.exists() else None
        try:
            decision, signature = apply(spec, record, existing, ceilings, plan_sha, hold, now)
        except ValueError as exc:
            # Fail closed: what cannot be applied is withdrawn, never left standing from an earlier run.
            stops = set(record.get('stopped_concepts') or [])
            if record.get('decision') == 'declined':
                stops |= set(concept_rules.by_id(spec))
            bare = {'proposal_id': record.get('proposal_id'), 'stopped_concepts': sorted(stops)}
            decision, signature = apply(spec, bare, existing, ceilings, plan_sha, hold or 'not_applied: ' + str(exc),
                                        now)
        write_json(target, decision)
        write_json(spec_path, dict(spec, signature=signature))
    return (spec['run_id'] + ': ' + str(len(decision['concepts'])) + ' concepts approved, '
            + str(len(decision['stopped_concepts'])) + ' stopped'
            + ('; held: ' + decision['concept_hold'] if decision['concept_hold'] else '')
            + '; decision.json written locally')


def _monday(spec):
    from engine.core import ny_time
    day = ny_time(spec['window']['start']).date()
    return (day - dt.timedelta(days=day.weekday())).isoformat()


# The loop's hook -------------------------------------------------------------------

def after_readback(root, decisions, now=None):
    """Called by the Control Center loop right after it matches decisions. Returns lines to print.

    First Krish's stops are recorded in the go-live ledger (cc_loop
    record_stops), so release reads them too. Then each week's mix plan with a
    decision becomes its record, and every run spec of that week that carries
    concepts gets its decision.json. A plan or run that cannot be trusted is a
    line and a withdrawn approval, never a crash."""
    from engine.cc_loop import record_stops, remembered_proposals
    root = Path(root)
    lines = []
    folder = root / MIX_DIR
    plans = sorted(folder.glob('plan-*.json')) if folder.is_dir() else []
    if not plans:
        return lines
    try:
        proposals = remembered_proposals(root)
        ledger = record_stops(root, proposals, decisions)
        cfg = mix_rules.load(root)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        lines.append('Mix plan decisions not read: ' + str(exc))
        proposals = ledger = cfg = None
    for path in plans if cfg is not None else []:
        try:
            mix_doc = read_json(path)
            record, why = readback(mix_doc, cfg, proposals, decisions, ledger, now)
            out = record_path(root, mix_doc['week_of'])
            with locked(out):
                old = read_json(out) if out.exists() else None
                kept = sticky(old, record)
                if kept is not None and kept != old:
                    write_json(out, kept)
            if record is None:
                lines.append('Mix plan ' + mix_doc['week_of'] + ': ' + str(why))
            if kept is None:
                continue
            lines.append('Mix plan ' + mix_doc['week_of'] + ': ' + kept['decision'] + ', '
                         + str(len(kept['approved'])) + ' concepts approved, ' + str(len(kept['stopped_concepts']))
                         + ' stopped' + ('; ' + kept['hold'] if kept.get('hold') else ''))
        except (ValueError, KeyError, OSError, TypeError, AttributeError) as exc:
            lines.append('Mix plan ' + path.name + ' held: ' + str(exc))
    runs = root / RUNS
    for spec_path in sorted(runs.glob('*/spec.json')) if runs.is_dir() else []:
        try:
            if not concept_rules.by_id(read_json(spec_path)):
                continue
            lines.append(write_run(root, spec_path, now))
        except (ValueError, KeyError, OSError, TypeError, AttributeError) as exc:
            lines.append(spec_path.parent.name + ': decision not written: ' + str(exc))
    return lines


def main(argv=None, root=None):
    root = Path(root) if root else ROOT
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['decide']:
        argv = argv[1:]
    parser = argparse.ArgumentParser(prog='growth.py run decide',
                                     description="Write a run's decision.json from the week's mix plan decision. Offline.")
    parser.add_argument('spec')
    parser.add_argument('--now')
    args = parser.parse_args(argv)
    try:
        print(write_run(root, args.spec, args.now))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}))
        return 1
