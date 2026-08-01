#!/bin/bash
set -euo pipefail

APP_DIR="${APP_HOME:-/home/alirpunkto/app}"
VENV_DIR="${VENV_DIR:-/home/alirpunkto/venv}"
CONFIG_FILE="${1:-production.ini}"

if [ "$BUILD_WITH_DEBUG" = "1" ]; then
    echo "Debug image enabled."
fi

# Fourth audit pass (2026-08-01): the packaging patch retired setup.py
# for pyproject.toml — checking for the removed file stopped the
# container before pserve ever ran.
if [ ! -f "${APP_DIR}/pyproject.toml" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
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
    # Fourth audit pass (P1): install the hashed test lock, never the
    # unpinned extra — the image already carries the editable install.
    pip install --no-cache-dir --require-hashes -r requirements-test.lock
fi

# Fourth audit pass (2026-08-01): inside the compose stack Waitress must
# bind 0.0.0.0 (Apache lives in another container — this loopback is
# unreachable from it) and trust the Apache container's fixed address
# (127.0.0.1 would fold the whole login throttle onto one window). The
# config file is bind-mounted read-only and shared with the bare host,
# so a derived copy is written next to it (same directory keeps
# %(here)s pointing at the application root) and served instead.
if [ -n "${PYRAMID_LISTEN:-}" ] || [ -n "${PYRAMID_TRUSTED_PROXY:-}" ]; then
    GENERATED_CONFIG="${CONFIG_FILE%.ini}.generated.ini"
    python3 "${APP_DIR}/docker/apply_server_overrides.py" \
        "${APP_DIR}/${CONFIG_FILE}" "${APP_DIR}/${GENERATED_CONFIG}"
    CONFIG_FILE="${GENERATED_CONFIG}"
fi

echo "Starting Alirpunkto with ${CONFIG_FILE}"
exec pserve "${CONFIG_FILE}"
