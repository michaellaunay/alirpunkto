"""Unit tests for ``alirpunkto.models.model_permissions.get_access_permissions``.

They cover audit fixes 2.1 (voters were never recognised because a string oid
was compared against a list of ``Voter`` dataclasses) and 2.2 (administrators
could not read candidatures, and uncovered matrix cells raised KeyError instead
of failing closed).
"""

from __future__ import annotations

import logging

import pytest

from alirpunkto.models.candidature import Candidature, CandidatureStates, Voter
from alirpunkto.models.member import Member, MemberTypes
from alirpunkto.models.model_permissions import (
    ADMIN_CANDIDATURE_PERMISSIONS,
    NO_MEMBER_PERMISSIONS,
    _resolve_permissions,
    access,
    get_access_permissions,
)
from alirpunkto.models.permissions import Permissions


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _candidature(state: CandidatureStates = CandidatureStates.PENDING) -> Candidature:
    candidature = Candidature()
    candidature.type = MemberTypes.ORDINARY
    candidature.candidature_state = state
    return candidature


def _member(oid: str, member_type: MemberTypes = MemberTypes.COOPERATOR) -> Member:
    member = Member(oid=oid)
    member.type = member_type
    return member


# --------------------------------------------------------------------------- #
# 2.1 - voter recognition
# --------------------------------------------------------------------------- #
def test_voter_gets_voter_permissions_for_candidature(members_mapping):
    """A registered voter must receive the ``voter`` permission profile.

    Regression: the voter branch compared ``accessor.oid`` (a string) to a list
    of ``Voter`` dataclasses and never matched, so voters silently fell through
    to the type-based (deny) path.
    """
    candidature = _candidature(CandidatureStates.PENDING)
    voter = _member("voter-1")
    candidature.voters = [
        Voter(oid="voter-1", email="v@example.com", pseudonym="v")
    ]

    permissions = get_access_permissions(candidature, voter)

    assert permissions is access["voter"][CandidatureStates.PENDING]
    # a voter must at least be able to cast a vote
    assert permissions.votes & Permissions.WRITE


def test_non_voter_does_not_get_voter_permissions(members_mapping):
    candidature = _candidature(CandidatureStates.PENDING)
    candidature.voters = [
        Voter(oid="someone-else", email="x@example.com", pseudonym="x")
    ]
    outsider = _member("not-a-voter")

    permissions = get_access_permissions(candidature, outsider)

    assert permissions is not access["voter"][CandidatureStates.PENDING]


# --------------------------------------------------------------------------- #
# 2.2 - administrator access + fail-closed resolution
# --------------------------------------------------------------------------- #
def test_administrator_can_read_candidature(members_mapping):
    """An administrator must resolve to the read-only candidature profile.

    Regression: ``access['Administrator']`` had no candidature-state entries, so
    an admin reading a candidature raised KeyError (HTTP 500).
    """
    candidature = _candidature(CandidatureStates.PENDING)
    admin = _member("admin-1", MemberTypes.ADMINISTRATOR)

    permissions = get_access_permissions(candidature, admin)

    assert permissions is ADMIN_CANDIDATURE_PERMISSIONS
    assert permissions.voters == Permissions.ACCESS | Permissions.READ


@pytest.mark.parametrize("state", list(CandidatureStates))
def test_administrator_reads_candidature_in_every_state(members_mapping, state):
    candidature = _candidature(state)
    admin = _member("admin-1", MemberTypes.ADMINISTRATOR)

    permissions = get_access_permissions(candidature, admin)

    assert permissions is ADMIN_CANDIDATURE_PERMISSIONS


def test_resolve_permissions_fails_closed_on_unknown_cell(caplog):
    """Missing ``(role, state)`` cells must deny and log, not raise.

    Regression: an uncovered cell used to raise KeyError (HTTP 500); it must now
    return ``NO_MEMBER_PERMISSIONS`` and emit a warning.
    """
    with caplog.at_level(logging.WARNING):
        permissions = _resolve_permissions("Owner", "not-a-real-state")

    assert permissions is NO_MEMBER_PERMISSIONS
    assert any(
        "no entry" in record.getMessage().lower() for record in caplog.records
    )
