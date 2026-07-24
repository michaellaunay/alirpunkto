"""Structural tests for the applications list configuration (issue #142).

The home page builds the applications list from the applications.<name>.<key>
settings; __init__.py raises (dropping the WHOLE list) if any application lacks
name/id/logo_file/url. These tests lock those structural invariants for the
configurations shipped in the repository.

The concrete deployment values — the SSO login URLs, the Moodle "CosmoPolitical
login" note, and the real logo assets — live in the operator's own production.ini
(not committed), so they are intentionally NOT asserted here: doing so would
couple the test suite to deployment data the repository deliberately keeps
generic.
"""
from __future__ import annotations

import configparser
import os
from collections import defaultdict

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAM = "applications."
REQUIRED = ("name", "id", "logo_file", "url")

# The .ini files that ship an applications list and are parsed by __init__.py.
INI_FILES = ["production.ini", "development.ini"]


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


@pytest.mark.parametrize("ini_name", INI_FILES)
def test_ini_file_is_parseable(ini_name):
    cp = configparser.ConfigParser(strict=True, interpolation=None)
    # Raises DuplicateOptionError / ParsingError on a malformed file.
    read = cp.read(os.path.join(ROOT, ini_name))
    assert read, f"{ini_name} could not be read"


@pytest.mark.parametrize("ini_name", INI_FILES)
def test_every_application_has_the_required_keys(ini_name):
    """__init__.py raises if any of these is missing, dropping the whole list."""
    apps = _parse(ini_name)
    assert apps, f"no applications configured in {ini_name}"
    for name, app in apps.items():
        for key in REQUIRED:
            assert key in app, f"{ini_name}: application {name} is missing {key!r}"


@pytest.mark.parametrize("ini_name", INI_FILES)
def test_application_urls_are_absolute_http(ini_name):
    """Every application link must be an absolute http(s) URL."""
    apps = _parse(ini_name)
    for name, app in apps.items():
        url = app["url"]
        assert url.startswith(("http://", "https://")), (
            f"{ini_name}: application {name} has a non-absolute url: {url!r}"
        )


@pytest.mark.parametrize("ini_name", INI_FILES)
def test_application_urls_have_no_surrounding_whitespace(ini_name):
    """A trailing space in a url would break the link (seen in the pilot config)."""
    apps = _parse(ini_name)
    for name, app in apps.items():
        assert app["url"] == app["url"].strip()
