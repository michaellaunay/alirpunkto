"""Transversal audit of 2026-10-24, lot 3 — capabilities and transitions.

A04  The SSO round trip is bound to the browser session: a one-time
     ``state`` and a PKCE verifier are armed at departure, the callback
     refuses a code without the matching, unexpired state, and the
     access token is verified against a fixed algorithm list and the
     realm's issuer.
A05  An e-mailed action link is a capability for one purpose and one
     emission: a reset link is consumed by the password change, the
     armed reset session dies with a newer request, an address-change
     or resignation link of another purpose is refused.
A08  The external write comes first: a directory refusal leaves the
     resignation pending and the address change retryable, never a
     local state that pretends the write happened.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.httpexceptions import HTTPFound
from pyramid.testing import DummyRequest, setUp, tearDown
from webob.multidict import MultiDict

import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import MEMBER_OID, _
from alirpunkto.models.member import (
    EmailSendStatus, Member, MemberDatas, MemberStates, MemberTypes,
)
from alirpunkto.views import check_new_email as cne
from alirpunkto.views import forgot_password as fp
from alirpunkto.views import sso_login as sso
from alirpunkto.views import unsubscribe as unsub


# ================================ A04 ====================================== #
@pytest.fixture
def routes():
    config = setUp()
    config.add_route('home', '/')
    config.add_route('sso_login', '/sso_login')
    config.add_route(sso.KEYCLOAK_REDIRECT_PATH, f'/{sso.KEYCLOAK_REDIRECT_PATH}')
    yield config
    tearDown()


def _openid(auth_url='https://kc.test/auth?x=1'):
    client = MagicMock()
    client.auth_url.return_value = auth_url
    client.token.return_value = {'access_token': 'at', 'refresh_token': 'rt',
                                 'refresh_expires_in': 1800}
    client.public_key.return_value = 'PUBKEY'
    return client


def test_the_departure_arms_a_state_and_a_pkce_challenge(routes):
    request = DummyRequest()
    request.session = {}
    client = _openid()
    with patch.object(sso, 'KeycloakOpenID', return_value=client), \
         patch.object(sso, 'get_secret', lambda *_: 's'):
        response = sso.sso_login_view(request)
    assert isinstance(response, HTTPFound)
    kwargs = client.auth_url.call_args.kwargs
    state = request.session[sso.SSO_STATE]
    assert kwargs['state'] == state and len(state) >= 32
    verifier = request.session[sso.SSO_VERIFIER]
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    assert kwargs['code_challenge'] == expected
    assert kwargs['code_challenge_method'] == 'S256'
    assert sso.SSO_STARTED_AT in request.session
    # Two departures, two states: never reused.
    with patch.object(sso, 'KeycloakOpenID', return_value=client), \
         patch.object(sso, 'get_secret', lambda *_: 's'):
        sso.sso_login_view(request)
    assert request.session[sso.SSO_STATE] != state


def _callback(session, params, client=None, member=None):
    request = DummyRequest(params=params)
    request.session = session
    client = client or _openid()
    member = member or SimpleNamespace(
        oid='m-1', pseudonym='p', email='e@x', type=MemberTypes.COOPERATOR,
        member_state=MemberStates.REGISTRED,
        data=SimpleNamespace(is_active=True, lang1='en'))
    with patch.object(sso, 'KeycloakOpenID', return_value=client), \
         patch.object(sso, 'get_secret', lambda *_: 'client-id'), \
         patch.object(sso.jwt, 'decode',
                      return_value={'employeeNumber': 'm-1'}) as decode, \
         patch.object(sso, 'update_member_from_ldap', return_value=member), \
         patch.object(sso, 'store_sso_tokens'), \
         patch.object(sso, 'remember', return_value=[]), \
         patch.object(sso, 'logout', lambda r: r.session.pop('user', None)):
        response = sso.callback_view(request)
    return response, request, client, decode


def _armed(age_seconds=0):
    return {sso.SSO_STATE: 'good-state', sso.SSO_VERIFIER: 'the-verifier',
            sso.SSO_STARTED_AT: (datetime.now()
                                 - timedelta(seconds=age_seconds)).isoformat()}


def test_a_callback_without_an_armed_departure_exchanges_nothing(routes):
    response, request, client, _d = _callback({}, {'code': 'c', 'state': 'x'})
    assert isinstance(response, HTTPFound) and response.location == '/'
    client.token.assert_not_called()
    assert request.session.get('logged_in') is not True


@pytest.mark.parametrize("params", [
    {'code': 'c'},                                  # no state at all
    {'code': 'c', 'state': 'other-browser'},        # another session's state
    {'state': 'good-state'},                        # no code
])
def test_a_callback_with_a_missing_or_foreign_state_is_refused(routes, params):
    response, request, client, _d = _callback(_armed(), params)
    assert isinstance(response, HTTPFound) and response.location == '/'
    client.token.assert_not_called()
    assert sso.SSO_STATE not in request.session       # consumed anyway


def test_a_stale_departure_is_refused(routes):
    response, request, client, _d = _callback(
        _armed(age_seconds=sso.SSO_STATE_TTL_SECONDS + 1),
        {'code': 'c', 'state': 'good-state'})
    client.token.assert_not_called()


def test_a_matching_state_is_single_use_and_carries_the_verifier(routes):
    session = _armed()
    response, request, client, decode = _callback(
        session, {'code': 'c', 'state': 'good-state'})
    client.token.assert_called_once()
    assert client.token.call_args.kwargs['code_verifier'] == 'the-verifier'
    assert client.token.call_args.kwargs['code'] == 'c'
    assert request.session['logged_in'] is True
    assert sso.SSO_STATE not in request.session
    # Replay of the same callback: the state is gone.
    response2, request2, client2, _d = _callback(
        request.session, {'code': 'c', 'state': 'good-state'})
    client2.token.assert_not_called()


def test_the_token_is_verified_against_fixed_algorithms_and_the_issuer(routes):
    with patch.object(sso, 'KEYCLOAK_SERVER_URL', 'https://kc.test/'), \
         patch.object(sso, 'KEYCLOAK_REALM', 'coop'):
        _r, _q, _c, decode = _callback(_armed(),
                                       {'code': 'c', 'state': 'good-state'})
    kwargs = decode.call_args.kwargs
    assert kwargs['algorithms'] == list(sso.JWT_ALGORITHMS)
    assert 'RS256' in kwargs['algorithms'] and 'none' not in kwargs['algorithms']
    assert kwargs['issuer'] == 'https://kc.test/realms/coop'
    assert kwargs['audience'] == ['client-id', 'account']


def test_the_header_algorithm_is_never_read():
    source = open(sso.__file__, encoding='utf-8').read()
    assert 'get_unverified_header' not in source
    assert "algorithms=[algo]" not in source


# ================================ A05 ====================================== #
def _reset_member():
    member = Member(data=MemberDatas(password='x', lang1='en'), oid='oid-1',
                    member_state=MemberStates.REGISTRED,
                    type=MemberTypes.COOPERATOR, email='m@example.org',
                    pseudonym='jdoe')
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION,
                                 'forgot_password')
    member.add_email_send_status(EmailSendStatus.SENT, 'reset_password_email')
    member.member_state = MemberStates.DATA_MODIFICATION_REQUESTED
    return member


def _reset_request(pairs, session):
    params = MultiDict()
    for key, value in pairs:
        params.add(key, value)
    return SimpleNamespace(
        POST=params, params=params, method='POST',
        url='http://example/forgot_password', tm=MagicMock(), session=session,
        registry=SimpleNamespace(settings={'site_name': 'S',
                                           'session.secret': 'x' * 32}))


def test_opening_the_reset_link_binds_the_session_to_its_seed():
    member = _reset_member()
    seed = member.email_send_status_history[-1].seed
    request = SimpleNamespace(
        params={'oid': 'enc'}, session={},
        registry=SimpleNamespace(settings={'session.secret': 'x' * 32}))
    with patch.object(fp, 'decrypt_oid', return_value=('oid-1', seed)), \
         patch.object(fp, 'get_member_by_oid', return_value=member):
        loaded, error = fp._retrieve_member(request)
    assert loaded is member and error is None
    assert request.session[fp.RESET_LINK_SEED] == seed


def test_a_link_of_another_purpose_does_not_open_the_reset_form():
    """Same member, valid seed, but the last emission was an address
    change: the reset form must not open on it."""
    member = _reset_member()
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, 'check_new_email')
    seed = member.email_send_status_history[-1].seed
    request = SimpleNamespace(
        params={'oid': 'enc'}, session={},
        registry=SimpleNamespace(settings={'session.secret': 'x' * 32}))
    with patch.object(fp, 'decrypt_oid', return_value=('oid-1', seed)), \
         patch.object(fp, 'get_member_by_oid', return_value=member):
        loaded, error = fp._retrieve_member(request)
    assert loaded is None and error['url_obsolete'] is True
    assert fp.RESET_LINK_SEED not in request.session


def test_the_password_change_consumes_the_link_and_disarms_the_session():
    member = _reset_member()
    seed = member.email_send_status_history[-1].seed
    session = {MEMBER_OID: 'oid-1', fp.RESET_LINK_SEED: seed}
    request = _reset_request(
        [('modify', '1'), ('password', 'ValidPass123@'),
         ('password_confirm', 'ValidPass123@')], session)
    with patch.object(fp, '_retrieve_member', return_value=(None, None)), \
         patch.object(fp, '_display_in_member_language'), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(fp, 'update_member_password',
                      return_value={'status': 'success'}) as change, \
         patch.object(fp, 'send_member_state_change_email',
                      return_value={'success': True}):
        result = fp.forgot_password(request)
    assert result['message'] == _('password_changed')
    change.assert_called_once()
    assert MEMBER_OID not in session and fp.RESET_LINK_SEED not in session
    # The link's seed is no longer the member's current one.
    assert member.email_send_status_history[-1].seed != seed
    assert not utils.link_matches_pending_action(member, seed, fp.RESET_PURPOSES)
    # Second POST with a copy of the armed cookie: refused, no change.
    session2 = {MEMBER_OID: 'oid-1', fp.RESET_LINK_SEED: seed}
    request2 = _reset_request(
        [('modify', '1'), ('password', 'Other1234@'),
         ('password_confirm', 'Other1234@')], session2)
    with patch.object(fp, '_retrieve_member', return_value=(None, None)), \
         patch.object(fp, '_display_in_member_language'), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(fp, 'update_member_password') as change2:
        result2 = fp.forgot_password(request2)
    change2.assert_not_called()
    assert result2.get('url_obsolete') is True
    assert MEMBER_OID not in session2


def test_a_newer_reset_request_kills_the_older_armed_session():
    member = _reset_member()
    old_seed = member.email_send_status_history[-1].seed
    # A second request mints a new link.
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, 'forgot_password')
    session = {MEMBER_OID: 'oid-1', fp.RESET_LINK_SEED: old_seed}
    request = _reset_request(
        [('modify', '1'), ('password', 'ValidPass123@'),
         ('password_confirm', 'ValidPass123@')], session)
    with patch.object(fp, '_retrieve_member', return_value=(None, None)), \
         patch.object(fp, '_display_in_member_language'), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(fp, 'update_member_password') as change:
        result = fp.forgot_password(request)
    change.assert_not_called()
    assert result.get('url_obsolete') is True


def test_an_address_change_link_must_match_its_own_emission():
    member = Member(oid='member-1')
    member.email = 'old@example.com'
    member.new_email = 'new@example.com'
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, 'check_new_email')
    current = member.email_send_status_history[-1].seed
    request = SimpleNamespace(
        params={'oid': 'enc'}, session={}, method='GET',
        url='http://example/check_new_email', tm=MagicMock(),
        registry=SimpleNamespace(settings={'session.secret': 'x'}))
    # A stale seed (an older emission) is refused, nothing written.
    with patch.object(cne, 'decrypt_oid', return_value=('member-1', 'older')), \
         patch.object(cne, 'get_member_by_oid', return_value=member), \
         patch.object(cne, 'update_ldap_member') as ldap:
        result = cne.check_new_email(request)
    assert result['error'] == _('invalid_oid')
    ldap.assert_not_called()
    assert member.email == 'old@example.com'
    # The current seed goes through, and is then consumed.
    with patch.object(cne, 'decrypt_oid', return_value=('member-1', current)), \
         patch.object(cne, 'get_member_by_oid', return_value=member), \
         patch.object(cne, 'update_ldap_member',
                      return_value={'status': 'success'}):
        result = cne.check_new_email(request)
    assert result['success'] == _('email_updated')
    assert member.email == 'new@example.com'
    assert member.email_send_status_history[-1].seed != current


def test_a_resignation_link_of_another_purpose_is_refused(routes):
    from tests.test_unsubscribe import _member
    member = _member(MemberStates.PENDING_UNSUBSCRIPTION)
    member.previous_member_state = MemberStates.REGISTRED
    member.unsubscription_requested_at = datetime.now()
    member.email_send_status_history = [
        SimpleNamespace(seed='seed', function_name='forgot_password')]
    request = DummyRequest(params={'oid': 'encrypted'})
    request.session = {'logged_in': True}
    request.registry = SimpleNamespace(settings={'session.secret': 'x' * 32})
    with patch.object(unsub, 'decrypt_oid', return_value=('member-1', 'seed')), \
         patch.object(unsub, 'get_member_by_oid', return_value=member), \
         patch.object(unsub, 'deactivate_member_in_ldap') as ldap, \
         patch.object(unsub, '_context', lambda request, **kw: kw):
        result = unsub.unsubscribe_confirm(request)
    ldap.assert_not_called()
    assert member.member_state == MemberStates.PENDING_UNSUBSCRIPTION
    assert result['error'] == _('invalid_oid')


def test_the_resignation_request_mints_its_own_link_seed(routes):
    """The e-mail helper reads the last event's seed: the request must
    record a fresh one under its own purpose first."""
    member = Member(data=MemberDatas(password='x', lang1='en'), oid='member-1',
                    member_state=MemberStates.REGISTRED,
                    type=MemberTypes.ORDINARY, email='m@example.org',
                    pseudonym='jdoe')
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, 'forgot_password')
    stale = member.email_send_status_history[-1].seed
    request = DummyRequest(post={'confirm': '1', 'csrf_token': 't'})
    request.session = {'logged_in': True, 'user': {'oid': 'member-1'}}
    request.POST = request.params = {'confirm': '1', 'csrf_token': 't'}
    with patch.object(unsub, 'get_member_by_oid', return_value=member), \
         patch.object(unsub, 'send_email_to_member',
                      return_value={'success': True}) as sender, \
         patch.object(unsub, '_context', lambda request, **kw: kw), \
         patch.object(unsub, '_show_quarantine', return_value=False):
        unsub.unsubscribe(request)
    sender.assert_called_once()
    last = member.email_send_status_history[-1]
    assert last.function_name == 'unsubscribe' and last.seed != stale
    assert utils.link_matches_pending_action(member, last.seed, ('unsubscribe',))
    assert not utils.link_matches_pending_action(member, stale, ('unsubscribe',))


# ================================ A08 ====================================== #
def test_a_directory_refusal_leaves_the_resignation_pending(routes):
    from tests.test_unsubscribe import _member
    member = _member(MemberStates.PENDING_UNSUBSCRIPTION)
    member.previous_member_state = MemberStates.REGISTRED
    member.unsubscription_requested_at = datetime.now()
    request = DummyRequest(params={'oid': 'encrypted'})
    request.session = {'logged_in': True, 'user': {'oid': 'member-1'}}
    request.registry = SimpleNamespace(settings={'session.secret': 'x' * 32})
    with patch.object(unsub, 'decrypt_oid', return_value=('member-1', 'seed')), \
         patch.object(unsub, 'get_member_by_oid', return_value=member), \
         patch.object(unsub, 'deactivate_member_in_ldap',
                      return_value={'status': 'error', 'message': 'ldap down'}), \
         patch.object(unsub, 'send_email_to_member') as sender, \
         patch.object(unsub, '_context', lambda request, **kw: kw):
        result = unsub.unsubscribe_confirm(request)
    assert result['error'] == 'ldap down'
    assert member.member_state == MemberStates.PENDING_UNSUBSCRIPTION
    assert member.data.is_active is True
    assert member.data.date_erasure_all_data is None
    assert getattr(member, 'departure_date', None) is None
    sender.assert_not_called()
    assert request.session.get('user')                 # session not ended
    # The same link, once the directory answers: it goes through.
    with patch.object(unsub, 'decrypt_oid', return_value=('member-1', 'seed')), \
         patch.object(unsub, 'get_member_by_oid', return_value=member), \
         patch.object(unsub, 'deactivate_member_in_ldap',
                      return_value={'status': 'success'}), \
         patch.object(unsub, 'send_email_to_member',
                      return_value={'success': True}), \
         patch.object(unsub, '_context', lambda request, **kw: kw):
        result = unsub.unsubscribe_confirm(request)
    assert member.member_state == MemberStates.UNSUBSCRIBED
    assert member.data.is_active is False


def test_the_directory_write_precedes_the_local_resignation():
    source = open(unsub.__file__, encoding='utf-8').read()
    body = source.split('def unsubscribe_confirm', 1)[1]
    assert body.index('deactivate_member_in_ldap(request, member, erasure_due)') \
        < body.index('member.member_state = MemberStates.UNSUBSCRIBED')


def test_a_refused_address_write_keeps_the_old_address_and_the_request():
    member = Member(oid='member-1')
    member.email = 'old@example.com'
    member.new_email = 'new@example.com'
    member.add_email_send_status(EmailSendStatus.IN_PREPARATION, 'check_new_email')
    seed = member.email_send_status_history[-1].seed
    request = SimpleNamespace(
        params={'oid': 'enc'}, session={}, method='GET',
        url='http://example/check_new_email', tm=MagicMock(),
        registry=SimpleNamespace(settings={'session.secret': 'x'}))
    with patch.object(cne, 'decrypt_oid', return_value=('member-1', seed)), \
         patch.object(cne, 'get_member_by_oid', return_value=member), \
         patch.object(cne, 'update_ldap_member',
                      return_value={'status': 'error'}) as ldap:
        result = cne.check_new_email(request)
    assert result['error'] == _('email_update_error')
    # The directory was asked with the NEW address, then the old one
    # came back and the request is still pending, link still valid.
    assert ldap.call_args.args[1].email == 'old@example.com'
    assert member.email == 'old@example.com'
    assert member.new_email == 'new@example.com'
    assert member.member_state != MemberStates.DATA_MODIFIED
    assert utils.link_matches_pending_action(member, seed, ('check_new_email',))
