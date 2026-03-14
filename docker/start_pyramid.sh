#!/bin/bash
set -euo pipefail

APP_DIR="${APP_HOME:-/home/alirpunkto/app}"
VENV_DIR="${VENV_DIR:-/home/alirpunkto/venv}"
CONFIG_FILE="${1:-production.ini}"

if [ "$BUILD_WITH_DEBUG" = "1" ]; then
    echo "Debug image enabled."
fi

if [ ! -f "${APP_DIR}/setup.py" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
    echo "Application sources are missing in ${APP_DIR}" >&2
    exit 1
fi

mkdir -p \
    "${APP_DIR}/var/log" \
    "${APP_DIR}/var/datas" \
    "${APP_DIR}/var/filestorage" \
    "${APP_DIR}/var/sessions"

if [ ! -f "${APP_DIR}/.env" ] && [ -f "${APP_DIR}/.env.example" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    echo "Created ${APP_DIR}/.env from .env.example"
fi

if [ ! -f "${APP_DIR}/${CONFIG_FILE}" ]; then
    echo "Missing configuration file: ${APP_DIR}/${CONFIG_FILE}" >&2
    exit 1
fi

. "${VENV_DIR}/bin/activate"
cd "${APP_DIR}"

if [ "${INSTALL_EXTRAS_TESTING:-false}" = "true" ]; then
    pip install --no-cache-dir -e ".[testing]"
fi

echo "Starting Alirpunkto with ${CONFIG_FILE}"
exec pserve "${CONFIG_FILE}"
