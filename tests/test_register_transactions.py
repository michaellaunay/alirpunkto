"""Unit tests for the section-3 commit removals in register.py.

These views used to call ``request.tm.commit()`` mid-request to flush a queued
email and record its "SENT" status. Emails go through the transaction-aware
``pyramid_mailer`` (never sent before commit), so the explicit commits were
redundant: pyramid_tm commits state changes, queued emails and status records
together at the end of the request. The tests assert the views no longer commit
explicitly while keeping their effects.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import MemberDatas
from alirpunkto.constants_and_globals import _
from alirpunkto.views import register as register_mod
from alirpunkto.views.register import (
    commit_candidature_changes,
    handle_unique_data_state,
    prepare_for_cooperator,
)


def test_commit_candidature_changes_registers_and_marks_sent_without_committing(
    members_mapping,
):
    candidature = Candidature()
    request = SimpleNamespace(tm=MagicMock())

    with patch.object(register_mod, "get_candidatures", return_value=members_mapping):
        result = commit_candidature_changes(request, candidature)

    # Candidature registered in the mapping and returned, validation email
    # marked SENT, and no explicit commit/abort (pyramid_tm handles it).
    assert members_mapping[candidature.oid] is candidature
    assert members_mapping.monitored_members[candidature.oid] is candidature
    assert result.get("candidature") is candidature
    request.tm.commit.assert_not_called()
    request.tm.abort.assert_not_called()


def test_handle_unique_data_confirm_advances_to_pending_without_explicit_commit(
    members_mapping,
):
    candidature = Candidature()
    candidature.candidature_state = CandidatureStates.UNIQUE_DATA
    request = SimpleNamespace(POST={"confirm": "1"}, tm=MagicMock())

    with patch.object(register_mod, "prepare_for_cooperator", return_value=None), \
         patch.object(register_mod, "_notify_verifiers_of_submission") as notify, \
         patch.object(register_mod, "get_candidatures", return_value=members_mapping):
        result = handle_unique_data_state(request, candidature)

    assert candidature.candidature_state == CandidatureStates.PENDING
    assert result.get("candidature") is candidature
    notify.assert_called_once()
    request.tm.commit.assert_not_called()


def test_handle_unique_data_without_confirm_does_not_advance(members_mapping):
    candidature = Candidature()
    candidature.candidature_state = CandidatureStates.UNIQUE_DATA
    request = SimpleNamespace(POST={}, tm=MagicMock())

    with patch.object(register_mod, "prepare_for_cooperator", return_value=None), \
         patch.object(
             register_mod, "get_template_parameters_for_cooperator",
             return_value={"candidature": candidature, "MemberTypes": None},
         ):
        handle_unique_data_state(request, candidature)

    assert candidature.candidature_state == CandidatureStates.UNIQUE_DATA
    request.tm.commit.assert_not_called()


def test_prepare_for_cooperator_returns_error_when_voter_selection_fails(
    members_mapping,
):
    # random_voters() opens an LDAP connection and reads entry attributes, so it
    # can raise. prepare_for_cooperator must return the voters_not_selected error
    # rather than let the exception propagate (HTTP 500).
    candidature = Candidature()
    candidature.data = MemberDatas(fullname="Ada", fullsurname="Lovelace")
    request = SimpleNamespace(
        route_url=lambda *a, **k: "http://example/vote",
        registry=SimpleNamespace(
            settings={
                "site_name": "S",
                "domain_name": "D",
                "organization_details": "O",
            }
        ),
    )

    with patch.object(
        register_mod, "random_voters", side_effect=Exception("LDAP down")
    ):
        result = prepare_for_cooperator(request, candidature)

    assert result is not None
    assert result["error"] == _("voters_not_selected")
    assert not candidature.voters  # nothing assigned on failure


def test_prepare_for_cooperator_assigns_voters_on_success(members_mapping):
    candidature = Candidature()
    fake = [
        {"uid": "u1", "mail": "a@x", "cn": "Alice"},
        {"uid": "u2", "mail": "b@x", "cn": "Bob"},
    ]

    with patch.object(register_mod, "random_voters", return_value=fake):
        result = prepare_for_cooperator(SimpleNamespace(), candidature)

    assert result is None
    assert [voter.oid for voter in candidature.voters] == ["u1", "u2"]
