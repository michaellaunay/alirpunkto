"""Regression tests for the postal address in e-mails (issue #169, PR #233).

Fourteen e-mail templates render `organization_details` (the reset-password
e-mail of the issue among them), and the sending helpers in utils.py used to
read the value from the ORGANIZATION_DETAILS environment constant only. The
deployment configures the address in the .ini (like site_name and domain_name),
so the constant fell back to its generic default and the postal address never
reached the e-mails — a spam-flagging factor. The helpers must prefer the
`organization_details` setting and fall back to the constant, so the value is
never None even when the .ini does not define it.
"""
from __future__ import annotations

import inspect
import os
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import ORGANIZATION_DETAILS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM = "The Cooperative, 1 Main Street, 59000 Lille, France"

FUNCTIONS = (
    "send_member_state_change_email",
    "send_email_to_member",
    "send_validation_email",
    "send_check_new_email",
)


def _request(settings_extra=None):
    settings = {
        'domain_name': 'alirpunkto.org',
        'site_name': 'AlirPunkto',
        'session.secret': 'x' * 32,
    }
    settings.update(settings_extra or {})
    return SimpleNamespace(
        registry=SimpleNamespace(settings=settings),
        route_url=lambda *a, **k: 'http://example/view',
    )


def _member():
    return SimpleNamespace(
        email='member@example.com',
        pseudonym='member',
        oid='oid-1',
        data=SimpleNamespace(fullname='Jean'),
        email_send_status_history=[SimpleNamespace(seed='seed-1')],
        add_email_send_status=lambda *a, **k: None,
    )


def _captured_vars(request):
    captured = {}

    def fake_send_email(req, subject, recipients, template_resolver,
                        template_vars, *a, **k):
        captured.update(template_vars)
        return True

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'get_localizer',
                      lambda r: SimpleNamespace(translate=lambda s: 'subject')), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'), \
         patch.object(utils, 'get_preferred_language', lambda r, member=None: 'en'):
        utils.send_email_to_member(
            request, _member(), 'test', 'reset_password_email',
            'reset_password_email_subject', 'forgot_password',
        )
    return captured


def test_falls_back_to_the_constant_when_the_setting_is_absent():
    """A deployment .ini without organization_details must not yield None."""
    captured = _captured_vars(_request())
    assert captured['organization_details'] == ORGANIZATION_DETAILS
    assert captured['organization_details']  # non-empty


def test_the_setting_wins_when_defined():
    captured = _captured_vars(_request({'organization_details': CUSTOM}))
    assert captured['organization_details'] == CUSTOM


@pytest.mark.parametrize("name", FUNCTIONS)
def test_every_sender_prefers_the_setting_with_a_fallback(name):
    src = inspect.getsource(getattr(utils, name))
    assert re.search(
        r"settings\.get\('organization_details'\)\s*\n?\s*or ORGANIZATION_DETAILS",
        src,
    ), f"{name} must prefer the setting and fall back to the constant"


def test_reset_password_template_renders_the_address():
    """The template of issue #169 must actually show the address (fr and en)."""
    from chameleon import PageTemplateFile
    for lang in ('fr', 'en'):
        path = os.path.join(ROOT, 'alirpunkto', 'locale', lang,
                            'LC_MESSAGES', 'reset_password_email.pt')
        html = PageTemplateFile(path)(
            organization_details=CUSTOM,
            domain_name='alirpunkto.org',
            site_name='AlirPunkto',
            user='jean',
            page_with_oid='http://example/reset',
            site_url='http://example/',
            member=SimpleNamespace(fullname='Jean'),
            textual=False,
        )
        assert CUSTOM in html
