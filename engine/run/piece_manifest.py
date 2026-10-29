"""Content-engine's piece manifest: what Growth checks a go-live against (W2.8).

Content-engine writes `0 Publish/manifest.json` for each piece once Krish
approves its publish board: the assets in order with their Drive ids and
sha256, the exact copy for each channel, the alt text, the QA state and the
digest of the board approval. Growth reads it by a direct download link and
its sha256 (named in the go-live dispatch, `piece_manifest`), and before a
post reaches Krish's list checks that each Buffer draft is exactly what the
manifest says for its channel: the words, the alt text and the assets, in
order. A draft that differs is held (`manifest_differs`); a manifest that is
not passed QA, does not hash to its sha256 or is not this closed shape holds
every slot.

The shape (`specs/schema/piece-manifest.schema.json`):
{"schema": "content-engine-piece-manifest/1", "piece_id", "approval_sha256",
 "qa": {"state": "passed" | "held" | "failed", "checked_at"},
 "assets": [{"name", "drive_id", "sha256", "order"}],
 "channels": {channel: {"words", "alt_text": [text, ...] | null, "assets": [name, ...]}}}

It never authorises anything: Krish's go-live does. It only refuses a draft
that is not what content-engine checked and he approved on the board.
"""
import hashlib
import json
import re

from engine.run.release import CHANNELS, HEX64

SCHEMA = 'content-engine-piece-manifest/1'
KEYS = frozenset({'schema', 'piece_id', 'approval_sha256', 'qa', 'assets', 'channels'})
QA_KEYS = frozenset({'state', 'checked_at'})
QA_STATES = ('passed', 'held', 'failed')
ASSET_KEYS = frozenset({'name', 'drive_id', 'sha256', 'order'})
CHANNEL_KEYS = frozenset({'words', 'alt_text', 'assets'})
PIECE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:._-]{0,119}$')
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$')
DRIVE_ID = re.compile(r'^[A-Za-z0-9_-]{10,100}$')
CHECKED_AT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$')
MAX_BYTES = 262144
MAX_ASSETS = 40


class ManifestRejected(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def parse(data, sha256):
    """The manifest from its bytes, checked against the sha256 the dispatch names.
    Raises ManifestRejected with a code; never returns a manifest that is not passed QA."""
    if not isinstance(data, (bytes, bytearray)) or not data or len(data) > MAX_BYTES:
        raise ManifestRejected('manifest_unreadable')
    if not isinstance(sha256, str) or not HEX64.match(sha256) or hashlib.sha256(data).hexdigest() != sha256:
        raise ManifestRejected('manifest_sha_mismatch')
    try:
        value = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise ManifestRejected('manifest_unreadable') from None
    validate(value)
    if value['qa']['state'] != 'passed':
        raise ManifestRejected('manifest_qa_not_passed')
    return value


def validate(value):
    if not isinstance(value, dict) or set(value) != KEYS or value.get('schema') != SCHEMA:
        raise ManifestRejected('manifest_malformed')
    if not isinstance(value['piece_id'], str) or not PIECE_ID.match(value['piece_id']):
        raise ManifestRejected('manifest_malformed')
    if not isinstance(value['approval_sha256'], str) or not HEX64.match(value['approval_sha256']):
        raise ManifestRejected('manifest_unapproved')
    qa = value['qa']
    if not isinstance(qa, dict) or set(qa) != QA_KEYS or qa['state'] not in QA_STATES \
            or not (isinstance(qa['checked_at'], str) and CHECKED_AT.match(qa['checked_at'])):
        raise ManifestRejected('manifest_malformed')
    assets = value['assets']
    if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
        raise ManifestRejected('manifest_malformed')
    names, orders = set(), set()
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != ASSET_KEYS \
                or not (isinstance(asset['name'], str) and NAME.match(asset['name'])) \
                or not (isinstance(asset['drive_id'], str) and DRIVE_ID.match(asset['drive_id'])) \
                or not (isinstance(asset['sha256'], str) and HEX64.match(asset['sha256'])) \
                or isinstance(asset['order'], bool) or not isinstance(asset['order'], int) or asset['order'] < 1:
            raise ManifestRejected('manifest_malformed')
        if asset['name'] in names or asset['order'] in orders:
            raise ManifestRejected('manifest_duplicate_asset')
        names.add(asset['name'])
        orders.add(asset['order'])
    channels = value['channels']
    if not isinstance(channels, dict) or not channels:
        raise ManifestRejected('manifest_malformed')
    for channel, entry in channels.items():
        if channel not in CHANNELS or not isinstance(entry, dict) or set(entry) != CHANNEL_KEYS \
                or not (isinstance(entry['words'], str) and entry['words'].strip()) \
                or not isinstance(entry['assets'], list) or any(n not in names for n in entry['assets']) \
                or len(set(entry['assets'])) != len(entry['assets']):
            raise ManifestRejected('manifest_malformed')
        alt = entry['alt_text']
        if alt is not None and not (isinstance(alt, list) and len(alt) == len(entry['assets'])
                                    and all(isinstance(a, str) for a in alt)):
            raise ManifestRejected('manifest_malformed')
    return value


def expected(manifest, channel):
    """(words, [asset sha256 in the channel's order], alt texts or None) for one channel, or None."""
    entry = manifest['channels'].get(channel)
    if entry is None:
        return None
    by_name = {a['name']: a['sha256'] for a in manifest['assets']}
    return entry['words'], [by_name[n] for n in entry['assets']], entry['alt_text']


def alt_texts(meta):
    """The alt text the draft carries for each asset, in order (None where an asset has
    none, or is not an image): read from meta, buffer_api.signed_meta's shape
    {"assets": [{"image": {"sha256", "metadata": {"altText"}}}]}."""
    assets = meta.get('assets') if isinstance(meta, dict) else None
    out = []
    for asset in assets if isinstance(assets, list) else []:
        inner = next(iter(asset.values()), None) if isinstance(asset, dict) and len(asset) == 1 else None
        metadata = inner.get('metadata') if isinstance(inner, dict) else None
        alt = metadata.get('altText') if isinstance(metadata, dict) else None
        out.append(alt if isinstance(alt, str) else None)
    return out


def line_hold(manifest, line):
    """None when the rebuilt go-live line is exactly the manifest's post for its channel,
    else the hold code: the manifest has no post for the channel, or the words, the
    assets (and their order) or the alt text differ."""
    want = expected(manifest, line.get('channel'))
    if want is None:
        return 'manifest_has_no_channel'
    words, assets, alt = want
    if line.get('words') != words or list(line.get('assets') or []) != assets:
        return 'manifest_differs'
    if alt is not None:
        carried = alt_texts(line.get('meta'))
        kinds = [next(iter(a)) if isinstance(a, dict) and len(a) == 1 else None
                 for a in ((line.get('meta') or {}).get('assets') or [])]
        if len(carried) != len(alt) or any(kind == 'image' and got != want
                                           for kind, got, want in zip(kinds, carried, alt)):
            return 'manifest_differs'
    return None
