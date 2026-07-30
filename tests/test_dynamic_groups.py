"""Transitions between the Dynamic Groups (issue #148).

The ticket's event algebra reduces to one pure truth table over four facts
— shares owned, yearly-contribution validity, sanction, Board/MAC role —
with the groups as persistent state. These tests lock the table case by
case against the ticket, then the LDAP synchroniser and the daily scan on
a mock directory, and finally the four event sources that call it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import alirpunkto.dynamic_groups as dg
import alirpunkto.utils as utils
from alirpunkto.dynamic_groups import (
    BOARD, COMMUNITY, COOPERATORS, LEGACY_ORDINARY, MAC, MANAGED_GROUPS,
    MISSING_SHARE, MISSING_SHARE_YEAR, MISSING_YEAR, SANCTIONED,
    SANCTIONED_MISSING_YEAR, SUSPENDED_BOARD, SUSPENDED_MAC,
    compute_target_groups, daily_group_scan, group_dn, member_dn,
    sync_member_groups)
from alirpunkto.models.member import MemberTypes

TODAY = date(2026, 7, 30)
VALID = TODAY + timedelta(days=100)
EXPIRED = TODAY - timedelta(days=1)

O, C = MemberTypes.ORDINARY, MemberTypes.COOPERATOR

TRUTH_TABLE = [
    # (id, type, active, shares, contrib_end, current, forced, expected)
    ("ordinary", O, True, 0, None, set(), None, {COMMUNITY}),
    ("registration_as_cooperator", C, True, 0, None, set(), None,
     {COMMUNITY, MISSING_SHARE_YEAR}),
    ("shares_acquired", C, True, 2, None, set(), None,
     {COMMUNITY, MISSING_YEAR}),
    ("contribution_paid_first", C, True, 0, VALID, set(), None,
     {COMMUNITY, MISSING_SHARE}),
    ("full_cooperator", C, True, 2, VALID, set(), None,
     {COMMUNITY, COOPERATORS}),
    ("contribution_expires", C, True, 2, EXPIRED, {COOPERATORS}, None,
     {COMMUNITY, MISSING_YEAR}),
    ("sanction_applied", C, True, 2, VALID, {COOPERATORS}, True,
     {COMMUNITY, SANCTIONED}),
    ("sanctioned_contribution_expires", C, True, 2, EXPIRED,
     {SANCTIONED}, None, {COMMUNITY, SANCTIONED_MISSING_YEAR}),
    ("sanction_lifted_missing_year", C, True, 2, EXPIRED,
     {SANCTIONED_MISSING_YEAR}, False, {COMMUNITY, MISSING_YEAR}),
    ("board_member", C, True, 2, VALID, {BOARD}, None,
     {COMMUNITY, COOPERATORS, BOARD}),
    ("board_contribution_expires", C, True, 2, EXPIRED,
     {BOARD, COOPERATORS}, None,
     {COMMUNITY, MISSING_YEAR, SUSPENDED_BOARD}),
    ("board_sanctioned", C, True, 2, VALID, {BOARD, COOPERATORS}, True,
     {COMMUNITY, SANCTIONED, SUSPENDED_BOARD}),
    ("suspended_board_recovers", C, True, 2, VALID,
     {SUSPENDED_BOARD, MISSING_YEAR}, None,
     {COMMUNITY, COOPERATORS, BOARD}),
    ("mac_sanctioned", C, True, 2, VALID, {MAC, COOPERATORS}, True,
     {COMMUNITY, SANCTIONED, SUSPENDED_MAC}),
    ("resigned", C, False, 2, VALID, {COOPERATORS}, None, set()),
]


@pytest.mark.parametrize(
    "case, mtype, active, shares, end, current, forced, expected",
    TRUTH_TABLE, ids=[row[0] for row in TRUTH_TABLE])
def test_the_truth_table_matches_the_ticket(
        case, mtype, active, shares, end, current, forced, expected):
    assert compute_target_groups(
        mtype, active, shares, end, current, TODAY,
        force_sanctioned=forced) == expected


def test_out_of_scope_types_are_untouched():
    assert compute_target_groups(
        MemberTypes.ADMINISTRATOR, True, 0, None, set(), TODAY) is None
    assert compute_target_groups(
        MemberTypes.PROVIDER, True, 0, None, set(), TODAY) is None


# ------------------------------ mock directory ----------------------------- #
def _directory():
    from ldap3 import Connection, Server, MOCK_SYNC, ALL
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    for name in MANAGED_GROUPS + ('providersGroup',):
        conn.add(group_dn(name), attributes={
            'objectClass': ['top', 'groupOfUniqueNames'],
            'cn': name, 'uniqueMember': ['cn=placeholder']})
    return conn


def _add_member(conn, oid, *, mtype='COOPERATOR', active='True',
                shares=0, end=None, groups=()):
    dn = member_dn(oid)
    attrs = {
        'objectClass': ['top', 'inetOrgPerson'],
        'uid': oid, 'cn': f'user-{oid}', 'sn': f'user-{oid}',
        'employeeType': mtype, 'isActive': active,
        'numberSharesOwned': str(shares),
    }
    if end is not None:
        attrs['dateEndValidityYearlyContribution'] = \
            datetime(end.year, end.month, end.day).strftime(
                '%Y-%m-%dT%H:%M:%S')
    if groups:
        attrs['uniqueMemberOf'] = [group_dn(g) for g in groups]
    conn.add(dn, attributes=attrs)
    for g in groups:
        conn.modify(group_dn(g), {'uniqueMember': [('MODIFY_ADD', [dn])]}) \
            if False else conn.modify(
                group_dn(g),
                {'uniqueMember': [(__import__('ldap3').MODIFY_ADD, [dn])]})
    return dn


def _groups_of(conn, oid):
    conn.search(member_dn(oid), '(objectclass=*)',
                attributes=['uniqueMemberOf'])
    entry = conn.entries[0]
    return dg._names_from_dns(
        entry.uniqueMemberOf.values if 'uniqueMemberOf' in entry else ())


def _group_has(conn, name, oid):
    conn.search(group_dn(name), '(objectclass=*)',
                attributes=['uniqueMember'])
    return member_dn(oid) in [
        str(v) for v in conn.entries[0].uniqueMember.values]


def test_sync_moves_a_member_on_both_sides_of_the_relation():
    conn = _directory()
    _add_member(conn, 'm1', shares=2, end=EXPIRED,
                groups=(COMMUNITY, COOPERATORS))
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        target = sync_member_groups(SimpleNamespace(), 'm1', today=TODAY)

    assert target == {COMMUNITY, MISSING_YEAR}
    assert _groups_of(conn, 'm1') == {COMMUNITY, MISSING_YEAR}
    assert _group_has(conn, MISSING_YEAR, 'm1')
    assert not _group_has(conn, COOPERATORS, 'm1')


def test_sync_removes_the_legacy_ordinary_group():
    conn = _directory()
    _add_member(conn, 'm2', mtype='ORDINARY', groups=(LEGACY_ORDINARY,))
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        target = sync_member_groups(SimpleNamespace(), 'm2', today=TODAY)

    assert target == {COMMUNITY}
    assert _groups_of(conn, 'm2') == {COMMUNITY}
    assert not _group_has(conn, LEGACY_ORDINARY, 'm2')


def test_the_daily_scan_turns_calendar_time_into_transitions():
    conn = _directory()
    _add_member(conn, 'm3', shares=2, end=EXPIRED,
                groups=(COMMUNITY, COOPERATORS))
    _add_member(conn, 'm4', shares=2, end=VALID,
                groups=(COMMUNITY, COOPERATORS))
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        changed = daily_group_scan(SimpleNamespace(), today=TODAY)

    assert changed == ['m3']
    assert _groups_of(conn, 'm3') == {COMMUNITY, MISSING_YEAR}
    assert _groups_of(conn, 'm4') == {COMMUNITY, COOPERATORS}


# ----------------------------- the event sources --------------------------- #
def test_registration_places_the_ordinary_member_in_community():
    conn = _directory()
    candidature = SimpleNamespace(
        oid='new-1', pseudonym='fresh', email='f@example.com',
        type=MemberTypes.ORDINARY,
        data=SimpleNamespace(lang1='en', lang2=None, lang3=None,
                             description=None),
    )
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'is_valid_unique_pseudonym',
                      return_value=None):
        result = utils.register_user_to_ldap(
            SimpleNamespace(), candidature, 'S3cret!!')

    assert result['status'] == 'success', result
    assert _groups_of(conn, 'new-1') == {COMMUNITY}
    assert _group_has(conn, COMMUNITY, 'new-1')
    assert not _group_has(conn, LEGACY_ORDINARY, 'new-1')


def test_the_upgrade_lands_in_the_matching_candidates_group():
    conn = _directory()
    _add_member(conn, 'up-1', mtype='ORDINARY', groups=(COMMUNITY,))
    candidature = SimpleNamespace(
        oid='cand-9', pseudonym='user-up-1', email='u@example.com',
        existing_member_oid='up-1', type=MemberTypes.COOPERATOR,
        data=SimpleNamespace(
            fullname='Jean', fullsurname='Doe', nationality='FR',
            birthdate=date(2000, 1, 1)))
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(dg, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'update_member_from_ldap'):
        result = utils.register_user_to_ldap(
            SimpleNamespace(), candidature, '')

    assert result['status'] == 'success', result
    assert _groups_of(conn, 'up-1') == {COMMUNITY, MISSING_SHARE_YEAR}
    assert not _group_has(conn, COOPERATORS, 'up-1')


def test_the_resignation_leaves_every_group():
    conn = _directory()
    _add_member(conn, 'gone-1', shares=2, end=VALID,
                groups=(COMMUNITY, COOPERATORS))
    member = SimpleNamespace(oid='gone-1')
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(dg, 'get_ldap_connection', return_value=conn):
        result = utils.deactivate_member_in_ldap(
            SimpleNamespace(), member, datetime.now())

    assert result['status'] == 'success'
    assert _groups_of(conn, 'gone-1') == set()
    assert not _group_has(conn, COOPERATORS, 'gone-1')
    assert not _group_has(conn, COMMUNITY, 'gone-1')
