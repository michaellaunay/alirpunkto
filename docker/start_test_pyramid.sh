#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_HOME:-/home/alirpunkto/app}"
VENV_DIR="${VENV_DIR:-/home/alirpunkto/venv}"
CONFIG_FILE="${1:-test.ini}"

if [ "${BUILD_WITH_DEBUG:-0}" = "1" ]; then
    echo "[Pyramid:test] Debug image enabled."
fi

if [ ! -f "${APP_DIR}/setup.py" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
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
    pip install --no-cache-dir -e ".[testing]"
fi

echo "[Pyramid:test] Starting AlirPunkto with ${CONFIG_FILE}"
echo "[Pyramid:test] LDAP=${LDAP_SERVER:-unset}:${LDAP_PORT:-unset} MAIL=${MAIL_HOST:-unset}:${MAIL_PORT:-unset}"
exec pserve "${CONFIG_FILE}"
