"""One local layout (W2.11): the folders on Krish's PC, read from config/studio.json.

Nothing else in this repository names a folder on his machine: the CI path
guard (tests/test_studio.py) refuses a hard-coded one outside this config and
the synthetic test fixtures. Resolving a path never creates, moves or deletes
anything; moving an existing clone waits on his consent row (Wave 3, W3.4).
"""
from pathlib import Path
import re

from .core import read_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path('config') / 'studio.json'
KINDS = ('repos', 'worktrees', 'runtime')
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$')


def roots(root=ROOT):
    value = read_json(Path(root) / CONFIG)
    found = value.get('local_roots') if isinstance(value, dict) else None
    if not isinstance(found, dict) or sorted(found) != sorted(KINDS) or not all(isinstance(v, str) for v in found.values()):
        raise ValueError('config/studio.json local_roots needs repos, worktrees and runtime')
    return found


def local_root(kind, repo=None, branch=None, root=ROOT):
    """The Windows path one kind of folder lives at, with {repo} and {branch} filled in."""
    template = roots(root)[kind]
    for key, value in (('repo', repo), ('branch', branch)):
        if '{' + key + '}' in template:
            if not (isinstance(value, str) and NAME.match(value.replace('/', '-'))):
                raise ValueError(kind + ' needs a ' + key)
            template = template.replace('{' + key + '}', value.replace('/', '\\'))
    return template
