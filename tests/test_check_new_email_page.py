"""The page following a successful e-mail update (issue #160).

Two defects: the title was the generic home-page welcome, unrelated to
the page, and the body showed the raw variable names — literal
${domain_name} and ${admin_email} — because the native Chameleon i18n
pipeline does not interpolate them. The page now carries a dedicated
success title, renders the body through _() so the site variables are
interpolated, shows the success block only on success, and a neutral
title on the error legs. Both new msgids live in the 33 catalogues and
the .pot.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_renderer_globals
from alirpunkto.constants_and_globals import _

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    yield config
    tearDown()


def _render(config, context, locale='fr'):
    config.include('pyramid_chameleon')
    config.add_subscriber(add_renderer_globals,
                          'pyramid.events.BeforeRender')
    config.add_static_view('static', 'alirpunkto:static')
    config.add_settings({'site_name': 'A', 'domain_name': 'D',
                         'site_logo': 'static/alirpunkto.png',
                         'site_logo_small': 'static/alirpunkto-16x16.png'})
    request = DummyRequest()
    request._LOCALE_ = locale
    request.session = _Session()
    request.accept_language = SimpleNamespace(
        best_match=lambda langs: locale)
    alirpunkto.add_localizer(NewRequest(request))
    from pyramid.threadlocal import manager
    manager.push({'request': request, 'registry': request.registry})
    try:
        base = {'logged_in': False, 'site_name': 'A', 'domain_name': 'D',
                'organization_details': 'O',
                'admin_email': 'admin@example.com'}
        base.update(context)
        return render('alirpunkto:templates/check_new_email.pt', base,
                      request=request)
    finally:
        manager.pop()


def test_success_shows_the_dedicated_title_and_interpolated_variables(config):
    html = _render(config, {'success': _('email_updated')})
    assert 'Bravo ! Tu as mis à jour ton adresse de courriel' in html
    # The variables are interpolated, never shown as code names:
    assert '${domain_name}' not in html
    assert '${admin_email}' not in html
    assert 'admin@example.com' in html
    assert 'communications futures avec D' in html
    # The generic home-page welcome is gone:
    assert 'Bienvenue sur' not in html


def test_the_error_legs_show_a_neutral_title_and_no_success_body(config):
    html = _render(config, {'error': 'boom'})
    assert "Changement d'adresse de courriel" in html
    assert 'Bravo' not in html
    assert 'mise à jour avec succès' not in html
    assert 'boom' in html


def test_both_msgids_exist_in_every_catalogue():
    catalogues = sorted(glob.glob(os.path.join(
        ROOT, 'alirpunkto', 'locale', '*', 'LC_MESSAGES', 'alirpunkto.po')))
    assert len(catalogues) == 33
    pot = open(os.path.join(ROOT, 'alirpunkto', 'locale',
                            'alirpunkto.pot'), encoding='utf-8').read()
    for mid in ('check_new_email_success_title', 'check_new_email_title'):
        missing = [po for po in catalogues
                   if f'msgid "{mid}"'
                   not in open(po, encoding='utf-8').read()]
        assert missing == [], mid
        assert f'msgid "{mid}"' in pot, mid
