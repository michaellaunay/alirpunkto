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
        registry=SimpleNamespace(queryUtility=lambda *a, **k: None, settings={
            'domain_name': 'alirpunkto.org',
            'site_name': 'AlirPunkto',
            'session.secret': 'x' * 32,
        }),
        route_url=lambda *a, **k: 'http://example/register',
    )

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'get_localizer', lambda r: SimpleNamespace(translate=lambda s: 'subject')), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'), \
         patch.object(utils, 'get_preferred_language', lambda r, member=None: 'en'):
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


RESULT_LANGUAGES = ('de', 'en', 'es', 'fr', 'it', 'nl', 'pl')


@pytest.mark.parametrize("lang", RESULT_LANGUAGES)
def test_rejection_template_exists(lang):
    """#214 / PR #235: the rejection template exists in the seven languages."""
    path = os.path.join(LOCALE, lang, 'LC_MESSAGES',
                        'send_candidature_rejected_email.pt')
    assert os.path.isfile(path), f"missing rejection template for {lang}"


def _result_render_vars():
    from alirpunkto.models.member import MemberTypes, MemberStates
    from alirpunkto.models.candidature import CandidatureStates
    cand = SimpleNamespace(
        pseudonym='jdoe', type=MemberTypes.COOPERATOR, oid='oid-1',
        modifications=['2026-01-01'],
        data=SimpleNamespace(lang1='fr', lang2='en', lang3='de',
                             fullname='Jean'),
    )
    return dict(
        page_register_with_oid='http://x/r', site_url='http://x/',
        site_name='AlirPunkto', domain_name='alirpunkto.org',
        organization_details='Org details', member=cand,
        MemberStates=MemberStates, user='jdoe', candidature=cand,
        CandidatureStates=CandidatureStates, MemberTypes=MemberTypes,
    )


@pytest.mark.parametrize("lang", RESULT_LANGUAGES)
@pytest.mark.parametrize("name", ['send_candidature_approuved_email',
                                  'send_candidature_rejected_email'])
@pytest.mark.parametrize("textual", [False, True])
def test_result_templates_render_cleanly(lang, name, textual):
    """PR #235: every result template renders with the real sender's variables,
    with no ## placeholder, no ${...} leftover, and no typographic-quote TAL
    attribute (the localized quotes broke Chameleon in five languages)."""
    from chameleon import PageTemplateFile
    path = os.path.join(LOCALE, lang, 'LC_MESSAGES', f'{name}.pt')
    html = PageTemplateFile(path)(**_result_render_vars(), textual=textual)
    assert '##' not in html
    assert '${' not in html
    assert 'jdoe' in html  # the pseudonym is actually rendered


def test_state_change_email_provides_member_types():
    """The approval template conditions on candidature.type == MemberTypes.X,
    so the sender must put MemberTypes in the template variables."""
    import inspect
    import alirpunkto.utils as utils
    src = inspect.getsource(utils.send_candidature_state_change_email)
    assert "'MemberTypes': MemberTypes" in src


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
