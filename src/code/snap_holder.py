"""Encapsulates a btrfs snapshot, and relevant metadata.

The existence of this object doesn't mean the snapshot exists;
it can also be an empty place holder.
"""

import dataclasses
import datetime
import json
import os

from . import utils

TIME_FORMAT = r'%Y%m%d%H%M%S'
TIME_FORMAT_LEN = 14

# Set this to True to globally disable snapshot changes.
DRYRUN = False


def _execute_sh(cmd: str):
  if DRYRUN:
    print('Would run ' + cmd)
  else:
    utils.execute_sh(cmd)


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
    if DRYRUN:
      print(f'Would create {fname}: {data}')
      return
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
    timestr = self._target[-TIME_FORMAT_LEN:]
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
    _execute_sh('btrfs subvolume snapshot -r '
                f'{parent} {self._target}')

  def delete(self) -> None:
    _execute_sh(f'btrfs subvolume delete {self._target}')
    if not DRYRUN:
      if os.path.exists(self._metadata_fname):
        os.remove(self._metadata_fname)
    else:
      print(f'Would delete {self._metadata_fname}')
