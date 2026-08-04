#!/usr/bin/env python3
"""Log into the local test stack through a real browser and capture
the screens.

This is the first validation scenario of the test-stack CI (eleventh
pass P1 items 3-4, twelfth pass P2) and the raw material of the
future illustrated user manual: every run produces dated, reproducible
screenshots of the login journey against the stack that
docker/init_test.sh builds.

Environment (all optional — defaults match init_test.sh):
    E2E_BASE_URL   https://alirpunkto.localhost:8443
    E2E_USERNAME   alice.test
    E2E_PASSWORD   AliceTest123!        (public test value)
    E2E_SHOT_DIR   <system temp dir>/e2e-shots

Exit code 0 when the journey succeeds (login form shown, credentials
accepted, authenticated page reached); 1 with a diagnostic otherwise.
The TLS certificate is the throwaway one init_test.sh generates, so
certificate errors are ignored on purpose.
"""

import os
import sys
import tempfile

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("E2E_BASE_URL", "https://alirpunkto.localhost:8443")
USERNAME = os.environ.get("E2E_USERNAME", "alice.test")
PASSWORD = os.environ.get("E2E_PASSWORD", "AliceTest123!")
SHOT_DIR = os.environ.get(
    "E2E_SHOT_DIR", os.path.join(tempfile.gettempdir(), "e2e-shots")
)


def shot(page, name: str) -> None:
    path = os.path.join(SHOT_DIR, name)
    page.screenshot(path=path, full_page=True)
    print(f"[e2e] captured {path}")


def main() -> int:
    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 800},
        ).new_page()

        page.goto(f"{BASE_URL}/login", wait_until="load")
        if page.locator('input[name="username"]').count() != 1:
            print("[e2e] FAIL: the login form did not render")
            shot(page, "99_failure.png")
            return 1
        shot(page, "01_login_page.png")

        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        shot(page, "02_login_filled.png")

        # A real browser sends the Origin/Referer headers Pyramid's
        # https CSRF protection expects — no curl workaround needed.
        page.click('input[type="submit"]')
        page.wait_for_load_state("load")

        content = page.content()
        still_on_login = page.locator('input[name="password"]').count() > 0
        if still_on_login or USERNAME not in content:
            print(f"[e2e] FAIL: login not accepted (url={page.url})")
            shot(page, "99_failure.png")
            return 1
        shot(page, "03_logged_in_home.png")

        # The member profile — the page whose issue-#55/#149 panels
        # shipped with Zope-path expressions this engine cannot run
        # (NameError: groups, first found by the client on the live
        # test server). A real visit keeps it renderable.
        page.goto(f"{BASE_URL}/modify_member", wait_until="load")
        content = page.content()
        if "Internal Server Error" in content or USERNAME not in content:
            print(f"[e2e] FAIL: /modify_member did not render (url={page.url})")
            shot(page, "99_failure.png")
            return 1
        shot(page, "04_modify_member.png")

        print(f"[e2e] PASS: authenticated as {USERNAME} at {page.url}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
