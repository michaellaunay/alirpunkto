"""Tests for security finding 1.3 — passwords are hashed, never cleartext.

Covers the four layers of the fix:

* the hashing helpers (``make_ldap_password`` / ``is_hashed_password`` /
  ``secure_password_fields``) — {SSHA} format, slappasswd-compatible
  verification, salting, idempotence;
* ``register_user_to_ldap`` — the LDAP ``add`` carries an ``{SSHA}`` hash that
  verifies the original password (so the bind-based login keeps working), and
  on success the ZODB copies (``data.password`` **and** ``data.password_confirm``)
  are purged; on failure they are kept so the approval can be retried;
* ``update_member_password`` — the ``MODIFY_REPLACE`` carries a hash;
* the data-migration tooling — ``tools/purge_zodb_cleartext_passwords.py``
  (settled entries cleared, pending candidatures hashed in place, dry-run
  mutates nothing) and ``docker/migrate_ldap_legacy.py`` (cleartext
  ``userPassword`` values in a legacy LDIF come out hashed).

The LDAP layer is mocked; what slapd itself does with an ``{SSHA}`` value at
bind time is covered by the post-migration runbook, not by this suite.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import sys
from unittest.mock import MagicMock, patch

import pytest

import alirpunkto.utils as utils
from alirpunkto import secret_manager as sm
from alirpunkto.constants_and_globals import (
    ADMIN_PASSWORD,
    LDAP_PASSWORD,
    MAIL_PASSWORD,
    SECRET_KEY,
)
from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import Member, MemberDatas, Members, MemberTypes
from alirpunkto.secret_manager import is_hashed_password, make_ldap_password

CLEAR = "S3cret!pw-1.3"


# --------------------------------------------------------------------------- #
# fixtures & helpers
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _secrets_env(monkeypatch):
    """Provide the secrets ``get_secret`` needs, with a fresh cache."""
    for name, value in (
        (SECRET_KEY, "dGVzdF9zZWNyZXRfa2V5XzEuMw=="),
        (LDAP_PASSWORD, "test-ldap-pw"),
        (ADMIN_PASSWORD, "test-admin-pw"),
        (MAIL_PASSWORD, "test-mail-pw"),
    ):
        monkeypatch.setenv(name, value)
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")
    # ``Candidature()`` draws a unique oid against the Members singleton, which
    # the shared ``reset_model_singletons`` fixture has just cleared: give it an
    # in-memory mapping (the teardown below and in conftest clears it again).
    Members._instance = Members()
    yield
    Members._instance = None
    if hasattr(sm.get_secret, "secrets"):
        delattr(sm.get_secret, "secrets")


def _ssha_verifies(value: str, cleartext: str) -> bool:
    """Recompute the salted SHA-1 exactly as slapd does at bind time."""
    assert value.startswith("{SSHA}")
    raw = base64.b64decode(value[len("{SSHA}"):])
    digest, salt = raw[:20], raw[20:]
    return hashlib.sha1(cleartext.encode("utf-8") + salt).digest() == digest


def _ldap_conn(add_ok: bool = True):
    """A mocked ldap3 connection plus a patcher for ``utils.get_ldap_connection``."""
    conn = MagicMock()
    conn.entries = []                       # pseudonym-uniqueness search: free
    conn.add.return_value = add_ok
    conn.modify.return_value = True
    conn.result = {"description": "success" if add_ok else "error"}
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    patcher = patch.object(utils, "get_ldap_connection", return_value=cm)
    return patcher, conn


def _candidature(password: str = CLEAR) -> Candidature:
    candidature = Candidature()
    candidature.pseudonym = "aliceTest01"
    candidature.email = "alice@example.org"
    candidature.type = MemberTypes.ORDINARY
    candidature.data = MemberDatas(
        password=password, password_confirm=password, lang1="en",
    )
    return candidature


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves string annotations through sys.modules[__module__];
    # register the module first or ``@dataclass`` raises AttributeError.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


# --------------------------------------------------------------------------- #
# hashing helpers
# --------------------------------------------------------------------------- #
def test_make_ldap_password_is_slappasswd_compatible_ssha():
    hashed = make_ldap_password(CLEAR)
    assert hashed.startswith("{SSHA}")
    assert hashed != CLEAR
    assert _ssha_verifies(hashed, CLEAR)
    assert not _ssha_verifies(hashed, "wrong-password")


def test_make_ldap_password_salts_and_is_idempotent():
    first, second = make_ldap_password(CLEAR), make_ldap_password(CLEAR)
    assert first != second                    # fresh salt every time
    assert make_ldap_password(first) == first  # already hashed: untouched


@pytest.mark.parametrize("value,expected", [
    ("{SSHA}abc", True),
    ("{ssha}abc", True),
    ("{PBKDF2-SHA512}1000$x$y", True),
    ("{CRYPT}$6$salt$digest", True),
    ("cleartext", False),
    ("", False),
    (None, False),
])
def test_is_hashed_password(value, expected):
    assert is_hashed_password(value) is expected


def test_secure_password_fields_hashes_and_drops_confirm():
    parameters = {"password": CLEAR, "password_confirm": CLEAR, "fullname": "A"}
    out = utils.secure_password_fields(parameters)
    assert _ssha_verifies(out["password"], CLEAR)
    assert out["password_confirm"] is None
    assert out["fullname"] == "A"             # other fields untouched
    # idempotent: a second pass changes nothing
    hashed = out["password"]
    assert utils.secure_password_fields(out)["password"] == hashed
    # tolerant of absent/empty fields
    assert utils.secure_password_fields({}) == {}
    assert utils.secure_password_fields({"password": None})["password"] is None


# --------------------------------------------------------------------------- #
# register_user_to_ldap — hash in LDAP, purge in ZODB
# --------------------------------------------------------------------------- #
def test_register_sends_hash_to_ldap_and_purges_zodb_copies():
    candidature = _candidature()
    patcher, conn = _ldap_conn(add_ok=True)
    with patcher:
        result = utils.register_user_to_ldap(MagicMock(), candidature, CLEAR)

    assert result["status"] == "success"
    conn.add.assert_called_once()
    attributes = conn.add.call_args.kwargs["attributes"]
    stored = attributes["userPassword"]
    assert stored.startswith("{SSHA}") and stored != CLEAR
    assert _ssha_verifies(stored, CLEAR)      # the bind will still succeed
    # once the LDAP account exists, nothing credential-shaped stays in ZODB
    assert candidature.data.password is None
    assert candidature.data.password_confirm is None


def test_register_failure_keeps_zodb_password_for_retry():
    candidature = _candidature()
    patcher, conn = _ldap_conn(add_ok=False)
    with patcher:
        result = utils.register_user_to_ldap(MagicMock(), candidature, CLEAR)

    assert result["status"] == "error"
    assert candidature.data.password == CLEAR
    assert candidature.data.password_confirm == CLEAR


def test_register_passes_prehashed_password_through_unchanged():
    """vote.py forwards the {SSHA} value stored at registration time."""
    prehashed = make_ldap_password(CLEAR)
    candidature = _candidature(password=prehashed)
    patcher, conn = _ldap_conn(add_ok=True)
    with patcher:
        utils.register_user_to_ldap(MagicMock(), candidature, prehashed)
    assert conn.add.call_args.kwargs["attributes"]["userPassword"] == prehashed


def test_update_member_password_sends_hash():
    from ldap3 import MODIFY_REPLACE

    patcher, conn = _ldap_conn()
    with patcher:
        result = utils.update_member_password(MagicMock(), "oid-1", CLEAR)

    assert result["status"] == "success"
    _, changes = conn.modify.call_args.args
    operation, values = changes["userPassword"][0]
    assert operation == MODIFY_REPLACE
    assert values[0].startswith("{SSHA}") and values[0] != CLEAR
    assert _ssha_verifies(values[0], CLEAR)


# --------------------------------------------------------------------------- #
# tools/purge_zodb_cleartext_passwords.py — legacy ZODB data
# --------------------------------------------------------------------------- #
@pytest.fixture()
def purge_tool(repo_root):
    return _load_module(
        repo_root / "tools" / "purge_zodb_cleartext_passwords.py", "purge_tool")


def _legacy_population():
    approved = Candidature()
    approved._candidature_state = CandidatureStates.APPROVED
    approved.data = MemberDatas(password="old-clear-1", password_confirm="old-clear-1")

    draft = Candidature()                     # __init__ leaves it in DRAFT
    draft.data = MemberDatas(password="draft-clear", password_confirm="draft-clear")

    pending_hashed = Candidature()
    pending_hashed.data = MemberDatas(password=make_ldap_password("kept"))

    member = Member(oid="member-legacy")
    member.data = MemberDatas(password="member-clear")

    return {
        "approved": approved, "draft": draft,
        "pending_hashed": pending_hashed, "member": member,
    }


def test_purge_tool_clears_settled_and_hashes_pending(purge_tool):
    population = _legacy_population()
    stats = purge_tool.purge_container(population, apply=True)

    assert population["approved"].data.password is None
    assert population["approved"].data.password_confirm is None
    assert population["member"].data.password is None
    # a pending candidature must still be able to create its LDAP account:
    draft_password = population["draft"].data.password
    assert draft_password.startswith("{SSHA}")
    assert _ssha_verifies(draft_password, "draft-clear")
    assert population["draft"].data.password_confirm is None
    # an already-hashed pending value is kept as-is
    kept = population["pending_hashed"].data.password
    assert _ssha_verifies(kept, "kept")

    assert stats["password_cleared"] == 2      # approved + member
    assert stats["password_hashed"] == 1       # draft
    assert stats["password_kept_hashed"] == 1  # pending_hashed
    assert stats["password_confirm_cleared"] == 2


def test_purge_tool_dry_run_mutates_nothing(purge_tool):
    population = _legacy_population()
    stats = purge_tool.purge_container(population, apply=False)

    assert population["approved"].data.password == "old-clear-1"
    assert population["draft"].data.password == "draft-clear"
    assert population["member"].data.password == "member-clear"
    assert len(stats["planned_changes"]) >= 4  # but they are only *planned*


# --------------------------------------------------------------------------- #
# docker/migrate_ldap_legacy.py — legacy LDAP data
# --------------------------------------------------------------------------- #
@pytest.fixture()
def migration_tool(repo_root):
    return _load_module(
        repo_root / "docker" / "migrate_ldap_legacy.py", "migrate_ldap_legacy")


LEGACY_LDIF = """dn: uid=u1,dc=alirpunkto,dc=org
objectClass: top
objectClass: inetOrgPerson
objectClass: alirpunktoPerson
uid: u1
cn: legacyUser
sn: Legacy
mail: legacy@example.org
employeeType: coperator
isActive: True
userPassword: legacy-clear-pw
"""


def test_migration_script_hashes_cleartext_userpassword(migration_tool):
    entries = migration_tool.parse_ldif(LEGACY_LDIF)
    report = migration_tool.Report()
    adapted = migration_tool.transform(
        entries, report, strict=False, keep_operational=False,
        hash_cleartext=True,
    )
    values = dict((a.lower(), v) for a, v in adapted[0].attrs)
    assert values["employeetype"] == "COOPERATOR"   # the historic typo
    assert values["userpassword"].startswith("{SSHA}")
    assert _ssha_verifies(values["userpassword"], "legacy-clear-pw")
    assert migration_tool.password_scheme(values["userpassword"]) != "CLEARTEXT"


def test_migration_script_can_keep_cleartext_on_request(migration_tool):
    entries = migration_tool.parse_ldif(LEGACY_LDIF)
    adapted = migration_tool.transform(
        entries, migration_tool.Report(), strict=False,
        keep_operational=False, hash_cleartext=False,
    )
    values = dict((a.lower(), v) for a, v in adapted[0].attrs)
    assert values["userpassword"] == "legacy-clear-pw"


MESSY_LEGACY_LDIF = """dn: dc=t,dc=org
objectClass: top
objectClass: dcObject
objectClass: organization
o: t
dc: t

dn: cn=mediationArbitrationCouncilGroup,dc=t,dc=org
objectClass: top
objectClass: groupOfUniqueNames
cn: mediationArbitrationCouncilGroup
uniqueMember: uid=00000000-0000-0000-0000-000000000000,cn=admin,dc=t,dc=org
uniqueMember: uid=real-1,cn=admin,dc=t,dc=org
uniqueMember: uid=ghost-9,cn=admin,dc=t,dc=org

dn: uid=real-1,dc=t,dc=org
objectClass: top
objectClass: inetOrgPerson
objectClass: alirpunktoPerson
uid: real-1
cn: RealOne
sn: One
mail: one@t.org
employeeType: PROVIDER
isActive: TRUE
description: None
uniqueMemberOf: cn=providerMembersGroup,dc=t,dc=org
userPassword: {SSHA}already+hashed+value000000000000
"""


def _messy_adapted(migration_tool):
    entries = migration_tool.parse_ldif(MESSY_LEGACY_LDIF)
    report = migration_tool.Report()
    adapted = migration_tool.transform(
        entries, report, strict=False, keep_operational=False,
        hash_cleartext=True)
    return adapted, report


def test_pipeline_reparents_cn_admin_member_refs(migration_tool):
    adapted, report = _messy_adapted(migration_tool)
    group = next(e for e in adapted if "mediationArbitration" in e.dn)
    members = group.get("uniqueMember")
    # the intentional all-zero placeholder stays under cn=admin
    assert "uid=00000000-0000-0000-0000-000000000000,cn=admin,dc=t,dc=org" in members
    # the real member is re-parented to its actual entry
    assert "uid=real-1,dc=t,dc=org" in members
    assert "uid=real-1,cn=admin,dc=t,dc=org" not in members
    # the ghost has no target entry: kept, but loudly reported
    assert "uid=ghost-9,cn=admin,dc=t,dc=org" in members
    assert "ghost-9" in report.text() and "kept as-is" in report.text()


def test_pipeline_drops_literal_none_descriptions(migration_tool):
    adapted, report = _messy_adapted(migration_tool)
    person = next(e for e in adapted if e.dn.startswith("uid=real-1"))
    assert person.get("description") == []
    assert "drop literal 'None' description" in report.text()


def test_pipeline_renames_provider_members_group_refs(migration_tool):
    adapted, _ = _messy_adapted(migration_tool)
    person = next(e for e in adapted if e.dn.startswith("uid=real-1"))
    assert person.get("uniqueMemberOf") == ["cn=providersGroup,dc=t,dc=org"]
