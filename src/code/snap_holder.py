"""Encapsulates a btrfs snapshot, and relevant metadata.

The existence of this object doesn't mean the snapshot exists;
it can also be an empty place holder.
"""

import dataclasses
import datetime
import json
import os

from . import shell

TIME_FORMAT = r'%Y%m%d%H%M%S'


@dataclasses.dataclass
class _Metadata:
  source: str = ''
  # Can be one of -
  # I - Package installation or system update
  # S - Scheduled
  # U - User
  trigger: str = ''
  comment: str = ''

  def save_file(self, fname: str) -> None:
    # Ignore empty strings.
    data = {k: v for k, v in dataclasses.asdict(self).items() if v != ''}
    with open(fname, 'w') as f:
      json.dump(data, f, indent=2)

  @classmethod
  def load_file(cls, fname: str) -> '_Metadata':
    if not os.path.isfile(fname):
      return cls()
    with open(fname) as f:
      return cls(**json.load(f))


class Snapshot:

  def __init__(self, target: str) -> None:
    self._target = target
    timestr = self._target[-14:]
    self._snaptime = datetime.datetime.strptime(timestr, TIME_FORMAT)
    self._metadata_fname = target + '-meta.json'
    self.metadata = _Metadata.load_file(self._metadata_fname)
    self._dryrun = False

  @property
  def target(self):
    return self._target

  @property
  def snaptime(self):
    return self._snaptime

  def create_from(self, parent: str) -> None:
    self.metadata.source = parent
    self.metadata.save_file(self._metadata_fname)
    shell.execute_sh('btrfs subvolume snapshot -r '
                     f'{parent} {self._target}')

  def delete(self) -> None:
    shell.execute_sh(f'btrfs subvolume delete {self._target}')
    if os.path.exists(self._metadata_fname):
      os.remove(self._metadata_fname)
