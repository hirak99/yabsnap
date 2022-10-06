import configparser
import dataclasses
import datetime
import pathlib
import os

from typing import Iterator, Optional


@dataclasses.dataclass
class Config:
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

  @classmethod
  def from_configfile(cls, config_file: str) -> 'Config':
    inifile = configparser.ConfigParser()
    inifile.read(config_file)
    section = inifile['DEFAULT']
    result = cls(source=section['source'], dest_prefix=section['dest_prefix'])
    if not result.source or not result.dest_prefix:
      raise ValueError(
          f'Invalid configuration, please specify source and dest_prefix in {config_file}'
      )
    for key, value in section.items():
      if key not in {'source', 'dest_prefix'}:
        setattr(result, key, int(value))
    return result

  @property
  def deletion_rules(self) -> dict[datetime.timedelta, int]:
    return {
        datetime.timedelta(hours=1): self.keep_hourly,
        datetime.timedelta(days=1): self.keep_daily,
        datetime.timedelta(weeks=1): self.keep_weekly,
        datetime.timedelta(days=30): self.keep_monthly,
        datetime.timedelta(days=365.24): self.keep_yearly,
    }


_CONFIG_PATH = pathlib.Path('/etc/yabsnap/configs')


def iterate_configs(source: Optional[str]) -> Iterator[Config]:
  if not _CONFIG_PATH.is_dir():
    print('No config found. Use \'create-config\' command to create a config.')
    return
  for fname in _CONFIG_PATH.iterdir():
    config = Config.from_configfile(str(fname))
    if not source or config.source == source:
      yield config


def create_config(name: str):
  _config_fname = _CONFIG_PATH / f'{name}.conf'
  if _config_fname.exists():
    print(f'Already exists: {_config_fname}')
    return
  script_dir = pathlib.Path(os.path.realpath(__file__)).parent
  with open(script_dir / 'example_config.conf') as f:
    try:
      _config_fname.parent.mkdir(parents=True, exist_ok=True)
      with _config_fname.open('w') as out:
        out.write(f.read())
    except PermissionError:
      print(f'Could not access or create {_config_fname}; run as root?')
  print(f'Created: {_config_fname}')
  print()
  print("Please edit to add values for 'source' and 'dest_prefix'.")
