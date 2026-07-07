"""Tests for ``tools/migrate_ldap_legacy_remote.py`` (bare-metal legacy LDAP).

The tool binds to the old server over the network instead of shelling out to
``slapcat``, then reuses the transformation pipeline of
``docker/migrate_ldap_legacy.py``. These tests cover what is specific to it:

* the ``.env``-driven configuration (file parsing, bind-DN construction that
  mirrors the application's ``LDAP_LOGIN[,LDAP_OU],LDAP_BASE_DN``, URL
  building from ``LDAP_USE_SSL``/``LDAP_PORT``, password resolution);
* the conversion of ldap3 raw byte values into the shared pipeline's
  representation (UTF-8 text kept as text, binary carried base64);
* the extraction itself against a fake connection — parents-first ordering
  (an LDAP search, unlike ``slapcat``, guarantees no order), referral
  filtering, the ACL warning when person entries lack ``userPassword``, the
  plain-search fallback for servers without RFC 2696 — and the end-to-end run
  through the shared transform (``coperator`` fixed, cleartext password hashed
  to a verifying ``{SSHA}``);
* the loud degradation on a pre-1.3 shared pipeline (patch 09.1 may land
  before the 1.3 patch): passwords kept verbatim plus an explicit warning,
  never a crash.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import inspect
import sys
from types import SimpleNamespace

import pytest


# --------------------------------------------------------------------------- #
# fixtures & helpers
# --------------------------------------------------------------------------- #
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
def remote_tool(repo_root):
    return _load_module(
        repo_root / "tools" / "migrate_ldap_legacy_remote.py",
        "migrate_ldap_legacy_remote",
    )


@pytest.fixture()
def shared(remote_tool):
    return remote_tool.load_shared()


def _ssha_verifies(value: str, cleartext: str) -> bool:
    assert value.startswith("{SSHA}")
    raw = base64.b64decode(value[len("{SSHA}"):])
    digest, salt = raw[:20], raw[20:]
    return hashlib.sha1(cleartext.encode("utf-8") + salt).digest() == digest


class _FakeStandard:
    def __init__(self, pages, raises=None):
        self._pages, self._raises = pages, raises

    def paged_search(self, **_kwargs):
        if self._raises:
            raise self._raises
        return iter(self._pages)


class _FakeConn:
    """Just enough of an ldap3 Connection for fetch_entries()."""

    def __init__(self, pages, paged_raises=None):
        self.extend = SimpleNamespace(
            standard=_FakeStandard(pages, paged_raises))
        self._pages = pages
        self.response = None
        self.result = {"description": "success"}

    def search(self, *_args, **_kwargs):
        self.response = list(self._pages)
        return True


_BASE = {
    "type": "searchResEntry",
    "dn": "dc=example,dc=org",
    "raw_attributes": {
        "objectClass": [b"top", b"dcObject", b"organization"],
        "o": [b"Example"], "dc": [b"example"],
    },
}
_OU = {
    "type": "searchResEntry",
    "dn": "ou=People,dc=example,dc=org",
    "raw_attributes": {
        "objectClass": [b"top", b"organizationalUnit"], "ou": [b"People"],
    },
}
_PERSON = {
    "type": "searchResEntry",
    "dn": "uid=u1,ou=People,dc=example,dc=org",
    "raw_attributes": {
        "uid": [b"u1"],
        "objectClass": [b"top", b"inetOrgPerson", b"alirpunktoPerson"],
        "cn": [b"Jos\xc3\xa9 L"], "sn": [b"L"],
        "mail": [b"u1@example.org"],
        "employeeType": [b"coperator"],          # the historic typo
        "isActive": [b"True"],
        "userPassword": [b"clear-remote-pw"],
    },
}
_REFERRAL = {"type": "searchResRef", "uri": ["ldap://elsewhere/"]}


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
def test_read_env_file_parses_quotes_export_and_inline_comments(remote_tool, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "LDAP_SERVER=ldap://old.example.org:389 #Something like\n"
        "export LDAP_LOGIN='cn=admin'\n"
        'LDAP_PASSWORD="p#ss word"\n'
        "\n"
        "NOT_A_LINE\n",
        encoding="utf-8",
    )
    values = remote_tool.read_env_file(env_file)
    assert values["LDAP_SERVER"] == "ldap://old.example.org:389"
    assert values["LDAP_LOGIN"] == "cn=admin"
    assert values["LDAP_PASSWORD"] == "p#ss word"   # '#' kept inside quotes
    assert "NOT_A_LINE" not in values
    assert remote_tool.read_env_file(tmp_path / "missing.env") == {}


def test_build_bind_dn_mirrors_the_application(remote_tool, monkeypatch):
    for name in ("LDAP_LOGIN", "LDAP_OU", "LDAP_BASE_DN"):
        monkeypatch.delenv(name, raising=False)
    env = {"LDAP_LOGIN": "cn=admin", "LDAP_BASE_DN": "dc=example,dc=org"}
    assert remote_tool.build_bind_dn(env) == "cn=admin,dc=example,dc=org"
    env["LDAP_OU"] = "ou=People"
    assert remote_tool.build_bind_dn(env) == "cn=admin,ou=People,dc=example,dc=org"
    # a full DN in LDAP_LOGIN is taken as-is; an override wins over everything
    assert remote_tool.build_bind_dn(
        {"LDAP_LOGIN": "cn=root,dc=x"}) == "cn=root,dc=x"
    assert remote_tool.build_bind_dn(env, "cn=other,dc=y") == "cn=other,dc=y"


def test_build_server_url_from_env(remote_tool, monkeypatch):
    for name in ("LDAP_SERVER", "LDAP_USE_SSL", "LDAP_PORT"):
        monkeypatch.delenv(name, raising=False)
    assert remote_tool.build_server_url(
        {"LDAP_SERVER": "ldap://a:389"}) == "ldap://a:389"       # untouched
    assert remote_tool.build_server_url(
        {"LDAP_SERVER": "old.example.org", "LDAP_USE_SSL": "true",
         "LDAP_PORT": "636"}) == "ldaps://old.example.org:636"
    assert remote_tool.build_server_url({}, "ldap://cli:389") == "ldap://cli:389"


def test_resolve_password_prefers_process_env(remote_tool, monkeypatch):
    monkeypatch.setenv("LDAP_PASSWORD", "from-process")
    assert remote_tool.resolve_password(
        {"LDAP_PASSWORD": "from-file"}, "LDAP_PASSWORD", ask=False) == "from-process"
    monkeypatch.delenv("LDAP_PASSWORD", raising=False)
    assert remote_tool.resolve_password(
        {"LDAP_PASSWORD": "from-file"}, "LDAP_PASSWORD", ask=False) == "from-file"
    with pytest.raises(SystemExit):
        remote_tool.resolve_password({}, "LDAP_PASSWORD", ask=False)


# --------------------------------------------------------------------------- #
# raw values
# --------------------------------------------------------------------------- #
def test_raw_to_value_text_binary_and_roundtrip(remote_tool, shared):
    assert remote_tool.raw_to_value(b"plain", shared.MARK_B64) == "plain"
    # UTF-8 text stays text: format_attr base64-encodes it on output
    assert remote_tool.raw_to_value(
        "José".encode("utf-8"), shared.MARK_B64) == "José"
    blob = b"\xff\xfe\x00\x01"
    value = remote_tool.raw_to_value(blob, shared.MARK_B64)
    assert value.startswith(shared.MARK_B64)
    assert base64.b64decode(value[len(shared.MARK_B64):]) == blob


# --------------------------------------------------------------------------- #
# extraction + shared pipeline
# --------------------------------------------------------------------------- #
def test_fetch_orders_parents_first_and_skips_referrals(remote_tool, shared):
    conn = _FakeConn([_PERSON, _REFERRAL, _BASE, _OU])   # deliberately shuffled
    rep = shared.Report()
    entries = remote_tool.fetch_entries(conn, "dc=example,dc=org", shared, rep)
    assert [e.dn for e in entries] == [
        "dc=example,dc=org",
        "ou=People,dc=example,dc=org",
        "uid=u1,ou=People,dc=example,dc=org",
    ]
    assert entries[2].attrs[0][0] == "objectClass"        # readability ordering
    assert "WITHOUT userPassword" not in rep.text()


def test_end_to_end_through_shared_transform(remote_tool, shared):
    if "hash_cleartext" not in inspect.signature(shared.transform).parameters:
        pytest.skip("shared pipeline predates the 1.3 patch (no {SSHA} hashing)")
    conn = _FakeConn([_PERSON, _BASE, _OU])
    rep = shared.Report()
    entries = remote_tool.fetch_entries(conn, "dc=example,dc=org", shared, rep)
    adapted = shared.transform(entries, rep, strict=False,
                               keep_operational=False, hash_cleartext=True)
    person = next(e for e in adapted if e.dn.startswith("uid=u1"))
    assert person.get("employeeType") == ["COOPERATOR"]
    hashed = person.get("userPassword")[0]
    assert _ssha_verifies(hashed, "clear-remote-pw")
    assert rep.errors == 0


def test_fetch_warns_when_acl_hides_userpassword(remote_tool, shared):
    naked = {
        "type": "searchResEntry",
        "dn": "uid=u2,ou=People,dc=example,dc=org",
        "raw_attributes": {
            "uid": [b"u2"],
            "objectClass": [b"top", b"inetOrgPerson", b"alirpunktoPerson"],
            "cn": [b"U2"], "sn": [b"Two"], "mail": [b"u2@example.org"],
            "employeeType": [b"COOPERATOR"], "isActive": [b"TRUE"],
        },
    }
    rep = shared.Report()
    remote_tool.fetch_entries(
        _FakeConn([_BASE, naked]), "dc=example,dc=org", shared, rep)
    assert rep.warnings >= 1
    assert "WITHOUT userPassword" in rep.text()


def test_fetch_falls_back_to_plain_search(remote_tool, shared):
    conn = _FakeConn([_BASE, _PERSON],
                     paged_raises=RuntimeError("no RFC 2696 on this relic"))
    rep = shared.Report()
    entries = remote_tool.fetch_entries(conn, "dc=example,dc=org", shared, rep)
    assert len(entries) == 2
    assert "falling back to a plain subtree search" in rep.text()


def test_degrades_loudly_on_pre_1_3_pipeline(remote_tool, shared):
    """A shared pipeline without ``hash_cleartext`` keeps passwords and warns."""
    def legacy_transform(entries, rep, strict, keep_operational):
        return entries                       # the V1 signature, untouched data

    pre_1_3 = SimpleNamespace(transform=legacy_transform)
    args = SimpleNamespace(strict=False, keep_operational=False,
                           keep_cleartext_passwords=False)

    rep = shared.Report()
    entries = remote_tool.fetch_entries(
        _FakeConn([_BASE, _PERSON]), "dc=example,dc=org", shared, rep)
    out, supports = remote_tool.transform_with_pipeline(
        pre_1_3, entries, rep, args)
    assert supports is False
    person = next(e for e in out if e.dn.startswith("uid=u1"))
    assert person.get("userPassword") == ["clear-remote-pw"]   # untouched
    assert "predates the 1.3 patch" in rep.text()

    # the real shared pipeline is probed the same way (True once 1.3 landed)
    probe = remote_tool.transform_with_pipeline(
        shared,
        remote_tool.fetch_entries(
            _FakeConn([_BASE, _PERSON]), "dc=example,dc=org",
            shared, shared.Report()),
        shared.Report(), args,
    )
    assert probe[1] is (
        "hash_cleartext" in inspect.signature(shared.transform).parameters)
