"""Regression tests for e-mail subjects in the recipient's language (issue #239).

The e-mail bodies follow the recipient's declared language (#204), but the
subjects were translated with the localizer of the triggering request — the
approval subject arrived in the language of the last verifier who voted. Every
sending helper now translates its subject with _translate_for_language and the
recipient's preferred language; an already-translated plain string (as built by
the per-verifier senders of #238) is respected as-is.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.i18n import make_localizer
from pyramid.interfaces import ITranslationDirectories
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import _


@pytest.fixture
def app_request():
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'domain_name': 'alirpunkto.org',
        'site_name': 'AlirPunkto',
    })
    config.add_translation_dirs('alirpunkto:locale/')
    request = DummyRequest()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    request.route_url = lambda *a, **k: 'http://example/view'
    alirpunkto.add_localizer(NewRequest(request))
    yield request
    tearDown()


def _member(lang1='fr'):
    return SimpleNamespace(
        email='m@example.com', pseudonym='m', oid='oid-1',
        member_state=None,
        data=SimpleNamespace(lang1=lang1, fullname='Jean'),
        email_send_status_history=[SimpleNamespace(seed='s')],
        add_email_send_status=lambda *a, **k: None,
    )


def _fr(request, msgid):
    tdirs = request.registry.queryUtility(ITranslationDirectories)
    return make_localizer('fr', tdirs).translate(_(msgid))


def _capture_subject(request, call):
    captured = {}

    def fake_send_email(req, subject, recipients, template_resolver,
                        template_vars, *a, **k):
        captured['subject'] = subject
        return True

    with patch.object(utils, 'send_email', fake_send_email), \
         patch.object(utils, 'encrypt_oid', lambda *a, **k: 'token'):
        call()
    return captured['subject']


def test_reset_password_subject_follows_the_member_language(app_request):
    member = _member('fr')
    subject = _capture_subject(app_request, lambda: utils.send_email_to_member(
        app_request, member, 'test', 'reset_password_email',
        'reset_password_email_subject', 'forgot_password'))
    assert subject == _fr(app_request, 'reset_password_email_subject')
    assert subject == "Réinitialise ton mot de passe"


def test_state_change_default_subject_follows_the_member_language(app_request):
    member = _member('fr')
    subject = _capture_subject(
        app_request,
        lambda: utils.send_member_state_change_email(
            app_request, member, 'test',
            template_name='member_state_change'))
    assert subject == _fr(app_request, 'email_member_state_changed')
    assert subject == "Changement dans ton profil de membre"


def test_a_pretranslated_plain_subject_is_respected(app_request):
    """The per-verifier senders of #238 pass subjects already translated in
    each verifier's language: a plain str must go through unchanged."""
    member = _member('fr')
    subject = _capture_subject(
        app_request,
        lambda: utils.send_member_state_change_email(
            app_request, member, 'test',
            template_name='member_state_change',
            subject='Already translated'))
    assert subject == 'Already translated'


def test_translate_for_language_still_importable_from_register():
    """#238 compatibility: register keeps exposing the helper."""
    import alirpunkto.views.register as register_module
    assert register_module._translate_for_language is utils._translate_for_language


def test_provider_activation_passes_a_translation_string():
    import alirpunkto.views.manage_provider as manage_provider
    src = inspect.getsource(manage_provider)
    assert "subject=_('provider_role_activated')" in src
