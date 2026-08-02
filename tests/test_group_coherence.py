"""Sixth audit pass (2026-08-01, §12.3).

The two sides of a group membership — the member's ``uniqueMemberOf``
and the group's ``uniqueMember`` — used to receive one shared diff
computed from the member side alone, so a half-applied write persisted
forever: a membership recorded on one side only was invisible to the
next sync, and the daily scan only discovered members through the group
side. Each side now converges independently onto the same target, a
detected divergence is logged before repair, the scan discovers members
from either side, and writes are ordered fail-closed (the application
reads the member side: grants land there last, revocations first).
"""
from __future__ import annotations

import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from ldap3 import MODIFY_ADD

import alirpunkto.dynamic_groups as dg
from alirpunkto.dynamic_groups import (
    COMMUNITY, COOPERATORS, LEGACY_ORDINARY, MISSING_YEAR,
    daily_group_scan, group_dn, member_dn, sync_member_groups)
from tests.test_dynamic_groups import (
    EXPIRED, TODAY, VALID, _add_member, _directory, _group_has, _groups_of)


def _add_member_side_only(conn, oid, *, mtype='COOPERATOR', shares=2,
                          end=VALID, member_of=()):
    """A member whose ``uniqueMemberOf`` names groups that do NOT list
    them back — the persistent half-applied state of the finding."""
    attrs = {
        'objectClass': ['top', 'inetOrgPerson'],
        'uid': oid, 'cn': f'user-{oid}', 'sn': f'user-{oid}',
        'employeeType': mtype, 'isActive': 'True',
        'numberSharesOwned': str(shares),
    }
    if end is not None:
        attrs['dateEndValidityYearlyContribution'] = \
            datetime(end.year, end.month, end.day).strftime(
                '%Y-%m-%dT%H:%M:%S')
    if member_of:
        attrs['uniqueMemberOf'] = [group_dn(g) for g in member_of]
    conn.add(member_dn(oid), attributes=attrs)


def test_a_member_side_only_membership_is_repaired_on_the_group_side():
    """The exact persistent state of §12.3: the member side already
    matches the target, so the old shared diff was empty and the group
    side stayed wrong forever."""
    conn = _directory()
    _add_member_side_only(conn, 'half-m',
                          member_of=(COMMUNITY, COOPERATORS))
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        target = sync_member_groups(SimpleNamespace(), 'half-m',
                                    today=TODAY)

    assert target == {COMMUNITY, COOPERATORS}
    assert _group_has(conn, COMMUNITY, 'half-m')
    assert _group_has(conn, COOPERATORS, 'half-m')
    assert _groups_of(conn, 'half-m') == {COMMUNITY, COOPERATORS}


def test_a_group_side_only_membership_is_detected_and_repaired(caplog):
    conn = _directory()
    _add_member_side_only(conn, 'half-g')      # no uniqueMemberOf at all
    conn.modify(group_dn(COOPERATORS),
                {'uniqueMember': [(MODIFY_ADD, [member_dn('half-g')])]})

    with caplog.at_level(logging.WARNING), \
         patch.object(dg, 'get_ldap_connection', return_value=conn):
        target = sync_member_groups(SimpleNamespace(), 'half-g',
                                    today=TODAY)

    assert "sides diverged" in caplog.text
    assert target == {COMMUNITY, COOPERATORS}
    assert _groups_of(conn, 'half-g') == {COMMUNITY, COOPERATORS}
    assert _group_has(conn, COMMUNITY, 'half-g')
    assert _group_has(conn, COOPERATORS, 'half-g')


def test_the_scan_discovers_a_member_recorded_on_the_member_side_only():
    """The old collector walked the groups' ``uniqueMember`` only: a
    member carrying a stale ``uniqueMemberOf`` while listed in no group
    was never scanned, hence never repaired."""
    conn = _directory()
    _add_member_side_only(conn, 'ghost', mtype='ORDINARY', shares=0,
                          end=None, member_of=(LEGACY_ORDINARY,))
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        changed = daily_group_scan(SimpleNamespace(), today=TODAY)

    assert 'ghost' in changed
    assert _groups_of(conn, 'ghost') == {COMMUNITY}
    assert _group_has(conn, COMMUNITY, 'ghost')
    assert not _group_has(conn, LEGACY_ORDINARY, 'ghost')


def test_grants_land_on_the_member_side_last_and_leave_it_first():
    """The application reads the member side, so it must be the last
    side a grant touches and the first side a revocation clears."""
    conn = _directory()
    _add_member(conn, 'ord-m', shares=2, end=EXPIRED,
                groups=(COMMUNITY, COOPERATORS))
    calls = []
    original_modify = conn.modify

    def recording(target_dn, changes):
        attribute = next(iter(changes))
        operation = changes[attribute][0][0]
        calls.append((target_dn, attribute, operation))
        return original_modify(target_dn, changes)

    conn.modify = recording
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        target = sync_member_groups(SimpleNamespace(), 'ord-m',
                                    today=TODAY)

    assert target == {COMMUNITY, MISSING_YEAR}
    dn = member_dn('ord-m')
    grant_group = calls.index(
        (group_dn(MISSING_YEAR), 'uniqueMember', 'MODIFY_ADD'))
    grant_member = calls.index((dn, 'uniqueMemberOf', 'MODIFY_ADD'))
    revoke_member = calls.index((dn, 'uniqueMemberOf', 'MODIFY_DELETE'))
    revoke_group = calls.index(
        (group_dn(COOPERATORS), 'uniqueMember', 'MODIFY_DELETE'))
    assert grant_group < grant_member
    assert revoke_member < revoke_group
