"""The administrative update of a Cooperator's financial facts (issue #267).

Issue #75 made the number of shares and the yearly-contribution validity
date "updated by the online commercial site via a Python script"; issue
#149 then turned every other member's profile into a read-only card, so
the script's POST on the profile form wrote nothing and a Cooperator who
had just paid kept losing their rights. ``/update_contribution`` is the
dedicated write path: administrator session, CSRF, the two fields of
#75 and nothing else, JSON in and out.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.testing import DummyRequest

from alirpunkto.models.member import MemberDatas, MemberStates, MemberTypes
from alirpunkto.views import update_contribution as uc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return 'csrf'


def _request(post=None, *, method='POST', logged_in=True, oid='adm-1'):
    request = DummyRequest(post=post or {})
    request.method = method
    request.session = _Session()
    if logged_in:
        request.session['logged_in'] = True
        request.session['user'] = json.dumps({'oid': oid, 'name': oid})
    return request


def _admin():
    return SimpleNamespace(oid='adm-1', type=MemberTypes.ADMINISTRATOR)


def _cooperator(**data):
    base = dict(password='x', number_shares_owned=0,
                date_end_validity_yearly_contribution=datetime.datetime(
                    2020, 1, 1, 12))
    base.update(data)
    return SimpleNamespace(oid='coop-1', type=MemberTypes.COOPERATOR,
                           member_state=MemberStates.REGISTRED,
                           data=MemberDatas(**base))


def _call(request, *, accessor=_admin(), target=None, ldap=None,
          groups=('communityMembersGroup', 'cooperatorsGroup')):
    ldap = ldap if ldap is not None else MagicMock(
        return_value={'status': 'success'})
    with patch.object(uc, 'get_member_by_oid', return_value=accessor), \
         patch.object(uc, 'update_member_from_ldap', return_value=target), \
         patch.object(uc, 'update_ldap_member', ldap), \
         patch('alirpunkto.dynamic_groups.get_member_groups',
               return_value=set(groups)):
        return uc.update_contribution(request), request.response.status_code, ldap


# ------------------------------- refusals --------------------------------- #
def test_only_post_is_accepted():
    body, status, _ = _call(_request(method='GET'))
    assert (status, body['error']) == (405, 'method_not_allowed')


def test_an_anonymous_call_is_refused():
    body, status, _ = _call(_request({'oid': 'coop-1'}, logged_in=False))
    assert (status, body['error']) == (401, 'not_logged_in')


def test_a_non_administrator_is_refused():
    member = SimpleNamespace(oid='m-1', type=MemberTypes.COOPERATOR)
    body, status, ldap = _call(_request({'oid': 'coop-1',
                                         'number_shares_owned': '1'}),
                               accessor=member)
    assert (status, body['error']) == (403, 'administrator_required')
    ldap.assert_not_called()


def test_the_oid_is_required():
    body, status, _ = _call(_request({'number_shares_owned': '1'}))
    assert (status, body['error']) == (400, 'missing_oid')


def test_at_least_one_of_the_two_fields_is_required():
    body, status, _ = _call(_request({'oid': 'coop-1', 'description': 'x'}))
    assert (status, body['error']) == (400, 'nothing_to_update')
    assert body['accepted_fields'] == ['number_shares_owned',
                                       'date_end_validity_yearly_contribution']


def test_invalid_values_are_named():
    body, status, _ = _call(_request({
        'oid': 'coop-1', 'number_shares_owned': '-2',
        'date_end_validity_yearly_contribution': '30/06/2027'}))
    assert (status, body['error']) == (400, 'invalid_value')
    assert set(body['fields']) == {'number_shares_owned',
                                   'date_end_validity_yearly_contribution'}


def test_an_unknown_member_is_a_404():
    body, status, _ = _call(_request({'oid': 'ghost',
                                      'number_shares_owned': '1'}),
                            target=None)
    assert (status, body['error']) == (404, 'unknown_member')


def test_an_ordinary_member_has_no_financial_facts():
    ordinary = SimpleNamespace(oid='o-1', type=MemberTypes.ORDINARY,
                               data=MemberDatas(password='x'))
    body, status, ldap = _call(_request({'oid': 'o-1',
                                         'number_shares_owned': '1'}),
                               target=ordinary)
    assert (status, body['error']) == (409, 'not_a_cooperator')
    assert body['member_type'] == 'ORDINARY'
    ldap.assert_not_called()


# ------------------------------- the write -------------------------------- #
def test_the_payment_updates_both_facts_and_answers_the_new_groups():
    """The exact shape ``tools/update_cooperator.py`` sends."""
    target = _cooperator()
    body, status, ldap = _call(_request({
        'oid': 'coop-1', 'csrf_token': 'csrf',
        'number_shares_owned': '1',
        'date_end_validity_yearly_contribution': '2027-06-30'}),
        target=target)
    assert status == 200
    assert body['status'] == 'success'
    assert target.data.number_shares_owned == 1
    assert target.data.date_end_validity_yearly_contribution == \
        datetime.datetime(2027, 6, 30, 12, 0, 0)
    ldap.assert_called_once()
    assert set(ldap.call_args.kwargs['fields_to_update']) == {
        'number_shares_owned', 'date_end_validity_yearly_contribution'}
    assert body['updated_fields'] == ['number_shares_owned',
                                      'date_end_validity_yearly_contribution']
    assert body['number_shares_owned'] == 1
    assert body['date_end_validity_yearly_contribution'] == '2027-06-30'
    assert body['groups'] == ['communityMembersGroup', 'cooperatorsGroup']
    assert target.member_state == MemberStates.DATA_MODIFIED


def test_only_the_changed_fact_is_written():
    target = _cooperator(number_shares_owned=1)
    body, status, ldap = _call(_request({
        'oid': 'coop-1', 'number_shares_owned': '1',
        'date_end_validity_yearly_contribution': '2027-06-30'}),
        target=target)
    assert status == 200
    assert ldap.call_args.kwargs['fields_to_update'] == [
        'date_end_validity_yearly_contribution']


def test_an_unchanged_payload_writes_nothing_but_still_answers():
    target = _cooperator(number_shares_owned=1)
    body, status, ldap = _call(_request({'oid': 'coop-1',
                                         'number_shares_owned': '1'}),
                               target=target)
    assert status == 200 and body['updated_fields'] == []
    ldap.assert_not_called()
    assert target.member_state == MemberStates.REGISTRED


def test_a_failed_directory_write_is_reported():
    target = _cooperator()
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '3'}),
                            target=target,
                            ldap=MagicMock(return_value={'status': 'error'}))
    assert (status, body['error']) == (502, 'error_while_updating_member')
    assert target.member_state == MemberStates.REGISTRED


def test_the_directory_write_triggers_the_group_move_and_keycloak():
    """End to end through the real ``update_ldap_member``: the write,
    then the group synchroniser, then the Keycloak propagation."""
    from alirpunkto import utils
    from contextlib import contextmanager

    @contextmanager
    def connection(**_):
        conn = MagicMock()
        conn.modify.return_value = True
        yield conn

    target = _cooperator()
    with patch.object(utils, 'get_ldap_connection', connection), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch('alirpunkto.dynamic_groups.sync_member_groups') as sync, \
         patch.object(utils, 'notify_keycloak_of_directory_change') as notify:
        body, status, _ = _call(_request({
            'oid': 'coop-1',
            'date_end_validity_yearly_contribution': '2027-06-30'}),
            target=target, ldap=utils.update_ldap_member)
    assert status == 200
    sync.assert_called_once()
    assert sync.call_args.args[1] == 'coop-1'
    notify.assert_called_once()


# ------------------------------- the route -------------------------------- #
def test_the_route_is_registered(app):
    introspector = app.registry.introspector
    routes = {intr['introspectable']['name']
              for intr in introspector.get_category('routes') or ()}
    assert 'update_contribution' in routes


@pytest.mark.functional
def test_the_endpoint_refuses_an_anonymous_post(testapp):
    """Through the real pipeline: CSRF first (403), never a 500."""
    response = testapp.post('/update_contribution', {'oid': 'x'},
                            expect_errors=True)
    assert response.status_code in (400, 403)


# ------------------------------- the script ------------------------------- #
def _load_script():
    path = os.path.join(ROOT, 'tools', 'update_cooperator.py')
    spec = importlib.util.spec_from_file_location('update_cooperator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_script_posts_to_the_dedicated_endpoint_with_the_csrf_token():
    script = _load_script()
    session = MagicMock()
    answer = MagicMock(status_code=200)
    answer.json.return_value = {'status': 'success', 'number_shares_owned': 1,
                                'date_end_validity_yearly_contribution':
                                    '2027-06-30',
                                'groups': ['cooperatorsGroup']}
    session.post.return_value = answer
    script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    url, = session.post.call_args.args
    data = session.post.call_args.kwargs['data']
    assert url.endswith('/update_contribution')
    assert data == {'oid': 'coop-1', 'csrf_token': 'tok',
                    'number_shares_owned': '1',
                    'date_end_validity_yearly_contribution': '2027-06-30'}


def test_the_script_raises_on_a_refusal_instead_of_printing_a_warning():
    script = _load_script()
    session = MagicMock()
    answer = MagicMock(status_code=403)
    answer.json.return_value = {'status': 'error',
                                'error': 'administrator_required'}
    session.post.return_value = answer
    with pytest.raises(RuntimeError, match='administrator_required'):
        script.modify_member(session, 'coop-1', '1', None, 'tok')


def test_the_script_login_reads_the_csrf_token_from_the_directory_page():
    script = _load_script()
    session = MagicMock()
    page = MagicMock(text='<input name="csrf_token" value="abc123" />')
    session.get.return_value = page
    assert script.login(session, 'admin', 'pw') == 'abc123'
    session.get.return_value = MagicMock(text='<html>home</html>')
    with pytest.raises(ValueError):
        script.login(session, 'admin', 'pw')
