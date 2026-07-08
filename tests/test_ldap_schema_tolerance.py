"""Tolerance to lagging directory schemas (field incident of 2026-07-07).

The updated application asks LDAP for member attributes that a legacy
alirpunkto directory does not define (``cooperativeBehaviourMarkUpdate``,
``IBAN``, ``dateErasureAllData``). ldap3 validates requested names client-side
(``check_names``) against the schema loaded at bind time and raises
``LDAPAttributeError`` before the search is even sent — which turned every
login/SSO attempt into a 500. These tests lock the fix:
``schema_safe_attributes()`` drops the unknown names with an explicit warning,
so ``update_member_from_ldap()`` degrades to "attribute absent" (which its
value extraction already tolerates) instead of crashing, while a modern schema
still receives the full list.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ldap3.core.exceptions import LDAPAttributeError
from ldap3.utils.ciDict import CaseInsensitiveWithAliasDict

import alirpunkto.utils as utils
from alirpunkto import secret_manager as sm
from alirpunkto.constants_and_globals import (
    ADMIN_PASSWORD,
    LDAP_PASSWORD,
    MAIL_PASSWORD,
    SECRET_KEY,
)
from alirpunkto.ldap_factory import schema_safe_attributes

_LEGACY_NAMES = [
    "cn", "mail", "employeeType", "sn", "uid", "employeeNumber", "isActive",
    "givenName", "nationality", "birthdate", "preferredLanguage",
    "secondLanguage", "thirdLanguage", "cooperativeBehaviourMark",
    "numberSharesOwned", "dateEndValidityYearlyContribution", "uniqueMemberOf",
]
_MODERN_ONLY = ["cooperativeBehaviourMarkUpdate", "IBAN", "dateErasureAllData"]


def _schema(names):
    types = CaseInsensitiveWithAliasDict()
    for name in names:
        types[name] = object()
    return types


LEGACY_SCHEMA = _schema(_LEGACY_NAMES)
MODERN_SCHEMA = _schema(_LEGACY_NAMES + _MODERN_ONLY)


@pytest.fixture(autouse=True)
def _secrets_env(monkeypatch):
    for name, value in (
        (SECRET_KEY, "dGVzdF9zY2hlbWFfdG9sZXJhbmNl"),
        (LDAP_PASSWORD, "test-ldap-pw"),
        (ADMIN_PASSWORD, "test-admin-pw"),
        (MAIL_PASSWORD, "test-mail-pw"),
    ):
        monkeypatch.setenv(name, value)
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")
    yield
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")


def _conn(attribute_types):
    conn = MagicMock()
    conn.server = SimpleNamespace(
        schema=SimpleNamespace(attribute_types=attribute_types))
    return conn


# --------------------------------------------------------------------------- #
# the helper itself
# --------------------------------------------------------------------------- #
def test_drops_unknown_attributes_and_warns(caplog):
    conn = _conn(LEGACY_SCHEMA)
    wanted = ["cn", "cooperativeBehaviourMarkUpdate", "iban",
              "dateErasureAllData", "mail"]
    with caplog.at_level(logging.WARNING):
        kept = schema_safe_attributes(conn, wanted)
    assert kept == ["cn", "mail"]
    assert "cooperativeBehaviourMarkUpdate" in caplog.text
    assert "alirpunkto_schema.ldif" in caplog.text        # actionable hint


def test_modern_schema_keeps_everything_case_insensitively():
    conn = _conn(MODERN_SCHEMA)
    wanted = _LEGACY_NAMES + ["cooperativeBehaviourMarkUpdate",
                              "iban", "dateErasureAllData"]
    # 'iban' (lowercase) must match the schema's 'IBAN'
    assert schema_safe_attributes(conn, wanted) == wanted


def test_bails_out_without_a_real_schema():
    wanted = ["cn", "anything"]
    assert schema_safe_attributes(MagicMock(), wanted) == wanted
    no_schema = SimpleNamespace(server=SimpleNamespace(schema=None))
    assert schema_safe_attributes(no_schema, wanted) == wanted
    assert schema_safe_attributes(SimpleNamespace(server=None), wanted) == wanted


# --------------------------------------------------------------------------- #
# the field incident, end to end through update_member_from_ldap
# --------------------------------------------------------------------------- #
def _ldap3_faithful_conn(attribute_types, captured=None):
    """search() raises exactly like ldap3's check_names on unknown attributes."""
    conn = _conn(attribute_types)

    def fake_search(base, search_filter, attributes=None, **_kwargs):
        for name in attributes or []:
            if name not in attribute_types:
                raise LDAPAttributeError(f"invalid attribute type {name}")
        if captured is not None:
            captured["attributes"] = list(attributes or [])
        conn.entries = []
        return True

    conn.search = fake_search
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_update_member_from_ldap_survives_a_legacy_schema():
    """Before the fix this raised LDAPAttributeError — a 500 on every login."""
    cm = _ldap3_faithful_conn(LEGACY_SCHEMA)
    with patch.object(utils, "get_ldap_connection", return_value=cm):
        result = utils.update_member_from_ldap("aaaaaaaa-0000", MagicMock())
    assert result is None                        # user not found, no crash


def test_update_member_from_ldap_still_requests_all_on_modern_schema():
    captured = {}
    cm = _ldap3_faithful_conn(MODERN_SCHEMA, captured)
    with patch.object(utils, "get_ldap_connection", return_value=cm):
        utils.update_member_from_ldap("aaaaaaaa-0000", MagicMock())
    assert "cooperativeBehaviourMarkUpdate" in captured["attributes"]
    assert "iban" in captured["attributes"]
    assert "dateErasureAllData" in captured["attributes"]
