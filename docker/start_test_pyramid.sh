#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_HOME:-/home/alirpunkto/app}"
VENV_DIR="${VENV_DIR:-/home/alirpunkto/venv}"
CONFIG_FILE="${1:-test.ini}"

if [ "${BUILD_WITH_DEBUG:-0}" = "1" ]; then
    echo "[Pyramid:test] Debug image enabled."
fi

# Fourth audit pass (2026-08-01): the packaging patch retired setup.py
# for pyproject.toml — checking for the removed file stopped the
# container before pserve ever ran.
if [ ! -f "${APP_DIR}/pyproject.toml" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
    echo "[Pyramid:test] Application sources are missing in ${APP_DIR}" >&2
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
    # Fourth audit pass (P1): the test stack installs the hashed test
    # lock (runtime + testing), not the runtime lock alone.
    pip install --no-cache-dir --require-hashes -r requirements-test.lock
    pip install --no-cache-dir -e . --no-deps
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
