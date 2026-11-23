"""Issue #272 — a member who lost every Dynamic Group stays lost.

A Cooperator whose yearly contribution lapses must remain in
``communityMembersGroup`` and join ``candidatesMissingYearContribGroup``
(#148). The truth table says so, but the daily scan only visited the
members ALREADY recorded in a managed group, on either side of the
relation: a member carrying no group at all — after a half-applied
write (the revocation landed, the grant did not), or a directory
reloaded without its memberships — was never looked at again, hence
never repaired. They kept no right on the platform, not even the one
to pay the contribution that would restore them.

The scan now walks every active Ordinary Member and Cooperator of the
directory, whatever their current groups.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from ldap3 import MODIFY_ADD

import alirpunkto.dynamic_groups as dg
from alirpunkto.dynamic_groups import (
    COMMUNITY, COOPERATORS, MISSING_SHARE_YEAR, MISSING_YEAR,
    daily_group_scan, sync_member_groups)
from tests.test_dynamic_groups import (
    EXPIRED, TODAY, VALID, _add_member, _directory, _group_has, _groups_of)


def _scan(conn):
    with patch.object(dg, 'get_ldap_connection', return_value=conn):
        return daily_group_scan(SimpleNamespace(), today=TODAY)


def test_a_groupless_lapsed_cooperator_is_found_and_restored():
    conn = _directory()
    _add_member(conn, 'lapsed', shares=2, end=EXPIRED)

    assert 'lapsed' in _scan(conn)
    assert _groups_of(conn, 'lapsed') == {COMMUNITY, MISSING_YEAR}
    assert _group_has(conn, COMMUNITY, 'lapsed')
    assert _group_has(conn, MISSING_YEAR, 'lapsed')


def test_a_groupless_paid_up_cooperator_is_restored_as_cooperator():
    conn = _directory()
    _add_member(conn, 'paid', shares=1, end=VALID)

    assert 'paid' in _scan(conn)
    assert _groups_of(conn, 'paid') == {COMMUNITY, COOPERATORS}


def test_a_groupless_ordinary_member_is_restored_in_the_community():
    conn = _directory()
    _add_member(conn, 'plain', mtype='ORDINARY')

    assert 'plain' in _scan(conn)
    assert _groups_of(conn, 'plain') == {COMMUNITY}


def test_a_cooperator_without_any_fact_still_belongs_to_the_community():
    """No share, no date at all: the weakest Cooperator status is still
    a member of the Community."""
    conn = _directory()
    _add_member(conn, 'bare', shares=0, end=None)

    _scan(conn)
    assert _groups_of(conn, 'bare') == {COMMUNITY, MISSING_SHARE_YEAR}


def test_resigned_and_out_of_scope_entries_are_left_alone():
    """``=> None`` of #148 stands: a resigned member has no group, and
    providers or administrators are not the scan's business."""
    conn = _directory()
    _add_member(conn, 'gone', active='False', shares=2, end=VALID)
    _add_member(conn, 'shop', mtype='PROVIDER')
    _add_member(conn, 'root', mtype='ADMINISTRATOR')

    assert _scan(conn) == []
    for oid in ('gone', 'shop', 'root'):
        assert _groups_of(conn, oid) == set()


def test_the_ticket_scenario_a_failed_grant_is_repaired_by_the_next_scan():
    """The path that produces the ticket's state: the contribution
    lapses, the revocation of ``cooperatorsGroup`` lands but the grants
    are refused that day. The member is left with no group — and the
    following pass must bring them back."""
    conn = _directory()
    _add_member(conn, 'unlucky', shares=2, end=EXPIRED,
                groups=(COOPERATORS,))
    real_modify = conn.modify

    def refuse_grants(target_dn, changes, *args, **kwargs):
        if any(op == MODIFY_ADD for ops in changes.values()
               for op, _ in ops):
            return False
        return real_modify(target_dn, changes, *args, **kwargs)

    with patch.object(dg, 'get_ldap_connection', return_value=conn), \
            patch.object(conn, 'modify', side_effect=refuse_grants):
        assert sync_member_groups(
            SimpleNamespace(), 'unlucky', today=TODAY) is None
    assert _groups_of(conn, 'unlucky') == set()
    assert not _group_has(conn, COOPERATORS, 'unlucky')

    assert _scan(conn) == ['unlucky']
    assert _groups_of(conn, 'unlucky') == {COMMUNITY, MISSING_YEAR}
