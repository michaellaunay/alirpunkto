"""Unit tests for the section-3 commit removals in forgot_password.

The view committed the pyramid_tm transaction in seven places (persisting the
member load, the reset BTree, state changes, and flushing queued emails). Emails
go through the transaction-aware pyramid_mailer, so the commits were redundant:
pyramid_tm commits everything at the end of the request. The tests assert the
view no longer commits explicitly while keeping its effects and the
anti-enumeration response (audit finding 1.8).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from webob.multidict import MultiDict

from alirpunkto.constants_and_globals import MEMBER_OID, _
from alirpunkto.models.member import MemberStates
from alirpunkto.views import forgot_password as fp


def _request(pairs, session=None):
    params = MultiDict()
    for key, value in pairs:
        params.add(key, value)
    return SimpleNamespace(
        POST=params,
        params=params,
        method="POST",
        url="http://example/forgot_password",
        tm=MagicMock(),
        session=session if session is not None else {},
        registry=SimpleNamespace(settings={"site_name": "S"}),
    )


def test_submit_requests_reset_without_explicit_commit(members_mapping):
    member = MagicMock()
    member.oid = "oid-1"
    root = {}
    conn = SimpleNamespace(root=lambda: root)
    request = _request([("submit", "1"), ("email", "user@example.org")])

    with patch.object(fp, "_retrieve_member", return_value=(None, None)), \
         patch.object(fp, "is_not_a_valid_email_address", return_value=None), \
         patch.object(fp, "get_member_by_email", return_value=[{"uid": "u1"}]), \
         patch.object(fp, "update_member_from_ldap", return_value=member), \
         patch.object(fp, "get_connection", return_value=conn), \
         patch.object(fp, "send_email_to_member", return_value=None):
        result = fp.forgot_password(request)

    assert member.member_state == MemberStates.DATA_MODIFICATION_REQUESTED
    assert result["message"] == _("forget_email_sent")
    request.tm.commit.assert_not_called()


def test_modify_changes_password_without_explicit_commit(members_mapping):
    member = MagicMock()
    member.oid = "oid-1"
    request = _request(
        [("modify", "1"), ("password", "ValidPass123@"),
         ("password_confirm", "ValidPass123@")],
        session={MEMBER_OID: "oid-1"},
    )

    with patch.object(fp, "_retrieve_member", return_value=(None, None)), \
         patch.object(fp, "get_member_by_oid", return_value=member), \
         patch.object(fp, "update_member_password", return_value={"status": "success"}), \
         patch.object(fp, "send_member_state_change_email", return_value={"success": True}):
        result = fp.forgot_password(request)

    assert member.member_state == MemberStates.DATA_MODIFIED
    assert result["message"] == _("password_changed")
    request.tm.commit.assert_not_called()


def test_unknown_email_returns_neutral_message_without_commit(members_mapping):
    # Anti-enumeration (finding 1.8): an unknown address yields the same
    # forget_email_sent message, and no transaction is committed.
    request = _request([("submit", "1"), ("email", "nobody@example.org")])

    with patch.object(fp, "_retrieve_member", return_value=(None, None)), \
         patch.object(fp, "is_not_a_valid_email_address", return_value=None), \
         patch.object(fp, "get_member_by_email", return_value=[]):
        result = fp.forgot_password(request)

    assert result["message"] == _("forget_email_sent")
    assert result["member"] is None
    request.tm.commit.assert_not_called()
