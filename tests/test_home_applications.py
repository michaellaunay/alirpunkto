"""The application list of the home page (issues #35, #142).

Each application of the settings catalog may declare an audience — all
(default), ordinary or cooperator — so the presentation portal carries a
different description per membership type and the democratic platforms only
show to Cooperators; an application without a configured URL (e.g. an SSO
connection not implemented yet) is hidden. The names and descriptions are
translation msgids equal to their English text, so untranslated languages
fall back to English instead of a bare key.
"""
from __future__ import annotations

import configparser
import os
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.utils as utils
from alirpunkto import add_localizer, add_renderer_globals
from alirpunkto.constants_and_globals import _
from alirpunkto.models.member import MemberTypes
from alirpunkto.utils import filter_applications_for_member

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATALOG = {
    'workspace': {'url': 'https://w/sso', 'audience': 'all',
                  'name': 'Our collaborative workspace', 'logo_file': 'x'},
    'trainings': {'url': 'https://t/login', 'audience': 'all',
                  'name': 'Our on-line trainings', 'logo_file': 'x'},
    'portal_ordinary': {'url': 'https://p/login', 'audience': 'ordinary',
                        'name': 'Our presentation portal', 'logo_file': 'x'},
    'portal_cooperator': {'url': 'https://p/login', 'audience': 'cooperator',
                          'name': 'Our presentation portal', 'logo_file': 'x'},
    'mailing_lists': {'url': 'https://l/', 'audience': 'all',
                      'name': 'Our mailing lists', 'logo_file': 'x'},
    'deliberative': {'url': '', 'audience': 'cooperator',
                     'name': 'Our deliberative democracy platform',
                     'logo_file': 'x'},
    'democratic_control': {'url': 'https://d/', 'audience': 'cooperator',
                           'name': 'Our democratic control platform',
                           'logo_file': 'x'},
}


def _request(oid='m-1'):
    return SimpleNamespace(session={'user': {'oid': oid} if oid else None})


def _member(member_type):
    return SimpleNamespace(type=member_type)


def _filtered(member_type, catalog=None, oid='m-1'):
    request = _request(oid)
    with patch.object(utils, 'get_member_by_oid',
                      return_value=_member(member_type)):
        return filter_applications_for_member(request, catalog or CATALOG)


def test_an_ordinary_member_sees_the_ordinary_catalog():
    assert set(_filtered(MemberTypes.ORDINARY)) == {
        'workspace', 'trainings', 'portal_ordinary', 'mailing_lists'}


def test_a_cooperator_sees_the_democratic_platforms():
    assert set(_filtered(MemberTypes.COOPERATOR)) == {
        'workspace', 'trainings', 'portal_cooperator', 'mailing_lists',
        'democratic_control'}


def test_an_administrator_gets_the_cooperator_view():
    assert 'portal_cooperator' in _filtered(MemberTypes.ADMINISTRATOR)


def test_an_unresolved_member_gets_the_ordinary_view():
    request = _request()
    with patch.object(utils, 'get_member_by_oid',
                      side_effect=RuntimeError("down")):
        result = filter_applications_for_member(request, CATALOG)
    assert set(result) == {
        'workspace', 'trainings', 'portal_ordinary', 'mailing_lists'}


def test_an_application_without_url_is_hidden_until_configured():
    assert 'deliberative' not in _filtered(MemberTypes.COOPERATOR)
    catalog = {**CATALOG,
               'deliberative': {**CATALOG['deliberative'], 'url': 'https://k/'}}
    assert 'deliberative' in _filtered(MemberTypes.COOPERATOR, catalog)


def test_the_audience_defaults_to_all():
    catalog = {'plain': {'url': 'https://x/', 'name': 'X', 'logo_file': 'x'}}
    assert 'plain' in _filtered(MemberTypes.ORDINARY, catalog)


# ------------------------- the repository catalogs ------------------------- #
@pytest.mark.parametrize("ini", ["production.ini", "development.ini"])
def test_the_repository_catalog_is_well_formed(ini):
    text = open(os.path.join(ROOT, ini), encoding='utf-8').read()
    assert not re.findall(r'^pplications\.', text, re.M)   # the lost-prefix typo
    apps = {}
    for m in re.finditer(r'^applications\.(\w+)\.(\w+) = ?(.*)$', text, re.M):
        apps.setdefault(m.group(1), {})[m.group(2)] = m.group(3)
    assert len(apps) == 7
    for app_id, app in apps.items():
        assert app.get('audience') in ('all', 'ordinary', 'cooperator'), app_id
        assert 'name' in app and 'logo_file' in app and 'url' in app, app_id
    assert apps['deliberative']['url'] == ''            # hidden until SSO-ready
    assert '/apps/sociallogin/custom_oidc/' in apps['workspace']['url']


# ---------------------------------- i18n ----------------------------------- #
@pytest.fixture
def localizer_for():
    config = setUp(settings={'pyramid.default_locale_name': 'en'})
    config.add_translation_dirs('alirpunkto:locale/')

    def _for(lang):
        request = DummyRequest()
        request._LOCALE_ = lang
        alirpunkto.add_localizer(NewRequest(request))
        return request.localizer

    yield _for
    tearDown()


def test_the_names_are_translated_in_french(localizer_for):
    assert localizer_for('fr').translate(_('Our collaborative workspace')) \
        == "Notre espace de travail collaboratif"


def test_untranslated_languages_fall_back_to_english(localizer_for):
    assert localizer_for('de').translate(_('Our collaborative workspace')) \
        == "Our collaborative workspace"


# ------------------------------ real rendering ----------------------------- #
def test_the_home_page_renders_the_filtered_catalog():
    config = setUp(settings={
        'pyramid.default_locale_name': 'en',
        'session.secret': 'x' * 32,
        'site_name': 'Access', 'domain_name': 'D',
        'site_logo': 'static/alirpunkto.png',
        'site_logo_small': 'static/alirpunkto-16x16.png',
    })
    config.include('pyramid_chameleon')
    config.add_translation_dirs('alirpunkto:locale/')
    config.add_subscriber(add_renderer_globals, 'pyramid.events.BeforeRender')
    for route in ('home', 'sso_login', 'register', 'logout',
                  'modify_member', 'vote', 'upgrade_to_cooperator'):
        config.add_route(route, '/' + route)
    config.add_static_view('static', 'alirpunkto:static')
    request = DummyRequest()
    request._LOCALE_ = 'fr'
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'fr')
    add_localizer(NewRequest(request))
    try:
        html = render('alirpunkto:templates/home.pt', {
            'logged_in': True, 'site_name': 'Access', 'domain_name': 'D',
            'organization_details': 'Org', 'user': {'name': 'Jean', 'oid': 'm-1', 'type': 'ORDINARY'},
            'applications': {
                'workspace': {'url': 'https://w/apps/sso/x',
                              'name': 'Our collaborative workspace',
                              'logo_file': 'static/alirpunkto.png'},
            },
        }, request=request)
    finally:
        tearDown()
    assert 'https://w/apps/sso/x' in html
    assert 'Notre espace de travail collaboratif' in html
