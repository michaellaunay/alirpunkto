"""Sixth audit pass (2026-08-01, §12.4).

A command line is world-readable in /proc/<pid>/cmdline, yet
``docker/init.sh`` used to push passwords (or, without slappasswd, the
CLEARTEXT password), e-mail addresses, names, birthdates and
descriptions through ``generate_ldif.py``'s argv — under a comment
claiming they travelled as "NUL-separated env vars". The "-" slot
mechanism of the revised audit now covers every personal field, the
values ride the generator's own single-use environment (scrubbed on
read), and init.sh no longer pre-hashes anything: the slappasswd
dependency and its cleartext fallback are gone.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PERSONAL_ENV = {
    "GENERATE_LDIF_ADMIN_PW": "admin-env-pw",
    "GENERATE_LDIF_U1_PW": "u1-env-pw",
    "GENERATE_LDIF_U2_PW": "u2-env-pw",
    "GENERATE_LDIF_ADMIN_EMAIL": "admin-env@x.org",
    "GENERATE_LDIF_U1_FIRST": "EnvFirst",
    "GENERATE_LDIF_U1_LAST": "EnvLast",
    "GENERATE_LDIF_U1_EMAIL": "u1-env@x.org",
    "GENERATE_LDIF_U1_BIRTHDATE": "1990-01-01T12:00:00",
    "GENERATE_LDIF_U1_DESCRIPTION": "Env bio",
    "GENERATE_LDIF_U2_FIRST": "EnvFirst2",
    "GENERATE_LDIF_U2_LAST": "EnvLast2",
    "GENERATE_LDIF_U2_EMAIL": "u2-env@x.org",
    "GENERATE_LDIF_U2_BIRTHDATE": "1991-02-02T12:00:00",
    "GENERATE_LDIF_U2_DESCRIPTION": "Env bio 2",
}

# argv exactly as the reworked init.sh builds it: "-" for every
# personal or secret slot, literal values for the rest.
DASH_ARGV_TAIL = (
    ["uuid-a", "admin", "AdminPseudo", "-", "-"]
    + ["u1-uuid", "COOPERATOR", "pseudo1", "-", "-", "en", "FR", "-", "-"]
    + ["u2-uuid", "COOPERATOR", "pseudo2", "-", "-", "fr", "DE", "-", "-"]
    + ["2026-08-01"]
    + ["", "", "-", "-"]
    + ["", "", "-", "-"])


def _run_generator(tmp_path, env):
    """Execute docker/generate_ldif.py with dash slots and ``env``;
    return the output text and, for each provided variable, whether it
    was still in the environment right after the run (scrub check must
    happen INSIDE the patched context — patch.dict restores on exit)."""
    template = tmp_path / "template.ldif"
    template.write_text("dn: dc=alirpunkto,dc=org\n", encoding="utf-8")
    out = tmp_path / "out.ldif"
    argv = [str(template), str(out), "dc=example,dc=com"] + DASH_ARGV_TAIL
    spec = importlib.util.spec_from_file_location(
        "generate_ldif_transport_under_test",
        os.path.join(ROOT, "docker", "generate_ldif.py"))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'argv', ["generate_ldif.py"] + argv), \
         patch.dict(os.environ, env, clear=False):
        try:
            spec.loader.exec_module(module)
        except SystemExit as exc:
            raise AssertionError(f"generator refused argv: {exc}")
        left_over = {name: name in os.environ for name in env}
    return out.read_text(encoding="utf-8"), left_over


def test_every_personal_slot_is_read_from_the_environment(tmp_path):
    content, _ = _run_generator(tmp_path, dict(PERSONAL_ENV))
    assert "mail: admin-env@x.org" in content
    assert "mail: u1-env@x.org" in content
    assert "mail: u2-env@x.org" in content
    assert "givenName: EnvFirst" in content
    assert "sn: EnvLast" in content
    assert "birthdate: 1990-01-01T12:00:00" in content
    assert "description: Env bio" in content
    # No slot may leak through as its literal placeholder.
    assert not re.search(r"(?m)^[A-Za-z]+: -$", content)


def test_passwords_are_hashed_and_every_variable_is_scrubbed(tmp_path):
    content, left_over = _run_generator(tmp_path, dict(PERSONAL_ENV))
    assert "{SSHA}" in content
    for cleartext in ("admin-env-pw", "u1-env-pw", "u2-env-pw"):
        assert cleartext not in content
    assert left_over == {name: False for name in PERSONAL_ENV}


def test_a_dash_slot_without_its_variable_stays_empty(tmp_path):
    env = {name: value for name, value in PERSONAL_ENV.items()
           if "BIRTHDATE" not in name and "DESCRIPTION" not in name}
    content, _ = _run_generator(tmp_path, env)
    assert "birthdate:" not in content
    assert "description:" not in content


def _init_script():
    with open(os.path.join(ROOT, "docker", "init.sh"),
              encoding="utf-8") as handle:
        return handle.read()


def test_the_args_array_carries_no_personal_value():
    script = _init_script()
    block = script.split("GENERATE_LDIF_ARGS=(", 1)[1].split(")", 1)[0]
    assert block.count('"-"') == 14
    for variable in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "HASHED",
                     "USER1_FIRSTNAME", "USER1_LASTNAME", "USER1_EMAIL",
                     "USER1_PASSWORD", "USER1_BIRTHDATE",
                     "USER1_DESCRIPTION", "USER2_FIRSTNAME",
                     "USER2_LASTNAME", "USER2_EMAIL", "USER2_PASSWORD",
                     "USER2_BIRTHDATE", "USER2_DESCRIPTION"):
        assert variable not in block, variable


def test_the_invocation_provides_every_environment_slot():
    script = _init_script()
    for name in PERSONAL_ENV:
        assert f"{name}=" in script, name


def test_the_script_no_longer_hashes_nor_lies_about_the_transport():
    script = _init_script()
    assert "hash_password" not in script
    assert "slappasswd" not in script
    assert "NUL-separated" not in script
