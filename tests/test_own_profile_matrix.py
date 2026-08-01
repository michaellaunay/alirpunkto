"""The per-role field matrix of one's own profile (issue #55).

The ticket's four regimes, locked case by case: every registered member
views and edits their presentation text, e-mail and languages; a
Cooperator or assimilated additionally edits the IBAN and views — never
edits — the identity data, nationality, CBM (with its update time),
shares, contribution validity and role; the pseudonym and user number are
view-only for everyone; the erasure date of issue #54 is visible to no
one. The groups one belongs to are shown read-only outside the form. A
member whose resignation is pending can still open their own profile —
the cancel button lives there.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from alirpunkto.models.member import (
    MemberDatas, MemberStates, MemberTypes)
from alirpunkto.models.model_permissions import (
    NO_MEMBER_PERMISSIONS, Permissions, get_access_permissions)

RW = Permissions.ACCESS | Permissions.READ | Permissions.WRITE
RO = Permissions.ACCESS | Permissions.READ


def _member(mtype, state=MemberStates.DATA_MODIFICATION_REQUESTED):
    return SimpleNamespace(
        oid='m-1', pseudonym='p', email='m@example.com', type=mtype,
        member_state=state,
        data=MemberDatas(password='', fullname='J', fullsurname='D'))


def _own(mtype, state=MemberStates.DATA_MODIFICATION_REQUESTED):
    member = _member(mtype, state)
    return get_access_permissions(member, member)


O, C = MemberTypes.ORDINARY, MemberTypes.COOPERATOR

TICKET_TABLE = [
    # (case_id, member_type, field, must_have, must_not_have)
    ("everyone_edits_description", O, 'description', RW, None),
    ("everyone_edits_languages", O, 'lang1', RW, None),
    ("cooperator_edits_description", C, 'description', RW, None),
    ("cooperator_edits_iban", C, 'iban', RW, None),
    ("ordinary_never_sees_iban", O, 'iban', None, Permissions.READ),
    ("cooperator_views_fullname", C, 'fullname', RO, Permissions.WRITE),
    ("cooperator_views_birthdate", C, 'birthdate', RO, Permissions.WRITE),
    ("cooperator_views_nationality", C, 'nationality', RO,
     Permissions.WRITE),
    ("ordinary_never_sees_identity", O, 'fullname', None, Permissions.READ),
    ("ordinary_never_sees_nationality", O, 'nationality', None,
     Permissions.READ),
    ("cooperator_views_cbm", C, 'cooperative_behaviour_mark', RO,
     Permissions.WRITE),
    ("cooperator_views_cbm_update", C, 'cooperative_behaviour_mark_update',
     RO, Permissions.WRITE),
    ("ordinary_never_sees_cbm", O, 'cooperative_behaviour_mark', None,
     Permissions.READ),
    ("cooperator_views_shares", C, 'number_shares_owned', RO,
     Permissions.WRITE),
    ("cooperator_views_contribution", C,
     'date_end_validity_yearly_contribution', RO, Permissions.WRITE),
    ("ordinary_never_sees_shares", O, 'number_shares_owned', None,
     Permissions.READ),
    ("cooperator_views_role", C, 'role', Permissions.READ,
     Permissions.WRITE),
    ("nobody_sees_the_erasure_date_ordinary", O, 'date_erasure_all_data',
     None, Permissions.READ | Permissions.WRITE | Permissions.ACCESS),
    ("nobody_sees_the_erasure_date_cooperator", C, 'date_erasure_all_data',
     None, Permissions.READ | Permissions.WRITE | Permissions.ACCESS),
]


@pytest.mark.parametrize(
    "case, mtype, field, must_have, must_not_have", TICKET_TABLE,
    ids=[row[0] for row in TICKET_TABLE])
def test_the_ticket_matrix(case, mtype, field, must_have, must_not_have):
    permissions = _own(mtype)
    value = getattr(permissions.data, field)
    if must_have is not None:
        assert value & must_have == must_have, (field, value)
    if must_not_have is not None:
        assert not (value & must_not_have), (field, value)


def test_everyone_edits_their_email():
    for mtype in (O, C):
        permissions = _own(mtype)
        assert permissions.email & RW == RW


def test_pseudonym_and_user_number_are_view_only_for_everyone():
    for mtype in (O, C):
        permissions = _own(mtype)
        assert permissions.pseudonym & RO == RO
        assert not (permissions.pseudonym & Permissions.WRITE)
        assert permissions.oid & RO == RO
        assert not (permissions.oid & Permissions.WRITE)


def test_a_pending_resignation_still_opens_ones_own_profile():
    """Regression lock: PENDING_UNSUBSCRIPTION had no Owner entry, so the
    fail-closed matrix denied a resigning member their own profile — where
    the cancel button lives."""
    permissions = _own(C, MemberStates.PENDING_UNSUBSCRIPTION)
    assert permissions is not NO_MEMBER_PERMISSIONS
    assert permissions.data.description & Permissions.READ


# ------------------------------ the panel ---------------------------------- #
def test_the_own_panel_carries_groups_and_role():
    from unittest.mock import patch
    from alirpunkto.models.member import MemberRoles
    from alirpunkto.views import modify_member as mm
    member = _member(C)
    member.data.role = MemberRoles.BOARD
    with patch('alirpunkto.dynamic_groups.get_member_groups',
               return_value={'communityMembersGroup', 'boardMembersGroup',
                             'cooperatorsGroup'}):
        panel = mm._own_member_panel(SimpleNamespace(), member)
    assert [name for name, _ in panel['groups']] == [
        'boardMembersGroup', 'communityMembersGroup', 'cooperatorsGroup']
    assert dict(panel['groups'])['boardMembersGroup'] == 'group_label_board'
    assert panel['role_i18n'] == 'member_roles_board'


def test_the_ordinary_panel_shows_groups_but_no_role():
    from unittest.mock import patch
    from alirpunkto.views import modify_member as mm
    member = _member(O)
    with patch('alirpunkto.dynamic_groups.get_member_groups',
               return_value={'communityMembersGroup'}):
        panel = mm._own_member_panel(SimpleNamespace(), member)
    assert panel['groups'] == [
        ('communityMembersGroup', 'group_label_community')]
    assert panel['role_i18n'] is None
