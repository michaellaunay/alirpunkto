#!/bin/bash
set -e

# This script initializes a clean LDAP server for testing purposes

# Generate a random admin password if not provided
LDAP_ADMIN_PASSWORD=${LDAP_ADMIN_PASSWORD:-$(tr -dc A-Za-z0-9 </dev/urandom | head -c 12)}

# Save the password to a known location for tests to use
echo "LDAP_ADMIN_PASSWORD=$LDAP_ADMIN_PASSWORD" > /test-data/ldap-credentials.env

echo "Initializing test LDAP server with admin password: $LDAP_ADMIN_PASSWORD"

# Create temporary debconf configuration
cat > /tmp/debconf-slapd.conf << EOF
slapd slapd/internal/adminpw password ${LDAP_ADMIN_PASSWORD}
slapd slapd/internal/generated_adminpw password ${LDAP_ADMIN_PASSWORD}
slapd slapd/password1 password ${LDAP_ADMIN_PASSWORD}
slapd slapd/password2 password ${LDAP_ADMIN_PASSWORD}
slapd slapd/domain string alirpunkto.com
slapd shared/organization string AlirPunkto
slapd slapd/backend select MDB
slapd slapd/purge_database boolean true
slapd slapd/move_old_database boolean true
slapd slapd/allow_ldap_v2 boolean false
slapd slapd/no_configuration boolean false
EOF

# Configure slapd using debconf
debconf-set-selections /tmp/debconf-slapd.conf
dpkg-reconfigure -f noninteractive slapd

# Function to wait for LDAP to be up
wait_for_ldap() {
    echo "Waiting for LDAP to start..."
    for i in {1..30}; do
        if ldapsearch -x -H ldap://localhost -b "" -s base "+" >/dev/null 2>&1; then
            echo "LDAP server is up and running."
            return 0
        fi
        echo "Waiting for LDAP to start... attempt $i/30"
        sleep 1
    done
    echo "LDAP server failed to start in time."
    return 1
}

# Start LDAP temporarily to add schema and test data
slapd -h "ldap:/// ldapi:///" -g openldap -u openldap -d 0 &
SLAPD_PID=$!

# Wait for LDAP to start
wait_for_ldap

# Import the Alirpunkto schema
if [ -f /etc/ldap/schema/alirpunkto_schema.ldif ]; then
    echo "Importing Alirpunkto schema..."
    ldap-schema-manager -i /etc/ldap/schema/alirpunkto_schema.ldif || echo "Could not import schema (might already be present or there was an error)."
    ldap-schema-manager -m /etc/ldap/schema/alirpunkto_schema.ldif -n || echo "Could not manage schema (might already be present or there was an error)."
else
    echo "Warning: Alirpunkto schema not found!"
fi

# Import test data if available
if [ -d /test-data ]; then
    echo "Importing test data..."
    for f in /test-data/*.ldif; do
        if [ -f "$f" ]; then
            echo "Importing $f..."
            # Try with admin credentials first, fallback to external auth if it fails
            ldapadd -x -D "cn=admin,dc=alirpunkto,dc=com" -w "$LDAP_ADMIN_PASSWORD" -H ldap://localhost -f "$f" || \
            ldapadd -Y EXTERNAL -H ldapi:/// -f "$f" || \
            echo "Failed to import $f, continuing..."
        fi
    done
else
    echo "No test data directory found."
fi

# Kill the temporary server
if [ -n "$SLAPD_PID" ]; then
    kill $SLAPD_PID
    wait $SLAPD_PID || true
fi

# Create a basic ldap.conf file
cat > /etc/ldap/ldap.conf << EOF
BASE    dc=alirpunkto,dc=com
URI     ldap://localhost
TLS_CACERT    /etc/ssl/certs/ca-certificates.crt
EOF

# If we're running in test mode, output the admin password
if [ "$TEST_MODE" = "1" ]; then
    echo "============================================"
    echo "LDAP server configured for testing"
    echo "Admin DN: cn=admin,dc=alirpunkto,dc=com"
    echo "Admin Password: $LDAP_ADMIN_PASSWORD"
    echo "============================================"
fi

# Execute the command provided as arguments to this script
echo "Starting OpenLDAP server for testing..."
exec "$@"