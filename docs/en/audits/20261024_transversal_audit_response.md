# Answer to the transversal audit of 24 October 2026 — trains 0122 to 0124

**Date**: 2026-10-24 · **Audit**: transversal audit of the project (ChatGPT, frozen commit `6f50670b`, train 0119; filed in French as `docs/fr/audits/20261024_audit_complet_alirpunkto.md`) · **Answer**: Claude (development assistant) · **Decision**: the three P0s and the circumscribed P1s are handled in three trains; four structural findings stay open and are listed below with their reason.

## Disposition per finding

| Ref. | Priority | Finding (summary) | Disposition | Train |
|---|---|---|---|---|
| A01 | P0 | Deactivation bypassable through recovery, `isActive` never read, session re-armed by the home page | **Fixed**: `is_account_closed` applied to the LDAP login, the SSO callback, the reset request, the reset link and the armed session; `isActive` loaded and typed; home requires the flag and the user payload | 0122 |
| A02 | P0 | Partial LDAP refresh: financial facts and `isActive` not refreshed; `get_member_by_oid(update=True)` answered `None` | **Fixed**: every directory attribute re-read typed and applied; absent ≠ empty (an absent fact is `None`, an absent identity attribute leaves the cache alone); the loaded member is returned; cache/directory divergence tested through the real endpoint | 0122 |
| A03 | P0 | Internal fields settable from the registration POST | **Fixed**: closed list `PUBLIC_REGISTRATION_FIELDS`; shares, mark, activity, role, IBAN, dates come from the model | 0122 |
| A04 | P1 | SSO callback without `state`, algorithm read from the header, issuer unchecked | **Fixed**: one-time, time-stamped `state` and PKCE S256 verifier; fixed algorithm list; issuer verified | 0124 |
| A05 | P1 | Link capabilities neither specialised nor consumed | **Fixed**: `link_matches_pending_action` (seed + purpose) on the reset, the address change and the resignation; reset session bound to the seed; link consumed after use; the resignation mints its own seed | 0124 |
| A06 | P1 | Purge: `TypeError` on a real `Member`, delete result ignored, history keeping the data | **Fixed**: `Member.erase_personal_data`, delete checked (`noSuchObject` resumes an interrupted pass), history reset; tests on a real `Member` | 0123 |
| A07 | P1 | Password branch triggered by other fields | **Fixed**: `field == "password"`, one run; tested through the real view | 0123 |
| A08 | P1 | Local transitions before external effects | **Fixed for the two flows named**: resignation and address change write the directory first and stay retryable on refusal. **Not done**: a general persistent effects queue ("outbox") | 0124 |
| A09 | P1 | Failed group reads taken as an empty set | **Fixed by train 0120** (`GroupSideUnreadable`, `read_member_groups`); the two-sided convergence re-read after writes remains to do | 0120 |
| A10 | P1 | `ignored` accepted; daily retry not guaranteed | **Fixed**: `ignored` = not propagated; persistent marker `var/keycloak_sync_pending` retried by the daily scan even without movement | 0123 |
| A11 | P1 | `Members` singleton shared across connections | **Not handled**: resolution through `request.root` is a refactoring that needs a two-connection concurrency test and touches every connection-less call. To be scoped separately |  |
| A12 | P1 cond. | POST and e-mail bodies in clear under DEBUG | **Fixed**: field names only, e-mail metadata only; the encrypted secret diagnosis stays as the maintainer decided | 0123 |
| A13 | P1 | Backup: wrong default path, success on an incomplete archive | **Fixed**: `production.ini` path, failure when a store is missing unless `ALLOW_PARTIAL=1`, SHA-256 manifest, archive verified before pruning, `umask 077`. **Not done**: `repozo`, encryption, restore drill (operations) | 0123 |
| A14 | P1 | Out-of-order payment notifications | **Not handled**: needs an operation identifier and a sequence on the commercial site's side; limit documented in `financial_status.md` |  |
| A15 | P1 | Python client: URL priority, HTTP, redirects, cookies | **Fixed**: `--base_url` without default (CLI > `.env` > default), https required unless local `--allow-http`, `allow_redirects=False`, origin of the 302 checked, cookies at 0600 | 0123 |
| A16 | P2 | Provider management without a check on the target's type | **Fixed**: the target must be a `PROVIDER` | 0123 |
| A17 | P2 | LDAP budgets, pagination | **Not handled**: real load not measured; to be scoped with metrics |  |
| A18 | P2 | Insufficient boundary tests | **Partly**: the three trains add tests on real `Member`s, the real profile view, the real loader on a mock directory, the real endpoint, the real Pyramid stack (0117); the test-LDAP slice and the isolated Keycloak journey remain to build | 0122-0124 |

## Proof

- 0122: 21 tests red on the previous tree, green after; suite 1235, coverage 75.37 %.
- 0123: 16 tests red then green; suite 1250, coverage 75.44 %.
- 0124: 20 tests red then green; suite 1269, coverage 76.39 %.
- ruff and bandit `-ll` green on every train; no dependency changed.

## What stays open

A11 (singleton), A14 (payment sequencing), A17 (LDAP budgets), the effects queue of A08, the convergence re-read of A09, and the operational items of A13. Each needs either a maintainer decision, an external partner, or a measurement on the real instance.
