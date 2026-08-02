# Security

> Status: current documentation — a synthesis; the detailed findings and
> fixes are in `docs/fr/audits/` (code reviews and Docker/Postfix audits,
> 2026, French).

## Application protections in force

- **Global CSRF**: `set_default_csrf_options(require_csrf=True)` — every
  view is protected, forms carry the token.
- **Sessions**: signed cookie, `httponly`, `secure`, `SameSite=Lax`;
  minimal content, the SSO *access token* is never stored (cookie budget,
  `tests/test_session_cookie_budget.py`).
- **Passwords**: hashed `{SSHA}` on every LDAP write
  (`secret_manager.make_ldap_password`), never stored in cleartext in the
  ZODB (`secure_password_fields`, purge on acceptance) — finding 1.3 of the
  code review, locked by `tests/test_security_1_3_password_hashing.py`.
  The tool `tools/purge_zodb_cleartext_passwords.py` sanitises historical
  stores.
- **Secrets**: read from the environment/`.env` through
  `alirpunkto/secret_manager.py` (session key derived from `SECRET_KEY`);
  no secret hard-coded. The `.env` is loaded **exactly once** at
  start-up; every later read goes through `os.getenv` — the process's
  real environment takes precedence, no `get_key()` re-reads the file
  at run time.
- **LDAP bootstrap**: the generated LDIF (identities and hashes) is
  born under `umask 077` and ends up mode `0600`; the generator can
  read the passwords from dedicated environment variables
  (`GENERATE_LDIF_*_PW`, scrubbed after reading).
- **Checked group writes**: every `conn.modify()` in `dynamic_groups`
  goes through `_checked_modify` — exception intercepted, return value
  checked, `conn.result` logged with member, group, operation and
  side.
- **Transactions**: no more explicit `transaction.commit()` in the views;
  `pyramid_tm` guarantees atomicity (2026 audit).
- **LDAP robustness**: tolerance to lagging schemas
  (`schema_safe_attributes`) — an out-of-date directory no longer causes a
  login denial of service.

## Infrastructure protections

Described and verified in `docker/README.md` and the Docker/Postfix
audits: Postfix anti-relay, port 25 unpublished, DKIM/SPF/DMARC, network
segmentation of the compose stack, backups, TLS.

## Known limits and target work

- The big worksites of the first four passes are **closed**: the
  Docker stack starts and proves itself with an end-to-end smoke test
  (P0); the three hashed locks, the multi-stage image with an
  application wheel and the digest-pinned bases hold the supply chain
  (P1, finished by 0075); validating LDAP TLS, parameter-keyed server
  cache, sealed refresh token, validated Keycloak responses, LDIF
  transport entirely off `argv` (NUL records on standard input,
  required fields enforced) and a reconciled group relation — member
  side authoritative, fail-closed write pairs (P2, trains 0073→0076).
  Details in the fourth-, sixth- and eighth-pass filings
  (`docs/en/audits/2026080*_external_chatgpt_audit_*`).
- **LDAPS is not enabled** in the shipped compose stack
  (`LDAP_USE_SSL=false`, port 389 on the internal network): the
  validating mechanism is ready (`Tls` + `LDAP_CA_CERT_FILE`);
  enabling it, and the certificate tooling of the LDAP container, is
  an operations decision.
- The **verifier reminder** still lives in the `NewRequest` event:
  execution not guaranteed without traffic, fragile in multi-process —
  P3 target, moved to cron (chapter
  [09](09_periodic_tasks.md)).
- `.env.example` documents `MAIL_USE_TLS`/`MAIL_USE_SSL` where the
  code reads `MAIL_TLS`/`MAIL_SSL`, presents `LDAP_SERVER` as a URL
  and ignores `LDAP_CA_CERT_FILE` — P3 target.
- The **daily group scan** costs members × groups in LDAP searches —
  P3 optimisation target (groups loaded once, inverse table, paged
  search).
- The **quality debt** is an assumed ratchet: mypy observing (124
  errors at adoption), Ruff limited to Pyflakes (`F841` excepted),
  coverage floor at 68%, Certbot and CSP untested.
- The **Pyramid ACLs** remain minimal; the class-hierarchy overhaul is the
  target (see
  [06_authorization_permissions](06_authorization_permissions.md)).
- The **end-to-end encryption** imagined at the outset
  (`../../fr/specifications_historiques/Scénarios/Chiffrement de bout en bout.md`,
  French) is exploratory and not implemented.
