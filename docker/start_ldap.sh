#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# LDAP entrypoint
#
# Logging levels:
#   DEBUG_LDAP=true
#       Enables safe verbose logs. Does NOT print LDAP_PASSWORD.
#
#   DEBUG_PASSWORD_LDAP=true
#       Enables shell xtrace and may print LDAP_PASSWORD in Docker logs.
#       Use only for temporary debugging, then rotate/delete existing logs.
# -----------------------------------------------------------------------------

DEBUG_LDAP="${DEBUG_LDAP:-false}"
DEBUG_PASSWORD_LDAP="${DEBUG_PASSWORD_LDAP:-false}"
SKIP_INITIAL_LDAP="${SKIP_INITIAL_LDAP:-false}"
LDIF_PATH="${INITIAL_USERS_LDIF:-/initials_users.ldif}"
LDIF_SCHEMA="${LDAP_SCHEMA_LDIF:-/schema/alirpunkto_schema.ldif}"
MARKER_PATH="${LDAP_INIT_MARKER:-/var/lib/ldap/.initials_users_loaded}"
LDAP_URI="${LDAP_URI:-ldap://localhost}"
LDAPI_URI="${LDAPI_URI:-ldapi:///}"
CONFIG_MARKER_PATH="${LDAP_CONFIG_MARKER:-/var/lib/ldap/.slapd_configured}"
LDAP_PASSWORD_FILE="${LDAP_PASSWORD_FILE:-/run/secrets/ldap_password}"

log() {
  echo "[LDAP] $*"
}

debug() {
  if [[ "$DEBUG_LDAP" = "true" || "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
    echo "[LDAP][DEBUG] $*"
  fi
}

error() {
  echo "[LDAP][ERROR] $*" >&2
}

if [[ "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
  echo "[LDAP][WARNING] DEBUG_PASSWORD_LDAP=true: shell tracing is enabled and secrets may appear in logs." >&2
  set -x
fi

# Ensure LDAP directories exist with correct ownership.
mkdir -p /etc/ldap /var/lib/ldap
chown -R openldap:openldap /etc/ldap /var/lib/ldap

# Read password from secret if not provided.
if [ -z "${LDAP_PASSWORD:-}" ]; then
  if [ -f "$LDAP_PASSWORD_FILE" ]; then
    log "Retrieving LDAP password from $LDAP_PASSWORD_FILE"
    LDAP_PASSWORD="$(cat "$LDAP_PASSWORD_FILE")"
  else
    error "You must provide LDAP_PASSWORD or create $LDAP_PASSWORD_FILE"
    exit 1
  fi
fi

# Store the password in a runtime-only file for LDAP tools.
# This avoids passing the password with -w "$LDAP_PASSWORD", which may be visible
# in process arguments and in xtrace output.
LDAP_PASSWORD_RUNTIME_FILE="$(mktemp)"
chmod 600 "$LDAP_PASSWORD_RUNTIME_FILE"
printf '%s' "$LDAP_PASSWORD" > "$LDAP_PASSWORD_RUNTIME_FILE"

cleanup() {
  rm -f "$LDAP_PASSWORD_RUNTIME_FILE"
}
trap cleanup EXIT

# Build domain from base DN.
if [ -n "${LDAP_BASE_DN:-}" ]; then
  LDAP_DOMAIN="$(echo "$LDAP_BASE_DN" | tr -d ' ' | sed -e 's/dc=//g' -e 's/,/./g')"
else
  LDAP_DOMAIN=""
fi

debug "LDAP_URI=$LDAP_URI"
debug "LDAPI_URI=$LDAPI_URI"
debug "LDAP_BASE_DN=${LDAP_BASE_DN:-}"
debug "LDAP_DOMAIN=$LDAP_DOMAIN"
debug "LDIF_PATH=$LDIF_PATH"
debug "LDIF_SCHEMA=$LDIF_SCHEMA"
debug "CONFIG_MARKER_PATH=$CONFIG_MARKER_PATH"
debug "MARKER_PATH=$MARKER_PATH"
debug "SKIP_INITIAL_LDAP=$SKIP_INITIAL_LDAP"

# Configure slapd only once.
if [ ! -f "$CONFIG_MARKER_PATH" ] && [ -n "${LDAP_BASE_DN:-}" ] && [ -n "${LDAP_PASSWORD:-}" ]; then
  LDAP_ORGANIZATION="${LDAP_ORGANIZATION:-$LDAP_DOMAIN}"

  if [[ "$DEBUG_LDAP" = "true" || "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
    debug "Preparing slapd debconf configuration:"
    debug "  slapd/no_configuration=false"
    debug "  slapd/domain=$LDAP_DOMAIN"
    debug "  shared/organization=$LDAP_ORGANIZATION"
    debug "  slapd/backend=MDB"
    debug "  slapd/purge_database=true"
    debug "  slapd/move_old_database=true"
    debug "  slapd/allow_ldap_v2=false"
    debug "  slapd/dump_database=when needed"
    debug "  slapd/dump_database_destdir=/var/backups/slapd-VERSION"

    if [[ "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
      debug "  slapd/password1=$LDAP_PASSWORD"
      debug "  slapd/password2=$LDAP_PASSWORD"
    else
      debug "  slapd/password1=<hidden>"
      debug "  slapd/password2=<hidden>"
    fi
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

  log "Configuring slapd..."
  dpkg-reconfigure -f noninteractive slapd
  touch "$CONFIG_MARKER_PATH"
  log "slapd configured"
else
  debug "Skipping slapd configuration: already configured or missing LDAP_BASE_DN/LDAP_PASSWORD"
fi

args=("$@")
if [ "${#args[@]}" -eq 0 ]; then
  SLAPD_DEBUG_LEVEL=0 #Production mode: foreground without verbose stats logs.

  if [[ "$DEBUG_LDAP" = "true" || "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
    # Debug mode: keep slapd stats logs.
    SLAPD_DEBUG_LEVEL=256
  fi

  args=(slapd -h "ldap:/// ldapi:/// ldaps:///" -g openldap -u openldap -d "$SLAPD_DEBUG_LEVEL")
fi

# Only run initialization when starting slapd.
if [ "${args[0]}" = "slapd" ]; then
  log "Starting slapd..."
  "${args[@]}" &
  slapd_pid=$!

  stop_slapd() {
    if kill -0 "$slapd_pid" >/dev/null 2>&1; then
      kill "$slapd_pid" >/dev/null 2>&1 || true
      wait "$slapd_pid" >/dev/null 2>&1 || true
    fi
  }

  log "Waiting for slapd to be ready..."
  ready=false

  for _ in $(seq 1 30); do
    if ldapsearch -x -H "$LDAP_URI" -s base -b "" >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 1
  done

  if [ "$ready" != "true" ]; then
    error "slapd did not become ready after 30 seconds"
    stop_slapd
    exit 1
  fi

  log "slapd is ready"

  # Load custom schema if provided.
  if [ -f "$LDIF_SCHEMA" ]; then
    log "Loading custom schema from $LDIF_SCHEMA"
    ldapadd -Y EXTERNAL -H "$LDAPI_URI" -f "$LDIF_SCHEMA" || true
  else
    debug "Custom schema not found: $LDIF_SCHEMA"
  fi

  # Ensure employeeType attribute exists.
  log "Checking for employeeType attribute..."
  if ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
      -b cn=schema,cn=config \
      '(olcAttributeTypes=*employeeType*)' >/dev/null 2>&1; then
    debug "employeeType attribute found"
  else
    debug "employeeType attribute not found or ldapsearch failed"
  fi

  # Ensure inetOrgPerson exists.
  log "Checking for inetOrgPerson schema..."
  if ! ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
      -b "cn=schema,cn=config" -s sub \
      "(cn=*inetorgperson*)" 2>/dev/null | grep -qi inetorgperson; then

    if [ -f /schema/inetorgperson.ldif ]; then
      log "Loading inetOrgPerson schema..."
      ldapadd -Y EXTERNAL -H "$LDAPI_URI" -f /schema/inetorgperson.ldif || true
    else
      debug "inetOrgPerson schema file not found: /schema/inetorgperson.ldif"
    fi
  else
    debug "inetOrgPerson schema already present"
  fi

  # Ensure alirpunkto schema exists.
  log "Checking for alirpunkto schema..."
  if ! ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
      -b "cn=schema,cn=config" -s sub \
      "(cn=*alirpunktoPerson*)" 2>/dev/null | grep -qi alirpunktoPerson; then
    error "alirpunktoPerson schema missing"
    stop_slapd
    exit 1
  fi

  debug "Checking for isActive attribute..."
  ldapsearch -Y EXTERNAL -H "$LDAPI_URI" \
    -b cn=schema,cn=config \
    '(olcAttributeTypes=*isActive*)' >/dev/null 2>&1 || true

  # Load initial users if not already done.
  if [ "$SKIP_INITIAL_LDAP" = "true" ]; then
    log "SKIP_INITIAL_LDAP=true: skipping initial users LDIF loading"
  else
    if [ -f "$LDIF_PATH" ] && [ ! -f "$MARKER_PATH" ]; then
      log "Importing initial users from $LDIF_PATH"

      ldapadd_output="$(ldapadd -c -x \
        -D "cn=admin,$LDAP_BASE_DN" \
        -y "$LDAP_PASSWORD_RUNTIME_FILE" \
        -H "$LDAP_URI" \
        -f "$LDIF_PATH" 2>&1)" || true

      if [[ "$DEBUG_LDAP" = "true" || "$DEBUG_PASSWORD_LDAP" = "true" ]]; then
        debug "ldapadd output:"
        echo "$ldapadd_output"
      fi

      # Verify LDAP entries.
      if echo "$ldapadd_output" | grep -q "adding new entry\|Already exists"; then
        touch "$MARKER_PATH"
        log "Initial users loaded or already present"
      else
        error "Failed to load initial users"
        stop_slapd
        exit 1
      fi
    else
      debug "Skipping initial users import: LDIF missing or marker already present"
      debug "LDIF exists: $([ -f "$LDIF_PATH" ] && echo true || echo false)"
      debug "Marker exists: $([ -f "$MARKER_PATH" ] && echo true || echo false)"
    fi
  fi

  wait "$slapd_pid"
else
  exec "${args[@]}"
fi