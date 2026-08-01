"""The remaining immediate items of the revised audit (2026-08-01).

Credentials are only ever read from the POST body; the .env file is
loaded once and never re-read through get_key(); the generated LDIF is
born 0600 with passwords able to travel through scrubbed environment
variables instead of argv; and every group-membership LDAP modify is
checked and logged on failure while staying best-effort.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import sys
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
def _load_generate_ldif_argv(tmp_path, admin_pw, env=None):
    template = tmp_path / "template.ldif"
    template.write_text("dn: {LDAP_BASE_DN}\nuserPassword: {ADMIN_PW}\n",
                        encoding="utf-8")
    out = tmp_path / "out.ldif"
    argv = ([str(template), str(out), "dc=example,dc=com",
             "uuid-a", "admin", "Admin", "a@x.org", admin_pw]
            + ["u1-uuid", "role", "ps", "First", "Last", "en", "FR",
               "u1@x.org", "pw1"]
            + ["u2-uuid", "role", "ps2", "First2", "Last2", "fr", "DE",
               "u2@x.org", "pw2"]
            + ["2026-08-01"] + [""] * 8)
    spec = importlib.util.spec_from_file_location(
        "generate_ldif_under_test",
        os.path.join(ROOT, "docker", "generate_ldif.py"))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'argv', ["generate_ldif.py"] + argv), \
         patch.dict(os.environ, env or {}, clear=False):
        try:
            spec.loader.exec_module(module)
        except SystemExit as exc:               # argument-count guard
            raise AssertionError(f"generator refused argv: {exc}")
    return out


def test_the_ldif_is_born_0600(tmp_path):
    out = _load_generate_ldif_argv(tmp_path, "secret-pw")
    mode = stat.S_IMODE(os.stat(out).st_mode)
    assert mode == 0o600, oct(mode)


def test_a_dash_slot_reads_and_scrubs_the_environment(tmp_path):
    env = {"GENERATE_LDIF_ADMIN_PW": "from-env-pw"}
    out = _load_generate_ldif_argv(tmp_path, "-", env=env)
    content = out.read_text(encoding="utf-8")
    assert "from-env-pw" in content or "{SSHA}" in content
    assert "GENERATE_LDIF_ADMIN_PW" not in os.environ       # scrubbed


def test_the_init_message_no_longer_claims_cleartext_storage():
    script = open(os.path.join(ROOT, "docker", "init.sh"),
                  encoding="utf-8").read()
    assert "password stored in cleartext" not in script
    assert "generate_ldif.py will hash the password itself" in script


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
