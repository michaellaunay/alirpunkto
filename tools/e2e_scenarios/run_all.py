#!/usr/bin/env python3
"""Run every manual-producing scenario against the local test stack."""

import sys

from playwright.sync_api import sync_playwright

import scenario_registration


def main() -> int:
    failures = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, run in (
            ("register_ordinary", scenario_registration.run_ordinary),
            ("register_cooperator", scenario_registration.run_cooperator),
        ):
            try:
                if not run(browser):
                    failures.append(name)
            except Exception as exc:  # capture-and-continue: the manifest
                print(f"[scenario:{name}] FAILED: {exc}")
                failures.append(name)
        browser.close()
    if failures:
        print(f"[scenarios] FAILED: {failures}")
        return 1
    print("[scenarios] all journeys green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
