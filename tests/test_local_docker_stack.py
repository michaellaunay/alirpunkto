"""Static regression tests for the local Docker test stack.

These tests intentionally do not start Docker containers.  They validate the
source files that make the local/offline stack reproducible and catch regressions
such as binding Pyramid to localhost only, exposing ports on all interfaces, or
accidentally enabling external mail delivery.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKER_DIR = REPO_ROOT / "docker"


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_local_docker_stack_files_exist() -> None:
    required_files = [
        "docker/test-docker-compose.yaml",
        "docker/init_test.sh",
        "docker/start_test_apache2.sh",
        "docker/start_test_postfix.sh",
        "docker/start_test_pyramid.sh",
        "docker/stop_clean_test.sh",
        "docker/README_TEST_LOCAL.md",
    ]

    missing = [path for path in required_files if not (REPO_ROOT / path).is_file()]

    assert missing == []


def test_test_stack_shell_scripts_are_syntax_valid() -> None:
    scripts = [
        "docker/init_test.sh",
        "docker/start_test_apache2.sh",
        "docker/start_test_postfix.sh",
        "docker/start_test_pyramid.sh",
        "docker/stop_clean_test.sh",
    ]

    for script in scripts:
        subprocess.run(
            ["bash", "-n", str(REPO_ROOT / script)],
            check=True,
            cwd=REPO_ROOT,
        )


def test_init_test_normalizes_waitress_bind_address_for_docker() -> None:
    script = read("docker/init_test.sh")

    assert "normalize_test_ini_for_docker" in script
    assert "listen = 0.0.0.0:6543" in script
    assert "localhost would only mean" in script

    # The normalisation must be executed during init, not merely defined.
    assert re.search(r"(?m)^normalize_test_ini_for_docker$", script)


def test_start_test_pyramid_rejects_localhost_only_bind_address() -> None:
    script = read("docker/start_test_pyramid.sh")

    assert "0.0.0.0:6543" in script
    assert "listen only on localhost" in script
    assert "localhost|127" in script or "127\\.0\\.0\\.1" in script


def test_test_compose_uses_test_container_names_only() -> None:
    compose = read("docker/test-docker-compose.yaml")

    expected_container_names = [
        "container_name: alirpunkto-test-ldap",
        "container_name: alirpunkto-test-postfix",
        "container_name: alirpunkto-test-pyramid",
        "container_name: alirpunkto-test-apache2",
    ]

    for expected in expected_container_names:
        assert expected in compose

    production_container_names = [
        "container_name: alirpunkto-ldap",
        "container_name: alirpunkto-postfix",
        "container_name: alirpunkto-pyramid",
        "container_name: alirpunkto-apache2",
    ]

    for forbidden in production_container_names:
        assert forbidden not in compose


def test_test_compose_binds_debug_ports_to_localhost_only() -> None:
    compose = read("docker/test-docker-compose.yaml")

    expected_bindings = [
        '"127.0.0.1:18389:389"',
        '"127.0.0.1:18636:636"',
        '"127.0.0.1:19025:25"',
        '"127.0.0.1:16543:6543"',
        '"127.0.0.1:8080:80"',
        '"127.0.0.1:8443:443"',
    ]

    for binding in expected_bindings:
        assert binding in compose

    # Catch accidental reintroduction of public host bindings such as "8443:443".
    publicly_bound_test_ports = re.findall(
        r'(?m)^\s*-\s*"(?:18389|18636|19025|16543|8080|8443):',
        compose,
    )
    assert publicly_bound_test_ports == []


def test_pyramid_healthcheck_uses_container_ip_not_localhost() -> None:
    compose = read("docker/test-docker-compose.yaml")

    assert "socket.gethostbyname(socket.gethostname())" in compose
    assert "http://localhost:6543/" not in compose


def test_apache_proxies_to_pyramid_service_name() -> None:
    compose = read("docker/test-docker-compose.yaml")
    apache = read("docker/start_test_apache2.sh")

    assert "APACHE_BACKEND_HOST: alirpunkto-test-pyramid" in compose
    assert "APACHE_BACKEND_PORT: 6543" in compose
    assert "ProxyPass / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/" in apache
    assert "ProxyPassReverse / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/" in apache


def test_postfix_test_stack_is_sink_only() -> None:
    compose = read("docker/test-docker-compose.yaml")
    postfix = read("docker/start_test_postfix.sh")

    assert 'POSTFIX_DISABLE_EXTERNAL_DELIVERY: "true"' in compose
    assert 'POSTFIX_RELAYHOST: ""' in compose
    assert "default_transport = discard:" in postfix
    assert "relay_transport = discard:" in postfix
    assert "local_transport = discard:" in postfix


def test_apache_test_stack_does_not_use_certbot() -> None:
    compose = read("docker/test-docker-compose.yaml")
    apache = read("docker/start_test_apache2.sh")

    assert 'ENABLE_CERTBOT: "false"' in compose
    assert "TEST_TLS_CERT" in compose
    assert "TEST_TLS_KEY" in compose
    assert "SSLCertificateFile ${TEST_TLS_CERT}" in apache
    assert "SSLCertificateKeyFile ${TEST_TLS_KEY}" in apache
