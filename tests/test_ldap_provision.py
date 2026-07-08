"""Tests for ``tools/ldap_provision.py`` (extract → seed → schema → load).

Covers the pure, target-independent parts of the provisioning tool:

* the seed-file contract (name and docker path interchangeable with the file
  ``docker/init.sh`` generates);
* the schema sync building blocks — parsing the reference
  ``alirpunkto/alirpunkto_schema.ldif`` (unfolding LDIF continuations),
  producing the idempotent ``replace:`` modify, extracting the discovered
  schema DN from ldapsearch output;
* the ldapi command assembly for both installation types (docker exec vs
  host, with and without sudo) and the ldapadd output accounting;
* the in-place password hashing against a fake connection: cleartext values
  are replaced by the pipeline's ``{SSHA}`` (cryptographically verified),
  hashed values are skipped, dry-run changes nothing;
* the admin's explicit installation-type choice (``--load`` without
  ``--install-type`` refuses to run).
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


@pytest.fixture()
def provision(repo_root):
    return _load_module(repo_root / "tools" / "ldap_provision.py",
                        "ldap_provision")


@pytest.fixture()
def shared(provision):
    return provision.load_remote().load_shared()


def _ssha_verifies(value: str, cleartext: str) -> bool:
    raw = base64.b64decode(value[len("{SSHA}"):])
    digest, salt = raw[:20], raw[20:]
    return hashlib.sha1(cleartext.encode("utf-8") + salt).digest() == digest


# --------------------------------------------------------------------------- #
# seed-file contract
# --------------------------------------------------------------------------- #
def test_seed_file_is_interchangeable_with_the_generated_one(provision):
    assert provision.SEED_FILE_NAME == "initials_users.generated.ldif"
    assert provision.DOCKER_SEED_PATH.as_posix().endswith(
        "docker/initials_users.generated.ldif")


# --------------------------------------------------------------------------- #
# schema sync building blocks
# --------------------------------------------------------------------------- #
def test_parse_schema_file_unfolds_the_reference_schema(provision):
    attribute_types, objectclass = provision.parse_schema_file()
    assert len(attribute_types) == 12
    joined = " ".join(attribute_types)
    for probe in provision.MODERN_SCHEMA_PROBES:
        assert f"NAME '{probe}'" in joined
    assert all("\n" not in value for value in attribute_types)
    assert objectclass.startswith("( 1.3.6.1.4.1.61000.2.2.1")
    assert "cooperativeBehaviourMarkUpdate" in objectclass


def test_build_schema_replace_ldif_is_an_idempotent_modify(provision):
    ldif = provision.build_schema_replace_ldif(
        "cn={5}alirpunktoperson,cn=schema,cn=config",
        ["( a1 )", "( a2 )"], "( oc )")
    lines = ldif.splitlines()
    assert lines[0] == "dn: cn={5}alirpunktoperson,cn=schema,cn=config"
    assert lines[1] == "changetype: modify"
    assert lines.count("replace: olcAttributeTypes") == 1
    assert lines.count("replace: olcObjectClasses") == 1
    assert "olcAttributeTypes: ( a1 )" in lines
    assert "olcObjectClasses: ( oc )" in lines
    assert "-" in lines                            # block separator


def test_parse_schema_dn_output_handles_folded_lines(provision):
    out = ("dn: cn={5}alirpunktoperson,cn=schema,cn=confi\n g\n\n")
    assert provision.parse_schema_dn_output(out) == \
        "cn={5}alirpunktoperson,cn=schema,cn=config"
    assert provision.parse_schema_dn_output("") is None


def test_build_ldapi_command_for_both_installation_types(provision):
    args = ["ldapmodify", "-Y", "EXTERNAL", "-H", "ldapi:///"]
    assert provision.build_ldapi_command("docker", "my-ldap", args, False) == \
        ["docker", "exec", "-i", "my-ldap", *args]
    assert provision.build_ldapi_command("host", "ignored", args, False) == args
    assert provision.build_ldapi_command("host", "ignored", args, True) == \
        ["sudo", *args]


def test_parse_ldapadd_output_accounts_for_everything(provision):
    stdout = ("adding new entry \"dc=t\"\n"
              "adding new entry \"uid=u1,dc=t\"\n"
              "ldap_add: Already exists (68)\n")
    stderr = "ldap_add: Invalid syntax (21)\n"
    stats = provision.parse_ldapadd_output(stdout, stderr)
    assert stats["added"] == 2
    assert stats["existing"] == 1
    assert stats["errors"] == ["ldap_add: Invalid syntax (21)"]


# --------------------------------------------------------------------------- #
# in-place password hashing (finding 1.3 on a live directory)
# --------------------------------------------------------------------------- #
class _FakeConn:
    def __init__(self, server_passwords):
        self._passwords = server_passwords
        self.entries = []
        self.modified = []
        self.result = {"description": "success"}

    def search(self, dn, *_args, **_kwargs):
        value = self._passwords.get(dn)
        self.entries = ([SimpleNamespace(
            userPassword=SimpleNamespace(value=value))]
            if value is not None else [])

    def modify(self, dn, changes):
        self.modified.append((dn, changes))
        return True


def _person(shared, dn, hashed):
    return shared.Entry(dn=dn, attrs=[
        ("objectClass", "inetOrgPerson"),
        ("objectClass", "alirpunktoPerson"),
        ("uid", dn.split(",")[0][4:]),
        ("userPassword", hashed),
    ])


def test_update_passwords_in_place_hashes_only_cleartext(provision, shared):
    hashed = shared.make_ssha("S3cret!clear")
    entries = [
        _person(shared, "uid=clear,dc=t", hashed),
        _person(shared, "uid=done,dc=t", shared.make_ssha("other")),
    ]
    conn = _FakeConn({"uid=clear,dc=t": "S3cret!clear",
                      "uid=done,dc=t": "{SSHA}serverAlreadyHashed000000"})
    rep = shared.Report()
    stats = provision.update_passwords_in_place(conn, entries, rep,
                                                dry_run=False)
    assert stats == {"hashed": 1, "already_hashed": 1,
                     "no_password": 0, "failed": 0}
    (dn, changes), = conn.modified
    assert dn == "uid=clear,dc=t"
    pushed = changes["userPassword"][0][1][0]
    assert pushed == hashed and _ssha_verifies(pushed, "S3cret!clear")


def test_update_passwords_in_place_dry_run_modifies_nothing(provision, shared):
    entries = [_person(shared, "uid=clear,dc=t", shared.make_ssha("pw"))]
    conn = _FakeConn({"uid=clear,dc=t": "pw"})
    stats = provision.update_passwords_in_place(conn, entries, shared.Report(),
                                                dry_run=True)
    assert stats["hashed"] == 1 and conn.modified == []


# --------------------------------------------------------------------------- #
# the admin must choose the installation type
# --------------------------------------------------------------------------- #
def test_load_without_install_type_is_refused(provision):
    with pytest.raises(SystemExit):
        provision.main(["--load"])
    with pytest.raises(SystemExit):
        provision.main(["--update-schema"])
