#!/bin/bash
set -e

# Script to run LDAP tests against a Docker container
# This can be used in your CI/CD pipeline or for local testing

# Cleanup function to ensure container is removed even if script fails
cleanup() {
    echo "Cleaning up test environment..."
    docker-compose -f docker-compose.test.yml down
    echo "Cleanup complete."
}

# Register the cleanup function to be called on exit
trap cleanup EXIT

echo "Starting LDAP test container..."
docker-compose -f docker-compose.test.yml up -d

# Wait for the container to be healthy
echo "Waiting for LDAP server to be ready..."
attempt=1
max_attempts=30
until docker-compose -f docker-compose.test.yml ps | grep "healthy" > /dev/null; do
    if [ $attempt -gt $max_attempts ]; then
        echo "LDAP server failed to start and be healthy in time."
        exit 1
    fi
    echo "Waiting for LDAP server... attempt $attempt/$max_attempts"
    sleep 2
    attempt=$((attempt+1))
done

echo "LDAP test server is up and healthy!"

# Get the admin password from the container (useful if randomly generated)
LDAP_ADMIN_PASSWORD=$(docker-compose -f docker-compose.test.yml exec ldap-test cat /test-data/ldap-credentials.env | grep LDAP_ADMIN_PASSWORD | cut -d= -f2)
echo "LDAP admin password: $LDAP_ADMIN_PASSWORD"

# Run a test query to verify the server is working
echo "Testing LDAP server with a query..."
docker-compose -f docker-compose.test.yml exec ldap-test ldapsearch -x -H ldap://localhost -b "dc=alirpunkto,dc=com" -D "cn=admin,dc=alirpunkto,dc=com" -w "$LDAP_ADMIN_PASSWORD"

echo "Setting environment variables for tests..."
export LDAP_HOST=localhost
export LDAP_PORT=3389
export LDAP_ADMIN_DN="cn=admin,dc=alirpunkto,dc=com"
export LDAP_ADMIN_PASSWORD="$LDAP_ADMIN_PASSWORD"
export LDAP_BASE_DN="dc=alirpunkto,dc=com"

# Run your actual tests here
echo "Running your tests..."
# python -m unittest discover tests
# or
# pytest tests/
# or any other test command you use

echo "Tests completed."

# Container will be automatically stopped and removed by the cleanup function