"""Encapsulates a btrfs snapshot, and relevant metadata.

The existence of this object doesn't mean the snapshot exists;
it can also be an empty place holder.
"""

import logging
import subprocess


class Snapshot:

  def __init__(self, target: str) -> None:
    self._target = target
    self._dryrun = False

  def _execute_sh(self, command: str, error_ok: bool = False) -> None:
    if self._dryrun:
      logging.info(f'# {command}')
      return

    logging.info(f'Running {command}')
    try:
      subprocess.run(command.split(' '), check=True)
    except subprocess.CalledProcessError as e:
      if not error_ok:
        raise e
      logging.warn(f'Process had error {e}')

  def create_from(self, parent: str) -> None:
    self._execute_sh('btrfs subvolume snapshot -r '
                     f'{parent} {self._target}')

  def delete(self) -> None:
    self._execute_sh(f'btrfs subvolume delete {self._target}')
