#!/usr/bin/env bash
# btrfs-send-receive.sh - mirror all yabsnap snapshots to another btrfs filesystem.
#
# Addresses https://github.com/hirak99/yabsnap/issues/60 (efficient incremental
# backups via `btrfs send/receive`).
# Originally contributed by @IComplainInComments -
# https://gist.github.com/IComplainInComments/c517b7bdbb3e8be901669bffb0ca0619
# (see https://github.com/hirak99/yabsnap/issues/60#issuecomment-6114242865).
#
# CAUTION: example script, not yet tested against live btrfs send/receive.
# Review DESTS below and try DRY_RUN=true before relying on it.
#
# Usage in a yabsnap config (the script needs no arguments):
#   post_transaction_scripts = "/usr/local/bin/btrfs-send-receive.sh"
#
# Yabsnap invokes it as `btrfs-send-receive.sh CONFIG_FILE` once per config
# that had snapshots created or deleted. The source snapshot directory is
# derived from that config's `dest_prefix`; the destination comes from the
# DESTS table below. For manual runs:
#   sudo ./btrfs-send-receive.sh /etc/yabsnap/configs/root.conf
#   sudo ./btrfs-send-receive.sh /.snapshots /mnt/backup   # DST override as $2
#
# Contract (see example_config.conf): the hook must be idempotent - it rescans
# both sides, sends whatever is missing (incrementally where possible), and
# prunes destination snapshots that no longer exist at the source.
#
# Set DRY_RUN=true to print pruning actions without deleting.
#
# NOTE: only read-only (btrfs-mechanism) snapshots can be sent. Snapshots that
# are not read-only are skipped with a warning.

set -euo pipefail

# --- User configuration: map each source snapshot dir to its backup dir. ---
declare -A DESTS=(
  ["/.snapshots"]="/mnt/backup"
)

DRY_RUN="${DRY_RUN:-false}"

usage() {
  echo "Usage: $0 CONFIG_FILE [DST_DIR]" >&2
  exit 2
}

# Resolve SRC_DIR from $1 (a yabsnap config file, or a snapshot dir directly).
first_arg="${1-}"
[[ -z "$first_arg" ]] && usage
if [[ -d "$first_arg" ]]; then
  SRC_DIR="$first_arg"
elif [[ -f "$first_arg" ]]; then
  dest_prefix="$(grep -E '^\s*dest_prefix\s*=' "$first_arg" | tail -n 1 | cut -d= -f2- | xargs)" || true
  [[ -z "${dest_prefix:-}" ]] && { echo "[-] Could not read dest_prefix from $first_arg" >&2; exit 1; }
  SRC_DIR="$(dirname "$dest_prefix")"
else
  echo "[-] Not a config file or directory: $first_arg" >&2
  exit 1
fi

# Destination: explicit $2 wins, otherwise the DESTS table.
if [[ "${2-}" != "" ]]; then
  DST_DIR="$2"
elif [[ -n "${DESTS[$SRC_DIR]:-}" ]]; then
  DST_DIR="${DESTS[$SRC_DIR]}"
else
  echo "[-] No destination configured for $SRC_DIR (add it to DESTS or pass DST_DIR as \$2)." >&2
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "[-] This script must be run as root (btrfs send/receive)." >&2
  exit 1
fi

# Per-destination lockfile: syncs to different disks are independent, so only
# serialize runs targeting the same destination. This is additional safety -
# yabsnap already serializes snapshot creation across processes with its own
# per-second lock; this just keeps two slow sends to the same disk from
# overlapping.
safe_dst="${DST_DIR//[^A-Za-z0-9]/_}"
LOCKFILE="/var/lock/yabsnap-btrfs-sync${safe_dst}.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
  echo "[-] Another instance is already running. Exiting." >&2
  exit 1
fi

# Both sides must be mounted btrfs filesystems, never fallback directories.
for dir in "$SRC_DIR" "$DST_DIR"; do
  if ! findmnt -M "$dir" -t btrfs &>/dev/null; then
    echo "[-] $dir is not a mounted btrfs filesystem. Aborting." >&2
    exit 1
  fi
done

echo "[+] Source: $SRC_DIR -> Destination: $DST_DIR"

mapfile -t src_entries < <(find "$SRC_DIR" -mindepth 1 -maxdepth 1 | sort)
mapfile -t dst_entries < <(find "$DST_DIR" -mindepth 1 -maxdepth 1 | sort)

# Keep only real subvolumes on the source; build the name set for pruning.
src_snaps=()
declare -A src_map=()
for entry in ${src_entries[@]+"${src_entries[@]}"}; do
  name="$(basename "$entry")"
  btrfs subvolume show "$entry" &>/dev/null || { echo "[*] Skipping '$name': not a btrfs subvolume."; continue; }
  src_snaps+=("$entry")
  src_map["$name"]=1
done

declare -A dst_map=()
for entry in ${dst_entries[@]+"${dst_entries[@]}"}; do
  dst_map["$(basename "$entry")"]=1
done

# --- Phase 1: send missing snapshots. ---
# The incremental parent (-p) must be a *source-side* snapshot whose name also
# exists at the destination; track it as we walk the sorted source list.
parent_src=""
for src_path in ${src_snaps[@]+"${src_snaps[@]}"}; do
  snap_name="$(basename "$src_path")"

  if [[ -n "${dst_map[$snap_name]:-}" ]]; then
    echo "[*] '$snap_name' already present at destination. Skipping."
    parent_src="$src_path"
    continue
  fi

  # yabsnap's btrfs snapshots are read-only, which is what `send` requires.
  # We deliberately do not toggle this: flipping ro would mutate the source.
  if [[ "$(btrfs property get "$src_path" ro 2>/dev/null)" != *"ro=true"* ]]; then
    echo "[*] Skipping '$snap_name': not read-only, cannot btrfs send." >&2
    continue
  fi

  echo "[+] Sending missing snapshot '$snap_name'..."
  if [[ -n "$parent_src" && -n "${dst_map[$(basename "$parent_src")]:-}" ]]; then
    echo "    -> incremental from '$(basename "$parent_src")'"
    if ! btrfs send -p "$parent_src" "$src_path" | btrfs receive "$DST_DIR"; then
      echo "    -> incremental send failed, falling back to full send..."
      btrfs send "$src_path" | btrfs receive "$DST_DIR"
    fi
  else
    echo "    -> no parent available, full send."
    btrfs send "$src_path" | btrfs receive "$DST_DIR"
  fi
  echo "    -> synced '$snap_name'."
  dst_map["$snap_name"]=1
  parent_src="$src_path"
done

# --- Phase 2: prune destination snapshots deleted at the source. ---
if [[ ${#src_snaps[@]} -eq 0 ]]; then
  # Empty source likely means an unmounted/misread SRC_DIR; never prune then.
  echo "[-] Source snapshot list is empty, skipping prune to avoid data loss." >&2
  exit 0
fi

for entry in ${dst_entries[@]+"${dst_entries[@]}"}; do
  snap_name="$(basename "$entry")"
  if [[ -z "${src_map[$snap_name]:-}" ]]; then
    echo "[+] Orphaned at destination: '$snap_name'."
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "    -> [DRY-RUN] would delete '$snap_name'."
      continue
    fi
    if btrfs subvolume show "$entry" &>/dev/null; then
      btrfs subvolume delete "$entry" && echo "    -> deleted '$snap_name'."
    else
      echo "    -> not a btrfs subvolume, leaving alone: '$snap_name'." >&2
    fi
  fi
done

echo "[+] Sync finished."
