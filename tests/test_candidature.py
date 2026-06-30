from __future__ import annotations

from datetime import datetime

import pytest

from alirpunkto.models.candidature import Candidature, CandidatureStates, Voter, VotingChoice
from alirpunkto.models.member import MemberDataFunctions, MemberStates, Members


@pytest.mark.parametrize(
    "state, name_id, value_id",
    [
        (CandidatureStates.DRAFT, "candidature_states_draft", "candidature_states_draft_value"),
        (
            CandidatureStates.EMAIL_VALIDATION,
            "candidature_states_email_validation",
            "candidature_states_email_validation_value",
        ),
        (
            CandidatureStates.CONFIRMED_HUMAN,
            "candidature_states_confirmed_human",
            "candidature_states_confirmed_human_value",
        ),
        (
            CandidatureStates.UNIQUE_DATA,
            "candidature_states_unique_data",
            "candidature_states_unique_data_value",
        ),
        (CandidatureStates.PENDING, "candidature_states_pending", "candidature_states_pending_value"),
        (CandidatureStates.APPROVED, "candidature_states_approved", "candidature_states_approved_value"),
        (CandidatureStates.REFUSED, "candidature_states_refused", "candidature_states_refused_value"),
    ],
)
def test_candidature_state_i18n_ids(state, name_id, value_id):
    assert CandidatureStates.get_i18n_id(state.name) == name_id
    assert CandidatureStates.get_i18n_id(state.value) == value_id


@pytest.mark.parametrize(
    "choice, name_id, value_id",
    [
        (VotingChoice.YES, "vote_types_yes", "vote_types_yes_value"),
        (VotingChoice.NO, "vote_types_no", "vote_types_no_value"),
        (VotingChoice.ABSTAIN, "vote_types_abstain", "vote_types_abstain_value"),
    ],
)
def test_voting_choice_i18n_ids(choice, name_id, value_id):
    assert VotingChoice.get_i18n_id(choice.name) == name_id
    assert VotingChoice.get_i18n_id(choice.value) == value_id


def test_voter_defaults_to_no_vote():
    voter = Voter(oid="voter-1", email="voter@example.com", pseudonym="voter")
    assert voter.vote is None


def test_candidature_initialization_records_member_and_candidature_events(
    members_mapping,
    monkeypatch,
):
    monkeypatch.setattr(MemberDataFunctions, "func_now", lambda: datetime(2026, 1, 1))
    monkeypatch.setattr(MemberDataFunctions, "func_uuid", lambda: "candidate-1")
    monkeypatch.setattr("alirpunkto.models.member.random_string", lambda length: "s" * length)

    candidature = Candidature()

    assert candidature.oid == "candidate-1"
    assert candidature.member_state is MemberStates.DRAFT
    assert candidature.candidature_state is CandidatureStates.DRAFT
    assert [event.function_name for event in candidature.modifications] == [
        "__init__",
        "Candidature.__init__",
    ]


def test_approved_candidature_also_registers_member(members_mapping):
    candidature = Candidature()

    candidature.candidature_state = CandidatureStates.APPROVED

    assert candidature.candidature_state is CandidatureStates.APPROVED
    assert candidature.member_state is MemberStates.REGISTRED
    assert [event.function_name for event in candidature.modifications[-2:]] == [
        "member_state",
        "state",
    ]


def test_candidature_mutable_properties_return_copies(members_mapping):
    candidature = Candidature()
    voter = Voter(oid="voter-1", email="voter@example.com", pseudonym="voter")

    candidature.challenge = {"A": ("one plus one", 2)}
    candidature.voters = [voter]
    candidature.votes = {voter.oid: VotingChoice.YES}

    returned_voters = candidature.voters
    returned_votes = candidature.votes
    returned_voters.clear()
    returned_votes.clear()

    assert candidature.challenge == {"A": ("one plus one", 2)}
    assert candidature.voters == [voter]
    assert candidature.votes == {voter.oid: VotingChoice.YES}


@pytest.mark.parametrize(
    "attribute, value, message",
    [
        ("candidature_state", "APPROVED", "state"),
        ("challenge", ["not-a-dict"], "dictionary"),
        ("voters", "not-a-list", "list or a tuple"),
        ("votes", ["not-a-dict"], "dict"),
    ],
)
def test_candidature_setters_validate_types(members_mapping, attribute, value, message):
    candidature = Candidature()
    with pytest.raises(TypeError, match=message):
        setattr(candidature, attribute, value)


def test_member_oid_generation_skips_existing_oids(members_mapping, monkeypatch):
    members_mapping["duplicate"] = object()
    sequence = iter(["duplicate", "unique"])
    monkeypatch.setattr(MemberDataFunctions, "func_uuid", lambda: next(sequence))

    assert Candidature.generate_unique_oid() == "unique"


def test_candidature_field_names_include_member_and_candidature_properties():
    assert set(Candidature.get_field_names()) >= {
        "oid",
        "seed",
        "member_state",
        "email",
        "pseudonym",
        "challenge",
        "voters",
        "votes",
        "candidature_state",
    }
