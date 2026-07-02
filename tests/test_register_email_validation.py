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


# --------------------------------------------------------------------------- #
# Regression: the pseudonym field must be editable right after the challenge
# (no page refresh needed).
#
# Two stacked causes produced the "refresh to make the pseudonym editable"
# symptom for ORDINARY candidates:
#   1. RegisterForm widgets are shared across instances (colander clone/bind
#      is shallow), and apply_permissions() mutated them in place - so any
#      earlier request applying a read-only profile (cooperator viewing a
#      PENDING candidature, admin, modify_member...) left pseudonym read-only
#      process-wide;
#   2. the post-challenge render (render_candidature_form) did not apply the
#      (CONFIRMED_HUMAN, type) permissions at all, unlike the refresh path
#      (handle_confirmed_human_state) - so it inherited the poisoned flags.
# The test reproduces the realistic sequence end to end with real rendering.
# --------------------------------------------------------------------------- #
import re

from pyramid.testing import DummyRequest, testConfig as pyramid_test_config

from alirpunkto.models.member import MemberTypes
from alirpunkto.models.model_permissions import access
from alirpunkto.schemas.register_form import RegisterForm
from alirpunkto.views.register import handle_confirmed_human_state


@pytest.fixture(autouse=True)
def _pristine_class_widgets():
    """Snapshot/restore class-level widget flags (see test_register_form)."""
    nodes = [
        node for node in RegisterForm.__all_schema_nodes__
        if getattr(node, "widget", None) is not None
    ]
    snapshot = [(node.widget, dict(node.widget.__dict__)) for node in nodes]
    yield
    for widget, saved in snapshot:
        widget.__dict__.clear()
        widget.__dict__.update(saved)


def _pseudonym_input(html: str):
    return re.search(r'<input[^>]*name="pseudonym"[^>]*>', html)


def _challenge_request():
    request = DummyRequest()
    request.POST = {
        "submit": "submit",
        "result_A": "14", "result_B": "41", "result_C": "17", "result_D": "13",
    }
    request.params = request.POST
    request.tm = MagicMock()
    request.localizer = SimpleNamespace(translate=str)
    return request


def test_pseudonym_is_editable_right_after_challenge_without_refresh(
    members_mapping,
):
    # [0] Another request in the same process applies a read-only profile
    #     through the public API (this is what poisoned the shared widgets).
    other = RegisterForm().bind(request=DummyRequest())
    read_only = access["Owner"][
        (CandidatureStates.PENDING, MemberTypes.COOPERATOR)
    ]
    other.apply_permissions(read_only.data)
    other.apply_permissions(read_only)

    # [1] An ORDINARY candidate submits the correct challenge answers.
    candidature = _candidature()
    candidature.type = MemberTypes.ORDINARY
    candidature.challenge = {
        "A": ("x", 14), "B": ("x", 41), "C": ("x", 17), "D": ("x", 13),
    }
    request = _challenge_request()
    with patch.object(
        register_mod, "send_confirm_validation_email", return_value={}
    ), pyramid_test_config(request=request):
        result = handle_email_validation_state(request, candidature)

    assert candidature.candidature_state == CandidatureStates.CONFIRMED_HUMAN
    post_input = _pseudonym_input(result["form"])
    assert post_input is not None, (
        "the post-challenge form must render an <input name='pseudonym'> "
        "(deform switches to its read-only template when the shared widget "
        "was poisoned, dropping the input entirely)"
    )
    assert 'readonly' not in post_input.group(0), (
        "the pseudonym field must be editable right after the challenge"
    )

    # [2] The refresh (GET on the CONFIRMED_HUMAN state) and the post-challenge
    #     render must agree: no more "refresh to unlock the field".
    get_request = DummyRequest()
    get_request.POST = {}
    get_request.params = {}
    get_request.tm = MagicMock()
    get_request.localizer = SimpleNamespace(translate=str)
    with pyramid_test_config(request=get_request):
        refreshed = handle_confirmed_human_state(get_request, candidature)
    refresh_input = _pseudonym_input(refreshed["form"])
    assert refresh_input is not None
    assert 'readonly' not in refresh_input.group(0)
