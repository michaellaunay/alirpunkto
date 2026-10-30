"""An environment behind the lock fails at boot, not at the first click
(production incident of 2026-10-30).

The server's virtualenv carried an old python-keycloak whose
``auth_url`` had no ``code_challenge`` parameter; the application booted
and every click on Login answered 500. ``assert_pkce_capable_client``
now runs first in ``main()``.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from keycloak import KeycloakOpenID

import alirpunkto
from alirpunkto import keycloak_client_check as check


def test_the_locked_library_passes_the_check():
    assert check.missing_parameters() == []
    assert check.assert_pkce_capable_client() is None


def _old_auth_url(self, redirect_uri, scope='email', state='', nonce=''):
    """``auth_url`` as python-keycloak 4.x declared it: no PKCE."""
    return 'https://kc.test/auth'


def test_an_old_library_stops_the_boot_with_an_explicit_message(caplog):
    with patch.object(KeycloakOpenID, 'auth_url', _old_auth_url), \
         patch.object(check, 'installed_version', return_value='4.0.0'), \
         caplog.at_level(logging.CRITICAL, logger='alirpunkto'):
        assert check.missing_parameters() == [
            'auth_url(code_challenge)', 'auth_url(code_challenge_method)']
        with pytest.raises(RuntimeError) as refusal:
            check.assert_pkce_capable_client()

    message = str(refusal.value)
    assert 'python-keycloak 4.0.0' in message
    assert 'auth_url(code_challenge)' in message
    assert 'python-keycloak>=7.1.1,<8' in message or \
        'python-keycloak<8,>=7.1.1' in message
    assert 'requirements.lock' in message
    assert any(r.levelno == logging.CRITICAL and r.getMessage() == message
               for r in caplog.records)


def test_the_requirement_is_read_from_the_distribution():
    """The message quotes what pyproject.toml asks for, not a copy that
    could drift."""
    requirement = check.required_version()
    assert requirement.startswith('python-keycloak')
    assert '7.1.1' in requirement


@pytest.mark.functional
def test_main_refuses_to_build_the_application(app_settings):
    with patch.object(alirpunkto, 'assert_pkce_capable_client',
                      side_effect=RuntimeError('old client')), \
         patch.object(alirpunkto, 'create_ldap_groups_if_not_exists',
                      return_value=None) as ldap:
        with pytest.raises(RuntimeError, match='old client'):
            alirpunkto.main({}, **app_settings)
    assert not ldap.called          # refused before touching the directory
