"""Unit tests for ``secret_manager.get_secret`` env handling (audit finding 2.16).

Secrets are read from the environment and the variables are then removed. The
removal used ``del os.environ[name]``, which raises ``KeyError`` when the
variable is absent — masking the intended ``ValueError`` for a missing
SECRET_KEY and crashing when an optional password is unset. The fix uses
``os.environ.pop(name, None)``.
"""

from __future__ import annotations

import os

import pytest

from alirpunkto import secret_manager as sm
from alirpunkto.constants_and_globals import (
    ADMIN_PASSWORD,
    LDAP_PASSWORD,
    MAIL_PASSWORD,
    SECRET_KEY,
)


@pytest.fixture
def fresh_secret_manager(monkeypatch):
    """Force get_secret to re-initialize and restore its cache afterwards.

    ``monkeypatch`` restores ``os.environ`` automatically at teardown.
    """
    had_cache = hasattr(sm.get_secret, "secrets")
    saved = sm.get_secret.secrets if had_cache else None
    if had_cache:
        del sm.get_secret.secrets
    yield sm
    if had_cache:
        sm.get_secret.secrets = saved
    elif hasattr(sm.get_secret, "secrets"):
        del sm.get_secret.secrets


def test_missing_secret_key_raises_valueerror_not_keyerror(
    fresh_secret_manager, monkeypatch
):
    monkeypatch.delenv(SECRET_KEY, raising=False)

    with pytest.raises(ValueError, match="SECRET_KEY"):
        fresh_secret_manager.get_secret(None)  # force initialization


def test_missing_password_env_vars_do_not_raise(fresh_secret_manager, monkeypatch):
    monkeypatch.setenv(SECRET_KEY, "a-secret")
    monkeypatch.delenv(LDAP_PASSWORD, raising=False)
    monkeypatch.delenv(ADMIN_PASSWORD, raising=False)
    monkeypatch.delenv(MAIL_PASSWORD, raising=False)

    fresh_secret_manager.get_secret(None)  # must not raise KeyError

    assert fresh_secret_manager.get_secret(LDAP_PASSWORD) is None
    assert fresh_secret_manager.get_secret(SECRET_KEY) == "a-secret"


def test_secrets_are_removed_from_environment_after_init(
    fresh_secret_manager, monkeypatch
):
    monkeypatch.setenv(SECRET_KEY, "a-secret")
    monkeypatch.setenv(LDAP_PASSWORD, "ldap-pw")
    monkeypatch.setenv(ADMIN_PASSWORD, "admin-pw")
    monkeypatch.setenv(MAIL_PASSWORD, "mail-pw")

    fresh_secret_manager.get_secret(None)

    assert SECRET_KEY not in os.environ
    assert LDAP_PASSWORD not in os.environ
    assert ADMIN_PASSWORD not in os.environ
    assert MAIL_PASSWORD not in os.environ
    assert fresh_secret_manager.get_secret(LDAP_PASSWORD) == "ldap-pw"
