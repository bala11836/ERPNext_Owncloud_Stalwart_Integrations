#!/bin/sh
# Daily read-only ZFS snapshot of the backup storage, keeping the newest N.
# Runs as root on the storage host (TrueNAS cron job). The backed-up server
# has no login here, so it cannot delete or encrypt these snapshots.
# Usage: zfs-snapshot-guard.sh DATASET [KEEP]   (default KEEP=60, one per day)
set -eu
DATASET="$1"; KEEP="${2:-60}"
case "$KEEP" in ''|*[!0-9]*) echo "KEEP must be a number" >&2; exit 2;; esac
[ "$KEEP" -ge 7 ] || { echo "Refusing to keep fewer than 7 snapshots" >&2; exit 2; }
zfs list -H -o name "$DATASET" >/dev/null
zfs snapshot "$DATASET@backup-guard-$(date +%Y-%m-%d_%H%M)"
# Only snapshots this script made are ever removed; oldest first.
zfs list -H -t snapshot -o name -s creation "$DATASET" \
  | grep "^$DATASET@backup-guard-" \
  | awk -v keep="$KEEP" '{ names[NR] = $0 } END { for (i = 1; i <= NR - keep; i++) print names[i] }' \
  | while read -r snap; do zfs destroy "$snap"; done
