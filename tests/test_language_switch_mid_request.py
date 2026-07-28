"""Applying a freshly chosen language to the current request (issue #247).

Storing the preferred language in the session (issue #204) only affects the
next request: add_localizer captured the localizer in a closure at NewRequest
time, so the response of the very request carrying the choice — the identity
document page and the verifier e-mail templates it embeds — was still rendered
in the language the procedure started with. switch_request_language rebuilds
request.localizer mid-request, and auto_translate now resolves it at call
time.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import _
from alirpunkto.utils import switch_request_language

WITNESS = 'email_copy_id_verification_subject'   # has a French msgstr
FRENCH_FRAGMENT = 'Vérifie mon identité'


@pytest.fixture
def request_():
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'domain_name': 'CosmoPolitical Cooperative SCE',
        'site_name': 'Access',
    })
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    yield request
    tearDown()


def test_switch_rebuilds_the_localizer_immediately(request_):
    before = request_.localizer.translate(_(WITNESS))
    assert FRENCH_FRAGMENT not in before

    assert switch_request_language(request_, 'fr') is True

    after = request_.localizer.translate(_(WITNESS))
    assert FRENCH_FRAGMENT in after
    assert request_.localizer.locale_name == 'fr'


def test_auto_translate_follows_the_switch(request_):
    """The heart of #247: auto_translate resolved the localizer from a
    closure frozen at NewRequest time, so a mid-request switch was invisible
    to everything rendered in the response."""
    before = request_.registry.translate(WITNESS)
    assert FRENCH_FRAGMENT not in before

    switch_request_language(request_, 'fr')

    after = request_.registry.translate(WITNESS)
    assert FRENCH_FRAGMENT in after
    # And the site variables are still interpolated (no ${...} leftover).
    assert '${domain_name}' not in after


def test_switch_sets_the_session_and_the_explicit_locale(request_):
    switch_request_language(request_, 'fr')
    assert request_.session['preferred_language'] == 'fr'
    assert request_._LOCALE_ == 'fr'


def test_an_unsupported_language_changes_nothing(request_):
    before = request_.localizer
    assert switch_request_language(request_, 'zz') is False
    assert request_.localizer is before
    assert 'preferred_language' not in request_.session


def test_cooperator_email_template_subject_follows_the_switch(request_):
    """The verifier e-mail templates embedded in the identity-document page
    are TranslationStrings rendered with the request localizer: after the
    switch they must come out in the candidate's language."""
    from alirpunkto.views.register import get_template_parameters_for_cooperator
    request_.registry.settings['organization_details'] = 'Org'
    request_.route_path = lambda *a, **k: '/vote?oid=x'
    candidature = SimpleNamespace(
        oid='c1', voters=[],
        data=SimpleNamespace(fullname='Jean', fullsurname='Doe'))

    switch_request_language(request_, 'fr')
    params = get_template_parameters_for_cooperator(request_, candidature)
    subject = request_.localizer.translate(
        params['data_email_copy_id_verification_subject'])

    assert FRENCH_FRAGMENT in subject


@pytest.mark.parametrize("module_path", [
    'alirpunkto.views.register',
    'alirpunkto.views.modify_member',
    'alirpunkto.views.login',
])
def test_the_entry_points_use_the_switch(module_path):
    import importlib
    src = inspect.getsource(importlib.import_module(module_path))
    assert 'switch_request_language(' in src
