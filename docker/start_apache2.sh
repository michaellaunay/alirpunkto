#!/bin/bash
set -euo pipefail

APACHE_SERVER_NAME="${APACHE_SERVER_NAME:-alirpunkto.com}"
APACHE_SERVER_ALIASES="${APACHE_SERVER_ALIASES:-}"
APACHE_BACKEND_HOST="${APACHE_BACKEND_HOST:-alirpunkto-pyramid}"
APACHE_BACKEND_PORT="${APACHE_BACKEND_PORT:-6543}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
ENABLE_CERTBOT="${ENABLE_CERTBOT:-false}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"

export APACHE_SERVER_NAME APACHE_SERVER_ALIASES APACHE_BACKEND_HOST APACHE_BACKEND_PORT HTTP_PORT HTTPS_PORT

mkdir -p /etc/apache2/sites-available /var/run/apache2
envsubst '${APACHE_SERVER_NAME} ${APACHE_SERVER_ALIASES} ${APACHE_BACKEND_HOST} ${APACHE_BACKEND_PORT} ${HTTP_PORT} ${HTTPS_PORT}' \
    < /templates/alirpunkto.conf.template \
    > /etc/apache2/sites-available/alirpunkto.conf

a2ensite alirpunkto.conf >/dev/null

CERT_PATH="/etc/letsencrypt/live/${APACHE_SERVER_NAME}/fullchain.pem"
if [ "${ENABLE_CERTBOT}" = "true" ] && [ ! -f "${CERT_PATH}" ]; then
    if [ -z "${LETSENCRYPT_EMAIL}" ]; then
        echo "LETSENCRYPT_EMAIL must be set when ENABLE_CERTBOT=true" >&2
        exit 1
    fi

    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "${LETSENCRYPT_EMAIL}" \
        -d "${APACHE_SERVER_NAME}"
fi

if [ "${ENABLE_CERTBOT}" = "true" ]; then
    certbot renew --quiet || true
fi

apache2ctl configtest
exec apache2ctl -D FOREGROUND
