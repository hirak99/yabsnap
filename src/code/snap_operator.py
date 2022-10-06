import datetime
import logging
import os

from . import configs
from . import deletion_logic
from . import snap_holder

from typing import Iterator

# To prevent slight differences in starting time of the cron job,
# will backup even if previous backup didn't expire by this much time.
_TRIGGER_BUFFER = datetime.timedelta(minutes=3)


def _get_old_backups(
    config: configs.Config) -> Iterator[snap_holder.Snapshot]:
  configdir = os.path.dirname(config.dest_prefix)
  for fname in os.listdir(configdir):
    pathname = os.path.join(configdir, fname)
    if not os.path.isdir(pathname):
      continue
    if not pathname.startswith(config.dest_prefix):
      continue
    yield snap_holder.Snapshot(pathname)


class SnapOperator:

  def __init__(self, config: configs.Config) -> None:
    self._config = config
    self._now = datetime.datetime.now()
    self._now_str = self._now.strftime(snap_holder.TIME_FORMAT)

  def _remove_expired(self, snaps: list[snap_holder.Snapshot]) -> bool:
    """Deletes old backups. Returns True if new backup is needed."""
    buffered_now = self._now + _TRIGGER_BUFFER

    candidates = [(x.snaptime, x.target) for x in snaps]
    # Append a placeholder to denote the backup that will be taken next.
    # If this is deleted, it would indicate not to create new backup.
    candidates.append((buffered_now, ''))

    delete = deletion_logic.DeleteManager(self._config.deletion_rules)
    for when, target in delete.get_deletes(buffered_now, candidates):
      if target == '':
        logging.info(f'New backup not needed for {self._config.source}')
        return False
      elapsed_secs = (self._now - when).total_seconds()
      if elapsed_secs > self._config.min_keep_secs:
        snap_holder.Snapshot(target).delete()
      else:
        logging.info(f'Not enough time passed, not deleting {target}')

    return True

  def on_pacman(self):
    if self._config.on_pacman:
      snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
      snapshot.metadata.tags = 'P'
      snapshot.create_from(self._config.source)

  def scheduled(self):
    previous_snaps = list(_get_old_backups(self._config))
    need_new = self._remove_expired(previous_snaps)
    if need_new:
      snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
      snapshot.metadata.tags = 'S'
      snapshot.create_from(self._config.source)
