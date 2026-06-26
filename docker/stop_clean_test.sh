#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root.
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml down -v --remove-orphans

echo "Local test containers and named volumes removed."
echo "Generated files are kept: docker/.env.test, docker/initials_users.test.generated.ldif, docker/certs/local-test/, test.ini"
