"""Directory changes reach the SSO infrastructure (issues #266 and #269).

Keycloak mirrors the directory lazily — a new member was unknown to the
mailing lists and the workspace until their first Keycloak login, a
member moved between Dynamic Groups kept their old rights until they
logged into AlirPunkto again. Now every directory write ends by asking
Keycloak, through its admin API, to re-import the changed entries, and a
registration additionally imports the new member at once through the
direct-access grant.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import alirpunkto.dynamic_groups as dg
import alirpunkto.keycloak_sync as ks
import alirpunkto.utils as utils
from alirpunkto.views import register as reg
from alirpunkto.models.member import MemberTypes


@pytest.fixture(autouse=True)
def _fresh_cache():
    ks.reset_cache()
    yield
    ks.reset_cache()


def _wire(components=None, sync_result=None, sync_error=None):
    """Reach the admin API: pytest guard off, realm configured, a fake
    KeycloakAdmin whose component listing and sync are observable."""
    admin = MagicMock()
    admin.get_components.return_value = components if components is not None else [
        {'id': 'ldap-1', 'providerId': 'ldap', 'name': 'openldap'},
        {'id': 'kerb-1', 'providerId': 'kerberos', 'name': 'krb'},
    ]
    if sync_error is not None:
        admin.sync_users.side_effect = sync_error
    else:
        admin.sync_users.return_value = sync_result if sync_result is not None \
            else {'added': 1, 'updated': 2, 'removed': 0, 'failed': 0}
    guards = (
        patch.object(ks, 'PYTEST_CURRENT_TEST', None),
        patch.object(ks, 'KEYCLOAK_SERVER_URL', 'https://kc.test'),
        patch.object(ks, 'KEYCLOAK_REALM', 'realm'),
        patch.object(ks, '_admin_client', return_value=admin),
    )
    return admin, guards


# ------------------------------ propagation -------------------------------- #
def test_propagation_is_skipped_under_pytest_by_default():
    with patch.object(ks, '_admin_client') as client:
        assert ks.propagate_ldap_changes_to_keycloak('x') is False
    client.assert_not_called()


def test_propagation_is_skipped_when_keycloak_is_not_configured():
    with patch.object(ks, 'PYTEST_CURRENT_TEST', None), \
         patch.object(ks, 'KEYCLOAK_SERVER_URL', None), \
         patch.object(ks, '_admin_client') as client:
        assert ks.propagate_ldap_changes_to_keycloak('x') is False
    client.assert_not_called()


def test_propagation_triggers_a_changed_users_sync_of_every_ldap_provider():
    admin, guards = _wire()
    with guards[0], guards[1], guards[2], guards[3]:
        assert ks.propagate_ldap_changes_to_keycloak('registration') is True
    admin.get_components.assert_called_once_with(
        query={'type': ks.USER_STORAGE_PROVIDER_TYPE})
    admin.sync_users.assert_called_once_with('ldap-1', 'triggerChangedUsersSync')


def test_the_storage_ids_are_discovered_once_per_process():
    admin, guards = _wire()
    with guards[0], guards[1], guards[2], guards[3]:
        ks.propagate_ldap_changes_to_keycloak('one')
        ks.propagate_ldap_changes_to_keycloak('two')
    assert admin.get_components.call_count == 1
    assert admin.sync_users.call_count == 2


def test_no_ldap_provider_means_nothing_to_propagate():
    admin, guards = _wire(components=[{'id': 'k', 'providerId': 'kerberos'}])
    with guards[0], guards[1], guards[2], guards[3]:
        assert ks.propagate_ldap_changes_to_keycloak('x') is False
    admin.sync_users.assert_not_called()


def test_a_refused_or_unreachable_keycloak_never_raises_and_forgets_the_cache():
    admin, guards = _wire(sync_error=RuntimeError('401 unauthorized'))
    with guards[0], guards[1], guards[2], guards[3]:
        assert ks.propagate_ldap_changes_to_keycloak('x') is False
        # Next call rediscovers (the realm may have been reconfigured).
        ks.propagate_ldap_changes_to_keycloak('x')
    assert admin.get_components.call_count == 2


def test_the_admin_client_uses_the_client_credentials_of_the_app():
    with patch.object(ks, 'KEYCLOAK_SERVER_URL', 'https://kc.test'), \
         patch.object(ks, 'KEYCLOAK_REALM', 'realm'), \
         patch.object(ks, 'get_secret', side_effect=lambda k: f'<{k}>'), \
         patch('keycloak.KeycloakOpenIDConnection') as connection, \
         patch('keycloak.KeycloakAdmin') as admin:
        ks._admin_client()
    kwargs = connection.call_args.kwargs
    assert kwargs['grant_type'] == 'client_credentials'
    assert kwargs['realm_name'] == 'realm'
    assert kwargs['client_id'] == '<KEYCLOAK_CLIENT_ID>'
    assert kwargs['client_secret_key'] == '<KEYCLOAK_CLIENT_SECRET>'
    assert kwargs['verify'] is True
    assert kwargs['timeout'] == ks.ADMIN_TIMEOUT_SECONDS
    admin.assert_called_once_with(connection=connection.return_value)


# --------------------------- import at registration ------------------------ #
def test_import_authenticates_the_new_member_once_and_discards_the_token():
    with patch.object(utils, 'get_keycloak_token',
                      return_value={'access_token': 'x'}) as token:
        assert ks.import_member_into_keycloak('oid-1', 'pw') is True
    user, password = token.call_args.args
    assert user.oid == 'oid-1' and password == 'pw'


def test_import_reports_a_refusal_without_raising():
    with patch.object(utils, 'get_keycloak_token', return_value=None):
        assert ks.import_member_into_keycloak('oid-1', 'pw') is False
    with patch.object(utils, 'get_keycloak_token',
                      side_effect=RuntimeError('down')):
        assert ks.import_member_into_keycloak('oid-1', 'pw') is False
    assert ks.import_member_into_keycloak('oid-1', '') is False


def test_import_is_a_keycloak_login_of_the_new_member_on_the_wire():
    """Nothing patched between the import and the HTTP client: the call
    is the very password grant ``login_view`` performs, so Keycloak's
    user federation imports the entry exactly as a manual first login
    would (the client's observation behind issue #266)."""
    response = MagicMock(status_code=200, text='')
    response.json.return_value = {
        'access_token': 'a', 'refresh_token': 'r',
        'expires_in': 60, 'refresh_expires_in': 1800}
    with patch.object(utils, 'PYTEST_CURRENT_TEST', None), \
         patch.object(utils, 'KEYCLOAK_SERVER_URL', 'https://kc.test'), \
         patch.object(utils, 'KEYCLOAK_REALM', 'realm'), \
         patch.object(utils, 'get_secret', side_effect=lambda k: f'<{k}>'), \
         patch.object(utils.requests, 'post', return_value=response) as post:
        assert ks.import_member_into_keycloak('oid-1', 'pw') is True
    post.assert_called_once()
    url = post.call_args.args[0]
    payload = post.call_args.kwargs['data']
    assert url == 'https://kc.test/realms/realm/protocol/openid-connect/token'
    assert payload['grant_type'] == 'password'
    assert payload['username'] == 'oid-1'
    assert payload['password'] == 'pw'
    assert payload['client_id'] == '<KEYCLOAK_CLIENT_ID>'


# ------------------------------ the event sources -------------------------- #
def test_a_successful_profile_update_notifies_keycloak():
    from tests.test_ldap_utils import _fully_populated_member, _run_update
    with patch.object(utils, 'notify_keycloak_of_directory_change') as notify, \
         patch('alirpunkto.dynamic_groups.sync_member_groups'):
        result, _ = _run_update(_fully_populated_member(),
                                ['date_end_validity_yearly_contribution'])
    assert result['status'] == 'success'
    notify.assert_called_once()
    assert 'date_end_validity_yearly_contribution' in notify.call_args.args[0]


def test_a_failed_profile_update_does_not_notify_keycloak():
    from tests.test_ldap_utils import _fully_populated_member
    from contextlib import contextmanager

    @contextmanager
    def failing_connection(**_):
        conn = MagicMock()
        conn.modify.return_value = False
        conn.result = {'description': 'other'}
        yield conn

    with patch.object(utils, 'get_ldap_connection', failing_connection), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        result = utils.update_ldap_member(MagicMock(), _fully_populated_member(),
                                          fields_to_update=['iban'])
    assert result['status'] == 'error'
    notify.assert_not_called()


def test_a_registration_notifies_keycloak():
    from tests.test_dynamic_groups import _directory
    conn = _directory()
    candidature = SimpleNamespace(
        oid='new-9', pseudonym='fresh9', email='f9@example.com',
        type=MemberTypes.ORDINARY,
        data=SimpleNamespace(password='{SSHA}x', fullname=None,
                             fullsurname='Fresh', description=None,
                             lang1=None, lang2=None, lang3=None,
                             is_active=True))
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', return_value='s'), \
         patch.object(utils, 'is_valid_unique_pseudonym', return_value=None), \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        result = utils.register_user_to_ldap(SimpleNamespace(), candidature,
                                             'pw')
    assert result['status'] == 'success'
    notify.assert_called_once()
    assert 'new-9' in notify.call_args.args[0]


def test_the_daily_scan_notifies_keycloak_only_when_someone_moved():
    from tests.test_dynamic_groups import (
        COMMUNITY, COOPERATORS, _add_member, _directory)
    today = date(2026, 7, 30)
    conn = _directory()
    _add_member(conn, 'm3', shares=2, end=today - timedelta(days=1),
                groups=(COMMUNITY, COOPERATORS))
    with patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        assert dg.daily_group_scan(SimpleNamespace(), today=today) == ['m3']
        notify.assert_called_once()
        assert '1 member(s)' in notify.call_args.args[0]
        # Second pass: converged, nothing to tell Keycloak.
        assert dg.daily_group_scan(SimpleNamespace(), today=today) == []
    assert notify.call_count == 1


def test_the_ordinary_registration_imports_the_member_at_once(members_mapping):
    """The view hands Keycloak the member's own password right after the
    directory entry exists — the only moment the cleartext is at hand."""
    from webob.multidict import MultiDict
    from alirpunkto.models.candidature import Candidature, CandidatureStates
    candidature = Candidature()
    candidature.email = 'ord@example.org'
    candidature.type = MemberTypes.ORDINARY
    candidature.candidature_state = CandidatureStates.CONFIRMED_HUMAN
    form = SimpleNamespace(render=lambda **k: '<form/>')
    params = MultiDict()
    for key, value in [('submit', '1'), ('pseudonym', 'OrdUser'),
                       ('password', 'ValidPass123@'),
                       ('password_confirm', 'ValidPass123@')]:
        params.add(key, value)
    request = SimpleNamespace(
        POST=params, params=params, method='POST', tm=MagicMock(),
        session=MagicMock(),
        registry=SimpleNamespace(settings={'site_name': 'S',
                                           'domain_name': 'D',
                                           'organization_details': 'O'}),
        route_url=lambda *a, **k: 'http://example/x',
        route_path=lambda *a, **k: '/x',
        localizer=SimpleNamespace(translate=lambda s: str(s)))
    with patch.object(reg, '_build_candidature_form',
                      return_value=(form, {}, None)), \
         patch.object(reg, 'is_valid_unique_pseudonym', return_value=None), \
         patch.object(reg, 'register_user_to_ldap',
                      return_value={'status': 'success'}), \
         patch.object(reg, 'send_candidature_state_change_email',
                      return_value=None), \
         patch.object(reg, 'get_candidatures', return_value=members_mapping), \
         patch.object(reg, 'import_member_into_keycloak') as importer:
        reg.handle_confirmed_human_state(request, candidature)
    assert candidature.candidature_state == CandidatureStates.APPROVED
    importer.assert_called_once_with(candidature.oid, 'ValidPass123@')


def test_a_failed_ordinary_registration_imports_nothing(members_mapping):
    from webob.multidict import MultiDict
    from alirpunkto.models.candidature import Candidature, CandidatureStates
    candidature = Candidature()
    candidature.email = 'ord@example.org'
    candidature.type = MemberTypes.ORDINARY
    candidature.candidature_state = CandidatureStates.CONFIRMED_HUMAN
    form = SimpleNamespace(render=lambda **k: '<form/>')
    params = MultiDict()
    for key, value in [('submit', '1'), ('pseudonym', 'OrdUser'),
                       ('password', 'ValidPass123@'),
                       ('password_confirm', 'ValidPass123@')]:
        params.add(key, value)
    request = SimpleNamespace(
        POST=params, params=params, method='POST', tm=MagicMock(),
        session=MagicMock(),
        registry=SimpleNamespace(settings={'site_name': 'S',
                                           'domain_name': 'D',
                                           'organization_details': 'O'}),
        route_url=lambda *a, **k: 'http://example/x',
        route_path=lambda *a, **k: '/x',
        localizer=SimpleNamespace(translate=lambda s: str(s)))
    with patch.object(reg, '_build_candidature_form',
                      return_value=(form, {}, None)), \
         patch.object(reg, 'is_valid_unique_pseudonym', return_value=None), \
         patch.object(reg, 'register_user_to_ldap',
                      return_value={'status': 'error', 'message': 'no'}), \
         patch.object(reg, 'get_candidatures', return_value=members_mapping), \
         patch.object(reg, 'import_member_into_keycloak') as importer:
        reg.handle_confirmed_human_state(request, candidature)
    importer.assert_not_called()
