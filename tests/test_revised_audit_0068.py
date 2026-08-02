"""The remaining immediate items of the revised audit (2026-08-01).

Credentials are only ever read from the POST body; the .env file is
loaded once and never re-read through get_key(); the generated LDIF is
born 0600 with passwords able to travel through scrubbed environment
variables instead of argv; and every group-membership LDAP modify is
checked and logged on failure while staying best-effort.
"""
from __future__ import annotations

import os
import stat
from unittest.mock import MagicMock, patch

import pytest
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto import dynamic_groups
from alirpunkto.views import login as login_module

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------ A. POST-only ------------------------------- #
@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_route('home', '/')
    yield config
    tearDown()


def test_a_crafted_get_with_credentials_is_never_processed(config):
    """/login?form.submitted=1&username=…&password=… used to authenticate:
    the password leaked into browser history and HTTP logs."""
    request = DummyRequest(params={'form.submitted': '1',
                                   'username': 'alice',
                                   'password': 'pw'})
    request.method = 'GET'
    request.session = {}
    request.client_addr = '1.2.3.4'
    oid_lookup = MagicMock()
    with patch.object(login_module, 'is_admin', MagicMock()) as admin, \
         patch.object(login_module, 'get_oid_from_pseudonym', oid_lookup):
        response = login_module.login_view(request)
    assert oid_lookup.call_count == 0
    assert admin.call_count == 0
    assert 'error' not in response          # the plain form, no processing
    assert request.session.get('logged_in') is not True   # still anonymous


def test_credentials_are_read_from_the_post_body_only():
    source = open(os.path.join(ROOT, 'alirpunkto', 'views', 'login.py'),
                  encoding='utf-8').read()
    assert "request.params.get('username'" not in source
    assert "request.params.get('password'" not in source
    assert "request.method == 'POST'" in source


# --------------------------- B. one .env read ------------------------------ #
def test_the_env_file_is_never_reread_through_get_key():
    for module in ('constants_and_globals.py', '__init__.py'):
        source = open(os.path.join(ROOT, 'alirpunkto', module),
                      encoding='utf-8').read()
        assert 'get_key(' not in source.replace(
            'get_key().', '')            # the explanatory comment survives
        assert 'import get_key' not in source
        assert 'get_key,' not in source


# ------------------------ C. LDIF permissions/argv ------------------------- #
# The transport itself moved twice since this file was written: "-"
# slots + environment variables (sixth audit pass), then NUL-delimited
# records on stdin with required-field enforcement (eighth audit pass,
# tests/test_ldif_transport.py). These locks keep the 0068 guarantees
# alive on the current interface.
from tests.test_ldif_transport import VALID_FIELDS, _run_generator


def test_the_ldif_is_born_0600(tmp_path):
    code, _, stderr = _run_generator(tmp_path, dict(VALID_FIELDS))
    assert code == 0, stderr
    mode = stat.S_IMODE(os.stat(tmp_path / "out.ldif").st_mode)
    assert mode == 0o600, oct(mode)


def test_passwords_cross_on_stdin_and_come_out_hashed(tmp_path):
    code, content, _ = _run_generator(
        tmp_path, dict(VALID_FIELDS, ADMIN_PW="from-stdin-pw"))
    assert code == 0
    assert "{SSHA}" in content
    assert "from-stdin-pw" not in content


def test_the_init_script_no_longer_touches_passwords_at_all():
    # Sixth audit pass (§12.4): init.sh used to pre-hash with slappasswd
    # and, without it, pushed the CLEARTEXT password onto argv. Eighth
    # audit pass (§4): the environment slots are gone too — every value
    # crosses the stdin pipe, and the invocation line carries only the
    # two file paths.
    script = open(os.path.join(ROOT, "docker", "init.sh"),
                  encoding="utf-8").read()
    assert "password stored in cleartext" not in script
    assert "hash_password" not in script
    assert "slappasswd" not in script
    assert "generate_ldif_records | python3" in script


# ----------------------- D. checked group modifies ------------------------- #
def test_a_failed_modify_is_logged_and_the_sync_continues(caplog):
    """One failing side of the pair is logged with its operation id and
    the sync keeps applying the rest (best-effort preserved)."""
    from datetime import date, timedelta
    from tests.test_dynamic_groups import _directory, _add_member
    conn = _directory()
    _add_member(conn, 'member-1', mtype='COOPERATOR', active='True',
                shares=1, end=date.today() + timedelta(days=200))
    original_modify = conn.modify
    calls = {'n': 0}

    def first_call_fails(dn, changes):
        calls['n'] += 1
        if calls['n'] == 1:
            return False
        return original_modify(dn, changes)

    conn.modify = first_call_fails
    conn.__enter__ = lambda *a: conn
    conn.__exit__ = lambda *a: False
    with patch.object(dynamic_groups, 'get_ldap_connection',
                      return_value=conn), \
         patch.object(dynamic_groups, 'get_secret', return_value='x'), \
         caplog.at_level('ERROR'):
        result = dynamic_groups.sync_member_groups(
            MagicMock(), 'member-1')
    assert 'group side' in caplog.text        # the failure, identified
    assert calls['n'] >= 2                    # best-effort: kept going
    assert result is not None                 # the sync did not abort
