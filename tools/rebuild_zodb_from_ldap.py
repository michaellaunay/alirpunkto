#!/usr/bin/env python3
"""Rebuild the ZODB member base from the directory — the strong path.

The LDAP directory is the source of truth for members; this tool
walks every ``uid`` it holds and creates or refreshes the matching
ZODB Member through the same code the application uses
(``update_member_from_ldap``). It is idempotent: run on a live
database it resynchronises, run on a fresh one it rebuilds.

Full wipe procedure (maintainer's decision, 2026-08-04 — pending
candidatures are lost; they are overwhelmingly spam that never
solved the registration challenge):

    1. stop the application;
    2. move the old database aside:
       mv var/datas/Data.fs      var/datas/Data.fs.pre-rebuild-$(date -u +%Y%m%dT%H%M%S)
       (also move Data.fs.index / .tmp / .lock if present);
    3. .venv/bin/python tools/rebuild_zodb_from_ldap.py production.ini
    4. restart the application.

The ZODB file lock guarantees exclusivity: if the application still
runs, opening the database fails — stop it first.

Usage:
    .venv/bin/python tools/rebuild_zodb_from_ldap.py production.ini
"""

import sys

import transaction
from pyramid.paster import bootstrap, setup_logging

from alirpunkto.constants_and_globals import (
    LDAP_BASE_DN,
    LDAP_PASSWORD,
    LDAP_USER,
)
from alirpunkto.secret_manager import get_secret
from alirpunkto.utils import get_ldap_connection, update_member_from_ldap

COMMIT_EVERY = 50


def iter_directory_uids():
    """Every member uid the directory holds."""
    with get_ldap_connection(
        ldap_user=LDAP_USER,
        ldap_password=get_secret(LDAP_PASSWORD),
    ) as conn:
        conn.search(LDAP_BASE_DN, "(uid=*)", attributes=["uid"])
        for entry in conn.entries:
            value = entry.uid.value
            if value:
                yield str(value)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ini = sys.argv[1]
    setup_logging(ini)
    ok = errors = 0
    with bootstrap(ini) as env:
        request = env["request"]
        for count, oid in enumerate(iter_directory_uids(), 1):
            try:
                update_member_from_ldap(oid, request)
                ok += 1
            except Exception as exc:  # keep walking, report at the end
                errors += 1
                print(f"[rebuild] ERROR on uid={oid}: {exc}")
            if count % COMMIT_EVERY == 0:
                transaction.commit()
        transaction.commit()
    print(f"[rebuild] done: {ok} member(s) created or refreshed, "
          f"{errors} error(s)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
