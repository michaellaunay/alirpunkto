"""Unit tests for ``alirpunkto.views.modify_member`` (audit finding 2.7).

Two fixed behaviours are exercised through the ``modify`` POST branch:

* the password branch now actually calls ``update_member_password`` and
  surfaces its failure (it used to compute validity and then do nothing);
* the final LDAP write now requires ``status == 'success'`` -- because
  ``update_ldap_member`` always returns a truthy dict, the old
  ``if not sending_success`` check let an LDAP error be treated as a success.

The view has heavy plumbing, so the accessor/accessed members, the permission
matrix, the LDAP helpers and the deform schema are all replaced; the assertions
focus only on the corrected branches.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID, _
from alirpunkto.models.member import Member, MemberDatas, MemberStates, MemberTypes
from alirpunkto.models.model_permissions import (
    MemberDataPermissions,
    MemberPermissions,
)
from alirpunkto.models.permissions import Permissions
from alirpunkto.views import modify_member as mm
from alirpunkto.views.modify_member import modify_member


_WRITE = Permissions.WRITE | Permissions.ACCESS


# --------------------------------------------------------------------------- #
# request / member / permission helpers
# --------------------------------------------------------------------------- #
class _Session(dict):
    def flash(self, message, queue=""):
        self.setdefault("_flashed", []).append((queue, message))


class _Request:
    def __init__(self, *, post, params=None, session, tm=None):
        self.POST = post
        self.params = params if params is not None else dict(post)
        self.session = session
        self.tm = tm if tm is not None else MagicMock()
        self.method = "POST"
        self.url = "http://example.com/modify_member"

    def route_url(self, name, **kw):
        return f"http://example.com/{name}"


def _session():
    session = _Session()
    session["logged_in"] = True
    session["user"] = {"oid": "accessor-1"}
    session[ACCESSED_MEMBER_OID] = "accessed-1"
    return session


def _accessor():
    member = Member(oid="accessor-1")
    member.type = MemberTypes.ORDINARY
    return member


def _accessed(**data):
    member = Member(oid="accessed-1")
    member.type = MemberTypes.ORDINARY
    member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
    member.email = "accessed@example.com"
    member.pseudonym = "accessed"
    member.data = MemberDatas(**data)
    return member


def _perms(**data_fields):
    return MemberPermissions(data=MemberDataPermissions(**data_fields))


@contextmanager
def _wire(accessor, accessed, perms, **extra):
    with ExitStack() as stack:
        stack.enter_context(patch.object(mm, "get_member_by_oid", return_value=accessor))
        stack.enter_context(patch.object(mm, "get_ldap_member_list", return_value=[]))
        stack.enter_context(
            patch.object(mm, "update_member_from_ldap", return_value=accessed)
        )
        stack.enter_context(patch.object(mm, "get_access_permissions", return_value=perms))
        stack.enter_context(patch.object(mm, "RegisterForm", MagicMock()))
        for name, value in extra.items():
            stack.enter_context(patch.object(mm, name, value))
        yield


# --------------------------------------------------------------------------- #
# final LDAP write result handling
# --------------------------------------------------------------------------- #
def test_modify_member_reports_ldap_update_failure():
    accessor = _accessor()
    accessed = _accessed(description="old desc")
    request = _Request(
        post={"modify": "1", "description": "New desc"}, session=_session()
    )

    with _wire(
        accessor,
        accessed,
        _perms(description=_WRITE),
        update_ldap_member=MagicMock(return_value={"status": "error"}),
    ):
        result = modify_member(request)

    assert result["error"] == _("error_while_updating_member")
    # the member must not be advanced to DATA_MODIFIED on a failed write
    assert accessed.member_state is MemberStates.DATA_MODIFICATION_REQUESTED


def test_modify_member_commits_on_ldap_success():
    accessor = _accessor()
    accessed = _accessed(description="old desc")
    request = _Request(
        post={"modify": "1", "description": "New desc"}, session=_session()
    )

    with _wire(
        accessor,
        accessed,
        _perms(description=_WRITE),
        update_ldap_member=MagicMock(return_value={"status": "success"}),
    ):
        result = modify_member(request)

    assert result["message"] == _("member_data_updated")
    assert accessed.member_state is MemberStates.DATA_MODIFIED
    assert accessed.data.description == "New desc"


# --------------------------------------------------------------------------- #
# password branch
# --------------------------------------------------------------------------- #
def test_modify_member_writes_password():
    accessor = _accessor()
    accessed = _accessed()  # password is None
    request = _Request(
        post={
            "modify": "1",
            "password": "NewPass123",
            "password_confirm": "NewPass123",
        },
        session=_session(),
    )
    update_password = MagicMock(return_value={"status": "success"})

    with _wire(
        accessor,
        accessed,
        _perms(password=_WRITE),
        is_valid_password=MagicMock(return_value=None),
        update_member_password=update_password,
    ):
        result = modify_member(request)

    update_password.assert_called_once_with(request, "accessed-1", "NewPass123")
    assert result["message"] == _("member_data_updated")


def test_modify_member_surfaces_password_update_failure():
    accessor = _accessor()
    accessed = _accessed()
    request = _Request(
        post={
            "modify": "1",
            "password": "NewPass123",
            "password_confirm": "NewPass123",
        },
        session=_session(),
    )

    with _wire(
        accessor,
        accessed,
        _perms(password=_WRITE),
        is_valid_password=MagicMock(return_value=None),
        update_member_password=MagicMock(return_value={"status": "error"}),
    ):
        result = modify_member(request)

    assert result["error"] == _("password_update_failed")


# --------------------------------------------------------------------------- #
# value coercion (the "#@TODO cast the value to the right type")
# --------------------------------------------------------------------------- #
def test_modify_member_casts_number_shares_owned_to_int():
    accessor = _accessor()
    accessed = _accessed(number_shares_owned=0)
    request = _Request(
        post={"modify": "1", "number_shares_owned": "5"}, session=_session()
    )
    update_ldap = MagicMock(return_value={"status": "success"})

    with _wire(
        accessor,
        accessed,
        _perms(number_shares_owned=_WRITE),
        update_ldap_member=update_ldap,
    ):
        result = modify_member(request)

    assert accessed.data.number_shares_owned == 5
    assert type(accessed.data.number_shares_owned) is int
    assert result["message"] == _("member_data_updated")
    update_ldap.assert_called_once()


def test_modify_member_casts_cooperative_behaviour_mark_to_float():
    accessor = _accessor()
    accessed = _accessed(cooperative_behaviour_mark=0.0)
    request = _Request(
        post={"modify": "1", "cooperative_behaviour_mark": "12.5"},
        session=_session(),
    )

    with _wire(
        accessor,
        accessed,
        _perms(cooperative_behaviour_mark=_WRITE),
        update_ldap_member=MagicMock(return_value={"status": "success"}),
    ):
        modify_member(request)

    assert accessed.data.cooperative_behaviour_mark == 12.5
    assert type(accessed.data.cooperative_behaviour_mark) is float


def test_modify_member_casts_is_active_to_bool():
    accessor = _accessor()
    accessed = _accessed(is_active=True)
    request = _Request(post={"modify": "1", "is_active": "false"}, session=_session())

    with _wire(
        accessor,
        accessed,
        _perms(is_active=_WRITE),
        update_ldap_member=MagicMock(return_value={"status": "success"}),
    ):
        modify_member(request)

    assert accessed.data.is_active is False


def test_modify_member_rejects_invalid_numeric_value():
    accessor = _accessor()
    accessed = _accessed(number_shares_owned=0)
    request = _Request(
        post={"modify": "1", "number_shares_owned": "abc"}, session=_session()
    )
    update_ldap = MagicMock(return_value={"status": "success"})

    with _wire(
        accessor,
        accessed,
        _perms(number_shares_owned=_WRITE),
        update_ldap_member=update_ldap,
    ):
        result = modify_member(request)

    assert str(result["error"]) == "invalid_field_value"
    assert accessed.data.number_shares_owned == 0  # unchanged
    update_ldap.assert_not_called()
