# External repository audit (ChatGPT), fifth pass — 1 August 2026

**Provenance.** Fifth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `21ebee1` (the Docker P0 train);
previous pass on `c20df5c`. Proposed overall grade: **7.8/10**. Across
the passes: 6.5 → 6.9 → 6.7 → 7.1 → 7.8. Text transmitted after the
fact (on 2026-08-02, together with the 7th, 9th and 11th) and filed
for the record: the findings below have since been addressed by trains
0072 through 0078 — this document describes a historical state of the
repository, not its current situation. (Translated from the French
original.)

**Status (retrospective).** The audit validates the P0 train by
inspection: the four Docker blockers are declared resolved, the smoke
test judged "correctly designed" — the client-address proof mechanics
(CSRF dance, eleven failures, address extracted from the throttle log)
are described exactly as built. Two clarifications of lasting value:
§8.2 rightly notes that the smoke test *dogfooded* the environment
slots while `docker/init.sh` itself was not yet migrated (done in
0074, redone in 0076); §7.5 notes that the Waitress port published on
the host loopback (`127.0.0.1:6543`) lets a local process bypass
Apache — low risk, an **operations decision** still open. The P1 image
plan it lays out (three locks, multi-stage, no out-of-lock upgrade,
non-editable, digests) is exactly the one executed by 0072 then 0075.

## Follow-ups delivered

0072 (locks/image), 0073 (LDAP/Keycloak), 0074+0076 (LDIF/groups),
0075 (image finishing), 0078 (callers) — chronicled in the filings of
the later passes.

# Full text of the audit (fifth pass, translated)

# Updated audit of the AlirPunkto repository — fifth pass

**Date:** 1 August 2026 — **Repository:** `michaellaunay/alirpunkto` —
**Branch:** `master` — **Commit examined:**
`21ebee1ea943bbef0d539e881eb4f88d333dfd0a` — **Previous audit:**
`c20df5c58898f99cf4439125a812562ee0624573`

## 1. Executive summary

The latest train of changes fixes the main deployment blockers
reported in the previous passes.

The four priority Docker findings are now addressed: the scripts check
`pyproject.toml` instead of the removed `setup.py`; the invalid
Waitress option `use_forwarded_proto` is gone; Waitress listens on
`0.0.0.0:6543` inside Compose; Waitress trusts the Apache container's
real address, not `127.0.0.1`.

The distinction between the two deployment modes is well designed:
`production.ini` keeps the values suited to a direct host deployment
with a local Apache; the container generates a
`production.generated.ini` copy carrying only the two substitutions
Docker needs.

A real GitHub Actions smoke test has also been added. It: 1. builds
the real images; 2. initialises a throwaway stack; 3. starts Compose
with the healthchecks; 4. goes through the Apache HTTPS vhost;
5. checks the login form; 6. triggers the authentication throttling;
7. checks that the client address seen by Waitress is neither Apache's
nor the loopback; 8. always tears the stack down.

Finally, Gitleaks now scans the whole Git history.

These fixes allow the old Docker P0s to be considered resolved by
inspection of the code and configuration.

The commit also reports: 966 tests passing; 71.66% coverage; Ruff and
Bandit clean. These results are declared in the commit message, but
the GitHub connector currently returns no status and no Actions run
for this SHA. They are therefore not independently confirmed in this
audit.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      7.2 | 7.4 |
| Code quality                      |      7.3 | 7.5 |
| Tests                             |      7.7 | 8.4 |
| CI and automated checks           |      7.5 | 8.8 |
| Documentation                     |      7.3 | 7.9 |
| Dependencies and reproducibility  |      7.5 | 7.5 |
| Application security              |      7.6 | 7.7 |
| Docker security and operation     |      4.5 | 8.3 |
| Operations and observability      |      6.1 | 7.0 |

**Updated overall grade: 7.8/10**, against 7.1/10 previously. The main
gain comes from closing the Docker blockers and adding an end-to-end
test.

# 3. Docker blockers now resolved

**3.1 pyproject.toml check — resolved.** Both start scripts now check
for `"${APP_DIR}/pyproject.toml"` and no longer for the old
`setup.py`. The container is no longer stopped by a check incompatible
with the new packaging chain.

**3.2 Invalid Waitress option — resolved.** `use_forwarded_proto` was
removed from `production.ini`; `[server:main]` now carries only
options Waitress recognises (`trusted_proxy`, `trusted_proxy_headers`,
`clear_untrusted_proxy_headers`, `use`, `listen`, `url_scheme`). A
test feeds the section's real parameters to
`waitress.adjustments.Adjustments`, so a future typo or unknown option
should be caught before deployment.

**3.3 Docker listen reachable from Apache — resolved.**
`production.ini` keeps its bare-metal values (`listen =
localhost:6543`, `trusted_proxy = 127.0.0.1`). In Compose mode the
variables `PYRAMID_LISTEN: "0.0.0.0:6543"` and `PYRAMID_TRUSTED_PROXY:
${ALIRPUNKTO_APACHE_IP:-172.28.10.10}` are injected;
`apply_server_overrides.py` rewrites only `listen` and `trusted_proxy`
into a derived copy. This avoids modifying the read-only mounted
production file, duplicating the whole configuration, breaking
`%(here)s` paths, or imposing Docker values on the bare-host
deployment.

**3.4 Apache proxy correctly identified — resolved.** Apache gets a
fixed address on the frontend network (`ipv4_address:
${ALIRPUNKTO_APACHE_IP:-172.28.10.10}`); the network defaults to
`subnet: ${ALIRPUNKTO_FRONTEND_SUBNET:-172.28.10.0/24}`. The address
in `PYRAMID_TRUSTED_PROXY` therefore matches the Apache container's,
so Waitress accepts Apache's `X-Forwarded-For` and the throttle works
on the client's address rather than the proxy's.

*Operational reserve.* The address and the subnet must be changed
together when a host conflict exists. This constraint is documented
but not automatically validated; a bad combination would normally
cause a Compose failure rather than a silent degradation.

# 4. End-to-end Docker smoke test

The new workflow `.github/workflows/smoke.yml` is this pass's most
important improvement.

**4.1 Real build and startup.** The workflow runs `docker compose ...
build` then `up -d --wait --wait-timeout 240`, using the real
Dockerfiles and the real Compose file. It would have caught the three
old blockers (setup.py check, unknown Waitress option, loopback-only
listen).

**4.2 Real path through Apache.** The test does not just hit the
published 6543 loopback port. It uses `curl --resolve
"smoke.alirpunkto.test:443:127.0.0.1" "https://smoke.alirpunkto.test/"`
— vhost name, SNI and port 443 force the Apache path. It also checks
that `/login` contains the `username` field.

**4.3 Effective client-address check.** The test fetches a CSRF token
then sends eleven failed logins, inspects the Pyramid log and extracts
the address from `login throttled for ip=...`. That address must
differ from `127.0.0.1` and from every Apache container address. The
test therefore really validates the chain client → Apache →
X-Forwarded-For → Waitress → request.client_addr — not just syntax.

**4.4 Diagnostics and teardown.** On failure the workflow prints
`docker compose ps` and the last 200 log lines; teardown uses
`if: always()` and removes the volumes too.

**Smoke test status: correctly designed.**

*Limit.* The certificate is self-signed and the requests use
`curl -k`. The test validates TLS routing, the HTTPS vhost, the Apache
termination and the proxy to Pyramid; it does not validate real Let's
Encrypt issuance, renewal, the trust chain, or Certbot in production.

# 5. Secret detection — resolved

The quality workflow now carries a Gitleaks job; checkout uses
`fetch-depth: 0`, so the whole history is scanned, not just the
branch's current state. The Gitleaks action is pinned by SHA. This
usefully complements Bandit, pip-audit, Ruff, coverage, the functional
tests and the Docker smoke test.

# 6. Docker non-regression tests

The new `tests/test_docker_startup.py` locks: the use of
`pyproject.toml`; the absence of `use_forwarded_proto` in every INI;
the validity of the Waitress options; the preservation of the
bare-metal values; the two-line-only change in the generated copy; the
Docker variable wiring; the identity between the Apache address and
the declared proxy; the presence of the smoke test. The combination is
sound: Python tests catch structural regressions fast, the smoke test
validates the stack's real behaviour.

# 7. Docker points still open

**7.1 Single lock shared by runtime, tests and quality.** The Pyramid
image still runs `pip install -r requirements.lock`, and that lock now
carries the test and quality extras — the production image ships
pytest, pytest-cov, Ruff, Bandit, pip-audit, mypy and their
dependencies. Consequences: bigger image, larger software surface,
longer builds, more dependencies to watch, useless tooling in
production. *Open, medium severity.* Recommendation: produce at least
`requirements-runtime.lock`, `requirements-test.lock`,
`requirements-quality.lock`.

**7.2 Single-stage Pyramid image.** The final image keeps
`build-essential`, `python3-dev`, the LDAP/SSL/XML/image dev libraries
and the Python install tooling. A multi-stage build would compile in a
first image and copy only the virtualenv and runtime libraries.
*Open.*

**7.3 Out-of-lock installation during the build.** The Dockerfile
still runs `pip install --upgrade pip setuptools wheel` before the
lock: undetermined versions, more external accesses, may fail or
change independently of the repository. *Open.*

**7.4 Editable installation in production.** Still `pip install -e .
--no-deps`; a non-editable `pip install . --no-deps` suits an
immutable image better. *Open, low-to-medium severity.*

**7.5 Waitress port published on the host loopback.** Compose still
publishes `127.0.0.1:6543:6543`. Not Internet-reachable, but a local
process can bypass Apache, its security headers, the TLS termination
and some reverse-proxy rules. May be kept for local diagnostics; in
strict production it can be removed if unneeded. *Low risk, an
operations decision.*

# 8. Application findings still open

**8.1 Bidirectional group coherence.** LDAP modification failures are
now detected and logged, but the two sides (`group.uniqueMember`,
`member.uniqueMemberOf`) are still written independently: one write
can succeed and the other fail. *Partially resolved.*

**8.2 LDIF production and process arguments.** The smoke test
correctly uses `GENERATE_LDIF_ADMIN_PW` / `_U1_PW` / `_U2_PW` and
passes `-` in the matching slots. However the real interactive script
`docker/init.sh` was not touched by this train and still builds a
command line carrying the password values or their hashes; when
`slappasswd` is missing its fallback can still momentarily pass the
cleartext password through `argv`. The smoke test proves the secure
mechanism works; it does not prove `init.sh` uses it. *Partially
resolved.*

**8.3 Keycloak refresh token in the cookie.** Still stored directly in
the signed session (`request.session[SSO_REFRESH] = ...`): integrity,
not confidentiality. *Open.*

**8.4 Keycloak response validation.** Timeouts and network errors are
handled, but JSON responses are still not validated before use:
invalid JSON, missing fields, wrong types, inconsistent expiry values.
*Open.*

**8.5 LDAP TLS.** The Docker configuration still uses LDAP on port 389
without application TLS; the LDAP factory does not yet build a `Tls`
object enforcing certificate and CA validation. Docker network
isolation reduces exposure but does not replace encryption and server
authentication. *Open.*

**8.6 LDAP server cache.** The first `ldap3.Server` object created is
still cached globally; later calls asking for another server, port,
SSL mode or info level may receive the first object. *Open.*

**8.7 Reminders triggered by HTTP requests.** The verifier reminder
remains subscribed to `NewRequest`. The lock and interval limit calls
within one process but guarantee neither execution without traffic,
multi-process coordination, single execution after restart, nor
absence of impact on the triggering request. *Open.*

**8.8 Inconsistent .env.example.** Still `MAIL_USE_TLS`/`MAIL_USE_SSL`
where the code reads `MAIL_TLS`/`MAIL_SSL`; still presents
`LDAP_SERVER` as a full URL while the port is configured separately.
*Open.*

# 9. Revised priorities

**P0 — closed**: pyproject-compatible scripts; valid Waitress
configuration; reachable Docker listen; correctly declared Apache
proxy; end-to-end Compose smoke test.

**P1 — slim and reproducible image**: 1. split the runtime, test and
quality locks; 2. make the Pyramid Dockerfile multi-stage; 3. remove
the unlocked pip/setuptools/wheel upgrade; 4. install the application
non-editable; 5. pin the base images by digest.

**P2 — remaining application security**: 1. enable LDAP TLS with
certificate validation; 2. encrypt the Keycloak refresh token;
3. validate the Keycloak response schema; 4. finish the off-argv
transport in `docker/init.sh`; 5. make the LDAP synchronisation
coherent or compensated; 6. remove the local Waitress port if
unneeded.

**P3 — operations and technical debt**: 1. move the reminders out of
the HTTP cycle; 2. fix `.env.example`; 3. reduce the mypy errors and
progressively make the job blocking; 4. extend Ruff beyond Pyflakes;
5. progressively raise the coverage floor; 6. test the Certbot cycle
and certificate renewal; 7. add a tested CSP.

# 10. Conclusion

Commit `21ebee1…` correctly closes the previous audit's main weakness:
the project no longer only tests its Python code, it now tests the
deployed product.

This combination is particularly solid: unit tests of the Docker
configuration; empirical validation of the Waitress parameters; image
builds; Compose startup with healthchecks; an HTTPS request through
Apache; verification of the real `client_addr`; diagnostics on
failure; systematic teardown; secret detection over the whole history.

The Docker stack can now be considered coherent and deployable by
design, subject to the workflow actually succeeding in GitHub Actions,
which the connector used for this audit cannot confirm.

The main remaining risks are no longer immediate startup blockers.
They now mostly concern: token confidentiality; LDAP TLS; the
coherence of LDAP writes; secret handling in `init.sh`; the size and
reproducibility of the production image; periodic tasks; the typing
debt.

**Current evaluation: 7.8/10.** The project can reach about 8.4/10
after splitting the runtime lock, moving to a multi-stage image,
hardening LDAP and closing the Keycloak/LDIF findings.
