"""Unit tests for ``register.validate_challenge`` (audit finding 2.17).

The validator read each answer with ``request.params[label]``, which raises
``KeyError`` (HTTP 500) when a challenge answer field is missing — e.g. the
candidate leaves one blank. A missing answer must count as an incorrect answer,
not crash. The fix reads it with ``request.params.get(label, '')``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from alirpunkto.constants_and_globals import _
from alirpunkto.models.candidature import Candidature
from alirpunkto.views.register import validate_challenge


def _candidature(challenge):
    candidature = Candidature()
    candidature.challenge = challenge
    return candidature


def _request(params):
    return SimpleNamespace(params=params)


def test_validate_challenge_missing_answer_returns_error(members_mapping):
    # Regression: a missing 'result_A' param used to raise KeyError.
    candidature = _candidature({"A": ("1 + 1", 2)})
    request = _request({})  # no answer submitted

    result = validate_challenge(request, candidature)

    assert result is not None
    assert result["error"] == _("invalid_challenge")


def test_validate_challenge_correct_answers_return_none(members_mapping):
    candidature = _candidature({"A": ("1 + 1", 2), "B": ("3 + 4", 7)})
    request = _request({"result_A": "2", "result_B": "7"})

    assert validate_challenge(request, candidature) is None


def test_validate_challenge_wrong_answer_returns_error(members_mapping):
    candidature = _candidature({"A": ("1 + 1", 2), "B": ("3 + 4", 7)})
    request = _request({"result_A": "2", "result_B": "8"})

    result = validate_challenge(request, candidature)

    assert result is not None
    assert result["error"] == _("invalid_challenge")


def test_validate_challenge_strips_whitespace(members_mapping):
    candidature = _candidature({"A": ("1 + 1", 2)})
    request = _request({"result_A": "  2  "})

    assert validate_challenge(request, candidature) is None
