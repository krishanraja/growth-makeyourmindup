"""Codex task cards: lint one card before anyone dispatches it. Offline; dispatches nothing."""
import argparse
import json
from pathlib import Path
import re

from ..social import validate
from .spec import ROOT

SCHEMA = ROOT / 'specs' / 'schema' / 'task-card.schema.json'
MAX_BYTES = 6 * 1024
MAX_READ = 5
NEVER = ('git', 'network', 'mcp', 'publishing', 'new-dependencies', 'edits-outside-write-allow')
EFFORTS = ('minimal', 'low', 'medium', 'high', 'xhigh')
FLOATING = re.compile(r'(?:^|[-_.:/])(?:latest|default|auto|any|best|current)$', re.I)
CATCH_ALL = ('*', '**', '**/*', '.', './', './*', './**')


def _relative(path):
    """A repository-relative path or glob: no absolute roots, drives or parent steps."""
    parts = re.split(r'[\\/]', path)
    return bool(path.strip()) and not re.match(r'^(?:[\\/]|[A-Za-z]:)', path) and '..' not in parts


def card_errors(raw):
    """Every reason this card cannot be dispatched, as [{code, message}]."""
    errors = []
    if len(raw) > MAX_BYTES:
        errors.append({'code': 'oversize', 'message': 'card is ' + str(len(raw)) + ' bytes; the limit is ' + str(MAX_BYTES)})
    try:
        card = json.loads(raw.decode('utf-8-sig'))
        validate(card, json.loads(SCHEMA.read_text(encoding='utf-8')))
    except ValueError as exc:
        return errors + [{'code': 'schema', 'message': str(exc)}]
    model, effort = card['model'].strip(), card['effort'].strip()
    if not model or FLOATING.search(model):
        errors.append({'code': 'model_unpinned', 'message': 'model must name one pinned model, not ' + json.dumps(card['model'])})
    if effort not in EFFORTS:
        errors.append({'code': 'effort_unpinned', 'message': 'effort must be one of ' + ', '.join(EFFORTS)})
    if card['worktree'] != {'path': '../growth-wt/' + card['id'], 'branch': 'codex/' + card['id']}:
        errors.append({'code': 'worktree', 'message': 'worktree is ../growth-wt/<id> on branch codex/<id>'})
    for glob in card['write_allow']:
        if not _relative(glob) or glob.strip() in CATCH_ALL:
            errors.append({'code': 'write_allow', 'message': 'write_allow glob is too wide or leaves the repository: ' + glob})
    if len(card['read_files']) > MAX_READ:
        errors.append({'code': 'read_files', 'message': 'at most ' + str(MAX_READ) + ' read files'})
    for path in card['read_files']:
        if not _relative(path):
            errors.append({'code': 'read_files', 'message': 'read file leaves the repository: ' + path})
    missing = [item for item in NEVER if item not in card['never']]
    if missing:
        errors.append({'code': 'never_list', 'message': 'never-list lacks ' + ', '.join(missing)})
    if not card['return_shape']:
        errors.append({'code': 'return_shape', 'message': 'return_shape names the JSON the task returns'})
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run', description='Codex task cards. Offline.')
    sub = parser.add_subparsers(dest='action', required=True)
    card = sub.add_parser('card').add_subparsers(dest='card_action', required=True)
    card.add_parser('lint').add_argument('file')
    args = parser.parse_args(argv)
    try:
        errors = card_errors(Path(args.file).read_bytes())
    except OSError as exc:
        errors = [{'code': 'unreadable', 'message': str(exc)}]
    print(json.dumps({'local_only': True, 'valid': not errors, 'errors': errors}, indent=2))
    return int(bool(errors))
