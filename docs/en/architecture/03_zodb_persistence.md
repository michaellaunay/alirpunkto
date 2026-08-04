# ZODB persistence

> Status: current documentation.
> Modules: `alirpunkto/models/member.py` (`Members`), configuration in
> `development.ini` / `production.ini`.

## Storage

The ZODB uses a local `FileStorage`:

```ini
zodbconn.uri = file://%(here)s/var/filestorage/Data.fs?connection_cache_size=20000
```

Blobs and logs live under `var/` (`var/blobs`, `var/log`). Each Pyramid
request gets its connection through `pyramid_zodbconn`; `pyramid_tm`
delimits the transaction and `pyramid_retry` replays the request on
conflict (3 attempts).

## Root and access

The single application entry point is the `Members` mapping
(`root['members']`). `Members.get_instance(connection)` **always rebinds
the instance to the given connection**: a persistent object is tied to the
connection that loaded it, so reusing a cache from a closed connection
would raise `ConnectionStateError`. The root factory calls `get_instance`
with the request's connection; connection-less callers (for example
`generate_unique_oid`) fall back to the current instance.

## Writes

Views never commit themselves: `pyramid_tm` commits at the end of the
request (the explicit `transaction.commit()` calls were removed during the
2026 audit). E-mails handed to `pyramid_mailer` leave at that same commit,
which guarantees no e-mail ever announces a state that was not persisted.

## Rebuilding from LDAP

The ZODB is rebuildable: if `var/` is removed and the application
restarted, `update_member_from_ldap` (`alirpunkto/utils.py`) recreates each
member at their first login from the LDAP entry — type and profile
included, with `password`/`password_confirm` kept at `None`. The behaviour
is locked by `tests/test_zodb_repopulation_from_ldap.py` and the procedure
is described in `docker/README.md` ("Repopulating the ZODB").

## Known limits

- `FileStorage` is single-writer: the application and the offline tools
  (`tools/purge_zodb_cleartext_passwords.py`) must not write at the same
  time.
- Refused or stale candidatures stay in the store; no automatic purge
  exists (see [09_periodic_tasks](09_periodic_tasks.md)).

## Schema versioning and upgrade steps (2026-08-04)

The LDAP directory is the source of truth for members; the ZODB
carries the application state around it (candidatures, workflows,
member data). Since train 0087 the database is **versioned**:
`app_root.schema_version` (0 for a pre-versioning database) against
the code's `SCHEMA_VERSION`, and every persisted-structure change
travels as an explicit **upgrade step** in `alirpunkto/upgrades.py`
— idempotent (replayable after a conflict), one per change, in the
spirit of GenericSetup's upgrade steps reduced to the essentials.

Two runners share the registry: the **lazy** one in `root_factory`
(an integer comparison per request; the first request after an
upgrade migrates inside its own transaction, replayed by
pyramid_retry on conflict) and the **explicit**
`tools/run_upgrades.py` to migrate with the application stopped —
recommended in production. The ZODB file lock guarantees
exclusivity.

The production deployment pinned at `e6603d22` needs **no data
step** to reach version 1: the changes since (the resignation flow)
extend the vocabulary without touching stored objects; step 1 only
stamps the database.

**The strong path** — maintainer's decision of 2026-08-04: wipe the
ZODB and rebuild it from LDAP, accepting the loss of pending
candidatures (overwhelmingly spam that never solved the registration
challenge). `tools/rebuild_zodb_from_ldap.py` implements it by
reusing the application's own factory (`update_member_from_ldap`,
which creates or refreshes): idempotent, it resynchronises a live
database or rebuilds a fresh one; the full wipe procedure heads the
script.
