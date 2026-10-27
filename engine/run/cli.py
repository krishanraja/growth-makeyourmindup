"""growth.py run: route each command to its module, imported only when used.

Every module's main(argv) receives the whole argv, command word first.
"""
import importlib
import sys

ROUTES = {'new': 'spec', 'lint': 'spec', 'status': 'spec', 'pack': 'pack', 'card': 'cards',
          'release': 'release', 'measure': 'measure', 'northstar': 'measure', 'verdict': 'measure',
          'cost': 'cost', 'ga4': 'ga4', 'autorelease': 'autorelease', 'keys': 'keys',
          'dispatch-check': 'backup', 'handoff': 'handoff'}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ROUTES:
        print('usage: growth.py run {' + ','.join(ROUTES) + '} ...')
        return 2
    name = 'engine.run.' + ROUTES[argv[0]]
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        print(argv[0] + ': not built yet')
        return 2
    return module.main(argv)
