import datetime
import logging
import os

from . import configs
from . import deletion_logic
from . import shell
from . import snap_holder

from typing import Iterable, Iterator, Optional

# To prevent slight differences in starting time of the cron job,
# will backup even if previous backup didn't expire by this much time.
_TRIGGER_BUFFER = datetime.timedelta(minutes=3)


def _get_old_backups(config: configs.Config) -> Iterator[snap_holder.Snapshot]:
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
    # Set to true on any delete operation.
    self._need_sync = False

  def _remove_expired(self, snaps: Iterable[snap_holder.Snapshot]) -> bool:
    """Deletes old backups. Returns True if new backup is needed."""
    buffered_now = self._now + _TRIGGER_BUFFER

    # Only consider scheduled backups for expiry.
    candidates = [(x.snaptime, x.target)
                  for x in snaps
                  if x.metadata.trigger in {'', 'S'}]
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
        self._need_sync = True
      else:
        logging.info(f'Not enough time passed, not deleting {target}')

    return True

  def _create_and_maintain_n_backups(self, count: int, trigger: str,
                                     comment: Optional[str]):
    if count > 0:
      snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
      snapshot.metadata.trigger = trigger
      if comment:
        snapshot.metadata.comment = comment
      snapshot.create_from(self._config.source)

    # Clean up old snaps.
    previous_snaps = [
        x for x in _get_old_backups(self._config)
        if x.metadata.trigger == trigger
    ]
    for expired in previous_snaps[:-count]:
      expired.delete()
      self._need_sync = True

  def btrfs_sync(self) -> None:
    if not self._need_sync:
      return
    print('Syncing ...', flush=True)
    shell.execute_sh(
        f'btrfs subvolume sync {os.path.dirname(self._config.dest_prefix)}')
    self._need_sync = False

  def find_target(self, target: str) -> Optional[snap_holder.Snapshot]:
    for snap in _get_old_backups(self._config):
      if snap.target == target:
        return snap_holder.Snapshot(target)
    return None

  def create(self, comment: Optional[str]):
    self._create_and_maintain_n_backups(count=self._config.keep_user,
                                        trigger='U',
                                        comment=comment)

  def on_pacman(self):
    self._create_and_maintain_n_backups(count=self._config.keep_preinstall,
                                        trigger='I',
                                        comment=None)

  def scheduled(self):
    previous_snaps = _get_old_backups(self._config)
    need_new = self._remove_expired(previous_snaps)
    if need_new:
      snapshot = snap_holder.Snapshot(self._config.dest_prefix + self._now_str)
      snapshot.metadata.trigger = 'S'
      snapshot.create_from(self._config.source)

  def list_backups(self):
    for snap in _get_old_backups(self._config):
      trigger_str = ''.join(
          c if snap.metadata.trigger == c else ' ' for c in 'SIU')
      print(f'{trigger_str}  ', end='')
      print(f'{snap.snaptime}  ', end='')
      print(f'{snap.target}  ', end='')
      print(snap.metadata.comment)
    print('')
