"""Regression tests for the applications list configuration (issue #142).

The links AlirPunkto shows for each application must be the SSO login URLs, so a
click logs the user straight into the application. The parser in __init__.py
requires name/id/logo_file/url for every application; this test locks the
production configuration against those invariants and against the pilot URLs.
"""
from __future__ import annotations

import os
from collections import defaultdict

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAM = "applications."
REQUIRED = ("name", "id", "logo_file", "url")


def _parse(ini_name):
    apps = defaultdict(dict)
    with open(os.path.join(ROOT, ini_name), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(PARAM) and "=" in line:
                key, val = line.split("=", 1)
                parts = key.strip()[len(PARAM):].split(".")
                if len(parts) == 2:
                    apps[parts[0]][parts[1]] = val.strip()
    return apps


@pytest.fixture
def apps():
    return _parse("production.ini")


def test_every_application_has_the_required_keys(apps):
    """__init__.py raises if any of these is missing, dropping the whole list."""
    assert apps, "no applications configured"
    for name, app in apps.items():
        for key in REQUIRED:
            assert key in app, f"application {name} is missing {key!r}"


def test_application_urls_are_sso_login_urls(apps):
    """Issue #142: the URLs must point at the SSO login entry points."""
    urls = {name: app["url"] for name, app in apps.items()}
    assert urls["nextcloud"] == (
        "https://workspace.cosmopolitical.coop/apps/sociallogin/custom_oidc/Keycloak"
    )
    assert urls["moodle"] == "https://learn.cosmopolitical.coop/login/index.php"
    assert urls["drupal"] == "https://www.cosmopolitical.coop/user/login"
    assert urls["liquidfeedback"] == (
        "https://operationaldecisions.cosmopolitical.coop/index/index.html"
    )
    # No leftover placeholder example URLs.
    for name, url in urls.items():
        assert "example.com" not in url, f"{name} still points at an example URL"


def test_moodle_carries_the_sso_button_instruction(apps):
    """Moodle needs the extra 'click the CosmoPolitical login button' note."""
    explanation = apps["moodle"].get("explanation", "")
    assert "CosmoPolitical login" in explanation


def test_no_application_references_a_missing_logo_asset(apps):
    """Every referenced logo file must actually exist under the package."""
    for name, app in apps.items():
        logo = app["logo_file"]
        assert os.path.isfile(os.path.join(ROOT, "alirpunkto", logo)), (
            f"application {name} references a missing logo: {logo}"
        )
