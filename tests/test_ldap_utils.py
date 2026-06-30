"""Unit tests for the LDAP-facing helpers in ``alirpunkto.utils``.

These tests mock the LDAP connection and assert on the modification operations
that would be sent to the directory. They cover the audit fixes 2.6 (align the
``update_ldap_member`` field names with the model, and the second/third language
update) and 2.9 (the invalid-pseudonym return contract of
``register_user_to_ldap``).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from ldap3 import MODIFY_DELETE, MODIFY_REPLACE

import alirpunkto.utils as utils
from alirpunkto.models.candidature import Candidature
from alirpunkto.models.member import Member, MemberDatas, MemberTypes


_SENTINEL = object()


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _make_member(**data_kwargs) -> Member:
    """Build a Member carrying the given MemberDatas keyword arguments."""
    member = Member(oid="member-1")
    member.email = data_kwargs.pop("email", "member@example.com")
    member.type = data_kwargs.pop("type", MemberTypes.COOPERATOR)
    member.data = MemberDatas(**data_kwargs)
    return member


def _fully_populated_member() -> Member:
    """A member whose every updatable field holds a valid, typed value."""
    return _make_member(
        email="member@example.com",
        type=MemberTypes.COOPERATOR,
        fullname="John",
        fullsurname="Doe",
        description="A member",
        nationality="FR",
        birthdate=datetime(1990, 1, 1),
        lang1="en",
        lang2="fr",
        lang3="es",
        is_active=True,
        cooperative_behaviour_mark=12.5,
        cooperative_behaviour_mark_update=datetime(2026, 1, 1),
        number_shares_owned=3,
        date_end_validity_yearly_contribution=datetime(2026, 12, 31),
        iban="FR7612345",
        unique_member_of="cn=cooperators,ou=groups,dc=example,dc=com",
        date_erasure_all_data=datetime(2030, 1, 1),
    )


def _run_update(member, fields_to_update=_SENTINEL):
    """Call ``update_ldap_member`` with the LDAP layer mocked.

    Returns ``(result, captured)`` where ``captured['attributes']`` is the
    dictionary of modifications handed to ``conn.modify``.
    """
    captured: dict = {}

    @contextmanager
    def fake_connection(**_kwargs):
        conn = MagicMock()
        conn.result = {"description": "success"}

        def _modify(dn, attributes):
            captured["dn"] = dn
            captured["attributes"] = attributes
            return True

        conn.modify.side_effect = _modify
        yield conn

    with patch.object(utils, "get_ldap_connection", fake_connection), \
         patch.object(utils, "get_secret", lambda *_: "secret"), \
         patch.object(utils, "LDAP_OU", "ou=users"), \
         patch.object(utils, "LDAP_BASE_DN", "dc=example,dc=com"):
        if fields_to_update is _SENTINEL:
            result = utils.update_ldap_member(MagicMock(), member)
        else:
            result = utils.update_ldap_member(
                MagicMock(), member, fields_to_update=fields_to_update
            )
    return result, captured


# --------------------------------------------------------------------------- #
# 2.6 - update_ldap_member
# --------------------------------------------------------------------------- #
EXPECTED_DEFAULT_ATTRIBUTES = {
    "mail", "sn", "description", "employeeType", "gn", "nationality",
    "birthdate", "preferredLanguage", "secondLanguage", "thirdLanguage",
    "isActive", "cooperativeBehaviourMark", "cooperativeBehaviourMarkUpdate",
    "numberSharesOwned", "dateEndValidityYearlyContribution", "IBAN",
    "uniqueMemberOf", "dateErasureAllData",
}


def test_default_update_covers_every_model_field_without_attribute_error():
    """Calling without ``fields_to_update`` must drive all 18 model fields.

    Regression: the default list used to contain *LDAP* attribute names, so the
    body dereferenced ``member.data.<ldapname>`` and raised AttributeError.
    """
    member = _fully_populated_member()
    result, captured = _run_update(member)  # fields_to_update=None -> default
    assert result["status"] == "success"
    assert set(captured["attributes"]) == EXPECTED_DEFAULT_ATTRIBUTES


def test_corrected_field_names_are_read_from_the_model():
    """The renamed fields must be read from their model attribute names."""
    member = _fully_populated_member()
    _, captured = _run_update(member)
    attrs = captured["attributes"]
    assert attrs["sn"] == [(MODIFY_REPLACE, ["Doe"])]            # fullsurname
    assert attrs["uniqueMemberOf"] == [
        (MODIFY_REPLACE, ["cn=cooperators,ou=groups,dc=example,dc=com"])
    ]                                                            # unique_member_of
    assert attrs["dateErasureAllData"][0][0] == MODIFY_REPLACE   # date_erasure_all_data


def test_cooperative_behaviour_mark_is_serialized_as_string():
    member = _fully_populated_member()
    _, captured = _run_update(member, ["cooperative_behaviour_mark"])
    assert captured["attributes"]["cooperativeBehaviourMark"] == [
        (MODIFY_REPLACE, ["12.5"])
    ]


@pytest.mark.parametrize(
    "lang2, lang3, expected_second, expected_third",
    [
        ("fr", "", [(MODIFY_REPLACE, ["fr"])], [(MODIFY_REPLACE, [])]),
        ("", "de", [(MODIFY_REPLACE, [])], [(MODIFY_REPLACE, ["de"])]),
        ("es", "de", [(MODIFY_REPLACE, ["es"])], [(MODIFY_REPLACE, ["de"])]),
        ("", "", [(MODIFY_REPLACE, [])], [(MODIFY_REPLACE, [])]),
    ],
)
def test_second_and_third_language_updates(
    lang2, lang3, expected_second, expected_third
):
    """Guard against the scrambled lang2/lang3 block.

    A populated language must keep its value (no data loss), an empty one must
    REPLACE with ``[]`` (never MODIFY_DELETE), and lang2 must target
    ``secondLanguage`` (not ``thirdLanguage``).
    """
    member = _make_member(lang2=lang2, lang3=lang3)
    _, captured = _run_update(member, ["lang2", "lang3"])
    attrs = captured["attributes"]
    assert attrs["secondLanguage"] == expected_second
    assert attrs["thirdLanguage"] == expected_third


def test_languages_never_use_modify_delete():
    member = _make_member(lang2="", lang3="")
    _, captured = _run_update(member, ["lang2", "lang3"])
    for operations in captured["attributes"].values():
        for operation, _value in operations:
            assert operation != MODIFY_DELETE


def test_ldap_modify_failure_is_reported_as_error():
    """A failed ``conn.modify`` must surface as ``status == 'error'``."""
    member = _make_member()

    @contextmanager
    def failing_connection(**_kwargs):
        conn = MagicMock()
        conn.result = {"description": "other"}
        conn.modify.return_value = False
        yield conn

    with patch.object(utils, "get_ldap_connection", failing_connection), \
         patch.object(utils, "get_secret", lambda *_: "secret"), \
         patch.object(utils, "LDAP_OU", "ou=users"), \
         patch.object(utils, "LDAP_BASE_DN", "dc=example,dc=com"):
        result = utils.update_ldap_member(
            MagicMock(), member, fields_to_update=["email"]
        )
    assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# 2.9 - register_user_to_ldap (invalid pseudonym contract)
# --------------------------------------------------------------------------- #
def test_register_user_invalid_pseudonym_returns_status_error_dict(members_mapping):
    """The invalid-pseudonym path must honour the ``status``/``message`` contract.

    Regression: it used to return the raw ``is_valid_unique_pseudonym`` dict
    (``{'error': ...}``) with no ``status``/``message`` keys, so callers raised
    KeyError on ``result['status']``.
    """
    candidature = Candidature()
    candidature.pseudonym = "taken"
    with patch.object(
        utils,
        "is_valid_unique_pseudonym",
        return_value={"error": "pseudonym_already_exists"},
    ):
        result = utils.register_user_to_ldap(MagicMock(), candidature, "pwd")
    assert result["status"] == "error"
    assert result["message"] == "pseudonym_already_exists"
    assert result["error"] == "pseudonym_already_exists"
