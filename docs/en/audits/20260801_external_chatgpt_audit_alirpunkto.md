# External repository audit (ChatGPT) — 1 August 2026

**Provenance.** Static audit of the public repository performed by
ChatGPT at Michaël Launay's request. Proposed overall grade: **6.5/10**.
The full text is reproduced in the second part of this document
(translated from the French original).

**Status.** Counter-reviewed against the actual code the same day
(every major finding checked on the master branch); a three-package
action plan was adopted, with three architecture decisions recorded.
Package A fixes are being delivered as numbered patches (0063+).

## Counter-review

The audit is **largely accurate**: the on-code verification confirmed
nearly every finding, down to the details — the parasitic
`from httpcore import request` (login.py l.7), the **open redirect**
after login (`session['redirect_url']` followed without validation,
l.87-90), the total absence of attempt limiting, the parameter-blind
global LDAP `Server` cache, the three `encrypt_secret_for_logs` calls
in `log.debug`, the refresh token in the signed session cookie, the
fully unbounded dependencies with `version='0.0'` and no lock, the CI
reduced to the single test job, the duplicated imports, the verifier
reminder subscribed to `NewRequest`, the cleartext internal LDAP of the
test compose, and the mail booleans travelling as strings.

Three measured qualifications. **Actual coverage is 70%** (4052 lines):
the recommended `fail-under=80` is a target, not the state — it applies
as a ratchet (68 first, raised progressively). **The test suite is
under-credited**: ~900 tests with systematic red demonstrations and
structural locks; the valid criticism is the absence of lint and
coverage *in CI*, not the suite itself. **The verifier reminder**: the
audit converges with the in-house documentation (chapter 09) — moving
it to `cron` was already the target.

## Recorded decisions

1. **The ciphered password logs stay.** Fernet-ciphering at DEBUG level
   is a full-chain diagnostic tool, assumed under the administrator's
   responsibility: triggering it requires precise intent (log level,
   reading the code and the documentation), and a malicious
   administrator could just as silently modify the code. The removal
   work item is abandoned.
2. **The `constants_and_globals` globals are a deliberate choice.** The
   audit's "excessive coupling" point is set aside; whether to split
   `__init__.py` remains a separate question.
3. **Keycloak will not become the single authentication entry point.**
   The test server is not connected to Keycloak and hosts only
   AlirPunkto — not the whole set of Cosmopolitical applications.
   Direct LDAP authentication is an assumed path of the architecture,
   not a debt; the Keycloak integration stays what it is today:
   obtaining an SSO token after the local authentication.

## Adopted action plan and progress

**Package A — immediate fixes (patches delivered one by one)**: the
open redirect (0063: `safe_local_redirect`, same-site targets only);
login attempt limiting (0064: sliding IP and username windows before
any LDAP work, Waitress `trusted_proxy` — without it the IP window
would be global behind Apache); bounded and locked dependencies (0065:
`pyproject.toml`, a 77-package `requirements.lock`, re-keyed CI); then
the quality CI (ruff, bandit, pip-audit, coverage ratchet at 68), the
targeted fixes (keyed `Server` cache, mail booleans, verifier reminder
moved to the chapter-09 cron) and ciphering the refresh token in the
cookie.

**Package B — infrastructure decisions**: TLS on the internal LDAP,
Apache vhost security headers (HSTS, CSP, `X-Forwarded-*` replacement),
replacing the mounted `.env` with targeted variables, image digests and
scanning, tested ZODB/LDAP backups.

**Package C — structural**: server-side sessions, review of the special
administrator account, possible split of `__init__.py` — without
Keycloak-as-single-entry (decision 3).

---

# Full audit text (translated)

## General conclusion

**Overall assessment: 6.5/10**

The project shows a coherent architecture and clear recent improvement
on containerisation, network isolation, CSRF protection, cookies and
secret management. The operations documentation is above that of many
comparable projects.

Several elements however still prevent considering AlirPunkto
sufficiently hardened for a publicly exposed application handling
identities:

| Domain                       |  Grade | Assessment                                                    |
| ---------------------------- | -----: | ------------------------------------------------------------- |
| Architecture                 |   7/10 | Coherent, but strongly coupled                                |
| Code quality                 |   6/10 | Functional, but visible technical debt                        |
| Tests and CI                 | 6.5/10 | Good base, incomplete quality gates                           |
| Documentation                | 7.5/10 | Rich, sometimes scattered or ambiguous                        |
| Dependency management        | 3.5/10 | Main weak point                                               |
| Application security         |   6/10 | Global protections present, significant targeted weaknesses   |
| Docker security              | 7.5/10 | Good hardening level                                          |
| Operability/observability    |   6/10 | Correct, but several operational risks                        |

## Priority findings

### Critical — Unversioned dependencies

Every dependency is declared with no minimum, maximum or locked
version. Two installations made at different dates can therefore
produce different environments. An incompatible major update or a
compromised release could be installed automatically. There is no lock
file and no reproducible dependency generation either.

**To do immediately:** migrate metadata to `pyproject.toml`; define
compatible constraints; generate a lock with `pip-tools`, `uv` or
Poetry; separate runtime, test and development dependencies; automate
`pip-audit`; enable Dependabot or Renovate. The lock must be committed
and regenerated deliberately.

### High — Open redirect after authentication

After login the application takes a URL straight from the session and
redirects the user to it. No visible validation requires the URL to be
internal, relative or bound to the AlirPunkto domain. An attacker could
build a path where the victim visits a prepared URL, is redirected to
login, authenticates, then is redirected to an attacker-controlled
domain — enabling post-authentication phishing.

**Fix:** validate that the target is local (no scheme, no authority, a
path starting with `/` but not `//`); ideally store only a route name
and its parameters rather than a free URL.

### High — No visible login attempt limiting

The login view performs LDAP authentication directly, with no per-
account or per-IP limit. This exposes the service to brute force,
credential stuffing, LDAP directory saturation and distributed attacks
against the administrator account.

**Recommendation:** a short per-IP window (for instance 10 attempts
over 5 minutes); a stricter per-username limit; progressive delays; an
identical answer for unknown account and wrong password; structured
logging without the password; blocking or an additional challenge after
anomalies.

### High — Potentially cleartext LDAP authentication

The LDAP factory supports SSL, but the Docker stack configures port 389
without SSL. In the current configuration, passwords appear able to
travel as plain LDAP on the internal Docker network. That network is
isolated, which strongly reduces exposure, but provides neither
confidentiality nor cryptographic authentication between Pyramid and
OpenLDAP.

**Recommendation:** enable StartTLS or LDAPS; verify the LDAP
certificate; never use `CERT_NONE`; forbid simple bind without TLS on
the OpenLDAP side; add an integration test guaranteeing startup failure
when TLS is mandatory but unavailable.

### High — Password reused towards Keycloak

After LDAP authentication, the supplied password is passed to
`get_keycloak_token(user, password)` — resembling a Resource Owner
Password Credentials flow where the application collects the password
to forward it to a second identity provider. Risks: more components
handling the password; LDAP/Keycloak coupling; worse compromise in case
of an application flaw; incompatibility with MFA, WebAuthn and modern
identity policies.

**Recommended architecture:** Keycloak as the entry point through
Authorization Code + PKCE; LDAP federated or synchronised behind
Keycloak; AlirPunkto never receives the password again; proper refresh
token rotation and invalidation; strict checking of `state`, `nonce`,
`iss`, `aud` and the JWT algorithm.

### High — Session stored entirely client-side

The application uses `SignedCookieSessionFactory`. The session is
signed but not ciphered: its content can be read by the browser, even
though it cannot be modified without invalidating the signature. The
code indicates that only the refresh token and its expiry are kept by
`store_sso_tokens`; a refresh token should not live in a merely signed
client-side session. The signing secret is derived through SHA-256
before being handed to Pyramid, which is acceptable, and `secure`,
`httponly` and `samesite='Lax'` are correctly enabled.

**Recommendation:** use a server-side session; keep only a random
identifier in the cookie; regenerate the identifier after
authentication; invalidate the server session at logout; store refresh
tokens ciphered server-side; use a distinct key per usage.

## Code quality

**Duplicated or unused imports**: `from httpcore import request` in
`login.py`; `Configurator` and `get_localizer` imported twice in
`__init__.py`. This indicates no strict linter currently blocks in CI.
To add: `ruff check`, `ruff format --check`, `mypy`.

**`__init__.py` far too loaded**: the main module handles secret
initialisation, sessions, translation, e-mail reminders, LDAP
configuration, group creation, the mailer, the routes and external
application parsing. It becomes a central coupling point, hard to test
and risky to change. Proposed split into `bootstrap/`, `services/`,
`settings/` modules.

**Business task executed during web requests**:
`remind_pending_verifiers` is subscribed to `NewRequest`. Each process
has its own lock and last-run time; a restart resets the delay; several
replicas can send duplicates; a slow task can raise request latency. To
replace with a cron or systemd task, a scheduler container, or
Celery/RQ/Dramatiq.

**Imperfect global LDAP cache**: the connection is no longer shared — a
good fix — but the `Server` object stays globally cached without regard
for parameters passed after its first creation. Fix: cache keyed by
`(hostname, port, use_ssl, get_info)`.

**Insufficient typing**: many public functions remain untyped; some
configuration values travel as strings, notably the mail ports and
booleans.

## Passwords and secrets

**Positives**: the manager requires a non-empty `SECRET_KEY`; removes
several secrets from the environment after loading; avoids logging
secrets by default; stores LDAP passwords as `{SSHA}` rather than
cleartext.

**Limits**: secrets are kept in the process's global memory;
`SECRET_KEY` seems used as a general-purpose secret (one key per usage
would limit the impact of a compromise); the `{SSHA}` format relies on
salted SHA-1, fast and therefore weak against offline attacks — prefer
Argon2id or PBKDF2-SHA256 if the deployed OpenLDAP allows it; even
ciphering a password for the logs remains a risky practice — **strong
recommendation: remove this feature entirely** [decision: kept, see
above].

## Docker and infrastructure security

**Very good points**: LDAP bound only to `127.0.0.1` on the host;
Pyramid bound to `127.0.0.1:6543`; Postfix unpublished; distinct
frontend/backend networks; `no-new-privileges`; all capabilities
dropped on Pyramid; non-root execution; memory and CPU quotas; Docker
log rotation; persistent volumes; healthchecks; the LDAP password
provided as a Docker secret; `production.ini` mounted read-only.

**Needed improvements**: `read_only: true` and targeted `tmpfs` where
possible; drop capabilities on the other containers; pin base images by
SHA-256 digest; scan images with Trivy or Grype; generate an SBOM; sign
images; add tested backups for ZODB and LDAP; do not mount the whole
`.env` into the Pyramid container.

## HTTP configuration and reverse proxy

`production.ini` enforces localhost listening, the HTTPS scheme,
`secure` and `httponly` cookies, and session lifetime limits. Attention
point: `use_forwarded_proto = true` — ensure only headers coming from
Apache are recognised and that direct access to Waitress cannot forge
`X-Forwarded-Proto`, `Host` or the client address. To check in Apache:
replacement (not mere forwarding) of `X-Forwarded-*` headers; strict
`Host` validation; HSTS; CSP; `X-Content-Type-Options: nosniff`;
`Referrer-Policy`; `Permissions-Policy`; `frame-ancestors`; maximum
request size; connection limits and timeouts.

## CSRF, XSS and forms

The global `require_csrf=True` activation is an excellent decision. It
must be completed by a systematic review: all mutations through
POST/PUT/PATCH/DELETE; no destructive view exempted without
justification; AJAX calls carry the token; Chameleon templates escape
user content; `structure` expressions inventoried; uploaded files
limited, inspected and stored away from execution. A global CSRF
protection guards against neither XSS, nor IDOR, nor open redirects,
nor brute force.

## Authentication and authorisation

Login singles out an administrator account through
`is_admin(username, password)` then uses LDAP for the other accounts.
This special administrator path must receive specific scrutiny:
constant-time password comparison; resistant storage; no possible
confusion between an LDAP account and the administrator; MFA; logging
of administrative logins. Long-term recommendation: replace this
special account with an IdP-managed administrator role.

## Documentation

**Positives**: the README clearly explains the purpose, the stack, the
layout, installation, tests, the Docker stacks and sensitive-file
handling.

**Weaknesses**: the virtual environment is created at the repository
root (`python3 -m venv .` — prefer `.venv`); documentation is scattered
(several READMEs, two language trees, historical notes); security
documents are missing (`SECURITY.md`, disclosure policy, threat model,
secret rotation, incident response and restore procedures, personal
data matrix).

## Tests and CI

**Good practices present**: runs on push and pull request; Python
3.11/3.12 matrix; `permissions: contents: read`; concurrent job
cancellation; temporary secrets; JUnit report.

**Gaps**: the CI does not block on formatting, lint, typing, Python
vulnerabilities, committed secrets, Docker vulnerabilities, static
security analysis, or minimum coverage. Recommended pipeline: ruff,
mypy, pytest with minimum coverage, pip-audit, bandit, detect-secrets,
semgrep, hadolint, trivy. GitHub actions should be pinned by commit
SHA.

## Maintainability and design

**Positives**: models/views/templates/schemas separation; the LDAP
directory encapsulated in a factory; self-contained tests; bilingual
documentation; often useful comments on the reasons behind choices.

**Negatives**: very long historical comments inside the code;
operations and business logic mixed; numerous global constants
[decision: assumed choice, see above]; configuration resolved in
several places; old setup.py, version `0.0`.

## Final opinion

The repository is not in a "dangerous by default" state. Several
defence measures are already well designed, particularly in Docker, the
minimal CI, the cookies and CSRF. The main current risks come from four
structural gaps: non-reproducible dependencies; authentication still
based on the password travelling between several systems; sessions and
tokens to verify or move server-side; no automated security gates in
CI.

This audit is a targeted static audit of the accessible repository, not
a penetration test. It does not validate the real server configuration,
the `.env` values, the final Apache rules, volume permissions, or the
production network behaviour.
