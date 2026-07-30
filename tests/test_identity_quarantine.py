"""The erasure date field and the Quarantine-aware identity check (issue #54).

The dateErasureAllData field the ticket asks for already exists and the
resignation flow fills it; what was missing: the 180-day statutory default
(§3.4), the identity-uniqueness check of Applicants against every LDAP
entry — resigned or excluded Cooperators in Quarantine included, so nobody
re-registers with a virgin reputation — and the message telling the former
member their identity data was indeed erased once the purge ran.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import (
    _, LDAP_BASE_DN, LDAP_OU, LDAP_TIME_FORMAT, QUARANTINE_PERIOD_DAYS)
from alirpunkto.models.member import MemberDatas, MemberStates
from alirpunkto.utils import is_valid_unique_identity


def test_the_quarantine_default_matches_the_statutes():
    """§3.4 of the statutes: 180 days by default."""
    import os
    if 'QUARANTINE_PERIOD_DAYS' not in os.environ:
        assert QUARANTINE_PERIOD_DAYS == 180


def _directory_with(*entries):
    from ldap3 import Connection, Server, MOCK_SYNC, ALL
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    for oid, gn, sn, birth, active in entries:
        dn = (f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}"
              if LDAP_OU else f"uid={oid},{LDAP_BASE_DN}")
        conn.add(dn, attributes={
            'objectClass': ['top', 'inetOrgPerson'],
            'uid': oid, 'cn': f'p-{oid}', 'sn': sn, 'gn': gn,
            'birthdate': datetime(birth.year, birth.month,
                                  birth.day).strftime(LDAP_TIME_FORMAT),
            'isActive': active, 'employeeType': 'COOPERATOR'})
    return conn


BIRTH = date(1990, 5, 17)


def test_an_identity_held_by_an_active_member_is_rejected():
    conn = _directory_with(('m1', 'Jean', 'Doe', BIRTH, 'True'))
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = is_valid_unique_identity('Jean', 'Doe', BIRTH)
    assert result and 'error' in result


def test_an_identity_in_quarantine_is_rejected_too():
    """The heart of the ticket: the resigned Cooperator's entry is inactive
    but kept — the same identity cannot register again."""
    conn = _directory_with(('gone', 'Jean', 'Doe', BIRTH, 'False'))
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = is_valid_unique_identity('Jean', 'Doe', BIRTH)
    assert result and 'error' in result


def test_a_free_identity_passes():
    conn = _directory_with(('m1', 'Jean', 'Doe', BIRTH, 'True'))
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        assert is_valid_unique_identity('Anne', 'Doe', BIRTH) is None
        assert is_valid_unique_identity(
            'Jean', 'Doe', date(1991, 1, 1)) is None


def test_after_the_purge_the_identity_is_free_again():
    conn = _directory_with(('gone', 'Jean', 'Doe', BIRTH, 'False'))
    dn = (f"uid=gone,{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid=gone,{LDAP_BASE_DN}")
    conn.delete(dn)
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        assert is_valid_unique_identity('Jean', 'Doe', BIRTH) is None


def test_string_birthdates_are_accepted():
    conn = _directory_with(('m1', 'Jean', 'Doe', BIRTH, 'True'))
    with patch.object(utils, 'get_ldap_connection', return_value=conn):
        result = is_valid_unique_identity('Jean', 'Doe', '1990-05-17')
    assert result and 'error' in result


# --------------------------- the erasure message --------------------------- #
def _unsubscribed(oid, email, due_delta_days):
    member = SimpleNamespace(
        oid=oid, email=email, pseudonym=f'p-{oid}',
        member_state=MemberStates.UNSUBSCRIBED,
        departure_date=datetime.now(), departure_reason='resignation',
        data=MemberDatas(password='', fullname='Jean', lang1='fr'))
    member.data.date_erasure_all_data = (
        date.today() + timedelta(days=due_delta_days))
    return member


def test_the_purge_tells_the_member_their_data_was_erased():
    from ldap3 import Connection, Server, MOCK_SYNC
    conn = Connection(Server('mock'), client_strategy=MOCK_SYNC)
    conn.bind()
    member = _unsubscribed('gone', 'bye@example.com', -1)
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_members',
                      return_value={'gone': member}), \
         patch.object(utils, 'send_email', return_value=True) as sender, \
         patch.object(utils, '_translate_for_language',
                      return_value='subject'):
        purged = utils.purge_unsubscribed_members(SimpleNamespace())

    assert purged == ['gone']
    sender.assert_called_once()
    args = sender.call_args[0]
    assert args[2] == ['bye@example.com']            # captured before erasure
    assert 'erasure_confirmation_email' in args[3]
    assert '/fr/' in args[3]                          # the member's language
    assert sender.call_args[0][4]['pseudonym'] == 'p-gone'
    assert member.email is None                       # address erased after


def test_no_message_when_the_quarantine_is_not_over():
    member = _unsubscribed('staying', 'still@example.com', +30)
    with patch.object(utils, 'get_members',
                      return_value={'staying': member}), \
         patch.object(utils, 'send_email') as sender:
        purged = utils.purge_unsubscribed_members(SimpleNamespace())
    assert purged == []
    sender.assert_not_called()
    assert member.email == 'still@example.com'
