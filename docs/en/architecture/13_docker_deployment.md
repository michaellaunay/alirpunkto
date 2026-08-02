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

## Blockers lifted (external audits, fourth → eleventh passes)

The three defects that stopped the stack before `pserve` (a check on
the removed `setup.py`, the unknown Waitress option
`use_forwarded_proto`, a loopback listen with a `trusted_proxy`
unsuited to the compose network) are **fixed and locked**: the stack
has its own server configuration, derived at runtime by
`docker/apply_server_overrides.py` whenever `PYRAMID_LISTEN` /
`PYRAMID_TRUSTED_PROXY` are set (compose sets them by default), and an
end-to-end **Compose smoke test** proves the Apache → Waitress path
down to the real client address seen by the login limiter. The image
is **multi-stage**: the venv installs the runtime lock alone in
hash-checking mode with `--only-binary=:all:` (three named pure sdists
excepted — any future sdist fails the build explicitly), the
application is installed **as a wheel** (file-for-file parity proven),
and the final stage ships neither compiler nor source tree — an
**explicit copy allowlist** replaces `COPY .`, which incidentally
repaired a latent break: the override helper, excluded by
`.dockerignore`, never reached the image. The four bases are pinned by
digest, with an **opt-in APT snapshot** (`ALIRPUNKTO_UBUNTU_SNAPSHOT`)
for strict reproducibility; the test stack bind-mounts its lock
(`requirements-test.lock`) and `test.ini` read-only. The tenth pass
reopened the P0 — a duplicate `args:` key on the LDAP service
(introduced by the image-finishing train itself) and two LDIF
generator callers left on the old contract — closed again by train
0078: a **shared emitter** `docker/ldif_records.sh` sourced by
`init.sh`, `init_test.sh` and the smoke workflow, and a **validation
gate** `compose config --quiet` on both files before any build. Full
chronicle:
`docs/en/audits/20260801_external_chatgpt_audit_alirpunkto_4th_pass.md`,
`…_6th_pass.md`, `20260802_…_8th_pass.md`, `…_10th_pass.md` and
`…_11th_pass.md` — the 5th, 7th and 9th, transmitted after the fact,
are filed there too.

## Containerless deployment

Bare-metal deployment (single host) is supported by the same tooling:
`tools/ldap_provision.py --install-type host` (schema, accounts), the
host's Postfix and slapd, `pserve` for the application.
