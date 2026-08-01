# Docker deployment

> Status: current documentation — a **synthesis**. The reference document,
> maintained along the audits, is `docker/README.md`; the local test stack
> is described in `docker/README_TEST_LOCAL.md`. This document does not
> duplicate their procedures.

## Services

The `docker/docker-compose.yaml` stack comprises four services:

- **apache2**: HTTPS front end (Let's Encrypt certificates, dedicated
  volumes);
- **pyramid**: the AlirPunkto application (Waitress);
- **ldap**: OpenLDAP, with the `alirpunktoPerson` schema loaded at
  initialisation;
- **postfix**: hardened outbound relay (DKIM, anti-relay, port 25
  unpublished).

Keycloak is **not** part of the stack: it is an optional external service,
configured through the `KEYCLOAK_*` variables of the `.env`.

## Initialisation and seeding

`docker/init.sh` prepares the environment: variable derivation, generation
of `docker/initials_users.generated.ldif` (bootstrap accounts) through
`docker/generate_ldif.py`, schema installation. The `start_*.sh` scripts
start each service. The seed file is **interchangeable** with the one
produced by `tools/ldap_provision.py` from an existing directory
(migration of a live instance).

## Data and backups

Data live in named volumes (`alirpunkto_ldap_*`, `alirpunkto_pyramid_var`,
`alirpunkto_postfix_*`, Apache certificates). `docker/backup.sh` saves
configuration and data; procedure and restore in `docker/README.md`.

## Known blockers (external audit, fourth pass — 2026-08-01)

The stack described above **does not start as it stands**: three
simple defects, invisible to unit tests, stop it before `pserve`. The
`start_pyramid.sh`/`start_test_pyramid.sh` scripts require a
`setup.py` removed in favour of `pyproject.toml`; `production.ini`
carries the `use_forwarded_proto` option, unknown to Waitress 3
(rejection verified as a `ValueError`); and `listen = localhost:6543`
is unreachable from the Apache container — which, as seen by Waitress,
is not `127.0.0.1` either (`trusted_proxy`), which would fold the
login limiter onto a single address. The internal healthcheck, which
queries the loopback, can stay green all the while. These values
remain the right ones for the bare-host deployment below; the fix (P0
patch) gives the stack its own server configuration and adds the
Compose smoke test that would have caught all three. The image, for
its part, installs the full lock — test and quality tools included —
after an out-of-lock upgrade: the lock split and the multi-stage image
are P1. Detail, counter-review and plan:
`docs/en/audits/20260801_external_chatgpt_audit_alirpunkto_4th_pass.md`.

## Containerless deployment

Bare-metal deployment (single host) is supported by the same tooling:
`tools/ldap_provision.py --install-type host` (schema, accounts), the
host's Postfix and slapd, `pserve` for the application.
