"""Unit tests for ``alirpunkto.utils.logout`` (audit finding 2.8).

The logout helper read ``username`` from the request parameters and then did
``del request.session['username']`` — but that key is never set, so
``/logout?username=X`` raised ``KeyError`` (HTTP 500). The clearing must be
safe and must not depend on a URL parameter.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from alirpunkto.constants_and_globals import (
    ACCESSED_MEMBER_OID,
    CANDIDATURE_OID,
    MEMBER_OID,
    SSO_EXPIRES_AT,
    SSO_REFRESH,
    SSO_TOKEN,
)
from alirpunkto.utils import logout


def _request(session=None, params=None):
    return SimpleNamespace(
        session=session if session is not None else {},
        params=params if params is not None else {},
    )


def test_logout_with_username_param_does_not_raise():
    # Regression: `?username=X` used to trigger del session['username'] (KeyError)
    request = _request(session={"user": "u1", "logged_in": True}, params={"username": "u1"})

    logout(request)  # must not raise

    assert request.session["logged_in"] is False
    assert "user" not in request.session


def test_logout_clears_user_and_marks_logged_out():
    request = _request(
        session={"user": "u1", "logged_in": True, "created_at": "now"}, params={}
    )

    logout(request)

    assert request.session["logged_in"] is False
    assert "user" not in request.session
    assert request.session["created_at"] is None


def test_logout_clears_sso_and_oid_keys():
    session = {
        "user": "u1",
        "logged_in": True,
        CANDIDATURE_OID: "c",
        MEMBER_OID: "m",
        ACCESSED_MEMBER_OID: "a",
        SSO_TOKEN: "t",
        SSO_REFRESH: "r",
        SSO_EXPIRES_AT: "e",
    }
    request = _request(session=session, params={})

    logout(request)

    for key in (
        CANDIDATURE_OID, MEMBER_OID, ACCESSED_MEMBER_OID,
        SSO_TOKEN, SSO_REFRESH, SSO_EXPIRES_AT,
    ):
        assert key not in request.session


def test_logout_without_user_marks_logged_out():
    request = _request(session={"logged_in": True}, params={})

    logout(request)

    assert request.session["logged_in"] is False
