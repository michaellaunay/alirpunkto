# External repository audit (ChatGPT), fourth pass — 1 August 2026

**Provenance.** Fourth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `c20df5c` (the CI quality gates);
previous pass on `885974e`. Proposed overall grade: **7.1/10**. Across
the passes: 6.5 → 6.9 → 6.7 → 7.1 — the auditor's own scale wobbles
from one pass to the next (the third rebased its reference), the slope
is what matters. The full text is reproduced in the second part of this
document (translated from the French original).

**Status.** Counter-reviewed against the actual code the same day
(clean clone of master, every finding checked — one of them
empirically). A four-part execution plan was adopted (patches 0071+).
The three architecture decisions of the first pass — ciphered DEBUG
password logs kept, `constants_and_globals` globals deliberate,
Keycloak not exclusive — stand; **the audit no longer questions them**.

## Counter-review

The audit is accurate on every verifiable finding; the three Docker
blockers it has repeated for two passes are real and confirmed down to
the line:

- **Both scripts require `setup.py`**
  (`docker/start_pyramid.sh` and `docker/start_test_pyramid.sh`, l.12),
  which the packaging patch removed in favour of `pyproject.toml`: the
  container exits before `pserve`.
- **`use_forwarded_proto = true` kills Waitress**: verified
  *empirically* — `waitress==3.0.2` (the locked version) raises
  `ValueError: Unknown adjustment 'use_forwarded_proto'` when the
  `Adjustments` are built. The option, inherited from another stack,
  was inert while it lived in `[app:main]`; moving the server options
  to `[server:main]` (the second pass's fix) made it lethal. To be
  removed everywhere — `url_scheme = https` already covers the need.
- **`listen = localhost:6543`** is unreachable from the Apache
  container, and **`trusted_proxy = 127.0.0.1`** does not match the
  address Apache presents on the compose network — the login limiter
  would then fold every visitor into a single window. The internal
  healthcheck (`urlopen('http://localhost:6543')`) can meanwhile stay
  green: which is exactly why nothing sees it. **Nuance**: both values
  are the *right* ones for the bare-host deployment (chapter 13,
  "Deployment without containers"), where Apache and Waitress share
  the host. The fix is therefore not to change `production.ini` for
  everyone, but to give the Docker stack its own server configuration.
- **§4, shared lock**: the auditor's inference is confirmed on the
  code — `requirements.lock` at `c20df5c` pins `ruff`, `bandit`,
  `mypy`, `pip-audit`, `pytest`…, and `DockerfilePyramid` installs
  that lock (after an out-of-lock `pip setuptools wheel` upgrade,
  l.52, also rightly flagged). The production image therefore embeds
  the test and quality tools. `pyramid_debugtoolbar` is indeed a
  *runtime* dependency of `pyproject.toml`.
- **`.env.example`** documents `MAIL_USE_TLS`/`MAIL_USE_SSL` where the
  code reads `MAIL_TLS`/`MAIL_SSL`, and presents `LDAP_SERVER` as a
  URL with scheme and port while the code hands server and port
  separately to `ldap3.Server`. Confirmed.
- The recalled security items (non-atomic two-sided LDAP group sync,
  `init.sh` still passing passwords and personal data through `argv`,
  signed-but-unencrypted refresh token, Keycloak responses not
  validated field by field, LDAP without TLS, a `Server` cache blind
  to its parameters, reminders on `NewRequest`) are the known
  remainders of the earlier plans — all confirmed still open.

Two measured nuances. **"957 tests and ~70 % not independently
verified"**: the auditor's GitHub connector returned nothing for this
commit; the figures are reproducible locally (clean clone, `mkdir
var`, `pytest --cov`) and the commit's workflows are green. **The
"global" throttling behind the proxy** is the containerised variant of
the point handled at the first pass for the bare host: the mechanism
(`trusted_proxy` + per-address windows) is in place, only the *value*
is wrong for compose.

## Decisions recorded (recap)

Unchanged since the first pass, and now integrated by the auditor
itself:

1. **The ciphered (DEBUG) password logs stay** — an assumed diagnostic
   tool, RSA-OAEP/SHA-256 towards a public key supplied by the
   environment, under the administrator's responsibility.
2. **The `constants_and_globals` globals are a choice**; the `.env`,
   however, is read only once (done, fourth fix train).
3. **Keycloak will not become the single authentication entry point** —
   the test server is not connected to it and hosts only AlirPunkto.

## Execution plan

### 0071 — P0: make the Docker stack start

- `pyproject.toml` replaces `setup.py` in both start scripts;
- `use_forwarded_proto` removed (everywhere);
- a server configuration of the stack's own: listen on `0.0.0.0:6543`
  *inside the container* (host publication staying on `127.0.0.1`, or
  dropped), a fixed address for the Apache container on the compose
  network and `trusted_proxy` set to it — without touching the
  bare-host values;
- **Compose smoke test in CI**: build the images, `up`, wait for the
  healthchecks, an end-to-end request *through Apache*, a check in the
  logs that `client_addr` is the real address (not the proxy's),
  unconditional `down`. That one job would have caught all three
  blockers;
- the secret scanner (gitleaks, SHA-pinned) rides the same train: it
  is one workflow addition.

### 0072 — P1: separate execution from development

- three locks generated with hashes (`--generate-hashes`): runtime,
  test, quality; the test CI installs the test lock, the quality
  workflow its own, Docker the runtime lock alone;
- a multi-stage `DockerfilePyramid` (builder with compilers and
  headers → final image without), base pinned by digest, no
  out-of-lock upgrade left;
- `pyramid_debugtoolbar` moved to a development extra
  (`development.ini` loads it, the production image no longer ships
  it).

### 0073+ — P2: remaining security

- `init.sh` finally wires `GENERATE_LDIF_*_PW` and passes the personal
  data through a `0600` temporary file (or standard input) — nothing
  through `argv` any more;
- **coherent** group synchronisation: the group side becomes
  authoritative and the daily scan reads and compares *both* sides to
  repair a divergence, instead of trusting `uniqueMemberOf` alone;
- the refresh token **encrypted** (Fernet, dedicated derived key)
  before it enters the signed cookie;
- Keycloak response validation (`json()` guarded, required fields and
  types checked);
- LDAP TLS with certificate validation: an operational decision to be
  made (internal compose network); the `ldap3.Tls` object and the
  parameter-keyed `Server` cache come with it.

### P3 — ratchets, as we go

- mypy: freeze the count (124 at adoption), forbid increases, make it
  blocking module by module;
- drop the `F841` exception, then extend Ruff family by family (`E`,
  `W`, `I`, `B`, `UP`);
- raise `--cov-fail-under` by two points per significant test
  campaign;
- move the verifier reminders from `NewRequest` to the chapter 09 cron
  — the audit converges with the in-house documentation.

# Full text of the audit (fourth pass)

**Date:** 1 August 2026
**Repository:** `michaellaunay/alirpunkto`
**Branch:** `master`
**Commit examined:** `c20df5c58898f99cf4439125a812562ee0624573`
**Previous audit:** commit `885974e756c00fad7039e92687694b76ba84c93f`

## 1. Executive summary

The latest commit significantly improves the industrialisation of the
project:

* Ruff is now blocking;
* Bandit is blocking for medium and higher alerts;
* `pip-audit` runs on the lock;
* a minimum coverage threshold of 68 % is enforced;
* GitHub actions are referenced by SHA;
* out-of-lock installs have been removed from the test workflow;
* several dead imports and two real defects detected by Ruff have been
  fixed;
* mypy is introduced as an informative control.

The commit also announces 957 passing tests and a measured coverage of
about 70 %. I could not, however, confirm those results from GitHub
Actions: the connector returned neither a run nor a check status for
this commit. The results are therefore documented in the commit, but
not independently validated here.

The main weakness is unchanged: **the documented Docker stack still
cannot start correctly**. No Docker file nor `production.ini` was
modified in this commit.

The three critical blockers therefore remain:

1. the scripts still look for `setup.py`;
2. `production.ini` contains an unknown Waitress option;
3. Waitress listens on the Pyramid container's loopback.

## 2. Updated assessment

| Area                              | Previous grade | New grade |
| --------------------------------- | -------------: | --------: |
| Application architecture          |            7.2 |       7.2 |
| Code quality                      |            6.8 |       7.3 |
| Tests                             |            7.3 |       7.7 |
| CI and automated controls         |            5.8 |       7.5 |
| Documentation                     |            7.3 |       7.3 |
| Dependencies and reproducibility  |            7.1 |       7.5 |
| Application security              |            7.3 |       7.6 |
| Docker security and operation     |            4.5 |       4.5 |
| Operations and observability      |            6.0 |       6.1 |

**Updated overall grade: 7.1/10**, against 6.7/10 previously.

The repository crosses the threshold of a properly controlled project
at the application and CI level, but remains penalised by the absence
of validation of the real deployment.

---

# 3. New findings resolved

## 3.1 Ruff blocking — resolved

A new `quality` workflow runs:

```yaml
ruff check alirpunkto tests tools
```

The control is blocking. The configuration currently selects the
Pyflakes family of errors, with `F841` temporarily ignored.

The clean-up notably removed:

* the duplicated `Configurator` imports;
* the duplicated `get_localizer` import;
* many unused imports;
* a `requests.request` import that shadowed a view parameter;
* a scoping error on the `DOMAINE` variable in a tool.

The `__init__.py` import clean-up, previously reported, is therefore
resolved.

**Status: resolved, with a deliberately still-limited Ruff rule set.**

The next step could be to progressively enable the `E`, `W`, `I`, `B`,
`UP` families and to drop the `F841` exception.

---

## 3.2 Bandit blocking — resolved

The workflow now runs:

```bash
bandit -r alirpunkto tools -ll -q
```

Medium and high alerts are therefore blocking.

The SHA-1 uses that produce the LDAP `{SSHA}` format are explicitly
documented with `# nosec B324`. That exception is consistent with the
OpenLDAP interoperability need: it is not about using SHA-1 as a
general application security mechanism, but about producing a format
the directory expects.

**Status: resolved.**

---

## 3.3 Dependency audit — resolved with a documented exception

The new workflow runs:

```bash
pip-audit -r requirements.lock --no-deps \
    --ignore-vuln PYSEC-2026-3447
```

The control is blocking, with the explicit exception of the
`PYSEC-2026-3447` identifier concerning `setuptools`. The reason for
the exception is documented directly in the workflow.

The `cryptography` bound was also raised and the lock regenerated.

**Status: resolved with a temporary accepted risk.**

The `setuptools` exception must stay visible and be removed as soon as
the dependency chain allows a fixed version.

---

## 3.4 Out-of-lock CI installs — resolved

The test workflow no longer runs:

```bash
pip install --upgrade pip setuptools wheel
pip install pytest
```

It installs the lock, then the application with `--no-deps`.

`pip`, `setuptools` and `wheel` are now included in the lock thanks to
generation with `--allow-unsafe`.

**Status: resolved for GitHub Actions.**

The point remains open in the production Dockerfile, however, which
still upgrades the build tools before installing the lock. The latest
commit does not modify that file.

---

## 3.5 GitHub actions pinned by SHA — resolved

The mutable references:

```yaml
actions/checkout@v4
actions/setup-python@v5
actions/upload-artifact@v4
```

have been replaced by 40-character SHAs. The readable version stays in
a comment.

**Status: resolved.**

---

## 3.6 Coverage threshold — resolved

The test workflow now runs:

```bash
pytest \
    --cov=alirpunkto \
    --cov-fail-under=68
```

The 68 % threshold is below the announced 70 % coverage, which makes a
good gradual-progression mechanism: coverage can no longer drop
freely.

**Status: resolved.**

The threshold should be raised progressively, for instance by two
points at each significant test campaign.

---

## 3.7 Static typing — engaged, not blocking

Mypy now runs on `alirpunkto`, but the job uses:

```yaml
continue-on-error: true
```

The commit reports 124 errors when the control was introduced.

**Status: improvement engaged, not yet a guard rail.**

This approach is reasonable to adopt mypy without immediately blocking
the project. What is needed now:

* record the current error count;
* prevent it from increasing;
* progressively fix the modules;
* make the job blocking once the debt becomes manageable.

---

# 4. New point of attention: one lock shared by production and quality

The lock was regenerated with the extras:

* `testing`;
* `quality`.

It therefore now contains not only the application dependencies, but
also:

* pytest;
* pytest-cov;
* Ruff;
* Bandit;
* pip-audit;
* mypy;
* their transitive dependencies.

The Pyramid Dockerfile still installs that same `requirements.lock`
into the production image.

Consequently, the production image now receives all the test and
quality tools. This is an inference based on the announced lock
regeneration with the quality extras and on Docker's unchanged
installation of that lock.

### Consequences

* a larger image;
* an increased attack surface;
* dependencies unnecessary at runtime;
* a noisier vulnerability audit;
* a longer build time.

### Recommended fix

Create three locks:

```text
requirements-runtime.lock
requirements-test.lock
requirements-quality.lock
```

The production image must install only the runtime lock.

**Severity: medium to high.**

---

# 5. Docker blockers still critical

## 5.1 The scripts still require `setup.py`

The production script still contains:

```bash
if [ ! -f "${APP_DIR}/setup.py" ] ||
   [ ! -d "${APP_DIR}/alirpunkto" ]; then
    exit 1
fi
```

The same check exists in `start_test_pyramid.sh`.

Yet `setup.py` was removed and replaced by `pyproject.toml`.

### Consequence

The Pyramid container stops before running `pserve`.

### Fix

```bash
if [ ! -f "${APP_DIR}/pyproject.toml" ] ||
   [ ! -d "${APP_DIR}/alirpunkto" ]; then
```

**Status: critical, open.**

---

## 5.2 Non-existent Waitress option

`production.ini` still contains:

```ini
use_forwarded_proto = true
```

That option is not among the parameters of Waitress 3.0.2. Waitress
refuses unknown options with a `ValueError`.

### Fix

Remove that line.

**Status: critical, open.**

---

## 5.3 Waitress listens on `localhost`

The configuration still contains:

```ini
listen = localhost:6543
```

Apache lives in another container. It therefore cannot reach the
Pyramid container's loopback.

### Fix

For the Docker stack:

```ini
listen = 0.0.0.0:6543
```

The port does not need to be published publicly on the host.

**Status: critical, open.**

---

## 5.4 Apache proxy not recognised by Waitress

The configuration still uses:

```ini
trusted_proxy = 127.0.0.1
```

Apache talks to Pyramid over the Docker network. Its source address is
therefore not `127.0.0.1`.

### Consequence

The throttling may consider every user as coming from the Apache
proxy's address.

**Status: high, open.**

---

# 6. Limits of the new CI

The new CI properly controls the Python code and the dependencies, but
it still does not validate:

* the Docker image builds;
* the Compose start-up;
* the effective validity of `production.ini` for Waitress;
* the Apache → Pyramid communication;
* the propagation of the real IP address;
* the stack's healthchecks;
* the LDAP migrations or initialisations;
* secret detection.

The commit explicitly acknowledges that the Docker build, the Compose
smoke test, the end-to-end test through Apache and secret scanning
remain out of scope.

### Priority test to add

A CI job must:

1. build the images;
2. generate a test configuration;
3. run `docker compose up -d`;
4. wait for the healthchecks;
5. query the application through Apache;
6. check the logs;
7. stop the stack even on failure.

That test would immediately have detected the three critical blockers.

---

# 7. Earlier findings still partially open

## 7.1 Two-sided LDAP synchronisation

`conn.modify()` failures are now checked and logged, but both sides of
the LDAP relation are still modified independently.

A divergence between:

* `group.uniqueMember`;
* `member.uniqueMemberOf`;

therefore remains possible.

**Status: partially resolved.**

---

## 7.2 LDIF generator passwords

`generate_ldif.py` can read the passwords from environment variables,
but `init.sh` still passes the values in positional arguments.

When `slappasswd` is missing, the cleartext password can therefore
still appear temporarily in the process command line.

**Status: partially resolved.**

---

## 7.3 Keycloak refresh token

The refresh token is still stored directly in a signed, but
unencrypted, session cookie.

**Status: open.**

---

## 7.4 Keycloak response validation

The calls carry timeouts and handle network errors, but:

* `response.json()` can fail;
* the mandatory fields are not checked;
* the types are not validated.

**Status: open.**

---

## 7.5 LDAP without validated TLS

The configuration still uses port 389 and `LDAP_USE_SSL=false`. The
factory defines no `Tls` object with certificate validation.

**Status: open.**

---

## 7.6 LDAP server cache

The first LDAP `Server` object built is still cached without regard to
the parameters of later calls.

**Status: open.**

---

## 7.7 Reminders inside the HTTP cycle

The verifier reminders are still triggered from the `NewRequest`
event.

**Status: open.**

---

## 7.8 `.env.example`

The file still documents `MAIL_USE_TLS` and `MAIL_USE_SSL`, while the
code expects `MAIL_TLS` and `MAIL_SSL`. It also describes
`LDAP_SERVER` as a full URL while the port is supplied separately.

**Status: open.**

---

# 8. Dependencies and reproducibility

## Now satisfactory

* bounded application dependencies;
* an exact lock;
* CI installation from the lock;
* CI tools included in the lock;
* automated vulnerability audit;
* GitHub actions pinned by SHA;
* `cryptography` updated.

## Still open

* no hashes in the lock;
* a single lock for runtime, tests and quality;
* an out-of-lock upgrade in the Dockerfile;
* the Ubuntu image not pinned by digest;
* the Pyramid image still single-stage;
* compilers and development headers kept in the final image;
* `pyramid_debugtoolbar` remains a runtime dependency.

---

# 9. Revised action plan

## P0 — Make the Docker stack start

1. Replace `setup.py` with `pyproject.toml` in the scripts.
2. Remove `use_forwarded_proto`.
3. Make Waitress listen on an interface reachable by Apache.
4. Fix `trusted_proxy`.
5. Add a Compose smoke test.

## P1 — Separate runtime and development

1. Create a runtime lock.
2. Create a test lock.
3. Create a quality lock.
4. Build a multi-stage image.
5. Remove compilers, pytest, Ruff, Bandit, mypy and pip-audit from the
   final image.
6. Add hashes to the locks.

## P2 — Remaining security

1. Enable LDAP TLS with certificate validation.
2. Encrypt the refresh token.
3. Validate the Keycloak JSON responses.
4. Finalise the out-of-`argv` transport of the LDIF data.
5. Make the LDAP group synchronisation coherent.
6. Add a secret scanner.

## P3 — Quality debt

1. Reduce the 124 mypy errors.
2. Make mypy blocking module by module.
3. Progressively drop the Ruff `F841` exception.
4. Extend Ruff to style, imports and Python modernisations.
5. Progressively raise the coverage threshold.

---

# 10. Conclusion

Commit `c20df5c…` is an important and correctly oriented improvement.

The repository now has real guard rails against:

* invalid imports and references;
* several statically detectable programming errors;
* medium- or high-severity Python security weaknesses;
* vulnerable dependencies not explicitly accepted;
* coverage drops;
* silent GitHub action changes.

The project's quality is no longer merely declarative: it is partially
enforced by the CI.

However, the CI mostly controls the Python code in isolation. It still
does not guarantee that the delivered product starts. The Docker stack
remains blocked by three simple errors that only an integration test
would have detected.

**Current assessment: 7.1/10.**

Once the P0 Docker points are fixed and the smoke test added, an
assessment between **7.8 and 8.1/10** would be justified without
revisiting the recorded architecture choices.
