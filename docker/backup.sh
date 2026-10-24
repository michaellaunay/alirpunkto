#!/usr/bin/env bash
#
# R4 — scheduled backups for AlirPunkto's two stateful stores.
#
#   * LDAP directory  -> slapcat (LDIF) of the config (-n 0) and data (-n 1)
#                        databases, taken from the running slapd (mdb allows
#                        concurrent reads, so this is consistent).
#   * ZODB Data.fs    -> hot copy of the FileStorage. ZODB's Data.fs is
#                        append-only, so copying a live file never corrupts it;
#                        at worst the last in-flight transaction is missing.
#                        For strict point-in-time snapshots use `repozo` instead
#                        (see the note at the bottom).
#
# Everything is written to a timestamped tarball and old tarballs are pruned.
# Run it from the HOST (it drives the containers via `docker`), e.g. from cron:
#
#     0 3 * * *  /path/to/repo/docker/backup.sh >> /var/log/alirpunkto-backup.log 2>&1
#
# ...or from a systemd timer. Copy the resulting tarballs OFF the host and test a
# restore periodically — a backup you have never restored is not a backup.
#
# Transversal audit of 2026-10-24 (A13): the script used to default to a
# Data.fs path the shipped configuration does not use, to go on when a
# container was missing (an empty archive announced as a success), and to
# prune the previous archives before anything had validated the new one.
# Now: the default path is the one production.ini uses; a missing store is
# a FAILURE unless ALLOW_PARTIAL=1 says otherwise; every file is listed in a
# manifest with its size and SHA-256; the tarball is verified before the
# pruning runs; and everything is written with umask 077.
#
# Environment overrides:
#   BACKUP_DIR     destination directory              (default /var/backups/alirpunkto)
#   KEEP_DAYS      prune tarballs older than N days    (default 14)
#   LDAP_CONTAINER / PYRAMID_CONTAINER                 (default alirpunkto-ldap / alirpunkto-pyramid)
#   ZODB_PATH      Data.fs path inside the pyramid container
#                  (default /home/alirpunkto/app/var/filestorage/Data.fs,
#                   production.ini: zodbconn.uri = file://%(here)s/var/filestorage/Data.fs)
#   ALLOW_PARTIAL  1 to accept a backup with one store missing (default 0)
#
set -euo pipefail
umask 077

BACKUP_DIR="${BACKUP_DIR:-/var/backups/alirpunkto}"
KEEP_DAYS="${KEEP_DAYS:-14}"
LDAP_CONTAINER="${LDAP_CONTAINER:-alirpunkto-ldap}"
PYRAMID_CONTAINER="${PYRAMID_CONTAINER:-alirpunkto-pyramid}"
ZODB_PATH="${ZODB_PATH:-/home/alirpunkto/app/var/filestorage/Data.fs}"
ALLOW_PARTIAL="${ALLOW_PARTIAL:-0}"

ts="$(date +%Y%m%d-%H%M%S)"
work="${BACKUP_DIR}/${ts}"
mkdir -p "${work}"
chmod 700 "${BACKUP_DIR}" "${work}"

missing=0
fail() { echo "[backup][ERROR] $*" >&2; exit 1; }
container_running() { docker ps --format '{{.Names}}' | grep -qx "$1"; }

echo "[backup] ${ts} -> ${work}"

# --- LDAP (config + data) as LDIF ------------------------------------------
if container_running "${LDAP_CONTAINER}"; then
    echo "[backup] slapcat config (-n 0) and data (-n 1) from ${LDAP_CONTAINER}"
    docker exec "${LDAP_CONTAINER}" slapcat -n 0 > "${work}/ldap-config.ldif"
    docker exec "${LDAP_CONTAINER}" slapcat -n 1 > "${work}/ldap-data.ldif"
    [ -s "${work}/ldap-data.ldif" ] || fail "slapcat produced an empty data LDIF"
else
    echo "[backup][WARN] ${LDAP_CONTAINER} not running; LDAP dump missing" >&2
    missing=1
fi

# --- ZODB Data.fs (hot copy) ------------------------------------------------
if container_running "${PYRAMID_CONTAINER}"; then
    echo "[backup] copying ${ZODB_PATH} from ${PYRAMID_CONTAINER}"
    docker cp "${PYRAMID_CONTAINER}:${ZODB_PATH}" "${work}/Data.fs"
    [ -s "${work}/Data.fs" ] || fail "the copied Data.fs is empty"
    # The .index speeds up reopening but is optional and safe to skip if absent.
    docker cp "${PYRAMID_CONTAINER}:${ZODB_PATH}.index" "${work}/Data.fs.index" 2>/dev/null || true
else
    echo "[backup][WARN] ${PYRAMID_CONTAINER} not running; ZODB copy missing" >&2
    missing=1
fi

if [ "${missing}" = "1" ] && [ "${ALLOW_PARTIAL}" != "1" ]; then
    rm -rf "${work}"
    fail "a store is missing; set ALLOW_PARTIAL=1 to accept a partial backup"
fi

# --- manifest ---------------------------------------------------------------
{
    echo "timestamp: ${ts}"
    echo "host: $(hostname)"
    echo "partial: ${missing}"
    echo "zodb_path: ${ZODB_PATH}"
    if command -v git >/dev/null 2>&1; then
        echo "app_revision: $(git -C "$(dirname "$0")" rev-parse HEAD 2>/dev/null || echo unknown)"
    fi
    echo "files:"
    ( cd "${work}" && for f in *; do
        [ "$f" = "MANIFEST" ] && continue
        printf '  %s size=%s sha256=%s\n' "$f" "$(stat -c %s "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
      done )
} > "${work}/MANIFEST"

# --- pack, verify, then prune ----------------------------------------------
tar -czf "${work}.tar.gz" -C "${BACKUP_DIR}" "${ts}"
chmod 600 "${work}.tar.gz"
# The archive must list every file of the working directory before the
# previous archives are touched: a truncated or empty tarball is a failure.
expected="$(cd "${work}" && ls -1 | wc -l)"
listed="$(tar -tzf "${work}.tar.gz" | grep -c -v '/$')"
[ "${listed}" -ge "${expected}" ] || fail "archive lists ${listed} files, ${expected} expected"
rm -rf "${work}"
echo "[backup] wrote ${work}.tar.gz (${listed} files, partial=${missing})"

echo "[backup] pruning tarballs older than ${KEEP_DAYS} days"
find "${BACKUP_DIR}" -maxdepth 1 -type f -name '*.tar.gz' -mtime "+${KEEP_DAYS}" -print -delete || true

echo "[backup] done"

# ---------------------------------------------------------------------------
# Restore (manual, review before running):
#   LDAP:  stop slapd, then in the LDAP container
#            slapadd -F /etc/ldap/slapd.d -n 0 -l ldap-config.ldif   # if rebuilding config
#            slapadd -F /etc/ldap/slapd.d -n 1 -l ldap-data.ldif
#          chown -R openldap:openldap /var/lib/ldap && start slapd.
#   ZODB:  stop the pyramid container, replace Data.fs in the
#          alirpunkto_pyramid_var volume with the backed-up Data.fs
#          (remove stale Data.fs.index/.lock/.tmp), then start it.
#   Check the MANIFEST sha256 of every file before restoring it.
#
# Point-in-time ZODB backups with repozo (incremental, consistent):
#   docker exec ${PYRAMID_CONTAINER} repozo --backup --full \
#       --file $(dirname "${ZODB_PATH}")/Data.fs --repository /some/repo
# ---------------------------------------------------------------------------
