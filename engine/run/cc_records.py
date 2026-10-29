"""Records the two L0 lanes keep in Control Center, read back by exact run_id.

engine.run.handoff writes them and engine.run.autorelease, the one executor,
reads them; nothing on GitHub Actions trusts a local file, a dispatch payload
or a PC .scratch. Each is an ordinary engine report (status ready, no
proposal unless it carries a plan part) whose run_id names what it holds:

- `makeyourmindup:review:<payload_sha256[:12]>` a derived slot's review
  (growth-derived-review/1), the full sha256 in the record;
- `makeyourmindup:derived:<YYYY-MM-DD>:<n>` the derived slots due that New
  York day (growth-derived-index/1), numbered from 1 in the order reported;
- `makeyourmindup:mixplan:<YYYY-Www>:<n>` a version of the week's mix plan
  (growth-mix-version/1): its parts by proposal_id and payload_sha256; the
  highest n is the plan in force;
- each plan part's own report `<proposal_id>:<payload_sha256[:12]>` carries
  its concepts (growth-mix-part/1) beside the proposal;
- `makeyourmindup:claimed:<32 hex>` a go-live autorelease finished acting on
  (growth-golive-claim/1), which seeds cc_loop.claim_golives' ledger;
- `makeyourmindup:mixslots:<YYYY-Www>:<plan key>:<i>` the week's slots
  (growth-mix-slots/1): which concept goes on which channel at which time, as
  the plan the handoff checked laid them out, in numbered chunks; the plan key
  is the first 12 hex of the sha256 of the version's parts (plan_key), so the
  slots are bound to the exact part digests Krish decides on and never change
  a part's words or digest;
- `makeyourmindup:mocks:<YYYY-Www>:<plan key>:<n>` the week's mock manifest
  (growth-mock-manifest/1): each approved mock file's sha256 to its Drive file
  id. Records are numbered from 1 in the order written; each names its
  manifest version and its chunk of that version, so a corrected manifest is
  the next version, written after the last record, and the highest version is
  the manifest in force (latest_version). The maker downloads each file by its
  id and refuses any whose bytes do not hash to its sha256.

A report's activity line is clipped and its whitespace collapsed
(control_center.clip), so a record rides as base64 of its canonical JSON in
numbered chunks with no whitespace in them (F118): `record <schema> i/n
<chunk>`. Words never reach a log; only codes and counts do.
"""
import base64
import binascii
import hashlib
import json
import re

from engine.control_center import (SLUG, ProtocolError, build_report, canonical_json, objective, report_digest,
                                   sha256_hex)

LINE_MAX = 500  # the schema's activity line
MAX_LINES = 38  # activity holds 40: two lines say in plain words what the report is
CHUNK = re.compile(r'^record ([a-z0-9-]+/[0-9]+) ([0-9]{1,2})/([0-9]{1,2}) ([A-Za-z0-9+/=]+)$')
REVIEW, INDEX, VERSION, PART, CLAIM = ('growth-derived-review/1', 'growth-derived-index/1', 'growth-mix-version/1',
                                       'growth-mix-part/1', 'growth-golive-claim/1')
SLOTS, MOCKS = 'growth-mix-slots/1', 'growth-mock-manifest/1'
MAX_CHUNKS = 24  # numbered chunks of one record read before a reader holds loudly
MAX_MOCK_RECORDS = 48  # numbered mock manifest records (every version's chunks) read before a lane holds loudly
NO_SPEND = 'this engine has no spend authority, bought no boosts and does not read platform ad spend'


def record_lines(schema, record):
    """The activity lines one record rides in; ValueError('record_too_large') past MAX_LINES."""
    data = base64.b64encode(canonical_json(record).encode('utf-8')).decode('ascii')
    width = LINE_MAX - len('record ' + schema + ' 99/99 ')
    chunks = [data[i:i + width] for i in range(0, len(data), width)]
    if not chunks or len(chunks) > MAX_LINES:
        raise ValueError('record_too_large')
    return [{'line': 'record ' + schema + ' ' + str(i) + '/' + str(len(chunks)) + ' ' + chunk}
            for i, chunk in enumerate(chunks, 1)]


def fits(schema, record):
    try:
        record_lines(schema, record)
    except ValueError:
        return False
    return True


def record_of(report, schema):
    """The one record of this schema a report carries, whole and in order, or ValueError."""
    chunks, total = {}, None
    for item in report.get('activity') or [] if isinstance(report, dict) else []:
        line = item.get('line') if isinstance(item, dict) else None
        match = CHUNK.match(line) if isinstance(line, str) else None
        if not match or match.group(1) != schema:
            continue
        index, count = int(match.group(2)), int(match.group(3))
        if total not in (None, count) or index in chunks or not 1 <= index <= count:
            raise ValueError('record_unreadable')
        total = count
        chunks[index] = match.group(4)
    if total is None or sorted(chunks) != list(range(1, total + 1)):
        raise ValueError('record_unreadable')
    try:
        value = json.loads(base64.b64decode(''.join(chunks[i] for i in range(1, total + 1)), validate=True)
                           .decode('utf-8'))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValueError('record_unreadable') from None
    if not isinstance(value, dict) or value.get('schema') != schema:
        raise ValueError('record_unreadable')
    return value


def read_report(cc, run_id):
    """The live report stored at run_id, its digest sound, or None when there is none. A report
    that is not live or whose digest does not recompute is ValueError; any other Control Center
    failure propagates (the caller fails closed)."""
    try:
        got = cc.read_report(run_id)
    except ProtocolError as error:
        if error.code == 'not_found':
            return None
        raise
    report = got.get('report') if isinstance(got, dict) else None
    if not isinstance(report, dict) or got.get('mode') != 'live' or report.get('mode') != 'live':
        raise ValueError('record_not_live')
    try:
        sound = got.get('payload_sha256') == report.get('payload_sha256') == report_digest(report)
    except (ValueError, TypeError):
        sound = False
    if not sound or report.get('run_id') != run_id:
        raise ValueError('record_digest_mismatch')
    return report


def read_record(cc, run_id, schema):
    """The record at run_id, or None when nothing is reported there yet."""
    report = read_report(cc, run_id)
    return None if report is None else record_of(report, schema)


def probe(cc, run_id_of, schema, cap):
    """Every numbered record from 1 up, in order, until the first number with none.

    run_id_of(n) names the n-th. Returns None when cap are all present (the caller
    holds loudly: it cannot tell it has read them all)."""
    out = []
    for number in range(1, cap + 1):
        record = read_record(cc, run_id_of(number), schema)
        if record is None:
            return out
        out.append(record)
    return None


# Addresses ---------------------------------------------------------------------

def review_run_id(payload_sha256):
    return SLUG + ':review:' + payload_sha256[:12]


def index_run_id(day, number):
    return SLUG + ':derived:' + day + ':' + str(number)


def version_run_id(week_label, number):
    return SLUG + ':mixplan:' + week_label + ':' + str(number)


def claim_run_id(proposal_id):
    """One claim per go-live, whatever decision it acted under: a go-live acts once (review 3, S4)."""
    return SLUG + ':claimed:' + hashlib.sha256(proposal_id.encode('utf-8')).hexdigest()[:32]


def plan_key(parts):
    """The first 12 hex of the sha256 of a mix version's parts [{proposal_id, payload_sha256}]: the address
    the week's slots and mock manifest are kept under, so each is bound to the exact digests he decides on."""
    return sha256_hex(parts)[:12]


def slots_run_id(week_label, key, number):
    return SLUG + ':mixslots:' + week_label + ':' + key + ':' + str(number)


def mocks_run_id(week_label, key, number):
    return SLUG + ':mocks:' + week_label + ':' + key + ':' + str(number)


# Records too large for one report ------------------------------------------------

def chunked(schema, make, items):
    """The fewest records make(items_chunk, i, n) can be split into, items in order, each fitting one report.

    Chunks are sized with worst-case numbering (99 of 99), so a chunk that fits here still fits once
    numbered. ValueError('record_too_large') when one item alone does not fit."""
    groups, current = [], []
    for item in items:
        if not fits(schema, make([item], 99, 99)):
            raise ValueError('record_too_large')
        if current and not fits(schema, make(current + [item], 99, 99)):
            groups.append(current)
            current = []
        current.append(item)
    groups.append(current)
    if len(groups) > MAX_CHUNKS:
        raise ValueError('record_too_large')
    return [make(group, number, len(groups)) for number, group in enumerate(groups, 1)]


def read_chunked(cc, run_id_of, schema):
    """Every chunk of one numbered record, in order, or None when chunk 1 is not reported yet.

    run_id_of(i) names chunk i. Each chunk must name its own number and the same count; a missing or
    inconsistent chunk is ValueError('record_unreadable'): a part of a record is never read as the whole."""
    first = read_record(cc, run_id_of(1), schema)
    if first is None:
        return None
    total = first.get('chunks')
    if type(total) is not int or not 1 <= total <= MAX_CHUNKS or first.get('chunk') != 1:
        raise ValueError('record_unreadable')
    out = [first]
    for number in range(2, total + 1):
        record = read_record(cc, run_id_of(number), schema)
        if record is None or record.get('chunk') != number or record.get('chunks') != total:
            raise ValueError('record_unreadable')
        out.append(record)
    return out


def latest_version(records):
    """The chunks of the highest manifest version among numbered records read in order (probe), or None
    when there are none. Versions count up from 1 and never go back; each version's chunks are numbered
    1..chunks, consecutive, and the highest is whole at the end. Anything else is ValueError('record_unreadable'):
    a part of a version is never read as the whole."""
    if not records:
        return None
    versions = [r.get('version') if isinstance(r, dict) else None for r in records]
    if not all(type(v) is int and v >= 1 for v in versions) or versions[0] != 1 or any(
            b not in (a, a + 1) for a, b in zip(versions, versions[1:])):
        raise ValueError('record_unreadable')
    top = versions[-1]
    group = [r for r in records if r['version'] == top]
    total = group[0].get('chunks')
    if type(total) is not int or not 1 <= total <= MAX_CHUNKS or len(group) != total or any(
            r.get('chunk') != number or r.get('chunks') != total for number, r in enumerate(group, 1)):
        raise ValueError('record_unreadable')
    return group


# Writing -----------------------------------------------------------------------

def objectives():
    return [objective('new_subscribers', reason='Measured by the measure job; this lane only records'),
            objective('paid_boosts_usd', reason='Measured by the measure job; ' + NO_SPEND)]


def record_report(run_id, schema, record, words, now, revision, proposals=()):
    """One live report carrying a record (and, for a plan part, its proposal), ready to post."""
    activity = [{'line': line} for line in words] + record_lines(schema, record)
    return build_report(run_id, 'live', now, revision, now, 'ready', objectives(), activity, list(proposals), [], [])
