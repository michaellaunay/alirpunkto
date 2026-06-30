from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


DOCKER_FILES = [
    "docker/init_test.sh",
    "docker/start_test_apache2.sh",
    "docker/start_test_postfix.sh",
    "docker/start_test_pyramid.sh",
    "docker/stop_clean_test.sh",
    "docker/test-docker-compose.yaml",
    "docker/README_TEST_LOCAL.md",
]

SHELL_FILES = [
    "docker/init_test.sh",
    "docker/start_test_apache2.sh",
    "docker/start_test_postfix.sh",
    "docker/start_test_pyramid.sh",
    "docker/stop_clean_test.sh",
    "tests/run-tests-docker-ldap.sh",
    "tools/export_sources_for_review.sh",
]


@pytest.mark.parametrize("relative_path", DOCKER_FILES)
def test_local_docker_stack_files_exist(repo_root: Path, relative_path: str):
    assert (repo_root / relative_path).is_file(), f"Missing {relative_path}"


@pytest.mark.parametrize("relative_path", SHELL_FILES)
def test_shell_scripts_are_syntax_valid(repo_root: Path, relative_path: str):
    path = repo_root / relative_path
    assert path.is_file(), f"Missing {relative_path}"
    subprocess.run(["bash", "-n", str(path)], check=True)


def test_init_test_normalizes_waitress_bind_address(repo_root: Path):
    script = (repo_root / "docker/init_test.sh").read_text(encoding="utf-8")

    assert "normalize_test_ini_for_docker" in script
    assert "listen = 0.0.0.0:6543" in script
    assert "localhost would only mean" in script
    assert re.search(r"copy_test_ini_if_needed\s*\nnormalize_test_ini_for_docker", script)


def test_test_compose_uses_isolated_container_names(repo_root: Path):
    compose = (repo_root / "docker/test-docker-compose.yaml").read_text(encoding="utf-8")

    for service in ("ldap", "postfix", "pyramid", "apache2"):
        assert f"container_name: alirpunkto-test-{service}" in compose
        assert f"image: alirpunkto-test-{service}" in compose

    assert "container_name: alirpunkto-ldap\n" not in compose
    assert "container_name: alirpunkto-pyramid\n" not in compose
    assert "container_name: alirpunkto-apache2\n" not in compose


def test_test_compose_exposes_only_localhost_debug_ports(repo_root: Path):
    compose = (repo_root / "docker/test-docker-compose.yaml").read_text(encoding="utf-8")

    expected_ports = [
        "127.0.0.1:18389:389",
        "127.0.0.1:18636:636",
        "127.0.0.1:19025:25",
        "127.0.0.1:16543:6543",
        "127.0.0.1:8080:80",
        "127.0.0.1:8443:443",
    ]
    for port in expected_ports:
        assert port in compose

    assert re.search(r'^\s+- "(?!127\.0\.0\.1:)[0-9]+:', compose, re.MULTILINE) is None


def test_test_compose_keeps_postfix_in_sink_mode(repo_root: Path):
    compose = (repo_root / "docker/test-docker-compose.yaml").read_text(encoding="utf-8")
    postfix = (repo_root / "docker/start_test_postfix.sh").read_text(encoding="utf-8")

    assert 'POSTFIX_TEST_MODE: "true"' in compose
    assert 'POSTFIX_DISABLE_EXTERNAL_DELIVERY: "true"' in compose
    assert 'POSTFIX_RELAYHOST: ""' in compose
    assert "default_transport = discard:" in postfix
    assert "relay_transport = discard:" in postfix
    assert "disable_dns_lookups = yes" in postfix


def test_test_compose_configures_apache_as_local_reverse_proxy(repo_root: Path):
    compose = (repo_root / "docker/test-docker-compose.yaml").read_text(encoding="utf-8")
    apache = (repo_root / "docker/start_test_apache2.sh").read_text(encoding="utf-8")

    assert "APACHE_BACKEND_HOST: alirpunkto-test-pyramid" in compose
    assert "APACHE_BACKEND_PORT: 6543" in compose
    assert 'ENABLE_CERTBOT: "false"' in compose
    assert "TEST_TLS_CERT" in compose
    assert "ProxyPass / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/" in apache
    assert "SSLCertificateFile ${TEST_TLS_CERT}" in apache


def test_pyramid_healthcheck_detects_container_network_bind(repo_root: Path):
    compose = (repo_root / "docker/test-docker-compose.yaml").read_text(encoding="utf-8")

    assert "socket.gethostbyname(socket.gethostname())" in compose
    assert "http://localhost:6543" not in compose
    assert "test.ini:/home/alirpunkto/app/test.ini:ro" in compose


def test_local_readme_documents_generated_files_and_ports(repo_root: Path):
    readme = (repo_root / "docker/README_TEST_LOCAL.md").read_text(encoding="utf-8")

    for generated in (
        "docker/.env.test",
        "docker/secrets/ldap_password_test",
        "docker/initials_users.test.generated.ldif",
        "docker/certs/local-test/fullchain.pem",
        "test.ini",
    ):
        assert generated in readme

    for port in ("8080", "8443", "16543", "18389", "18636", "19025"):
        assert port in readme
