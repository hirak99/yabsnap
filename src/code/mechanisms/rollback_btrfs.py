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

from . import btrfs_utils
from . import common_fs_utils
from .. import global_flags

from typing import Optional

# This will be cleaned up if it exists by rollback script.
_PACMAN_LOCK_FILE = "/var/lib/pacman/db.lck"


def _get_now_str():
    return datetime.datetime.now().strftime(global_flags.TIME_FORMAT)


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
    nested_subvol_warnings: list[str] = []
    for source, dest in source_dests:
        nested_subdirs = btrfs_utils.get_nested_subvs(source)
        if nested_subdirs:
            nested_subv_msg = (
                f"Nested subvolume{'s' if len(nested_subdirs) > 1 else ''} "
                f"'{', '.join(nested_subdirs)}' inside '{source}' will not be included in rollback."
            )
            nested_subvol_warnings.append(nested_subv_msg)
        live_subvolume = common_fs_utils.mount_attributes(source)
        backup_subvolume = common_fs_utils.mount_attributes(os.path.dirname(dest))
        # The snapshot must be on the same block device as the original (target) volume.
        assert (
            backup_subvolume.device == live_subvolume.device
        ), f"{backup_subvolume=} {live_subvolume=}"
        mount_pt = mount_points[live_subvolume.device]
        if current_dir != mount_pt:
            sh_lines += [f"cd {mount_pt}", ""]
            current_dir = mount_pt
        live_path = drop_root_slash(live_subvolume.subvol_name)
        backup_path = f"{drop_root_slash(backup_subvolume.subvol_name)}/rollback_{now_str}_{live_path}"
        backup_path_after_reboot = (
            f"{os.path.dirname(dest)}/rollback_{now_str}_{live_path}"
        )
        # sh_lines.append(f'[[ -e {backup_path} ]] && btrfs subvolume delete {backup_path}')
        sh_lines.append(f"mv {live_path} {backup_path}")
        backup_paths.append(backup_path_after_reboot)
        sh_lines.append(f"btrfs subvolume snapshot {dest} {live_path}")
        if os.path.isfile(dest + _PACMAN_LOCK_FILE):
            sh_lines.append(f"rm {live_path}{_PACMAN_LOCK_FILE}")
        sh_lines.append("")
    sh_lines += ["echo Please reboot to complete the rollback.", "echo"]
    sh_lines.append("echo After reboot you may delete -")
    for backup_path in backup_paths:
        sh_lines.append(f'echo "# sudo btrfs subvolume delete {backup_path}"')

    if nested_subvol_warnings:
        nested_subvol_warnings.append(
            "Support for nested subvolumes is limited. You will need to manually move them after rollback."
        )
        sh_lines.append("")
        for warning in nested_subvol_warnings:
            logging.warning(warning)
            sh_lines.append(f"# WARNING: {warning}")
    return sh_lines
