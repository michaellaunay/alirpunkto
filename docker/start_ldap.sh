#!/bin/bash
set -euo pipefail
set -x

# Ensure LDAP directories exist with correct ownership.
mkdir -p /etc/ldap /var/lib/ldap
chown -R openldap:openldap /etc/ldap /var/lib/ldap

DEBUG_LDAP=${DEBUG_LDAP:-false}
LDIF_PATH="${INITIAL_USERS_LDIF:-/initials_users.ldif}"
LDIF_SCHEMA="${LDAP_SCHEMA_LDIF:-/schema/alirpunkto_schema.ldif}"
MARKER_PATH="${LDAP_INIT_MARKER:-/var/lib/ldap/.initials_users_loaded}"
LDAP_URI="${LDAP_URI:-ldap://localhost}"
LDAPI_URI="${LDAPI_URI:-ldapi:///}"
CONFIG_MARKER_PATH="${LDAP_CONFIG_MARKER:-/var/lib/ldap/.slapd_configured}"
LDAP_PASSWORD_FILE="${LDAP_PASSWORD_FILE:-/run/secrets/ldap_password}"

# Read password from secret if not provided
if [ -z "${LDAP_PASSWORD:-}" ]; then
  if [ -f "$LDAP_PASSWORD_FILE" ]; then
    echo "Retrieving password from $LDAP_PASSWORD_FILE"
    LDAP_PASSWORD="$(cat "$LDAP_PASSWORD_FILE")"
  else
    echo "You must provide LDAP_PASSWORD or create $LDAP_PASSWORD_FILE"
    exit 1
  fi
fi


# Build domain from base DN
if [ -n "${LDAP_BASE_DN:-}" ]; then
  LDAP_DOMAIN="$(echo "$LDAP_BASE_DN" | tr -d ' ' | sed -e 's/dc=//g' -e 's/,/./g')"
fi

# Configure slapd only once
if [ ! -f "$CONFIG_MARKER_PATH" ] && [ -n "${LDAP_BASE_DN:-}" ] && [ -n "${LDAP_PASSWORD:-}" ]; then
  LDAP_ORGANIZATION="${LDAP_ORGANIZATION:-$LDAP_DOMAIN}"

  if [[ "${DEBUG_LDAP}" = "true" ]]; then
    echo "debconf-set-selections <<EOF" \
      "slapd slapd/no_configuration boolean false" \
      "slapd slapd/domain string $LDAP_DOMAIN" \
      "slapd shared/organization string $LDAP_ORGANIZATION" \
      "slapd slapd/password1 password $LDAP_PASSWORD" \
      "slapd slapd/password2 password $LDAP_PASSWORD" \
      "slapd slapd/backend select MDB" \
      "slapd slapd/purge_database boolean true" \
      "slapd slapd/move_old_database boolean true" \
      "slapd slapd/allow_ldap_v2 boolean false" \
      "slapd slapd/dump_database select when needed" \
      "slapd slapd/dump_database_destdir string /var/backups/slapd-VERSION" \
      "EOF"
  fi
  debconf-set-selections <<EOF
slapd slapd/no_configuration boolean false
slapd slapd/domain string $LDAP_DOMAIN
slapd shared/organization string $LDAP_ORGANIZATION
slapd slapd/password1 password $LDAP_PASSWORD
slapd slapd/password2 password $LDAP_PASSWORD
slapd slapd/backend select MDB
slapd slapd/purge_database boolean true
slapd slapd/move_old_database boolean true
slapd slapd/allow_ldap_v2 boolean false
slapd slapd/dump_database select when needed
slapd slapd/dump_database_destdir string /var/backups/slapd-VERSION
EOF

  dpkg-reconfigure -f noninteractive slapd
  touch "$CONFIG_MARKER_PATH"
fi

args=("$@")
if [ "${#args[@]}" -eq 0 ]; then
  args=(slapd -h "ldap:/// ldapi:/// ldaps:///" -g openldap -u openldap -d 256)
fi

# Only run initialization when starting slapd.
if [ "${args[0]}" = "slapd" ]; then
  "${args[@]}" &
  slapd_pid=$!

  echo "Waiting for slapd to be ready..."
  for _ in $(seq 1 30); do
    if ldapsearch -x -H "$LDAP_URI" -s base -b "" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  # Load custom schema if provided
  if [ -f "$LDIF_SCHEMA" ]; then
    echo "Loading custom schema -H $LDAPI_URI -f $LDIF_SCHEMA..."
    ldapadd -Y EXTERNAL -H "$LDAPI_URI" -f "$LDIF_SCHEMA" || true
  fi

  # Ensure employeeType attribute exists (required by alirpunkto schema)
  echo "Checking for employeeType attribute..."
  ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
    -b cn=schema,cn=config \
    '(olcAttributeTypes=*employeeType*)'

  # Ensure inetOrgPerson exists
  echo "Checking for inetOrgPerson schema..."
  if ! ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
      -b "cn=schema,cn=config" -s sub \
      "(cn=*inetorgperson*)" 2>/dev/null | grep -qi inetorgperson; then
    if [ -f /schema/inetorgperson.ldif ]; then
      ldapadd -Y EXTERNAL -H "$LDAPI_URI" -f /schema/inetorgperson.ldif || true
    fi
  fi

  # Ensure alirpunkto schema exists
  echo "Checking for alirpunkto schema..."
  if ! ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
      -b "cn=schema,cn=config" -s sub \
      "(cn=*alirpunktoPerson*)" 2>/dev/null | grep -qi alirpunktoPerson; then
    echo "ERROR: alirpunktoPerson schema missing"
    kill "$slapd_pid"
    exit 1
  fi
  ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
  -b cn=schema,cn=config \
  '(olcAttributeTypes=*isActive*)' 

  # Load initial users if not already done
  if [ "$DEBUG_LDAP" = "true" ]; then
    echo "[DEBUG MODE] Skipping initials_users.ldif loading"
  else
    if [ -f "$LDIF_PATH" ] && [ ! -f "$MARKER_PATH" ]; then
      echo "Importing initial users from $LDIF_PATH"
      if ldapadd -x \
        -D "cn=admin,$LDAP_BASE_DN" \
        -w "$LDAP_PASSWORD" \
        -H "$LDAP_URI" \
        -f "$LDIF_PATH"; then
        touch "$MARKER_PATH"
        echo "Initial users imported successfully"
      else
        echo "Failed to load initial users" >&2
        kill "$slapd_pid"
        exit 1
      fi
    fi
  fi
  wait "$slapd_pid"
else
  exec "${args[@]}"
fi
