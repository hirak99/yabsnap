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

import argparse
import datetime
import logging

from . import configs
from . import rollbacker
from . import os_utils
from . import snap_holder
from . import snap_operator

from typing import Iterable


def _parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(prog='yabsnap')
  parser.add_argument('--sync',
                      help='Wait for btrfs to sync for any delete operations.',
                      action='store_true')
  parser.add_argument('--source',
                      help='Restrict to config with this source path.')
  parser.add_argument(
      '--dry-run',
      help='If passed, will disable all snapshot creation and deletion.',
      action='store_true')
  subparsers = parser.add_subparsers(dest='command')

  # User commands.
  subparsers.add_parser('list')
  create = subparsers.add_parser('create', help='Create new snapshots.')
  create.add_argument('--comment', help='Comment attached to this snapshot.')
  create_config = subparsers.add_parser(
      'create-config',
      help='Bootstrap a config for new filesystem to snapshot.')
  create_config.add_argument(
      'config_name', help='Name to be given to config file, e.g. "home".')
  delete = subparsers.add_parser('delete',
                                 help='Delete a snapshot created by yabsnap.')
  rollback = subparsers.add_parser(
      'rollback-gen', help='Generate script to rollback one or more snaps.')

  for command_with_target in [delete, rollback]:
    command_with_target.add_argument(
        'target_suffix', help='Datetime string, or full path of a snapshot.')

  # Internal commands used in scheduling and pacman hook.
  subparsers.add_parser('internal-cronrun', help=argparse.SUPPRESS)
  subparsers.add_parser('internal-preupdate', help=argparse.SUPPRESS)

  args = parser.parse_args()
  return args


def _btrfs_sync(dryrun: bool, mount_paths: set[str]) -> None:
  for mount_path in sorted(mount_paths):
    if dryrun:
      print(f'Would sync {mount_path}')
      continue
    print('Syncing ...', flush=True)
    os_utils.execute_sh(f'btrfs subvolume sync {mount_path}')


def _delete_snap(configs_iter: Iterable[configs.Config], path_suffix: str,
                 sync: bool):
  found = False
  for config in configs_iter:
    snap = snap_operator.find_target(config, path_suffix)
    if snap:
      found = True
      snap.delete()
      # TODO: synce if 'sync' is true.
      if sync:
        _btrfs_sync(snap_holder.DRYRUN, {config.mount_path})

  if not found:
    print(f'Target {path_suffix} not found in any config.')


def main():
  args = _parse_args()
  command: str = args.command
  if not command:
    print('Start with --help to see common args.')
    return

  if args.dry_run:
    snap_holder.DRYRUN = True

  logging.basicConfig(level=logging.INFO if command.
                      startswith('internal-') else logging.WARNING)

  if configs.is_schedule_enabled():
    if not os_utils.timer_enabled():
      print('\n'.join([
          '',
          '*** NOTE - Backup schedule exists but yabsnap.timer is not active ***',
          'To enable scheduled backups, please run -',
          '  sudo systemctl enable --now yabsnap.timer',
          '',
      ]))

  if command == 'create-config':
    configs.create_config(args.config_name, args.source)
    return

  if command == 'delete':
    _delete_snap(configs.iterate_configs(source=args.source),
                 path_suffix=args.target_suffix,
                 sync=args.sync)
    return

  if command == 'rollback-gen':
    rollbacker.rollback(configs.iterate_configs(source=args.source),
                        args.target_suffix)
    return

  # Single timestamp for all operations.
  now = datetime.datetime.now()

  # Which mount paths to sync.
  to_sync: set[str] = set()

  # Commands that need to access existing config.
  for config in configs.iterate_configs(source=args.source):
    if command == 'list':
      print(f'Config: {config.config_file} (source={config.source})')
    snapper = snap_operator.SnapOperator(config, now)
    if command == 'internal-cronrun':
      snapper.scheduled()
    elif command == 'internal-preupdate':
      snapper.on_pacman()
    elif command == 'list':
      snapper.list_backups()
    elif command == 'create':
      snapper.create(args.comment)
    else:
      raise ValueError(f'Command not implemented: {command}')

    if snapper.need_sync:
      to_sync.add(config.mount_path)

  if args.sync:
      _btrfs_sync(args.dry_run, to_sync)


if __name__ == '__main__':
  main()
