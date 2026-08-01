"""The quality gates exist and stay wired (external audit, 2026-08-01).

ruff (pyflakes) blocks, bandit at medium+ blocks, pip-audit runs on the
lock with one documented accepted risk, mypy runs informatively, the
coverage ratchet sits at 68, and every GitHub action is pinned by
commit SHA — mutable tags being a supply-chain risk.
"""
from __future__ import annotations

import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


def test_the_quality_workflow_runs_the_three_gates():
    workflow = _read(".github", "workflows", "quality.yml")
    assert "ruff check alirpunkto tests tools" in workflow
    assert "bandit -r alirpunkto tools -ll" in workflow
    assert "pip-audit -r requirements.lock" in workflow
    assert "continue-on-error: true" in workflow        # mypy informative


def test_the_coverage_ratchet_is_armed():
    workflow = _read(".github", "workflows", "tests.yml")
    assert "--cov-fail-under=68" in workflow


def test_every_action_is_pinned_by_commit_sha():
    for name in ("tests.yml", "quality.yml"):
        workflow = _read(".github", "workflows", name)
        for line in workflow.splitlines():
            if "uses:" in line:
                assert re.search(r"@[0-9a-f]{40}\b", line), (name, line)


def test_no_out_of_lock_installs_remain_in_ci():
    workflow = _read(".github", "workflows", "tests.yml")
    assert "--upgrade pip setuptools wheel" not in workflow
    assert re.search(r"pip install pytest\s*$", workflow, re.M) is None


def test_ruff_and_the_quality_extra_are_configured():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        data = tomllib.load(f)
    assert data["tool"]["ruff"]["lint"]["select"] == ["F"]
    quality = data["project"]["optional-dependencies"]["quality"]
    assert any(dep.startswith("ruff") for dep in quality)
    assert any(dep.startswith("pip-audit") for dep in quality)


def test_cryptography_carries_the_cve_floor():
    lock = _read("requirements.lock")
    match = re.search(r"^cryptography==([\d.]+)", lock, re.M)
    assert match and tuple(map(int, match.group(1).split(".")[:2])) >= (48, 0)
