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

import datetime
import logging
import os
import shlex

from . import btrfs_utils
from . import common_fs_utils
from .. import global_flags

from typing import Iterator, Optional

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
        yield f'echo "sudo rmdir {new_live_path}/{nested_dir}"  # Empty, if snapshot was taken with the nested subvolume.'
        yield f'echo "sudo mv {old_live_path}/{nested_dir} {new_live_path}/{nested_dir}"'


def rollback_gen(source_dests: list[tuple[str, str]]) -> list[str]:
    if not source_dests:
        return ["# No snapshot matched to rollback."]

    sh_lines: list[str] = []

    # Mount all required volumes at root.
    mount_points: dict[str, str] = {}
    for live_path, _ in source_dests:
        live_subvolume = common_fs_utils.mount_attributes(live_path)
        if live_subvolume.device not in mount_points:
            mount_pt = f"/run/mount/_yabsnap_internal_{len(mount_points)}"
            mount_points[live_subvolume.device] = mount_pt
            sh_lines += [
                f"mkdir -p {mount_pt}",
                f"mount {live_subvolume.device} {mount_pt} -o subvolid=5",
            ]

    now_str = _get_now_str()

    def drop_root_slash(s: str) -> str:
        if s[0] != "/":
            raise RuntimeError(f"Could not drop initial / from {s!r}")
        if "/" in s[1:]:
            raise RuntimeError(f"Unexpected / after the first one in subvolume {s!r}")
        return s[1:]

    sh_lines.append("")
    backup_paths: list[str] = []
    current_dir: Optional[str] = None
    nested_subvol_commands: list[str] = []
    for live_path, snap_path in source_dests:
        nested_subdirs = btrfs_utils.get_nested_subvs(live_path)
        if nested_subdirs:
            nested_subv_msg = (
                f"Nested subvolume{'s' if len(nested_subdirs) > 1 else ''} "
                f"{', '.join(f"'{x}'" for x in nested_subdirs)} "
                f"detected inside {live_path!r}."
            )
            logging.warning(nested_subv_msg)
        live_subvolume = common_fs_utils.mount_attributes(live_path)
        snap_subvolume = common_fs_utils.mount_attributes(os.path.dirname(snap_path))
        # The snapshot must be on the same block device as the original (target) volume.
        assert (
            snap_subvolume.device == live_subvolume.device
        ), f"{snap_subvolume=} {live_subvolume=}"
        mount_pt = mount_points[live_subvolume.device]
        if current_dir != mount_pt:
            sh_lines += [f"cd {mount_pt}", ""]
            current_dir = mount_pt
        # The path where it will be mounted when running the script.
        script_live_path = drop_root_slash(live_subvolume.subvol_name)
        backup_path = f"{drop_root_slash(snap_subvolume.subvol_name)}/rollback_{now_str}_{script_live_path}"
        backup_path_after_reboot = shlex.quote(
            f"{os.path.dirname(snap_path)}/rollback_{now_str}_{script_live_path}"
        )
        sh_lines.append(f"mv {script_live_path} {backup_path}")
        backup_paths.append(backup_path_after_reboot)
        sh_lines.append(f"btrfs subvolume snapshot {snap_path} {script_live_path}")

        nested_subvol_commands += _handle_nested_subvolume(
            nested_dirs=nested_subdirs,
            old_live_path=backup_path_after_reboot,
            new_live_path=live_path,
        )

        # If the snapshot was taken by installation hook, the lock file may exist.
        if os.path.isfile(snap_path + _PACMAN_LOCK_FILE):
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
