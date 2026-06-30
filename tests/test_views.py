from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from pyramid.httpexceptions import HTTPFound

from alirpunkto.constants_and_globals import SSO_EXPIRES_AT, SSO_REFRESH
from alirpunkto.views.default import my_view
from alirpunkto.views.home import home_view, is_authenticated
from alirpunkto.views.logout import logout_view
from alirpunkto.views.notfound import notfound_view


def test_my_view(app_request):
    info = my_view(app_request)
    assert app_request.response.status_int == 200
    assert info["project"] == "alirpunkto"


def test_notfound_view(app_request):
    info = notfound_view(app_request)
    assert info == {}


def test_home_view_for_anonymous_user(dummy_request):
    result = home_view(dummy_request)

    assert result["logged_in"] is False
    assert result["applications"] == []
    assert result["user"] == {"name": "unknown"}
    assert dummy_request.session["logged_in"] is False


def test_home_view_for_logged_in_user(dummy_request):
    dummy_request.session["user"] = json.dumps({"name": "Alice"})
    dummy_request.registry.settings["applications"] = {"app": {"name": "App"}}

    result = home_view(dummy_request)

    assert result["logged_in"] is True
    assert result["applications"] == {"app": {"name": "App"}}
    assert result["user"] == {"name": "Alice"}


def test_home_view_logs_out_when_sso_refresh_is_expired(dummy_request):
    dummy_request.session["user"] = json.dumps({"name": "Alice"})
    dummy_request.session[SSO_REFRESH] = "refresh-token"
    dummy_request.session[SSO_EXPIRES_AT] = "2000-01-01T00:00:00"

    result = home_view(dummy_request)

    assert result["logged_in"] is False
    assert result["applications"] == []
    assert "user" not in dummy_request.session


def test_home_view_refreshes_valid_sso_token(dummy_request):
    dummy_request.session["user"] = json.dumps({"name": "Alice"})
    dummy_request.session[SSO_REFRESH] = "refresh-token"
    dummy_request.session[SSO_EXPIRES_AT] = (datetime.now() + timedelta(minutes=5)).isoformat()

    with patch("alirpunkto.views.home.refresh_keycloak_token") as refresh:
        refresh.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "refresh_expires_in": 3600,
        }
        result = home_view(dummy_request)

    assert result["logged_in"] is True
    assert dummy_request.session[SSO_REFRESH] == "new-refresh-token"
    assert "Authorization" in dummy_request.headers


def test_is_authenticated_uses_session_user(dummy_request):
    assert is_authenticated(dummy_request) is False
    dummy_request.session["user"] = json.dumps({"name": "Alice"})
    assert is_authenticated(dummy_request) is True


def test_logout_view_redirects_home(dummy_request):
    dummy_request.session.update({"user": "{}", "logged_in": True})

    response = logout_view(dummy_request)

    assert isinstance(response, HTTPFound)
    assert response.location == "http://example.com/home"
    assert "user" not in dummy_request.session
