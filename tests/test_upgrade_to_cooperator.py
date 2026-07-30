"""Upgrade from Ordinary Member to Cooperator (issue #7).

A button on the home page — Ordinary Members only — leads to a short
identity form; submitting it opens a COOPERATOR candidature carrying the
member's pseudonym and e-mail (never asked again), pre-set to UNIQUE_DATA so
the existing registration flow draws the verifiers and runs the vote; on
approval the LDAP entry is updated in place — no duplicate, same pseudonym.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
import alirpunkto.utils as utils
from alirpunkto import add_localizer, add_renderer_globals
from alirpunkto.constants_and_globals import _, CANDIDATURE_OID
from alirpunkto.models import member as member_module
from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import MemberDatas, MemberTypes
from alirpunkto.views import register as register_view_module
from alirpunkto.views import upgrade_to_cooperator as upgrade_module
from alirpunkto.views.upgrade_to_cooperator import upgrade_to_cooperator


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


class _Candidatures(dict):
    def __init__(self):
        super().__init__()
        self.monitored_members = {}


def _member(member_type=MemberTypes.ORDINARY):
    return SimpleNamespace(
        oid='member-1', email='m@example.com', pseudonym='jdoe',
        type=member_type,
        data=SimpleNamespace(lang1='fr', lang2=None, lang3=None,
                             description='hello'))


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'register', 'upgrade_to_cooperator'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, user=None):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session['logged_in'] = user is not None
    if user is not None:
        request.session['user'] = user
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def test_anonymous_visitors_are_sent_home(config):
    request = _request(config, user=None)
    result = upgrade_to_cooperator(request)
    assert isinstance(result, HTTPFound)
    assert result.location.endswith('/home')


def test_cooperators_cannot_upgrade_again(config):
    request = _request(config, user={'oid': 'member-1', 'type': 'COOPERATOR'})
    with patch.object(upgrade_module, 'get_member_by_oid',
                      return_value=_member(MemberTypes.COOPERATOR)):
        result = upgrade_to_cooperator(request)
    assert result['error'] == _('upgrade_only_ordinary_error')


def test_the_identity_form_is_shown_to_ordinary_members(config):
    import deform
    request = _request(config, user={'oid': 'member-1', 'type': 'ORDINARY'})
    with patch.object(upgrade_module, 'get_member_by_oid',
                      return_value=_member()), \
         patch.object(upgrade_module, 'get_candidatures',
                      return_value=_Candidatures()), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        # Hermetic to the application-wide deform renderer another test may
        # have installed globally (same isolation lesson as issue #171).
        result = upgrade_to_cooperator(request)
    assert result['error'] is None
    for field in ('fullname', 'fullsurname', 'nationality'):
        assert f'name="{field}"' in result['form']
    # deform's date widget renders a peppercorn mapping, not a flat input:
    assert 'item-birthdate' in result['form']
    assert 'name="pseudonym"' not in result['form']   # never asked again


def test_submitting_opens_the_upgrade_candidature(config):
    candidatures = _Candidatures()
    # The date widget submits a peppercorn mapping, exactly as a browser does.
    post = {
        'csrf_token': 'csrf-token',
        'fullname': 'Jean', 'fullsurname': 'Doe',
        '__start__': 'birthdate:mapping',
        'date': '2000-01-01',
        '__end__': 'birthdate:mapping',
        'nationality': 'FR',
        'submit': 'submit',
    }
    request = _request(config, post=post,
                       user={'oid': 'member-1', 'type': 'ORDINARY'})
    with patch.object(upgrade_module, 'get_member_by_oid',
                      return_value=_member()), \
         patch.object(upgrade_module, 'get_candidatures',
                      return_value=candidatures), \
         patch.object(upgrade_module, 'is_valid_unique_identity',
                      return_value=None), \
         patch.object(member_module.Members, 'get_instance',
                      return_value={'members': {}, 'candidatures': {}}):
        result = upgrade_to_cooperator(request)

    assert isinstance(result, HTTPFound)
    assert result.location.endswith('/register')
    assert len(candidatures) == 1
    candidature = next(iter(candidatures.values()))
    assert candidature.type == MemberTypes.COOPERATOR
    assert candidature.candidature_state == CandidatureStates.UNIQUE_DATA
    assert candidature.pseudonym == 'jdoe'
    assert candidature.email == 'm@example.com'
    assert candidature.existing_member_oid == 'member-1'
    assert candidature.data.fullname == 'Jean'
    assert candidature.data.birthdate == date(2000, 1, 1)
    assert candidature.data.lang1 == 'fr'
    assert candidature.data.password == ''
    assert request.session[CANDIDATURE_OID] == candidature.oid
    assert candidatures.monitored_members[candidature.oid] is candidature


def test_a_running_upgrade_is_resumed_not_duplicated(config):
    candidatures = _Candidatures()
    with patch.object(member_module.Members, 'get_instance',
                      return_value={'members': {}, 'candidatures': {}}):
        running = Candidature()
    running.existing_member_oid = 'member-1'
    running.candidature_state = CandidatureStates.PENDING
    candidatures[running.oid] = running

    request = _request(config, user={'oid': 'member-1', 'type': 'ORDINARY'})
    with patch.object(upgrade_module, 'get_member_by_oid',
                      return_value=_member()), \
         patch.object(upgrade_module, 'get_candidatures',
                      return_value=candidatures):
        result = upgrade_to_cooperator(request)

    assert isinstance(result, HTTPFound)
    assert result.location.endswith('/register')
    assert request.session[CANDIDATURE_OID] == running.oid
    assert len(candidatures) == 1                      # no second candidature


def test_the_dispatch_routes_the_upgrade_candidature_to_unique_data(config):
    with patch.object(member_module.Members, 'get_instance',
                      return_value={'members': {}, 'candidatures': {}}):
        candidature = Candidature()
    candidature.candidature_state = CandidatureStates.UNIQUE_DATA
    request = _request(config, user={'oid': 'member-1', 'type': 'ORDINARY'})
    with patch.object(register_view_module, 'handle_unique_data_state',
                      return_value={}) as handler:
        register_view_module._handle_candidature_state(request, candidature)
    handler.assert_called_once()


# ------------------------------- LDAP upgrade ------------------------------ #
def _mock_ldap_with_member(member_oid='member-1'):
    from ldap3 import Connection, Server, MOCK_SYNC, ALL
    from alirpunkto.constants_and_globals import LDAP_BASE_DN, LDAP_OU
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    dn = (f"uid={member_oid},{LDAP_OU},{LDAP_BASE_DN}"
          if LDAP_OU else f"uid={member_oid},{LDAP_BASE_DN}")
    conn.add(dn, attributes={
        'objectClass': ['top', 'inetOrgPerson'],
        'uid': member_oid, 'cn': 'jdoe', 'sn': 'jdoe',
        'mail': 'm@example.com', 'employeeType': 'ORDINARY'})
    group_dn = (f"cn=cooperatorsGroup,{f'{LDAP_OU},' if LDAP_OU else ''}"
                f"{LDAP_BASE_DN}")
    conn.add(group_dn, attributes={
        'objectClass': ['top', 'groupOfUniqueNames'],
        'cn': 'cooperatorsGroup', 'uniqueMember': ['cn=placeholder']})
    return conn, dn


def test_the_ldap_entry_is_updated_in_place_on_approval(config):
    conn, dn = _mock_ldap_with_member()
    with patch.object(member_module.Members, 'get_instance',
                      return_value={'members': {}, 'candidatures': {}}):
        candidature = Candidature()
    candidature.type = MemberTypes.COOPERATOR
    candidature.pseudonym = 'jdoe'
    candidature.email = 'm@example.com'
    candidature.existing_member_oid = 'member-1'
    candidature.data = MemberDatas(
        password='', fullname='Jean', fullsurname='Doe',
        birthdate=date(2000, 1, 1), nationality='FR', lang1='fr')

    request = SimpleNamespace()
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'update_member_from_ldap') as refresh:
        result = utils.register_user_to_ldap(request, candidature, '')

    assert result['status'] == 'success', result
    conn.search(dn, '(objectclass=*)',
                attributes=['employeeType', 'sn', 'gn', 'cn', 'mail'])
    entry = conn.entries[0]
    assert str(entry.employeeType) == 'COOPERATOR'
    assert str(entry.sn) == 'Doe'
    assert str(entry.cn) == 'jdoe'                 # pseudonym untouched
    assert str(entry.mail) == 'm@example.com'      # e-mail untouched
    refresh.assert_called_once_with('member-1', request)


# ------------------------------- the button -------------------------------- #
def _render_home(config, user_type):
    config.include('pyramid_chameleon')
    config.add_subscriber(add_renderer_globals, 'pyramid.events.BeforeRender')
    for route in ('sso_login', 'logout', 'modify_member', 'vote'):
        config.add_route(route, '/' + route)
    config.add_static_view('static', 'alirpunkto:static')
    config.add_settings({'site_name': 'A', 'domain_name': 'D',
                         'site_logo': 'static/alirpunkto.png',
                         'site_logo_small': 'static/alirpunkto-16x16.png'})
    request = DummyRequest()
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    add_localizer(NewRequest(request))
    # pyramid_chameleon's translator resolves the localizer through the
    # request threadlocal — push it, as a real request lifecycle would.
    from pyramid.threadlocal import manager
    manager.push({'request': request, 'registry': request.registry})
    try:
        return render('alirpunkto:templates/home.pt', {
            'logged_in': True, 'site_name': 'A', 'domain_name': 'D',
            'organization_details': 'Org',
            'user': {'name': 'Jean', 'oid': 'member-1', 'type': user_type},
            'applications': {},
        }, request=request)
    finally:
        manager.pop()


def test_the_home_button_shows_only_to_ordinary_members(config):
    html = _render_home(config, 'ORDINARY')
    assert 'Become a Cooperator' in html
    assert '/upgrade_to_cooperator' in html


def test_the_home_button_is_absent_for_cooperators(config):
    html = _render_home(config, 'COOPERATOR')
    assert 'Become a Cooperator' not in html
