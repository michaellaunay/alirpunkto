from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT = "tools/export_sources_for_review.sh"


def test_export_sources_script_exists_and_is_valid_bash(repo_root: Path):
    path = repo_root / SCRIPT
    assert path.is_file(), f"Missing {SCRIPT}"
    subprocess.run(["bash", "-n", str(path)], check=True)


def test_export_sources_script_excludes_generated_and_sensitive_files(repo_root: Path):
    script = (repo_root / SCRIPT).read_text(encoding="utf-8")

    for pattern in (
        ".env",
        ".env.*",
        "docker/secrets",
        "docker/certs",
        "*.pem",
        "*.key",
        "*.crt",
        "*.generated.ldif",
        "test.ini",
        "__pycache__",
        "locale",
        "static",
    ):
        assert pattern in script


def test_export_sources_script_outputs_numbered_sections(repo_root: Path):
    script = (repo_root / SCRIPT).read_text(encoding="utf-8")

    assert "=== %s ===" in script
    assert "nl -ba" in script
    assert "/tmp/" in script
    assert "alirpunkto" in script
    assert "tests" in script
    assert "docker" in script
