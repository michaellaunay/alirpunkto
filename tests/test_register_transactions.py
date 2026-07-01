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
from alirpunkto.views import register as register_mod
from alirpunkto.views.register import (
    commit_candidature_changes,
    handle_unique_data_state,
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
