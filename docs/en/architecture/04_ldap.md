# LDAP directory

> Status: current documentation.
> Modules: `alirpunkto/ldap_factory.py`, `alirpunkto/utils.py`,
> `alirpunkto/alirpunkto_schema.ldif`, `docker/migrate_ldap_legacy.py`,
> `tools/migrate_ldap_legacy_remote.py`, `tools/ldap_provision.py`.

## Role

OpenLDAP is the **identity referential**: accounts, passwords, profile
attributes and functional groups. Authentication is an LDAP *bind*; the
ZODB never stores a password.

## Topology

- flat person entries: `uid=<uuid>,<LDAP_BASE_DN>` (no OU), object classes
  `inetOrgPerson` + `alirpunktoPerson`;
- groups `cn=<name>Group,<LDAP_BASE_DN>` (`groupOfUniqueNames`); every
  group contains at least the placeholder member
  `uid=00000000-…,cn=admin,<base>` required by the class;
- membership is mirrored on the person side by the application-maintained
  attribute `uniqueMemberOf` (there is no `memberOf` overlay).

## Dedicated schema

`alirpunkto/alirpunkto_schema.ldif` declares 12 attributes
(`isActive`, `nationality`, `birthdate`, `secondLanguage`, `thirdLanguage`,
`cooperativeBehaviourMark(+Update)`, `numberSharesOwned`,
`dateEndValidityYearlyContribution`, `IBAN`, `uniqueMemberOf`,
`dateErasureAllData`) and the auxiliary class `alirpunktoPerson`
(`MUST isActive`).

## Access from the code

`ldap_factory.get_ldap_server` caches an ldap3 `Server`
(`get_info=ALL`: the server schema is loaded at bind time);
`get_ldap_connection` returns a fresh connection (mocked outside Docker
during tests). `schema_safe_attributes(connection, attributes)` filters the
requested attributes the server schema does not know: a directory lagging
one attribute behind must never turn login into a 500 error (incident of
2026-07-07, locked by `tests/test_ldap_schema_tolerance.py`).

Main writes (`utils.py`): `register_user_to_ldap` (creation),
`update_ldap_member` (profile), `update_member_password` — all hash the
password to `{SSHA}` through `secret_manager.make_ldap_password` (audit
finding 1.3). Read/synchronisation: `update_member_from_ldap` rebuilds or
updates the ZODB `Member` from the LDAP entry.

## Migration and provisioning

Three tools share the same adaptation pipeline
(`docker/migrate_ldap_legacy.py`: normalisations, reference repairs,
`{SSHA}` hashing):

- `docker/migrate_ldap_legacy.py`: from a `slapcat` export;
- `tools/migrate_ldap_legacy_remote.py`: network extraction via `.env`;
- `tools/ldap_provision.py`: the whole journey — a seed file
  interchangeable with `docker/initials_users.generated.ldif`, idempotent
  schema upgrade, loading (`--install-type docker|host`), in-place password
  hashing.

The detailed procedures are in `docker/README.md`.

## Known limits

- `uniqueMemberOf` is maintained by the application: a group change made
  outside the application can desynchronise it;
- the placeholder member `uid=00000000-…` must be ignored by any group
  processing.
