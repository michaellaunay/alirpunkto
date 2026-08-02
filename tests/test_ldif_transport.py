"""Eighth audit pass (2026-08-02, §4/§5) — the LDIF transport, closed.

The sixth-audit rework still put logins, pseudonyms, UUIDs, roles,
languages and NATIONALITIES on generate_ldif.py's argv — personal data,
some of it sensitive — and an absent password variable silently became
the valid {SSHA} hash of the empty string. The command line now carries
the two file paths only; every value crosses as NUL-delimited
NAME=VALUE records on stdin; required fields (passwords above all)
abort when missing OR empty; unknown names abort too.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_FIELDS = {
    "LDAP_BASE_DN": "dc=example,dc=com",
    "ADMIN_UUID": "uuid-a", "ADMIN_LOGIN": "admin",
    "ADMIN_PSEUDONYM": "AdminPseudo", "ADMIN_EMAIL": "admin@x.org",
    "ADMIN_PW": "admin-pw",
    "U1_UUID": "u1-uuid", "U1_ROLE": "COOPERATOR",
    "U1_PSEUDONYM": "pseudo1", "U1_FIRST": "First", "U1_LAST": "Last",
    "U1_LANG": "en", "U1_NAT": "FR", "U1_EMAIL": "u1@x.org",
    "U1_PW": "u1-pw",
    "U2_UUID": "u2-uuid", "U2_ROLE": "COOPERATOR",
    "U2_PSEUDONYM": "pseudo2", "U2_FIRST": "First2", "U2_LAST": "Last2",
    "U2_LANG": "fr", "U2_NAT": "DE", "U2_EMAIL": "u2@x.org",
    "U2_PW": "u2-pw",
    "TODAY": "2026-08-02",
    "U1_BIRTHDATE": "1990-01-01T12:00:00",
    "U1_DESCRIPTION": "Bio one",
}


def _records(fields):
    return b"".join(f"{name}={value}".encode("utf-8") + b"\0"
                    for name, value in fields.items())


def _run_generator(tmp_path, fields):
    """Execute docker/generate_ldif.py with only the two paths on argv
    and ``fields`` as NUL records on stdin. Returns (exit_code, output
    text or None, stderr text)."""
    template = tmp_path / "template.ldif"
    template.write_text("dn: dc=alirpunkto,dc=org\n", encoding="utf-8")
    out = tmp_path / "out.ldif"
    spec = importlib.util.spec_from_file_location(
        "generate_ldif_stdin_under_test",
        os.path.join(ROOT, "docker", "generate_ldif.py"))
    module = importlib.util.module_from_spec(spec)
    fake_stdin = SimpleNamespace(buffer=io.BytesIO(_records(fields)))
    stderr = io.StringIO()
    code = 0
    with patch.object(sys, 'argv',
                      ["generate_ldif.py", str(template), str(out)]), \
         patch.object(sys, 'stdin', fake_stdin), \
         contextlib.redirect_stderr(stderr):
        try:
            spec.loader.exec_module(module)
        except SystemExit as exc:
            code = exc.code or 0
    text = out.read_text(encoding="utf-8") if out.exists() else None
    return code, text, stderr.getvalue()


def test_every_value_travels_on_stdin_and_lands_in_the_ldif(tmp_path):
    code, content, stderr = _run_generator(tmp_path, dict(VALID_FIELDS))
    assert code == 0, stderr
    assert "mail: admin@x.org" in content
    assert "givenName: First" in content
    assert "sn: Last2" in content
    assert "nationality: DE" in content
    assert "birthdate: 1990-01-01T12:00:00" in content
    assert "description: Bio one" in content


def test_passwords_are_hashed_and_never_clear(tmp_path):
    code, content, _ = _run_generator(tmp_path, dict(VALID_FIELDS))
    assert code == 0
    assert "{SSHA}" in content
    for cleartext in ("admin-pw", "u1-pw", "u2-pw"):
        assert cleartext not in content


def test_a_missing_password_aborts_instead_of_hashing_nothing(tmp_path):
    """§5: an absent variable used to become the valid {SSHA} hash of
    the empty string — a silently created empty-password account."""
    fields = {name: value for name, value in VALID_FIELDS.items()
              if name != "U1_PW"}
    code, content, stderr = _run_generator(tmp_path, fields)
    assert code != 0
    assert content is None          # no LDIF was written
    assert "U1_PW" in stderr


def test_an_empty_password_aborts_too(tmp_path):
    fields = dict(VALID_FIELDS, ADMIN_PW="")
    code, content, stderr = _run_generator(tmp_path, fields)
    assert code != 0
    assert content is None
    assert "ADMIN_PW" in stderr


def test_an_unknown_record_name_aborts(tmp_path):
    fields = dict(VALID_FIELDS, TYPO_FIELD="x")
    code, content, stderr = _run_generator(tmp_path, fields)
    assert code != 0
    assert content is None
    assert "TYPO_FIELD" in stderr


def test_absent_optional_fields_stay_absent(tmp_path):
    fields = {name: value for name, value in VALID_FIELDS.items()
              if name not in ("U1_BIRTHDATE", "U1_DESCRIPTION")}
    code, content, _ = _run_generator(tmp_path, fields)
    assert code == 0
    assert "birthdate:" not in content
    assert "description:" not in content


def _init_script():
    with open(os.path.join(ROOT, "docker", "init.sh"),
              encoding="utf-8") as handle:
        return handle.read()


def test_the_command_line_carries_only_the_two_paths():
    """§4: pseudonyms, logins, roles and nationalities are personal
    data too — nothing user-provided may reach argv."""
    script = _init_script()
    assert "GENERATE_LDIF_ARGS" not in script
    assert "GENERATE_LDIF_" not in script     # the env slots are gone too
    call = script.rsplit("generate_ldif.py", 1)[1].split("\n\n", 1)[0]
    assert '"${LDIF_TEMPLATE}"' in call
    assert '"${LDIF_OUT}"' in call
    for variable in ("ADMIN", "USER1", "USER2", "NATIONALITY",
                     "PSEUDONYM", "PASSWORD"):
        assert variable not in call, variable


def test_the_records_pipeline_feeds_stdin():
    script = _init_script()
    assert "printf '%s=%s\\0'" in script
    assert "generate_ldif_records | python3" in script
