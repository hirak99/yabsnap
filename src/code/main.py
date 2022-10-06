import argparse
import logging

from . import configs
from . import snap_operator


def _parse_args() -> str:
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  subparsers.add_parser('internal-cronrun')
  subparsers.add_parser('internal-preupdate')
  subparsers.add_parser('list')
  subparsers.add_parser('create')
  args = parser.parse_args()
  return args.command


def main():
  command = _parse_args()
  if not command:
    print('Start with --help to see common args.')
    return

  logging.basicConfig(
      level=logging.WARNING if command == 'list' else logging.INFO)

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
