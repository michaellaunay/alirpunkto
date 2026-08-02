# External repository audit (ChatGPT), sixth pass — 1 August 2026

**Provenance.** Sixth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `e80f39e` (split locks and
multi-stage image); previous pass (the fifth, graded 7.8 on `21ebee1`,
text not transmitted). Proposed overall grade: **8.2/10**. Across the
passes: 6.5 → 6.9 → 6.7 → 7.1 → 7.8 → 8.2. The full text is reproduced
in the second part of this document (translated from the French
original).

**Status.** Counter-reviewed against the actual code the same day. P0
(Docker startup) and P1 (supply chain) declared closed by the auditor —
who honestly notes that the GitHub connector returns no Actions run for
this SHA: the test figures are those of the commit messages, not
independently confirmed. The three architecture decisions remain in
force and unchallenged. Response delivered: patches 0073 (P2, items 1
to 4) and 0074 (items 5 and 6), themselves evaluated by the eighth pass
(`20260802_external_chatgpt_audit_alirpunkto_8th_pass.md`).

## Counter-review

Every application-level finding of §12 was verified against the code
before being fixed:

- **§12.1, LDAP TLS**: confirmed *on the ldap3 2.9.1 sources* —
  without a `Tls` object the default is `ssl.CERT_NONE`: no certificate
  is validated at all. Also verified: with `CERT_REQUIRED`, ldap3 loads
  the system CA store when no bundle is given (`load_default_certs`)
  and performs the hostname check itself.
- **§12.2, server cache**: confirmed — `_server` was a module
  singleton returned regardless of the parameters; the first call
  imposed its host, port and SSL mode on every later one.
- **§12.5, refresh token**: confirmed — written in clear by the single
  write point `store_sso_tokens`, into a cookie that is signed
  (integrity) but not encrypted (confidentiality). The fix surfaced a
  constraint the audit could not see: encrypting without compressing
  would have blown the 4093-byte cookie budget again (the 2026-07-08
  field incident) — hence the compress-then-encrypt sealing, documented
  in the code.
- **§12.6, Keycloak responses**: confirmed — `response.json()` could
  raise, no field or type was checked, expiry values were unbounded.
- **§12.4**: both of the auditor's clarifications are exact — the
  "NUL-separated env vars" comment did not match the code (a Bash array
  expanded as positional arguments), and the `hash_password` fallback
  returned the cleartext password whenever `slappasswd` was missing.
- **Image reserves (§11)**: all grounded; addressed by the
  image-finishing train (0075), which furthermore uncovered that "all
  wheels" had been a pip-cache illusion (three locked packages are
  sdist-only, pure python) and repaired a latent first-start crash (the
  override helper excluded from the image by `.dockerignore`).

## Decisions in force (reminder)

Unchanged since the first pass: encrypted DEBUG password logs kept;
`constants_and_globals` globals wanted; Keycloak never the sole
authentication point. Enabling LDAPS in the compose stack remains an
operations decision of the client — the validating mechanism is ready
(0073), the internal-network default unchanged.

## Execution plan adopted

- **0073** — P2 items 1 to 4: validating LDAP TLS (`Tls` + optional
  `LDAP_CA_CERT_FILE`), parameter-keyed server cache, sealed refresh
  token (zlib then Fernet), strict Keycloak response validation
  (fields, types, 90-day bound, body-free logging).
- **0074** — P2 items 5 and 6: LDIF transport off `argv`
  (generalisation of the environment slots), group coherence (both
  sides read, per-side convergence, two-sided scan discovery).
- **Image finishing** (§11 reserves): application wheel,
  `--only-binary` with named exceptions, reduced context, opt-in APT
  snapshot — delivered as 0075.

# Full text of the audit (sixth pass, translated)

# Updated audit of the AlirPunkto repository — sixth pass

**Date:** 1 August 2026
**Repository:** `michaellaunay/alirpunkto`
**Branch:** `master`
**Commit examined:** `e80f39e912e239cc267dda8489bc68cbc57f37ac`
**Previous audit:** commit `21ebee1ea943bbef0d539e881eb4f88d333dfd0a`

## 1. Executive summary

The latest commit closes the essential part of P1, concerning the build
chain and the production image.

The main improvements are:

* separation of runtime, test and quality dependencies into three locks;
* SHA-256 hashes added on every locked dependency;
* use of `--require-hashes` during installations;
* removal of pytest, Ruff, Bandit, mypy and `pip-audit` from the production image;
* `pyramid_debugtoolbar` moved to a development extra;
* the Pyramid image converted to a multi-stage build;
* removal of the unlocked upgrade of pip, setuptools and wheel;
* removal of compilers and development headers from the final image;
* digest pinning of the four Ubuntu images;
* auditing of the three locks by `pip-audit`;
* non-regression tests added over this whole chain.

The commit reports:

* 974 tests passing;
* a coverage of 71.61%;
* an execution inside an environment built solely from the test lock.

These results are documented in the commit message, but the GitHub
connector currently returns neither an Actions run nor a combined
status for this SHA. They are therefore not independently confirmed in
this audit.

The Python and Docker chain now reaches a good level of
reproducibility. It is not yet strictly bit-for-bit reproducible,
mainly because the Ubuntu packages installed with `apt-get` are neither
versioned nor served from a frozen repository.

## 2. Updated evaluation

| Domain                            | Previous grade | New grade |
| --------------------------------- | -------------: | --------: |
| Application architecture          |            7.4 |       7.5 |
| Code quality                      |            7.5 |       7.6 |
| Tests                             |            8.4 |       8.7 |
| CI and automated checks           |            8.8 |       9.0 |
| Documentation                     |            7.9 |       8.0 |
| Dependencies and reproducibility  |            7.5 |       9.0 |
| Application security              |            7.7 |       7.7 |
| Docker security and operation     |            8.3 |       9.0 |
| Operations and observability      |            7.0 |       7.2 |

**Updated overall grade: 8.2/10**, against 7.8/10 previously.

The project now has a solid build chain, structurally tested and
protected against many dependency drifts.

---

# 3. Lock separation — resolved

Three distinct files now exist:

```text
requirements.lock
requirements-test.lock
requirements-quality.lock
```

The first contains only the dependencies needed at runtime. The other
two respectively add the test and quality dependencies. This structure
is also documented in `pyproject.toml`.

The headers of the three files show they are generated with:

```text
--generate-hashes
--allow-unsafe
--strip-extras
```

## Positive consequences

* development tools are no longer shipped to production;
* runtime versions stay identical across the three lanes;
* a dependency altered on the index without matching the expected hash is refused;
* test and quality dependencies can evolve without inflating the production image.

**Status: resolved.**

---

# 4. Hash-checked installation — resolved

The Dockerfile now installs the runtime lock with:

```dockerfile
pip install --require-hashes -r requirements.lock
```

The test workflow uses:

```bash
pip install --require-hashes -r requirements-test.lock
```

The Ruff, Bandit, mypy and `pip-audit` jobs use the quality lock with
the same check.

The start scripts also install the test lock with `--require-hashes`
when `INSTALL_EXTRAS_TESTING` is explicitly enabled.

**Status: resolved.**

---

# 5. Auditing the three locks — resolved

The quality workflow submits the three files to `pip-audit`:

```bash
pip-audit \
  --no-deps \
  --ignore-vuln PYSEC-2026-3447 \
  -r requirements.lock \
  -r requirements-test.lock \
  -r requirements-quality.lock
```

Repeated `-r` usage is officially supported by `pip-audit`. Its
documentation also notes that `--require-hashes` is preferable when the
files are fully hashed. In this repository, hash checking is already
performed when each lane installs; the audit then uses `--no-deps` to
avoid a fresh resolution.

The `PYSEC-2026-3447` exception remains explicitly documented.

**Status: resolved with an accepted risk.**

The exception must be removed as soon as the dependency chain allows an
unaffected version.

---

# 6. Test tooling absent from the runtime — resolved

The new test `test_the_runtime_lock_ships_no_tooling` forbids in the
runtime lock:

* pytest;
* pytest-cov;
* WebTest;
* Ruff;
* Bandit;
* mypy;
* `pip-audit`;
* `pyramid_debugtoolbar`.

`pyramid_debugtoolbar` now lives only in the `dev` extra, since only
the development configuration uses it.

**Status: resolved.**

---

# 7. Multi-stage Pyramid image — resolved

The Dockerfile now has two stages.

## Build stage

It contains:

* the compilers;
* the Python headers;
* the LDAP, SSL, XML and image development libraries;
* the virtualenv;
* the Python dependencies.

## Runtime stage

It keeps only:

* Python;
* the certificate authorities;
* the built virtualenv;
* the application sources;
* the start script.

Compilers and `*-dev` packages are no longer present in the final
image.

The Dockerfile also copies the lock before the sources, which lets the
dependency layer be reused when a change only touches the code.

**Status: resolved.**

---

# 8. Out-of-lock installation removed — resolved

The old Dockerfile ran:

```dockerfile
pip install --upgrade pip setuptools wheel
```

That step is gone.

The virtualenv uses the pip provided at its creation and installs the
versions defined in the lock. The project installation uses
`--no-build-isolation`, avoiding the automatic download of an unlocked
build environment.

**Status: resolved.**

---

# 9. Base images pinned by digest — resolved

The Pyramid, Apache, LDAP and Postfix images now use a reference of the
form:

```dockerfile
FROM ubuntu:24.04@sha256:...
```

The Apache Dockerfile confirms it directly.

A test walks every `Dockerfile*` and requires a SHA-256 digest on each
`FROM` instruction.

This prevents a silent change of the image behind the `ubuntu:24.04`
tag.

**Status: resolved.**

---

# 10. Supply-chain tests — resolved

The new file `tests/test_supply_chain.py` checks:

* the presence of three hashed locks;
* the absence of test tooling in the runtime;
* identical runtime versions across the three locks;
* the debug toolbar's placement in the `dev` extra;
* the multi-stage build;
* the absence of an out-of-lock pip upgrade;
* the pinning of every base image;
* each workflow using its own lock;
* the start scripts using the test lock.

These tests properly complement the Docker smoke test added in the
previous pass.

**Status: resolved.**

---

# 11. Remaining reserves on the image

## 11.1 Editable installation in production

The application is still installed with:

```dockerfile
pip install --no-build-isolation --no-deps -e .
```

This works because the sources are copied to the same path in the final
image. However, an editable installation is not necessary in an
immutable image.

A regular installation would be simpler to reason about:

```bash
pip install --no-build-isolation --no-deps .
```

or through an application wheel built in the first stage.

**Status: open, low severity.**

---

## 11.2 Assumption that every dependency ships a wheel

The Dockerfile states that every currently locked dependency ships a
wheel. The build stage nevertheless deliberately keeps the compilers in
case a future lock brings a source archive back.

That creates a future risk:

1. a dependency is compiled against a system library in the builder stage;
2. the virtualenv is copied;
3. the corresponding shared library does not exist in the final image;
4. the import fails only at runtime.

### Recommendation

Enforce in the image:

```bash
pip install --only-binary=:all: --require-hashes \
  -r requirements.lock
```

The absence of a wheel then causes an explicit build failure.

Alternative: precisely list the required runtime libraries in the
second stage.

**Status: open, medium preventive severity.**

---

## 11.3 APT packages are not frozen

The base images are immutable thanks to the digest, but the following
commands remain time-dependent:

```dockerfile
apt-get update
apt-get install ...
```

Two builds run at different dates may therefore obtain different
revisions of the Ubuntu packages, even from the same base image.

### Recommendation

For strict reproducibility:

* use a dated Ubuntu snapshot;
* or pin the APT versions;
* or build and publish signed internal images, then deploy only by digest.

**Status: open, medium severity for strict reproducibility.**

---

## 11.4 A few non-runtime artefacts are still copied

`.dockerignore` already excludes:

* the tests;
* the tools;
* the documentation;
* the virtual environments;
* the secret files;
* the runtime data.

However, the final image can still receive through `COPY .`:

* `.github/`;
* `requirements-test.lock`;
* `requirements-quality.lock`;
* some development configuration files.

This has no major security impact, but a more explicit copy list would
produce an even cleaner image.

**Status: open, low severity.**

---

# 12. Application findings still open

## 12.1 LDAP TLS

The LDAP factory still uses `Server(..., use_ssl=...)` without a `Tls`
object enforcing:

* certificate validation;
* a trust authority;
* an expected server name.

The `_server` cache also remains unique, whatever the requested server,
port or TLS mode.

**Status: open.**

---

## 12.2 LDAP server cache

Once `_server` is set, `get_ldap_server()` returns it without comparing
the call's parameters.

A first call can therefore impose its server and SSL mode on every
later one.

**Status: open.**

---

## 12.3 Bidirectional group coherence

LDAP failures are logged, but the modifications of:

* `group.uniqueMember`;
* `member.uniqueMemberOf`;

remain independent.

One half of the relation can be applied without the other.

**Status: partially resolved.**

---

## 12.4 LDIF data still passed through `argv`

The generator knows how to read passwords from environment variables,
but `docker/init.sh` still builds an argument array containing:

* the hashes or passwords;
* the e-mail addresses;
* the names;
* the birthdates;
* the descriptions.

The comment claiming these are NUL-separated environment variables does
not match the code: it is a Bash array expanded as positional
arguments.

The `hash_password` fallback can still pass the cleartext password when
`slappasswd` is missing.

**Status: partially resolved.**

---

## 12.5 Keycloak refresh token

The refresh token is still stored directly in the signed cookie
session.

The signature protects integrity, not confidentiality.

**Status: open.**

---

## 12.6 Keycloak response validation

The calls now have timeouts and handle network errors, but:

* `response.json()` can fail;
* required fields can be missing;
* types are not validated;
* expiry values are not checked.

**Status: open.**

---

## 12.7 Reminder task inside the HTTP cycle

The verifier reminder is still executed from the `NewRequest` event.

This architecture guarantees neither execution without traffic nor
uniqueness in a multi-process environment.

**Status: open.**

---

## 12.8 Inconsistent `.env.example`

The file still uses:

```text
MAIL_USE_TLS
MAIL_USE_SSL
```

while the application reads:

```text
MAIL_TLS
MAIL_SSL
```

It also presents `LDAP_SERVER` as a full URL while the port is
configured separately.

**Status: open.**

---

# 13. Revised priorities

## P0 — closed

* Docker startup;
* Waitress configuration;
* Apache proxy;
* end-to-end smoke test;
* secret scanning.

## P1 — closed in its main objective

* lock separation;
* hashes;
* runtime without test tooling;
* multi-stage image;
* removal of out-of-lock pip upgrades;
* pinned base images.

## P2 — application security

1. Enable LDAP TLS with certificate validation.
2. Fix the LDAP cache.
3. Encrypt the Keycloak refresh token.
4. Validate Keycloak responses.
5. Finish moving the LDIF transport off `argv`.
6. Guarantee the coherence of the LDAP group relations.

## P3 — image finishing

1. Build an application wheel rather than an editable installation.
2. Enforce `--only-binary=:all:`.
3. Freeze or snapshot the APT packages.
4. Further reduce the context copied into the image.
5. Publish and deploy the images by digest.

## P4 — operations and debt

1. Move the reminders out of the HTTP cycle.
2. Fix `.env.example`.
3. Reduce the mypy errors.
4. Progressively extend Ruff.
5. Raise the coverage floor.
6. Test the Certbot renewal.
7. Add a tested CSP.

---

# 14. Conclusion

Commit `e80f39e…` strongly improves the delivery quality.

The Python chain is now:

* separated by usage;
* bounded;
* locked;
* hashed;
* audited;
* tested;
* free of development tooling in the runtime.

The Docker chain is now:

* multi-stage;
* based on pinned images;
* free of compilers in the final image;
* tested by a real smoke test;
* protected against configuration regressions.

The main remaining issues no longer concern startup, packaging or CI.
They now concentrate on:

* LDAP;
* Keycloak;
* transactional coherence;
* secret transport;
* periodic tasks;
* strict reproducibility of system packages.

**Current evaluation: 8.2/10.**

A grade close to **8.7/10** would become justified after LDAP
hardening, refresh-token encryption, strict Keycloak validation and a
complete fix of the LDIF transport.
