# The financial status of a Cooperator

Covers issues #75 (tracking of the financial facts), #148 (transitions
between Dynamic Groups), #267 (update on payment) and #269 (propagation
to the SSO), and the external audit of 2026-10-24 (train 0117).

## The two facts

For every Cooperator the directory carries two attributes that issue #75
entrusts to the **online commercial site**:

- `numberSharesOwned` — the number of shares owned (non-negative
  integer, `0` at registration);
- `dateEndValidityYearlyContribution` — the end of validity of the
  yearly contribution (a past date at registration).

Together with the sanction and the role, these two facts determine the
member's Dynamic Group (#148): shares plus a valid contribution make a
**full Cooperator** (`cooperatorsGroup`); an expired contribution sends
them back among the candidates awaiting their contribution.

## The update on payment (#267)

As soon as a Cooperator pays their contribution (or subscribes shares),
the commercial site calls the client script (`tools/update_cooperator.py`,
or its PHP port kept by the shop), which opens an **administrator**
session on AlirPunkto and submits the new facts to the dedicated endpoint
`POST /update_contribution`:

| Parameter | Role |
|---|---|
| `oid` | the Cooperator's number (required) |
| `number_shares_owned` | new number of shares (integer from 0 to 1 000 000 — `0` is a value, the ceiling is a guard against overflows and misplaced amounts, enforced by the server and the clients alike) |
| `date_end_validity_yearly_contribution` | new end date, `YYYY-MM-DD` |
| `csrf_token` | the session's token (global CSRF guard) |

At least one of the two facts is required; **no other field is
accepted** — another member's card stays read-only for everyone,
administrators included (#149).

### The three outcomes of a payment

A payment is not "two attributes written": it is a Cooperator who gets
their rights back. The answer therefore reports three steps, not one:

| Field | Values | Meaning |
|---|---|---|
| `financial_update` | `success`, `unchanged` | the facts in the directory (`unchanged`: they were already there) |
| `groups_sync` | `success`, `error` | the Dynamic Groups converged (#148) |
| `keycloak_sync` | `success`, `error` | the change reached Keycloak (#269) |
| `groups` | list, or `null` | the member's Dynamic Groups **after** the transition; `null` when the directory could not be read back (never `[]` for that) |

The overall `status` is `success` only when all three steps are, and
`partial` — still HTTP 200, because the facts **are** recorded — when
the groups or Keycloak lag behind or the groups cannot be read back. The
answer also carries `oid`, `updated_fields` and both facts after the
write, so the caller can check that the portal applied **its** values to
**its** member.

A `partial` answer is **retryable**: the same call again writes nothing
(`financial_update: unchanged`) but drives the group synchroniser and the
Keycloak propagation once more, so the retry can repair what lagged. The
daily scan (#148, #269) is the last safety net.

Refusals (JSON `{"status": "error", "error": …}`): `405` outside `POST`,
`401` without a session, `403` when the session is not an
administrator's, `400` missing or invalid parameter (`fields` names the
culprits) or CSRF refused (token, or `Origin`/`Referer` over HTTPS),
`404` unknown member, `409` when the member is not a Cooperator, `502`
when the directory refuses the write.

## The script

```
python tools/update_cooperator.py --env shop.env --oid <uuid> \
    --number-shares 1 --validity-date 2027-06-30 \
    --base_url https://access.example.coop
```

What the wire wants, and what the script does:

1. `GET /login` opens the session and carries its `csrf_token`;
2. `POST /login` with the credentials, that token and an `Origin` (and
   `Referer`) header naming the portal — the global CSRF guard answers
   400 to a bare POST, before the credentials are even looked at;
3. `GET /modify_member`: a logged-in session renders the member
   directory with its `csrf_token`, an anonymous one is sent back to the
   home page without it — the login check, and the token of step 4;
4. `POST /update_contribution` with the facts, the token and the same
   headers; every call has a connect/read timeout.

**Exit code 0 means, and only means**: the portal confirmed that the
facts are in the directory with the values requested (OID and values
checked against the answer), that the Dynamic Groups converged and that
the Keycloak synchronisation ran without reported failure — the client
requires `financial_update`, `groups_sync` and `keycloak_sync` to say so
and `groups` to be a list; a bare `success` is not trusted. It does not
prove that every client application has already refreshed its own
authorisations. On the server side those indicators are honest since
trains 0119 and 0120: a refused membership write, or an unreadable
group side, makes the group synchroniser answer failure without writing,
and only a Keycloak `SynchronizationResult` of known shape with
`failed = 0` is a propagation. Any
refusal, mismatch or `partial` answer exits 1 with the portal's reason —
a payment that did not restore the rights must never go unnoticed. A
call that asks for no change at all is an error too, never a silent
exit 0; `--base_url` must be the portal's origin (`scheme://host`).

The unit tests of the script are backed by `tests/test_update_contribution_wire.py`,
which runs its `login` and `modify_member` through the real Pyramid
pipeline (HTTPS scheme, secure cookie, CSRF guard) with only the LDAP
and Keycloak edges stubbed.

## The daily scan (#148, #269)

The rest of the time, the daily maintenance turns the calendar into
transitions (expired contribution) and tells the SSO; see
[09_periodic_tasks](../architecture/09_periodic_tasks.md).

## Known limit — out-of-order payments

The endpoint receives an **absolute** value, not a payment event: two
notifications of the same Cooperator processed out of order leave the
older total in the directory. A commercial-operation identifier with a
monotonic sequence, letting the portal refuse a stale state, is the
medium-term answer (external audit of 2026-10-24, §4); it is not in
scope of train 0117.
