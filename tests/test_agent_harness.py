"""Structural locks for the multi-agent harness (twelfth audit pass).

The harness (AGENTS.md, CLAUDE.md, .claude/settings.json) is
configuration like any other: the twelfth external audit found the
same class of mistakes there that the rest of the suite guards
against elsewhere — an over-broad deny pattern blocking the tracked
.env.example, a generated credentials file left readable, a setup
that did not install the tools it then requires, and documented
commands drifting from the CI's. These tests pin the fixes.
"""

import fnmatch
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def _settings() -> dict:
    return json.loads(_read(".claude", "settings.json"))


def test_the_claude_settings_are_valid_json_with_the_three_rule_lists():
    settings = _settings()
    permissions = settings["permissions"]
    for key in ("allow", "ask", "deny"):
        assert isinstance(permissions[key], list) and permissions[key]


def test_claude_md_imports_the_shared_contract():
    assert "@AGENTS.md" in _read("CLAUDE.md")


def test_the_sensitive_files_are_denied_to_claude():
    deny = _settings()["permissions"]["deny"]
    for rule in (
        "Read(./.env)",
        "Read(./docker/.env)",
        "Read(./docker/.env.test)",
        "Read(./docker/secrets/**)",
        "Bash(git push:*)",
    ):
        assert rule in deny, f"missing deny rule: {rule}"


def test_the_tracked_env_example_stays_readable():
    """Twelfth pass, §4: Read(./.env.*) unintentionally matched the
    tracked .env.example, which agents must be able to audit. No deny
    Read pattern may match it."""
    read_patterns = [
        rule[len("Read("):-1]
        for rule in _settings()["permissions"]["deny"]
        if rule.startswith("Read(")
    ]
    for candidate in (".env.example", "./.env.example"):
        for pattern in read_patterns:
            assert not fnmatch.fnmatch(candidate, pattern), (
                f"deny pattern {pattern!r} blocks {candidate!r}"
            )


def test_the_quality_tools_live_in_the_installed_lock():
    """Twelfth pass, §9: the documented setup must actually provide
    the tools the documented commands call."""
    agents = _read("AGENTS.md")
    assert "requirements-quality.lock" in agents
    lock = _read("requirements-quality.lock")
    for tool in ("ruff==", "bandit==", "pip-audit=="):
        assert tool in lock, f"{tool} not pinned in the quality lock"


def test_the_documented_commands_match_the_quality_workflow():
    """Twelfth pass, §10: the 'Exact CI commands' section must carry
    the workflow's run lines verbatim — drift on either side fails."""
    agents = _read("AGENTS.md")
    workflow = _read(".github", "workflows", "quality.yml")
    runs = re.findall(r"run: >-\n((?:\s{10}.+\n)+)|run: (.+)", workflow)
    commands = []
    for block, inline in runs:
        if inline:
            commands.append(inline.strip())
        else:
            commands.append(" ".join(line.strip() for line in block.splitlines()))
    for needle in ("ruff check", "bandit -r", "pip-audit"):
        matching = [c for c in commands if c.startswith(needle.split()[0])]
        assert matching, f"no {needle} command found in quality.yml"
        for command in matching:
            if command.startswith("pip install"):
                continue
            assert command in agents, (
                f"AGENTS.md does not quote the CI command verbatim: {command}"
            )


def test_the_agent_local_state_files_are_gitignored():
    gitignore = _read(".gitignore")
    assert ".claude/settings.local.json" in gitignore
    assert ".kimi-code/local.toml" in gitignore
