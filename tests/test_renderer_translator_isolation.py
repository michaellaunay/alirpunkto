"""The template translator is a per-request object (issue #244).

add_localizer published auto_translate on the *registry*, which is shared by
every request: the last request to enter dictated the language of every _()
block rendered afterwards. The docker healthcheck probes the site every few
seconds without an Accept-Language header, negotiating English — and the
arithmetic-challenge page keeps its request open for seconds while the e-mail
is sent over SMTP, so its _() blocks were rendered with the healthcheck's
English translator while the i18n:translate parts of the same page, resolved
per request, stayed in the visitor's language.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_renderer_globals

FRENCH_FRAGMENT = "Nous t'avons envoyé"
ENGLISH_FRAGMENT = "We sent you"
MSGID = 'human_verification_explanation'


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')
    yield config
    tearDown()


def _request(lang=None):
    request = DummyRequest()
    if lang:
        request._LOCALE_ = lang
    # A healthcheck-style probe sends no Accept-Language at all.
    request.accept_language = SimpleNamespace(best_match=lambda langs: lang)
    alirpunkto.add_localizer(NewRequest(request))
    return request


def _renderer_underscore(request):
    event = {'request': request}
    add_renderer_globals(event)
    return event['_']


def test_a_concurrent_probe_does_not_steal_the_language(config):
    """The heart of #244: the healthcheck entering *after* the visitor must
    not switch the visitor's _() blocks to English."""
    visitor = _request('fr')
    _request(None)          # healthcheck probe: no Accept-Language -> English

    rendered = _renderer_underscore(visitor)(MSGID)

    assert FRENCH_FRAGMENT in rendered
    assert ENGLISH_FRAGMENT not in rendered


def test_the_probe_itself_renders_english(config):
    visitor = _request('fr')
    probe = _request(None)

    rendered = _renderer_underscore(probe)(MSGID)

    assert ENGLISH_FRAGMENT in rendered


def test_the_registry_mirror_is_kept_for_compatibility(config):
    request = _request('fr')
    assert callable(request.registry.translate)
    assert FRENCH_FRAGMENT in request.registry.translate(MSGID)
