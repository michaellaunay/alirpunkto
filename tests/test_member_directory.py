"""Issue #249 locks: the member directory and the role-scoped card.

Every logged-in member browses the directory and opens another
member's read-only card; the accessor's role scopes the card's
content (public fields for members, the full card plus the e-mail
address for administrators); selecting oneself still leads to the
edit form; and the wording is neutral — the card never borrows the
edit form's second-person labels.
"""

import json
import re
from types import SimpleNamespace
from unittest.mock import patch

from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.models.member import MemberTypes
from alirpunkto.views import modify_member as mm

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, *args, **kwargs):
        pass


def _member(oid, type_, pseudonym="pseudo", email="m@example.org"):
    return SimpleNamespace(
        oid=oid, pseudonym=pseudonym, email=email, type=type_,
        data=SimpleNamespace(
            description="about me", role=None,
            cooperative_behaviour_mark=0.0,
            cooperative_behaviour_mark_update=None),
        member_state=None,
        departure_date=None, departure_reason=None)


def _request(post=None, accessor_oid="acc-1"):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session["logged_in"] = True
    request.session["user"] = json.dumps({"oid": accessor_oid,
                                          "name": "acc"})
    return request


def _call(accessor, others, post=None):
    listed = [SimpleNamespace(oid=m.oid, name=m.pseudonym)
              for m in [accessor] + others]
    by_oid = {m.oid: m for m in [accessor] + others}
    with patch.object(mm, "get_member_by_oid",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "update_member_from_ldap",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "get_ldap_member_list", return_value=listed):
        config = setUp()
        try:
            return mm.modify_member(_request(post=post,
                                             accessor_oid=accessor.oid))
        finally:
            tearDown()


def test_every_member_sees_the_directory():
    """#249 supersedes #201: a plain GET shows the member list to
    any logged-in member, not only to administrators."""
    accessor = _member("acc-1", MemberTypes.ORDINARY)
    other = _member("mem-2", MemberTypes.COOPERATOR, pseudonym="zorro")
    context = _call(accessor, [other])
    assert isinstance(context, dict)
    assert context["accessed_members"], "the directory must be exposed"
    assert "mem-2" in context["accessed_members"]
    assert not context.get("admin_view")


def test_a_member_opens_a_reduced_public_card():
    accessor = _member("acc-1", MemberTypes.ORDINARY)
    other = _member("mem-2", MemberTypes.COOPERATOR, pseudonym="zorro")
    context = _call(accessor, [other],
                    post={"submit": "submit",
                          "accessed_member_oid": "mem-2"})
    card = context.get("admin_view")
    assert card, "another member's profile must be a read-only card"
    assert set(card) == {"oid", "pseudonym", "cooperative_behaviour_mark",
                         "cooperative_behaviour_mark_update", "has_avatar"}
    assert card["pseudonym"] == "zorro"


def test_an_admin_card_includes_the_email():
    accessor = _member("acc-1", MemberTypes.ADMINISTRATOR)
    other = _member("mem-2", MemberTypes.COOPERATOR,
                    email="zorro@example.org")
    context = _call(accessor, [other],
                    post={"submit": "submit",
                          "accessed_member_oid": "mem-2"})
    card = context.get("admin_view")
    assert card and card["email"] == "zorro@example.org"
    assert "description" in card and "role_i18n" in card


def test_selecting_oneself_never_yields_a_card():
    """One's own profile stays the edit path (no read-only card)."""
    accessor = _member("acc-1", MemberTypes.ORDINARY)
    with patch.object(mm, "get_access_permissions",
                      return_value=None):
        context = _call(accessor, [],
                        post={"submit": "submit",
                              "accessed_member_oid": "acc-1"})
    assert not (isinstance(context, dict) and context.get("admin_view"))


def test_the_wording_is_neutral():
    def msgstr(lang, msgid):
        text = open(os.path.join(
            ROOT, "alirpunkto", "locale", lang, "LC_MESSAGES",
            "alirpunkto.po"), encoding="utf-8").read()
        match = re.search(
            r'^msgid "%s"\nmsgstr "(.*)"$' % re.escape(msgid), text,
            re.M)
        return match.group(1) if match else None

    assert msgstr("en", "modify_member_title") == "Member profile"
    assert msgstr("fr", "modify_member_title") == "Profil du membre"
    assert msgstr("fr", "modify_member") == "Consulter les membres"
    template = open(os.path.join(
        ROOT, "alirpunkto", "templates", "modify_member.pt"),
        encoding="utf-8").read()
    assert "member_card_email_label" in template
    assert "_('pseudonym_label')" not in template, (
        "the card must not borrow the edit form's labels")


def test_the_self_query_opens_ones_own_edit_form():
    """Issue #258: a GET with ?self=1 goes straight to one's own edit
    path (so post-upload flashes land on the profile page, never on
    the directory)."""
    accessor = _member("acc-1", MemberTypes.ORDINARY)
    other = _member("mem-2", MemberTypes.COOPERATOR)
    listed = [SimpleNamespace(oid=m.oid, name=m.pseudonym)
              for m in (accessor, other)]
    by_oid = {m.oid: m for m in (accessor, other)}
    with patch.object(mm, "get_member_by_oid",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "update_member_from_ldap",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "get_ldap_member_list", return_value=listed), \
         patch.object(mm, "get_access_permissions", return_value=None):
        config = setUp()
        try:
            request = _request(accessor_oid="acc-1")
            request.params = {"self": "1"}
            request.method = "GET"
            context = mm.modify_member(request)
        finally:
            tearDown()
    assert not (isinstance(context, dict) and context.get("admin_view"))
    # The edit path was taken (its permission gate answered), not the
    # directory (which would return member=<object> with the list).
    assert context["member"] is None


def test_the_avatar_redirects_target_ones_own_profile():
    source = open(os.path.join(ROOT, "alirpunkto", "views",
                               "avatar.py"), encoding="utf-8").read()
    assert "request.route_url('modify_member')" not in source, (
        "a bare modify_member redirect lands on the directory (#258)")
    assert source.count("_query={'self': '1'}") == 6
