#!/usr/bin/env bash
# =============================================================================
# tools/export_sources_for_review.sh
#
# Export selected AlirPunkto source files into a single numbered text file for
# external review, debugging or LLM-assisted analysis.
#
# The script includes:
#   - application sources under alirpunkto/
#   - tests under tests/
#   - Dockerfiles, Compose files, shell scripts and Docker README files
#
# The script deliberately excludes generated, local or sensitive files:
#   - .env and .env.* files
#   - docker/secrets/
#   - docker/certs/
#   - generated LDIF files
#   - local test.ini
#   - caches, eggs, locale and static assets
#
# Usage, from the repository root:
#   chmod +x scripts/export_sources_for_review.sh
#   ./scripts/export_sources_for_review.sh
#
# Optional output path:
#   ./scripts/export_sources_for_review.sh /tmp/alirpunkto_sources.txt
#
# Default output:
#   /tmp/YYYYMMDD_alirpunkto_sources.txt
#
# This script is intended to export source code only. It should not be used to
# package runtime secrets, certificates, generated local configuration or private
# deployment material.
# =============================================================================
set -euo pipefail

OUT="/tmp/$(date +%Y%m%d)_alirpunkto_sources.txt"

git ls-files \
  alirpunkto tests docker \
  ':!:*/__pycache__/*' \
  ':!:*/eggs/*' \
  ':!:*/locale/*' \
  ':!:*/static/*' \
  ':!:docker/certs/*' \
  ':!:*.pem' \
  ':!:*.key' \
  ':!:*.crt' \
  ':!:docker/secrets/*' \
  ':!:docker/.env*' \
  ':!:docker/*.generated.ldif' \
  ':!:test.ini' |
while IFS= read -r file; do
  [ -f "$file" ] || continue

  case "$file" in
    docker/Dockerfile*|docker/*.yaml|docker/*.yml|docker/*.sh|docker/README*.md|alirpunkto/*|tests/*)
      ;;
    *)
      continue
      ;;
  esac

  if [ "$(file -b --mime-encoding -- "$file")" = "binary" ]; then
    continue
  fi

  printf '=== %s ===\n' "$file"
  nl -ba -w1 -s': ' -- "$file"
  printf '\n\n'
done > "$OUT"

echo "Written: $OUT"
