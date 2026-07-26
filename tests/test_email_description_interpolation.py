"""Regression tests for the e-mail explanation on /register (issue #223, reopened).

The email_description catalog message references ${domain_name} three times,
but the template rendered it through i18n:translate without providing the
variable, so the literal placeholder was displayed. The paragraph now renders
through _() — auto_translate — which merges SITE_INFORMATION_MAPPING into the
mapping and substitutes the site variables.
"""
from __future__ import annotations

import os

from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import DOMAIN_NAME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PT = os.path.join(ROOT, "alirpunkto", "templates", "register.pt")


def test_email_description_interpolates_the_domain_name():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')
    try:
        request = DummyRequest()
        alirpunkto.add_localizer(NewRequest(request))
        rendered = request.registry.translate('email_description')
        assert DOMAIN_NAME in rendered
        assert '${domain_name}' not in rendered
    finally:
        tearDown()


def test_register_template_renders_the_description_through_auto_translate():
    content = open(REGISTER_PT, encoding="utf-8").read()
    assert 'tal:content="_(\'email_description\')"' in content
    assert 'i18n:translate="email_description"' not in content


def test_register_template_still_compiles():
    from chameleon import PageTemplateFile
    PageTemplateFile(REGISTER_PT).cook_check()
