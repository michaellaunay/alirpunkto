"""Regression tests for the approval/rejection e-mails (issues #213, #214).

#213: at the end of the registration the candidate got the generic
candidature_state_change template instead of the friendly
send_candidature_approuved_email, because the caller passed the template name as
the sending_function_name positional argument, leaving template_name=None.

#214: no send_candidature_rejected_email template existed, so a rejected
candidate could not receive a rejection e-mail.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import alirpunkto.utils as utils


LOCALE = os.path.join(os.path.dirname(utils.__file__), 'locale')


def _template_for(name):
    """Return the resolved template path send_email would receive for `name`."""
    captured = {}

    def fake_send_email(request, subject, recipients, template_resolver, template_vars, *a, **k):
        captured['template'] = str(template_resolver)
        captured['subject'] = subject
        return True

    member = SimpleNamespace(
        email='cand@example.com',
        pseudonym='cand',
        oid='oid-1',
        email_send_status_history=[SimpleNamespace(seed='seed-1')],
        add_email_send_status=lambda *a, **k: None,
    )

    request = SimpleNamespace(
        registry=SimpleNamespace(settings={
            'domain_name': 'alirpunkto.org',
            'site_name': 'AlirPunkto',
            'session.secret': 'x' * 32,
        }),
        route_url=lambda *a, **k: 'http://example/register',
    )

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'get_localizer', lambda r: SimpleNamespace(translate=lambda s: 'subject')), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'), \
         patch.object(utils, 'get_preferred_language', lambda r: 'en'):
        utils.send_candidature_state_change_email(
            request, member,
            sending_function_name='test',
            template_name=name,
        )
    return captured


@pytest.mark.parametrize("name", [
    'send_candidature_approuved_email',
    'send_candidature_rejected_email',
])
def test_result_email_uses_the_friendly_template(name):
    """The resolved template must be the requested one, not the generic fallback."""
    captured = _template_for(name)
    assert captured['template'].endswith(f"{name}.pt")
    assert 'candidature_state_change.pt' not in captured['template']


def test_rejection_template_exists_in_english_and_french():
    """#214: the rejection template must exist (English is the fallback)."""
    for lang in ('en', 'fr'):
        path = os.path.join(LOCALE, lang, 'LC_MESSAGES',
                            'send_candidature_rejected_email.pt')
        assert os.path.isfile(path), f"missing rejection template for {lang}"


def test_rejection_template_renders_without_leftover_placeholder():
    from chameleon import PageTemplateFile
    path = os.path.join(LOCALE, 'en', 'LC_MESSAGES',
                        'send_candidature_rejected_email.pt')
    cand = SimpleNamespace(oid='oid-1', type=SimpleNamespace(name='ORDINARY'),
                           modifications=['2026-01-01'])
    # send_email renders e-mail templates with `textual` in scope (True for the
    # text part, False for HTML); provide it as the real sender does.
    html = PageTemplateFile(path)(domain_name='alirpunkto.org', user='cand',
                                  candidature=cand,
                                  organization_details='Org details',
                                  textual=False)
    assert 'not been approved' in html
    assert '${' not in html
    assert 'alirpunkto.org' in html


def test_callers_pass_the_template_as_template_name():
    """#213 guard: register/vote must pass the friendly template as template_name,
    not as the sending_function_name positional argument (which left the generic
    template in use)."""
    import inspect
    import alirpunkto.views.register as reg
    import alirpunkto.views.vote as vote

    reg_src = inspect.getsource(reg)
    vote_src = inspect.getsource(vote)

    # The fixed call sites name template_name explicitly.
    assert "template_name=email_template" in reg_src
    assert "template_name=email_template" in vote_src
