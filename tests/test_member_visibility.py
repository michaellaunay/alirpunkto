"""Member visibility under issue #249 (supersedes the #201 locks).

Every logged-in member browses the directory; another member's
profile is only ever a read-only card scoped by the accessor's role
— never the edit form, and never the sensitive fields for
non-administrators. A profile visit still never clobbers a running
resignation.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.constants_and_globals import ACCESSED_MEMBER_OID
from alirpunkto.models.member import MemberStates, MemberTypes
from alirpunkto.views import modify_member as mm


class _Session(dict):
    def get_csrf_token(self):
        return "csrf-token"

    def flash(self, *args, **kwargs):
        pass


def _member(oid, type_=MemberTypes.ORDINARY, state=None):
    return SimpleNamespace(
        oid=oid, pseudonym=f"p-{oid}", email=f"{oid}@example.com",
        type=type_,
        data=SimpleNamespace(
            description="hello", role=None,
            cooperative_behaviour_mark=1.0,
            cooperative_behaviour_mark_update=None),
        member_state=state,
        departure_date=None, departure_reason=None)


def _request(post=None, oid="me-1", session_extra=None):
    request = DummyRequest(post=post or {})
    request.session = _Session()
    request.session["logged_in"] = True
    request.session["user"] = json.dumps({"oid": oid, "name": oid})
    if session_extra:
        request.session.update(session_extra)
    return request


def _call(accessor, others, post=None, session_extra=None,
          expose_list=True):
    listed = ([SimpleNamespace(oid=m.oid, name=m.pseudonym)
               for m in [accessor] + others] if expose_list else [])
    by_oid = {m.oid: m for m in [accessor] + others}
    with patch.object(mm, "get_member_by_oid",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "update_member_from_ldap",
                      side_effect=lambda oid, *a, **k: by_oid.get(oid)), \
         patch.object(mm, "get_ldap_member_list",
                      return_value=listed) as lister:
        setUp()
        try:
            result = mm.modify_member(
                _request(post=post, oid=accessor.oid,
                         session_extra=session_extra))
        finally:
            tearDown()
    return result, lister


def test_a_plain_get_shows_the_directory():
    accessor = _member("me-1")
    other = _member("other-2", MemberTypes.COOPERATOR)
    context, _ = _call(accessor, [other])
    assert context["form"] is None
    assert "other-2" in context["accessed_members"]


def test_the_directory_is_fetched_for_every_member():
    accessor = _member("me-1")
    _, lister = _call(accessor, [])
    lister.assert_called_once()


def test_targeting_another_member_yields_the_public_card_only():
    """A crafted POST at someone else's oid never reaches the edit
    form nor the sensitive fields — it lands on the reduced card."""
    accessor = _member("me-1")
    other = _member("other-2", MemberTypes.COOPERATOR)
    context, _ = _call(accessor, [other],
                       post={"submit": "submit",
                             "accessed_member_oid": "other-2"})
    assert context["form"] is None
    card = context["admin_view"]
    assert "email" not in card and "description" not in card
    assert card["pseudonym"] == "p-other-2"


def test_a_stale_session_oid_yields_the_card_not_the_form():
    accessor = _member("me-1")
    other = _member("other-2", MemberTypes.COOPERATOR)
    context, _ = _call(accessor, [other],
                       post={"modify": "modify"},
                       session_extra={ACCESSED_MEMBER_OID: "other-2"})
    assert context["form"] is None
    assert context.get("admin_view", {}).get("pseudonym") == "p-other-2"


def test_a_profile_visit_does_not_clobber_a_running_resignation():
    accessor = _member(
        "me-1", state=MemberStates.PENDING_UNSUBSCRIPTION)
    with patch.object(mm, "get_access_permissions", return_value=None):
        context, _ = _call(accessor, [],
                           post={"submit": "submit",
                                 "accessed_member_oid": "me-1"})
    assert accessor.member_state == MemberStates.PENDING_UNSUBSCRIPTION
