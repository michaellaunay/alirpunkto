"""The "Forgot password" view is fully translated (issue #175).

The template already carried i18n msgids for the title and the e-mail
label — both translated across the 33 catalogues by earlier campaigns —
but the instruction msgid existed in no catalogue at all (gettext fell
back to the inline English everywhere), and the deform button was the
auto-capitalised untranslated 'Modify'. The instruction now lives in
every catalogue (French translation, explicit English fallback for the
others, recorded in the .pot), and the button carries the translated
submit_button label while keeping its historical 'modify' name.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_renderer_globals
from alirpunkto.models.member import MemberStates
from alirpunkto.views import forgot_password as fp
from alirpunkto.views.forgot_password import forgot_password

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


def _member(lang1='fr'):
    return SimpleNamespace(
        oid='m-1', pseudonym='p-m-1', email='m@example.com',
        member_state=MemberStates.DATA_MODIFICATION_REQUESTED,
        email_send_status_history=[SimpleNamespace(seed='seed')],
        data=SimpleNamespace(lang1=lang1, lang2=None, lang3=None))


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    yield config
    tearDown()


def test_the_instruction_msgid_exists_in_every_catalogue():
    """The regression that made the ticket: the template referenced a
    msgid no catalogue defined, so gettext showed English everywhere."""
    catalogues = sorted(glob.glob(os.path.join(
        ROOT, 'alirpunkto', 'locale', '*', 'LC_MESSAGES', 'alirpunkto.po')))
    assert len(catalogues) == 33
    missing = [po for po in catalogues
               if 'msgid "forgot_password_fill_form"'
               not in open(po, encoding='utf-8').read()]
    assert missing == []
    pot = open(os.path.join(ROOT, 'alirpunkto', 'locale',
                            'alirpunkto.pot'), encoding='utf-8').read()
    assert 'msgid "forgot_password_fill_form"' in pot


def test_the_change_password_screen_renders_in_french(config):
    import deform
    member = _member('fr')
    request = DummyRequest(params={'oid': 'encrypted'})
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    config.include('pyramid_chameleon')
    config.add_subscriber(add_renderer_globals,
                          'pyramid.events.BeforeRender')
    config.add_static_view('static', 'alirpunkto:static')
    config.add_settings({'site_name': 'A', 'domain_name': 'D',
                         'site_logo': 'static/alirpunkto.png',
                         'site_logo_small': 'static/alirpunkto-16x16.png'})
    with patch.object(fp, 'decrypt_oid', return_value=('m-1', 'seed')), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        context = forgot_password(request)

    from pyramid.threadlocal import manager
    manager.push({'request': request, 'registry': request.registry})
    try:
        base = {'logged_in': False, 'site_name': 'A', 'domain_name': 'D',
                'organization_details': 'O', 'member': context['member'],
                'form': context['form']}
        html = render('alirpunkto:templates/forgot_password.pt', base,
                      request=request)
    finally:
        manager.pop()

    # The member's language (issue #248) and the translated instruction:
    assert 'As-tu oublié ton mot de passe' in html
    assert 'Choisis ton nouveau mot de passe ci-dessous.' in html
    assert 'Please fill the fields' not in html


def test_the_button_carries_the_translated_label(config):
    import deform
    member = _member('fr')
    request = DummyRequest(params={'oid': 'encrypted'})
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    with patch.object(fp, 'decrypt_oid', return_value=('m-1', 'seed')), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        result = forgot_password(request)
    html = result['form']
    assert 'name="modify"' in html          # the POST branch relies on it
    assert 'submit_button' in html          # msgid under the stock renderer
    assert '>Modify<' not in html
