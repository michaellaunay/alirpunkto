# External repository audit (ChatGPT), ninth pass — 2 August 2026

**Provenance.** Ninth pass of the external static audit (ChatGPT, at
Michaël Launay's request), on commit `72e65db2` (image finishing);
previous pass on `2bc56291`. Proposed overall grade: **8.4/10** —
down. Across the passes: 6.5 → 6.9 → 6.7 → 7.1 → 7.8 → 8.2 → 8.5 →
8.6 → 8.4. Text transmitted after the fact (on 2026-08-02) and filed
for the record: this document describes the state after train 0075 —
**this is where the duplicate `args:` key of the LDAP service was
first reported**, but since the text was not transmitted at the time,
it was the tenth pass that carried it to us; the fix (0078) arrived
two passes later than it should have. (Translated from the French
original.)

**Status (retrospective).** The audit validates the image finishing
(wheel, real parity, only-binary with named exceptions, zero
compiler, allowlist copy, APT snapshot) and confirms the latent
override-helper break — noting, with appreciable honesty, that its own
earlier passes "had validated the wiring by inspection without
checking the effective composition of the Docker context". It
discovers in return the P0 regression this same train introduced (the
duplicate `args:` key) — fixed in 0078 with the `compose config
--quiet` gate it prescribed word for word. Two suggestions kept on the
books: **structurally verifying the purity of the three sdist
exceptions** (the test could build each wheel and refuse any tag other
than `py3-none-any`) and **an autonomous test image** (the dynamic
installation of the test lock at startup makes the local stack depend
on the index).

## Follow-ups delivered

0078 (args blocks merged, compose gate, shared emitter, caller tests)
— chronicled in the filings of the 10th and 11th passes.

# Full text of the audit (ninth pass, translated)

# Updated audit of the AlirPunkto repository — ninth pass

**Date:** 2 August 2026 — **Repository:** `michaellaunay/alirpunkto` —
**Branch:** `master` — **Commit examined:**
`72e65db2de566bc193c5d14130ac301594b4231a` — **Previous audit:**
`2bc562912856a20a777d38b748bece8b41916c97`

## 1. Executive summary

The new commit markedly improves the Pyramid image build: the
application installed as a non-editable wheel; the source tree
entirely removed from the final image; binary distributions enforced,
except three explicitly named pure-python exceptions; compilers and
dev headers removed, including from the builder; the runtime copy
limited to an explicit list; an optional reproducible APT mode based
on Ubuntu snapshots; the test stack adapted to the source-free image;
real verification of the wheel's completeness.

It also fixes a latent Docker blocker that invalidates a conclusion of
the previous audit: `start_pyramid.sh` called
`docker/apply_server_overrides.py`, but `.dockerignore` excluded the
whole `docker/` directory. The helper could therefore not reach the
image — Docker strips ignored paths from the context before sending it
to the builder, and a `COPY` instruction can only use a file present
in that context. The helper is now explicitly re-included in the
context and explicitly copied into the final image.

However, the commit simultaneously introduces a new P0 regression in
the production Compose: the LDAP service carries two `args:` keys at
the same level.

```yaml
build:
  context: .
  dockerfile: DockerfileOpenLDAP
  args:
    UBUNTU_SNAPSHOT: ${ALIRPUNKTO_UBUNTU_SNAPSHOT:-}
  args:
    BUILD_WITH_DEBUG: ${BUILD_WITH_DEBUG:-0}
```

YAML mapping keys must be unique. The file is therefore invalid per
the YAML specification; a strict parser must refuse it, while a
permissive parser risks overwriting the first block. In the latter
case `UBUNTU_SNAPSHOT` would not be passed to the LDAP image; in the
former, the whole production stack would be unstartable.

The commit message reports 1,009 tests passing with 72.10% coverage,
but no workflow or GitHub Actions status is returned for this SHA. The
commit itself states that no Docker daemon was available in its build
environment. These results therefore remain unconfirmed by an
end-to-end run.

## 2. Updated evaluation

| Domain                            | Previous | New |
| --------------------------------- | -------: | --: |
| Application architecture          |      7.8 | 7.9 |
| Code quality                      |      8.0 | 8.1 |
| Tests                             |      9.2 | 9.1 |
| CI and automated checks           |      9.0 | 8.8 |
| Documentation                     |      8.0 | 8.0 |
| Dependencies and reproducibility  |      9.0 | 9.4 |
| Application security              |      8.8 | 8.8 |
| Docker security and operation     |      9.1 | 7.9 |
| Operations and observability      |      7.4 | 7.5 |

**Updated overall grade: 8.4/10**, against 8.6/10 previously. The
image improvements are excellent, but they do not fully compensate for
an invalid production Compose file.

# 3. Latent Docker helper blocker — resolved

**3.1 Prior problem.** Since the Docker P0 train, the start script
runs `python3 "${APP_DIR}/docker/apply_server_overrides.py" …`
whenever `PYRAMID_LISTEN` or `PYRAMID_TRUSTED_PROXY` is set — and
Compose sets them by default. Yet the old `.dockerignore` excluded
`docker/` except the start script alone. The container would therefore
have failed before `pserve` launched. This weakness was not caught by
the previous pass, which had validated the wiring by inspection
without checking the effective composition of the Docker context.

**3.2 Current fix.** `.dockerignore` now carries the
`!docker/apply_server_overrides.py` re-inclusion and the Dockerfile
adds an explicit copy of the helper into the image. *Resolved by
inspection.*

*Test limit.* The current test only checks the textual presence of the
re-inclusion rule and the `COPY` instruction. It does not actually
build the Docker context nor verify BuildKit receives the file. The
real smoke test therefore remains indispensable.

# 4. P0 regression: duplicate args key in Compose

The LDAP service of `docker/docker-compose.yaml` carries two
consecutive `args:` keys in the same mapping; YAML mapping keys must
be unique.

*Possible consequences.* **Strict parser**: `docker compose
--env-file docker/.env -f docker/docker-compose.yaml config` fails
before any build — the stack cannot start. **Permissive parser**: the
second `args` block replaces the first — `UBUNTU_SNAPSHOT` is no
longer passed to OpenLDAP. Either way the result is wrong.

*Required fix.* Merge the two blocks into one
`args: {BUILD_WITH_DEBUG, UBUNTU_SNAPSHOT}`.

*CI control to add.* Before any Docker build, validate both Compose
files with `docker compose … config --quiet`.

**Status: open, P0.**

# 5. Application installed as a wheel — resolved

The application is no longer installed editable. The builder now runs
`pip install --no-cache-dir --no-build-isolation --no-deps .`; the
installed virtualenv is copied into the final stage; the source tree
is no longer needed at runtime. The start script no longer looks for
`pyproject.toml` or an application tree — it directly checks
`"${VENV_DIR}/bin/python" -c "import alirpunkto"`.

# 6. Wheel completeness — correctly tested

A wheel installation can import fine yet be unusable if it omits
Chameleon templates, translation catalogues, LDAP schemas or other
data files. The new test: 1. builds the real wheel; 2. opens its ZIP
archive; 3. collects the Git-tracked files under `alirpunkto/`;
4. requires every tracked file to appear in the wheel. Markedly more
reliable than a mere import test.

*Light reserve.* The test checks Git-tracked files, not generated or
needed-but-untracked files. It nevertheless fits the main risk.

# 7. Binary distributions enforced — largely resolved

Dependencies install with `--only-binary=:all:
--no-binary=pyramid-chameleon,pyramid-handlers,validate-email`. Any
new sdist-only dependency will fail the build explicitly unless added
to the allowed list. The three current exceptions are described as
pure-python packages producing `py3-none-any` wheels.

The tests check the presence of `--only-binary=:all:`, the exact
identity of the exceptions, the effective presence of each exception
in the runtime lock, and the absence of compilers and `*-dev`
packages.

*Reserve.* The "pure python" nature of the three exceptions is
asserted in the code and the commit but not structurally validated in
the test. The test could build each wheel and refuse a
platform-specific wheel, a wheel containing a native library, or any
tag other than `py3-none-any`.

# 8. Compilers removed from every stage — resolved

The builder no longer installs `build-essential`, `python3-dev`, the
LDAP/SSL headers or the XML and image dev libraries — only Python,
`python3-venv` and the CA certificates. The runtime keeps only Python
and the certificates, apart from explicitly enabled diagnostics.

# 9. Limited runtime copy — resolved

The final stage no longer does `COPY .`. It copies only the
virtualenv, `production.ini`, `.env.example`,
`apply_server_overrides.py` and `start_pyramid.sh`. The context now
also excludes `.github/`, `requirements-test.lock`,
`requirements-quality.lock`, `development.ini`, the tests, the tools
and the documentation.

# 10. Dependency installation at startup

**Production — resolved.** `start_pyramid.sh` runs no pip
installation any more; the image launches exactly what was built.

**Test stack — still dynamic.** `start_test_pyramid.sh` still installs
the test lock at startup when `INSTALL_EXTRAS_TESTING=true`, mounted
read-only from the host. Acceptable for development, but startup then
needs index access, the result depends on artefact availability, the
healthcheck waits for the install, and the container test is not fully
autonomous. A dedicated test image built from a separate Docker stage
would be more deterministic.

# 11. Ubuntu snapshots — correct mechanism, incomplete wiring

Every Dockerfile now offers `ARG UBUNTU_SNAPSHOT=""`; when set, the
deb822 file receives `Snapshot: YYYYMMDDTHHMMSSZ`. Ubuntu 24.04
supports this option, and snapshot identifiers do use that format. The
mode remains deliberately optional: empty, current Ubuntu archives;
set, the archive state at the chosen instant.

*Current limit.* Because of the duplicate `args` key, the snapshot is
not correctly wired for the production LDAP service. The mechanism is
therefore correctly implanted in the Dockerfiles, correctly wired in
the test stack, incorrectly wired in the production Compose.
*Partially resolved.*

# 12. Image train tests

Ten new static and semi-dynamic checks verify: the non-editable
install; the binary policy; the absence of compilers; the allowlist
runtime copy; the reduced Docker context; the presence of the helper;
the snapshot mechanism; the absence of runtime pip in production; the
test-lock mount; the real wheel parity.

These tests are useful, but they do not really analyse the YAML
structure. The snapshot check merely searches for the string
`ALIRPUNKTO_UBUNTU_SNAPSHOT` in the Compose file, so it does not
detect: a duplicated YAML key; an argument placed in the wrong
service; an overwritten argument; an indentation mistake; an
unparseable Compose. **Structural coverage insufficient for Compose.**

# 13. Earlier findings still open

**13.1 LDAP reconciliation.** The previous pass's reserves hold:
first-write failures do not condition the second write; the union of
the two sides can restore a stale role or sanction; the scan performs
many searches per member.

**13.2 LDIF transport.** Passwords and the main profile data left
`argv`, but other personal data remains there: pseudonyms, UUIDs,
roles, languages, nationalities. A JSON-on-stdin or 0600-file
interface remains preferable.

**13.3 Missing LDIF password.** An absent password variable can still
be replaced by an empty string and hashed.

**13.4 Encrypted LDAP.** LDAPS certificates are validated when LDAPS
is enabled, but the shipped stacks still default to cleartext LDAP.

**13.5 Periodic reminders.** Still triggered inside `NewRequest`.

**13.6 .env.example.** `MAIL_USE_TLS`/`MAIL_USE_SSL` remain
incompatible with the variables actually read, and `LDAP_CA_CERT_FILE`
is undocumented.

**13.7 Quality debt.** mypy not blocking; Ruff limited to the F rules
with `F841` ignored; minimum coverage at 68%; Certbot and CSP
uncovered.

# 14. Revised priorities

**P0 — reopened.** Fix the production Compose: immediately merge the
two `args` blocks of the LDAP service, then add a mandatory
`docker compose … config --quiet` validation preceding the build and
the smoke test.

**P1 — image nearly finished.** Resolved: non-editable wheel; minimal
runtime context; no compilers; enforced binary dependencies; APT
snapshot available; helper actually copied. To complete: 1. finally
run the Docker smoke test in GitHub Actions; 2. build an autonomous
test image; 3. verify the sdist exceptions really produce universal
wheels; 4. make the snapshot mandatory for release builds.

**P2 — application security.** 1. finish the transactional coherence
of the groups; 2. remove all personal data from `argv`; 3. refuse
missing passwords; 4. enable and test LDAPS in Compose.

**P3 — operations.** 1. move the reminders out of the HTTP cycle;
2. fix `.env.example`; 3. optimise the LDAP scan; 4. test the Certbot
renewal; 5. enable and test a CSP.

# 15. Conclusion

Commit `72e65db…` brings excellent finishing to the Pyramid image:
cleanly installed wheel; sources absent from the runtime; reduced
context; compilers removed; explicit binary strategy; optional APT
reproducibility; wheel completeness really tested.

It also fixes a particularly important defect the earlier audits had
missed: the Waitress override helper never entered the Docker context.

However, adding the snapshot introduced a duplicate `args` key in the
production Compose. Until that mistake is fixed, the stack must be
considered potentially unstartable and the Docker P0 stays open.

**Current evaluation: 8.4/10.** After merging the two `args` blocks
and an observable successful smoke workflow, the evaluation could
immediately return to around 8.8/10.
