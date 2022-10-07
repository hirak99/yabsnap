import argparse
import logging

from . import configs
from . import rollbacker
from . import snap_holder
from . import snap_operator

from typing import Iterable


def _parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
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
      'config', help='Name to be given to config file, e.g. "home".')
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


def _delete_snap(configs_iter: Iterable[configs.Config], path_suffix: str):
  found = False
  for config in configs_iter:
    snapper = snap_operator.SnapOperator(config)
    snap = snapper.find_target(path_suffix)
    if snap:
      found = True
      snap.delete()
      snapper.btrfs_sync(force=True)

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

  if command == 'create-config':
    configs.create_config(args.config)
    return

  if command == 'delete':
    _delete_snap(configs.iterate_configs(source=args.source),
                 args.target_suffix)
    return

  if command == 'rollback-gen':
    rollbacker.rollback(configs.iterate_configs(source=args.source),
                        args.target_suffix)
    return

  for config in configs.iterate_configs(source=args.source):
    if command == 'list':
      print(f'Config: {config.config_file} (source={config.source})')
    snapper = snap_operator.SnapOperator(config)
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
    snapper.btrfs_sync()


if __name__ == '__main__':
  main()
