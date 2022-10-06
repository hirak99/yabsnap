import argparse
import logging

from . import configs
from . import snap_operator


def _parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  subparsers.add_parser('internal-cronrun')
  subparsers.add_parser('internal-preupdate')
  subparsers.add_parser('list')
  subparsers.add_parser('create')
  deleter = subparsers.add_parser('delete')
  deleter.add_argument('target')
  args = parser.parse_args()
  return args


def main():
  args = _parse_args()
  command: str = args.command
  if not command:
    print('Start with --help to see common args.')
    return

  logging.basicConfig(
      level=logging.INFO if command.startswith('internal-') else logging.WARNING)

  if command == 'delete':
    for config in configs.CONFIGS:
      snapper = snap_operator.SnapOperator(config)
      snap = snapper.find_target(args.target)
      if snap:
        snap.delete()
        print('Syncing ...', flush=True)
        snapper.btrfs_sync()
        break
    else:
      print(f'Target {args.target} not found in any configs.')
    return

  for config in configs.CONFIGS:
    if command == 'list':
      print(f'Config: source={config.source}')
    snapper = snap_operator.SnapOperator(config)
    if command == 'internal-cronrun':
      snapper.scheduled()
    elif command == 'internal-preupdate':
      snapper.on_pacman()
    elif command == 'list':
      snapper.list_backups()
    elif command == 'create':
      snapper.create()
    else:
      raise ValueError(f'Unknown command {command}')


if __name__ == '__main__':
  main()
