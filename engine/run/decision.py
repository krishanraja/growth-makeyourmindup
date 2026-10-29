"""Concept approval goes live: Krish's decision on the week's mix plan becomes decision.json.

Ruling (Krish, 2026-10-29): "I just need to be in control of the idea and the
mocks and then I'm happy to let you let that engine just go for gold."

Two steps, both local and offline; nothing here calls Control Center, Buffer
or any network, and nothing schedules or posts.

1. readback: in the Control Center loop's own run (engine/cc_loop.py, right
   after it reads and matches decisions), each week's mix plan file
   (.scratch/mix/plan-<Monday>.json) is checked against the plan proposal the
   loop reported and his latest decision on it. His approval on the plan's
   exact payload_sha256, or his amended version when amended_sha256
   recomputes, approves each ready concept whose line stands in that text
   exactly (engine/mix.py approved_map); a concept whose line he deleted or
   changed is stopped. His decline, or a stop on the plan in the go-live
   ledger, stops every concept. The result is kept in
   .scratch/mix/decision-<Monday>.json, and a stop there never lifts.
2. apply: for each run spec of that week, decision.json gains `concepts`
   {concept_id: concept_sha256}, `concept_proposal_id`, `concept_decision`,
   `concept_manifest` (each approved concept in full, so a reader can
   recompute its hash), `concept_daily_caps` and `stopped_concepts`, and the
   spec signature gains `concepts_digest` and `concept_proposal_id`. The
   week's go-live part (`proposal_id`, `slots`, `amended`) is kept as it is,
   and must still match its own signature. With no go-live, the decision is
   concept-only: `proposal_id` and `decision` null, `slots` {}, and the
   approved mix plan is the go-live authority for posts made from its
   concepts, each still checked by release (engine/concepts.py, R101).

docs/CONCEPT-MANIFEST.md is the contract a release executor reads.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

from engine import concepts as concept_rules
from engine import intensity, mix as mix_rules
from engine.control_center import _latest, amendment_ok, payload_digest, sha256_hex, stopped_plans
from engine.core import instant, locked, read_json, write_json
from engine.social import validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / 'specs' / 'schema' / 'decision.schema.json'
SPEC_SCHEMA = ROOT / 'specs' / 'schema' / 'run-spec.schema.json'
MIX_DIR = Path('.scratch') / 'mix'
RUNS = Path('.scratch') / 'runs'
RECORD = 'growth-mix-decision/1'
EMPTY_DIGEST = sha256_hex({})


def iso(value):
    return instant(value).isoformat()


# 1. The readback -------------------------------------------------------------

def readback(mix_doc, cfg, proposals, decisions, ledger=None, now=None):
    """(record, None) for his decision on this week's mix plan, or (None, why nothing is recorded yet).

    proposals are the staged proposals the loop reported (cc_loop
    remembered_proposals); decisions are the matched decisions it read, which
    keep his amended version; ledger is the loop's go-live ledger. Pure.
    Raises ValueError when the plan file cannot be trusted.
    """
    pid = mix_rules.proposal_id(mix_doc['week_of'])
    item = mix_doc.get('proposal')
    if not isinstance(item, dict) or item.get('proposal_id') != pid:
        raise ValueError('the mix plan for ' + mix_doc['week_of'] + ' carries no plan proposal ' + pid)
    rebuilt = mix_rules.payload_text(mix_doc, cfg)
    own = payload_digest(item.get('wall'), item.get('channel'), item.get('exact_payload'), item.get('target'),
                         item.get('amount_usd'))
    if item.get('exact_payload') != rebuilt or own != item.get('payload_sha256'):
        raise ValueError('the mix plan file changed after its proposal was built; nothing in it is approved')
    reported = {p.get('proposal_id'): p for p in proposals or [] if isinstance(p, dict)}
    if pid not in reported:
        return None, 'the mix plan ' + pid + ' has not been reported to Control Center'
    if reported[pid].get('payload_sha256') != item['payload_sha256']:
        raise ValueError('the plan reported as ' + pid + ' is not this plan file; nothing in it is approved')
    latest, undated = _latest(decisions)
    if pid in undated:
        return None, 'a decision on ' + pid + ' has no readable time, so it is held, never guessed'
    stops = stopped_plans(list(reported.values()), decisions, ledger)
    decision = latest.get(pid)
    ready = sorted(c['concept_id'] for c in mix_doc['concepts'] if c.get('ready'))
    record = {'schema': RECORD, 'proposal_id': pid, 'week_of': mix_doc['week_of'],
              'plan_payload_sha256': item['payload_sha256'], 'read_at': iso(now),
              'decided_at': (decision or {}).get('decided_at'), 'amended': False, 'amended_sha256': None,
              'approved': {}, 'stopped_concepts': [], 'changed_concepts': [], 'plan_lines_changed': 0}
    if pid in stops or (decision or {}).get('decision') == 'declined':
        record.update(decision='declined', stopped_concepts=ready)
        return record, None
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
    record.update(decision='approved', approved=mix_rules.approved_map(mix_doc, text),
                  stopped_concepts=sorted(set(deleted) | set(changed)), changed_concepts=changed,
                  plan_lines_changed=mix_rules.plan_lines_changed(mix_doc, cfg, text))
    return record, None


def sticky(old, new):
    """A stop never lifts: a declined week stays declined, and a stopped concept stays stopped."""
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


def apply(spec, record, existing=None, caps=None, now=None):
    """(decision, signature) for this run from the week's mix decision record. Pure; raises ValueError."""
    pid = concept_rules.plan_proposal_id(spec)
    if pid is None or pid != record.get('proposal_id'):
        raise ValueError('the spec week does not match the mix plan ' + str(record.get('proposal_id')))
    known = concept_rules.by_id(spec)
    if not known:
        raise ValueError('the spec carries no concepts (run new --mix)')
    stopped = set(record.get('stopped_concepts') or []) | set((existing or {}).get('stopped_concepts') or [])
    if record.get('decision') == 'declined':
        stopped |= set(known)
    approved = {}
    for cid, sha in sorted((record.get('approved') or {}).items()):
        concept = known.get(cid)
        if cid in stopped or concept is None or concept.get('concept_sha256') != sha \
                or concept_rules.concept_errors(concept):
            continue
        approved[cid] = sha
    part = _go_live_part(spec, existing)
    decision = part or {'run_id': spec['run_id'], 'proposal_id': None, 'decision': None, 'decided_at': None,
                        'slots': {}}
    caps = caps or {}
    channels = sorted({p['channel'] for cid in approved for p in known[cid]['placements']})
    decision.update(
        concepts=approved, concept_proposal_id=pid,
        concept_decision={k: record.get(k) for k in ('decision', 'decided_at', 'plan_payload_sha256', 'amended',
                                                    'amended_sha256', 'read_at')},
        concept_manifest=[dict(concept_rules.concept_payload(known[cid]), concept_sha256=approved[cid])
                          for cid in approved],
        concept_daily_caps={c: caps.get(c) for c in channels},
        stopped_concepts=sorted(stopped), changed_concepts=sorted(record.get('changed_concepts') or []))
    if any(not isinstance(v, int) or isinstance(v, bool) for v in decision['concept_daily_caps'].values()):
        raise ValueError('a concept channel has no readable daily cap, so no concept is applied')
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


def write_run(root, spec_path, now=None):
    """Write decision.json and the spec signature for one run from its week's record. Returns a summary line."""
    spec_path = Path(spec_path)
    spec = read_json(spec_path)
    pid = concept_rules.plan_proposal_id(spec)
    if pid is None:
        raise ValueError('the spec has no window, so no mix plan names its week')
    path = record_path(root, _monday(spec))
    if not path.exists():
        return spec['run_id'] + ': no decision on ' + pid + ' has been read yet; nothing written'
    from engine.run.release import concept_caps
    from engine.run.spec import run_dir
    target = run_dir(spec, None, root) / 'decision.json'
    with locked(target):
        existing = read_json(target) if target.exists() else None
        caps = concept_caps(intensity.state(root, now)['urgency'], root)
        decision, signature = apply(spec, read_json(path), existing, caps, now)
        write_json(target, decision)
        write_json(spec_path, dict(spec, signature=signature))
    return (spec['run_id'] + ': ' + str(len(decision['concepts'])) + ' concepts approved, '
            + str(len(decision['stopped_concepts'])) + ' stopped; decision.json written locally')


def _monday(spec):
    from engine.core import ny_time
    day = ny_time(spec['window']['start']).date()
    return (day - dt.timedelta(days=day.weekday())).isoformat()


# The loop's hook -------------------------------------------------------------------

def after_readback(root, decisions, now=None):
    """Called by the Control Center loop right after it matches decisions. Returns lines to print.

    Each week's mix plan with a decision becomes its record, then every run
    spec of that week that carries concepts gets its decision.json. A plan or
    run that cannot be trusted is a line, never a crash and never a write."""
    from engine.cc_loop import golive_ledger, remembered_proposals
    root = Path(root)
    lines = []
    folder = root / MIX_DIR
    plans = sorted(folder.glob('plan-*.json')) if folder.is_dir() else []
    if not plans:
        return lines
    try:
        cfg = mix_rules.load(root)
        proposals = remembered_proposals(root)
        ledger = golive_ledger(root)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        return ['Mix plan decisions not read: ' + str(exc)]
    for path in plans:
        try:
            mix_doc = read_json(path)
            record, why = readback(mix_doc, cfg, proposals, decisions, ledger, now)
            out = record_path(root, mix_doc['week_of'])
            with locked(out):
                old = read_json(out) if out.exists() else None
                kept = sticky(old, record)
                if kept is not None and kept != old:
                    write_json(out, kept)
            if kept is None:
                lines.append('Mix plan ' + mix_doc['week_of'] + ': ' + str(why))
                continue
            lines.append('Mix plan ' + mix_doc['week_of'] + ': ' + kept['decision'] + ', '
                         + str(len(kept['approved'])) + ' concepts approved, ' + str(len(kept['stopped_concepts']))
                         + ' stopped' + (', ' + str(kept['plan_lines_changed']) + ' plan lines changed by him'
                                         ' for the next plan to read' if kept['plan_lines_changed'] else ''))
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
