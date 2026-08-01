"""The "Change password" view speaks the member's language (issue #248).

The bearer of the e-mailed reset link IS the member: the view switches the
request to their preferred language (lang1) through the issue #247
machinery, whatever the browser says. The anonymous request leg — anyone
can type any e-mail address — deliberately never switches: a language
change there would betray whether the address exists.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyramid.events import NewRequest
from pyramid.testing import DummyRequest, setUp, tearDown

import alirpunkto
from alirpunkto.models.member import MemberStates
from alirpunkto.views import forgot_password as fp
from alirpunkto.views.forgot_password import forgot_password


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


def _request(config, *, post=None, params=None):
    request = DummyRequest(post=post or {}, params=params or post or {})
    request.session = _Session()
    request.accept_language = SimpleNamespace(best_match=lambda langs: 'en')
    alirpunkto.add_localizer(NewRequest(request))
    return request


def test_the_link_bearer_gets_the_view_in_their_language(config):
    import deform
    member = _member('fr')
    request = _request(config, params={'oid': 'encrypted'})
    with patch.object(fp, 'decrypt_oid', return_value=('m-1', 'seed')), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        result = forgot_password(request)

    assert request._LOCALE_ == 'fr'
    assert request.localizer.locale_name == 'fr'
    assert result['form']                       # the change-password form


def test_an_absent_preference_changes_nothing(config):
    import deform
    member = _member(lang1=None)
    request = _request(config, params={'oid': 'encrypted'})
    with patch.object(fp, 'decrypt_oid', return_value=('m-1', 'seed')), \
         patch.object(fp, 'get_member_by_oid', return_value=member), \
         patch.object(deform.form.Form, 'default_renderer',
                      deform.template.default_renderer):
        forgot_password(request)
    assert '_LOCALE_' not in request.__dict__


def test_the_anonymous_request_leg_never_switches(config):
    """Anyone can type any address: a language switch would betray that
    the account exists. The response stays in the browser's language."""
    member = _member('fr')
    request = _request(config, post={'submit': '1',
                                     'email': 'm@example.com',
                                     'csrf_token': 'csrf-token'})
    from unittest.mock import MagicMock
    member.add_email_send_status = lambda *a, **k: None
    zodb = MagicMock()
    zodb.root.return_value = {}
    with patch.object(fp, 'get_member_by_email',
                      return_value=[{'uid': 'm-1'}]), \
         patch.object(fp, 'update_member_from_ldap', return_value=member), \
         patch.object(fp, 'get_connection', return_value=zodb), \
         patch.object(fp, 'send_member_email_forgot_password',
                      return_value={'success': True}, create=True), \
         patch.object(fp, 'send_email_to_member',
                      return_value={'success': True}, create=True):
        result = forgot_password(request)

    assert '_LOCALE_' not in request.__dict__
    assert request.localizer.locale_name == 'en'
