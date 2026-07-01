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
