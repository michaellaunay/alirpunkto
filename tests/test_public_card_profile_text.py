"""The public member card carries the profile text and the avatar
(issue #270).

The card another member sees showed the pseudonym, the role, the
Cooperative Behaviour Mark and its date — "nothing very personal". The
self-declared profile text and the avatar now join them, so the reader
gets an idea of who the person is. The e-mail address and the user number
stay on the administrator's card only.
"""
from __future__ import annotations

import os
import re

from tests.test_member_visibility import _call, _member
from alirpunkto.models.member import MemberTypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'alirpunkto', 'templates', 'modify_member.pt')


def test_the_public_card_carries_the_profile_text_and_the_avatar_flag():
    accessor = _member("me-1")
    other = _member("other-2", MemberTypes.COOPERATOR)
    context, _ = _call(accessor, [other],
                       post={"submit": "submit",
                             "accessed_member_oid": "other-2"})
    card = context["admin_view"]
    assert card["description"] == "hello"
    assert "has_avatar" in card
    assert "email" not in card and "oid" in card   # oid feeds the avatar URL


def test_the_template_shows_the_profile_text_on_every_card():
    with open(TEMPLATE, encoding='utf-8') as f:
        source = f.read()
    card = source[source.index('admin-member-card'):]
    description = card.index("member_card_description_label")
    admin_only = card.index("<tal:full condition=\"python: 'email' in admin_view\">")
    assert description < admin_only, \
        "the profile text must not sit inside the administrator-only block"
    assert "admin_view.get('description')" in card
    # The avatar row never depended on the card's audience.
    assert re.search(r"<img tal:condition=\"python: admin_view\['has_avatar'\]\"",
                     card)
