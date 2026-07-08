# Periodic tasks

> Status: current documentation.

## Current state: no application scheduler

The application **embeds no scheduler**: the 2023 `@TODO` of the design
journal (integrate `pyramid_scheduler`) was never carried out. Deadlines
are checked **at access time**:

- the SSO refresh token expiry is checked by `home_view` at each visit
  (see [05_authentication](05_authentication.md));
- candidature states only move under a user's or a verifier's action.

## Scheduled tasks outside the application

The Docker stack takes care of the recurring work:

- **backups**: `docker/backup.sh` saves configuration and data (directory,
  ZODB); its scheduling and the restore procedure are described in
  `docker/README.md` ("Backups");
- TLS renewal and Postfix supervision also belong to the stack (2026
  Docker audit).

## Known limits and envisaged evolution

Without an application scheduler there is no purge of stale candidatures,
no automatic retry of failed e-mails and no processing of
`dateErasureAllData` (right to erasure): these operations are manual.
Integrating a scheduler (or dedicated `cron` entries calling `tools/`
scripts) remains the target; the decision will be recorded in
[architecture_decisions](architecture_decisions.md) once settled.
