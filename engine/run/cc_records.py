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
  (growth-golive-claim/1), which seeds cc_loop.claim_golives' ledger.

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

from engine.control_center import SLUG, ProtocolError, build_report, canonical_json, objective, report_digest

LINE_MAX = 500  # the schema's activity line
MAX_LINES = 38  # activity holds 40: two lines say in plain words what the report is
CHUNK = re.compile(r'^record ([a-z0-9-]+/[0-9]+) ([0-9]{1,2})/([0-9]{1,2}) ([A-Za-z0-9+/=]+)$')
REVIEW, INDEX, VERSION, PART, CLAIM = ('growth-derived-review/1', 'growth-derived-index/1', 'growth-mix-version/1',
                                       'growth-mix-part/1', 'growth-golive-claim/1')
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


# Writing -----------------------------------------------------------------------

def objectives():
    return [objective('new_subscribers', reason='Measured by the measure job; this lane only records'),
            objective('paid_boosts_usd', reason='Measured by the measure job; ' + NO_SPEND)]


def record_report(run_id, schema, record, words, now, revision, proposals=()):
    """One live report carrying a record (and, for a plan part, its proposal), ready to post."""
    activity = [{'line': line} for line in words] + record_lines(schema, record)
    return build_report(run_id, 'live', now, revision, now, 'ready', objectives(), activity, list(proposals), [], [])
