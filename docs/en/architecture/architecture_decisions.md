# Architecture decisions

> Status: current register. Format: context, decision, consequences.
> A "transitional" decision is assumed but meant to evolve; "proposed" is
> not implemented yet.

## ADR-001 — Pyramid (adopted)

A light, mature web framework with explicit routing and an integrated
transactional ecosystem (`pyramid_tm`, `pyramid_retry`, `pyramid_zodbconn`,
`pyramid_mailer`). Consequence: configuration is concentrated in
`alirpunkto/__init__.py`.

## ADR-002 — ZODB (adopted)

Business objects (`Member`, `Candidature`) are Python graphs persisted as
such, with native transactions and no ORM. Consequences: single-writer
`FileStorage`; offline tools must not write while the application runs;
the ZODB is rebuildable from LDAP.

## ADR-003 — OpenLDAP as the identity referential (adopted)

Accounts, passwords and groups live in the directory, interoperable with
Keycloak and the third-party applications. Consequence: two referentials
(LDAP authoritative for identity, ZODB for the application), synchronised
by `update_member_from_ldap`.

## ADR-004 — Dedicated LDAP schema (adopted)

`alirpunktoPerson` carries typed business attributes rather than a
catch-all field. Consequence: the schema has versions; the idempotent
upgrade tooling (`tools/ldap_provision.py --update-schema`) and the read
tolerance (`schema_safe_attributes`) follow from it.

## ADR-005 — Chameleon / TAL / METAL (adopted)

Continuity with the team's Zope/Plone experience; `layout.pt` factors the
structure through METAL. Consequence: templates close to HTML, a gentle
entry curve for contributors coming from Plone.

## ADR-006 — Local Postfix (adopted)

A controlled relay (DKIM/SPF/DMARC, anti-relay) rather than a third-party
service. Consequence: deliverability is the stack's responsibility; the
hardening is audited and documented in `docker/README.md`.

## ADR-007 — Docker (adopted)

Reproducible deployment and a local, offline test stack. Consequence: two
composes (production, test), initialisation scripts, persistent named
volumes.

## ADR-008 — Testing strategy (adopted)

LDAP mocked by default, the Docker stack for integration, and above all:
**every audit finding or field incident is closed by dedicated, dated
tests**. Consequence: the suite is also the journal of forbidden
regressions.

## ADR-009 — Current permission model (transitional)

Access checks inside the views + fine-grained per-attribute matrix
(`model_permissions.py`); Pyramid ACL reduced to `group:admins`. Assumed
while the overhaul (ADR-010) is pending.

## ADR-010 — ACL overhaul as a class hierarchy (proposed)

Target: derive the `__acl__` and the views' `permission=` from the same
source as the per-attribute matrix, through a hierarchy of resource
classes. Status: decided in principle, not implemented.

## ADR-011 — SSO tokens in the session: refresh only (adopted, 2026-07-08)

The session cookie (4093 bytes) only stores the refresh token and its
expiry (`utils.store_sso_tokens`); the *access token*, never read back and
inflated by group claims, is excluded. Complementary target (proposed): a
server-side session, which would lift the size constraint and keep the
token off the client machine.
