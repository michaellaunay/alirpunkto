# Periodic tasks

> Status: current documentation.
> Modules: `alirpunkto/maintenance.py`, `alirpunkto/dynamic_groups.py`,
> `alirpunkto/utils.py` (`purge_unsubscribed_members`),
> `alirpunkto/keycloak_sync.py`.

## Deadlines checked at access time

Some deadlines are checked **at access time**, with no task:

- the SSO refresh token expiry is checked by `home_view` at each visit
  (see [05_authentication](05_authentication.md));
- candidature states only move under a user's or a verifier's action;
- the expiry of unconfirmed resignation requests is **lazy** (checked on
  the profile page and when the link is clicked).

## Scheduled tasks outside the application

The Docker stack takes care of the recurring work that does not touch
the application data:

- **backups**: `docker/backup.sh` saves configuration and data (directory,
  ZODB); its scheduling and the restore procedure are described in
  `docker/README.md` ("Backups");
- TLS renewal and Postfix supervision also belong to the stack (2026
  Docker audit).

## Pending SSO propagation (transversal audit of 2026-10-24, A10)

A Keycloak propagation that fails — unreachable server, a provider
answering `failed > 0` or `ignored` — leaves a marker file
(`var/keycloak_sync_pending`, overridable with
`KEYCLOAK_SYNC_PENDING_MARKER`). The daily scan calls Keycloak again
while that marker exists, even on a day when no member changed group;
a successful propagation removes it. Without it, a directory that had
converged while Keycloak was down was never re-propagated until the next
unrelated change.

## The daily maintenance inside the application (#148, #269)

Issue #148 asks AlirPunkto to **scan the directory every day** (an
expired contribution leaves `cooperatorsGroup`, an ended quarantine
erases a resigned member) and issue #269 adds that the members whose
Dynamic Group changed must reach the SSO infrastructure **the same day**.
Both treatments existed as callable functions, but nothing called them:
the scheduling had been delegated to an external `cron`, which cannot
work with the shipped stack — the ZODB `FileStorage` is locked by the
running application, a second process opening it fails
(`tools/run_upgrades.py` says as much: stop the application first).

The maintenance therefore runs **inside the application process**
(`alirpunkto/maintenance.py`), in a daemon thread started by the app
factory when the configuration asks for it:

```ini
daily_maintenance.enabled = true      ; false in development.ini and testing.ini
daily_maintenance.initial_delay = 120 ; first pass, seconds after start-up
daily_maintenance.interval = 86400    ; then one pass a day
```

Every pass (`run_daily_maintenance`):

1. **post-quarantine purge** — `utils.purge_unsubscribed_members` walks
   the `UNSUBSCRIBED` members whose `data.date_erasure_all_data` is due:
   the LDAP entry is deleted, the personal data erased (only **the
   pseudonym, the departure date and the reason** remain), the member
   moves to `DELETED`, and the former member is informed by e-mail (#54).
   The thread works on the `members` mapping of **its own ZODB
   connection** (`members=` parameter) without rebinding the `Members`
   singleton, which belongs to the request threads, and commits its own
   transaction;
2. **dynamic-group scan** — `dynamic_groups.daily_group_scan`
   re-synchronises every member of the managed groups: it is what turns
   **calendar time** (an expired or renewed yearly contribution) into
   transitions (#148);
3. **SSO propagation** — when at least one member changed group, the scan
   asks Keycloak to re-import the changed entries
   (`keycloak_sync.propagate_ldap_changes_to_keycloak`, see
   [05_authentication](05_authentication.md)).

Everything is idempotent: a restart that repeats a pass is harmless, a
failing pass only logs and the next one retries. Waitress being a single
multi-threaded process, there is one maintenance thread.

## Manual run

With the application **stopped** (ZODB lock), an operator can trigger a
pass from a Python shell:

```python
from pyramid.paster import bootstrap
from alirpunkto.maintenance import run_daily_maintenance

with bootstrap("production.ini") as env:
    print(run_daily_maintenance(env["registry"]))
```

## Known limits and envisaged evolution

Still no purge of stale candidatures and no automatic retry of failed
e-mails: those operations remain manual. The in-process thread decision
is recorded in [architecture_decisions](architecture_decisions.md)
(ADR-012).
