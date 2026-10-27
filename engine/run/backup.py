"""`growth.py run dispatch-check`: the backup morning run's gate.

Control Center wakes .github/workflows/control-center.yml at 05:10 UTC with a
repository_dispatch. A schedule at 05:40 UTC is the backup: before running
the loop it asks the GitHub API whether a repository_dispatch run of that
workflow already succeeded today (UTC). If one did it says "dispatch already
ran today" and the loop is skipped; otherwise the loop runs.

Read-only, with the job's own GITHUB_TOKEN (permissions actions: read). It
talks to api.github.com only, follows no redirect and never prints the
token or a response body. If the read fails, the backup runs: a second
report on a quiet day costs less than a missing one.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

from ..core import instant

API = 'https://api.github.com'
WORKFLOW = 'control-center.yml'
EVENT = 'repository_dispatch'
REPO = re.compile(r'^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$')
MAX_RESPONSE = 2000000
TIMEOUT = 20
ALREADY = 'dispatch already ran today'
RUN = 'no successful dispatch run today (UTC); running the backup'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('github_redirect_refused')


def runs_url(repo, day):
    if not isinstance(repo, str) or not REPO.match(repo):
        raise ValueError('GITHUB_REPOSITORY must be owner/name')
    query = urlencode({'event': EVENT, 'status': 'success', 'created': '>=' + day, 'per_page': 30})
    return API + '/repos/' + quote(repo, safe='/') + '/actions/workflows/' + WORKFLOW + '/runs?' + query


def dispatch_succeeded_today(runs, now=None):
    """True when the API's runs list holds a successful repository_dispatch run created today (UTC)."""
    day = instant(now).date()
    items = runs.get('workflow_runs') if isinstance(runs, dict) else None
    if not isinstance(items, list):
        raise ValueError('github_bad_response')
    for run in items:
        if not isinstance(run, dict) or run.get('event') != EVENT:
            continue
        if run.get('status') != 'completed' or run.get('conclusion') != 'success':
            continue
        if not isinstance(run.get('created_at'), str):
            continue  # instant(None) would read as now
        try:
            created = instant(run['created_at'])
        except (TypeError, ValueError, AttributeError):
            continue
        if created.date() == day:
            return True
    return False


def fetch_runs(repo, token, now=None, open_fn=None):
    day = instant(now).date().isoformat()
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(runs_url(repo, day), headers=headers, method='GET')
    open_fn = open_fn or urllib.request.build_opener(NoRedirect()).open
    try:
        with open_fn(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as error:
        error.close()
        raise ValueError('github_http_' + str(error.code)) from None
    except (urllib.error.URLError, OSError):
        raise ValueError('github_unreachable') from None
    if len(raw) > MAX_RESPONSE:
        raise ValueError('github_response_too_large')
    try:
        return json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise ValueError('github_bad_response') from None


def decide(environ=None, now=None, open_fn=None):
    """(skip, line). Never raises: an unreadable answer means run the backup."""
    environ = os.environ if environ is None else environ
    try:
        runs = fetch_runs(environ.get('GITHUB_REPOSITORY', ''), environ.get('GITHUB_TOKEN', ''), now, open_fn)
        if dispatch_succeeded_today(runs, now):
            return True, ALREADY
        return False, RUN
    except ValueError as exc:
        code = str(exc) if re.match(r'^[a-z][a-z0-9_]{0,63}$', str(exc)) else 'github_read_failed'
        return False, 'could not read the workflow runs (' + code + '); running the backup'


def main(argv=None, environ=None, now=None, open_fn=None, out=print):
    environ = os.environ if environ is None else environ
    skip, line = decide(environ, now, open_fn)
    out(line)
    output = environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as handle:
            handle.write('skip=' + ('true' if skip else 'false') + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
