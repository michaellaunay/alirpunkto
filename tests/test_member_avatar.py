"""Member avatar as jpegPhoto in LDAP (issue #150).

The upload is JPEG-only three ways — extension (with the ticket's exact
error message), magic bytes, size ceiling — only the owner can change or
remove theirs, any logged-in member can view any avatar, and the bytes
never touch ZODB.
"""
from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import _, LDAP_BASE_DN, LDAP_OU
from alirpunkto.views import avatar as avatar_module
from alirpunkto.views.avatar import avatar_upload, member_avatar

JPEG = b'\xff\xd8\xff\xe0' + b'fake-jpeg-payload' * 10
PNG = b'\x89PNG\r\n\x1a\n' + b'not-a-jpeg' * 10


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


class _Upload:
    def __init__(self, filename, payload):
        self.filename = filename
        self.file = io.BytesIO(payload)


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'modify_member', 'member_avatar', 'avatar_upload'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, params=None, logged_in=True,
             oid='member-1'):
    request = DummyRequest(post=post or {}, params=params or {})
    request.session = _Session()
    request.session['logged_in'] = logged_in
    if logged_in:
        request.session['user'] = {'oid': oid, 'name': 'jdoe'}
    return request


def _mock_member(oid='member-1', jpeg=None):
    from ldap3 import Connection, Server, MOCK_SYNC, ALL
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    dn = (f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={oid},{LDAP_BASE_DN}")
    attrs = {'objectClass': ['top', 'inetOrgPerson'],
             'uid': oid, 'cn': 'jdoe', 'sn': 'jdoe'}
    if jpeg:
        attrs['jpegPhoto'] = jpeg
    conn.add(dn, attributes=attrs)
    return conn, dn


# ------------------------------- viewing ----------------------------------- #
def test_any_logged_in_member_sees_an_avatar(config):
    conn, _dn = _mock_member('other-9', jpeg=JPEG)
    request = _request(config, params={'oid': 'other-9'})
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        response = member_avatar(request)
    assert response.content_type == 'image/jpeg'
    assert response.body == JPEG


def test_a_missing_avatar_is_a_404(config):
    conn, _dn = _mock_member('bare-1')
    request = _request(config, params={'oid': 'bare-1'})
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         pytest.raises(HTTPNotFound):
        member_avatar(request)


def test_anonymous_visitors_are_sent_home(config):
    request = _request(config, logged_in=False)
    result = member_avatar(request)
    assert isinstance(result, HTTPFound)


# ------------------------------- uploading --------------------------------- #
def _flash_errors(request):
    return [m for q, m in request.session.get('_flash', ()) if q == 'error']


def test_a_valid_jpeg_is_stored(config):
    conn, dn = _mock_member()
    post = {'avatar': _Upload('me.JPG', JPEG), 'upload': '1'}
    request = _request(config, post=post)
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = avatar_upload(request)

    assert isinstance(result, HTTPFound)
    assert not _flash_errors(request)
    conn.search(dn, '(objectclass=*)', attributes=['jpegPhoto'])
    stored = conn.entries[0].jpegPhoto.value
    assert (stored[0] if isinstance(stored, list) else stored) == JPEG


def test_the_ticket_error_for_a_wrong_extension(config):
    """Issue #150 verbatim: JPEG only, .JPG or .JPEG."""
    conn, _dn = _mock_member()
    post = {'avatar': _Upload('me.png', JPEG), 'upload': '1'}
    request = _request(config, post=post)
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(avatar_module, 'set_member_avatar') as setter:
        avatar_upload(request)
    assert _flash_errors(request) == [_('avatar_format_error')]
    setter.assert_not_called()


def test_a_jpeg_extension_with_non_jpeg_content_is_refused(config):
    conn, _dn = _mock_member()
    post = {'avatar': _Upload('sneaky.jpg', PNG), 'upload': '1'}
    request = _request(config, post=post)
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(avatar_module, 'set_member_avatar') as setter:
        avatar_upload(request)
    assert _flash_errors(request) == [_('avatar_format_error')]
    setter.assert_not_called()


def test_an_oversized_avatar_is_refused(config):
    conn, _dn = _mock_member()
    big = b'\xff\xd8\xff' + b'0' * (4096 * 1024)
    post = {'avatar': _Upload('big.jpg', big), 'upload': '1'}
    request = _request(config, post=post)
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(avatar_module, 'set_member_avatar') as setter:
        avatar_upload(request)
    assert _flash_errors(request) == [_('avatar_too_large_error')]
    setter.assert_not_called()


def test_the_upload_targets_only_the_session_owner(config):
    """The oid comes from the session, never from the request."""
    conn, _dn = _mock_member('victim-7')
    post = {'avatar': _Upload('me.jpg', JPEG), 'upload': '1',
            'oid': 'victim-7'}
    request = _request(config, post=post, oid='member-1')
    with patch.object(avatar_module, 'set_member_avatar',
                      return_value={'status': 'success'}) as setter:
        avatar_upload(request)
    setter.assert_called_once()
    assert setter.call_args[0][1] == 'member-1'


def test_removing_ones_avatar(config):
    conn, dn = _mock_member(jpeg=JPEG)
    post = {'remove': '1'}
    request = _request(config, post=post)
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = avatar_upload(request)
    assert isinstance(result, HTTPFound)
    conn.search(dn, '(objectclass=*)', attributes=['jpegPhoto'])
    entry = conn.entries[0]
    assert 'jpegPhoto' not in entry or not entry.jpegPhoto.value
