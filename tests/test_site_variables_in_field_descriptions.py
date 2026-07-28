"""The #236 site variables are interpolated in the form field descriptions
(issues #210, #209, #208).

The three descriptions displayed ${forgetting_time_constant},
${url_pay_yearly_contrib} and ${url_purchase_shares} by name: the deform
fields capture SITE_INFORMATION_MAPPING at import time, and the mapping was
frozen on the environment constants. Since the variables exist (#236) and the
mapping resolves every key at rendering time from the deployment settings
(#242), the values show — these tests lock each ticket's field end to end,
through the bound form and the real localizer.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import (
    FORGETTING_TIME_CONSTANT,
    URL_PAY_YEARLY_CONTRIB,
    URL_PURCHASE_SHARES,
)

CASES = [
    # (issue, field, placeholder, constant fallback)
    ('#210', 'cooperative_behaviour_mark',
     'forgetting_time_constant', str(FORGETTING_TIME_CONSTANT)),
    ('#209', 'date_end_validity_yearly_contribution',
     'url_pay_yearly_contrib', URL_PAY_YEARLY_CONTRIB),
    ('#208', 'number_shares_owned',
     'url_purchase_shares', URL_PURCHASE_SHARES),
]


def _bound_description(settings, field):
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32, **settings})
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    try:
        from alirpunkto.schemas.register_form import RegisterForm
        schema = RegisterForm().bind(request=request)
        return request.localizer.translate(schema.get(field).description)
    finally:
        tearDown()


@pytest.mark.parametrize("issue, field, placeholder, fallback", CASES)
def test_the_value_shows_instead_of_the_variable_name(
        issue, field, placeholder, fallback):
    rendered = _bound_description({}, field)
    assert '${' + placeholder + '}' not in rendered, issue
    assert fallback in rendered, issue


@pytest.mark.parametrize("issue, field, placeholder, fallback", CASES)
def test_the_deployment_setting_wins(issue, field, placeholder, fallback):
    rendered = _bound_description({placeholder: 'CONFIGURED-VALUE'}, field)
    assert 'CONFIGURED-VALUE' in rendered, issue
    assert '${' + placeholder + '}' not in rendered, issue
