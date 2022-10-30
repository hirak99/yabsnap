# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import configparser
import dataclasses
import datetime
import pathlib
import os

from typing import Iterator, Optional

# Shortens the scheduled times by this amount. This ensures that sheduled backup
# happens, even if previous backup didn't expire by this much time.
#
# Since the scheduled job runs once per hour, this will not result in denser
# snapshots; just the deletion check will be lineant.
_DURATION_BUFFER = datetime.timedelta(minutes=3)

# Where config files are stored.
_CONFIG_PATH = pathlib.Path('/etc/yabsnap/configs')


@dataclasses.dataclass
class Config:
  config_file: str

  source: str
  dest_prefix: str
  # Only snapshots older than this will be deleted.
  min_keep_secs: int = 30 * 60
  # How many user backups to keep.
  keep_user: int = 1
  # How many to keep on pacman installation or updates.
  keep_preinstall: int = 0
  # Will keep this many of snapshots; rest will be removed during housekeeping.
  keep_hourly: int = 0
  keep_daily: int = 0
  keep_weekly: int = 0
  keep_monthly: int = 0
  keep_yearly: int = 0

  def is_schedule_enabled(self) -> bool:
    return (self.keep_hourly > 0 or self.keep_daily > 0 or
            self.keep_weekly > 0 or self.keep_monthly > 0 or
            self.keep_yearly > 0)

  @classmethod
  def from_configfile(cls, config_file: str) -> 'Config':
    inifile = configparser.ConfigParser()
    inifile.read(config_file)
    section = inifile['DEFAULT']
    result = cls(config_file=config_file,
                 source=section['source'],
                 dest_prefix=section['dest_prefix'])
    for key, value in section.items():
      if key not in {'source', 'dest_prefix'}:
        setattr(result, key, int(value))
    return result

  @property
  def deletion_rules(self) -> list[tuple[datetime.timedelta, int]]:
    return [
        (datetime.timedelta(hours=1) - _DURATION_BUFFER, self.keep_hourly),
        (datetime.timedelta(days=1) - _DURATION_BUFFER, self.keep_daily),
        (datetime.timedelta(weeks=1) - _DURATION_BUFFER, self.keep_weekly),
        (datetime.timedelta(days=30) - _DURATION_BUFFER, self.keep_monthly),
        (datetime.timedelta(days=365.24) - _DURATION_BUFFER, self.keep_yearly),
    ]

  @property
  def mount_path(self) -> str:
    return os.path.dirname(self.dest_prefix)


def iterate_configs(source: Optional[str]) -> Iterator[Config]:
  if not _CONFIG_PATH.is_dir():
    print('No config found. Use \'create-config\' command to create a config.')
    return
  for fname in _CONFIG_PATH.iterdir():
    config = Config.from_configfile(str(fname))
    if not config.source or not config.dest_prefix:
      print(f'WARNING: Skipping invalid configuration {fname}'
            ' (please specify source and dest_prefix)')
      continue
    if not source or config.source == source:
      yield config


def is_schedule_enabled() -> bool:
  for config in iterate_configs(None):
    if config.is_schedule_enabled():
      return True
  return False


def create_config(name: str, source: str | None):

  inadmissible_chars = '@/.'
  if any(c in inadmissible_chars for c in name):
    print(
        f'Error: Config name should be a file name, without following chars: {inadmissible_chars}'
    )
    return

  _config_fname = _CONFIG_PATH / f'{name}.conf'
  if _config_fname.exists():
    print(f'Already exists: {_config_fname}')
    return

  script_dir = pathlib.Path(os.path.realpath(__file__)).parent
  lines: list[str] = []
  for line in open(script_dir / 'example_config.conf'):
    line = line.strip()
    if source and line.startswith('source ='):
      line = f'source = {source}'
    elif line.startswith('dest_prefix ='):
      line = f'dest_prefix = /.snapshots/@{name}-'
    lines.append(line)

  try:
    _config_fname.parent.mkdir(parents=True, exist_ok=True)
    with _config_fname.open('w') as out:
      out.write('\n'.join(lines))
  except PermissionError:
    print(f'Could not access or create {_config_fname}; run as root?')
    return

  print()
  print(f'Created: {_config_fname}')
  if not source:
    print("Please edit the file to set 'source = ' field.")
