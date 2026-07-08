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
  no secret hard-coded.
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

- The SSO **refresh token** lives in the signed but unencrypted session
  cookie; the target is a server-side session.
- The **Pyramid ACLs** remain minimal; the class-hierarchy overhaul is the
  target (see
  [06_authorization_permissions](06_authorization_permissions.md)).
- The **end-to-end encryption** imagined at the outset
  (`../../fr/specifications_historiques/Scénarios/Chiffrement de bout en bout.md`,
  French) is exploratory and not implemented.
