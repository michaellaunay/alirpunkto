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

- The **documented Docker stack does not start**: the `setup.py` check
  in both scripts points at a removed file, the unknown Waitress
  option `use_forwarded_proto` (rejection verified as a `ValueError`),
  a listen on the container's loopback — and `trusted_proxy =
  127.0.0.1` which, behind the compose proxy, would fold the login
  limiter onto a single address. Detail and plan in the fourth-pass
  audit
  (`docs/en/audits/20260801_external_chatgpt_audit_alirpunkto_4th_pass.md`);
  P0 fix with the Compose smoke test that would have caught them.
- `init.sh` still passes passwords and personal data through `argv`:
  the `GENERATE_LDIF_*_PW` mechanism awaits its wiring, and the
  personal data their `0600` temporary file (P2).
- The **single lock** ships the test and quality tools into the
  production image; the split into three hashed locks and the
  multi-stage image are P1.
- The group synchronisation writes **both sides independently**: a
  one-sided failure can leave a divergence the scan, which reads
  `uniqueMemberOf` alone, does not see (P2: authoritative group side,
  a scan comparing both sides).
- The SSO **refresh token** lives in the signed but unencrypted session
  cookie; the target is a server-side session — and, until then,
  encryption of the value (P2).
- The **Pyramid ACLs** remain minimal; the class-hierarchy overhaul is the
  target (see
  [06_authorization_permissions](06_authorization_permissions.md)).
- The **end-to-end encryption** imagined at the outset
  (`../../fr/specifications_historiques/Scénarios/Chiffrement de bout en bout.md`,
  French) is exploratory and not implemented.
