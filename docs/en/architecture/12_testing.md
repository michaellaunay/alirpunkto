# Testing

> Status: current documentation.
> Location: `tests/` (over 580 tests as of 2026-07-25).

## Running the suite

```bash
export SECRET_KEY=... LDAP_PASSWORD=... ADMIN_PASSWORD=... MAIL_PASSWORD=...
mkdir -p var
pytest tests
```

The four secrets must exist in the environment (see
`alirpunkto/secret_manager.py`) and `var/` must exist for the test ZODB.

## LDAP mocked by default

Outside the Docker stack, `ldap_factory` automatically switches to a mocked
server (`MOCK_SYNC`, `OFFLINE_SLAPD_2_4` schema) as soon as
`PYTEST_CURRENT_TEST` is set and `TEST_WITH_DOCKER_LDAP` is not: the suite
runs without a directory. Real integration tests go through the local
stack (`docker/test-docker-compose.yaml`, `docker/README_TEST_LOCAL.md`).

## Test families

- **Views and models**: classic unit tests (`test_views.py`,
  `test_home_sso.py`, …).
- **Internationalization**: rendering the registration e-mails in every
  locale and for every member type; rendering the result e-mails
  (7 languages × 2 templates × 2 `textual` modes), `.po`/`.mo` parity
  through the real localizer, recipient preferred language and the locale
  negotiator.
- **Security, per audit finding**: each fixed finding has its file —
  `test_security_1_3_password_hashing.py` (`{SSHA}` hashing, ZODB purge),
  `test_ldap_schema_tolerance.py`, `test_session_cookie_budget.py`.
- **Migration and provisioning**: `test_migrate_ldap_legacy_remote.py`,
  `test_ldap_provision.py`.
- **Incident non-regression**: `test_zodb_repopulation_from_ldap.py`
  (rebuilding the ZODB from LDAP).

## Continuous integration

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs the suite
on Python 3.11 and 3.12 on every push and pull request: pip cache keyed on
`setup.py` (`cache-dependency-path`), creation of `var/`, export of the
test secrets, `junitxml` report published as an artifact. A fix is only
considered deliverable with the matrix green.

## Project convention

Every fix born from an audit or a field incident is **locked by dedicated
tests**, dated in their docstring: the suite tells the story of the
findings and forbids their return. A fix without a test is not considered
closed.

## 2026-07-30 campaign

The suite grew from about 580 to **more than 800** tests. Durable harness
lessons, encoded in the tests themselves: the **mock `ldap3`** directory
(`client_strategy=MOCK_SYNC`) binds **anonymously** (no fictitious admin)
and returns dates as strings — adapters parse them; rendering templates
under `pytest` requires the **threadlocal** pushed
(`pyramid.threadlocal.manager.push({'request': …, 'registry': …})`); a
test rendering a `deform` form pins `deform.form.Form.default_renderer`
to stay hermetic to the global renderer another test installs; the date
widget submits a **peppercorn** structure (`__start__`/`date`/`__end__`),
exactly as a browser does; and the dynamic-group truth table is locked
**case by case** against ticket #148 by parametrized tests.

## 2026-08-01 campaign

The suite reaches **867 tests**. The lesson that will stick:
`@view_config` is a *veneer* — it returns the function unchanged and
marks it for `config.scan`. A function slid **between** the decorator
and the `def` silently becomes THE view of the route: tests calling the
view directly stay green, production serves a 500. The group-4 fix
reattaches the decorator and adds a **structural lock**
(`test_the_view_config_decorates_the_view_itself`). Also gained: the
issue #55 matrix is locked **case by case** by a parametrized table
mirroring the ticket (nineteen regimes), and template renderings assert
against the **catalogue msgstr**, never the inline fallback texts.

## 2026-08-01 campaign, continued: 894 tests

Two more lessons. **A validator built at class definition freezes at
import**: the birthdate age bound (`get_majority_date()`) dated from
process start — after a few weeks the form refused candidates who had
since come of age. The cure is **`colander.deferred`**, resolved at
every `bind` hence at every request, locked by a test that shifts the
majority by sixty days and checks the bind follows. And on the harness
side: a verification clone needs its `var/` — without it the ZODB fails
in `zc.lockfile` and six functional tests error out as ghosts.

## External-audit campaign (2026-08-01): 931 tests

pytest's live logging becomes **opt-in** (`log_cli = false`): the suite
deliberately exercises failure branches — unreachable LDAP, unknown
enum values, refused e-mails — whose `log.error` lines are the verified
behaviour; a green run used to shout dozens of `[ERROR]` lines. Failing
tests keep their captured logs in their own report, and the live stream
returns on demand (`pytest -o log_cli=true`). On the build chain:
dependencies are bounded in `pyproject.toml` (versions measured on the
tested environment), pinned in `requirements.lock` (77 packages,
commented provenance), and the CI installs that lock — its cache key,
once derived from `setup.py`, follows `pyproject.toml` and the lock.
Six packaging tests guard the whole arrangement, `setup.py` included in
its absence.

## Quality gates (2026-08-02): 1022 tests

The CI no longer merely runs the suite: a second workflow
(`quality.yml`) makes **Ruff blocking** (the Pyflakes family; `F841`
as a documented exception, the ratchet's next notch), **Bandit
blocking** from medium severity up (the two SHA-1 uses of the `{SSHA}`
format carry their reasoned `# nosec` — it is the format slapd
consumes), and **pip-audit on the lock** (a single exception,
documented in the workflow itself: `PYSEC-2026-3447`, a transitive
setuptools held back by the deform chain). Measurements preceded the
gates: 137 Ruff findings brought to zero, among them two real
defects — a missing `global DOMAINE` that broke a tool's fallback, and
a stray `from requests import request` that shadowed the view
parameter (and manufactured five Bandit false positives along the
way). Coverage, measured at ~70 %, receives a `--cov-fail-under=68`
floor — a ratchet, not a target. Every GitHub action is pinned by
commit SHA (the readable tag kept in a comment), no out-of-lock
install remains in the workflows (`--allow-unsafe` pins
pip/setuptools/wheel into the lock), and mypy enters as an observer
(`continue-on-error`, 124 errors at adoption).
`tests/test_quality_gates.py` locks the wiring itself: gates invoked,
floor armed, every `uses:` a 40-char SHA, zero out-of-lock installs,
the `cryptography` floor kept. A harness lesson: never "restore" a red
demonstration with `git checkout --` — it brings HEAD back and
destroys uncommitted fixes; only a side copy is safe.

The 0071→0078 trains brought the suite from 957 to **1022 tests**,
locking every gain with a **red demonstration** against the previous
state: Docker startup and server overrides
(`test_docker_startup.py`); the supply chain — three hashed locks,
identical extension, one CI lane each (`test_supply_chain.py`); image
finishing down to **real wheel parity** — the test rebuilds the
application wheel and requires all 449 tracked files
(`test_image_finishing.py`); the LDIF transport on standard input
with enforced required fields (`test_ldif_transport.py`); the generator's **caller**
contract — all three callers source the shared emitter,
emitter↔generator parity via `ast`, compose YAML free of duplicate
keys, the `config --quiet` gate before any build
(`test_ldif_callers.py`); the sealed
SSO token and the cookie budget measured on an incompressible token;
the Keycloak response validation; and group coherence down to
**injected write vetoes** and half-lifted latches that do not
resurrect (`test_group_coherence.py`). Coverage reaches 72.10% over
the 68 floor.
