"""Tenth audit pass (2026-08-02, §8-§11) — every caller, one contract.

The eighth-pass rework moved the LDIF transport onto stdin, but the
tests inspected a single caller (docker/init.sh): the interface change
silently broke docker/init_test.sh and the smoke workflow, and a
duplicate ``args:`` key slipped into the LDAP compose service — hidden
by PyYAML's permissive loader, which keeps the last duplicate instead
of failing like compose does. These tests lock the whole caller set
onto the shared emitter (docker/ldif_records.sh) and parse the compose
files with a duplicate-rejecting reader.
"""
from __future__ import annotations

import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CALLERS = (
    ("docker", "init.sh"),
    ("docker", "init_test.sh"),
    (".github", "workflows", "smoke.yml"),
)

COMPOSE_FILES = (
    ("docker", "docker-compose.yaml"),
    ("docker", "test-docker-compose.yaml"),
)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def _duplicate_mapping_keys(text):
    """Minimal duplicate-key detector for the block-style YAML these
    compose files use. PyYAML silently keeps the last duplicate — the
    exact behaviour that hid the broken LDAP service — so the check is
    done directly on the mapping structure: one scope per indentation
    level, reset by list items."""
    duplicates = []
    scopes = []  # list of (indent, seen_keys)
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        content = stripped.strip()
        while scopes and scopes[-1][0] >= indent and not (
                scopes[-1][0] == indent and not content.startswith("- ")):
            if scopes[-1][0] > indent:
                scopes.pop()
            else:
                break
        if content.startswith("- "):
            # Every list item opens a fresh scope for its own keys.
            scopes.append((indent + 2, set()))
            content = content[2:]
            indent += 2
        match = re.match(r"([A-Za-z_][\w.-]*):(\s|$)", content)
        if not match:
            continue
        key = match.group(1)
        if not scopes or scopes[-1][0] < indent:
            scopes.append((indent, set()))
        seen = scopes[-1][1]
        if key in seen:
            duplicates.append((number, key))
        seen.add(key)
    return duplicates


def test_the_compose_files_have_no_duplicate_mapping_keys():
    """§8: the LDAP service carried two ``args:`` keys — compose
    refuses the file, or the second block silently erases the first
    and the Ubuntu snapshot never reaches the build."""
    for parts in COMPOSE_FILES:
        duplicates = _duplicate_mapping_keys(_read(*parts))
        assert not duplicates, (parts, duplicates)


def test_the_ldap_build_keeps_both_arguments():
    compose = _read("docker", "docker-compose.yaml")
    ldap_build = compose.split("DockerfileOpenLDAP", 1)[1].split("image:", 1)[0]
    assert "BUILD_WITH_DEBUG" in ldap_build
    assert "UBUNTU_SNAPSHOT" in ldap_build
    assert ldap_build.count("args:") == 1


def test_every_caller_sources_the_shared_emitter():
    """§10/§11: one copy of the transport contract, sourced everywhere
    — and the retired environment slots are gone from every caller."""
    for parts in CALLERS:
        script = _read(*parts)
        assert "ldif_records.sh" in script, parts
        assert "generate_ldif_records | python3" in script, parts
        assert "GENERATE_LDIF_" not in script, parts


def test_no_caller_passes_more_than_the_two_paths():
    """§9: the generator refuses any invocation whose command line is
    not exactly the two file paths — so no caller may still speak the
    positional interface."""
    for parts in CALLERS:
        script = _read(*parts)
        chunk = script.rsplit("generate_ldif.py", 1)[1]
        lines = chunk.splitlines()
        lines[0] = lines[0].lstrip('"')  # closing quote of the script path
        command_tail = []
        for line in lines:
            command_tail.append(line.strip())
            if not line.rstrip().endswith("\\"):
                break
        joined = " ".join(command_tail).replace("\\", " ")
        paths = [token for token in re.findall(r'"[^"]*"|\S+', joined)
                 if token.strip()]
        assert len(paths) == 2, (parts, paths)


def test_the_emitter_covers_exactly_the_generator_fields():
    """The emitter and the generator must never drift apart: the set
    of emitted record names equals REQUIRED_FIELDS + OPTIONAL_FIELDS."""
    module = ast.parse(_read("docker", "generate_ldif.py"))
    declared = {}
    for node in ast.walk(module):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                        "REQUIRED_FIELDS", "OPTIONAL_FIELDS"):
                    declared[target.id] = set(ast.literal_eval(node.value))
    assert set(declared) == {"REQUIRED_FIELDS", "OPTIONAL_FIELDS"}
    emitted = set(re.findall(r"emit ([A-Z0-9_]+) ",
                             _read("docker", "ldif_records.sh")))
    assert emitted == declared["REQUIRED_FIELDS"] | declared["OPTIONAL_FIELDS"]


def test_no_shell_side_password_hashing_remains():
    """§10: init_test.sh hashed the passwords itself — pushing each one
    through a python argv on the way. The generator is the only hasher
    now, on both setup scripts."""
    for name in ("init.sh", "init_test.sh"):
        script = _read("docker", name)
        assert "hash_ssha" not in script, name
        assert "slappasswd" not in script, name
        assert "SSHA" not in script, name


def test_the_smoke_validates_compose_before_building():
    """§8's control: ``compose config --quiet`` on both files, before
    any image is built."""
    smoke = _read(".github", "workflows", "smoke.yml")
    gate = smoke.index("config --quiet")
    assert smoke.count("config --quiet") == 2
    assert gate < smoke.index("- name: Build the images")
