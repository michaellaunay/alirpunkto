"""Regression tests for the site configuration semantics (#223 reopened, #242).

Two sources coexisted for the site variables: the .ini settings (read by the
views) and the environment constants (captured at import by
SITE_INFORMATION_MAPPING and the deform field descriptions). The register page
thus showed two different values for ${domain_name}. The .ini settings are now
the source of truth, resolved at rendering time; the constants are fallbacks.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import DOMAIN_NAME, SITE_INFORMATION_MAPPING
from alirpunkto.utils import get_site_url

PLATFORM = "CosmoPolitical Cooperative SCE"
SITE_URL = "https://access.cosmopolitical.coop"


@pytest.fixture
def configured():
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'domain_name': PLATFORM,
        'site_name': 'Access',
        'site_url': SITE_URL,
    })
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    request.route_url = lambda *a, **k: 'http://localhost:6543/view'
    alirpunkto.add_localizer(NewRequest(request))
    yield request
    tearDown()


# ------------------- the settings drive the interpolation ------------------
def test_mapping_reads_the_settings_at_rendering_time(configured):
    assert SITE_INFORMATION_MAPPING['domain_name'] == PLATFORM
    assert SITE_INFORMATION_MAPPING['site_url'] == SITE_URL


def test_mapping_falls_back_to_the_constants_without_settings():
    assert SITE_INFORMATION_MAPPING['domain_name'] == DOMAIN_NAME


def test_email_description_shows_the_configured_platform_name(configured):
    """The customer's report: the register page showed alirpunkto.org (the
    environment constant) while the title showed the configured name."""
    rendered = configured.registry.translate('email_description')
    # The GDPR paragraph cites the cooperative literally, so assert on the
    # interpolation site itself and on the absence of the constant values.
    assert f'infrastructure of {PLATFORM} will use' in rendered
    assert 'alirpunkto.org' not in rendered
    assert 'example.com' not in rendered  # the test-env constant


def test_deform_field_description_follows_the_settings(configured):
    """The schema captured the mapping at import time: it must still resolve
    the value configured in the .ini."""
    from alirpunkto.schemas.register_form import RegisterForm
    schema = RegisterForm().bind(request=configured)
    description = schema.get('email').description
    rendered = configured.localizer.translate(description)
    assert f'infrastructure of {PLATFORM} will use' in rendered
    assert 'alirpunkto.org' not in rendered
    assert 'example.com' not in rendered


# ------------------------------- get_site_url -------------------------------
def test_get_site_url_prefers_the_setting(configured):
    assert get_site_url(configured) == SITE_URL


def test_get_site_url_falls_back_to_the_environment():
    request = SimpleNamespace(registry=SimpleNamespace(settings={}))
    assert get_site_url(request).endswith(f"://{DOMAIN_NAME}")


def test_get_site_url_strips_the_trailing_slash():
    request = SimpleNamespace(registry=SimpleNamespace(
        settings={'site_url': SITE_URL + '/'}))
    assert get_site_url(request) == SITE_URL


# --------------------- the e-mail site_url follows suit ---------------------
def test_email_site_url_variable_uses_the_configuration(configured):
    captured = {}

    def fake_send_email(req, subject, recipients, template_resolver,
                        template_vars, *a, **k):
        captured.update(template_vars)
        return True

    member = SimpleNamespace(
        email='m@example.com', pseudonym='m', oid='oid-1',
        data=SimpleNamespace(lang1='en', fullname='Jean'),
        email_send_status_history=[SimpleNamespace(seed='s')],
        add_email_send_status=lambda *a, **k: None,
    )
    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'):
        utils.send_email_to_member(
            configured, member, 'test', 'reset_password_email',
            'reset_password_email_subject', 'forgot_password')
    assert captured['site_url'] == SITE_URL
    assert 'localhost' not in captured['site_url']
