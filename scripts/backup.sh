#!/bin/bash
# Ninedex database backup
#   1) local copy (consistent, safe while the app is running), keeps the last KEEP_LOCAL
#   2) optional copy to a mounted network share (e.g. a NAS), keeps the last KEEP_NAS
#
# Settings via environment variables (or edit the defaults below):
#   DB_FILE     path to the SQLite database      (default: ./data/pokedex.db)
#   BACKUP_DIR  local backup folder              (default: ./backups)
#   NAS_MOUNT   mount point of the share         (default: empty = skip the NAS step)
#   NAS_SUBDIR  folder inside the share          (default: ninedex)
#
# Example cron job (daily at 03:15, as root if the share must be mounted):
#   15 3 * * * DB_FILE=/srv/ninedex/data/pokedex.db BACKUP_DIR=/srv/ninedex/backups NAS_MOUNT=/mnt/nas /srv/ninedex/scripts/backup.sh

DB_FILE="${DB_FILE:-./data/pokedex.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
NAS_MOUNT="${NAS_MOUNT:-}"
NAS_DIR="$NAS_MOUNT/${NAS_SUBDIR:-ninedex}"
KEEP_LOCAL="${KEEP_LOCAL:-14}"
KEEP_NAS="${KEEP_NAS:-60}"
LOG="$BACKUP_DIR/backup.log"
FILE="pokedex-$(date +%Y%m%d).db"

mkdir -p "$BACKUP_DIR"
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

if [ ! -f "$DB_FILE" ]; then
  log "ERROR: database not found: $DB_FILE"
  exit 1
fi

# 1) local backup (SQLite online backup API)
python3 - "$DB_FILE" "$BACKUP_DIR/$FILE" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
PY
if [ $? -ne 0 ]; then
  log "ERROR: local backup failed"
  exit 1
fi
log "OK local: $BACKUP_DIR/$FILE"
ls -1t "$BACKUP_DIR"/pokedex-*.db 2>/dev/null | tail -n +$((KEEP_LOCAL + 1)) | xargs -r rm --

# 2) optional: network share
[ -z "$NAS_MOUNT" ] && exit 0
if ! mountpoint -q "$NAS_MOUNT"; then
  mount "$NAS_MOUNT" 2>/dev/null   # works if the share has an /etc/fstab entry
fi
if mountpoint -q "$NAS_MOUNT"; then
  if mkdir -p "$NAS_DIR" && cp "$BACKUP_DIR/$FILE" "$NAS_DIR/$FILE" && cmp -s "$BACKUP_DIR/$FILE" "$NAS_DIR/$FILE"; then
    log "OK share: $NAS_DIR/$FILE"
  else
    log "ERROR: copy to the share failed"
    exit 2
  fi
  ls -1t "$NAS_DIR"/pokedex-*.db 2>/dev/null | tail -n +$((KEEP_NAS + 1)) | xargs -r rm --
else
  log "WARNING: share not mounted, only the local backup was created"
  exit 2
fi
