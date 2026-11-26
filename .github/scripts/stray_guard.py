#!/usr/bin/env python3
"""No branch is left unmerged (Ruling, Krish, 2026-11-26: "ensure stray branches may NEVER ever be left unmerged").

Run every hour by .github/workflows/stray-guard.yml. For every branch except the default one:

- its work is already on the default branch: the branch is deleted;
- its only pull request was closed without merging, at this same commit: the branch is deleted (GitHub keeps
  the commits at refs/pull/<n>/head, so nothing is lost);
- it has no pull request and its last commit is older than IDLE_HOURS: a ready pull request is opened for it;
- its pull request is a draft not touched for DRAFT_HOURS: it is marked ready;
- a ready pull request whose CI is green at its head commit is merged; with no CI run yet, CI is started where the
  repository allows it (workflow_dispatch);
- anything still open after that (red CI, a conflict, a draft still young) is listed in one issue, "Stray branches
  and pull requests", which is closed when nothing is left.

Only branches of this repository are touched, never a fork's. KEEP is a regular expression of branch names never
touched. DRY_RUN=true reports what it would do and changes nothing.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

REPO = os.environ['REPO']
CI = os.environ.get('CI_WORKFLOW', 'CI')
CI_FILE = os.environ.get('CI_FILE', '')
DRY = os.environ.get('DRY_RUN', 'false') == 'true'
IDLE_HOURS = float(os.environ.get('IDLE_HOURS', '6'))
DRAFT_HOURS = float(os.environ.get('DRAFT_HOURS', '24'))
KEEP = re.compile(os.environ.get('KEEP', r'^(gh-pages)$'))
ISSUE_TITLE = 'Stray branches and pull requests'
NOW = dt.datetime.now(dt.timezone.utc)


def gh(*args, ok=False):
    r = subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode and not ok:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout if not r.returncode else None


def pages(path):
    out = gh('api', '--paginate', '--jq', '.[]', path)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def age_hours(stamp):
    return (NOW - dt.datetime.fromisoformat(stamp.replace('Z', '+00:00'))).total_seconds() / 3600


def ci_state(sha):
    runs = json.loads(gh('api', f'repos/{REPO}/actions/runs?head_sha={sha}&per_page=100'))['workflow_runs']
    runs = [r for r in runs if r['name'] == CI]
    if not runs:
        return None
    if any(r['status'] != 'completed' for r in runs):
        return 'pending'
    return 'success' if all(r['conclusion'] == 'success' for r in runs) else 'failure'


def act(note, *args):
    print(('would: ' if DRY else 'do: ') + note)
    if not DRY and args:
        return gh(*args, ok=True)
    return ''


def main():
    default = json.loads(gh('api', f'repos/{REPO}'))['default_branch']
    left = []
    for b in pages(f'repos/{REPO}/branches?per_page=100'):
        name, sha = b['name'], b['commit']['sha']
        if name == default or KEEP.search(name):
            continue
        cmp = json.loads(gh('api', f'repos/{REPO}/compare/{default}...{sha}', '--jq',
                            '{ahead_by, last: (.commits[-1].commit.committer.date // null), '
                            'subject: ((.commits[-1].commit.message // "") | split("\n")[0])}'))
        if cmp['ahead_by'] == 0:
            act(f'delete {name}: its work is on {default}', 'api', '-X', 'DELETE', f'repos/{REPO}/git/refs/heads/{name}')
            continue
        last = cmp['last'] or NOW.isoformat()
        prs = json.loads(gh('pr', 'list', '-R', REPO, '--head', name, '--state', 'all', '--json',
                            'number,state,isDraft,updatedAt,headRefOid,mergedAt,isCrossRepository'))
        prs = [p for p in prs if not p['isCrossRepository']]
        open_prs = [p for p in prs if p['state'] == 'OPEN']
        if not open_prs:
            closed_here = [p for p in prs if p['state'] == 'CLOSED' and not p['mergedAt'] and p['headRefOid'] == sha]
            if closed_here:
                act(f"delete {name}: pull request #{closed_here[0]['number']} was closed without merging at this commit "
                    f"(kept at refs/pull/{closed_here[0]['number']}/head)",
                    'api', '-X', 'DELETE', f'repos/{REPO}/git/refs/heads/{name}')
                continue
            if age_hours(last) < IDLE_HOURS:
                continue
            subject = cmp['subject'] or name
            out = act(f'open a pull request for {name}', 'pr', 'create', '-R', REPO, '--base', default, '--head', name,
                      '--title', subject[:200], '--body',
                      f'Opened by the stray-branch guard: `{name}` had {cmp["ahead_by"]} commit(s) not on `{default}` '
                      f'and no pull request for {IDLE_HOURS:g} hours. It merges when its CI is green (Ruling, Krish, '
                      f'2026-11-26: no branch is ever left unmerged). Close it if the work is not wanted.')
            if DRY:
                left.append(f'- `{name}`: no pull request yet ({cmp["ahead_by"]} commits)')
                continue
            open_prs = json.loads(gh('pr', 'list', '-R', REPO, '--head', name, '--state', 'open', '--json',
                                     'number,isDraft,updatedAt,headRefOid') or '[]')
            if not open_prs:
                left.append(f'- `{name}`: a pull request could not be opened ({(out or "").strip()[:120]})')
                continue
        pr = open_prs[0]
        num = pr['number']
        if pr['isDraft']:
            if age_hours(pr['updatedAt']) < DRAFT_HOURS:
                left.append(f'- #{num} `{name}`: draft, touched {age_hours(pr["updatedAt"]):.0f} h ago')
                continue
            act(f'mark #{num} ready: a draft untouched for {DRAFT_HOURS:g} hours', 'pr', 'ready', str(num), '-R', REPO)
        state = ci_state(pr['headRefOid'])
        if state == 'success':
            res = act(f'merge #{num} ({name}): CI is green', 'pr', 'merge', str(num), '-R', REPO, '--merge', '--delete-branch')
            if res is None:
                left.append(f'- #{num} `{name}`: green but would not merge (a conflict with `{default}`?)')
            continue
        if state is None and CI_FILE:
            act(f'start CI on {name} for #{num}', 'workflow', 'run', CI_FILE, '-R', REPO, '--ref', name)
            state = 'pending'
        left.append(f'- #{num} `{name}`: CI {state or "has not run"}')
    report(left)


def report(left):
    issues = json.loads(gh('issue', 'list', '-R', REPO, '--state', 'open', '--search', f'"{ISSUE_TITLE}" in:title',
                           '--json', 'number,title'))
    issue = next((i['number'] for i in issues if i['title'] == ISSUE_TITLE), None)
    body = ('Everything the stray-branch guard could not merge or delete on its last run '
            f'({NOW:%Y-%m-%d %H:%M} UTC). Each one needs fixing (red CI, a conflict) or closing.\n\n' + '\n'.join(left))
    print(body)
    if DRY:
        return
    if left and issue:
        gh('issue', 'edit', str(issue), '-R', REPO, '--body', body, ok=True)
    elif left:
        gh('issue', 'create', '-R', REPO, '--title', ISSUE_TITLE, '--body', body, ok=True)
    elif issue:
        gh('issue', 'close', str(issue), '-R', REPO, '--comment', 'Nothing stray left.', ok=True)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as e:
        sys.exit(str(e))
