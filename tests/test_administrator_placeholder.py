"""Regression tests for the ${administrator} placeholder (issue #81, PR #230).

Three catalog messages reference ${administrator}: the identity-verification
e-mail template shown to the cooperator (email_copy_id_verification_body), the
voters_not_selected error page, and modify_member's forget_email_send_error.
Their call sites did not provide the value, so the literal ${administrator} was
displayed instead of the administrator's e-mail address.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.views.register as register_module
from alirpunkto.constants_and_globals import _
from alirpunkto.views.register import get_template_parameters_for_cooperator

ADMIN = "admin@example.org"
MSGIDS = (
    "email_copy_id_verification_body",
    "voters_not_selected",
    "forget_email_send_error",
)


@pytest.fixture
def localizer():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    alirpunkto.add_localizer(NewRequest(request))
    yield request.localizer
    tearDown()


@pytest.mark.parametrize("msgid", MSGIDS)
def test_catalog_interpolates_administrator(localizer, msgid):
    """The catalogs must substitute ${administrator} when the mapping has it."""
    rendered = localizer.translate(_(msgid, {'administrator': ADMIN}))
    assert ADMIN in rendered
    assert "${administrator}" not in rendered


def test_cooperator_email_templates_carry_the_administrator(localizer):
    """Issue #81: the identity-verification e-mail bodies must interpolate."""
    request = SimpleNamespace(
        registry=SimpleNamespace(settings={
            'site_name': 'AlirPunkto',
            'domain_name': 'alirpunkto.org',
            'organization_details': 'Org details',
        }),
        route_path=lambda *a, **k: '/vote?oid=x',
        route_url=lambda *a, **k: 'http://example/vote?oid=x',
    )
    candidature = SimpleNamespace(
        oid='cand-1',
        voters=[],
        data=SimpleNamespace(fullname='Jean', fullsurname='Candidate'),
    )
    with patch.object(register_module, 'ADMIN_EMAIL', ADMIN):
        params = get_template_parameters_for_cooperator(request, candidature)

    body = params['data_email_copy_id_verification_body']
    assert body.mapping['administrator'] == ADMIN
    rendered = localizer.translate(body)
    assert ADMIN in rendered
    assert "${administrator}" not in rendered


def test_error_call_sites_provide_the_administrator():
    """The error messages must carry the mapping at their call sites."""
    reg_src = inspect.getsource(register_module)
    assert "_('voters_not_selected',\n"
    assert "{'administrator': ADMIN_EMAIL}" in reg_src

    import alirpunkto.views.modify_member as modify_member_module
    mm_src = inspect.getsource(modify_member_module)
    assert "forget_email_send_error'," in mm_src.replace('\n', '') or \
           "_('forget_email_send_error'" in mm_src
    assert "{'administrator': ADMIN_EMAIL}" in mm_src
