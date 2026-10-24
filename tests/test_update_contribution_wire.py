"""``tools/update_cooperator.py`` against the REAL Pyramid pipeline.

External audit of 2026-10-24, §3: the script's unit tests drove a
``MagicMock`` session, so they passed while the real portal answered
400 to every login — the global CSRF guard wants the login page's
token and, over HTTPS, an ``Origin``/``Referer`` naming the portal.
These tests run the script's own ``login`` and ``modify_member`` through
WebTest, HTTPS scheme, secure session cookie and all: only the LDAP and
Keycloak edges are stubbed.
"""
from __future__ import annotations

import importlib.util
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

import pytest

from alirpunkto.constants_and_globals import HTTP_TEST_HOST
from alirpunkto.models.member import MemberDatas, MemberStates, MemberTypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN = f"https://{HTTP_TEST_HOST}"


def _load_script():
    path = os.path.join(ROOT, 'tools', 'update_cooperator.py')
    spec = importlib.util.spec_from_file_location('update_cooperator_wire', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DOMAINE = ORIGIN
    module.LOGIN_URL = f"{ORIGIN}/{module.LOGIN_PATH}"
    module.MODIFY_URL = f"{ORIGIN}/{module.MODIFY_PATH}"
    module.CONTRIBUTION_URL = f"{ORIGIN}/{module.CONTRIBUTION_PATH}"
    return module


class _Response:
    def __init__(self, response):
        self.status_code = response.status_code
        self.text = response.text

    def json(self):
        return self._response_json

    @classmethod
    def wrap(cls, response):
        wrapped = cls(response)
        try:
            wrapped._response_json = response.json
        except Exception:
            wrapped._response_json = None
            wrapped.json = _raise_value_error
        return wrapped


def _raise_value_error():
    raise ValueError("not json")


class _WireSession:
    """A ``requests.Session`` look-alike over ``webtest.TestApp``: same
    cookie jar across calls, HTTPS scheme (the session cookie is Secure,
    the CSRF origin check only runs over https), redirects left to the
    caller as ``requests`` would report them before following."""

    def __init__(self, testapp):
        self.app = testapp
        self.env = {'wsgi.url_scheme': 'https', 'HTTP_HOST': HTTP_TEST_HOST}

    def _path(self, url):
        parts = urlsplit(url)
        return parts.path + (f"?{parts.query}" if parts.query else "")

    def get(self, url, timeout=None, headers=None):
        response = self.app.get(self._path(url), headers=headers or {},
                                extra_environ=self.env, expect_errors=True)
        return _Response.wrap(response)

    def post(self, url, data=None, headers=None, timeout=None):
        response = self.app.post(self._path(url), data or {},
                                 headers=headers or {},
                                 extra_environ=self.env, expect_errors=True)
        return _Response.wrap(response)


def _admin_member():
    return SimpleNamespace(oid='admin-oid', type=MemberTypes.ADMINISTRATOR,
                           member_state=MemberStates.REGISTRED,
                           pseudonym='admin', email='admin@example.com',
                           data=MemberDatas(password='x', lang1='en'))


def _cooperator():
    return SimpleNamespace(oid='coop-1', type=MemberTypes.COOPERATOR,
                           member_state=MemberStates.REGISTRED,
                           data=MemberDatas(password='x', number_shares_owned=3))


@pytest.fixture
def portal(testapp):
    """The edges stubbed: the LDAP administrator credentials, the member
    sync at login, Keycloak, the directory behind the pages."""
    from alirpunkto import utils
    from alirpunkto.views import login as login_view
    from alirpunkto.views import modify_member as modify_view
    from alirpunkto.views import update_contribution as uc
    admin = _admin_member()
    with patch.object(utils, 'ADMIN_LOGIN', 'admin'), \
         patch.object(utils, 'get_secret', lambda *_: 'admin-pw'), \
         patch.object(login_view, 'update_member_from_ldap',
                      return_value=admin), \
         patch.object(login_view, 'get_keycloak_token', return_value=None), \
         patch.object(modify_view, 'get_member_by_oid', return_value=admin), \
         patch.object(modify_view, 'get_ldap_member_list', return_value=[]), \
         patch.object(uc, 'get_member_by_oid', return_value=admin), \
         patch.object(uc, 'update_member_from_ldap',
                      return_value=_cooperator()), \
         patch.object(uc, 'update_ldap_member', MagicMock(return_value={
             'status': 'success', 'groups_sync': 'success',
             'keycloak_sync': 'success'})) as ldap, \
         patch('alirpunkto.dynamic_groups.read_member_groups',
               return_value={'cooperatorsGroup', 'communityMembersGroup'}):
        yield SimpleNamespace(session=_WireSession(testapp), ldap=ldap)


@pytest.mark.functional
def test_a_bare_login_post_is_refused_by_the_csrf_guard(portal):
    """What the 0.2/0.3 clients did — and why they never got in."""
    answer = portal.session.post(f"{ORIGIN}/login", data={
        'username': 'admin', 'password': 'admin-pw', 'form.submitted': 'True'})
    assert answer.status_code == 400
    assert 'CSRF' in answer.text


@pytest.mark.functional
def test_the_script_logs_in_through_the_real_csrf_guard(portal):
    script = _load_script()
    token = script.login(portal.session, 'admin', 'admin-pw')
    assert token and len(token) >= 16


@pytest.mark.functional
def test_the_script_login_without_the_origin_header_is_refused(portal):
    """Over HTTPS the token alone is not enough: Pyramid's origin check
    wants the request to come from the portal itself."""
    script = _load_script()
    with patch.object(script, 'csrf_headers', return_value={}):
        with pytest.raises(RuntimeError, match='CSRF token or Origin'):
            script.login(portal.session, 'admin', 'admin-pw')


@pytest.mark.functional
def test_wrong_credentials_are_reported_as_such(portal):
    from alirpunkto.views import login as login_view
    script = _load_script()
    with patch.object(login_view, 'get_oid_from_pseudonym', return_value=None):
        with pytest.raises(ValueError, match='invalid credentials'):
            script.login(portal.session, 'admin', 'wrong')


@pytest.mark.functional
def test_the_payment_goes_through_end_to_end_with_zero_shares(portal):
    """Login, token, endpoint, CSRF, JSON, checks — the whole wire, with
    the two audit regressions in the payload: ``0`` shares and the
    confirmation of the recorded values."""
    script = _load_script()
    token = script.login(portal.session, 'admin', 'admin-pw')
    answer = script.modify_member(portal.session, 'coop-1', '0',
                                  '2027-06-30', token)
    assert answer['status'] == 'success'
    assert answer['oid'] == 'coop-1'
    assert answer['number_shares_owned'] == 0
    assert answer['date_end_validity_yearly_contribution'] == '2027-06-30'
    assert answer['groups'] == ['communityMembersGroup', 'cooperatorsGroup']
    assert set(portal.ldap.call_args.kwargs['fields_to_update']) == {
        'number_shares_owned', 'date_end_validity_yearly_contribution'}


@pytest.mark.functional
def test_the_endpoint_refuses_a_stale_or_missing_token_on_the_wire(portal):
    script = _load_script()
    script.login(portal.session, 'admin', 'admin-pw')
    with pytest.raises(RuntimeError, match='did not answer JSON'):
        script.modify_member(portal.session, 'coop-1', '1', None, 'stale')
