"""Tests for the source export helper used for code review."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "export_sources_for_review.sh"


def test_export_sources_for_review_script_exists() -> None:
    assert SCRIPT.is_file()


def test_export_sources_for_review_script_is_syntax_valid() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True, cwd=REPO_ROOT)


def test_export_sources_for_review_excludes_local_or_sensitive_artifacts() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    expected_exclusions = [
        ".env",
        "docker/certs",
        "docker/secrets",
        "generated.ldif",
        "test.ini",
        "__pycache__",
        "eggs",
        "locale",
        "static",
    ]

    missing = [pattern for pattern in expected_exclusions if pattern not in content]

    assert missing == []


def test_export_sources_for_review_numbers_output_lines() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "nl -ba" in content or "cat -n" in content
