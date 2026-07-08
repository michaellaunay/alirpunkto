# Testing

> Status: current documentation.
> Location: `tests/` (over 420 tests as of 2026-07-08).

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
  locale and for every member type.
- **Security, per audit finding**: each fixed finding has its file —
  `test_security_1_3_password_hashing.py` (`{SSHA}` hashing, ZODB purge),
  `test_ldap_schema_tolerance.py`, `test_session_cookie_budget.py`.
- **Migration and provisioning**: `test_migrate_ldap_legacy_remote.py`,
  `test_ldap_provision.py`.
- **Incident non-regression**: `test_zodb_repopulation_from_ldap.py`
  (rebuilding the ZODB from LDAP).

## Project convention

Every fix born from an audit or a field incident is **locked by dedicated
tests**, dated in their docstring: the suite tells the story of the
findings and forbids their return. A fix without a test is not considered
closed.
