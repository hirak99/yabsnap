import argparse
import logging

from . import configs
from . import snap_manager


def _parse_args() -> bool:
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  subparsers.add_parser('cronrun')
  args = parser.parse_args()
  if not args.command:
    print('Start with --help to see common args.')
    return False
  return True


def main():
  logging.basicConfig(level=logging.INFO)

  if not _parse_args():
    return

  for config in configs.CONFIGS:
    snapper = snap_manager.SnapManager(config)
    snapper.do_update()


if __name__ == '__main__':
  main()
