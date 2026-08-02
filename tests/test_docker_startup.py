"""P0 of the fourth external audit pass (2026-08-01).

The documented Docker stack could not start: both start scripts
demanded the retired setup.py, [server:main] carried a non-Waitress
option that raises ValueError before the socket binds, and the
container listened on its own loopback while trusting the wrong proxy
address. These tests pin each fix, the override helper, the compose
wiring and the smoke workflow that would have caught all three.
"""
import configparser
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_the_start_scripts_probe_the_installed_package_not_setup_py():
    """Fourth audit pass: the old scripts checked for the retired
    setup.py and stopped the container before pserve ever ran. Sixth
    audit pass (§11.1): the image ships no source tree any more, so the
    sanity check probes the installed wheel instead of pyproject.toml."""
    for name in ("start_pyramid.sh", "start_test_pyramid.sh"):
        script = _read("docker", name)
        assert "setup.py" not in script, name
        assert 'pyproject.toml' not in script, name
        assert '-c "import alirpunkto"' in script, name


def test_use_forwarded_proto_is_gone_from_every_ini():
    """5.2: the option is unknown to Waitress 3 — it must not survive
    anywhere, in any section."""
    for ini in ("production.ini", "development.ini", "testing.ini"):
        config = configparser.ConfigParser(interpolation=None)
        config.read(os.path.join(ROOT, ini))
        for section in config.sections():
            assert not config.has_option(section, "use_forwarded_proto"), (
                ini,
                section,
            )


def test_every_server_option_is_a_known_waitress_adjustment():
    """5.2, empirically: Waitress refuses unknown [server:main] options
    with `ValueError: Unknown adjustment` before binding — the stack
    died on use_forwarded_proto. Feed the real section to Adjustments
    so any future typo fails here instead of in production."""
    from waitress.adjustments import Adjustments

    config = configparser.ConfigParser(interpolation=None)
    config.read(os.path.join(ROOT, "production.ini"))
    options = {
        key: value
        for key, value in config.items("server:main")
        if key != "use" and key not in config.defaults()
    }
    Adjustments(**options)


def test_the_bare_host_defaults_are_preserved():
    """The audited values are the RIGHT ones for the bare-host
    deployment (doc chapter 13) — the Docker fix must not leak into
    them."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(os.path.join(ROOT, "production.ini"))
    assert config.get("server:main", "listen") == "localhost:6543"
    assert config.get("server:main", "trusted_proxy") == "127.0.0.1"


def test_the_override_helper_rewrites_only_the_two_server_lines(tmp_path):
    """The helper must change listen and trusted_proxy inside
    [server:main] and nothing else — %(here)s, logging and app settings
    travel untouched into the derived copy."""
    src = os.path.join(ROOT, "production.ini")
    dst = tmp_path / "production.generated.ini"
    env = dict(os.environ)
    env["PYRAMID_LISTEN"] = "0.0.0.0:6543"
    env["PYRAMID_TRUSTED_PROXY"] = "172.28.10.10"
    subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "docker", "apply_server_overrides.py"),
            src,
            str(dst),
        ],
        check=True,
        env=env,
        capture_output=True,
    )
    original = open(src, encoding="utf-8").read().splitlines()
    derived = dst.read_text(encoding="utf-8").splitlines()
    changed = [
        (a, b) for a, b in zip(original, derived, strict=True) if a != b
    ]
    assert sorted(changed) == [
        ("listen = localhost:6543", "listen = 0.0.0.0:6543"),
        ("trusted_proxy = 127.0.0.1", "trusted_proxy = 172.28.10.10"),
    ]

    config = configparser.ConfigParser(interpolation=None)
    config.read(dst)
    assert config.get("server:main", "listen") == "0.0.0.0:6543"
    assert config.get("server:main", "trusted_proxy") == "172.28.10.10"


def test_the_start_scripts_forward_the_docker_overrides():
    """5.3/5.4: both start scripts must turn PYRAMID_LISTEN and
    PYRAMID_TRUSTED_PROXY into a derived config served by pserve."""
    for name in ("start_pyramid.sh", "start_test_pyramid.sh"):
        script = _read("docker", name)
        assert "PYRAMID_LISTEN" in script, name
        assert "PYRAMID_TRUSTED_PROXY" in script, name
        assert "apply_server_overrides.py" in script, name
        assert ".generated.ini" in script, name


def test_the_compose_stack_pins_bind_and_proxy_addresses():
    """5.3/5.4: the stack must bind all interfaces inside the container
    and point trusted_proxy at the Apache container's fixed address —
    the same default on both sides, inside the pinned subnet."""
    compose = _read("docker", "docker-compose.yaml")
    assert 'PYRAMID_LISTEN: "0.0.0.0:6543"' in compose
    proxies = re.findall(r"\$\{ALIRPUNKTO_APACHE_IP:-([0-9.]+)\}", compose)
    assert len(proxies) == 2, proxies
    assert len(set(proxies)) == 1, proxies
    assert "ipv4_address" in compose
    subnet = re.search(
        r"\$\{ALIRPUNKTO_FRONTEND_SUBNET:-([0-9./]+)\}", compose
    )
    assert subnet is not None
    prefix = subnet.group(1).rsplit(".", 1)[0]
    assert proxies[0].startswith(prefix + "."), (proxies[0], subnet.group(1))


def test_the_compose_smoke_workflow_guards_the_stack():
    """§6: the CI never proved the delivered stack starts. The smoke
    workflow must build the images, boot compose, go through Apache
    over HTTPS, assert the real client address in the throttle log,
    and always tear down."""
    smoke = _read(".github", "workflows", "smoke.yml")
    assert "docker compose" in smoke
    assert "up -d --wait" in smoke
    assert "https://" in smoke
    assert "login throttled for ip=" in smoke
    assert "if: always()" in smoke
    assert "down -v" in smoke
