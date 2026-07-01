"""End-to-end journey test for the cooperator registration flow.

Drives the register state machine through
DRAFT -> EMAIL_VALIDATION -> CONFIRMED_HUMAN -> UNIQUE_DATA -> PENDING
by calling the state handlers in sequence on a single persistent candidature.
External boundaries (email sending, LDAP pseudonym/voter lookups, deform
rendering) are mocked. The test locks the whole flow — the state transitions
and the section-3 behaviour (no explicit commit) — to secure future changes.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from webob.multidict import MultiDict

from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import MemberTypes
from alirpunkto.views import register as reg


def _request(pairs):
    params = MultiDict()
    for key, value in pairs:
        params.add(key, value)
    return SimpleNamespace(
        POST=params,
        params=params,
        method="POST",
        tm=MagicMock(),
        session=MagicMock(),
        registry=SimpleNamespace(
            settings={
                "site_name": "S",
                "domain_name": "D",
                "organization_details": "O",
            }
        ),
        route_url=lambda *a, **k: "http://example/vote",
        localizer=SimpleNamespace(translate=lambda s: str(s)),
    )


def test_cooperator_full_journey(members_mapping):
    candidature = Candidature()
    candidature.email = "coop@example.org"
    candidature.type = MemberTypes.COOPERATOR
    assert candidature.candidature_state == CandidatureStates.DRAFT

    # --- Step 1: DRAFT -> EMAIL_VALIDATION ---------------------------------
    req = _request([("submit", "1"), ("email", "coop@example.org"),
                    ("choice", "cooperator")])
    with patch.object(reg, "validate_candidature_choice_and_email", return_value=None), \
         patch("alirpunkto.utils.generate_math_challenges",
               return_value={"A": ("1 + 1", 2)}), \
         patch.object(reg, "attempt_send_validation_email", return_value=True), \
         patch.object(reg, "get_candidatures", return_value=members_mapping):
        reg.handle_draft_state(req, candidature)

    assert candidature.candidature_state == CandidatureStates.EMAIL_VALIDATION
    assert members_mapping[candidature.oid] is candidature

    # --- Step 2: EMAIL_VALIDATION -> CONFIRMED_HUMAN -----------------------
    req = _request([("submit", "1"), ("result_A", "2")])
    with patch.object(reg, "send_confirm_validation_email", return_value={}), \
         patch.object(reg, "render_candidature_form", return_value="<form/>"):
        result = reg.handle_email_validation_state(req, candidature)

    assert candidature.candidature_state == CandidatureStates.CONFIRMED_HUMAN
    assert result.get("form") == "<form/>"

    # --- Step 3: CONFIRMED_HUMAN -> UNIQUE_DATA ----------------------------
    fake_voters = [{"uid": "v1", "mail": "v1@x", "cn": "V1"}]
    req = _request([
        ("submit", "1"),
        ("pseudonym", "CoopUser"),
        ("password", "ValidPass123@"),
        ("password_confirm", "ValidPass123@"),
        ("fullname", "Ada"),
        ("fullsurname", "Lovelace"),
        ("nationality", "FR"),
        ("__start__", "birthdate:mapping"),
        ("date", "1990-01-01"),
        ("__end__", "birthdate:mapping"),
    ])
    with patch.object(reg, "is_valid_unique_pseudonym", return_value=None), \
         patch.object(reg, "send_candidature_state_change_email", return_value=None), \
         patch.object(reg, "random_voters", return_value=fake_voters), \
         patch.object(reg, "get_candidatures", return_value=members_mapping), \
         patch.object(reg, "get_template_parameters_for_cooperator",
                      return_value={"candidature": candidature,
                                    "MemberTypes": MemberTypes}):
        reg.handle_confirmed_human_state(req, candidature)

    assert candidature.candidature_state == CandidatureStates.UNIQUE_DATA
    assert [voter.oid for voter in candidature.voters] == ["v1"]
    assert candidature.pseudonym == "CoopUser"

    # --- Step 4: UNIQUE_DATA -> PENDING ------------------------------------
    req = _request([("confirm", "1")])
    with patch.object(reg, "_notify_verifiers_of_submission", return_value=None), \
         patch.object(reg, "get_candidatures", return_value=members_mapping):
        reg.handle_unique_data_state(req, candidature)

    assert candidature.candidature_state == CandidatureStates.PENDING
