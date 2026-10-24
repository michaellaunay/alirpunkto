"""Transversal audit of 2026-10-24, lot 2 — the circumscribed P1s.

A06  The purge works on a REAL Member (the e-mail setter refused None),
     checks the directory's answer to the delete, and erases the change
     history that kept the previous data alive.
A07  The password branch of the profile form runs once, for its own
     field — never for a language or a name.
A10  A Keycloak "ignored" synchronisation is not a success, and a failed
     propagation leaves a persistent marker the daily scan retries even
     when nobody moved that day.
A12  Neither the registration POST nor the e-mail bodies reach the logs.
A13  The backup script defaults to the configured Data.fs path, refuses
     a partial backup by default, writes a manifest and verifies the
     archive before pruning.
A15  The Python client: URL priority, https by default, no credential
     replay through redirects, private cookie file.
A16  The provider management view writes providers only.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import alirpunkto.dynamic_groups as dg
import alirpunkto.keycloak_sync as ks
import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import _
from alirpunkto.models.member import (
    Member, MemberDatas, MemberStates, MemberTypes,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding='utf-8').read()


# ================================ A06 ====================================== #
def _gone_member(oid='gone-1'):
    member = Member(data=MemberDatas(password='', fullname='Jean',
                                     fullsurname='Doe', nationality='FR',
                                     lang1='fr'),
                    oid=oid, member_state=MemberStates.REGISTRED,
                    type=MemberTypes.COOPERATOR, email='jean@example.org',
                    pseudonym='jdoe')
    member.email = 'jean2@example.org'          # a change: history grows
    member.member_state = MemberStates.UNSUBSCRIBED
    member.data.date_erasure_all_data = date.today() - timedelta(days=1)
    member.departure_date = datetime.now() - timedelta(days=200)
    member.departure_reason = 'resignation'
    return member


def _mock_directory(oid='gone-1'):
    from ldap3 import ALL, MOCK_SYNC, Connection, Server
    from alirpunkto.constants_and_globals import LDAP_BASE_DN, LDAP_OU
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    dn = f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU \
        else f"uid={oid},{LDAP_BASE_DN}"
    conn.add(dn, attributes={'objectClass': ['top', 'inetOrgPerson'],
                             'uid': oid, 'cn': 'jdoe', 'sn': 'Doe'})
    return conn, dn


def test_the_purge_works_on_a_real_member_and_forgets_its_history():
    """SimpleNamespace stand-ins hid it: ``member.email = None`` raised
    TypeError on a real Member after the LDAP entry was already gone,
    and the previous MemberDatas survived in the change history."""
    conn, dn = _mock_directory()
    member = _gone_member()
    assert any(isinstance(event.value_before, MemberDatas) or
               event.value_before == 'jean@example.org'
               for event in member.modifications)
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, '_send_erasure_confirmation') as farewell:
        purged = utils.purge_unsubscribed_members(
            SimpleNamespace(), members={'gone-1': member})
    assert purged == ['gone-1']
    assert member.member_state == MemberStates.DELETED
    assert member.pseudonym == 'jdoe'
    assert member.departure_reason == 'resignation'
    assert member.email == ''
    assert member.data.fullname is None and member.data.nationality is None
    history = member.modifications
    assert all(event.value_before in (None, 'None') or
               isinstance(event.value_before, str) and
               'jean' not in event.value_before.lower()
               for event in history)
    assert not any(isinstance(event.value_before, MemberDatas)
                   for event in history)
    assert member.email_send_status_history == []
    farewell.assert_called_once()
    assert farewell.call_args.args[1] == 'jean2@example.org'
    conn.search(dn, '(objectclass=*)', attributes=['cn'])
    assert not conn.entries


def test_a_directory_that_refuses_the_delete_leaves_the_member_intact():
    member = _gone_member()
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda s, *a: False
    conn.delete.return_value = False
    conn.result = {'description': 'insufficientAccessRights'}
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, '_send_erasure_confirmation') as farewell:
        purged = utils.purge_unsubscribed_members(
            SimpleNamespace(), members={'gone-1': member})
    assert purged == []
    assert member.member_state == MemberStates.UNSUBSCRIBED
    assert member.data.fullname == 'Jean'
    farewell.assert_not_called()


def test_an_entry_already_gone_from_the_directory_still_gets_erased():
    """Resuming an interrupted pass: the LDAP delete answers noSuchObject
    (32) — the directory side is done, the ZODB side must follow."""
    member = _gone_member()
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = lambda s, *a: False
    conn.delete.return_value = False
    conn.result = {'result': 32, 'description': 'noSuchObject'}
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, '_send_erasure_confirmation'):
        purged = utils.purge_unsubscribed_members(
            SimpleNamespace(), members={'gone-1': member})
    assert purged == ['gone-1']
    assert member.member_state == MemberStates.DELETED
    assert member.data.fullname is None


# ================================ A07 ====================================== #
def test_the_password_branch_is_keyed_on_its_own_field():
    source = _read('alirpunkto', 'views', 'modify_member.py')
    assert 'elif field == "password":' in source
    assert '"password" in request.POST and "password" in writable_fields' \
        not in source


def test_a_language_change_with_an_empty_password_field_is_not_a_password_change():
    """Through the real view, with the permission matrix of a member
    editing their own profile: lang1 changes, the empty password field
    is ignored, update_member_password never runs."""
    from tests.test_modify_member import (
        _Request, _accessed, _accessor, _perms, _session, _wire, _WRITE)
    from alirpunkto.views.modify_member import modify_member
    accessed = _accessed(lang1='fr', password='x')
    perms = _perms(lang1=_WRITE, password=_WRITE)
    request = _Request(post={'modify': 'modify', 'lang1': 'en',
                             'password': '', 'password_confirm': ''},
                       session=_session())
    pwd = MagicMock(return_value={'status': 'success'})
    with _wire(_accessor(), accessed, perms,
               update_ldap_member=MagicMock(return_value={'status': 'success'}),
               update_member_password=pwd,
               switch_request_language=MagicMock()):
        result = modify_member(request)
    assert accessed.data.lang1 == 'en'
    pwd.assert_not_called()
    assert result.get('error') is None
    assert not [m for q, m in request.session.get('_flashed', []) if q == 'error']


def test_a_language_and_a_password_change_run_the_password_change_once():
    from tests.test_modify_member import (
        _Request, _accessed, _accessor, _perms, _session, _wire, _WRITE)
    from alirpunkto.views.modify_member import modify_member
    accessed = _accessed(lang1='fr', password='x')
    perms = _perms(lang1=_WRITE, lang2=_WRITE, password=_WRITE)
    request = _Request(post={'modify': 'modify', 'lang1': 'en', 'lang2': 'de',
                             'password': 'ValidPass123@',
                             'password_confirm': 'ValidPass123@'},
                       session=_session())
    pwd = MagicMock(return_value={'status': 'success'})
    with _wire(_accessor(), accessed, perms,
               update_ldap_member=MagicMock(return_value={'status': 'success'}),
               update_member_password=pwd,
               switch_request_language=MagicMock()):
        modify_member(request)
    assert pwd.call_count == 1
    assert accessed.data.lang1 == 'en' and accessed.data.lang2 == 'de'


# ================================ A10 ====================================== #
def test_an_ignored_synchronisation_is_not_a_propagation():
    assert ks.sync_failed({'ignored': True, 'added': 0, 'updated': 0,
                           'removed': 0, 'failed': 0}) is True
    assert ks.sync_failed({'ignored': False, 'failed': 0}) is False


def _wire(sync_result=None, sync_error=None):
    admin = MagicMock()
    admin.get_components.return_value = [
        {'id': 'ldap-1', 'providerId': 'ldap', 'name': 'openldap'}]
    if sync_error is not None:
        admin.sync_users.side_effect = sync_error
    else:
        admin.sync_users.return_value = sync_result
    return admin, (
        patch.object(ks, 'PYTEST_CURRENT_TEST', None),
        patch.object(ks, 'KEYCLOAK_SERVER_URL', 'https://kc.test'),
        patch.object(ks, 'KEYCLOAK_REALM', 'realm'),
        patch.object(ks, '_admin_client', return_value=admin))


def test_a_failed_propagation_leaves_a_marker_a_success_clears():
    ks.reset_cache()
    _, guards = _wire(sync_error=RuntimeError('keycloak down'))
    with guards[0], guards[1], guards[2], guards[3]:
        assert ks.propagate_ldap_changes_to_keycloak('payment of x') is False
    assert ks.propagation_pending() is True
    assert 'payment of x' in open(ks.PENDING_MARKER_PATH).read()
    ks.reset_cache()
    _, guards = _wire(sync_result={'added': 0, 'updated': 1, 'removed': 0,
                                   'failed': 0})
    with guards[0], guards[1], guards[2], guards[3]:
        assert ks.propagate_ldap_changes_to_keycloak('retry') is True
    assert ks.propagation_pending() is False


def test_the_daily_scan_retries_a_pending_propagation_on_a_quiet_day():
    """The directory converged yesterday while Keycloak was down; today
    nobody moves — the scan must still call Keycloak."""
    from tests.test_dynamic_groups import _directory
    conn = _directory()                          # groups only, no member
    ks._mark_pending('yesterday')
    with patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        assert dg.daily_group_scan(SimpleNamespace(), today=date(2026, 7, 30)) == []
    notify.assert_called_once()
    assert 'pending propagation retried' in notify.call_args.args[0]


def test_the_daily_scan_stays_quiet_without_changes_nor_pending_work():
    from tests.test_dynamic_groups import _directory
    conn = _directory()
    with patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        assert dg.daily_group_scan(SimpleNamespace(), today=date(2026, 7, 30)) == []
    notify.assert_not_called()


# ================================ A12 ====================================== #
def test_the_registration_post_and_the_mail_bodies_stay_out_of_the_logs():
    register = _read('alirpunkto', 'views', 'register.py')
    assert '{request.POST}' not in register
    assert 'POST fields: ' in register
    source = _read('alirpunkto', 'utils.py')
    for line in source.splitlines():
        if 'log.' in line and 'text_body' in line:
            assert '{text_body}' not in line, line
    assert 'and contains {text_body}' not in source


# ================================ A13 ====================================== #
def test_the_backup_script_defaults_and_guards():
    script = _read('docker', 'backup.sh')
    ini = _read('production.ini')
    assert 'var/filestorage/Data.fs' in ini
    assert 'ZODB_PATH="${ZODB_PATH:-/home/alirpunkto/app/var/filestorage/Data.fs}"' \
        in script
    assert '/app/var/Data.fs}' not in script
    assert 'umask 077' in script
    assert 'ALLOW_PARTIAL' in script
    assert 'sha256sum' in script and 'MANIFEST' in script
    # The archive is verified BEFORE the previous ones are pruned.
    assert script.index('tar -tzf') < script.index('-mtime "+${KEEP_DAYS}" -print -delete')
    assert 'set -euo pipefail' in script


# ================================ A15 ====================================== #
def test_the_client_url_priority_is_command_line_then_env_then_default():
    source = _read('tools', 'update_cooperator.py')
    assert 'parser.add_argument("--base_url", type=str, default=None' in source
    assert 'allow_redirects=False' in source
    assert 'os.O_CREAT | os.O_TRUNC, 0o600' in source


def test_the_client_cookie_file_is_private(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'update_cooperator_lot2',
        os.path.join(ROOT, 'tools', 'update_cooperator.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    session = SimpleNamespace(cookies=[SimpleNamespace(name='session',
                                                       value='abc')])
    path = tmp_path / 'cookies.txt'
    module.save_cookies(session, path)
    assert path.read_text() == 'session=abc\n'
    assert oct(path.stat().st_mode & 0o777) == '0o600'


# ================================ A16 ====================================== #
def test_the_provider_view_refuses_to_update_a_cooperator():
    from tests.test_manage_provider import _Request, _dispatch, _wire as wire
    from alirpunkto.views import manage_provider as mp
    from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID
    admin = Member(oid='admin-1')
    admin.type = MemberTypes.ADMINISTRATOR
    cooperator = Member(oid='c-1')
    cooperator.type = MemberTypes.COOPERATOR
    cooperator.email = 'coop@example.org'
    cooperator.data = MemberDatas()
    request = _Request(method='POST', post={
        'update': '1', ACCESSED_MEMBER_OID: 'c-1',
        'provider_email': 'hijacked@example.org',
        'provider_password': 'ValidPass123@'})
    ldap = MagicMock(return_value={'status': 'success'})
    pwd = MagicMock(return_value={'status': 'success'})
    with wire(admin, get_member=_dispatch(**{'admin-1': admin, 'c-1': cooperator}),
              update_ldap_member=ldap, update_member_password=pwd):
        result = mp.manage_provider_view(request)
    assert result['error'] == _('no_permission')
    ldap.assert_not_called()
    pwd.assert_not_called()
    assert cooperator.email == 'coop@example.org'
    assert re.search(r"member\.type != MemberTypes\.PROVIDER",
                     _read('alirpunkto', 'views', 'manage_provider.py'))
