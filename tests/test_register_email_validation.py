"""Unit tests for ``register.handle_email_validation_state`` (audit section 3).

The view committed the pyramid_tm transaction mid-request
(``request.tm.commit()``) right before rendering the candidate form. Committing
mid-view rebinds the candidature to a finished transaction, so the rendered
section/form read a stale state — the "refresh to make the pseudonym field
appear" symptom. It also failed to render the form when the confirmation email
failed. The fix drops the explicit commit (pyramid_tm commits at the end of the
request) and always renders the form.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.views import register as register_mod
from alirpunkto.views.register import handle_email_validation_state


def _candidature():
    candidature = Candidature()
    candidature.candidature_state = CandidatureStates.EMAIL_VALIDATION
    candidature.challenge = {}  # no items -> validate_challenge passes
    return candidature


def _request():
    # A truthy 'submit' drives the validation branch; tm is a mock so we can
    # assert it is never committed by the view.
    return SimpleNamespace(POST={"submit": "1"}, params={}, tm=MagicMock())


def test_email_validation_advances_state_and_renders_form_without_explicit_commit(
    members_mapping,
):
    candidature = _candidature()
    request = _request()

    with patch.object(register_mod, "send_confirm_validation_email", return_value={}), \
         patch.object(register_mod, "render_candidature_form", return_value="<form/>"):
        result = handle_email_validation_state(request, candidature)

    assert candidature.candidature_state == CandidatureStates.CONFIRMED_HUMAN
    assert result.get("form") == "<form/>"       # section can render the form
    request.tm.commit.assert_not_called()        # pyramid_tm commits, not the view
    request.tm.abort.assert_not_called()


def test_email_validation_still_renders_form_when_confirmation_email_fails(
    members_mapping,
):
    candidature = _candidature()
    request = _request()

    with patch.object(
        register_mod, "send_confirm_validation_email", return_value={"error": True}
    ), patch.object(register_mod, "render_candidature_form", return_value="<form/>"):
        result = handle_email_validation_state(request, candidature)

    # State advances and the form is rendered even when the notification email
    # fails, so the template never renders a missing form.
    assert candidature.candidature_state == CandidatureStates.CONFIRMED_HUMAN
    assert result.get("form") == "<form/>"


def test_email_validation_returns_challenge_error_on_wrong_answer(members_mapping):
    candidature = _candidature()
    candidature.challenge = {"A": ("1 + 1", 2)}  # answer expected, none submitted
    request = _request()

    with patch.object(register_mod, "send_confirm_validation_email") as send:
        result = handle_email_validation_state(request, candidature)

    # Challenge failed: no state change, no email, error returned.
    assert candidature.candidature_state == CandidatureStates.EMAIL_VALIDATION
    assert result.get("error") is not None
    send.assert_not_called()
