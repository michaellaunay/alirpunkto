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

Two periodic treatments now exist as **callable utility functions** — the
repository still ships no application scheduler, and that is a choice:
scheduling belongs to operations (2026-07-30).

## Post-Quarantine purge

`utils.purge_unsubscribed_members(request, now=None)` walks the
`UNSUBSCRIBED` members whose `data.date_erasure_all_data` is due: the LDAP
entry is deleted, the personal data erased (only **the pseudonym, the
departure date and the reason** remain), the member moves to `DELETED`,
and the former member is informed by e-mail (#54). Idempotent; returns the
purged oids.

## Daily dynamic-group scan

`dynamic_groups.daily_group_scan(request, today=None)` re-synchronises
every member of the managed groups: it is what turns **calendar time** (an
expired or renewed yearly contribution) into transitions (#148).
Idempotent; returns the oids whose groups changed.

## Wiring

Both are called together, once a day, from `cron` (or a systemd timer)
through a small script using `pyramid.paster.bootstrap` with the
instance's `production.ini` — for example:

```python
from pyramid.paster import bootstrap
from alirpunkto.utils import purge_unsubscribed_members
from alirpunkto.dynamic_groups import daily_group_scan

with bootstrap("production.ini") as env:
    request = env["request"]
    purge_unsubscribed_members(request)
    daily_group_scan(request)
```

The expiry of unconfirmed resignation requests needs no task: it is
**lazy** (checked on the profile page and when the link is clicked).

## Known limits and envisaged evolution

Still no purge of stale candidatures and no automatic retry of failed
e-mails: those operations remain manual. A console entry point
(`console_scripts`) packaging the script above is the natural evolution;
the decision will be recorded in
[architecture_decisions](architecture_decisions.md) once settled.
