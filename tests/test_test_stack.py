"""Structural locks for the test-stack CI and its browser harness.

The test-stack workflow is the answer to the eleventh pass's P1
items 3-4 (run docker/init_test.sh in a clean environment, actually
start the local test stack) and the twelfth pass's P2. These tests
pin its load-bearing pieces: the untouched init_test.sh dogfood, the
compose validation gate before any build, the hashed e2e lock, the
browser capture step, the screenshot artifacts (published even on
failure — they are the diagnostic), and the teardown.
"""

import os
import py_compile

from tests.test_ldif_callers import _duplicate_mapping_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def _workflow() -> str:
    return _read(".github", "workflows", "test-stack.yml")


def test_the_workflow_has_no_duplicate_mapping_keys():
    """PyYAML is deliberately absent from the test lock (and its
    loader swallows duplicates anyway) — the home-grown strict
    detector is the yardstick, as everywhere else in the suite."""
    assert _duplicate_mapping_keys(_workflow()) == []


def test_init_test_is_dogfooded_untouched():
    """The whole point (11th pass, §7 reserve): CI must run the very
    script a developer runs, not a private re-implementation."""
    assert "bash docker/init_test.sh" in _workflow()


def test_the_compose_gate_runs_before_any_build():
    text = _workflow()
    gate = text.index("config --quiet")
    build = text.index(" build")
    assert gate < build
    assert "--env-file docker/.env.test" in text
    assert "-f docker/test-docker-compose.yaml" in text


def test_the_browser_harness_installs_from_the_hashed_lock():
    text = _workflow()
    assert "pip install --require-hashes -r requirements-e2e.lock" in text
    assert "playwright install --with-deps chromium" in text


def test_the_e2e_lock_pins_playwright_with_hashes():
    lock = _read("requirements-e2e.lock")
    assert "playwright==" in lock
    assert "--hash=sha256:" in lock


def test_the_capture_script_is_wired_and_compiles():
    assert "tools/e2e_login_capture.py" in _workflow()
    script = _read("tools", "e2e_login_capture.py")
    # The journey must cover the member profile — the page whose
    # panels shipped broken and were first caught by the client.
    assert "/modify_member" in script
    assert "04_modify_member.png" in script
    py_compile.compile(
        os.path.join(ROOT, "tools", "e2e_login_capture.py"), doraise=True
    )


def test_the_screenshots_are_published_even_on_failure():
    """The captures ARE the diagnostic when the journey fails, and
    the manual's raw material when it passes — always() both ways."""
    text = _workflow()
    upload = text.index("upload-artifact")
    window = text[max(0, upload - 200):upload]
    assert "if: always()" in window
    assert "/tmp/e2e-shots/" in text


def test_the_stack_is_always_torn_down():
    assert "down -v" in _workflow()


def test_the_capture_script_carries_no_secret_beyond_public_test_values():
    """Only the documented public test defaults of init_test.sh may
    appear — anything else in there would be a leak."""
    script = _read("tools", "e2e_login_capture.py")
    assert "AliceTest123!" in script  # the documented public default
    for forbidden in ("BEGIN RSA", "BEGIN OPENSSH", "ghp_", "AKIA"):
        assert forbidden not in script
