"""The vote is final once concluded (issue #219, option 2 of the ticket).

A verifier re-using their voting link after every verifier had voted re-ran
the tally: the member was registered in LDAP again, the state-change e-mail
was sent again, and a changed ballot could even flip an approved candidature
to refused. The ticket settles on option 2: a verifier may change their mind
while the vote is open, and nothing may change once it is closed — which is
exactly when the candidature leaves PENDING.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.constants_and_globals import _
from alirpunkto.models.candidature import CandidatureStates, VotingChoice
from alirpunkto.views import vote
from alirpunkto.views.vote import vote_view

from tests.test_vote import _in_memory_candidature, _request, _wire


@pytest.mark.parametrize("closed_state", [
    CandidatureStates.APPROVED, CandidatureStates.REFUSED])
def test_a_revote_after_closure_changes_nothing(members_mapping, closed_state):
    candidature = _in_memory_candidature(["voter-1"], state=closed_state)
    candidature.voters[0].vote = VotingChoice.YES.name
    request = _request(candidature.oid, submit=True,
                       vote_value=VotingChoice.NO.name)

    with _wire(candidature, candidature.oid), \
         patch.object(vote, "send_candidature_state_change_email") as sender, \
         patch.object(vote, "register_user_to_ldap") as ldap:
        result = vote_view(request)

    assert result['error'] == _('voting_period_ended')
    assert candidature.voters[0].vote == VotingChoice.YES.name  # unchanged
    assert candidature.candidature_state == closed_state        # unchanged
    sender.assert_not_called()
    ldap.assert_not_called()


def test_the_link_after_closure_shows_the_period_ended(members_mapping):
    candidature = _in_memory_candidature(
        ["voter-1"], state=CandidatureStates.APPROVED)
    request = _request(candidature.oid)

    with _wire(candidature, candidature.oid):
        result = vote_view(request)

    assert result['error'] == _('voting_period_ended')


def test_changing_ones_mind_stays_possible_while_open(members_mapping):
    """Option 2: while the vote is open — here a second verifier has not
    voted yet — a verifier may change their ballot freely."""
    candidature = _in_memory_candidature(["voter-1", "voter-2"])
    candidature.voters[0].vote = VotingChoice.YES.name
    request = _request(candidature.oid, submit=True,
                       vote_value=VotingChoice.NO.name)

    with _wire(candidature, candidature.oid), \
         patch.object(vote, "send_candidature_state_change_email") as sender:
        result = vote_view(request)

    assert 'error' not in result
    assert candidature.voters[0].vote == VotingChoice.NO.name   # changed
    assert candidature.candidature_state == CandidatureStates.PENDING
    sender.assert_not_called()   # not everyone has voted: no tally yet
