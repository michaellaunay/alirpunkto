#!/bin/bash
set -e

# Function to wait for LDAP to be up
wait_for_ldap() {
    echo "Waiting for LDAP to start..."
    for i in {1..30}; do
        if ldapsearch -x -H ldap://localhost -b "" -s base "+" >/dev/null 2>&1; then
            echo "LDAP is up and running."
            return 0
        fi
        echo "Waiting for LDAP to start... attempt $i/30"
        sleep 1
    done
    echo "LDAP failed to start in time."
    return 1
}

# Check if LDAP data already exists
if [ ! -f /var/lib/ldap/initialized ]; then
    echo "First run detected, configuring LDAP server..."
    
    # Check if config is mounted or needs to be created
    if [ ! -f /etc/ldap/slapd.d/cn\=config.ldif ]; then
        echo "No existing configuration found, initializing default LDAP server..."
        
        # Set LDAP admin password
        LDAP_ADMIN_PASSWORD=${LDAP_ADMIN_PASSWORD:-admin}
        
        # Generate LDAP admin password hash
        LDAP_ADMIN_PASSWORD_HASH=$(slappasswd -s "$LDAP_ADMIN_PASSWORD")
        
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
        
        # Remove temporary file
        rm /tmp/debconf-slapd.conf
    else
        echo "Using existing LDAP configuration from mounted volume."
    fi
    
    # Start LDAP temporarily to add schema
    slapd -h "ldap:/// ldapi:///" -g openldap -u openldap -d 0 &
    SLAPD_PID=$!
    
    # Wait for LDAP to start
    wait_for_ldap
    
    # Check if we need to add the alirpunkto schema
    if [ -f /etc/ldap/schema/alirpunkto_schema.ldif ]; then
        echo "Found alirpunkto schema, attempting to add it..."
        ldap-schema-manager -i /etc/ldap/schema/alirpunkto_schema.ldif || echo "Could not import schema, might already be present or there was an error."
        ldap-schema-manager -m /etc/ldap/schema/alirpunkto_schema.ldif -n || echo "Could not manage schema, it might already be present or there was an error."
    else
        echo "No alirpunkto schema found at /etc/ldap/schema/alirpunkto_schema.ldif"
    fi
    
    # Run any custom initialization scripts
    if [ -d /docker-entrypoint-initdb.d ]; then
        echo "Running custom initialization scripts..."
        for f in /docker-entrypoint-initdb.d/*; do
            case "$f" in
                *.sh)     echo "Running $f"; . "$f" ;;
                *.ldif)   echo "Importing LDIF file $f"; ldapadd -Y EXTERNAL -H ldapi:/// -f "$f" || echo "Failed to import $f, continuing..." ;;
                *)        echo "Ignoring $f" ;;
            esac
        done
    fi
    
    # Stop temporary LDAP server
    if [ -n "$SLAPD_PID" ]; then
        kill $SLAPD_PID
        wait $SLAPD_PID || true
    fi
    
    # Mark as initialized
    touch /var/lib/ldap/initialized
    
    echo "LDAP server initialization completed."
else
    echo "LDAP server already initialized, using existing data."
fi

# Create config file if it doesn't exist
if [ ! -f /etc/ldap/ldap.conf ]; then
    echo "Creating default ldap.conf..."
    cat > /etc/ldap/ldap.conf << EOF
#
# LDAP Defaults
#
# See ldap.conf(5) for details
# This file should be world readable but not world writable.
BASE    dc=alirpunkto,dc=com
URI ldap://127.0.0.1
#SIZELIMIT    12
#TIMELIMIT    15
#DEREF        never
# TLS certificates (needed for GnuTLS)
TLS_CACERT    /etc/ssl/certs/ca-certificates.crt
EOF
fi

# Execute the command provided as arguments to this script
echo "Starting OpenLDAP server..."
exec "$@"