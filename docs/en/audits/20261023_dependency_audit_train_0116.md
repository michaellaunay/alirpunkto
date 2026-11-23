# Dependency audit follow-up — train 0116 (October 2026)

**Date**: 2026-10-23 · **Auditor**: Claude (development assistant) · **Reference**: master `023d2c77` (train 0115) · **Parent file**: [dependency audit and train 0113](20260912_dependency_audit_train_0113.md) · **Decision**: raise three pins, nothing else.

## 1. Finding

The `quality` workflow is red on both 20 October commits (`d8d8c9cb`, `023d2c77`) while `Tests`, `smoke` and `test-stack` are green. The commits are not at fault: the `pip-audit (blocking)` job fails on advisories published between the last green run (12 September) and 20 October, and a third package joined since. The `mypy (informative)` job shows red (133 errors) but stays `continue-on-error`: it never failed the workflow.

| Package | Pin | Advisory | Fix | Taken |
|---|---|---|---|---|
| PyJWT | 2.14.0 | PYSEC-2026-4141 / CVE-2026-101918 (`RecursionError` on a deeply nested JSON payload, escaping `PyJWTError`); PYSEC-2026-4183 / CVE-2026-102275 (`OKPAlgorithm.from_jwk` does not check `d` against `x`) | 2.15.0 | **2.15.1** (28/09) |
| urllib3 | 2.7.0 | PYSEC-2026-4175 / CVE-2026-97687 (proxy TLS settings overwritten by the target's); PYSEC-2026-4176 / CVE-2026-97688 (infinite loop on trailing bytes after a Deflate stream); PYSEC-2026-4177 / CVE-2026-97689 (unbounded chunk-size field in streaming) | 2.8.0 | **2.8.0** (15/09) |
| certifi | 2026.7.22 | PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2 (`emSign ECC Root CA - G3` root, eMudhra intermediates with compromised keys) | 2026.10.19 | **2026.10.23** (23/10) |

Actual exposure: `views/sso_login.py` calls `jwt.decode` with signature verification, so the nested-payload path is only reachable with a token minted by the Keycloak back channel; urllib3 and certifi carry the `requests`/`python-keycloak` calls to Keycloak. Low, but the CI gate is blocking by design (decision of the 4th external pass).

## 2. Fix

`pip-compile --upgrade-package pyjwt --upgrade-package urllib3 --upgrade-package certifi` on each of the three locks, seeded with the previous lock: the diff holds only the three pins and their hashes. The header loses `--no-index`, a trace of September's PyPI-less sandbox (local wheelhouse); resolution here ran against PyPI. The e2e lock carries none of the three packages and stays untouched.

`tests/test_october_2026_cve_floors.py` locks two layers: the PYSEC-2026-4141 reproducer against the library (a payload nested 10,000 levels deep must raise a `PyJWTError`, not a bare `RecursionError`), the absence of the compromised emSign root from the certifi bundle, and one floor per package per lock.

## 3. Proof

- Red on the previous state (September locks and libraries): 11 failures (2 library + 9 floors); green after: 11.
- Full suite: 1166 green (1155 + 11), coverage 74.07 %, gate 68 unchanged.
- CI-exact gates: ruff green, bandit `-ll` green, `pip-audit --no-deps --ignore-vuln PYSEC-2026-3447` on the three locks: no vulnerability, 2 ignored; e2e lock: none.
- No bound of `pyproject.toml` changed (`PyJWT>=2.7.0,<3`, `requests>=2.33.1,<3`).

## 4. Not handled here

- mypy: 133 informative errors (132 in September), non-blocking job, out of scope.
- setuptools 80.10.2 / PYSEC-2026-3447: still blocked by deform 3.0.1 and pyramid 2.1 (§2.2 of the 0113 file), ignore kept.
- The Docker images vendor certifi through the runtime lock: rebuild `alirpunkto-pyramid` on kuneagi02 at deployment (the certifi advisory asks for it explicitly).

## 5. Follow-up of 24 October — train 0118

The `quality` workflow went red again on `34a224f7` and `38dedcf7`: two new advisories published after the 0116 locks were computed.

| Package | Pin | Advisory | Fix | Decision |
|---|---|---|---|---|
| filelock | 3.32.6 (quality lock only, via cachecontrol under pip-audit) | CVE-2026-112907 / 112913 / 112940 (SQLite-backed and soft locks abused by another local account) | 4.2.1 | **4.2.4** (19/10), `pip-compile --upgrade-package filelock` on the quality lock alone; `>= 4.2.1` floor in `tests/test_october_2026_cve_floors.py` |
| setuptools | 80.10.2 | GHSA-xmj3-9gf7-h52w (installation path `Wheel.install_as_egg`, Windows, hostile wheel's `namespace_packages.txt`) | 84.1.0 | **dated ignore** in `quality.yml`, same chain and same class as PYSEC-2026-3447: deform 3.0.1 (`setuptools<81`) and pyramid 2.1 (`<82`) are still the latest PyPI releases on 24/10; both ignores lift together |

`AGENTS.md` quotes the new command verbatim (`tests/test_agent_harness.py` requires it) and a test checks that each ignore carries its review date.

## 6. Follow-up of 23 November — train 0127

The `quality` workflow has been red since `dda6b466` and `636eddc2` (30 October) on `pip-audit` alone; `Tests`, `smoke` and `test-stack` are green. Nine advisories on three packages, all published after the 0118 locks were computed.

| Package | Pin | Advisory | Fix | Decision |
|---|---|---|---|---|
| pyasn1 | 0.6.4 (three locks — runtime, via ldap3) | CVE-2026-119194 / 119195 / 119196 / 119197 (quadratic CPU time in four decoder paths: schemaless containers with many long tag IDs, fragmented OCTET and BIT STRINGs, REAL with a large mantissa) | 0.6.5 | **0.6.5** |
| soupsieve | 2.9.2 (test lock only, via beautifulsoup4 under WebTest) | CVE-2026-126190 / 126191 / 126192 / 126193 (polynomial or exponential time, or unbounded recursion, on hostile selectors or deeply nested documents) | 4.0.0 for the last one | **4.1.3**; beautifulsoup4 4.15.0 accepts it unchanged |
| msgpack | 1.2.2 (quality lock only, via cachecontrol under pip-audit) | CVE-2026-114613 (the C extension leaks a decoded map value per rejected key) | 1.2.3 | **1.2.4** |

Actual exposure: pyasn1 is the only runtime package — ldap3 decodes the directory's answers with it, and the directory is a trusted peer on the internal network; soupsieve and msgpack never reach the production image. `pip-compile --upgrade-package` per lock, seeded with the previous one: the diff holds only these pins and their hashes; the e2e lock carries none of the three. `tests/test_november_2026_cve_floors.py` locks one floor per package per lock (red on the previous locks: 5 failures) and a BER round trip of an ldap3 bind request on the raised pyasn1. No bound of `pyproject.toml` changed, no new ignore.

The production venv on kuneagi01 is not rebuilt by the deployment: reinstall it from `requirements.lock` with `--require-hashes` to receive pyasn1 0.6.5.

## Log

- 2026-10-23: diagnosis of the two red runs, three pins raised, lock test, filing of this note.
- 2026-10-24: follow-up (§5) — filelock raised in the quality lock, second dated setuptools ignore, train 0118.
- 2026-11-23: follow-up (§6) — pyasn1, soupsieve and msgpack raised, November floor test, train 0127.
