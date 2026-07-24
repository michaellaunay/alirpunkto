"""Regression tests for the site-specific i18n variables (issue #236).

The schema descriptions carry ${...} placeholders. Only domain_name, site_name
and organization_details used to be interpolated, so ${url_purchase_shares},
${url_pay_yearly_contrib} and ${forgetting_time_constant} were rendered as
literal variable names (issues #208, #209, #210).
"""
from __future__ import annotations

import pytest
from pyramid.i18n import TranslationString

from alirpunkto.constants_and_globals import (
    SITE_INFORMATION_MAPPING,
    URL_WORKSPACE,
    URL_PAY_YEARLY_CONTRIB,
    URL_PURCHASE_SHARES,
    FORGETTING_TIME_CONSTANT,
)
from alirpunkto.schemas.register_form import RegisterForm


REQUIRED_KEYS = (
    'domain_name',
    'site_name',
    'organization_details',
    'url_workspace',
    'url_pay_yearly_contrib',
    'url_purchase_shares',
    'forgetting_time_constant',
)


@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_mapping_exposes_every_site_variable(key):
    assert key in SITE_INFORMATION_MAPPING


def test_mapping_is_read_only():
    """It is shared by every TranslationString, so it must not be mutable."""
    with pytest.raises(TypeError):
        SITE_INFORMATION_MAPPING['domain_name'] = 'hijacked'


def test_mapping_carries_the_configured_values():
    assert SITE_INFORMATION_MAPPING['url_workspace'] == URL_WORKSPACE
    assert SITE_INFORMATION_MAPPING['url_pay_yearly_contrib'] == URL_PAY_YEARLY_CONTRIB
    assert SITE_INFORMATION_MAPPING['url_purchase_shares'] == URL_PURCHASE_SHARES
    assert SITE_INFORMATION_MAPPING['forgetting_time_constant'] == FORGETTING_TIME_CONSTANT


@pytest.mark.parametrize(
    "field, placeholder",
    [
        ('cooperative_behaviour_mark', 'forgetting_time_constant'),
        ('number_shares_owned', 'url_purchase_shares'),
        ('date_end_validity_yearly_contribution', 'url_pay_yearly_contrib'),
    ],
)
def test_field_description_interpolates_its_placeholder(field, placeholder):
    """The description must substitute the placeholder, not print its name."""
    description = RegisterForm().get(field).description
    assert isinstance(description, TranslationString)
    assert placeholder in description.mapping

    # Interpolating the raw msgid (no catalog) must not leave ${name} behind.
    rendered = TranslationString(
        f"value=${{{placeholder}}}", mapping=description.mapping
    ).interpolate()
    assert rendered == f"value={SITE_INFORMATION_MAPPING[placeholder]}"
    assert "${" not in rendered
