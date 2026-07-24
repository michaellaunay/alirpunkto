"""Regression tests for ${...} interpolation in templates (issue #223).

Templates call _('msgid') (registry.translate). Many messages carry ${...}
placeholders — domain_name, site_name, and the site URLs of issue #236. The
localizer only substitutes them when the TranslationString carries a mapping, so
_() must inject SITE_INFORMATION_MAPPING; otherwise ${domain_name} is rendered
as literal text on the first registration page and in several e-mails.
"""
from __future__ import annotations

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import SITE_INFORMATION_MAPPING


@pytest.fixture
def translate():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    alirpunkto.add_localizer(NewRequest(request))  # installs registry.translate
    yield request.registry.translate
    tearDown()


@pytest.mark.parametrize(
    "msgid",
    [
        'cosmopolitical_cooperative_description',
        'ordinary_member_data_explanation',
        'cooperator_data_explanation',
    ],
)
def test_template_message_has_no_leftover_placeholder(translate, msgid):
    rendered = translate(msgid)
    assert '${domain_name}' not in rendered
    assert '${site_name}' not in rendered


def test_translate_interpolates_the_domain(translate):
    rendered = translate('cosmopolitical_cooperative_description')
    # DOMAIN_NAME defaults to example.com in the test environment.
    assert SITE_INFORMATION_MAPPING['domain_name'] in rendered


def test_translate_accepts_extra_mapping_keys(translate):
    # Explicit keys win and site keys are still available.
    rendered = translate('cosmopolitical_cooperative_description',
                          {'domain_name': 'override.example'})
    assert 'override.example' in rendered
    assert '${' not in rendered


def test_translate_defaults_do_not_mutate_the_shared_mapping(translate):
    translate('cosmopolitical_cooperative_description', {'domain_name': 'x'})
    # The shared, read-only mapping must be untouched by a per-call override.
    assert SITE_INFORMATION_MAPPING['domain_name'] != 'x'
