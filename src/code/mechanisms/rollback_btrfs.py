# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

import dataclasses
import datetime
import logging
import os
import shlex
from collections.abc import Iterator

from .. import global_flags
from ..mechanisms import abstract_mechanism
from ..utils import btrfs_utils
from ..utils import mtab_parser
from ..utils import os_utils

# This will be cleaned up if it exists by rollback script.
_PACMAN_LOCK_FILE = "/var/lib/pacman/db.lck"


def _get_now_str():
    return datetime.datetime.now().strftime(global_flags.TIME_FORMAT)


def _handle_nested_subvolume(
    nested_dirs: list[str], old_live_path: str, new_live_path: str
) -> Iterator[str]:
    """Generate commands for handling nested subvolumes.

    Args:
        nested_dirs: Nested subdirs relative to the mounted path.
        old_live_path: Where the live path before roll-back is backed up. This is where the nested subvolumes will also reside. This is also currently mounted when the rollback happens.
        new_live_path: The restored or rolled-back snapshot. This will become live after reboot. This is where the subdirs should be moved.

    Yields:
        Lines which must be shell executable or shell comments.
    """
    for nested_dir in nested_dirs:
        full_live_path = os.path.join(new_live_path, nested_dir)
        # `rmdir` will work if snapshot was taken with the subdir.
        # It can fail if the subdir was already moved (e.g. it had its own snapshot).
        # Or if a the directory was created by an applicaiton (and not a subvolume).
        yield f'echo "sudo rmdir {full_live_path}"  # Empty, otherwise validate subdir is already moved.'
        yield f'echo "sudo mv {old_live_path}/{nested_dir} {full_live_path}"'


def _drop_root_slash(s: str) -> str:
    """Helper to remove leading slash and check for other slashes."""
    if s[0] != "/":
        # Allow subvolume names without a leading slash, such as '@'.
        if "/" in s:
            raise RuntimeError(f"Unexpected / in subvolume {s!r}")
        return s

    if s[0] != "/":
        raise RuntimeError(f"Could not drop initial / from {s!r}")
    return s[1:]


def _is_within_path(child: str, parent: str) -> bool:
    """Whether child is parent itself or nested inside it (top-level-relative paths)."""
    return child == parent or child.startswith(parent + "/")


def _resolve_live_subvol_name(
    snap: abstract_mechanism.LightSnapshot,
    snap_subvolume: mtab_parser._MountAttributes,
    subvol_map: dict[str, str],
) -> tuple[str, bool]:
    """Resolve the live subvolume name for a snapshot.

    Returns (live_subvol_name, using_subvol_map).
    """
    snap_source = snap.metadata.source
    if snap_source in subvol_map:
        logging.info(f"Using mapped subvol for {snap_source!r}.")
        return subvol_map[snap_source], True
    if snap.metadata.btrfs and snap.metadata.btrfs.source_subvol:
        logging.info(f"Using recorded subvol for {snap_source!r}.")
        return snap.metadata.btrfs.source_subvol, False
    live_subvolume = mtab_parser.mount_attributes(snap_source)
    if snap_subvolume.device != live_subvolume.device:
        raise RuntimeError(
            f"{snap_source!r} and {snap.target!r} are not on the same device."
        )
    logging.info(
        f"Using currently mounted source as subvol for {snap_source!r}."
        " This is for older snapshots, and expected to work for online rollbacks."
    )
    return live_subvolume.subvol_name, False


def rollback_gen(
    snapshots: list[abstract_mechanism.LightSnapshot],
    subvol_map: dict[str, str] | None,
) -> list[str]:
    """Generates rollback script assuming running on a live (non-snapshot) system.

    Args:
        snapshots: List of snapshots to roll back.

        subvol_map: For any paths here, we will directly use it to find the
          subvolume name, and not depend on /etc/mtab.
          E.g. {"/": "@", "/home": "@home"}.

    Returns:
      Lines which can be executed on shell to perform roll back.
    """
    if not snapshots:
        return ["# No snapshot matched to rollback."]

    if not subvol_map:
        subvol_map = {}

    now_str = _get_now_str()

    # 0. Resolve all live/snapshot subvolumes first so incompatible layouts
    # fail fast before any script lines are generated (see issue #90).
    # IMPORTNT NOTE: Do not assume the snap_source is live.
    # In particular, it should not be used to gather mtab attributes.
    @dataclasses.dataclass
    class _SnapPlan:
        snap: abstract_mechanism.LightSnapshot
        snap_subvolume: mtab_parser._MountAttributes
        live_subvol_name: str
        using_subvol_map: bool
        script_live_path: str
        backup_path: str

    plans: list[_SnapPlan] = []
    for snap in snapshots:
        # 1. We retrieve device and snapshot subvolume information from the snapshot path.
        snap_subvolume = mtab_parser.mount_attributes(os.path.dirname(snap.target))
        # 2. We retrieve the name of the `live_subvolume`.
        live_subvol_name, using_subvol_map = _resolve_live_subvol_name(
            snap, snap_subvolume, subvol_map
        )
        # The path where it will be mounted when running the script.
        script_live_path = _drop_root_slash(live_subvol_name)
        # If the subvolume being rolled back is nested, normalize for the backup path.
        normalized_live_path = script_live_path.replace("/", "_")
        backup_path = f"{_drop_root_slash(snap_subvolume.subvol_name)}/rollback_{now_str}_{normalized_live_path}"
        if _is_within_path(backup_path, script_live_path):
            raise RuntimeError(
                f"Cannot roll back {snap.metadata.source!r} to {snap.target!r}: "
                f"the live subvolume {live_subvol_name!r} would be moved into itself "
                f"({script_live_path!r} -> {backup_path!r}). "
                "The snapshot storage (dirname of the snapshot, i.e. the "
                "`dest_prefix` directory in the config) must be outside the "
                "subvolume being rolled back; move `dest_prefix` to a separate "
                "subvolume (e.g. `dest_prefix = /.snapshots/@root-` with "
                "`/.snapshots` on its own subvolume)."
            )
        plans.append(
            _SnapPlan(
                snap=snap,
                snap_subvolume=snap_subvolume,
                live_subvol_name=live_subvol_name,
                using_subvol_map=using_subvol_map,
                script_live_path=script_live_path,
                backup_path=backup_path,
            )
        )

    sh_lines: list[str] = []

    # 1. Generate code to mount all the required volumes for rollback.
    temp_mount_points: dict[str, str] = {}
    for plan in plans:
        snap = plan.snap
        # Note that live_path and snap_path must be on the same volume.
        snap_subvolume_for_device = mtab_parser.mount_attributes(snap.target)
        device = snap_subvolume_for_device.device

        if device not in temp_mount_points:
            temp_mount_pt = f"/run/mount/_yabsnap_internal_{len(temp_mount_points)}"
            temp_mount_points[device] = temp_mount_pt
            sh_lines += [
                f"mkdir -p {temp_mount_pt}",
                f"mount {device} {temp_mount_pt} -o subvolid=5",
            ]
            # Check if the uuids match.
            uuid = os_utils.get_filesystem_uuid(snap.target)
            if snap.metadata.source_uuid is not None:
                if uuid == snap.metadata.source_uuid:
                    logging.info(f"Verified UUID of the device with {snap.target!r}.")
                else:
                    logging.warning(
                        f"UUID of the device with {snap.target!r} has changed.\n"
                        "  This can happen if you are using the snap on a mirror volume.\n"
                        "  Proceed with caution.\n"
                        f"  Old UUID: {snap.metadata.source_uuid}\n"
                        f"  New UUID: {uuid}"
                    )

    sh_lines.append("")
    backup_paths: list[str] = []
    current_dir: str | None = None
    nested_subvol_commands: list[str] = []
    for plan in plans:
        snap = plan.snap
        snap_source = snap.metadata.source
        snap_subvolume = plan.snap_subvolume
        live_subvol_name = plan.live_subvol_name
        using_subvol_map = plan.using_subvol_map
        script_live_path = plan.script_live_path
        backup_path = plan.backup_path

        # Check nested subvolumes.
        # Note: `btrfs_utils.get_nested_subvs` depends on `mount_attributes`(`live_path`).
        # In a read-only snapshot, the `live_path` (/) points to the snapshot, which may not be what we want.
        # It is best to skip this check in offline mode.
        nested_subdirs: list[str] = []
        if using_subvol_map:
            logging.warning(
                f"Skipped any nested subvolume detection with {snap_source!r} in --subvol-map."
            )
        else:
            nested_subdirs = btrfs_utils.get_nested_subvs(snap.target, live_subvol_name)
            if nested_subdirs:
                nested_subv_msg = (
                    f"Nested subvolume{'s' if len(nested_subdirs) > 1 else ''} "
                    f"{', '.join(f"'{x}'" for x in nested_subdirs)} "
                    f"detected inside {live_subvol_name!r}."
                )
                logging.warning(nested_subv_msg)

        # 3. Logic to switch to the mount point for recovery.
        # The if block ensures this is executed once even if multiple subvolumes
        # are part of the same file system.
        temp_mount_pt = temp_mount_points[snap_subvolume.device]
        if current_dir != temp_mount_pt:
            sh_lines += [f"cd {temp_mount_pt}", ""]
            current_dir = temp_mount_pt

        if using_subvol_map:
            sh_lines.append(
                f"# Using --subvol-map: {snap_source!r} -> {live_subvol_name!r}."
            )

        # If the subvolume being rolled back is nested, warn (backup name was
        # normalized with / -> _ during planning).
        if "/" in script_live_path:
            logging.warning(
                f"Rolling back snapshot of nested subvolume {script_live_path!r} is experimental."
            )

        # Normalize '/' so the post-reboot path matches the top-level backup name.
        # E.g. script_live_path='volume/nested1' -> '.../rollback_..._volume_nested1',
        # not '.../rollback_..._volume/nested1' (a nonexistent subdirectory).
        backup_path_after_reboot = shlex.quote(
            f"{os.path.dirname(snap.target)}/rollback_{now_str}_{script_live_path.replace('/', '_')}"
        )
        sh_lines.append(f"mv {script_live_path} {backup_path}")
        backup_paths.append(backup_path_after_reboot)
        sh_lines.append(f"btrfs subvolume snapshot {snap.target} {script_live_path}")

        nested_subvol_commands += _handle_nested_subvolume(
            nested_dirs=nested_subdirs,
            old_live_path=backup_path_after_reboot,
            new_live_path=snap_source,
        )

        # If the snapshot was taken by installation hook, the lock file may exist.
        if os.path.isfile(snap.target + _PACMAN_LOCK_FILE):
            sh_lines.append(f"rm {script_live_path}{_PACMAN_LOCK_FILE}")

        sh_lines.append("")
    sh_lines += ["echo Please reboot to complete the rollback.", "echo"]
    sh_lines.append("echo After reboot you may delete -")
    for backup_path in backup_paths:
        sh_lines.append(f'echo "# sudo btrfs subvolume delete {backup_path}"')

    if nested_subvol_commands:
        logging.warning(
            "You will need to manually move nested subvolumes after rollback."
        )
        sh_lines += [
            "",
            "echo Support for nested subvolume is limited. See FAQ on Nested Subvolumes.",
            "echo Please review tentative commands below carefully, and run them after a reboot to manually move the subvolumes.",
        ]
        sh_lines += nested_subvol_commands
    return sh_lines
