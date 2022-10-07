import argparse
import logging

from . import configs
from . import snap_holder
from . import snap_operator


def _parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument('--source', help='Restrict to config with this source path.')
  parser.add_argument('--dry-run', help='If passed, will disable all snapshot creation and deletion.', action='store_true')
  subparsers = parser.add_subparsers(dest='command')

  # User commands.
  subparsers.add_parser('list')
  create = subparsers.add_parser('create', help='Create new snapshots.')
  create.add_argument('--comment', help='Comment attached to this snapshot.')
  create_config = subparsers.add_parser('create-config', help='Bootstrap a config for new filesystem to snapshot.')
  create_config.add_argument('config', help='Name to be given to config file, e.g. "home".')
  delete = subparsers.add_parser('delete', help='Delete a snapshot created by yabsnap.')
  delete.add_argument('target', help='Full path of the target snapshot to be removed.')

  # Internal commands used in scheduling and pacman hook.
  subparsers.add_parser('internal-cronrun', help=argparse.SUPPRESS)
  subparsers.add_parser('internal-preupdate', help=argparse.SUPPRESS)

  args = parser.parse_args()
  return args


def main():
  args = _parse_args()
  command: str = args.command
  if not command:
    print('Start with --help to see common args.')
    return

  if args.dry_run:
    snap_holder.DRYRUN = True

  logging.basicConfig(
      level=logging.INFO if command.startswith('internal-') else logging.WARNING)

  if command == 'create-config':
    configs.create_config(args.config)
    return

  if command == 'delete':
    for config in configs.iterate_configs(source=args.source):
      snapper = snap_operator.SnapOperator(config)
      snap = snapper.find_target(args.target)
      if snap:
        snap.delete()
        snapper.btrfs_sync(force=True)
        break
    else:
      print(f'Target {args.target} not found in any config.')
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
      raise ValueError(f'Unknown command {command}')
    snapper.btrfs_sync()


if __name__ == '__main__':
  main()
