#!/usr/bin/env bash
set -euo pipefail

# R7: tear down the whole production stack (all services), mirroring
# stop_clean_test.sh. The previous version only removed the LDAP service,
# leaving Postfix, Pyramid, Apache and their volumes behind.
#
# Run from the repository root.
#
# Usage:
#   docker/stop_clean_delete.sh              # stop & remove containers (keep data volumes)
#   docker/stop_clean_delete.sh --volumes    # also remove named volumes (DESTROYS data)

REMOVE_VOLUMES=""
case "${1:-}" in
  -v|--volumes)
    REMOVE_VOLUMES="-v"
    echo "WARNING: named volumes will be removed — LDAP directory and app data will be lost."
    ;;
  "" ) ;;
  * ) echo "Unknown option: $1 (use --volumes to also remove data volumes)"; exit 2 ;;
esac

docker compose --env-file docker/.env -f docker/docker-compose.yaml down --remove-orphans ${REMOVE_VOLUMES}

echo "Production stack stopped and removed."
if [ -z "${REMOVE_VOLUMES}" ]; then
  echo "Named volumes were kept. Re-run with --volumes to delete persistent data."
fi
