#!/usr/bin/env bash
# ==============================================================================
# Yabsnap Cross-Drive Incremental Btrfs Sync Script
# Compares 1st drive snapshots against 2nd drive backup snapshots and 
# syncs any missing ones using btrfs send/receive.
# ==============================================================================

set -euo pipefail

# --- CONFIGURATION ---
# Adjust these paths to match your actual mount points and snapshot folders
SRC_DIR="/.snapshots"             # Where your 1st drive stores yabsnap snapshots
DST_DIR="/mnt/backup/"  # Where your 2nd drive stores backup snapshots
LOCKFILE="/var/lock/yabsnap-sync.lock"

# Ensure script is run as root (mandatory for btrfs send/receive)
if [[ $EUID -ne 0 ]]; then
   echo "[-] Error: This script must be run as root." >&2
   exit 1
fi

# Prevent overlapping concurrent executions using flock
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[-] Error: Another instance of yabsnap-sync is already running. Exiting." >&2
    exit 1
fi


# --- SAFETY CHECK 1: STRICT MOUNT VALIDATION ---
# Ensure both paths are actively mounted Btrfs filesystems, not fallback folders.
if ! findmnt -M "$SRC_DIR" -t btrfs &>/dev/null; then
    echo "[-] Error: $SRC_DIR is not a valid, actively mounted Btrfs filesystem." >&2
    exit 1
fi

if ! findmnt -M "$DST_DIR" -t btrfs &>/dev/null; then
    echo "[-] Error: $DST_DIR is not a valid, actively mounted Btrfs filesystem (2nd drive unmounted?)." >&2
    exit 1
fi


echo "[+] Scanning snapshots on 1st drive ($SRC_DIR)..."
mapfile -t src_snapshots < <(find "$SRC_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

echo "[+] Scanning snapshots on 2nd drive ($DST_DIR)..."
mapfile -t dst_snapshots < <(find "$DST_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

# Build a lookup map of existing snapshots on the 1st drive
declare -A src_map
for s in "${src_snapshots[@]}"; do
    src_map["$(basename "$s")"]=1
done

# Build a lookup map of existing snapshots on the 2nd drive
declare -A dst_map
for d in "${dst_snapshots[@]}"; do
    dst_map["$(basename "$d")"]=1
done

echo "[+] Analyzing gaps and synchronizing..."

# Track the last verified or transferred snapshot to use as an incremental parent
last_parent=""

for src_path in "${src_snapshots[@]}"; do
    snap_name="$(basename "$src_path")"
    dst_path="$DST_DIR/$snap_name"

    # Sanity check: Verify it's a valid Btrfs subvolume root
    if ! btrfs subvolume show "$src_path" &>/dev/null; then
        echo "[*] Skipping '$snap_name': Not a valid Btrfs subvolume."
        continue
    fi

    # Case 1: Snapshot already exists on the 2nd drive
    if [[ -n "${dst_map[$snap_name]:-}" ]]; then
        echo "[*] Snapshot '$snap_name' already exists on 2nd drive. Skipping."
        last_parent="$dst_path" # This can serve as a parent for subsequent missing snapshots
        continue
    fi

    # Case 2: Snapshot is missing on the 2nd drive
    echo "[+] Found missing snapshot: '$snap_name'. Syncing..."

    # turn "read only" on to follow btrfs send guidelines
    btrfs property set "$src_path" ro true

    # Determine if we can leverage an incremental parent (-p)
    if [[ -n "$last_parent" && -d "$last_parent" ]]; then
        echo "    -> Using incremental send with parent: $(basename "$last_parent")"
        if btrfs send -p "$last_parent" "$src_path" | btrfs receive "$DST_DIR"; then
            echo "    -> Successfully synced (incremental): '$snap_name'."
        else
            echo "    [-] Incremental send failed. Falling back to a full send..."
            if btrfs send "$src_path" | btrfs receive "$DST_DIR"; then
                echo "    -> Successfully synced (full fallback): '$snap_name'."
            else
                echo "    [-] Error: Failed to transfer snapshot '$snap_name'." >&2
                exit 1
            fi
        fi
    else
        echo "    -> No valid parent available. Performing a full send..."
        if btrfs send "$src_path" | btrfs receive "$DST_DIR"; then
            echo "    -> Successfully synced (full): '$snap_name'."
        else
            echo "    [-] Error: Failed to transfer snapshot '$snap_name'." >&2
            exit 1
        fi
    fi

    # turn "read only" off to revert btrfs send requirement.
    btrfs property set "$src_path" ro false

    # Update the parent pointer to this newly synced snapshot
    last_parent="$dst_path"
done

# --- PHASE 2: PRUNE ORPHANED SNAPSHOTS ON DST ---
echo "[+] Checking for orphaned snapshots on 2nd drive..."

# Safety Guard A: If source array is empty, abort to protect against unmount glitches
if [[ ${#src_snapshots[@]} -eq 0 ]]; then
    echo "[-] Warning: Source snapshot list is empty. Skipping cleanup phase to prevent accidental data loss." >&2
else
    # Collect all candidates for deletion first
    orphaned_snapshots=()
    for dst_path in "${dst_snapshots[@]}"; do
        snap_name="$(basename "$dst_path")"
        
        # Use the native -v operator to safely check if the snapshot key is missing on the 1st drive
        if [[ ! -v src_map["$snap_name"] ]]; then
            orphaned_snapshots+=("$dst_path")
        fi
    done

    # Execute deletion for valid orphans
    for dst_path in "${orphaned_snapshots[@]}"; do
        snap_name="$(basename "$dst_path")"
        echo "[+] Found orphaned snapshot on 2nd drive: '$snap_name'."

        if [[ "$DRY_RUN" == "true" ]]; then
            echo "    -> [DRY-RUN] Would delete orphaned snapshot: '$snap_name'."
            continue
        fi

        if btrfs subvolume delete "$dst_path"; then
            echo "    -> Successfully deleted orphaned snapshot: '$snap_name'."
        else
            echo "    [-] Error: Failed to delete orphaned snapshot '$snap_name'." >&2
        fi
    done
fi

echo "[+] Snapshot synchronization and cleanup finished successfully!"
