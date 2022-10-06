"""Encapsulates a btrfs snapshot, and relevant metadata.

The existence of this object doesn't mean the snapshot exists;
it can also be an empty place holder.
"""

import datetime
import logging
import subprocess

_TIME_FORMAT = r'%Y%m%d%H%M%S'


class Snapshot:

  def __init__(self, target: str) -> None:
    self._target = target
    timestr = self._target[-14:]
    self._snaptime = datetime.datetime.strptime(timestr, _TIME_FORMAT)
    self._dryrun = False

  @property
  def target(self):
    return self._target

  @property
  def snaptime(self):
    return self._snaptime

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
