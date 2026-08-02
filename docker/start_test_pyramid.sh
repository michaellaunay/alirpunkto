#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_HOME:-/home/alirpunkto/app}"
VENV_DIR="${VENV_DIR:-/home/alirpunkto/venv}"
CONFIG_FILE="${1:-test.ini}"

if [ "${BUILD_WITH_DEBUG:-0}" = "1" ]; then
    echo "[Pyramid:test] Debug image enabled."
fi

# Sixth audit pass (2026-08-01, §11.1/§11.4): the application is an
# installed wheel — the image ships no source tree, so the sanity check
# probes the venv instead of the old source-tree file checks.
if ! "${VENV_DIR}/bin/python" -c "import alirpunkto" 2>/dev/null; then
    echo "[Pyramid:test] The alirpunkto package is not installed in ${VENV_DIR}" >&2
    exit 1
fi

mkdir -p \
    "${APP_DIR}/var/log" \
    "${APP_DIR}/var/datas" \
    "${APP_DIR}/var/filestorage" \
    "${APP_DIR}/var/sessions"

if [ ! -f "${APP_DIR}/.env" ]; then
    echo "[Pyramid:test] Missing ${APP_DIR}/.env; run ./docker/init_test.sh first." >&2
    exit 1
fi

if [ ! -f "${APP_DIR}/${CONFIG_FILE}" ]; then
    echo "[Pyramid:test] Missing configuration file: ${APP_DIR}/${CONFIG_FILE}" >&2
    echo "[Pyramid:test] Run ./docker/init_test.sh to create test.ini from production.ini/development.ini." >&2
    exit 1
fi

. "${VENV_DIR}/bin/activate"
cd "${APP_DIR}"

if [ "${INSTALL_EXTRAS_TESTING:-false}" = "true" ]; then
    # Sixth audit pass (§11.4): the test lock left the image; the test
    # compose bind-mounts it read-only next to test.ini. The wheel
    # policy of the image applies here too, and the old editable
    # reinstall is gone — the image already carries the application.
    if [ ! -f "${APP_DIR}/requirements-test.lock" ]; then
        echo "[Pyramid:test] requirements-test.lock is missing: it is no longer baked into the image;" >&2
        echo "[Pyramid:test] test-docker-compose.yaml must bind-mount it (see its pyramid volumes)." >&2
        exit 1
    fi
    pip install --no-cache-dir --require-hashes \
        --only-binary=:all: \
        --no-binary=pyramid-chameleon,pyramid-handlers,validate-email \
        -r requirements-test.lock
fi

# Fourth audit pass (2026-08-01): same Docker override as the production
# start script — bind 0.0.0.0 inside the stack and trust the Apache
# container's address, through a derived copy of the config file.
if [ -n "${PYRAMID_LISTEN:-}" ] || [ -n "${PYRAMID_TRUSTED_PROXY:-}" ]; then
    GENERATED_CONFIG="${CONFIG_FILE%.ini}.generated.ini"
    python3 "${APP_DIR}/docker/apply_server_overrides.py" \
        "${APP_DIR}/${CONFIG_FILE}" "${APP_DIR}/${GENERATED_CONFIG}"
    CONFIG_FILE="${GENERATED_CONFIG}"
fi

echo "[Pyramid:test] Starting AlirPunkto with ${CONFIG_FILE}"
echo "[Pyramid:test] LDAP=${LDAP_SERVER:-unset}:${LDAP_PORT:-unset} MAIL=${MAIL_HOST:-unset}:${MAIL_PORT:-unset}"
exec pserve "${CONFIG_FILE}"
