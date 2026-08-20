"""Locks for tickets #253 (reopened), #264 and #265."""

import os
from types import SimpleNamespace
from unittest.mock import patch

from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.models.member import MemberStates
from alirpunkto.views import login as lg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, *args, **kwargs):
        pass


def _login(state):
    member = SimpleNamespace(member_state=state, oid="m-1",
                             pseudonym="p", email="e@x",
                             data=SimpleNamespace(lang1="en", lang2=None,
                                                  lang3=None))
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
         patch.object(lg, "update_member_from_ldap",
                      return_value=member), \
         patch.object(lg, "record_failure"), \
         patch.object(lg, "record_success"), \
         patch.object(lg, "remember", return_value=[]):
        config = setUp()
        try:
            config.add_route('home', '/')
            config.add_route('login', '/login')
            return lg.login_view(request), request
        finally:
            tearDown()


def test_265_departure_states_cannot_log_in():
    for state in (MemberStates.UNSUBSCRIBED, MemberStates.EXCLUDED,
                  MemberStates.DELETED):
        context, request = _login(state)
        assert isinstance(context, dict) and context.get("error"), state
        assert request.session.get("logged_in") is not True


def test_265_living_states_still_log_in():
    context, request = _login(MemberStates.REGISTRED)
    assert not (isinstance(context, dict) and context.get("error"))


def test_264_the_role_derives_from_the_type():
    source = open(os.path.join(ROOT, "alirpunkto", "utils.py"),
                  encoding="utf-8").read()
    assert "MemberTypes.ORDINARY: MemberRoles.ORDINARY" in source
    assert "MemberTypes.COOPERATOR: MemberRoles.COOPERATOR" in source
    assert "role=derived_role" in source


def test_253_the_email_and_screen_are_quarantine_conditional():
    view = open(os.path.join(ROOT, "alirpunkto", "views",
                             "unsubscribe.py"), encoding="utf-8").read()
    assert "'show_quarantine': _show_quarantine(request)})" in view
    assert view.count("return False") >= 2
    for lang in ("en", "fr"):
        template = open(os.path.join(
            ROOT, "alirpunkto", "locale", lang, "LC_MESSAGES",
            "unsubscribe_confirmation_email.pt"), encoding="utf-8").read()
        assert 'tal:condition="show_quarantine | nothing"' in template
