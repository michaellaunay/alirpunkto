# Unsubscription (member resignation)

Implements the historical scenario
[Démissionner](../../fr/specifications_historiques/Scénarios/Démissionner.md)
(French source).

## Nominal path

1. From **their own** profile page, the member follows "Deactivate my
   account".
2. The page lists the **implications**: no more login to the platform nor
   to the connected applications; data kept during the **Quarantine**
   (180 days by default, §3.4 of the statutes, tunable via
   `QUARANTINE_PERIOD_DAYS`) then erased, only the pseudonym, the date
   and the reason being retained; nothing happens without the
   confirmation link.
3. On form confirmation, the member enters `PENDING_UNSUBSCRIPTION` and
   receives an e-mail whose **link is the real confirmation** (valid 7
   days). If sending fails, the state is rolled back.
4. When the link is followed: state `UNSUBSCRIBED`, account
   **deactivated** in the directory (the entry is kept — the pseudonym
   and the identity stay reserved through the Quarantine), erasure date
   scheduled, farewell e-mail, session ended. Login is refused from then
   on.
5. After the Quarantine, the **purge** (periodic task, see
   [09_periodic_tasks](../architecture/09_periodic_tasks.md)) erases
   everything but the pseudonym, the date and the reason, deletes the
   directory entry and **informs the former member** that the data was
   indeed erased.

## Alternative scenarios

- **Cancellation**: while the request is pending, the profile offers
  "Cancel my deactivation request" — the previous state is restored.
- **Expiry**: a request unconfirmed within 7 days expires by itself
  (lazily checked on the profile and at link time); the account stays
  active.
- **Link re-clicked**: idempotent — the page simply confirms the account
  is deactivated.

## Guarantees

- A deactivated account can no longer log in (authentication guard).
- A resigned member's identity cannot re-register during the Quarantine
  (#54).
- The member leaves every dynamic group upon deactivation (#148).
