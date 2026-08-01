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

## Dynamic groups (#148, 2026-07-30)

The eleven groups of issue #148 (created at startup alongside the three
historical ones) now get their **transitions**
(`alirpunkto/dynamic_groups.py`). The ticket's event algebra reduces to a
**pure function**, `compute_target_groups`, over four facts — shares
owned, yearly-contribution validity
(`dateEndValidityYearlyContribution`), sanction, Board/MAC role — the
groups themselves being the persistent state (sanction and role are read
from current memberships). The applier `sync_member_groups` is
**idempotent** and maintains **both sides** of the relation
(the member's `uniqueMemberOf`, the group's `uniqueMember`); it is
**best-effort by design**: a failure never breaks the calling operation,
the daily scan catches up. Since the external audit, every write goes
through `_checked_modify` — exception intercepted, return value
checked, `conn.result` logged with member, group, operation and
side — but both sides are still written independently: a one-sided
failure can leave a divergence the scan, which reads `uniqueMemberOf`
alone, does not see (P2 target: one authoritative side and a scan that
compares both). It is wired to the four event sources:
registration (an Ordinary Member joins `communityMembersGroup`; the legacy
`ordinaryMembersGroup` **drains progressively**), upgrade approval
(landing in `candidatesMissingShareYearContribGroup`), resignation (no
group left, the entry staying through the Quarantine) and any profile
update. Sanction and promotion events (#56/#57) keep a ready hook
(`force_sanctioned`) for the future admin views.

## Identity uniqueness and Quarantine (#54)

`is_valid_unique_identity(given names, family names, date of birth)`
compares every Applicant's identity against **all** LDAP entries —
deliberately **without an `isActive` filter**: a resigned or excluded
Cooperator's entry is kept through the Quarantine precisely so they cannot
register again with a virgin reputation. The check is wired to both
Cooperator entry points: the registration form and the upgrade (#7).

## Avatar (`jpegPhoto`, #150)

The avatar lives **only** in the LDAP `jpegPhoto` attribute — no ZODB, no
`deform` form: two dedicated views (`member_avatar` serves it,
`avatar_upload` writes it), a triple check (extension, magic number, size
≤ 4 MB), and writing restricted to the session owner.

## Long-term provisions (#110, #127, 2026-08-01)

Seven attributes join the reference schema while no feature exposes
them yet — **invisibility by construction**: no `MemberDatas` field, no
form node, no view, and a test locks that these names never reach the
application surface. `tools/ldap_provision.py` deploys them in one
resynchronisation (the modernity probes include the new names).

**The Shared Directory of Cooperators** (#110, statutes §5.3.1): five
slots `eMailDestinationCooperator1`…`5` — the written list is **the
whole state**, unused slots are cleared, no stale address survives —
and `cipheredPersonalData`, a single block bounded by the statutes to
**fewer than 512 characters**. The `shared_directory.py` module ships
the whole chain: compact JSON, **two-letter codes** for groups and role
(the twelve group names alone outweigh the entire bound), `zlib`, then
Fernet on the session secret — a maximal member measures **440
characters**, proving the future version can rely on the bound; an
oversized block is refused rather than written truncated. Noted for the
real feature: a purged Cooperator's address may survive in other
members' slots.

**The Identity Recovery Code** (#127): the `identityRecoveryCode`
attribute contains "a string of 64 characters" — which is, a design
choice documented in `identity_recovery.py`, the **SHA-256 hex digest**
of the code's canonical form: the secret itself is **never** stored.
The code handed to the member — five groups of five characters from an
alphabet without ambiguous glyphs (~122 bits) — copies reliably by
hand; canonicalisation forgives case, spaces and hyphens, and
verification is constant-time.
