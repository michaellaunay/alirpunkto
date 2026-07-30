"""Member resignation (specification "Démissionner").

The flow of the spec: profile → implications page → pending state + e-mailed
confirmation link → link followed → account deactivated in LDAP (kept during
the Quarantine period, erasure date recorded), farewell e-mail, session
ended. Alternative scenarios: cancellation, and lazy expiry of a stale
request. The deferred purge — everything deleted except the pseudonym, the
departure date and the reason — is a utility meant for a periodic caller.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import _, QUARANTINE_PERIOD_DAYS
from alirpunkto.models.member import MemberDatas, MemberStates
from alirpunkto.views import unsubscribe as unsub_module
from alirpunkto.views.unsubscribe import (
    unsubscribe, unsubscribe_cancel, unsubscribe_confirm)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


def _member(state=MemberStates.REGISTRED):
    return SimpleNamespace(
        oid='member-1', email='m@example.com', pseudonym='jdoe',
        member_state=state, previous_member_state=None,
        unsubscription_requested_at=None,
        data=SimpleNamespace(is_active=True, date_erasure_all_data=None))


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'modify_member', 'unsubscribe',
                  'unsubscribe_cancel', 'unsubscribe_confirm'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, params=None, logged_in=True):
    request = DummyRequest(post=post or {}, params=params or post or {})
    request.session = _Session()
    request.session['logged_in'] = logged_in
    if logged_in:
        request.session['user'] = {'oid': 'member-1', 'name': 'jdoe'}
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def test_the_request_opens_pending_and_mails_the_link(config):
    member = _member()
    request = _request(config, post={'confirm': '1',
                                     'csrf_token': 'csrf-token'})
    with patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member), \
         patch.object(unsub_module, 'send_email_to_member',
                      return_value={'success': True}) as sender:
        result = unsubscribe(request)

    assert member.member_state == MemberStates.PENDING_UNSUBSCRIPTION
    assert member.previous_member_state == MemberStates.REGISTRED
    assert member.unsubscription_requested_at is not None
    assert result['pending'] is True and result['success']
    args = sender.call_args[0]
    assert args[3] == 'unsubscribe_confirmation_email'
    assert args[5] == 'unsubscribe_confirm'


def test_a_failed_email_rolls_the_state_back(config):
    member = _member()
    request = _request(config, post={'confirm': '1',
                                     'csrf_token': 'csrf-token'})
    with patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member), \
         patch.object(unsub_module, 'send_email_to_member',
                      return_value={'error': 'boom'}):
        result = unsubscribe(request)

    assert member.member_state == MemberStates.REGISTRED
    assert member.previous_member_state is None
    assert result['error'] == _('email_not_sent')


def test_the_link_confirms_the_resignation(config):
    member = _member(MemberStates.PENDING_UNSUBSCRIPTION)
    member.previous_member_state = MemberStates.REGISTRED
    member.unsubscription_requested_at = datetime.now()
    request = _request(config, params={'oid': 'encrypted'})
    with patch.object(unsub_module, 'decrypt_oid',
                      return_value=('member-1', 'seed')), \
         patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member), \
         patch.object(unsub_module, 'deactivate_member_in_ldap',
                      return_value={'status': 'success'}) as ldap, \
         patch.object(unsub_module, 'send_email_to_member',
                      return_value={'success': True}) as sender:
        result = unsubscribe_confirm(request)

    assert member.member_state == MemberStates.UNSUBSCRIBED
    assert member.departure_reason == 'resignation'
    expected_due = (member.departure_date
                    + timedelta(days=QUARANTINE_PERIOD_DAYS)).date()
    assert member.data.date_erasure_all_data == expected_due
    assert member.data.is_active is False
    ldap.assert_called_once()
    assert sender.call_args[0][3] == 'unsubscribed_email'
    assert 'user' not in request.session          # session ended
    assert result['success'] == _('Your account is deactivated.')


def test_a_stale_link_expires_and_restores_the_state(config):
    member = _member(MemberStates.PENDING_UNSUBSCRIPTION)
    member.previous_member_state = MemberStates.REGISTRED
    member.unsubscription_requested_at = datetime.now() - timedelta(days=8)
    request = _request(config, params={'oid': 'encrypted'})
    with patch.object(unsub_module, 'decrypt_oid',
                      return_value=('member-1', 'seed')), \
         patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member), \
         patch.object(unsub_module, 'deactivate_member_in_ldap') as ldap:
        result = unsubscribe_confirm(request)

    assert member.member_state == MemberStates.REGISTRED
    ldap.assert_not_called()
    assert 'expired' in result['error'].lower()


def test_cancelling_restores_the_previous_state(config):
    member = _member(MemberStates.PENDING_UNSUBSCRIPTION)
    member.previous_member_state = MemberStates.DATA_MODIFIED
    member.unsubscription_requested_at = datetime.now()
    request = _request(config, post={'cancel': '1',
                                     'csrf_token': 'csrf-token'})
    with patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member):
        result = unsubscribe_cancel(request)

    assert isinstance(result, HTTPFound)
    assert member.member_state == MemberStates.DATA_MODIFIED
    assert member.previous_member_state is None


def test_an_already_unsubscribed_link_is_idempotent(config):
    member = _member(MemberStates.UNSUBSCRIBED)
    request = _request(config, params={'oid': 'encrypted'})
    with patch.object(unsub_module, 'decrypt_oid',
                      return_value=('member-1', 'seed')), \
         patch.object(unsub_module, 'get_member_by_oid',
                      return_value=member), \
         patch.object(unsub_module, 'deactivate_member_in_ldap') as ldap, \
         patch.object(unsub_module, 'send_email_to_member') as sender:
        result = unsubscribe_confirm(request)

    ldap.assert_not_called()
    sender.assert_not_called()
    assert result['success'] == _('Your account is deactivated.')


# ------------------------------- LDAP layer -------------------------------- #
def _mock_ldap_entry(member_oid='member-1'):
    from ldap3 import Connection, Server, MOCK_SYNC, ALL
    from alirpunkto.constants_and_globals import LDAP_BASE_DN, LDAP_OU
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")
    conn.add(dn, attributes={
        'objectClass': ['top', 'inetOrgPerson'],
        'uid': member_oid, 'cn': 'jdoe', 'sn': 'jdoe',
        'employeeType': 'ORDINARY', 'isActive': 'True'})
    return conn, dn


def test_deactivation_keeps_the_entry_but_turns_it_inactive(config):
    conn, dn = _mock_ldap_entry()
    member = _member()
    due = datetime.now() + timedelta(days=QUARANTINE_PERIOD_DAYS)
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = utils.deactivate_member_in_ldap(
            SimpleNamespace(), member, due)

    assert result['status'] == 'success'
    conn.search(dn, '(objectclass=*)',
                attributes=['isActive', 'dateErasureAllData', 'cn'])
    entry = conn.entries[0]
    assert str(entry.isActive) == 'False'
    assert str(entry.cn) == 'jdoe'                 # entry kept: quarantine
    assert str(entry.dateErasureAllData)           # due date recorded


def test_the_purge_deletes_everything_but_the_three_retained_facts(config):
    conn, dn = _mock_ldap_entry()
    gone = _member(MemberStates.UNSUBSCRIBED)
    gone.data = MemberDatas(password='', fullname='Jean', fullsurname='Doe',
                            nationality='FR')
    gone.data.date_erasure_all_data = date.today() - timedelta(days=1)
    gone.departure_date = datetime.now() - timedelta(
        days=QUARANTINE_PERIOD_DAYS + 1)
    gone.departure_reason = 'resignation'
    staying = _member(MemberStates.UNSUBSCRIBED)
    staying.oid = 'member-2'
    staying.data = MemberDatas(password='', fullname='Anne')
    staying.data.date_erasure_all_data = date.today() + timedelta(days=30)

    members = {'member-1': gone, 'member-2': staying}
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_members', return_value=members):
        purged = utils.purge_unsubscribed_members(SimpleNamespace())

    assert purged == ['member-1']
    assert gone.member_state == MemberStates.DELETED
    assert gone.pseudonym == 'jdoe'                # retained
    assert gone.departure_reason == 'resignation'  # retained
    assert gone.data.fullname is None              # personal data gone
    conn.search(dn, '(objectclass=*)', attributes=['cn'])
    assert not conn.entries                        # LDAP entry deleted
    assert staying.data.fullname == 'Anne'         # quarantine not over


# --------------------------- structural anchors ---------------------------- #
def test_the_login_guard_sits_between_ldap_and_user_creation():
    src = open(os.path.join(ROOT, 'alirpunkto', 'views', 'sso_login.py'),
               encoding='utf-8').read()
    i_update = src.index('update_member_from_ldap(oid, request)')
    i_guard = src.index('if not member.data.is_active:')
    i_user = src.index('user = User(')
    assert i_update < i_guard < i_user


def test_the_profile_page_links_to_the_resignation_flow():
    tpl = open(os.path.join(ROOT, 'alirpunkto', 'templates',
                            'modify_member.pt'), encoding='utf-8').read()
    m = re.search(r'deactivate-account.*?route_url\(\'unsubscribe\'\)',
                  tpl, re.S)
    assert m
    assert "getattr(member, 'oid', None) == getattr(accessed_member, 'oid', None)" in tpl
