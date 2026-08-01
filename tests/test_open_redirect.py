"""The post-login redirect only ever targets this site (external audit).

login_view honours session['redirect_url'] after authentication; the
value used to be followed blindly — an attacker able to plant that key
sent freshly authenticated members anywhere. The legitimate writers
(vote, get_email) store request.current_route_url(), an absolute URL of
this very site, so safe_local_redirect accepts an absolute http(s) URL
only when its authority is exactly the request's host (user-info tricks
fail that equality) or a local absolute path; everything else falls back
to home, and the session key is purged either way.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.httpexceptions import HTTPFound
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.utils import safe_local_redirect
from alirpunkto.views import login as login_module

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST_REQ = SimpleNamespace(host="site.test")


# ------------------------------ the validator ------------------------------ #
@pytest.mark.parametrize("url", [
    "https://evil.com/x",
    "http://evil.com/",
    "//evil.com/x",                       # protocol-relative
    "https://site.test@evil.com/x",       # user-info trick
    "https://site.test.evil.com/x",       # prefix trick
    "javascript:alert(1)",
    "ftp://site.test/x",
    "\\\\evil.com\\x",
    "/\\evil.com",
    "relative/path",                      # not rooted
    "", None, 42,
])
def test_unsafe_targets_are_refused(url):
    assert safe_local_redirect(url, HOST_REQ) is None


@pytest.mark.parametrize("url", [
    "/",
    "/profil?a=1&b=2",
    "/vote#anchor",
    "https://site.test/vote?id=2",        # the vote/get_email case
    "http://site.test/get_email",
    "  /padded/path  ",
])
def test_same_site_targets_are_followed(url):
    assert safe_local_redirect(url, HOST_REQ) == url.strip()


# --------------------------- the login integration ------------------------- #
@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_route('home', '/')
    yield config
    tearDown()


def _login_post(session):
    request = DummyRequest(post={'form.submitted': '1',
                                 'username': 'alice',
                                 'password': 'pw'})
    request.method = 'POST'
    request.session = session
    request.host = 'site.test'
    return request


def _successful_login(request):
    user = MagicMock()
    user.to_json.return_value = {'name': 'alice'}
    member = MagicMock()
    member.data.lang1 = None
    with patch.object(login_module, 'is_admin', return_value=False), \
         patch.object(login_module, 'get_oid_from_pseudonym',
                      return_value='oid-1'), \
         patch.object(login_module, 'check_password', return_value=user), \
         patch.object(login_module, 'update_member_from_ldap',
                      return_value=member), \
         patch.object(login_module, 'get_keycloak_token',
                      return_value=None), \
         patch.object(login_module, 'switch_request_language'), \
         patch.object(login_module, 'remember', return_value=[]):
        return login_module.login_view(request)


def test_a_planted_external_url_falls_back_to_home(config):
    request = _login_post({'redirect_url': 'https://evil.com/phish'})
    response = _successful_login(request)
    assert isinstance(response, HTTPFound)
    assert response.location == request.route_url('home')
    assert 'redirect_url' not in request.session      # purged either way


def test_the_legitimate_stored_url_is_followed(config):
    request = _login_post({'redirect_url': 'https://site.test/vote?id=2'})
    response = _successful_login(request)
    assert response.location == 'https://site.test/vote?id=2'
    assert 'redirect_url' not in request.session


def test_no_stored_url_goes_home_as_before(config):
    request = _login_post({})
    response = _successful_login(request)
    assert response.location == request.route_url('home')


# ------------------------------- housekeeping ------------------------------ #
def test_the_parasitic_httpcore_import_is_gone():
    source = open(os.path.join(ROOT, 'alirpunkto', 'views', 'login.py'),
                  encoding='utf-8').read()
    assert 'from httpcore import request' not in source
