#!/usr/bin/env bash
set -euo pipefail

APACHE_SERVER_NAME="${APACHE_SERVER_NAME:-alirpunkto.localhost}"
APACHE_SERVER_ALIASES="${APACHE_SERVER_ALIASES:-localhost alirpunkto.local 127.0.0.1}"
APACHE_BACKEND_HOST="${APACHE_BACKEND_HOST:-alirpunkto-test-pyramid}"
APACHE_BACKEND_PORT="${APACHE_BACKEND_PORT:-6543}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"
TEST_TLS_CERT="${TEST_TLS_CERT:-/etc/ssl/alirpunkto-test/fullchain.pem}"
TEST_TLS_KEY="${TEST_TLS_KEY:-/etc/ssl/alirpunkto-test/privkey.pem}"

mkdir -p /etc/apache2/sites-available /var/run/apache2 /var/log/apache2

a2enmod ssl rewrite proxy proxy_http headers remoteip >/dev/null

a2dissite 000-default.conf >/dev/null 2>&1 || true

if [ ! -f "${TEST_TLS_CERT}" ] || [ ! -f "${TEST_TLS_KEY}" ]; then
    echo "[Apache:test] Missing local TLS certificate:" >&2
    echo "  cert: ${TEST_TLS_CERT}" >&2
    echo "  key : ${TEST_TLS_KEY}" >&2
    echo "Run ./docker/init_test.sh from the repository root before starting the stack." >&2
    exit 1
fi

SERVER_ALIAS_LINE=""
if [ -n "${APACHE_SERVER_ALIASES}" ]; then
    SERVER_ALIAS_LINE="    ServerAlias ${APACHE_SERVER_ALIASES}"
fi

cat > /etc/apache2/sites-available/alirpunkto-test.conf <<EOF
<VirtualHost *:${HTTP_PORT}>
    ServerName ${APACHE_SERVER_NAME}
${SERVER_ALIAS_LINE}

    ProxyPreserveHost On
    ProxyPass / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/ retry=0
    ProxyPassReverse / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/

    RequestHeader set X-Forwarded-Proto "http"
    RequestHeader set X-Forwarded-Port "${HTTP_PORT}"

    ErrorLog \${APACHE_LOG_DIR}/alirpunkto-test-http-error.log
    CustomLog \${APACHE_LOG_DIR}/alirpunkto-test-http-access.log combined
</VirtualHost>

<VirtualHost *:${HTTPS_PORT}>
    ServerName ${APACHE_SERVER_NAME}
${SERVER_ALIAS_LINE}

    SSLEngine on
    SSLCertificateFile ${TEST_TLS_CERT}
    SSLCertificateKeyFile ${TEST_TLS_KEY}

    ProxyPreserveHost On
    ProxyPass / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/ retry=0
    ProxyPassReverse / http://${APACHE_BACKEND_HOST}:${APACHE_BACKEND_PORT}/

    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "${HTTPS_PORT}"
    Header always set Strict-Transport-Security "max-age=0"

    ErrorLog \${APACHE_LOG_DIR}/alirpunkto-test-https-error.log
    CustomLog \${APACHE_LOG_DIR}/alirpunkto-test-https-access.log combined
</VirtualHost>
EOF

a2ensite alirpunkto-test.conf >/dev/null

apache2ctl configtest
exec apache2ctl -D FOREGROUND
