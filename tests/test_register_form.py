"""Unit tests for the password validator of ``RegisterForm`` (audit finding 2.11).

The field used ``colander.Function(is_valid_password)`` directly, which inverts
the result: ``colander.Function`` treats a falsy/string result as a failure and
a truthy non-string result as success, while ``is_valid_password`` returns
``None`` when valid and an error mapping when not. A valid password was thus
rejected and an invalid one accepted. The fix wraps it in an adapter.
"""

from __future__ import annotations

from unittest.mock import patch

import colander
import pytest

from alirpunkto.schemas import register_form as rf
from alirpunkto.schemas.register_form import RegisterForm, _validate_password


# --------------------------------------------------------------------------- #
# the adapter
# --------------------------------------------------------------------------- #
def test_validate_password_returns_true_for_valid():
    with patch.object(rf, "is_valid_password", return_value=None):
        assert _validate_password("whatever") is True


def test_validate_password_returns_message_for_invalid():
    with patch.object(rf, "is_valid_password", return_value={"error": "password_too_short"}):
        assert _validate_password("x") == "password_too_short"


# --------------------------------------------------------------------------- #
# behaviour through colander.Function
# --------------------------------------------------------------------------- #
def test_colander_function_accepts_valid_password():
    node = colander.SchemaNode(colander.String())
    validator = colander.Function(_validate_password)
    with patch.object(rf, "is_valid_password", return_value=None):
        validator(node, "GoodPass1$")  # must not raise


def test_colander_function_rejects_invalid_password():
    node = colander.SchemaNode(colander.String())
    validator = colander.Function(_validate_password)
    with patch.object(rf, "is_valid_password", return_value={"error": "password_too_short"}):
        with pytest.raises(colander.Invalid):
            validator(node, "x")


# --------------------------------------------------------------------------- #
# the actual schema field validator (catches the inversion regardless of impl)
# --------------------------------------------------------------------------- #
def test_registerform_password_field_is_not_inverted():
    password_node = RegisterForm().get("password")
    validator = password_node.validator

    with patch.object(rf, "is_valid_password", return_value=None):
        validator(password_node, "GoodPass1$")  # valid -> must not raise

    with patch.object(rf, "is_valid_password", return_value={"error": "bad"}):
        with pytest.raises(colander.Invalid):
            validator(password_node, "x")  # invalid -> must raise


# --------------------------------------------------------------------------- #
# widget isolation (the "pseudonym read-only after the e-mail challenge" bug)
#
# colander's clone()/bind() shallow-copies schema nodes: the ``widget``
# attribute is the very same object as on the class-level definition, hence
# shared by every RegisterForm instance in the process. apply_permissions()
# used to mutate widget.readonly/hidden in place, so the permission profile of
# one request leaked into every later render that did not re-apply
# permissions - e.g. the form rendered right after the e-mail challenge.
# --------------------------------------------------------------------------- #
from pyramid.testing import DummyRequest

from alirpunkto.models.candidature import CandidatureStates
from alirpunkto.models.member import MemberTypes
from alirpunkto.models.model_permissions import access


@pytest.fixture(autouse=True)
def _pristine_class_widgets():
    """Snapshot/restore the class-level widget flags around each test.

    Protects the rest of the suite from cross-test pollution if the
    widget-sharing regression ever comes back (before the fix, a single
    apply_permissions() call poisoned every subsequent RegisterForm render
    in the process).
    """
    nodes = [
        node for node in RegisterForm.__all_schema_nodes__
        if getattr(node, "widget", None) is not None
    ]
    snapshot = [
        (node.widget, dict(node.widget.__dict__)) for node in nodes
    ]
    yield
    for widget, saved in snapshot:
        widget.__dict__.clear()
        widget.__dict__.update(saved)


def _read_only_owner_profile():
    # Any profile where pseudonym is READ-only does: a cooperator viewing
    # their PENDING candidature is a realistic production request.
    return access["Owner"][(CandidatureStates.PENDING, MemberTypes.COOPERATOR)]


def test_apply_permissions_does_not_leak_into_other_instances():
    profile = _read_only_owner_profile()

    first = RegisterForm().bind(request=DummyRequest())
    first.apply_permissions(profile.data)
    first.apply_permissions(profile)
    assert first.get("pseudonym").widget.readonly is True  # applied locally

    fresh = RegisterForm().bind(request=DummyRequest())
    assert not getattr(fresh.get("pseudonym").widget, "readonly", False), (
        "apply_permissions() on one RegisterForm instance must not make the "
        "pseudonym widget read-only on a fresh instance (shared-widget leak)"
    )


def test_apply_permissions_gives_each_instance_its_own_widgets():
    profile = _read_only_owner_profile()

    first = RegisterForm().bind(request=DummyRequest())
    first.apply_permissions(profile.data)
    first.apply_permissions(profile)

    fresh = RegisterForm().bind(request=DummyRequest())
    assert first.get("pseudonym").widget is not fresh.get("pseudonym").widget, (
        "after apply_permissions() the instance must own a private widget copy"
    )
