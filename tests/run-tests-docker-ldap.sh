#!/usr/bin/env bash
set -euo pipefail

# Run the pytest suite against the current local Docker test stack.
# The legacy LDAP-only compose file has been replaced by docker/test-docker-compose.yaml.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="docker/test-docker-compose.yaml"
ENV_FILE="docker/.env.test"

cd "${REPO_ROOT}"

compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    elif command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        echo "ERROR: neither 'docker compose' nor 'docker-compose' is available." >&2
        exit 1
    fi
}

cleanup() {
    compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "ERROR: ${COMPOSE_FILE} does not exist." >&2
    exit 1
fi

./docker/init_test.sh

compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build ldap postfix pyramid apache2

export TEST_WITH_DOCKER_LDAP=true
export TEST_WITH_DOCKER_LDAP_SERVER=localhost
export TEST_WITH_DOCKER_LDAP_PORT=18389
export DISABLE_EMAIL_MX_CHECKS=true

python -m pytest tests/ --use-docker-ldap -v "$@"
