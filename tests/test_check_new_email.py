"""Unit tests for ``alirpunkto.views.check_new_email`` (audit finding 2.7).

The fix makes the view treat the result of ``update_ldap_member`` properly:
because that helper always returns a truthy dict, the old ``if result is None``
check let an LDAP *error* be considered a success and committed the email
change anyway. The view must now require ``status == 'success'`` before
committing.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.constants_and_globals import _
from alirpunkto.models.member import Member
from alirpunkto.views import check_new_email as cne
from alirpunkto.views.check_new_email import check_new_email


class _Session(dict):
    def flash(self, message, queue=""):
        self.setdefault("_flashed", []).append((queue, message))


class _Request:
    def __init__(self, *, params, session=None, tm=None, settings=None):
        self.params = params
        self.session = session if session is not None else _Session()
        self.tm = tm if tm is not None else MagicMock()
        self.registry = SimpleNamespace(
            settings=settings if settings is not None else {"session.secret": "x"}
        )
        self.method = "GET"
        self.url = "http://example.com/check_new_email"


def _member_with_pending_email():
    member = Member(oid="member-1")
    member.email = "old@example.com"
    member.new_email = "new@example.com"  # set when the change was requested
    return member


@patch.object(cne, "decrypt_oid", return_value=("member-1", "seed"))
def test_check_new_email_rejects_failed_ldap_update(_decrypt):
    member = _member_with_pending_email()
    tm = MagicMock()
    request = _Request(params={"oid": "encrypted"}, tm=tm)

    with patch.object(cne, "get_member_by_oid", return_value=member), \
         patch.object(cne, "update_ldap_member", return_value={"status": "error"}):
        result = check_new_email(request)

    assert result["error"] == _("email_update_error")
    tm.commit.assert_not_called()


@patch.object(cne, "decrypt_oid", return_value=("member-1", "seed"))
def test_check_new_email_rejects_none_ldap_result(_decrypt):
    member = _member_with_pending_email()
    tm = MagicMock()
    request = _Request(params={"oid": "encrypted"}, tm=tm)

    with patch.object(cne, "get_member_by_oid", return_value=member), \
         patch.object(cne, "update_ldap_member", return_value=None):
        result = check_new_email(request)

    assert result["error"] == _("email_update_error")
    tm.commit.assert_not_called()


@patch.object(cne, "decrypt_oid", return_value=("member-1", "seed"))
def test_check_new_email_commits_on_success(_decrypt):
    member = _member_with_pending_email()
    tm = MagicMock()
    request = _Request(params={"oid": "encrypted"}, tm=tm)

    with patch.object(cne, "get_member_by_oid", return_value=member), \
         patch.object(cne, "update_ldap_member", return_value={"status": "success"}):
        result = check_new_email(request)

    assert result["success"] == _("email_updated")
    assert member.email == "new@example.com"
    tm.commit.assert_called()
