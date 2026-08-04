"""Locks for the data-schema versioning and upgrade-steps framework.

The directory is the source of truth; the ZODB is versioned so that
persisted-structure changes travel as explicit, idempotent steps —
and so the strong path (wipe + rebuild from LDAP, maintainer's
decision of 2026-08-04) stays an outillage, not a habit.
"""

import os
import py_compile

from alirpunkto.upgrades import (
    SCHEMA_VERSION,
    UPGRADE_STEPS,
    get_schema_version,
    run_pending_upgrades,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeRoot:
    """A bare object: attribute persistence is all the runner needs."""


def test_a_fresh_database_is_version_zero_and_gets_stamped():
    root = FakeRoot()
    assert get_schema_version(root) == 0
    applied = run_pending_upgrades(root)
    assert applied == list(range(1, SCHEMA_VERSION + 1))
    assert root.schema_version == SCHEMA_VERSION


def test_running_twice_is_a_no_op():
    root = FakeRoot()
    run_pending_upgrades(root)
    assert run_pending_upgrades(root) == []
    assert root.schema_version == SCHEMA_VERSION


def test_a_failing_step_does_not_advance_the_version(monkeypatch):
    root = FakeRoot()

    def boom(app_root):
        raise RuntimeError("step failed")

    monkeypatch.setattr(
        "alirpunkto.upgrades.UPGRADE_STEPS",
        [(1, "boom", boom)],
    )
    try:
        run_pending_upgrades(root)
    except RuntimeError:
        pass
    else:  # pragma: no cover - the step must raise
        raise AssertionError("the failing step should propagate")
    assert get_schema_version(root) == 0


def test_the_registry_is_contiguous_and_matches_the_target():
    versions = [v for v, _, _ in UPGRADE_STEPS]
    assert versions == list(range(1, SCHEMA_VERSION + 1))


def test_the_cli_commits_each_step():
    root = FakeRoot()
    commits = []
    run_pending_upgrades(root, commit_each=lambda: commits.append(True))
    assert len(commits) == SCHEMA_VERSION


def test_root_factory_wires_the_lazy_runner():
    with open(os.path.join(ROOT, "alirpunkto", "__init__.py"),
              encoding="utf-8") as handle:
        source = handle.read()
    assert "run_pending_upgrades(root)" in source
    assert 'getattr(root, "schema_version", 0) < SCHEMA_VERSION' in source


def test_the_operator_tools_compile_and_bootstrap():
    for name in ("run_upgrades.py", "rebuild_zodb_from_ldap.py"):
        path = os.path.join(ROOT, "tools", name)
        py_compile.compile(path, doraise=True)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        assert "bootstrap" in text
    rebuild = open(os.path.join(ROOT, "tools", "rebuild_zodb_from_ldap.py"),
                   encoding="utf-8").read()
    # The strong path reuses the application's own member factory and
    # records the maintainer's decision.
    assert "update_member_from_ldap" in rebuild
    assert "2026-08-04" in rebuild
