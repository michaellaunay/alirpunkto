# Dependency audit and train 0113

**Date**: 2026-09-12 · **Auditor**: Claude (development assistant) · **Reference**: master `00bd677` (train 0112) · **Counter-review**: ChatGPT, versions 2 and 3 of the steering file (Python 3.14 qualified separately, then withdrawn from scope) · **Decision**: Python 3.12 remains the target interpreter; the 3.14 qualification is a separate, deferred lot.

## Chain of scores

This audit does not score the project: it covers the four hashed locks and the quality CI run, red since 1 September. It extends the series (12th internal pass of 20/08: 8.8) without changing it.

## 1. Method

Reading of the four locks (`requirements.lock`, `-test`, `-quality`, `-e2e`), comparison of every pin with the latest stable, non-yanked release on PyPI, `pip-audit --no-deps` on each lock, `pip-compile --upgrade` under Python 3.12.3, then a full run: test suite, CI-exact ruff, bandit, pip-audit, mypy, wheel build, and a ZODB round trip between the previous and the new Zope stack.

**Count**: 106 distinct packages across the four locks (the first version of this audit said 105; the counter-review was right — `pip` only appears in the quality lock and had been lost in deduplication). 74 up to date, 30 behind, 2 known vulnerabilities.

## 2. Vulnerabilities

### 2.1 WebOb 1.8.10 — PYSEC-2026-3943 / CVE-2026-54770 / GHSA-6hx8-3wjj-gr8g — P0, fixed (commit A)

Up to 1.8.10, `Response._make_location_absolute()` checked the scheme and the leading `//` on the raw value but resolved it with `urllib.parse.urljoin()`, which on Python ≥ 3.10 first strips leading C0 control characters and spaces: `" //evil.example/"` passed both guards and left the host. The `HTTPFound` family bypassed the guard entirely. Since the `pip-audit (blocking)` job of `quality.yml` only ignores PYSEC-2026-3447, the quality CI was red (counter-review: failure observed in the 1 September log).

Fix: `webob==1.8.11` alone, in the three locks, with no other movement (`pip-compile --upgrade-package webob`). `tests/test_webob_redirect_lock.py` locks both layers: the advisory's reproducers against the library (5 red on 1.8.10, green on 1.8.11) and `safe_local_redirect` from train 0063, which already refused these payloads (`strip()` removes the space; a bare C0 byte is not a rooted path), plus a `>= 1.8.11` floor per lock.

### 2.2 setuptools 80.10.2 — PYSEC-2026-3447 / CVE-2026-59890 — unchanged, ignore now dated

Still blocked: `deform 3.0.1` declares `setuptools<81`, `pyramid 2.1` declares `<82`, and **both import `pkg_resources` at runtime** (`pyramid/asset.py`, `deform/template.py`). Fixed in 83.0.0. The CVE concerns sdist building on macOS (Unicode normalisation of `MANIFEST.in`), outside the execution path and outside the image. The ignore stays and now carries its review date and its trigger (deform 3.1 or pyramid 2.2). AlirPunkto's own direct `pkg_resources` import is migrated (commit C) — hygiene, not a lift of the block.

## 3. Inventory and decisions

| Package | Before | After | Decision |
|---|---|---|---|
| webob | 1.8.10 | 1.8.11 | **CVE**, commit A |
| cryptography | 50.0.0 | 50.0.1 | patch, taken |
| PyJWT | 2.13.0 | 2.14.0 | taken; 39 SSO/Keycloak/seal tests green |
| jwcrypto | 1.5.8 | 1.6.0 | taken (via python-keycloak) |
| python-dotenv | 1.2.2 | 1.2.3 | taken; the 0080 `find_dotenv` scenario green |
| zope.interface / zope.proxy / persistent / BTrees / zodbpickle | 8.5 / 7.2 / 6.7 / 6.4 / 4.4 | 8.6 / 7.3 / 6.8 / 6.5 / 4.5 | taken; ZODB round trip §4.3 |
| anyio, charset-normalizer, idna, packaging, cffi | — | — | transitive, taken |
| coverage | 7.15.2 | 7.16.0 | taken; 72.76 % → 72.69 %, no line lost, gate 68 unchanged |
| pygments, soupsieve | — | — | taken |
| ruff | 0.16.1 | 0.16.7 | taken; CI-exact green (F rules only) |
| cyclonedx-python-lib, librt, filelock, platformdirs, msgpack, stevedore, pip-api, pip | — | — | quality transitives, taken |
| greenlet | 3.5.4 | 3.5.5 | taken (e2e) |
| **mypy** | 1.20.2 | 1.20.2 | **not taken**: mypy 2.x tightens defaults, informative job at 132; pyproject bound `<2` |
| **pyee** | 13.0.1 | 13.0.1 | **not taken**: playwright 1.62.0 requires `pyee<14` |
| **setuptools** | 80.10.2 | 80.10.2 | **blocked** (§2.2) |

No bound in `pyproject.toml` was changed: every target sits inside the declared ranges. Outside PyPI, not handled in this train: the `ubuntu:24.04` digest of the four images (to refresh on kuneagi02), the GitHub Actions SHAs, `validate_email` 1.3 (2015) and `pyramid_handlers` 0.5 (2012), unmaintained.

## 4. Proof

### 4.1 Commit A — webob alone

- `pip-audit --no-deps --ignore-vuln PYSEC-2026-3447` on the previous locks: 1 vulnerability (webob); on the new ones: none, 2 ignored.
- Diff of the three locks: only `webob==` and its two hashes.
- `tests/test_webob_redirect_lock.py`: 14 green on 1.8.11; webob forced back to 1.8.10: 5 red (4 hijacked `Response.location` + the `HTTPFound` path), the app-guard tests stay green.
- Full suite on a fresh clone, Python 3.12.3: 1086 green, coverage 72.76 %.

### 4.2 Commit B — refresh

- `pip check` clean; 1100 green (1086 + 14), coverage 72.69 %; ruff 0.16.7 CI-exact green; bandit -ll green; pip-audit on the four locks: no vulnerability, 2 ignored; mypy 132 before and after.
- Invariants checked in the locks: `mypy==1.20.2`, `pyee==13.0.1`, `setuptools==80.10.2`.

### 4.3 ZODB round trip (the train's only real risk)

A `Data.fs` of 50 members built with the real models (`appmaker`, `Members`, `Member`, `MemberDatas`) by the previous stack (zodbpickle 4.4, persistent 6.7, BTrees 6.4, zope.interface 8.5): opened by the new stack, `run_pending_upgrades` finds nothing pending, all 50 members read back and checked, one member added, one modified, `db.pack()`, reopen — then the packed file is reread by the old stack. **Limit**: this is not kuneagi02's Data.fs; the step on a copy of production remains due before deployment.

### 4.4 Commit C — importlib.resources

- 1102 green (1100 + 2); `grep pkg_resources` empty on `alirpunkto/`, `tools/` and the two Docker scripts.
- Wheel built with `python -m build`, installed `--no-deps` on the runtime lock in a fresh venv (the Pyramid image model): both template directories resolve to real paths, `form.pt` present.

## 5. What was not done here

- kuneagi02's real Data.fs (§4.3), the Docker image builds, `smoke.yml` and `test-stack.yml`: for the CI and Michaël.
- The CI logs (302 to blob from the sandbox): the 1 September failure is the one reported by the counter-review.
- The `ubuntu:24.04` digest and the Actions tags (domains outside the sandbox allow-list).
- Python 3.14: withdrawn from scope by the 12/09 decision; the counter-review noted that WebOb 1.8.11 adds `legacy-cgi>=2.6 ; python_version>='3.13'`, so a lock computed under 3.12 does not hold for 3.13+ — to be picked up on qualification day.

## 6. Deployment

kuneagi02: `cd ~/alirpunkto/docker && git pull && docker compose build alirpunkto-pyramid && docker compose up -d alirpunkto-pyramid`, then `/login` and a `/modify_member` (the LDAP sync at login, fix 0112, exercises ZODB reads and writes). kuneagi01 (historical production pinned at `e6603d22`): do not touch; the 0087 file will apply on a master that includes 0113.

## Log

- 2026-09-12: first version of the audit (Claude), ChatGPT counter-review v2 (Python 3.14 qualified separately, `pkg_resources` imported by the application, conditional `legacy-cgi`, count 106), Python 3.12 decision, counter-review v3, execution of train 0113 in three commits and filing of this audit.
- 2026-10-23: follow-up — six advisories published since (PyJWT, urllib3, certifi) turned the quality CI red again; three pins raised, see [train 0116](20261023_dependency_audit_train_0116.md).
