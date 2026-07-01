"""Unit tests for ``alirpunkto.views.manage_provider`` (audit finding 2.4).

The view was broken in several ways: the duplicate check compared an email
string against a list of ``User`` objects (always false), and the update branch
used a non-existent form API, an undefined ``MemberStates.ACTIVE``, and passed a
dict where ``update_ldap_member`` expects a list of field names. These tests
cover the corrected add and update branches plus the access guards.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID, _
from alirpunkto.models.member import Member, MemberDatas, MemberStates, MemberTypes
from alirpunkto.models.users import User
from alirpunkto.views import manage_provider as mp
from alirpunkto.views.manage_provider import manage_provider_view


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
class _Request:
    def __init__(self, *, post=None, params=None, session=None, method="POST", tm=None):
        self.POST = post if post is not None else {}
        self.params = params if params is not None else dict(self.POST)
        self.session = session if session is not None else {"user": "{}"}
        self.method = method
        self.tm = tm if tm is not None else MagicMock()
        self.url = "http://example.com/manage_provider"


def _admin():
    member = Member(oid="admin-1")
    member.type = MemberTypes.ADMINISTRATOR
    return member


def _provider(oid="p1", email="old@example.com"):
    member = Member(oid=oid)
    member.type = MemberTypes.PROVIDER
    member.email = email
    member.data = MemberDatas()
    return member


def _dispatch(**members):
    """A get_member_by_oid replacement resolving oids to prepared members."""
    return MagicMock(side_effect=lambda oid, request, *a: members.get(oid))


@contextmanager
def _wire(accessor, *, get_member=None, providers=None, **extra):
    with ExitStack() as stack:
        user_cls = stack.enter_context(patch.object(mp, "User"))
        user_cls.from_json.return_value = SimpleNamespace(
            oid=(accessor.oid if accessor else "admin-1")
        )
        stack.enter_context(
            patch.object(
                mp,
                "get_member_by_oid",
                get_member if get_member is not None else MagicMock(return_value=accessor),
            )
        )
        stack.enter_context(
            patch.object(mp, "get_ldap_member_list", MagicMock(return_value=providers or []))
        )
        stack.enter_context(
            patch.object(mp, "send_member_state_change_email", MagicMock(return_value=None))
        )
        for name, value in extra.items():
            stack.enter_context(patch.object(mp, name, value))
        yield


# --------------------------------------------------------------------------- #
# access guards
# --------------------------------------------------------------------------- #
def test_manage_provider_requires_login():
    request = _Request(method="GET", session={})  # no 'user'
    result = manage_provider_view(request)
    assert result["error"] == _("user_not_logged_in")


def test_manage_provider_requires_admin():
    ordinary = Member(oid="u-1")
    ordinary.type = MemberTypes.ORDINARY
    request = _Request(method="GET")

    with _wire(ordinary):
        result = manage_provider_view(request)

    assert result["error"] == _("must_be_administrator")


# --------------------------------------------------------------------------- #
# add branch
# --------------------------------------------------------------------------- #
def test_add_provider_rejects_existing_email():
    existing = User(
        name="P", email="p@example.com", oid="p1", isActive=True,
        type=MemberTypes.PROVIDER,
    )
    request = _Request(
        post={
            "add_provider": "1",
            "provider_email": "p@example.com",
            "provider_pseudonym": "prov",
            "provider_password": "Secret123",
        }
    )

    with _wire(
        _admin(),
        providers=[existing],
        is_valid_email=MagicMock(return_value=None),
        is_valid_password=MagicMock(return_value=None),
    ):
        result = manage_provider_view(request)

    assert result["error"] == _("provider_email_already_exists")


def test_add_provider_creates_new(members_mapping):
    register = MagicMock(return_value={"status": "success"})
    request = _Request(
        post={
            "add_provider": "1",
            "provider_email": "new@example.com",
            "provider_pseudonym": "prov",
            "provider_password": "Secret123",
        }
    )

    with _wire(
        _admin(),
        providers=[],
        is_valid_email=MagicMock(return_value=None),
        is_valid_password=MagicMock(return_value=None),
        register_user_to_ldap=register,
    ):
        result = manage_provider_view(request)

    register.assert_called_once()
    assert result["success"] == _("provider_created")


# --------------------------------------------------------------------------- #
# update branch
# --------------------------------------------------------------------------- #
def test_update_provider_updates_email():
    admin = _admin()
    provider = _provider(email="old@example.com")
    update_ldap = MagicMock(return_value={"status": "success"})
    request = _Request(
        post={
            "update": "1",
            ACCESSED_MEMBER_OID: "p1",
            "provider_email": "new@example.com",
        }
    )

    with _wire(
        admin,
        get_member=_dispatch(**{"admin-1": admin, "p1": provider}),
        is_valid_email=MagicMock(return_value=None),
        update_ldap_member=update_ldap,
    ):
        result = manage_provider_view(request)

    assert provider.email == "new@example.com"
    update_ldap.assert_called_once()
    _call_args, kwargs = update_ldap.call_args
    assert kwargs.get("fields_to_update") == ["email"]
    assert provider.member_state is MemberStates.DATA_MODIFIED
    assert result["success"] == _("provider_updated")


def test_update_provider_surfaces_ldap_failure():
    admin = _admin()
    provider = _provider(email="old@example.com")
    request = _Request(
        post={
            "update": "1",
            ACCESSED_MEMBER_OID: "p1",
            "provider_email": "new@example.com",
        }
    )

    with _wire(
        admin,
        get_member=_dispatch(**{"admin-1": admin, "p1": provider}),
        is_valid_email=MagicMock(return_value=None),
        update_ldap_member=MagicMock(return_value={"status": "error"}),
    ):
        result = manage_provider_view(request)

    assert result["error"] == _("provider_update_failed")
    assert provider.member_state is not MemberStates.DATA_MODIFIED


def test_update_provider_updates_password():
    admin = _admin()
    provider = _provider()
    update_password = MagicMock(return_value={"status": "success"})
    request = _Request(
        post={
            "update": "1",
            ACCESSED_MEMBER_OID: "p1",
            "provider_password": "NewPass123",
        }
    )

    with _wire(
        admin,
        get_member=_dispatch(**{"admin-1": admin, "p1": provider}),
        is_valid_password=MagicMock(return_value=None),
        update_member_password=update_password,
    ):
        result = manage_provider_view(request)

    update_password.assert_called_once_with(request, "p1", "NewPass123")
    assert result["success"] == _("provider_updated")


def test_update_provider_missing_oid():
    admin = _admin()
    request = _Request(post={"update": "1"})  # no accessed_member_oid

    with _wire(admin):
        result = manage_provider_view(request)

    assert result["error"] == _("accessed_member_oid_missing")
