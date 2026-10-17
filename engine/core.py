"""Business dates, canonical links, attribution and atomic local state."""
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

UTC = dt.timezone.utc
TIMEZONE = 'America/New_York'
OWN_HOSTS = {'makeyourmindup.ai', 'www.makeyourmindup.ai', 'home.makeyourmindup.ai'}
KINDS = ('daily', 'pitches', 'swaps', 'radar', 'numbers', 'report', 'conversion', 'partners')
PLATFORMS = ('linkedin', 'x', 'substack', 'youtube', 'instagram', 'tiktok', 'spotify',
             'reddit', 'email', 'seo', 'podcast', 'partner', 'other')


def instant(value=None):
    if value is None:
        return dt.datetime.now(UTC)
    if isinstance(value, str):
        value = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValueError('timestamp must include a UTC offset')
    return value.astimezone(UTC)


def ny_time(value=None):
    value = instant(value)
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        return value.astimezone(ZoneInfo(TIMEZONE))
    except (ImportError, ZoneInfoNotFoundError):
        # Windows often has no IANA database. US rules since 2007, evaluated
        # from a UTC instant, including the repeated hour at the autumn change.
        if value.year < 2007:
            raise ValueError('New York fallback supports dates from 2007; install tzdata for earlier dates')
        march = dt.datetime(value.year, 3, 8, 7, tzinfo=UTC)
        start = march + dt.timedelta(days=(6 - march.weekday()) % 7)
        november = dt.datetime(value.year, 11, 1, 6, tzinfo=UTC)
        end = november + dt.timedelta(days=(6 - november.weekday()) % 7)
        offset = -4 if start <= value < end else -5
        return value.astimezone(dt.timezone(dt.timedelta(hours=offset), TIMEZONE))


def today(value=None):
    return ny_time(value).date().isoformat()


def calendar_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('date must be YYYY-MM-DD')
    date = dt.date.fromisoformat(value)
    if date.isoformat() != value:
        raise ValueError('date must be YYYY-MM-DD')
    return date


def http_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        u = urlsplit(value)
        return u.scheme in ('http', 'https') and bool(u.hostname) and not (u.username or u.password) and bool(u.port or u.netloc)
    except ValueError:
        return False


def canonical(url):
    if not http_url(url):
        raise ValueError('an http or https URL without credentials is required')
    u = urlsplit(url)
    host = u.netloc.lower()
    if host == 'www.makeyourmindup.ai':
        host = 'makeyourmindup.ai'
    # Functional parameters, including referral codes, survive. Tracking and
    # fragments do not define a different story or draft identity.
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((u.scheme.lower(), host, u.path or '/', urlencode(sorted(query)), ''))


def identity(prefix, *parts):
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return prefix + '_' + hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]


def tracked(url, platform, job, day=None, asset=None, placement=None, variant='a'):
    if platform not in PLATFORMS or job not in KINDS:
        raise ValueError('unknown platform or job')
    date = calendar_date(day or today()).strftime('%Y%m%d')
    if not http_url(url):
        raise ValueError('invalid destination URL')
    u = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.lower().startswith('utm_')]
    if (asset is None) != (placement is None):
        raise ValueError('asset and placement must be supplied together')
    content = identity('placement', asset, platform, placement, variant) if asset else job + '-' + date
    query += [('utm_source', platform), ('utm_medium', 'organic'), ('utm_campaign', 'growth'), ('utm_content', content)]
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(query), u.fragment))


def acquisition(url, previous=None, internal=False):
    """Keep original acquisition separate from an internal journey event.

    This is a handoff contract, not website instrumentation. Call only with
    consented/session-scoped attribution supplied by the actual website.
    """
    if not http_url(url):
        raise ValueError('invalid URL')
    tags = {k: v for k, v in parse_qsl(urlsplit(url).query) if k.lower().startswith('utm_')}
    if internal:
        return {'original': previous, 'placement': tags or None}
    return {'original': previous or tags or None, 'placement': None}


def read_json(path):
    with open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temp = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def locked(path):
    path = Path(str(path) + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('another run holds ' + str(path) + '; check that run before removing a stale lock')
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()
