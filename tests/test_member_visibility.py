"""Non-admin members only ever see their own profile (issue #201).

The modify_member view used to expose the full member list to every
logged-in member and let them open anyone's profile. Now: administrators
keep the selection flow; everyone else lands straight on their own
profile — the member list is never fetched for them, and any crafted POST
or stale session oid targeting someone else is neutralised. A profile
visit no longer clobbers a running resignation state either.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID
from alirpunkto.models.member import MemberStates, MemberTypes
from alirpunkto.views import modify_member as mm
from alirpunkto.views.modify_member import modify_member


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, message, queue=""):
        self.setdefault('_flash', []).append((queue, message))


def _member(oid='me-1', mtype=MemberTypes.ORDINARY,
            state=MemberStates.REGISTRED):
    data = SimpleNamespace(
        fullname='Jean', fullsurname='Doe', description='d',
        birthdate=None, nationality='FR', lang1='en', lang2=None,
        lang3=None, cooperative_behaviour_mark=None,
        cooperative_behaviour_mark_update=None, number_shares_owned=0,
        date_end_validity_yearly_contribution=None, iban=None)
    return SimpleNamespace(oid=oid, pseudonym=f'p-{oid}',
                           email=f'{oid}@example.com', type=mtype,
                           member_state=state, data=data)


class _StubSchema:
    def apply_permissions(self, *_):
        return None


class _StubForm:
    def __init__(self, *a, **k):
        pass

    def render(self, appstruct=None):
        return "<form>profile</form>"


@pytest.fixture
def config():
    config = setUp(settings={'pyramid.default_locale_name': 'en',
                             'session.secret': 'x' * 32})
    config.add_translation_dirs('alirpunkto:locale/')
    for route in ('home', 'modify_member'):
        config.add_route(route, '/' + route)
    yield config
    tearDown()


def _request(config, *, post=None, session_extra=None, oid='me-1'):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session['logged_in'] = True
    request.session['user'] = json.dumps({'oid': oid, 'name': f'p-{oid}'})
    if session_extra:
        request.session.update(session_extra)
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def _run(config, accessor, *, post=None, session_extra=None,
         resolved=None):
    """Run the view with the harness stubs; `resolved` maps oid → member
    for update_member_from_ldap."""
    resolved = resolved or {accessor.oid: accessor}
    permissions = MagicMock()
    request = _request(config, post=post, session_extra=session_extra,
                       oid=accessor.oid)
    with patch.object(mm, 'get_member_by_oid', return_value=accessor), \
         patch.object(mm, 'update_member_from_ldap',
                      side_effect=lambda o, r: resolved.get(o)), \
         patch.object(mm, 'get_ldap_member_list') as lister, \
         patch.object(mm, 'get_access_permissions',
                      return_value=permissions), \
         patch.object(mm, 'RegisterForm',
                      return_value=SimpleNamespace(
                          bind=lambda **k: _StubSchema())), \
         patch.object(mm.deform, 'Form', _StubForm):
        lister.return_value = [
            SimpleNamespace(oid='me-1', name='p-me-1'),
            SimpleNamespace(oid='other-2', name='p-other-2')]
        result = modify_member(request)
    return result, request, lister


def test_a_plain_get_lands_on_ones_own_profile(config):
    me = _member()
    result, request, lister = _run(config, me)
    assert result['accessed_member'] == 'me-1'
    assert result['form'] == "<form>profile</form>"
    assert result['accessed_members'] == {}


def test_the_member_list_is_never_fetched_for_non_admins(config):
    me = _member()
    result, request, lister = _run(config, me)
    lister.assert_not_called()


def test_a_crafted_post_targeting_another_member_is_neutralised(config):
    """The heart of the ticket: whatever oid the POST carries, a non-admin
    only ever opens their own profile."""
    me = _member()
    other = _member('other-2')
    result, request, lister = _run(
        config, me,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'me-1': me, 'other-2': other})
    assert result['accessed_member'] == 'me-1'


def test_a_stale_session_oid_of_another_member_is_neutralised(config):
    me = _member()
    other = _member('other-2')
    result, request, lister = _run(
        config, me,
        session_extra={ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'me-1': me, 'other-2': other})
    assert result['accessed_member'] == 'me-1'
    assert request.session[ACCESSED_MEMBER_OID] == 'me-1'


def test_admins_keep_the_selection_flow(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    result, request, lister = _run(config, admin)
    lister.assert_called_once()
    assert result['accessed_member'] is None          # the selection page
    assert 'other-2' in result['accessed_members']


def test_admins_still_open_other_profiles(config):
    admin = _member('adm-1', MemberTypes.ADMINISTRATOR)
    other = _member('other-2')
    result, request, lister = _run(
        config, admin,
        post={'submit': '1', ACCESSED_MEMBER_OID: 'other-2'},
        resolved={'adm-1': admin, 'other-2': other})
    assert result['accessed_member'] == 'other-2'


def test_a_profile_visit_does_not_clobber_a_running_resignation(config):
    me = _member(state=MemberStates.PENDING_UNSUBSCRIPTION)
    result, request, lister = _run(config, me)
    assert me.member_state == MemberStates.PENDING_UNSUBSCRIPTION
    assert result['accessed_member'] == 'me-1'
