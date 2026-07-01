"""Unit tests for the ``get_i18n_id`` fallbacks (audit finding 2.12).

The ``case _`` (should-never-happen) branch of several enums returned the
literal string ``"name.lower()"`` (an f-string without braces) instead of
interpolating the name. These tests check that every fallback interpolates the
name with the class's i18n prefix, and that a known name still resolves to its
explicit id.
"""

from __future__ import annotations

import pytest

from alirpunkto.models.candidature import CandidatureStates, VotingChoice
from alirpunkto.models.member import MemberRoles, MemberStates, MemberTypes
from alirpunkto.models.permissions import Permissions


# --------------------------------------------------------------------------- #
# the four fixed fallbacks
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "enum_cls, unknown, expected",
    [
        (MemberStates, "SOMETHING", "member_state_something"),
        (MemberTypes, "SOMETHING", "member_types_something"),
        (Permissions, "SOMETHING", "access_permissions_something"),
        (CandidatureStates, "SOMETHING", "candidature_states_something"),
    ],
)
def test_default_branch_interpolates_name(enum_cls, unknown, expected):
    assert enum_cls.get_i18n_id(unknown) == expected


# --------------------------------------------------------------------------- #
# already-correct fallbacks kept as controls
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "enum_cls, unknown, expected",
    [
        (MemberRoles, "SOMETHING", "role_types_something"),
        (VotingChoice, "SOMETHING", "vote_types_something"),
    ],
)
def test_control_fallbacks_still_interpolate(enum_cls, unknown, expected):
    assert enum_cls.get_i18n_id(unknown) == expected


# --------------------------------------------------------------------------- #
# no fallback returns the literal, and known names still resolve
# --------------------------------------------------------------------------- #
def test_no_fallback_returns_the_literal():
    for enum_cls in (
        MemberStates, MemberTypes, Permissions, CandidatureStates,
        MemberRoles, VotingChoice,
    ):
        assert enum_cls.get_i18n_id("anything") != "name.lower()"


def test_known_names_resolve_to_explicit_ids():
    assert MemberStates.get_i18n_id(MemberStates.CREATED.name) == "member_state_created_name"
    assert MemberTypes.get_i18n_id(MemberTypes.PROVIDER.name) == "member_types_provider"
    assert CandidatureStates.get_i18n_id(CandidatureStates.PENDING.name) == "candidature_states_pending"
    assert VotingChoice.get_i18n_id(VotingChoice.YES.name) == "vote_types_yes"
