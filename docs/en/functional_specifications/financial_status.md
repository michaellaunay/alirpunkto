# The financial status of a Cooperator

Covers issues #75 (tracking of the financial facts), #148 (transitions
between Dynamic Groups), #267 (update on payment) and #269 (propagation
to the SSO).

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
the commercial site calls `tools/update_cooperator.py`, which opens an
**administrator** session on AlirPunkto and submits the new facts to the
dedicated endpoint `POST /update_contribution`:

| Parameter | Role |
|---|---|
| `oid` | the Cooperator's number (required) |
| `number_shares_owned` | new number of shares (integer ≥ 0) |
| `date_end_validity_yearly_contribution` | new end date, `YYYY-MM-DD` |
| `csrf_token` | the session's token (global CSRF guard) |

At least one of the two facts is required; **no other field is
accepted** — another member's card stays read-only for everyone,
administrators included (#149). The answer is JSON: `status`,
`updated_fields`, both facts after the write and `groups`, the member's
Dynamic Groups **after** the transition.

The effect is **immediate**: the directory write triggers the group
synchroniser (#148) then the propagation to Keycloak (#269), so the
Cooperator gets their rights back on every application without waiting
for their next login nor for the daily scan.

Refusals (JSON `{"status": "error", "error": …}`): `405` outside `POST`,
`401` without a session, `403` when the session is not an
administrator's, `400` missing or invalid parameter (`fields` names the
culprits), `404` unknown member, `409` when the member is not a
Cooperator, `502` when the directory refuses the write.

## The script

```
python tools/update_cooperator.py --env shop.env --oid <uuid> \
    --number-shares 1 --validity-date 2027-06-30 \
    --base_url https://access.example.coop
```

The script logs in, reads the CSRF token from the member directory page,
posts the facts and **fails loudly** (`RuntimeError`) on any refusal — a
payment that did not reach the directory must never go unnoticed again.

## The daily scan (#148, #269)

The rest of the time, the daily maintenance turns the calendar into
transitions (expired contribution) and tells the SSO; see
[09_periodic_tasks](../architecture/09_periodic_tasks.md).
