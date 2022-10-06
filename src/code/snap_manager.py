import datetime
import logging
import os
import subprocess

from . import configs
from . import deletion_logic

from typing import Iterator

_TIME_FORMAT = r'%Y%m%d%H%M%S'

# To prevent slight differences in starting time of the cron job,
# will backup even if previous backup didn't expire by this much time.
_TRIGGER_BUFFER = datetime.timedelta(minutes=3)

# TODO: Add operations -
# --hourlyrun
# --pacpre COMMENT


def _get_old_backups(
    config: configs.Config) -> Iterator[tuple[datetime.datetime, str]]:
  configdir = os.path.dirname(config.dest_prefix)
  for fname in os.listdir(configdir):
    pathname = os.path.join(configdir, fname)
    if pathname.startswith(config.dest_prefix):
      timestr = pathname[len(config.dest_prefix):]
      snaptime = datetime.datetime.strptime(timestr, _TIME_FORMAT)
      yield snaptime, pathname


class SnapManager:

  def __init__(self, config: configs.Config) -> None:
    self._config = config
    self._now = datetime.datetime.now()
    self._now_str = self._now.strftime(_TIME_FORMAT)
    self._dryrun = False

  def _execute_sh(self, command: str, error_ok=False) -> None:
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

  def _remove_expired(self, snaps: list[tuple[datetime.datetime, str]]) -> bool:
    """Deletes old backups. Returns True if new backup is needed."""
    buffered_now = self._now + _TRIGGER_BUFFER
    # Append a placeholder to denote the backup that will be taken next.
    # If this is deleted, it would indicate not to create new backup.
    snaps.append((buffered_now, ''))

    delete = deletion_logic.DeleteManager(self._config.deletion_rules)
    for when, fname in delete.get_deletes(buffered_now, snaps):
      if fname == '':
        logging.info(f'New backup not needed for {self._config.source}')
        return False
      elapsed_secs = (self._now - when).total_seconds()
      if elapsed_secs > self._config.min_keep_secs:
        self._execute_sh(f'btrfs subvolume delete {fname}')
      else:
        logging.info(f'Not enough time passed, not deleting {fname}')

    return True

  def on_pacman(self):
    if self._config.on_pacman:
      self._execute_sh(
          'btrfs subvolume snapshot -r '
          f'{self._config.source} {self._config.dest_prefix}{self._now_str}')

  def do_update(self):
    previous_snaps = list(_get_old_backups(self._config))
    need_new = self._remove_expired(previous_snaps)
    if need_new:
      self._execute_sh(
          'btrfs subvolume snapshot -r '
          f'{self._config.source} {self._config.dest_prefix}{self._now_str}')
