#!/usr/bin/env bash
# =============================================================================
# docker/init_test.sh — non-interactive local/offline test setup for AlirPunkto
#
# Run from the REPOSITORY ROOT:
#   chmod +x docker/init_test.sh docker/start_test_*.sh
#   ./docker/init_test.sh
#
# Generates local-only test material:
#   docker/.env.test
#   docker/secrets/ldap_password_test
#   docker/initials_users.test.generated.ldif
#   docker/certs/local-test/fullchain.pem
#   docker/certs/local-test/privkey.pem
#   test.ini  (copied from production.ini or development.ini if absent)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
SECRETS_DIR="${DOCKER_DIR}/secrets"
CERT_DIR="${DOCKER_DIR}/certs/local-test"
ENV_FILE="${DOCKER_DIR}/.env.test"
LDIF_TEMPLATE="${DOCKER_DIR}/initials_users.ldif"
LDIF_OUT="${DOCKER_DIR}/initials_users.test.generated.ldif"
TEST_INI="${REPO_ROOT}/test.ini"

DOMAIN="${DOMAIN:-alirpunkto.localhost}"
APACHE_SERVER_NAME="${APACHE_SERVER_NAME:-${DOMAIN}}"
APACHE_SERVER_ALIASES="${APACHE_SERVER_ALIASES:-localhost alirpunkto.local 127.0.0.1}"
MAINTAINER_EMAIL="${MAINTAINER_EMAIL:-test-admin@${DOMAIN}}"
LDAP_ORGANIZATION="${LDAP_ORGANIZATION:-AlirPunkto Local Test}"
LDAP_BASE_DN="dc=$(echo "${DOMAIN}" | sed 's/\./,dc=/g')"
LDAP_PASSWORD="${LDAP_PASSWORD:-alirpunkto-test-ldap-password}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminTest123!}"
USER1_PASSWORD="${USER1_PASSWORD:-AliceTest123!}"
USER2_PASSWORD="${USER2_PASSWORD:-BobTest123!}"
ADMIN_UUID="${LDAP_ADMIN_OID:-00000000-0000-0000-0000-000000000001}"
USER1_UUID="${USER1_UUID:-11111111-1111-1111-1111-111111111111}"
USER2_UUID="${USER2_UUID:-22222222-2222-2222-2222-222222222222}"

info() { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }
success() { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m[WARN]\033[0m %s\n' "$*" >&2; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }

hash_ssha() {
    python3 - "$1" <<'PY'
import base64, hashlib, os, sys
password = sys.argv[1].encode("utf-8")
salt = os.urandom(8)
digest = hashlib.sha1(password + salt).digest()
print("{SSHA}" + base64.b64encode(digest + salt).decode("ascii"))
PY
}

generate_secret_key() {
    local generator="${REPO_ROOT}/alirpunkto/generate_secret.py"
    local secret=""
    if [ -f "${generator}" ]; then
        secret="$(python3 "${generator}" | sed -n 's/^SECRET_KEY="\([^"]*\)".*/\1/p' | head -n 1 || true)"
    fi
    if [ -z "${secret}" ]; then
        secret="$(python3 - <<'PY'
import base64, secrets
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
PY
)"
    fi
    printf '%s' "${secret}"
}

copy_test_ini_if_needed() {
    if [ -f "${TEST_INI}" ]; then
        info "Keeping existing test.ini"
        return
    fi

    if [ -f "${REPO_ROOT}/production.ini" ]; then
        cp "${REPO_ROOT}/production.ini" "${TEST_INI}"
        info "Created test.ini from production.ini"
    elif [ -f "${REPO_ROOT}/development.ini" ]; then
        cp "${REPO_ROOT}/development.ini" "${TEST_INI}"
        info "Created test.ini from development.ini"
    else
        error "Neither production.ini nor development.ini exists; cannot create test.ini."
        exit 1
    fi

    # Safe replacements in the local copy only. Review test.ini afterwards if the app has hard-coded public URLs.
    sed -i \
        -e "s/alirpunkto\.cosmopolitical\.coop/${APACHE_SERVER_NAME}/g" \
        -e "s/testalirpunkto\.cosmopolitical\.coop/${APACHE_SERVER_NAME}/g" \
        -e "s|https://alirpunkto\.cosmopolitical\.coop|https://${APACHE_SERVER_NAME}:8443|g" \
        -e "s|https://testalirpunkto\.cosmopolitical\.coop|https://${APACHE_SERVER_NAME}:8443|g" \
        "${TEST_INI}" || true
}

normalize_test_ini_for_docker() {
    if [ ! -f "${TEST_INI}" ]; then
        error "Missing ${TEST_INI}; cannot normalize Pyramid bind address."
        exit 1
    fi

    python3 - "${TEST_INI}" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

server_re = re.compile(r'(?ms)^(\[server:main\]\n)(.*?)(?=^\[|\Z)')
match = server_re.search(text)

if not match:
    raise SystemExit(f"[init_test] ERROR: no [server:main] section found in {path}")

body = match.group(2)
lines = body.splitlines()

new_lines = []
listen_written = False

for line in lines:
    # Force Waitress/Pyramid to listen on all interfaces inside the container.
    # localhost would only mean "inside the Pyramid container", and Apache would
    # get "connection refused" when proxying to alirpunkto-test-pyramid:6543.
    if re.match(r'^\s*listen\s*=', line):
        if not listen_written:
            new_lines.append("listen = 0.0.0.0:6543")
            listen_written = True
        continue

    # Avoid conflicting waitress options if the source ini used host/port.
    if re.match(r'^\s*(host|port)\s*=', line):
        continue

    new_lines.append(line)

    # If the source file had no listen= line, insert one just after use=.
    if not listen_written and re.match(r'^\s*use\s*=', line):
        new_lines.append("listen = 0.0.0.0:6543")
        listen_written = True

if not listen_written:
    new_lines.insert(0, "listen = 0.0.0.0:6543")

new_body = "\n".join(new_lines)
if body.endswith("\n"):
    new_body += "\n"

text = text[:match.start(2)] + new_body + text[match.end(2):]
path.write_text(text, encoding="utf-8")

print(f"[init_test] Normalized Pyramid bind address in {path}: listen = 0.0.0.0:6543")
PY

    success "Normalised test.ini for Docker networking."
}

generate_local_certificate() {
    mkdir -p "${CERT_DIR}"
    chmod 700 "${CERT_DIR}"

    local key="${CERT_DIR}/privkey.pem"
    local cert="${CERT_DIR}/fullchain.pem"
    local cfg="${CERT_DIR}/openssl-local-test.cnf"

    cat > "${cfg}" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = ${APACHE_SERVER_NAME}
O = AlirPunkto Local Test

[v3_req]
subjectAltName = @alt_names
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = ${APACHE_SERVER_NAME}
DNS.2 = localhost
DNS.3 = alirpunkto.local
DNS.4 = mail.${DOMAIN}
IP.1 = 127.0.0.1
EOF

    if [ ! -f "${key}" ] || [ ! -f "${cert}" ]; then
        if ! command -v openssl >/dev/null 2>&1; then
            error "openssl is required to generate the local test certificate. Install it with: sudo apt install openssl"
            exit 1
        fi
        openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
            -keyout "${key}" \
            -out "${cert}" \
            -config "${cfg}" >/dev/null 2>&1
        chmod 600 "${key}"
        chmod 644 "${cert}"
        success "Generated local self-signed TLS certificate in docker/certs/local-test/"
    else
        info "Keeping existing local TLS certificate"
    fi
}

generate_env_file() {
    local secret_key
    secret_key="$(generate_secret_key)"

    mkdir -p "${SECRETS_DIR}"
    chmod 700 "${SECRETS_DIR}"
    (umask 077; printf '%s' "${LDAP_PASSWORD}" > "${SECRETS_DIR}/ldap_password_test")

    cat > "${ENV_FILE}" <<EOF
# Generated by docker/init_test.sh — $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Local/offline test configuration. Do not use these credentials in production.

BUILD_WITH_DEBUG=1
INSTALL_EXTRAS_TESTING=false
DEBUG_LDAP=false

DOMAIN="${DOMAIN}"
MAINTAINER_EMAIL="${MAINTAINER_EMAIL}"
SECRET_KEY="${secret_key}"

LDAP_SERVER="alirpunkto-test-ldap"
LDAP_PORT=389
LDAP_BASE_DN="${LDAP_BASE_DN}"
LDAP_ORGANIZATION="${LDAP_ORGANIZATION}"
LDAP_LOGIN="cn=admin"
LDAP_OU=""
LDAP_PASSWORD="${LDAP_PASSWORD}"
LDAP_USE_SSL=false
LDAP_PASSWORD_FILE=/run/secrets/ldap_password
LDAP_ADMIN_OID="${ADMIN_UUID}"

APACHE_SERVER_NAME="${APACHE_SERVER_NAME}"
APACHE_SERVER_ALIASES="${APACHE_SERVER_ALIASES}"
APACHE_BACKEND_HOST=alirpunkto-test-pyramid
APACHE_BACKEND_PORT=6543
ENABLE_CERTBOT=false
LETSENCRYPT_EMAIL=""

POSTFIX_MYHOSTNAME="mail.${DOMAIN}"
POSTFIX_RELAYHOST=""
POSTFIX_INET_PROTOCOLS=ipv4
POSTFIX_MESSAGE_SIZE_LIMIT=26214400
POSTFIX_TEST_MODE=true
POSTFIX_DISABLE_EXTERNAL_DELIVERY=true

MAIL_SERVER=alirpunkto-test-postfix
MAIL_HOST=alirpunkto-test-postfix
MAIL_PORT=25
MAIL_SENDER="test-admin@${DOMAIN}"
MAIL_USERNAME=None
MAIL_PASSWORD=None
MAIL_TLS=false
MAIL_SSL=false

ADMIN_LOGIN="admin"
ADMIN_EMAIL="admin@${DOMAIN}"
ADMIN_PASSWORD="${ADMIN_PASSWORD}"

KEYCLOAK_SERVER_URL=""
KEYCLOAK_REALM=""
KEYCLOAK_CLIENT_ID=""
KEYCLOAK_CLIENT_SECRET=""
EOF

    success "Written docker/.env.test and docker/secrets/ldap_password_test"
}

generate_test_ldif() {
    if [ ! -f "${LDIF_TEMPLATE}" ]; then
        error "Template not found: ${LDIF_TEMPLATE}"
        exit 1
    fi

    local admin_hash user1_hash user2_hash today
    admin_hash="$(hash_ssha "${ADMIN_PASSWORD}")"
    user1_hash="$(hash_ssha "${USER1_PASSWORD}")"
    user2_hash="$(hash_ssha "${USER2_PASSWORD}")"
    today="$(date -u +"%Y-%m-%dT%H:%M:%S")"

    python3 "${DOCKER_DIR}/generate_ldif.py" \
        "${LDIF_TEMPLATE}" \
        "${LDIF_OUT}" \
        "${LDAP_BASE_DN}" \
        "${ADMIN_UUID}" "admin" "admin.test" "admin@${DOMAIN}" "${admin_hash}" \
        "${USER1_UUID}" "ADMINISTRATOR" "alice.test" "Alice" "Test" "fr" "FR" "alice@${DOMAIN}" "${user1_hash}" \
        "${USER2_UUID}" "ORDINARY_MEMBER" "bob.test" "Bob" "Test" "fr" "FR" "bob@${DOMAIN}" "${user2_hash}" \
        "${today}" \
        "en" "" "1990-01-01T12:00:00" "Local test administrator account" \
        "" "" "1991-01-01T12:00:00" "Local test ordinary member account"

    success "Written docker/initials_users.test.generated.ldif"
}

info "Repository root: ${REPO_ROOT}"
info "Local test domain: ${DOMAIN}"

generate_env_file
generate_test_ldif
generate_local_certificate
copy_test_ini_if_needed
normalize_test_ini_for_docker

cat <<EOF

Local test setup generated.

Recommended /etc/hosts entry:
  127.0.0.1 ${APACHE_SERVER_NAME} alirpunkto.local mail.${DOMAIN}

Start the stack:
  docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build

Open:
  https://${APACHE_SERVER_NAME}:8443/

Test accounts:
  admin.test / ${ADMIN_PASSWORD}
  alice.test / ${USER1_PASSWORD}
  bob.test   / ${USER2_PASSWORD}

Postfix is in local sink mode: it accepts mail from Pyramid but does not relay to the Internet.
EOF
