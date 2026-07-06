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
# Environment overrides:
#   BACKUP_DIR   destination directory              (default /var/backups/alirpunkto)
#   KEEP_DAYS    prune tarballs older than N days    (default 14)
#   LDAP_CONTAINER / PYRAMID_CONTAINER               (default alirpunkto-ldap / alirpunkto-pyramid)
#   ZODB_PATH    Data.fs path inside the pyramid container
#                (default /home/alirpunkto/app/var/Data.fs)
#
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/alirpunkto}"
KEEP_DAYS="${KEEP_DAYS:-14}"
LDAP_CONTAINER="${LDAP_CONTAINER:-alirpunkto-ldap}"
PYRAMID_CONTAINER="${PYRAMID_CONTAINER:-alirpunkto-pyramid}"
ZODB_PATH="${ZODB_PATH:-/home/alirpunkto/app/var/Data.fs}"

ts="$(date +%Y%m%d-%H%M%S)"
work="${BACKUP_DIR}/${ts}"
mkdir -p "${work}"

echo "[backup] ${ts} -> ${work}"

# --- LDAP (config + data) as LDIF ------------------------------------------
if docker ps --format '{{.Names}}' | grep -qx "${LDAP_CONTAINER}"; then
    echo "[backup] slapcat config (-n 0) and data (-n 1) from ${LDAP_CONTAINER}"
    docker exec "${LDAP_CONTAINER}" slapcat -n 0 > "${work}/ldap-config.ldif"
    docker exec "${LDAP_CONTAINER}" slapcat -n 1 > "${work}/ldap-data.ldif"
else
    echo "[backup][WARN] ${LDAP_CONTAINER} not running; skipping LDAP dump" >&2
fi

# --- ZODB Data.fs (hot copy) ------------------------------------------------
if docker ps --format '{{.Names}}' | grep -qx "${PYRAMID_CONTAINER}"; then
    echo "[backup] copying ${ZODB_PATH} from ${PYRAMID_CONTAINER}"
    docker cp "${PYRAMID_CONTAINER}:${ZODB_PATH}" "${work}/Data.fs"
    # The .index speeds up reopening but is optional and safe to skip if absent.
    docker cp "${PYRAMID_CONTAINER}:${ZODB_PATH}.index" "${work}/Data.fs.index" 2>/dev/null || true
else
    echo "[backup][WARN] ${PYRAMID_CONTAINER} not running; skipping ZODB copy" >&2
fi

# --- pack + prune -----------------------------------------------------------
tar -czf "${work}.tar.gz" -C "${BACKUP_DIR}" "${ts}"
rm -rf "${work}"
echo "[backup] wrote ${work}.tar.gz"

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
#
# Point-in-time ZODB backups with repozo (incremental, consistent):
#   docker exec ${PYRAMID_CONTAINER} repozo --backup --full \
#       --file $(dirname "${ZODB_PATH}")/Data.fs --repository /some/repo
# ---------------------------------------------------------------------------
