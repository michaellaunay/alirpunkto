#!/usr/bin/env python3
"""Run the pending ZODB upgrade steps with the application stopped.

The lazy runner in root_factory migrates on the first request; this
CLI is for operators who prefer to migrate explicitly before serving
(recommended for production: stop the app, run this, restart).

Usage:
    .venv/bin/python tools/run_upgrades.py production.ini

The ZODB file lock guarantees exclusivity: if the application is
still running, opening the database fails — stop it first.
"""

import sys

import transaction
from pyramid.paster import bootstrap, setup_logging

from alirpunkto.upgrades import (
    SCHEMA_VERSION,
    get_schema_version,
    run_pending_upgrades,
)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ini = sys.argv[1]
    setup_logging(ini)
    with bootstrap(ini) as env:
        root = env["root"]
        before = get_schema_version(root)
        applied = run_pending_upgrades(root, commit_each=transaction.commit)
        if applied:
            print(f"[upgrades] {before} -> {applied[-1]}: "
                  f"applied step(s) {applied}")
        else:
            print(f"[upgrades] already at schema version {before} "
                  f"(code expects {SCHEMA_VERSION}) — nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
