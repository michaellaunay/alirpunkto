#!/bin/bash
set -e

# Ensure LDAP directories exist with correct ownership.
mkdir -p /etc/ldap /var/lib/ldap
chown -R openldap:openldap /etc/ldap /var/lib/ldap

LDAP_ENV_FILE="${LDAP_ENV_FILE:-/alirpunkto.env}"
LDIF_PATH="${INITIAL_USERS_LDIF:-/initials_users.ldif}"
MARKER_PATH="${LDAP_INIT_MARKER:-/var/lib/ldap/.initials_users_loaded}"
CONFIG_MARKER_PATH="${LDAP_CONFIG_MARKER:-/var/lib/ldap/.slapd_configured}"
LDAP_URI="${LDAP_URI:-ldap://localhost}"

if [ -f "$LDAP_ENV_FILE" ]; then
  set -a
  . "$LDAP_ENV_FILE"
  set +a
fi

if [ -n "$LDAP_BASE_DN" ]; then
  LDAP_DOMAIN="$(echo "$LDAP_BASE_DN" | tr -d ' ' | sed -e 's/dc=//g' -e 's/,/./g')"
fi

if [ -n "$LDAP_LOGIN" ] && [ -n "$LDAP_BASE_DN" ]; then
  if echo "$LDAP_LOGIN" | grep -q ','; then
    LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-$LDAP_LOGIN}"
  else
    LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-$LDAP_LOGIN,$LDAP_BASE_DN}"
  fi
fi
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-$LDAP_PASSWORD}"

if [ ! -f "$CONFIG_MARKER_PATH" ] && [ -n "$LDAP_BASE_DN" ] && [ -n "$LDAP_ADMIN_PASSWORD" ]; then
  LDAP_ORGANIZATION="${LDAP_ORGANIZATION:-$LDAP_DOMAIN}"
  debconf-set-selections <<EOF
slapd slapd/no_configuration boolean false
slapd slapd/domain string $LDAP_DOMAIN
slapd shared/organization string $LDAP_ORGANIZATION
slapd slapd/password1 password $LDAP_ADMIN_PASSWORD
slapd slapd/password2 password $LDAP_ADMIN_PASSWORD
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

  # Wait for slapd to accept connections before running ldapadd.
  for _ in $(seq 1 30); do
    if ldapsearch -x -H "$LDAP_URI" -s base -b "" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if [ -f "$LDIF_PATH" ] && [ ! -f "$MARKER_PATH" ]; then
    if [ -n "$LDAP_ADMIN_DN" ] && [ -n "$LDAP_ADMIN_PASSWORD" ]; then
      ldapadd -x -H "$LDAP_URI" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" -f "$LDIF_PATH"
      touch "$MARKER_PATH"
    else
      echo "LDAP_ADMIN_DN or LDAP_ADMIN_PASSWORD not set; skipping initial LDIF load."
    fi
  fi

  wait "$slapd_pid"
else
  exec "${args[@]}"
fi
