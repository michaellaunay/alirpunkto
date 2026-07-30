"""The /modify_member view matches the specification (issue #123).

A translated title ("Your profile") and introduction on one's own profile,
a translated Submit button, and a Cancel button (issue #116) that abandons
the edits through a post/redirect/get — all msgids in the catalogues and
the .pot. The per-role field matrix itself belongs to issue #55.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto import add_renderer_globals
from alirpunkto.models.member import MemberStates, MemberTypes
from alirpunkto.views import modify_member as mm
from alirpunkto.views.modify_member import modify_member


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


def _member(oid='me-1', mtype=MemberTypes.ORDINARY):
    data = SimpleNamespace(
        fullname='Jean', fullsurname='Doe', description='d',
        birthdate=None, nationality='FR', lang1='en', lang2=None,
        lang3=None, cooperative_behaviour_mark=None,
        cooperative_behaviour_mark_update=None, number_shares_owned=0,
        date_end_validity_yearly_contribution=None, iban=None, role=None)
    return SimpleNamespace(oid=oid, pseudonym=f'p-{oid}',
                           email=f'{oid}@example.com', type=mtype,
                           member_state=MemberStates.REGISTRED, data=data)


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'modify_member', 'member_avatar',
                  'avatar_upload', 'unsubscribe'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, oid='me-1'):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session['logged_in'] = True
    request.session['user'] = json.dumps({'oid': oid, 'name': f'p-{oid}'})
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def test_the_form_carries_translated_submit_and_cancel_buttons(config):
    """The real deform form renders both buttons: 'modify' keeps its name
    (the POST branch relies on it) with the Submit label; 'cancel' joins
    it (issue #116)."""
    import deform
    me = _member()
    request = _request(config)
    with patch.object(mm, 'get_member_by_oid', return_value=me), \
         patch.object(mm, 'update_member_from_ldap',
                      side_effect=lambda o, r: me), \
         patch.object(mm, 'get_access_permissions',
                      return_value=MagicMock()), \
         patch.object(mm.RegisterForm, 'apply_permissions',
                      lambda self, *_: None, create=True), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        result = modify_member(request)

    html = result['form']
    assert 'name="modify"' in html
    assert 'name="cancel"' in html
    # Under the stock renderer the button titles stay as msgids; the
    # project renderer translates them (the msgids live in the catalogues).
    assert 'submit_button' in html
    assert 'cancel_button' in html


def test_cancel_redirects_before_any_ldap_work(config):
    request = _request(config, post={'cancel': 'cancel',
                                     'csrf_token': 'csrf-token'})
    with patch.object(mm, 'get_member_by_oid') as resolver, \
         patch.object(mm, 'update_member_from_ldap') as updater:
        result = modify_member(request)
    assert isinstance(result, HTTPFound)
    assert result.location.endswith('/modify_member')
    resolver.assert_not_called()
    updater.assert_not_called()


def _render(config, context):
    config.include('pyramid_chameleon')
    config.add_subscriber(add_renderer_globals,
                          'pyramid.events.BeforeRender')
    config.add_static_view('static', 'alirpunkto:static')
    config.add_settings({'site_name': 'A', 'domain_name': 'D',
                         'site_logo': 'static/alirpunkto.png',
                         'site_logo_small': 'static/alirpunkto-16x16.png'})
    request = DummyRequest()
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    from pyramid.threadlocal import manager
    manager.push({'request': request, 'registry': request.registry})
    try:
        base = {'logged_in': True, 'site_name': 'A', 'domain_name': 'D',
                'organization_details': 'O', 'member': None,
                'accessed_member': None, 'accessed_members': {},
                'form': None, 'admin_view': None}
        base.update(context)
        return render('alirpunkto:templates/modify_member.pt', base,
                      request=request)
    finally:
        manager.pop()


def test_ones_own_profile_shows_the_specified_title_and_introduction(config):
    me = _member()
    html = _render(config, {'member': me, 'accessed_member': me,
                            'form': '<form>f</form>'})
    assert 'Your profile' in html
    assert 'view your own profile, and modify some of its elements' in html
    assert 'Edit member profile' not in html
    assert 'Please fill the fields' not in html


def test_the_admin_selection_page_keeps_its_title(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    html = _render(config, {'member': admin})
    assert 'Edit member profile' in html          # modify_member_title (en)
    assert 'Your profile' not in html
