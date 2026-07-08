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
