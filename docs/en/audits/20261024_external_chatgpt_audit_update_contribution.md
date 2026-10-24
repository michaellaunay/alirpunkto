# External ChatGPT audit of 24 October 2026 — payment client and `/update_contribution`

**Date**: 2026-10-24 · **Auditor**: ChatGPT (counter-review requested by Michaël) · **Subject**: the payment software's PHP script (`modify_contributor_alirpunkto.php`, version 0.3 ported the day before to `/update_contribution`), compared with the code of `master` (`34a224f7`) and with `tools/update_cooperator.py` · **Auditor's verdict**: functionally consistent, not yet robust enough for unattended financial use · **Answer**: train 0117 (repository) and version 0.4 of the PHP script (outside the repository).

## Findings and disposition

| Ref. | Finding | Priority | Disposition |
|---|---|---|---|
| A1 | Exit 0 when no change is requested | Critical | **Fixed** (PHP 0.4 and Python tool): refused before any login, exit 1 |
| A2 | `update_ldap_member` ignores the results of `sync_member_groups` (None on failure) and `notify_keycloak_of_directory_change` (False); `get_member_groups` answers `set()` on a read failure — a `success` answer does not guarantee the rights | Critical | **Fixed** server side: `propagate_member_change` reports `groups_sync` and `keycloak_sync`; the answer carries `financial_update`, those two statuses, `status: partial` when one lags, `groups: null` when the directory cannot be read back; a repeat call with unchanged facts drives the propagation again to repair. Both clients treat `partial` as a failure to retry |
| A3 | The client checks neither the OID nor the values that come back | High | **Fixed** (PHP 0.4 and Python tool): OID and every fact sent compared with the answer |
| A4 | No HTTP timeout; unbounded redirects | High | **Fixed**: connect and read timeouts in both clients; in PHP, redirects capped, protocols restricted, destination host checked |
| A5 | Temporary cookie file kept after use | High | **Fixed** (PHP 0.4): file at 0600, removed in the `finally` unless `--cookie` is explicit |
| A6 | CSRF tokens written in verbose mode | Medium | **Fixed** (PHP 0.4): no token and no full body in the logs any more |
| A7 | HTTP status of the login not inspected: a CSRF 400 became "invalid credentials" | Medium | **Fixed** in both clients: a 4xx on the login POST is named for what it is |
| A8 | `.env` mandatory even with credentials on the command line; passwords trimmed; home-made `.env` parser | Medium | **Partly**: `.env` optional when the credentials are given; the password is no longer trimmed; the parser only strips matching delimiting quotes. A third-party dotenv parser on the PHP side is the shop's call |
| §3 | `tools/update_cooperator.py` logged in without token nor `Origin` (400 on the wire); its tests ran on a `MagicMock` | Confirmed | **Fixed**: sequence GET /login → POST with token and `Origin` → GET /modify_member; `tests/test_update_contribution_wire.py` runs `login` and `modify_member` through the real Pyramid stack (HTTPS, secure cookie, CSRF guard) |
| §4 | Absolute share count: two out-of-order notifications leave the older total | Medium term | **Not handled**; limit documented in `financial_status.md`, to be worked out with the shop (operation identifier, monotonic sequence) |
| §5 | `Throwable` rather than `Exception`, real program name, validation of `--base_url` (origin without path), `curl` and `dom` extensions | Minor | **Fixed** (PHP 0.4): `Throwable`, `$argv[0]`, origin check, extension check at start-up |

## Proof of train 0117

- New and reworked tests on the previous state of the code (original server and tool, new tests): 30 red and 6 errors out of 39; after: 39 green.
- The most telling red: `test_the_script_login_posts_the_login_page_token_with_the_origin` and, on the wire, `test_a_bare_login_post_is_refused_by_the_csrf_guard` (400 "Bad CSRF token"); without an `Origin` header over HTTPS, 400 "Bad CSRF Origin", verified by a WebTest probe on 24 October.
- Full suite, ruff, bandit: see the train's commit message.

## Second pass (same day) — PHP 0.4 and train 0117 re-read

The auditor validates the syntax of PHP 0.4 (PHP 8.4.24), the architecture, the CSRF sequence and the new `success`/`partial` contract, and raises six new points.

| Ref. | Finding | Priority | Disposition |
|---|---|---|---|
| P1 | Under PHP 8, `curl_close()` is a no-op: the cookie jar is rewritten when the handle is destroyed, after the `unlink` | High | **Fixed** (PHP 0.4.1): `unset($curl)` before the removal, cleanup in a `finally` that wraps `initCurl`, file removed when `chmod` fails |
| P2 | `assertStayedOnPortal` checked after redirects had been followed; an external 307 would have replayed the credentials POST | High | **Fixed** (PHP 0.4.1): no automatic following at all; the login POST's 302 is recognised without being followed, any other 3xx is an error; scheme, host and port compared; HTTP refused unless `--allow-http` |
| P3 | The client accepted a `success` without indicators, or one contradicted by `groups_sync: error` | High | **Fixed** in both clients: `financial_update`, `groups_sync`, `keycloak_sync` and a `groups` list required |
| P4 | `ctype_digit` then `(int)` silently saturated at `PHP_INT_MAX` | Medium | **Fixed** in both clients: business ceiling of one million shares, overflow refused |
| P5 | `sync_member_groups` answered the target even when a membership write had failed: `groups_sync: success` wrongly | Critical | **Fixed** (train 0119): every `_checked_modify` failure is remembered, the function answers `None`; tests on refused grant, refused revocation and exception |
| P6 | `propagate_ldap_changes_to_keycloak` answered `True` without reading the `failed` counter of the `SynchronizationResult` | Critical | **Fixed** (train 0119): `sync_failed` reads `failed` and `status`; a failing provider makes the propagation false, the others are still synchronised |

Limit recalled by the auditor and kept: a successful propagation proves the mechanism ran, not that every application has already refreshed its rights.

## Third pass (same day) — PHP 0.4.1 and train 0119 re-read

The auditor confirms P1 to P6 fixed (PHP 8.4 syntax checked, P5 and P6 re-read on `master`) and raises six new points.

| Ref. | Finding | Priority | Disposition |
|---|---|---|---|
| P7 | `getopt()` silently ignores an unknown, misspelt or valueless option: `--validitydate` let a half-applied payment through with exit 0 | P0 | **Fixed** (PHP 0.4.2): strict home-made `argv` parser — unknown options, missing values, duplicates and positional arguments refused |
| P8 | `--allow-http` accepted any remote host | High | **Fixed** (PHP 0.4.2): restricted to `localhost`, `127.0.0.1` and `::1` |
| P9 | One-million share ceiling in the clients, absent from the server contract | High | **Fixed** (train 0120): `MAX_SHARES` in `update_contribution.py`, `400 invalid_value` above it; a test checks client/server equality. The figure remains to be validated by the cooperative's rules |
| P10 | `trim` of unquoted `.env` values; password visible in the process list through `--password`; persistent `--cookie` without a permission check | Medium | **Partly** (PHP 0.4.2): the help documents quoting and recommends `.env` over `--password`; an existing `--cookie` readable by others is refused, a new one is created at 0600. The `.env` parser stays minimal |
| P11 | `--help` required the `curl` and `dom` extensions | Minor | **Fixed** (PHP 0.4.2): arguments parsed before the extension check |
| P12 | `_group_side_groups` continued on a read exception, the group taken as empty: a membership to revoke could go unseen and convergence be reported | High | **Fixed** (train 0120): an unreadable read raises `GroupSideUnreadable`, `sync_member_groups` answers `None` without writing; test on a revocation with an unreadable group side |
| — | `sync_failed` took a Keycloak answer of unknown shape as clean | Medium | **Fixed** (train 0120): only an object carrying `failed` or `status` is recognised, anything else is a failure |
| — | Date `0000-01-01` accepted by PHP, refused by Python | Minor | **Fixed** in both clients: year between 1900 and 2199 |
| — | Wording of exit code 0: "confirmation of the synchronisation operations", not "rights restored everywhere" | Precision | **Reworded** in both clients' headers and in the specification |

## Log

- 2026-10-24: audit received, A2 verified in `utils.py`, `dynamic_groups.py` and `views/update_contribution.py` (confirmed), train 0117 and PHP script version 0.4 executed, this note filed.
- 2026-10-24 (second pass): P5 and P6 confirmed by reading, train 0119 and PHP 0.4.1.
- 2026-10-24 (third pass): P7 to P12, train 0120 and PHP 0.4.2.
