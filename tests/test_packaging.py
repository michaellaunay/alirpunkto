"""Dependencies are bounded, locked and reproducible (external audit).

The legacy setup.py declared every dependency unbounded with
version='0.0' and no lock — two installs at different dates produced
different environments. pyproject.toml now carries measured bounds and a
real version, the paste.app_factory entry point survives, the exact set
is pinned in requirements.lock (what the CI installs), and setup.py may
not come back.
"""
from __future__ import annotations

import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)["project"]


def test_the_project_has_a_real_version_and_python_floor():
    project = _project()
    assert project["version"] not in ("", "0.0")
    assert project["requires-python"].startswith(">=3.11")


def test_every_dependency_is_bounded():
    project = _project()
    deps = project["dependencies"] + project[
        "optional-dependencies"]["testing"]
    for dep in deps:
        assert ">=" in dep, f"unbounded (no floor): {dep}"
        name = re.split(r"[<>=;\[ ]", dep)[0]
        if name == "pytz":        # calendar versioning: floor only
            continue
        assert "<" in dep, f"unbounded (no ceiling): {dep}"


def test_the_paste_entry_point_survives():
    """plaster/pserve boots the app through this exact entry point."""
    project = _project()
    assert project["entry-points"]["paste.app_factory"]["main"] \
        == "alirpunkto:main"


def test_the_lock_pins_the_whole_dependency_tree():
    lock = open(os.path.join(ROOT, "requirements.lock"),
                encoding="utf-8").read()
    pinned = {line.split("==")[0].strip().lower().replace("_", "-")
              for line in lock.splitlines()
              if "==" in line and not line.lstrip().startswith("#")}
    assert len(pinned) >= 40                       # the whole tree, not a stub
    for dep in _project()["dependencies"]:
        name = re.split(r"[<>=;\[ ]", dep)[0].lower().replace("_", "-")
        assert name in pinned, f"{name} missing from requirements.lock"


def test_the_legacy_setup_py_is_gone():
    assert not os.path.exists(os.path.join(ROOT, "setup.py"))


def test_the_ci_installs_from_the_lock():
    ci = open(os.path.join(ROOT, ".github", "workflows", "tests.yml"),
              encoding="utf-8").read()
    assert "setup.py" not in ci
    assert "requirements.lock" in ci
    assert "pyproject.toml" in ci

def test_the_docker_builds_install_from_the_lock():
    """Revised audit: the production image resolved from the pyproject
    ranges — two images built at different dates could diverge."""
    dockerfile = open(os.path.join(ROOT, "docker", "DockerfilePyramid"),
                      encoding="utf-8").read()
    assert "requirements.lock" in dockerfile
    assert "--no-deps" in dockerfile
    script = open(os.path.join(ROOT, "docker", "start_test_pyramid.sh"),
                  encoding="utf-8").read()
    assert "requirements.lock" in script


def test_waitress_options_live_in_the_server_section():
    """Revised audit: trusted_proxy sat in [app:main], where Waitress
    never reads — the whole proxy trust was inert."""
    import configparser
    config = configparser.ConfigParser()
    config.read(os.path.join(ROOT, "production.ini"))
    # Fourth audit pass: use_forwarded_proto left the tuple — it is not
    # a Waitress option at all (see tests/test_docker_startup.py).
    for option in ("trusted_proxy", "trusted_proxy_headers",
                   "clear_untrusted_proxy_headers"):
        assert config.has_option("server:main", option), option
        assert not config.has_option("app:main", option), option
