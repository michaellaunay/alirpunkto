"""Administrators view a fixed read-only card of other members (issue #149).

Exactly the eight fields the ticket lists — pseudonym, profile text,
avatar, user number, role, Cooperative Behaviour Mark and its last update,
date and reason of departure — and no modification form: viewing never
flips the member's state, never arms the session for a later 'modify'
POST, and a crafted 'modify' POST is refused outright.
"""
from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID, _
from alirpunkto.models.member import MemberRoles, MemberStates, MemberTypes
from alirpunkto.views import modify_member as mm
from alirpunkto.views.modify_member import modify_member


class _StubSchema:
    def apply_permissions(self, *_):
        return None


class _StubForm:
    def __init__(self, *a, **k):
        pass

    def render(self, appstruct=None):
        return "<form>profile</form>"

EIGHT_FIELDS = {
    'oid', 'pseudonym', 'description', 'role_i18n',
    'cooperative_behaviour_mark', 'cooperative_behaviour_mark_update',
    'departure_date', 'departure_reason', 'has_avatar'}


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


def _member(oid='me-1', mtype=MemberTypes.ORDINARY,
            state=MemberStates.REGISTRED, role=None):
    data = SimpleNamespace(
        fullname='Jean', fullsurname='Doe', description='hello world',
        birthdate=None, nationality='FR', lang1='en', lang2=None,
        lang3=None, cooperative_behaviour_mark=4.2,
        cooperative_behaviour_mark_update=datetime(2026, 6, 1, 12, 0),
        number_shares_owned=0,
        date_end_validity_yearly_contribution=None, iban='FR76-SECRET',
        role=role)
    return SimpleNamespace(oid=oid, pseudonym=f'p-{oid}',
                           email=f'{oid}@example.com', type=mtype,
                           member_state=state, data=data)


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'modify_member', 'member_avatar'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, oid='adm-1'):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session['logged_in'] = True
    request.session['user'] = json.dumps({'oid': oid, 'name': f'p-{oid}'})
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def _run(config, accessor, *, post=None, resolved=None, avatar=None):
    resolved = resolved or {accessor.oid: accessor}
    request = _request(config, post=post, oid=accessor.oid)
    with patch.object(mm, 'get_member_by_oid', return_value=accessor), \
         patch.object(mm, 'update_member_from_ldap',
                      side_effect=lambda o, r: resolved.get(o)), \
         patch.object(mm, 'get_ldap_member_list',
                      return_value=[SimpleNamespace(oid=o, name=f'p-{o}')
                                    for o in resolved]), \
         patch.object(mm, 'get_access_permissions',
                      return_value=MagicMock()), \
         patch.object(mm, 'RegisterForm',
                      return_value=SimpleNamespace(
                          bind=lambda **k: _StubSchema())), \
         patch.object(mm.deform, 'Form', _StubForm), \
         patch('alirpunkto.views.avatar.get_member_avatar',
               return_value=avatar):
        result = modify_member(request)
    return result, request


def test_the_admin_sees_the_card_and_no_form(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2', role=MemberRoles.COOPERATOR)
    other.departure_date = datetime(2026, 7, 1)
    other.departure_reason = 'resignation'
    result, request = _run(
        config, admin,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'adm-1': admin, 'other-2': other})

    assert result['form'] is None                     # view, never modify
    card = result['admin_view']
    assert set(card) == EIGHT_FIELDS
    assert card['pseudonym'] == 'p-other-2'
    assert card['description'] == 'hello world'
    assert card['oid'] == 'other-2'
    assert card['role_i18n'] == 'member_roles_cooperator'
    assert card['cooperative_behaviour_mark'] == 4.2
    assert card['departure_reason'] == 'resignation'


def test_nothing_sensitive_leaks_into_the_card(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2')
    result, request = _run(
        config, admin,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'adm-1': admin, 'other-2': other})
    blob = repr(result['admin_view'])
    assert 'FR76-SECRET' not in blob                  # no IBAN
    assert 'other-2@example.com' not in blob          # no e-mail
    assert 'Doe' not in blob                          # no identity data


def test_viewing_neither_flips_state_nor_arms_the_session(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2')
    result, request = _run(
        config, admin,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'adm-1': admin, 'other-2': other})
    assert other.member_state == MemberStates.REGISTRED
    assert ACCESSED_MEMBER_OID not in request.session


def test_a_crafted_modify_post_writes_nothing(config):
    """A 'modify' POST aimed at another member is intercepted by the card
    shunt before any write path: the admin gets the read-only card and the
    member's data is untouched."""
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2')
    request = _request(config, post={'modify': '1', 'description': 'pwned'},
                       oid='adm-1')
    request.session[ACCESSED_MEMBER_OID] = 'other-2'
    with patch.object(mm, 'get_member_by_oid', return_value=admin), \
         patch.object(mm, 'update_member_from_ldap',
                      side_effect=lambda o, r: {'adm-1': admin,
                                                'other-2': other}.get(o)), \
         patch.object(mm, 'get_ldap_member_list',
                      return_value=[SimpleNamespace(oid='other-2',
                                                    name='p-other-2')]), \
         patch.object(mm, 'get_access_permissions',
                      return_value=MagicMock()), \
         patch('alirpunkto.views.avatar.get_member_avatar',
               return_value=None):
        result = modify_member(request)
    assert result['form'] is None
    assert result['admin_view']['oid'] == 'other-2'   # the card, not a form
    assert other.data.description == 'hello world'    # untouched


def test_the_admin_still_edits_their_own_profile(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    result, request = _run(
        config, admin,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'adm-1'})
    assert 'admin_view' not in result
    assert result['form'] is not None                 # the usual form


def test_has_avatar_follows_the_directory(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2')
    for avatar, expected in ((b'\xff\xd8jpeg', True), (None, False)):
        result, request = _run(
            config, admin,
            post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
            resolved={'adm-1': admin, 'other-2': other}, avatar=avatar)
        assert result['admin_view']['has_avatar'] is expected
