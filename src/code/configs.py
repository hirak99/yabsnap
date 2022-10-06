import configparser
import dataclasses
import datetime

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


_CONFIGS: list[Config] = [
    Config(source='/',
           dest_prefix='/.snapshots/@root-',
           keep_preinstall=3,
           keep_user=3,
           keep_daily=3,
           keep_weekly=3,
           keep_monthly=2),
    Config(source='/home',
           dest_prefix='/.snapshots/@home-',
           keep_preinstall=3,
           keep_user=3,
           keep_hourly=3,
           keep_daily=5),
]


def iterate_configs(source: Optional[str]) -> Iterator[Config]:
  for config in _CONFIGS:
    if not source or config.source == source:
      yield config
