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

from . import configs
from . import snap_holder
from . import snap_operator

from typing import Iterable, Optional


@dataclasses.dataclass
class MountAttributes:
  device: str
  subvol_name: str


def _get_mount_attributes(mount_point: str) -> MountAttributes:
  for line in open('/etc/mtab'):
    tokens = line.split()
    if tokens[1] == mount_point:
      break
  else:
    raise ValueError(f'Mount point not found: {mount_point}')

  if tokens[2] != 'btrfs':
    raise ValueError(f'Mount point is not btrfs: {mount_point} ({tokens[2]})')
  for mount_param in tokens[3].split(','):
    subvol_prefix = 'subvol='
    if not mount_param.startswith(subvol_prefix):
      continue
    subvol_name = mount_param[len(subvol_prefix):]
    return MountAttributes(device=tokens[0], subvol_name=subvol_name)
  raise ValueError(f'Could not determine subvol in {line!r}')


def rollback(configs_iter: Iterable[configs.Config], path_suffix: str):
  to_rollback: list[snap_holder.Snapshot] = []
  for config in configs_iter:
    snapper = snap_operator.SnapOperator(config)
    snap = snapper.find_target(path_suffix)
    if snap:
      to_rollback.append(snap)

  sh_lines = [
      '#!/bin/bash',
      '# Save this to a script, review and run as root to perform the rollback.',
      '',
      'set -uexo pipefail',
      '',
  ]

  # Mount all required volumes at root.
  mount_points: dict[str, str] = {}
  for snap in to_rollback:
    mount_attr = _get_mount_attributes(snap.metadata.source)
    if mount_attr.device not in mount_points:
      mount_pt = f'/run/mount/_yabsnap_internal_{len(mount_points)}'
      mount_points[mount_attr.device] = mount_pt
      sh_lines += [
          f'mkdir -p {mount_pt}',
          f'mount {mount_attr.device} {mount_pt} -o subvolid=5'
      ]

  now_str = datetime.datetime.now().strftime(snap_holder.TIME_FORMAT)

  sh_lines.append('')
  backup_paths: list[str] = []
  current_dir: Optional[str] = None
  for snap in to_rollback:
    mount_attr = _get_mount_attributes(snap.metadata.source)
    target_mount = _get_mount_attributes(os.path.dirname(snap.target))
    assert target_mount.device == mount_attr.device
    mount_pt = mount_points[mount_attr.device]
    if current_dir != mount_pt:
      sh_lines += [f'cd {mount_pt}', '']
      current_dir = mount_pt
    live_path = mount_attr.subvol_name[1:]
    backup_path = f'{target_mount.subvol_name[1:]}/rollback_{now_str}_{mount_attr.subvol_name[1:]}'
    backup_path_after_reboot = f'{os.path.dirname(snap.target)}/rollback_{now_str}_{mount_attr.subvol_name[1:]}'
    # sh_lines.append(f'[[ -e {backup_path} ]] && btrfs subvolume delete {backup_path}')
    sh_lines.append(f'mv {live_path} {backup_path}')
    backup_paths.append(backup_path_after_reboot)
    sh_lines.append(f'btrfs subvolume snapshot {snap.target} {live_path}')
    sh_lines.append('')
  sh_lines += ['echo Please reboot to complete the rollback.', 'echo']
  sh_lines.append('echo After reboot you may delete -')
  for backup_path in backup_paths:
    sh_lines.append(f'echo "# sudo btrfs subvolume delete {backup_path}"')

  print('\n'.join(sh_lines))
