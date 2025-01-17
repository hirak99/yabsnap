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

import dataclasses
import datetime
import os

from .. import global_flags

from typing import Iterable, Optional

# This will be cleaned up if it exists by rollback script.
_PACMAN_LOCK_FILE = "/var/lib/pacman/db.lck"


@dataclasses.dataclass
class _MountAttributes:
    # The device e.g. /mnt/volume/subv under which we have the subv or its parent is mounted.
    device: str
    subvol_name: str


def _get_mount_attributes(
    mount_point: str, mtab_lines: Iterable[str]
) -> _MountAttributes:
    # For a mount point, this denotes the longest path that was seen in /etc/mtab.
    # This is therefore the point where that directory is mounted.
    longest_match_to_mount_point = ""
    # Which line matches the mount point.
    matched_line: str = ""
    for this_line in mtab_lines:
        this_tokens = this_line.split()
        if mount_point.startswith(this_tokens[1]):
            if len(this_tokens[1]) > len(longest_match_to_mount_point):
                longest_match_to_mount_point = this_tokens[1]
                matched_line = this_line

    if not matched_line:
        raise ValueError(f"Mount point not found: {mount_point}")
    tokens = matched_line.split()

    if tokens[2] != "btrfs":
        raise ValueError(f"Mount point is not btrfs: {mount_point} ({tokens[2]})")
    mount_param: str = ""
    for mount_param in tokens[3].split(","):
        subvol_prefix = "subvol="
        if mount_param.startswith(subvol_prefix):
            break
    else:
        raise RuntimeError(f"Could not find subvol= in {matched_line!r}")
    subvol_name = mount_param[len(subvol_prefix) :]
    if tokens[1] != mount_point:
        nested_subvol = mount_point.removeprefix(tokens[1])
        assert nested_subvol.startswith("/")
        subvol_name = nested_subvol
    return _MountAttributes(device=tokens[0], subvol_name=subvol_name)


def _get_mount_attributes_from_mtab(mount_point: str) -> _MountAttributes:
    return _get_mount_attributes(mount_point, open("/etc/mtab"))


def _get_now_str():
    return datetime.datetime.now().strftime(global_flags.TIME_FORMAT)


def rollback_gen(source_dests: list[tuple[str, str]]) -> list[str]:
    if not source_dests:
        return ["# No snapshot matched to rollback."]

    sh_lines: list[str] = []

    # Mount all required volumes at root.
    mount_points: dict[str, str] = {}
    for source, _ in source_dests:
        live_subvolume = _get_mount_attributes_from_mtab(source)
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
    for source, dest in source_dests:
        live_subvolume = _get_mount_attributes_from_mtab(source)
        backup_subvolume = _get_mount_attributes_from_mtab(os.path.dirname(dest))
        # The snapshot must be on the same block device as the original (target) volume.
        assert backup_subvolume.device == live_subvolume.device
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

    return sh_lines
