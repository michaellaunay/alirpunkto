"""The minimum age of Cooperators is enforced (issue #80).

The rule already half-existed: the birthdate node's Range capped at
get_majority_date() — the exact civil rule (18th birthday reached, Feb 29
handled), truer than the ticket's 6575-day approximation of the same
intent — and the description already carried the explanation text. Two
real gaps are closed here: the validator was built once at import, so
the majority date froze at process start and a long-running server
refused candidates who had since come of age; and the refusal was
colander's generic range message instead of the ticket's. The validator
is now deferred — recomputed at every bind — and carries the ticket's
message. The upgrade form clones the node, so both Cooperator doors are
covered; the Ordinary form has no birthdate at all, keeping the minors'
path open as the ticket itself invites.
"""
from __future__ import annotations

import datetime
from unittest.mock import patch

import colander
import pytest
from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.schemas import register_form as rf
from alirpunkto.schemas.register_form import RegisterForm


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    yield config
    tearDown()


def _birthdate_node(config):
    request = DummyRequest()
    return RegisterForm().bind(request=request).get('birthdate')


def test_the_validator_is_deferred_until_bind():
    """The regression that motivated the fix: built at class definition,
    the majority date froze at import."""
    unbound = RegisterForm().get('birthdate')
    assert isinstance(unbound.validator, colander.deferred)


def test_the_bound_follows_the_bind_not_the_import(config):
    """A server started weeks ago must still accept whoever came of age
    since: each bind recomputes the majority date."""
    future_majority = datetime.date.today() + datetime.timedelta(days=60)
    with patch.object(rf, 'get_majority_date',
                      return_value=future_majority):
        node = _birthdate_node(config)
    assert node.validator.max == future_majority
    node = _birthdate_node(config)
    assert node.validator.max == rf.get_majority_date()


def test_an_18th_birthday_today_is_accepted(config):
    node = _birthdate_node(config)
    majority = rf.get_majority_date()
    assert node.deserialize(majority.isoformat()) == majority


def test_the_eve_of_the_18th_birthday_is_refused_with_the_ticket_message(
        config):
    node = _birthdate_node(config)
    too_young = (rf.get_majority_date()
                 + datetime.timedelta(days=1)).isoformat()
    with pytest.raises(colander.Invalid) as excinfo:
        node.deserialize(too_young)
    assert 'cooperator_underage_error' in str(excinfo.value.asdict())


def test_the_upgrade_door_is_covered_too(config):
    """The ticket invites minors to register as Ordinary and upgrade
    later — the upgrade form must therefore enforce the same rule."""
    from alirpunkto.views.upgrade_to_cooperator import (
        _upgrade_identity_schema)
    class _Session(dict):
        def get_csrf_token(self):
            return "csrf-token"
    request = DummyRequest()
    request.session = _Session()
    node = _upgrade_identity_schema(request).get('birthdate')
    too_young = (rf.get_majority_date()
                 + datetime.timedelta(days=1)).isoformat()
    with pytest.raises(colander.Invalid) as excinfo:
        node.deserialize(too_young)
    assert 'cooperator_underage_error' in str(excinfo.value.asdict())
    majority = rf.get_majority_date()
    assert node.deserialize(majority.isoformat()) == majority


def test_the_ordinary_flow_carries_no_birthdate_field():
    """The minors' path stays open: the Ordinary form drops the identity
    fields, birthdate included (issue #80's own invitation)."""
    schema = RegisterForm()
    schema.prepare_for_ordinary()
    assert schema.get('birthdate') is None


def test_the_explanation_lives_in_the_description(config):
    node = _birthdate_node(config)
    assert 'birthdate_description' in str(node.description)
