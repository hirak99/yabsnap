import dataclasses
import datetime


@dataclasses.dataclass
class Config:
  source: str
  dest_prefix: str
  on_pacman: bool
  # Only snapshots older than this will be deleted.
  min_keep_secs: int = int(3.5 * 60 * 60)  # 3.5 hrs
  # Will keep this many of snapshots; rest will be removed during housekeeping.
  keep_hourly: int = 0
  keep_daily: int = 0
  keep_weekly: int = 0
  keep_monthly: int = 0
  keep_yearly: int = 0

  @property
  def deletion_rules(self) -> dict[datetime.timedelta, int]:
    return {
        datetime.timedelta(hours=1): self.keep_hourly,
        datetime.timedelta(days=1): self.keep_daily,
        datetime.timedelta(weeks=1): self.keep_weekly,
        datetime.timedelta(days=30): self.keep_monthly,
        datetime.timedelta(days=365.24): self.keep_yearly,
    }


CONFIGS: list[Config] = [
    Config(source='/',
           dest_prefix='/.snapshots/@root-',
           on_pacman=True,
           keep_daily=3,
           keep_weekly=3,
           keep_monthly=2),
    Config(source='/home',
           dest_prefix='/.snapshots/@home-',
           on_pacman=True,
           keep_hourly=3,
           keep_daily=5),
]
