import argparse
import logging

from . import configs
from . import snap_manager


def _parse_args() -> str:
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  subparsers.add_parser('cronrun')
  subparsers.add_parser('pacmanpre')
  args = parser.parse_args()
  return args.command


def main():
  logging.basicConfig(level=logging.INFO)

  command = _parse_args()
  if not command:
    print('Start with --help to see common args.')
    return

  for config in configs.CONFIGS:
    snapper = snap_manager.SnapManager(config)
    if command == 'cronrun':
      snapper.do_update()
    elif command == 'pacmanpre':
      snapper.on_pacman()
    else:
      raise ValueError(f'Unknown command {command}')


if __name__ == '__main__':
  main()
