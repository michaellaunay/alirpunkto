"""Transversal audit of 2026-10-24, lot 1 — the three P0 invariants.

A01  A closed account (departure state, or ``isActive`` down in the
     directory) is refused at every door: LDAP login, SSO callback,
     password-reset request, reset link, armed reset session; and the
     home page never re-arms ``logged_in`` from a stray ``user`` key.
A02  The LDAP loader refreshes EVERY attribute the directory owns on a
     cached member — financial facts and isActive included — reads them
     typed, keeps "absent" apart from "empty", and ``get_member_by_oid
     (update=True)`` returns the member it just loaded instead of None.
A03  The public registration form fills a closed list of fields: the
     facts of the Cooperative (shares, mark, activity, role, IBAN…) can
     no longer be seeded from the POST.
"""
from __future__ import annotations

import datetime
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pyramid.testing import DummyRequest, setUp, tearDown
from webob.multidict import MultiDict

import alirpunkto.utils as utils
from alirpunkto.constants_and_globals import (
    DEFAULT_COOPERATIVE_BEHAVIOUR_MARK, LDAP_BASE_DN, LDAP_OU, MEMBER_OID, _,
)
from alirpunkto.models.member import (
    Member, MemberDatas, MemberStates, MemberTypes,
)
from alirpunkto.views import forgot_password as fp
from alirpunkto.views import home as home_mod
from alirpunkto.views import login as lg
from alirpunkto.views import register as reg
from alirpunkto.views import update_contribution as uc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------- helpers ----------------------------------- #
def _dn(oid):
    return f"uid={oid},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU \
        else f"uid={oid},{LDAP_BASE_DN}"


def _directory(oid='coop-1', without=(), **attributes):
    """A mock directory holding one Cooperator entry."""
    from ldap3 import ALL, MOCK_SYNC, Connection, Server
    server = Server('mock', get_info=ALL)
    conn = Connection(server, client_strategy=MOCK_SYNC)
    conn.bind()
    attrs = {
        'objectClass': ['top', 'inetOrgPerson'],
        'uid': oid, 'cn': 'jdoe', 'sn': 'Doe', 'givenName': 'Jean',
        'mail': 'jdoe@example.org', 'employeeType': 'COOPERATOR',
        'preferredLanguage': 'fr',
    }
    attrs.update(attributes)
    for name in without:
        attrs.pop(name, None)
    conn.add(_dn(oid), attributes=attrs)
    return conn


def _cached(oid='coop-1', **data):
    base = dict(password='x', fullname='Jean', fullsurname='Doe',
                number_shares_owned=3, is_active=True, lang1='fr',
                date_end_validity_yearly_contribution=datetime.datetime(
                    2030, 1, 1, 12))
    base.update(data)
    return Member(data=MemberDatas(**base), oid=oid,
                  member_state=MemberStates.REGISTRED,
                  type=MemberTypes.COOPERATOR, email='jdoe@example.org',
                  pseudonym='jdoe')


def _load(conn, members, oid='coop-1'):
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, 'get_members', return_value=members):
        return utils.update_member_from_ldap(oid, SimpleNamespace())


# ================================ A02 ====================================== #
def test_the_loader_refreshes_the_financial_facts_of_a_cached_member():
    """Cache: 3 shares, valid until 2030, active. Directory: 1 share,
    expired, inactive, a mark. The directory wins on every one."""
    conn = _directory(numberSharesOwned='1', isActive='False',
                      dateEndValidityYearlyContribution='2024-01-01T12:00:00',
                      cooperativeBehaviourMark='7.5',
                      cooperativeBehaviourMarkUpdate='2024-02-02T12:00:00',
                      iban='FR76 0000', description='hello')
    cached = _cached()
    member = _load(conn, {'coop-1': cached})
    assert member is cached
    assert member.data.number_shares_owned == 1
    assert isinstance(member.data.number_shares_owned, int)
    assert member.data.is_active is False
    assert member.data.date_end_validity_yearly_contribution == \
        datetime.datetime(2024, 1, 1, 12)
    assert member.data.cooperative_behaviour_mark == 7.5
    assert member.data.cooperative_behaviour_mark_update == \
        datetime.datetime(2024, 2, 2, 12)
    assert member.data.iban == 'FR76 0000'
    assert member.data.description == 'hello'


def test_an_attribute_erased_in_the_directory_clears_the_cache():
    """Absent is not "keep the old value": the directory no longer
    carries the shares nor the validity, so neither does the cache."""
    conn = _directory()                      # no financial attribute at all
    cached = _cached(iban='FR00')
    member = _load(conn, {'coop-1': cached})
    assert member.data.number_shares_owned is None
    assert member.data.date_end_validity_yearly_contribution is None
    assert member.data.iban is None
    assert member.data.is_active is True     # absent isActive: never deactivated
    assert member.data.cooperative_behaviour_mark == \
        DEFAULT_COOPERATIVE_BEHAVIOUR_MARK


def test_an_identity_attribute_the_entry_lacks_is_unknown_not_erased():
    """sn is mandatory in inetOrgPerson: an entry without it is broken,
    and the cached surname stays; an empty language, by contrast, is a
    value the directory carries and the cache follows."""
    conn = _directory(without=('sn',), preferredLanguage='en')
    cached = _cached(fullsurname='Kept', lang1='fr')
    member = _load(conn, {'coop-1': cached})
    assert member.data.fullsurname == 'Kept'
    assert member.data.lang1 == 'en'


def test_zero_and_false_from_the_directory_are_values_not_gaps():
    conn = _directory(numberSharesOwned='0', isActive='False')
    member = _load(conn, {'coop-1': _cached()})
    assert member.data.number_shares_owned == 0
    assert member.data.is_active is False


def test_a_member_created_from_the_directory_carries_the_typed_facts():
    conn = _directory(numberSharesOwned='2', isActive='False')
    members = {}
    member = _load(conn, members)
    assert isinstance(member, Member) and members['coop-1'] is member
    assert member.data.number_shares_owned == 2
    assert member.data.is_active is False
    assert member.data.fullsurname == 'Doe'


def test_get_member_by_oid_with_update_returns_the_freshly_loaded_member():
    """The loader used to be called and its result dropped."""
    conn = _directory(numberSharesOwned='2')
    members = {}
    with patch.object(utils, 'get_ldap_connection', return_value=conn), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, 'get_members', return_value=members):
        member = utils.get_member_by_oid('coop-1', SimpleNamespace(), True)
        again = utils.get_member_by_oid('coop-1', SimpleNamespace(), True)
    assert isinstance(member, Member) and member.oid == 'coop-1'
    assert again is member
    with patch.object(utils, 'get_members', return_value={}):
        assert utils.get_member_by_oid('ghost', SimpleNamespace(), False) is None


def test_update_contribution_compares_with_the_directory_not_the_cache():
    """Cache 3, directory 1, payment says 3: the endpoint must WRITE 3,
    not answer "unchanged" from a stale cache."""
    conn = _directory(numberSharesOwned='1')
    cached = _cached()
    members = {'coop-1': cached}
    request = DummyRequest(post={'oid': 'coop-1', 'number_shares_owned': '3'})
    request.method = 'POST'
    request.session = {'logged_in': True,
                       'user': json.dumps({'oid': 'adm-1', 'name': 'adm'})}
    admin = SimpleNamespace(oid='adm-1', type=MemberTypes.ADMINISTRATOR)
    ldap_write = MagicMock(return_value={'status': 'success',
                                         'groups_sync': 'success',
                                         'keycloak_sync': 'success'})

    def real_loader(oid, req):
        return _load(conn, members, oid)

    with patch.object(uc, 'get_member_by_oid', return_value=admin), \
         patch.object(uc, 'update_member_from_ldap', real_loader), \
         patch.object(uc, 'update_ldap_member', ldap_write), \
         patch('alirpunkto.dynamic_groups.read_member_groups',
               return_value={'cooperatorsGroup'}):
        body = uc.update_contribution(request)
    assert request.response.status_code == 200
    ldap_write.assert_called_once()
    assert ldap_write.call_args.kwargs['fields_to_update'] == [
        'number_shares_owned']
    assert body['updated_fields'] == ['number_shares_owned']
    assert body['number_shares_owned'] == 3
    assert cached.data.number_shares_owned == 3


# ================================ A01 ====================================== #
@pytest.mark.parametrize("state", [MemberStates.UNSUBSCRIBED,
                                   MemberStates.EXCLUDED,
                                   MemberStates.DELETED])
def test_a_departure_state_closes_the_account(state):
    member = SimpleNamespace(member_state=state,
                             data=SimpleNamespace(is_active=True))
    assert utils.is_account_closed(member) is True


def test_an_inactive_directory_flag_closes_the_account():
    member = SimpleNamespace(member_state=MemberStates.REGISTRED,
                             data=SimpleNamespace(is_active=False))
    assert utils.is_account_closed(member) is True
    living = SimpleNamespace(member_state=MemberStates.REGISTRED,
                             data=SimpleNamespace(is_active=True))
    assert utils.is_account_closed(living) is False
    assert utils.is_account_closed(None) is False


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, *args, **kwargs):
        pass


def _ldap_login(member):
    request = DummyRequest(post={"form.submitted": "true",
                                 "username": "p", "password": "x"})
    request.session = _Session()
    request.cookies = {}
    request.accept_language = None
    request.params = dict(request.POST)
    request.headers = {"Accept-Language": "en"}
    with patch.object(lg, "is_admin", return_value=False), \
         patch.object(lg, "get_oid_from_pseudonym", return_value="m-1"), \
         patch.object(lg, "check_password",
                      return_value=SimpleNamespace(
                          oid="m-1", name="p",
                          to_json=lambda: '{"oid": "m-1", "name": "p"}')), \
         patch.object(lg, "update_member_from_ldap", return_value=member), \
         patch.object(lg, "record_failure"), \
         patch.object(lg, "record_success"), \
         patch.object(lg, "get_keycloak_token", return_value=None), \
         patch.object(lg, "remember", return_value=[]):
        config = setUp()
        try:
            config.add_route('home', '/')
            config.add_route('login', '/login')
            return lg.login_view(request), request
        finally:
            tearDown()


def test_ldap_login_refuses_an_account_the_directory_deactivated():
    """A living state but isActive=False: the directory still binds the
    password, AlirPunkto must still say no."""
    member = SimpleNamespace(member_state=MemberStates.REGISTRED, oid="m-1",
                             pseudonym="p", email="e@x",
                             data=SimpleNamespace(is_active=False, lang1="en"))
    context, request = _ldap_login(member)
    assert isinstance(context, dict) and context.get("error")
    assert request.session.get("logged_in") is not True


def _reset_request(pairs, session=None):
    params = MultiDict()
    for key, value in pairs:
        params.add(key, value)
    return SimpleNamespace(
        POST=params, params=params, method="POST",
        url="http://example/forgot_password", tm=MagicMock(),
        session=session if session is not None else {},
        registry=SimpleNamespace(settings={"site_name": "S",
                                           "session.secret": "x" * 32}),
    )


def _closed_member(state=MemberStates.UNSUBSCRIBED, active=False):
    member = MagicMock()
    member.oid = "oid-1"
    member.member_state = state
    member.data.is_active = active
    member.data.lang1 = 'en'
    return member


def test_a_reset_request_never_reopens_a_closed_account(members_mapping):
    """The reset used to overwrite UNSUBSCRIBED with
    DATA_MODIFICATION_REQUESTED and mail a link to the former member."""
    member = _closed_member()
    request = _reset_request([("submit", "1"), ("email", "user@example.org")])
    with patch.object(fp, "_retrieve_member", return_value=(None, None)), \
         patch.object(fp, "is_not_a_valid_email_address", return_value=None), \
         patch.object(fp, "get_member_by_email", return_value=[{"uid": "u1"}]), \
         patch.object(fp, "update_member_from_ldap", return_value=member), \
         patch.object(fp, "get_connection") as connection, \
         patch.object(fp, "send_email_to_member") as mailer:
        result = fp.forgot_password(request)
    assert result["message"] == _("forget_email_sent")        # neutral answer
    assert member.member_state == MemberStates.UNSUBSCRIBED  # untouched
    mailer.assert_not_called()
    connection.assert_not_called()


def test_a_reset_link_of_a_closed_account_is_obsolete():
    member = _closed_member(MemberStates.REGISTRED, active=False)
    request = SimpleNamespace(
        params={"oid": "encrypted"},
        registry=SimpleNamespace(settings={"session.secret": "x" * 32}))
    with patch.object(fp, "decrypt_oid", return_value=("oid-1", "seed")), \
         patch.object(fp, "get_member_by_oid", return_value=member):
        loaded, error = fp._retrieve_member(request)
    assert loaded is None
    assert error["url_obsolete"] is True and error["member"] is None


def test_an_armed_reset_session_dies_with_the_account():
    """The cookie was armed before the member left: the POST must not
    change the password any more, and the session is disarmed."""
    member = _closed_member()
    request = _reset_request(
        [("modify", "1"), ("password", "ValidPass123@"),
         ("password_confirm", "ValidPass123@")],
        session={MEMBER_OID: "oid-1"})
    with patch.object(fp, "_retrieve_member", return_value=(None, None)), \
         patch.object(fp, "get_member_by_oid", return_value=member), \
         patch.object(fp, "update_member_password") as change:
        result = fp.forgot_password(request)
    change.assert_not_called()
    assert MEMBER_OID not in request.session
    assert result.get("message") != _("password_changed")


def test_the_home_page_does_not_rearm_a_half_cleared_session():
    request = DummyRequest()
    request.session = {'user': json.dumps({'oid': 'm-1', 'name': 'p'})}
    request.registry = SimpleNamespace(settings={'applications': {}})
    with patch.object(home_mod, 'filter_applications_for_member') as apps, \
         patch.object(home_mod, 'get_member_by_oid', return_value=None):
        context = home_mod.home_view(request)
    assert context['logged_in'] is False
    assert request.session['logged_in'] is False
    apps.assert_not_called()


def test_the_home_page_still_serves_an_authenticated_session():
    request = DummyRequest()
    request.session = {'logged_in': True,
                       'user': json.dumps({'oid': 'm-1', 'name': 'p'})}
    request.registry = SimpleNamespace(settings={'applications': {}})
    with patch.object(home_mod, 'filter_applications_for_member',
                      return_value=[]) as apps, \
         patch.object(home_mod, 'get_member_by_oid', return_value=None):
        context = home_mod.home_view(request)
    assert context['logged_in'] is True
    apps.assert_called_once()


def test_the_sso_callback_checks_the_departure_states_too():
    source = open(os.path.join(ROOT, 'alirpunkto', 'views', 'sso_login.py'),
                  encoding='utf-8').read()
    i_update = source.index('update_member_from_ldap(oid, request)')
    i_closed = source.index('if is_account_closed(member):')
    i_user = source.index('user = User(')
    assert i_update < i_closed < i_user


# ================================ A03 ====================================== #
def test_the_public_form_cannot_seed_the_facts_of_the_cooperative():
    params = MultiDict([
        ('fullname', 'Jean'), ('fullsurname', 'Doe'), ('nationality', 'FR'),
        ('password', 'Secret123@'), ('password_confirm', 'Secret123@'),
        ('lang1', 'fr'), ('lang2', ''), ('lang3', 'en'),
        ('description', 'hi'),
        # the injection attempt
        ('number_shares_owned', '999'), ('cooperative_behaviour_mark', '100'),
        ('cooperative_behaviour_mark_update', '2026-01-01T12:00:00'),
        ('is_active', 'True'), ('role', 'BOARD'),
        ('date_end_validity_yearly_contribution', '2099-12-31T12:00:00'),
        ('unique_member_of', 'cn=boardMembersGroup'), ('iban', 'FR76'),
        ('date_erasure_all_data', '2000-01-01T12:00:00'),
    ])
    parameters = reg.public_registration_parameters(params)
    assert set(parameters) == {'fullname', 'fullsurname', 'nationality',
                               'password', 'password_confirm', 'lang1',
                               'lang3', 'description'}
    data = MemberDatas(**parameters)
    assert data.number_shares_owned == 0
    assert data.cooperative_behaviour_mark == DEFAULT_COOPERATIVE_BEHAVIOUR_MARK
    assert data.is_active is True
    assert data.role.name == 'NONE'
    assert data.date_end_validity_yearly_contribution is None
    assert data.iban is None and data.unique_member_of == ""


def test_the_registration_view_no_longer_walks_the_model_fields():
    source = open(os.path.join(ROOT, 'alirpunkto', 'views', 'register.py'),
                  encoding='utf-8').read()
    assert 'MemberDatas.__dataclass_fields__' not in source
    assert 'public_registration_parameters(request.params)' in source
    for reserved in ('number_shares_owned', 'cooperative_behaviour_mark',
                     'is_active', 'role', 'iban'):
        assert reserved not in reg.PUBLIC_REGISTRATION_FIELDS


def test_the_cooperator_entry_starts_with_the_system_facts():
    """What register_user_to_ldap writes for a fresh Cooperator comes
    from the model defaults, whatever the POST said."""
    candidature = SimpleNamespace(
        oid='cand-1', pseudonym='newbie', email='n@example.org',
        type=MemberTypes.COOPERATOR, existing_member_oid=None,
        data=MemberDatas(**reg.public_registration_parameters(MultiDict([
            ('fullname', 'A'), ('fullsurname', 'B'), ('nationality', 'FR'),
            ('number_shares_owned', '999'), ('cooperative_behaviour_mark', '100'),
        ])), birthdate=datetime.datetime(1990, 1, 1, 12)))
    captured = {}

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def add(self, dn, attributes=None, **_):
            captured.update(attributes or {})
            return True

        result = {'description': 'success'}

    with patch.object(utils, 'is_valid_unique_pseudonym', return_value=None), \
         patch.object(utils, 'get_ldap_connection', return_value=_Conn()), \
         patch.object(utils, 'get_secret', lambda *_: 's'), \
         patch.object(utils, 'notify_keycloak_of_directory_change',
                      return_value=True), \
         patch('alirpunkto.dynamic_groups.sync_member_groups',
               return_value=set()):
        utils.register_user_to_ldap(SimpleNamespace(), candidature, 'Pw123456@')
    assert captured.get('numberSharesOwned') == 0
    assert captured.get('cooperativeBehaviourMark') == \
        DEFAULT_COOPERATIVE_BEHAVIOUR_MARK
    assert captured.get('isActive') == 'True'
