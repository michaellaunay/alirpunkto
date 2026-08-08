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


def test_the_test_postfix_captures_mail_locally():
    """The scenarios read the challenge e-mails from the postfix
    container: the test compose enables the capture mode and the
    start script implements it (catchall mailbox, luser_relay)."""
    compose = _read("docker", "test-docker-compose.yaml")
    assert 'POSTFIX_LOCAL_CAPTURE: "1"' in compose
    # The capture lives in the TEST entrypoint (the container runs
    # start_test_postfix.sh, not the production script — the 0091
    # block sat in the wrong file and was never executed).
    script = _read("docker", "start_test_postfix.sh")
    assert "POSTFIX_LOCAL_CAPTURE" in script
    assert "luser_relay = catchall" in script
    assert "local_recipient_maps =" in script
    assert "maillog_file = /dev/stdout" in script
    # Outbound mail stays discarded even in capture mode.
    assert script.count('"default_transport = discard:"') == 2
    prod = _read("docker", "start_postfix.sh")
    assert "POSTFIX_LOCAL_CAPTURE" not in prod
    framework = _read("tools", "e2e_scenarios", "framework.py")
    # The Debian main.cf sets home_mailbox = Maildir/: deliveries land
    # in one-file-per-message under the catchall home (run 84784429694
    # proved it: "delivered to maildir"), not in /var/mail.
    assert "/home/catchall/Maildir/new/" in framework
    assert "/home/catchall/Maildir/cur/" in framework


def test_the_scenarios_drive_the_choice_select():
    """register.pt's membership choice is a <select>, not radios —
    the first CI run timed out on page.check (run 84778749823)."""
    scenario = _read("tools", "e2e_scenarios", "scenario_registration.py")
    assert "select_option" in scenario
    assert "page.check(" not in scenario


def test_the_draft_submit_is_verified_before_captioning():
    """Run 84781541914: the 'challenge_sent' caption immortalised an
    e-mail-send failure. The scenario now asserts the challenge form
    is on screen before captioning success."""
    scenario = _read("tools", "e2e_scenarios", "scenario_registration.py")
    assert "challenge form not shown" in scenario
    assert "draft_submit_failed" in scenario


def test_the_identity_screen_is_driven_by_its_real_widgets():
    """Run 84789315715: the identity screen is a deform form — its
    submit is <button id=deformsubmit>, its birth-date field is named
    "date", and nationality is not on it."""
    scenario = _read("tools", "e2e_scenarios", "scenario_registration.py")
    assert 'button[type="submit"], input[type="submit"]' in scenario
    assert 'input[name="date"]' in scenario
    assert "nationality" not in scenario.replace(
        "nationality is NOT on this", "").replace(
        "later profile steps", "")
