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

## Containerless deployment

Bare-metal deployment (single host) is supported by the same tooling:
`tools/ldap_provision.py --install-type host` (schema, accounts), the
host's Postfix and slapd, `pserve` for the application.
