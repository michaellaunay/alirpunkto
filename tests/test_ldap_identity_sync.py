"""The family name follows the directory (production bug, 2026-09-01).

update_member_from_ldap read givenName but never sn: a member created
from the directory — every member of a ZODB rebuilt from LDAP — got
their given name as surname, and the profile view showed the first name
under "Family name". sn is now read, used at creation and synchronised
at update, so each member heals at their next login (the login view
forces this update). The French labels and descriptions of both fields,
empty until now, are filled in both catalogues.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from alirpunkto import utils
from alirpunkto.models.member import Member, MemberDatas, MemberTypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OID = "2dc94f27-a8b8-4aec-8560-c8006e2b72a3"


def _v(value):
    return SimpleNamespace(value=value)


def _entry(sn="Launay", given="Michaël"):
    """The production entry, attributes present exactly as in the LDIF."""
    return SimpleNamespace(
        uid=_v(OID), cn=_v("Scilovema"), sn=_v(sn), givenName=_v(given),
        mail=_v("m@example.coop"), employeeType=_v("COOPERATOR"),
        isActive=_v("TRUE"), nationality=_v("FR"),
        preferredLanguage=_v("fr"),
    )


def _conn(entry):
    conn = MagicMock()
    conn.search.return_value = True
    conn.entries = [entry]
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _sync(entry, existing=None):
    appended = []
    with patch.object(utils, "get_ldap_connection", return_value=_conn(entry)), \
         patch.object(utils, "get_secret", return_value="x"), \
         patch.object(utils, "get_member_by_oid", return_value=existing), \
         patch.object(utils, "append_member",
                      side_effect=lambda m, r: appended.append(m)):
        result = utils.update_member_from_ldap(OID, MagicMock())
    return result, appended


def test_a_member_created_from_the_directory_gets_the_real_surname():
    member, appended = _sync(_entry())
    assert member.data.fullname == "Michaël"
    assert member.data.fullsurname == "Launay"      # was "Michaël"
    assert appended == [member]


def test_an_existing_member_heals_at_the_next_login():
    """The rebuilt-ZODB case: surname wrongly holding the given name."""
    stale = Member(email="m@example.coop", pseudonym="Scilovema", oid=OID,
                   type=MemberTypes.COOPERATOR,
                   data=MemberDatas(fullname="Michaël",
                                    fullsurname="Michaël"))
    member, appended = _sync(_entry(), existing=stale)
    assert member is stale
    assert member.data.fullsurname == "Launay"
    assert appended == []                             # updated, not recreated


def test_a_directory_without_sn_leaves_the_surname_alone():
    entry = _entry()
    del entry.sn
    stale = Member(email="m@example.coop", pseudonym="Scilovema", oid=OID,
                   type=MemberTypes.COOPERATOR,
                   data=MemberDatas(fullname="Michaël", fullsurname="Kept"))
    member, _ = _sync(entry, existing=stale)
    assert member.data.fullsurname == "Kept"


def test_the_identity_labels_are_translated_in_french_and_english():
    for lang in ("fr", "en"):
        po = open(os.path.join(ROOT, "alirpunkto", "locale", lang,
                               "LC_MESSAGES", "alirpunkto.po"),
                  encoding="utf-8").read()
        for msgid in ("full_name_as_in_id_label",
                      "full_surname_as_in_id_label",
                      "full_name_as_in_id_description",
                      "full_surname_as_in_id_description"):
            block = po.split(f'msgid "{msgid}"\n', 1)[1].split("\n", 1)[0]
            assert block != 'msgstr ""', (lang, msgid)
    fr = open(os.path.join(ROOT, "alirpunkto", "locale", "fr",
                           "LC_MESSAGES", "alirpunkto.po"),
              encoding="utf-8").read()
    assert "Nom(s) de famille" in fr and "Prénom(s)" in fr
