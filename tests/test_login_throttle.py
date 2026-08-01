"""Login attempts are rate-limited (external audit, 2026-08-01).

Two sliding windows guard the login view before any LDAP work: per
client IP (10 over 5 minutes) and, stricter, per username (5 over 15
minutes, across addresses). A success clears both counters; the windows
expire on their own; the throttled answer is uniform and the directory
is never touched. State is in-process by design (single Waitress
process), documented as such.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto import login_throttle as lt
from alirpunkto.views import login as login_module


@pytest.fixture(autouse=True)
def clean_state():
    lt._reset_for_tests()
    yield
    lt._reset_for_tests()


# ------------------------------- the windows ------------------------------- #
def test_under_the_thresholds_nothing_blocks():
    for _ in range(lt.USERNAME_MAX_ATTEMPTS - 1):
        lt.record_failure('1.2.3.4', 'alice')
    assert not lt.is_throttled('1.2.3.4', 'alice')


def test_the_ip_window_blocks_a_spray():
    for i in range(lt.IP_MAX_ATTEMPTS):
        lt.record_failure('1.2.3.4', f'user{i}')       # names all differ
    assert lt.is_throttled('1.2.3.4', 'yet-another')
    assert not lt.is_throttled('5.6.7.8', 'yet-another')


def test_the_username_window_blocks_across_addresses():
    for i in range(lt.USERNAME_MAX_ATTEMPTS):
        lt.record_failure(f'10.0.0.{i}', 'Alice')      # IPs all differ
    assert lt.is_throttled('99.99.99.99', ' alice ')   # case/space folded
    assert not lt.is_throttled('99.99.99.99', 'bob')


def test_a_success_clears_the_username_counter_only():
    for _ in range(lt.USERNAME_MAX_ATTEMPTS):
        lt.record_failure('1.2.3.4', 'alice')
    assert lt.is_throttled('1.2.3.4', 'alice')
    lt.record_success('1.2.3.4', 'alice')
    assert not lt.is_throttled('1.2.3.4', 'alice')


def test_an_authenticated_attacker_cannot_reset_the_ip_window():
    """Revised audit: probing usernames then logging into one's own
    valid account must not wipe the address history."""
    for i in range(lt.IP_MAX_ATTEMPTS):
        lt.record_failure('6.6.6.6', f'victim{i}')
    assert lt.is_throttled('6.6.6.6', 'victim0')
    lt.record_success('6.6.6.6', 'attacker-own-account')   # own login
    assert lt.is_throttled('6.6.6.6', 'victim0')           # still blocked


def test_the_window_expires_on_its_own():
    clock = {'now': 1000.0}
    with patch.object(lt, '_now', side_effect=lambda: clock['now']):
        for _ in range(lt.USERNAME_MAX_ATTEMPTS):
            lt.record_failure('1.2.3.4', 'alice')
        assert lt.is_throttled('1.2.3.4', 'alice')
        clock['now'] += lt.USERNAME_WINDOW_SECONDS + 1
        assert not lt.is_throttled('1.2.3.4', 'alice')


# --------------------------- the login integration ------------------------- #
@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_route('home', '/')
    yield config
    tearDown()


def _post(username='alice'):
    request = DummyRequest(post={'form.submitted': '1',
                                 'username': username,
                                 'password': 'wrong'})
    request.method = 'POST'
    request.session = {}
    request.client_addr = '1.2.3.4'
    return request


def test_the_throttled_attempt_never_reaches_ldap(config):
    """The audit's directory-saturation point: once the window is full,
    the view answers before any LDAP call."""
    for _ in range(lt.USERNAME_MAX_ATTEMPTS):
        lt.record_failure('1.2.3.4', 'alice')
    oid_lookup = MagicMock()
    with patch.object(login_module, 'is_admin', return_value=False), \
         patch.object(login_module, 'get_oid_from_pseudonym', oid_lookup):
        response = login_module.login_view(_post())
    assert oid_lookup.call_count == 0
    assert 'too_many_login_attempts' in str(response['error'])


def test_failed_attempts_accumulate_through_the_view(config):
    with patch.object(login_module, 'is_admin', return_value=False), \
         patch.object(login_module, 'get_oid_from_pseudonym',
                      return_value=None):
        for _ in range(lt.USERNAME_MAX_ATTEMPTS):
            response = login_module.login_view(_post())
            assert 'invalid_username_or_password' in str(response['error'])
        response = login_module.login_view(_post())
    assert 'too_many_login_attempts' in str(response['error'])


def test_a_successful_login_resets_the_counters(config):
    for _ in range(lt.USERNAME_MAX_ATTEMPTS - 1):
        lt.record_failure('1.2.3.4', 'alice')
    user = MagicMock(); user.to_json.return_value = {}
    member = MagicMock(); member.data.lang1 = None
    request = _post()
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
        login_module.login_view(request)
    assert not lt.is_throttled('1.2.3.4', 'alice')


def test_both_failure_branches_share_the_uniform_error():
    source = open(login_module.__file__, encoding='utf-8').read()
    assert source.count("_('invalid_username_or_password')") == 2
