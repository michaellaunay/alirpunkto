"""Keycloak calls carry timeouts and survive outages (revised audit).

A hung or unreachable Keycloak used to pin a Waitress thread for an
unbounded time — including after a successful LDAP authentication. Both
token calls now send a (connect, read) timeout, translate any
requests.RequestException into None with a password-free warning, and
never log the raw response body.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import requests

from alirpunkto import utils

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _user():
    user = MagicMock()
    user.name = 'alice'
    user.oid = 'oid-1'
    return user


def _reach_the_wire():
    """Neutralise the pytest guard and the config guard of
    get_keycloak_token so the HTTP layer is actually reached."""
    return (patch.object(utils, 'PYTEST_CURRENT_TEST', None),
            patch.object(utils, 'KEYCLOAK_SERVER_URL', 'https://kc.test'),
            patch.object(utils, 'KEYCLOAK_REALM', 'realm'),
            patch.object(utils, 'get_secret', return_value='s'))


def test_the_token_call_sends_a_timeout():
    ok = MagicMock(status_code=200)
    ok.json.return_value = {'access_token': 'x', 'expires_in': 60,
                            'refresh_token': 'y'}
    g1, g2, g3, g4 = _reach_the_wire()
    with g1, g2, g3, g4,          patch.object(utils.requests, 'post', return_value=ok) as post:
        utils.get_keycloak_token(_user(), 'pw')
    assert post.call_args.kwargs.get('timeout') == (3.0, 10.0)


def test_an_unreachable_keycloak_returns_none_instead_of_hanging():
    g1, g2, g3, g4 = _reach_the_wire()
    with g1, g2, g3, g4,          patch.object(utils.requests, 'post',
                      side_effect=requests.ConnectionError('down')) as post:
        assert utils.get_keycloak_token(_user(), 'pw') is None
        assert utils.refresh_keycloak_token('refresh-x') is None
    assert post.call_count == 2          # both really reached the wire


def test_the_refresh_call_sends_a_timeout_too():
    ok = MagicMock(status_code=200)
    ok.json.return_value = {'access_token': 'x'}
    with patch.object(utils.requests, 'post', return_value=ok) as post:
        utils.refresh_keycloak_token('refresh-x')
    assert post.call_args.kwargs.get('timeout') == (3.0, 10.0)


def test_error_bodies_are_never_logged_raw():
    source = open(os.path.join(ROOT, 'alirpunkto', 'utils.py'),
                  encoding='utf-8').read()
    assert '- {response.text}' not in source
