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

    # First issuance runs at boot, BEFORE Apache starts: port 80 is
    # free, standalone is the right mode here. The sed below then
    # migrates the renewal conf to the apache plugin, which is the
    # right mode for renewals that happen while Apache is running.
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "${LETSENCRYPT_EMAIL}" \
        -d "${APACHE_SERVER_NAME}"
fi

if [ "${ENABLE_CERTBOT}" = "true" ]; then
    # R3 — renew periodically, not only at startup. A container running longer
    # than a certificate's ~90-day lifetime without a restart would otherwise
    # serve an expired certificate. certbot reloads Apache (graceful) via the
    # deploy hook only when a certificate actually changes.
    # Renewal replays the authenticator recorded in the renewal conf.
    # Standalone would need port 80 while Apache (the container's
    # foreground process!) holds it — and stopping Apache kills the
    # container. The apache plugin (installed in the image) does the
    # challenge in-place and reloads by itself, so the loop stays
    # hook-free. Existing volumes issued with standalone are migrated
    # to the apache authenticator on the fly.
    for conf in /etc/letsencrypt/renewal/*.conf; do
        [ -f "$conf" ] && sed -i 's/^authenticator = standalone$/authenticator = apache/' "$conf"
    done
    certbot renew --quiet || true
    (
        while true; do
            # certbot's recommended cadence is twice a day; renewal is a no-op
            # until the cert is within its renewal window.
            sleep 12h
            certbot renew --quiet || true
        done
    ) &
fi

apache2ctl configtest
exec apache2ctl -D FOREGROUND
