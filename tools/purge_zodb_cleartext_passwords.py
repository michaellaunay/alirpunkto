#!/usr/bin/env python3
"""
purge_zodb_cleartext_passwords.py — remove the legacy cleartext passwords that
candidatures stored in the ZODB (security finding 1.3).

Since finding 1.3 was fixed, the application never writes a cleartext password
to the ZODB: ``register.py`` stores an ``{SSHA}`` hash in ``data.password``
(and no ``password_confirm`` at all), and the hash itself is purged once the
LDAP account is created. This tool brings the EXISTING database to the same
state:

  * plain members and APPROVED / REFUSED candidatures  → ``password`` cleared
    (their LDAP account already exists — or never will — so nothing is needed);
  * still-pending candidatures (DRAFT … voting)        → cleartext ``password``
    hashed in place to ``{SSHA}`` (their approval must still be able to create
    the LDAP account; ``register_user_to_ldap`` passes a hash through
    unchanged);
  * ``password_confirm``                               → cleared everywhere
    (a second cleartext copy the old registration flow persisted).

Values that are already hashed are left as they are (pending) or cleared
(account exists).

USAGE — run **inside the application virtualenv** (the ZODB pickles reference
``alirpunkto`` classes) and with the **Pyramid app stopped** (FileStorage is
single-writer). Take a backup first (``docker/backup.sh``).

    # inspect what would change
    python tools/purge_zodb_cleartext_passwords.py \
        --data-fs var/filestorage/Data.fs --dry-run

    # then apply
    python tools/purge_zodb_cleartext_passwords.py \
        --data-fs var/filestorage/Data.fs
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys

# States whose LDAP account either already exists (APPROVED) or never will
# (REFUSED): the stored password serves no purpose any more.
_SETTLED_STATES = {"APPROVED", "REFUSED"}

_HASH_PREFIXES = (
    "{SSHA}", "{SHA}", "{SSHA256}", "{SHA256}", "{SSHA512}", "{SHA512}",
    "{SMD5}", "{MD5}", "{CRYPT}", "{ARGON2}", "{PBKDF2}", "{PBKDF2-SHA1}",
    "{PBKDF2-SHA256}", "{PBKDF2-SHA512}",
)


def is_hashed(value: str | None) -> bool:
    return bool(value) and value.upper().startswith(
        tuple(p.upper() for p in _HASH_PREFIXES))


def make_ssha(cleartext: str, salt_len: int = 8) -> str:
    """`slappasswd -h {SSHA}`-compatible hash (verified natively by slapd)."""
    salt = os.urandom(salt_len)
    digest = hashlib.sha1(cleartext.encode("utf-8") + salt).digest()  # nosec B324 — {SSHA} is the format slapd consumes (accepted risk, see docs/*/audits/)
    return "{SSHA}" + base64.b64encode(digest + salt).decode("ascii")


def _is_pending(obj) -> bool:
    """True for a candidature whose approval is still ahead of it."""
    state = getattr(obj, "_candidature_state", None)
    if state is None:
        state = getattr(obj, "candidature_state", None)
    if state is None:            # plain Member: account already in LDAP
        return False
    return getattr(state, "name", str(state)) not in _SETTLED_STATES


def purge_container(container, apply: bool = True) -> dict:
    """Purge/hash password fields on every entry of a members-like mapping.

    ``container`` only needs ``.items()`` yielding (oid, member-like) pairs
    where entries may carry ``.data.password`` / ``.data.password_confirm``.
    Returns a stats dict; mutates entries only when ``apply`` is True.
    """
    stats = {
        "scanned": 0,
        "password_cleared": 0,        # settled entry, password dropped
        "password_hashed": 0,         # pending entry, cleartext -> {SSHA}
        "password_kept_hashed": 0,    # pending entry, already hashed
        "password_confirm_cleared": 0,
        "already_clean": 0,
        "planned_changes": [],        # (oid, action) — filled in dry-run too
    }
    for oid, obj in container.items():
        stats["scanned"] += 1
        data = getattr(obj, "data", None)
        if data is None:
            stats["already_clean"] += 1
            continue

        pw = getattr(data, "password", None)
        pc = getattr(data, "password_confirm", None)
        pending = _is_pending(obj)
        changed = False

        if pw:
            if pending and not is_hashed(pw):
                stats["password_hashed"] += 1
                stats["planned_changes"].append((oid, "hash password ({SSHA})"))
                if apply:
                    data.password = make_ssha(pw)
                changed = True
            elif pending:
                stats["password_kept_hashed"] += 1
            else:
                stats["password_cleared"] += 1
                stats["planned_changes"].append((oid, "clear password"))
                if apply:
                    data.password = None
                changed = True

        if pc:
            stats["password_confirm_cleared"] += 1
            stats["planned_changes"].append((oid, "clear password_confirm"))
            if apply:
                data.password_confirm = None
            changed = True

        if not changed and not pw and not pc:
            stats["already_clean"] += 1

        if changed and apply and hasattr(obj, "_p_changed"):
            # MemberDatas is a plain dataclass nested in a Persistent object:
            # the container entry must be flagged for ZODB to persist the edit.
            obj._p_changed = True
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Purge legacy cleartext passwords from the AlirPunkto ZODB "
                    "(finding 1.3). Stop the app and back up Data.fs first.",
    )
    parser.add_argument("--data-fs", default="var/filestorage/Data.fs",
                        help="path to the ZODB FileStorage "
                             "(default: var/filestorage/Data.fs)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args(argv)

    if not os.path.exists(args.data_fs):
        print(f"error: {args.data_fs} not found", file=sys.stderr)
        return 1

    # Imported here so `--help` works without the app environment.
    import transaction
    from ZODB import DB
    from ZODB.FileStorage import FileStorage

    storage = FileStorage(args.data_fs, read_only=args.dry_run)
    db = DB(storage)
    conn = db.open()
    try:
        root = conn.root()
        members = root.get("members")
        if members is None:
            print("error: no 'members' container in this ZODB root",
                  file=sys.stderr)
            return 1

        stats = purge_container(members, apply=not args.dry_run)

        mode = "DRY-RUN (nothing written)" if args.dry_run else "APPLIED"
        print(f"[{mode}] scanned {stats['scanned']} entries")
        print(f"  password cleared (member/approved/refused): "
              f"{stats['password_cleared']}")
        print(f"  password hashed in place (pending):         "
              f"{stats['password_hashed']}")
        print(f"  password already hashed, kept (pending):    "
              f"{stats['password_kept_hashed']}")
        print(f"  password_confirm cleared:                   "
              f"{stats['password_confirm_cleared']}")
        print(f"  already clean:                              "
              f"{stats['already_clean']}")
        for oid, action in stats["planned_changes"]:
            print(f"    - {oid}: {action}")

        if not args.dry_run:
            transaction.commit()
            print("committed.")
        return 0
    finally:
        conn.close()
        db.close()
        storage.close()


if __name__ == "__main__":
    raise SystemExit(main())
