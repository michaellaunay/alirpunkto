#!/usr/bin/env bash
# =============================================================================
# docker/init.sh — First-run interactive configurator for AlirPunkto
#
# Run from the REPOSITORY ROOT:
#   chmod +x docker/init.sh
#   ./docker/init.sh
#
# Generates:
#   docker/.env
#   docker/secrets/ldap_password
#   docker/initials_users.generated.ldif
# =============================================================================
set -euo pipefail

# ── Anchor to repo root ───────────────────────────────────────────────────────
# The script lives in docker/; we want all paths relative to the repo root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
SECRETS_DIR="${DOCKER_DIR}/secrets"
ENV_FILE="${DOCKER_DIR}/.env"
LDIF_TEMPLATE="${DOCKER_DIR}/initials_users.ldif"
LDIF_OUT="${DOCKER_DIR}/initials_users.generated.ldif"

# ── helpers ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}${BOLD}[OK]${RESET}    $*"; }
error()   { echo -e "${RED}${BOLD}[ERROR]${RESET} $*" >&2; }

ask() {
    # ask <var_name> <prompt> [default]
    local var="$1" prompt="$2" default="${3:-}"
    local value=""
    while [ -z "$value" ]; do
        if [ -n "$default" ]; then
            read -rp "$(echo -e "${BOLD}${prompt}${RESET} [${default}]: ")" value
            value="${value:-$default}"
        else
            read -rp "$(echo -e "${BOLD}${prompt}${RESET}: ")" value
        fi
        [ -z "$value" ] && error "This field is required."
    done
    printf -v "$var" '%s' "$value"
}

ask_optional() {
    # ask_optional <var_name> <prompt>  — empty answer is accepted
    local var="$1" prompt="$2"
    local value=""
    read -rp "$(echo -e "${BOLD}${prompt}${RESET} (leave empty to skip): ")" value
    printf -v "$var" '%s' "$value"
}

ask_secret() {
    # ask_secret <var_name> <prompt>
    local var="$1" prompt="$2"
    local value="" confirm=""
    while true; do
        read -rsp "$(echo -e "${BOLD}${prompt}${RESET}: ")" value; echo
        [ -z "$value" ] && { error "Password cannot be empty."; continue; }
        read -rsp "$(echo -e "${BOLD}Confirm password${RESET}: ")" confirm; echo
        [ "$value" = "$confirm" ] && break
        error "Passwords do not match, please try again."
    done
    printf -v "$var" '%s' "$value"
}

ask_role() {
    # ask_role <var_name> <user_label>
    local var="$1" label="$2"
    echo -e "${BOLD}Role for ${label}:${RESET}"
    local roles=("COPERATOR" "ORDINARY_MEMBER" "BOARD_MEMBER" "ADMINISTRATOR")
    local i=1
    for r in "${roles[@]}"; do echo "  $i) $r"; ((i++)); done
    local choice=""
    while true; do
        read -rp "$(echo -e "${BOLD}Choice [1-${#roles[@]}]${RESET}: ")" choice
        if [[ "$choice" =~ ^[1-4]$ ]]; then
            printf -v "$var" '%s' "${roles[$((choice-1))]}"
            break
        fi
        error "Enter a number between 1 and ${#roles[@]}."
    done
}

generate_uuid() {
    if command -v uuidgen &>/dev/null; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    else
        cat /proc/sys/kernel/random/uuid
    fi
}

hash_password() {
    if command -v slappasswd &>/dev/null; then
        slappasswd -s "$1"
    else
        error "slappasswd not found — password stored in cleartext." \
              "Install package 'slapd' locally to fix this."
        echo "$1"
    fi
}

# ── guard: already initialised ───────────────────────────────────────────────

if [ -f "${ENV_FILE}" ]; then
    echo -e "${BOLD}A configuration already exists at ${ENV_FILE}.${RESET}"
    read -rp "Re-run initialisation and overwrite it? [y/N]: " overwrite
    [[ "${overwrite,,}" == "y" ]] || { info "Aborting — existing configuration kept."; exit 0; }
fi

# ── banner ────────────────────────────────────────────────────────────────────

echo
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║     AlirPunkto — first-run setup         ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo
info "Repository root : ${REPO_ROOT}"
info "Docker dir      : ${DOCKER_DIR}"
echo

# ── general settings ──────────────────────────────────────────────────────────

info "=== General settings ==="
ask DOMAIN            "Domain name (e.g. alirpunkto.com)"
ask MAINTAINER_EMAIL  "Maintainer e-mail"
ask LDAP_ORGANIZATION "Organisation name" "AlirPunkto"

LDAP_BASE_DN="dc=$(echo "$DOMAIN" | sed 's/\./,dc=/g')"
info "LDAP base DN will be: ${LDAP_BASE_DN}"

ask_secret LDAP_PASSWORD "LDAP admin password"
ask LDAP_LOGIN "LDAP admin login (DN prefix)" "cn=admin"
ask_optional LDAP_OU "LDAP organisational unit (leave empty if none)"

# ── application secret key ───────────────────────────────────────────────────────────────
# Use the project's own generator if available; fall back to a Python one-liner.
# alirpunkto/generate_secret.py is the canonical way documented in the README.
GENERATE_SECRET="${REPO_ROOT}/alirpunkto/generate_secret.py"
if [ -f "${GENERATE_SECRET}" ]; then
    SECRET_KEY="$(python3 "${GENERATE_SECRET}")"
    info "SECRET_KEY generated via alirpunkto/generate_secret.py"
else
    SECRET_KEY="$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")"
    error "alirpunkto/generate_secret.py not found — used fallback generator."
fi
info "SECRET_KEY written to .env (never share or commit it)."

# ── application admin account ───────────────────────────────────────────────────────────────

echo
info "=== Application admin account ==="
ask ADMIN_LOGIN    "Admin login" "admin"
ask ADMIN_EMAIL    "Admin e-mail" "${MAINTAINER_EMAIL}"
ask_secret ADMIN_PASSWORD "Admin password"

# ── first user ────────────────────────────────────────────────────────────────

echo
info "=== First user ==="
ask USER1_FIRSTNAME   "First name"
ask USER1_LASTNAME    "Last name"
ask USER1_EMAIL       "E-mail"
ask USER1_LANG        "Preferred language (ISO 639-1)" "fr"
ask USER1_NATIONALITY "Nationality (ISO 3166-1 alpha-2)" "FR"
ask_role USER1_ROLE   "${USER1_FIRSTNAME} ${USER1_LASTNAME}"
ask_secret USER1_PASSWORD "Password for ${USER1_FIRSTNAME} ${USER1_LASTNAME}"
USER1_UUID="$(generate_uuid)"

# ── second user ───────────────────────────────────────────────────────────────

echo
info "=== Second user ==="
ask USER2_FIRSTNAME   "First name"
ask USER2_LASTNAME    "Last name"
ask USER2_EMAIL       "E-mail"
ask USER2_LANG        "Preferred language (ISO 639-1)" "fr"
ask USER2_NATIONALITY "Nationality (ISO 3166-1 alpha-2)" "FR"
ask_role USER2_ROLE   "${USER2_FIRSTNAME} ${USER2_LASTNAME}"
ask_secret USER2_PASSWORD "Password for ${USER2_FIRSTNAME} ${USER2_LASTNAME}"
USER2_UUID="$(generate_uuid)"

# ── Apache / TLS ──────────────────────────────────────────────────────────────

echo
info "=== Apache / TLS settings ==="
ask APACHE_SERVER_NAME "Public hostname for Apache" "$DOMAIN"
ask LETSENCRYPT_EMAIL  "Let's Encrypt e-mail" "$MAINTAINER_EMAIL"
read -rp "$(echo -e "${BOLD}Enable Certbot (request TLS certificate now)? [y/N]${RESET}: ")" certbot_yn
ENABLE_CERTBOT="false"
[[ "${certbot_yn,,}" == "y" ]] && ENABLE_CERTBOT="true"

# ── Postfix ───────────────────────────────────────────────────────────────────

echo
info "=== Postfix settings ==="
ask POSTFIX_MYHOSTNAME "Mail hostname" "mail.${DOMAIN}"
ask_optional POSTFIX_RELAYHOST "Relay host (e.g. [smtp.provider.example]:587)"
ask MAIL_SENDER    "Mail sender address (From:)" "${MAINTAINER_EMAIL}"
ask MAIL_PORT      "SMTP port used by Pyramid to reach Postfix" "9025"
ask_optional MAIL_USERNAME "SMTP auth username (leave empty if none)"
if [ -n "${MAIL_USERNAME}" ]; then
    ask_secret MAIL_PASSWORD "SMTP auth password"
else
    MAIL_PASSWORD="None"
fi

# ── write docker/.env ─────────────────────────────────────────────────────────

mkdir -p "${DOCKER_DIR}"
cat > "${ENV_FILE}" <<EOF
# Generated by docker/init.sh — $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Do NOT commit this file to version control.

# ── General ───────────────────────────────────────────────────────────────────
DOMAIN=${DOMAIN}
MAINTAINER_EMAIL=${MAINTAINER_EMAIL}

# ── Application ───────────────────────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}

# ── LDAP ──────────────────────────────────────────────────────────────────────
LDAP_BASE_DN=${LDAP_BASE_DN}
LDAP_ORGANIZATION=${LDAP_ORGANIZATION}
LDAP_LOGIN=${LDAP_LOGIN}
LDAP_OU=${LDAP_OU}
LDAP_PASSWORD_FILE=/run/secrets/ldap_password

# ── Apache ────────────────────────────────────────────────────────────────────
APACHE_SERVER_NAME=${APACHE_SERVER_NAME}
APACHE_BACKEND_HOST=alirpunkto-pyramid
APACHE_BACKEND_PORT=6543
ENABLE_CERTBOT=${ENABLE_CERTBOT}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}

# ── Postfix ───────────────────────────────────────────────────────────────────
POSTFIX_MYHOSTNAME=${POSTFIX_MYHOSTNAME}
POSTFIX_RELAYHOST=${POSTFIX_RELAYHOST}
POSTFIX_INET_PROTOCOLS=ipv4

# ── Mail (Pyramid → SMTP) ─────────────────────────────────────────────────────
MAIL_SERVER=alirpunkto-postfix
MAIL_PORT=${MAIL_PORT}
MAIL_SENDER=${MAIL_SENDER}
MAIL_USERNAME=${MAIL_USERNAME}
MAIL_PASSWORD=${MAIL_PASSWORD}

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN_LOGIN=${ADMIN_LOGIN}
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ── Pyramid ───────────────────────────────────────────────────────────────────
LDAP_SERVER=alirpunkto-ldap
LDAP_PORT=389
MAIL_HOST=alirpunkto-postfix
EOF
success "docker/.env written."

# ── write docker/secrets/ldap_password ───────────────────────────────────────

mkdir -p "${SECRETS_DIR}"
chmod 700 "${SECRETS_DIR}"
(umask 077; printf '%s' "${LDAP_PASSWORD}" > "${SECRETS_DIR}/ldap_password")
success "docker/secrets/ldap_password written."

# ── hash passwords ────────────────────────────────────────────────────────────

USER1_HASHED_PW="$(hash_password "${USER1_PASSWORD}")"
USER2_HASHED_PW="$(hash_password "${USER2_PASSWORD}")"
TODAY="$(date -u +"%Y-%m-%dT%H:%M:%S")"

# ── generate initials_users.generated.ldif ────────────────────────────────────

if [ ! -f "${LDIF_TEMPLATE}" ]; then
    error "Template not found: ${LDIF_TEMPLATE}"
    exit 1
fi

# Replace the placeholder base DN with the real one and strip the two
# hardcoded test users (keep only the admin placeholder uniqueMember).
sed "s|dc=alirpunkto,dc=org|${LDAP_BASE_DN}|g" "${LDIF_TEMPLATE}" \
    | grep -v "^uniqueMember: uid=[^0]" \
    > "${LDIF_OUT}"

# Append bootstrap users
cat >> "${LDIF_OUT}" <<EOF

# =====================
# Users
# =====================

dn: uid=${USER1_UUID},${LDAP_BASE_DN}
objectClass: inetOrgPerson
objectClass: alirpunktoPerson
uid: ${USER1_UUID}
sn: ${USER1_LASTNAME}
cn: ${USER1_FIRSTNAME} ${USER1_LASTNAME}
employeeNumber: ${USER1_UUID}
employeeType: ${USER1_ROLE}
isActive: TRUE
preferredLanguage: ${USER1_LANG}
givenName: ${USER1_FIRSTNAME}
nationality: ${USER1_NATIONALITY}
cooperativeBehaviourMark: 0
mail: ${USER1_EMAIL}
userPassword: ${USER1_HASHED_PW}
numberSharesOwned: 1
dateEndValidityYearlyContribution: ${TODAY}

dn: uid=${USER2_UUID},${LDAP_BASE_DN}
objectClass: inetOrgPerson
objectClass: alirpunktoPerson
uid: ${USER2_UUID}
sn: ${USER2_LASTNAME}
cn: ${USER2_FIRSTNAME} ${USER2_LASTNAME}
employeeNumber: ${USER2_UUID}
employeeType: ${USER2_ROLE}
isActive: TRUE
preferredLanguage: ${USER2_LANG}
givenName: ${USER2_FIRSTNAME}
nationality: ${USER2_NATIONALITY}
cooperativeBehaviourMark: 0
mail: ${USER2_EMAIL}
userPassword: ${USER2_HASHED_PW}
numberSharesOwned: 1
dateEndValidityYearlyContribution: ${TODAY}
EOF

success "docker/initials_users.generated.ldif written."

# ── add group memberships for new users ──────────────────────────────────────

add_member_to_group() {
    local uuid="$1" role="$2"
    local dn="uid=${uuid},${LDAP_BASE_DN}"
    local groups=("communityMembersGroup")
    case "$role" in
        COPERATOR)       groups+=("coperatorsGroup") ;;
        ORDINARY_MEMBER) groups+=("ordinaryMembersGroup") ;;
        BOARD_MEMBER)    groups+=("boardMembersGroup" "coperatorsGroup") ;;
        ADMINISTRATOR)   groups+=("administratorsGroup" "coperatorsGroup") ;;
    esac
    for g in "${groups[@]}"; do
        # Insert the new uniqueMember line after the last existing one for that group
        sed -i "/^cn: ${g}$/,/^$/ {
            /^uniqueMember:/ { h; d }
            /^$/ { x; /./{ p; x }; x }
        }" "${LDIF_OUT}" 2>/dev/null || true
        # Simpler fallback: append after the group block's last uniqueMember
        perl -i -0pe \
            "s|(cn: ${g}\n(?:.*\n)*?)(uniqueMember: [^\n]+\n)(?!uniqueMember)|\${1}\${2}uniqueMember: ${dn}\n|" \
            "${LDIF_OUT}" 2>/dev/null || true
    done
}

add_member_to_group "${USER1_UUID}" "${USER1_ROLE}"
add_member_to_group "${USER2_UUID}" "${USER2_ROLE}"

success "Group memberships updated."

# ── summary ───────────────────────────────────────────────────────────────────

echo
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  Configuration complete!${RESET}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${RESET}"
echo
echo -e "  Domain       : ${BOLD}${DOMAIN}${RESET}"
echo -e "  LDAP base DN : ${BOLD}${LDAP_BASE_DN}${RESET}"
echo -e "  User 1       : ${BOLD}${USER1_FIRSTNAME} ${USER1_LASTNAME}${RESET} <${USER1_EMAIL}> — ${USER1_ROLE} [${USER1_UUID}]"
echo -e "  User 2       : ${BOLD}${USER2_FIRSTNAME} ${USER2_LASTNAME}${RESET} <${USER2_EMAIL}> — ${USER2_ROLE} [${USER2_UUID}]"
echo
echo -e "Next step:"
echo -e "  ${CYAN}${BOLD}docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d${RESET}"
echo
