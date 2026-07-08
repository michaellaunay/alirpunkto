"""The ZODB repopulates itself from LDAP — the recipe behind
``tools/ldap_provision.py``'s "delete var and restart" step.

When the object store is fresh (the admin removed ``var/``) and a user logs
in, ``update_member_from_ldap`` finds no member in the ZODB and rebuilds it
from the LDAP entry via ``append_member``. These tests lock that behaviour:
the member is created with the LDAP data, its ``password`` and
``password_confirm`` stay ``None`` (finding 1.3), and an unknown legacy
``employeeType`` degrades to ORDINARY instead of crashing.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import alirpunkto.utils as utils
from alirpunkto import secret_manager as sm
from alirpunkto.constants_and_globals import (
    ADMIN_PASSWORD,
    LDAP_PASSWORD,
    MAIL_PASSWORD,
    SECRET_KEY,
)
from alirpunkto.models.member import Members, MemberTypes


@pytest.fixture(autouse=True)
def _secrets_and_members(monkeypatch):
    for name, value in (
        (SECRET_KEY, "dGVzdF96b2RiX3JlcG9wdWxhdGlvbg=="),
        (LDAP_PASSWORD, "test-ldap-pw"),
        (ADMIN_PASSWORD, "test-admin-pw"),
        (MAIL_PASSWORD, "test-mail-pw"),
    ):
        monkeypatch.setenv(name, value)
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")
    # a FRESH object store, exactly like after `mv var var.bak`
    Members._instance = Members()
    yield
    Members._instance = None
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")


def _ldap_entry(**overrides):
    values = {
        "cn": "Scilovema",
        "sn": "Launay",
        "mail": "member@example.org",
        "employeeType": "COOPERATOR",
        "givenName": "Michaël",
        "nationality": "FR",
        "birthdate": "1973-01-19T12:00:00",
        "preferredLanguage": "fr",
        "secondLanguage": "en",
        "thirdLanguage": "eo",
        "cooperativeBehaviourMark": "0",
        "numberSharesOwned": "8",
        "dateEndValidityYearlyContribution": "2026-07-28T12:00:00",
        "uniqueMemberOf": "cn=cooperatorsGroup,dc=t,dc=org",
    }
    values.update(overrides)
    return SimpleNamespace(**{k: SimpleNamespace(value=v)
                              for k, v in values.items() if v is not None})


def _ldap_conn(entry):
    conn = MagicMock()
    conn.entries = [entry]
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_fresh_zodb_is_repopulated_from_ldap_at_login():
    oid = "2dc94f27-a8b8-4aec-8560-c8006e2b72a3"
    assert oid not in Members._instance          # the store is fresh
    with patch.object(utils, "get_connection", lambda request: None), \
         patch.object(utils, "get_ldap_connection",
                      return_value=_ldap_conn(_ldap_entry())):
        member = utils.update_member_from_ldap(oid, MagicMock())

    assert member is not None
    assert oid in Members._instance              # ...and now it is not
    stored = Members._instance[oid]
    assert stored.email == "member@example.org"
    assert stored.pseudonym == "Scilovema"
    assert stored.type == MemberTypes.COOPERATOR
    assert stored.data.fullname == "Michaël"
    assert stored.data.birthdate == datetime(1973, 1, 19, 12, 0, 0)
    # finding 1.3: nothing credential-shaped enters the rebuilt ZODB
    assert stored.data.password is None
    assert stored.data.password_confirm is None


def test_unknown_legacy_employee_type_degrades_to_ordinary():
    oid = "11111111-2222-3333-4444-555555555555"
    entry = _ldap_entry(employeeType="BOARD_MEMBER")   # pre-migration value
    with patch.object(utils, "get_connection", lambda request: None), \
         patch.object(utils, "get_ldap_connection",
                      return_value=_ldap_conn(entry)):
        member = utils.update_member_from_ldap(oid, MagicMock())
    assert member is not None
    assert Members._instance[oid].type == MemberTypes.ORDINARY
