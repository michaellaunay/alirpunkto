"""The administrative update of a Cooperator's financial facts (issue #267).

Issue #75 made the number of shares and the yearly-contribution validity
date "updated by the online commercial site via a Python script"; issue
#149 then turned every other member's profile into a read-only card, so
the script's POST on the profile form wrote nothing and a Cooperator who
had just paid kept losing their rights. ``/update_contribution`` is the
dedicated write path: administrator session, CSRF, the two fields of
#75 and nothing else, JSON in and out.

External audit of 2026-10-24 (train 0117): the answer now tells the
three outcomes apart — facts recorded, groups converged, SSO told — and
is ``partial`` when the last two lag; ``groups`` is ``null`` when the
directory could not be read back; the script checks what comes back and
treats ``0`` shares as a value and "nothing to send" as an error.
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

ALL_GREEN = {'status': 'success', 'groups_sync': 'success',
             'keycloak_sync': 'success'}


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
          groups=('communityMembersGroup', 'cooperatorsGroup'),
          repropagate=None):
    ldap = ldap if ldap is not None else MagicMock(return_value=dict(ALL_GREEN))
    repropagate = repropagate if repropagate is not None else MagicMock(
        return_value={'groups_sync': 'success', 'keycloak_sync': 'success'})
    read = MagicMock(return_value=set(groups)) if groups is not None \
        else MagicMock(side_effect=OSError("directory down"))
    with patch.object(uc, 'get_member_by_oid', return_value=accessor), \
         patch.object(uc, 'update_member_from_ldap', return_value=target), \
         patch.object(uc, 'update_ldap_member', ldap), \
         patch.object(uc, 'propagate_member_change', repropagate), \
         patch('alirpunkto.dynamic_groups.read_member_groups', read):
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


def test_the_share_ceiling_is_the_same_on_the_server(monkeypatch):
    """Third audit pass (P9): the clients' ceiling must exist in the
    contract too, not only in their own code."""
    script = _load_script()
    assert uc.MAX_SHARES == script.MAX_SHARES
    body, status, ldap = _call(_request({
        'oid': 'coop-1', 'number_shares_owned': str(uc.MAX_SHARES + 1)}),
        target=_cooperator())
    assert (status, body['error']) == (400, 'invalid_value')
    assert str(uc.MAX_SHARES) in body['fields']['number_shares_owned']
    ldap.assert_not_called()
    body, status, _ = _call(_request({
        'oid': 'coop-1', 'number_shares_owned': str(uc.MAX_SHARES)}),
        target=_cooperator())
    assert status == 200 and body['number_shares_owned'] == uc.MAX_SHARES


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


def test_zero_shares_is_a_value_the_endpoint_records():
    target = _cooperator(number_shares_owned=3)
    body, status, ldap = _call(_request({'oid': 'coop-1',
                                         'number_shares_owned': '0'}),
                               target=target)
    assert status == 200 and body['number_shares_owned'] == 0
    assert ldap.call_args.kwargs['fields_to_update'] == ['number_shares_owned']


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
    assert body['financial_update'] == 'unchanged'


def test_a_failed_directory_write_is_reported():
    target = _cooperator()
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '3'}),
                            target=target,
                            ldap=MagicMock(return_value={'status': 'error'}))
    assert (status, body['error']) == (502, 'error_while_updating_member')
    assert target.member_state == MemberStates.REGISTRED


# ------------------- the three outcomes (audit 2026-10-24, A2) ------------ #
def test_a_full_success_names_its_three_steps():
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '2'}),
                            target=_cooperator())
    assert status == 200
    assert (body['status'], body['financial_update'], body['groups_sync'],
            body['keycloak_sync']) == ('success', 'success', 'success',
                                       'success')


@pytest.mark.parametrize("lagging", ['groups_sync', 'keycloak_sync'])
def test_a_lagging_propagation_is_a_partial_answer_not_a_success(lagging):
    """The facts ARE in the directory (HTTP 200, member DATA_MODIFIED),
    but a client testing for ``success`` must fail loudly and retry."""
    result = dict(ALL_GREEN, **{lagging: 'error'})
    target = _cooperator()
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '2'}),
                            target=target,
                            ldap=MagicMock(return_value=result))
    assert status == 200
    assert body['status'] == 'partial'
    assert body[lagging] == 'error'
    assert body['financial_update'] == 'success'
    assert body['number_shares_owned'] == 2
    assert target.member_state == MemberStates.DATA_MODIFIED


def test_a_legacy_write_result_without_sub_statuses_reads_as_partial():
    """Defensive: a ``{'status': 'success'}`` with no propagation report
    must not be promoted to a full success."""
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '2'}),
                            target=_cooperator(),
                            ldap=MagicMock(return_value={'status': 'success'}))
    assert (status, body['status']) == (200, 'partial')


def test_an_unreadable_directory_answers_null_groups_not_an_empty_list():
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '2'}),
                            target=_cooperator(), groups=None)
    assert status == 200
    assert body['groups'] is None
    assert body['status'] == 'partial'


def test_a_retry_with_unchanged_facts_re_propagates_so_it_can_repair():
    """After a partial answer the shop runs the same command again: the
    facts are already there, so the groups and Keycloak must be driven
    again — otherwise the retry could never converge."""
    repropagate = MagicMock(return_value={'groups_sync': 'success',
                                          'keycloak_sync': 'success'})
    target = _cooperator(number_shares_owned=1)
    body, status, ldap = _call(_request({'oid': 'coop-1',
                                         'number_shares_owned': '1'}),
                               target=target, repropagate=repropagate)
    ldap.assert_not_called()
    repropagate.assert_called_once()
    assert repropagate.call_args.args[1] == 'coop-1'
    assert (status, body['status'], body['financial_update']) == (
        200, 'success', 'unchanged')


def test_a_retry_whose_propagation_still_fails_stays_partial():
    repropagate = MagicMock(return_value={'groups_sync': 'error',
                                          'keycloak_sync': 'success'})
    body, status, _ = _call(_request({'oid': 'coop-1',
                                      'number_shares_owned': '1'}),
                            target=_cooperator(number_shares_owned=1),
                            repropagate=repropagate)
    assert (status, body['status'], body['groups_sync']) == (
        200, 'partial', 'error')


def test_propagate_member_change_reports_each_step():
    from alirpunkto import utils
    cases = [
        ({'cooperatorsGroup'}, True, ('success', 'success')),
        (None, True, ('error', 'success')),
        ({'cooperatorsGroup'}, False, ('success', 'error')),
        (None, False, ('error', 'error')),
    ]
    for target, propagated, expected in cases:
        with patch('alirpunkto.dynamic_groups.sync_member_groups',
                   return_value=target), \
             patch.object(utils, 'notify_keycloak_of_directory_change',
                          return_value=propagated):
            report = utils.propagate_member_change(None, 'coop-1', 'why')
        assert (report['groups_sync'], report['keycloak_sync']) == expected


def test_update_ldap_member_reports_the_propagation_it_triggers():
    """Through the real ``update_ldap_member``: the write, then the group
    synchroniser, then the Keycloak propagation — and their outcome in
    the returned dict."""
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
         patch('alirpunkto.dynamic_groups.sync_member_groups',
               return_value=None) as sync, \
         patch.object(utils, 'notify_keycloak_of_directory_change',
                      return_value=True) as notify:
        body, status, _ = _call(_request({
            'oid': 'coop-1',
            'date_end_validity_yearly_contribution': '2027-06-30'}),
            target=target, ldap=utils.update_ldap_member)
    assert status == 200
    sync.assert_called_once()
    assert sync.call_args.args[1] == 'coop-1'
    notify.assert_called_once()
    assert (body['status'], body['groups_sync'], body['keycloak_sync']) == (
        'partial', 'error', 'success')


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


def _answer(status_code=200, **body):
    answer = MagicMock(status_code=status_code)
    answer.json.return_value = body
    return answer


def _success(oid='coop-1', shares=1, validity='2027-06-30', **extra):
    body = {'status': 'success', 'oid': oid, 'number_shares_owned': shares,
            'date_end_validity_yearly_contribution': validity,
            'financial_update': 'success', 'groups_sync': 'success',
            'keycloak_sync': 'success', 'groups': ['cooperatorsGroup']}
    body.update(extra)
    return body


def test_the_script_posts_to_the_dedicated_endpoint_with_the_csrf_token():
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(**_success())
    script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    url, = session.post.call_args.args
    data = session.post.call_args.kwargs['data']
    assert url.endswith('/update_contribution')
    assert data == {'oid': 'coop-1', 'csrf_token': 'tok',
                    'number_shares_owned': '1',
                    'date_end_validity_yearly_contribution': '2027-06-30'}
    # The CSRF guard's origin check and a bounded wait (audit A4).
    headers = session.post.call_args.kwargs['headers']
    assert headers['Origin'] == 'https://alirpunkto.cosmopolitical.coop'
    assert headers['Referer'].startswith(headers['Origin'])
    assert session.post.call_args.kwargs['timeout'] == script.TIMEOUT


def test_the_script_raises_on_a_refusal_instead_of_printing_a_warning():
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(
        403, status='error', error='administrator_required')
    with pytest.raises(RuntimeError, match='administrator_required'):
        script.modify_member(session, 'coop-1', '1', None, 'tok')


def test_the_script_sends_zero_shares_and_refuses_an_empty_request():
    """Audit A1: ``0`` is a value; no fact at all is an error, never a
    silent exit 0."""
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(**_success(shares=0, validity=None))
    script.modify_member(session, 'coop-1', '0', None, 'tok')
    assert session.post.call_args.kwargs['data']['number_shares_owned'] == '0'
    for shares, validity in ((None, None), ('', ''), ('  ', None)):
        with pytest.raises(ValueError, match='At least one financial fact'):
            script.check_requested_changes(shares, validity)
    session.post.reset_mock()
    with pytest.raises(ValueError):
        script.modify_member(session, 'coop-1', None, None, 'tok')
    session.post.assert_not_called()


def test_the_script_checks_the_member_and_the_values_that_come_back():
    """Audit A3: a 200/success for another member, or with other values,
    is not a confirmation."""
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(**_success(oid='someone-else'))
    with pytest.raises(RuntimeError, match='someone-else'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    session.post.return_value = _answer(**_success(shares=3))
    with pytest.raises(RuntimeError, match='number_shares_owned'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    session.post.return_value = _answer(**_success(validity='2026-06-30'))
    with pytest.raises(RuntimeError,
                       match='date_end_validity_yearly_contribution'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    # Only the facts actually sent are compared.
    session.post.return_value = _answer(**_success(shares=7))
    assert script.modify_member(session, 'coop-1', None, '2027-06-30', 'tok')


def test_the_script_treats_a_partial_answer_as_a_failure_to_retry():
    """Audit A2: facts recorded but rights not restored is exit 1, with
    the two lagging steps named."""
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(**_success(
        status='partial', groups_sync='error', keycloak_sync='success',
        groups=None))
    with pytest.raises(RuntimeError, match='groups_sync=error'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')


def test_the_script_requires_each_of_the_three_steps_to_be_confirmed():
    """Second audit pass (P3): a bare ``success``, or a ``success`` that
    contradicts its own step indicators, is not a confirmation."""
    script = _load_script()
    session = MagicMock()
    session.post.return_value = _answer(status='success', oid='coop-1',
                                        number_shares_owned=1)
    with pytest.raises(RuntimeError, match='financial update'):
        script.modify_member(session, 'coop-1', '1', None, 'tok')
    session.post.return_value = _answer(**_success(groups_sync='error'))
    with pytest.raises(RuntimeError, match='groups_sync'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    session.post.return_value = _answer(**_success(keycloak_sync=None))
    with pytest.raises(RuntimeError, match='keycloak_sync'):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    session.post.return_value = _answer(**_success(groups=None))
    with pytest.raises(RuntimeError, match="member's groups"):
        script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')
    session.post.return_value = _answer(**_success(financial_update='unchanged'))
    assert script.modify_member(session, 'coop-1', '1', '2027-06-30', 'tok')


def test_the_script_refuses_an_absurd_number_of_shares():
    """Second audit pass (P4): a digit string beyond any business
    meaning (or any integer range) is a caller bug, not a payment."""
    script = _load_script()
    with pytest.raises(ValueError, match='must not exceed'):
        script.check_requested_changes('99999999999999999999999999999', None)
    assert script.check_requested_changes(str(script.MAX_SHARES), None) == {
        'number_shares_owned': str(script.MAX_SHARES)}


def test_the_script_refuses_an_implausible_validity_year():
    """Third audit pass: ``0000-01-01`` and its cousins are typos."""
    script = _load_script()
    for bad in ('0000-01-01', '1899-12-31', '2200-01-01', '2027-02-30'):
        with pytest.raises(ValueError):
            script.check_requested_changes(None, bad)
    assert script.check_requested_changes(None, '2027-06-30') == {
        'date_end_validity_yearly_contribution': '2027-06-30'}


def test_the_script_refuses_a_non_json_or_non_object_answer():
    script = _load_script()
    session = MagicMock()
    bad = MagicMock(status_code=200)
    bad.json.side_effect = ValueError
    session.post.return_value = bad
    with pytest.raises(RuntimeError, match='did not answer JSON'):
        script.modify_member(session, 'coop-1', '1', None, 'tok')
    session.post.return_value = MagicMock(
        status_code=200, json=MagicMock(return_value=['not', 'an', 'object']))
    with pytest.raises(RuntimeError, match='not an object'):
        script.modify_member(session, 'coop-1', '1', None, 'tok')


def test_the_script_login_posts_the_login_page_token_with_the_origin():
    """The CSRF guard refuses a bare login POST: the script reads the
    login page first, posts its token with the Origin header, then reads
    the session token from the member directory page."""
    script = _load_script()
    session = MagicMock()
    login_page = MagicMock(status_code=200,
                           text='<input name="csrf_token" value="login-tok" />')
    directory = MagicMock(status_code=200,
                          text='<input name="csrf_token" value="abc123" />')
    session.get.side_effect = [login_page, directory]
    session.post.return_value = MagicMock(status_code=302)
    assert script.login(session, 'admin', 'pw') == 'abc123'
    data = session.post.call_args.kwargs['data']
    assert data['csrf_token'] == 'login-tok'
    assert data['form.submitted'] == 'True'
    assert session.post.call_args.kwargs['headers']['Origin'] == \
        'https://alirpunkto.cosmopolitical.coop'
    assert session.get.call_args_list[0].args[0].endswith('/login')
    assert session.get.call_args_list[1].args[0].endswith('/modify_member')


def test_the_script_login_tells_a_csrf_refusal_from_bad_credentials():
    """Audit A7: a 400 on the login POST is the guard, not the password."""
    script = _load_script()
    session = MagicMock()
    login_page = MagicMock(status_code=200,
                           text='<input name="csrf_token" value="t" />')
    session.get.side_effect = [login_page, MagicMock(text='<html>home</html>')]
    session.post.return_value = MagicMock(status_code=400)
    with pytest.raises(RuntimeError, match='CSRF token or Origin'):
        script.login(session, 'admin', 'pw')
    session.get.side_effect = [login_page, MagicMock(text='<html>home</html>')]
    session.post.return_value = MagicMock(status_code=302)
    with pytest.raises(ValueError, match='invalid credentials'):
        script.login(session, 'admin', 'pw')
    session.get.side_effect = [MagicMock(status_code=404, text='nope')]
    with pytest.raises(RuntimeError, match='no CSRF token'):
        script.login(session, 'admin', 'pw')


def test_the_script_base_url_must_be_the_portal_origin():
    script = _load_script()
    assert script.portal_origin('https://access.example.coop/') == \
        'https://access.example.coop'
    assert script.portal_origin('http://localhost:6543') == \
        'http://localhost:6543'
    for bad in ('https://access.example.coop/alirpunkto', 'access.example.coop',
                'ftp://x', 'https://h/?a=1'):
        with pytest.raises(ValueError):
            script.portal_origin(bad)
