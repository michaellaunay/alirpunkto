"""Unit tests for the SSO refresh path of ``home_view`` (audit finding 2.13).

The refresh block dereferenced ``refresh_keycloak_token``'s result without
guarding ``None`` (TypeError on failure), wrote ``f'Bearer {sso_token}'`` (the
whole dict) into the *incoming* request headers instead of storing the access
token, and defaulted a missing expiry to a past date. The fix stores the access
token string in the session, logs out cleanly when the refresh fails or the
window is gone, and no longer writes to the request headers.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from alirpunkto.constants_and_globals import SSO_EXPIRES_AT, SSO_REFRESH, SSO_TOKEN
from alirpunkto.views import home
from alirpunkto.views.home import home_view


def _request(session, settings=None):
    return SimpleNamespace(
        session=session,
        params={},
        headers={},
        registry=SimpleNamespace(
            settings=settings if settings is not None else {"applications": []}
        ),
    )


def _authenticated_session(**extra):
    session = {"user": '{"name": "u"}', "logged_in": True}
    session.update(extra)
    return session


def _future():
    return (datetime.now() + timedelta(hours=1)).isoformat()


def _past():
    return (datetime.now() - timedelta(hours=1)).isoformat()


def test_home_refresh_failure_logs_out_without_crashing():
    # Regression: a None refresh result used to raise TypeError on ['access_token'].
    session = _authenticated_session(**{SSO_REFRESH: "RT", SSO_EXPIRES_AT: _future()})
    request = _request(session)

    with patch.object(home, "refresh_keycloak_token", return_value=None), \
         patch.object(home, "logout") as mock_logout:
        result = home_view(request)  # must not raise

    mock_logout.assert_called_once_with(request)
    assert result["logged_in"] is False


def test_home_refresh_success_stores_access_token_in_session():
    session = _authenticated_session(**{SSO_REFRESH: "RT", SSO_EXPIRES_AT: _future()})
    request = _request(session)
    token = {
        "access_token": "AT",
        "refresh_token": "RT2",
        "refresh_expires_in": 300,
    }

    with patch.object(home, "refresh_keycloak_token", return_value=token):
        result = home_view(request)

    assert session[SSO_TOKEN] == "AT"          # the string, not the dict
    assert session[SSO_REFRESH] == "RT2"
    assert "Authorization" not in request.headers  # no bogus header write
    assert result["logged_in"] is True


def test_home_expired_refresh_window_logs_out_without_refreshing():
    session = _authenticated_session(**{SSO_REFRESH: "RT", SSO_EXPIRES_AT: _past()})
    request = _request(session)

    with patch.object(home, "refresh_keycloak_token") as mock_refresh, \
         patch.object(home, "logout") as mock_logout:
        result = home_view(request)

    mock_refresh.assert_not_called()
    mock_logout.assert_called_once_with(request)
    assert result["logged_in"] is False


def test_home_missing_expiry_logs_out_instead_of_using_a_past_default():
    session = _authenticated_session(**{SSO_REFRESH: "RT"})  # no SSO_EXPIRES_AT
    request = _request(session)

    with patch.object(home, "refresh_keycloak_token") as mock_refresh, \
         patch.object(home, "logout") as mock_logout:
        result = home_view(request)

    mock_refresh.assert_not_called()
    mock_logout.assert_called_once_with(request)
    assert result["logged_in"] is False
