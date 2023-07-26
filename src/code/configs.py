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
import logging
import pathlib
import os

from . import human_interval
from . import os_utils

from typing import Iterator, Optional

# Shortens the scheduled times by this amount. This ensures that sheduled backup
# happens, even if previous backup didn't expire by this much time.
#
# Since the scheduled job runs once per hour, this will not result in denser
# snapshots; just the deletion check will be lineant.
DURATION_BUFFER = datetime.timedelta(minutes=3)

# Where config files are stored.
_CONFIG_PATH = pathlib.Path("/etc/yabsnap/configs")


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
    keep_preinstall: int = 1
    # How much time must have passed since last pacman install.
    preinstall_interval: float = 5 * 60.0
    # After how much time this backup will be triggered. Currently, the system
    # timer runs with a frequency of 60 minutes. Hence only multiples of 60
    # minutes should be used.
    trigger_interval: float = 60 * 60.0
    # Will keep this many of snapshots; rest will be removed during housekeeping.
    keep_hourly: int = 0
    keep_daily: int = 5
    keep_weekly: int = 0
    keep_monthly: int = 0
    keep_yearly: int = 0

    def is_schedule_enabled(self) -> bool:
        return (
            self.keep_hourly > 0
            or self.keep_daily > 0
            or self.keep_weekly > 0
            or self.keep_monthly > 0
            or self.keep_yearly > 0
        )

    @classmethod
    def from_configfile(cls, config_file: str) -> "Config":
        inifile = configparser.ConfigParser()
        inifile.read(config_file)
        section = inifile["DEFAULT"]
        result = cls(
            config_file=config_file,
            source=section["source"],
            dest_prefix=section["dest_prefix"],
        )
        for key, value in section.items():
            if not hasattr(result, key):
                logging.warning(f"Invalid field {key=} found in {config_file=}")
            if key.endswith("_interval"):
                setattr(result, key, human_interval.parse_to_secs(value))
            elif key not in {"source", "dest_prefix"}:
                setattr(result, key, int(value))
        return result

    @property
    def deletion_rules(self) -> list[tuple[datetime.timedelta, int]]:
        return [
            (datetime.timedelta(hours=1) - DURATION_BUFFER, self.keep_hourly),
            (datetime.timedelta(days=1) - DURATION_BUFFER, self.keep_daily),
            (datetime.timedelta(weeks=1) - DURATION_BUFFER, self.keep_weekly),
            (datetime.timedelta(days=30) - DURATION_BUFFER, self.keep_monthly),
            (datetime.timedelta(days=365.24) - DURATION_BUFFER, self.keep_yearly),
        ]

    @property
    def mount_path(self) -> str:
        return os.path.dirname(self.dest_prefix)


def iterate_configs(source: Optional[str]) -> Iterator[Config]:
    if not _CONFIG_PATH.is_dir():
        os_utils.eprint(
            "Config directory does not exist. Use 'create-config' command to create a config."
        )
        return
    configs_found = False
    for fname in _CONFIG_PATH.iterdir():
        logging.info(f'Reading config {fname}')
        config = Config.from_configfile(str(fname))
        if not config.source or not config.dest_prefix:
            os_utils.eprint(
                f"WARNING: Skipping invalid configuration {fname}"
                " (please specify source and dest_prefix)"
            )
            continue
        if not source or config.source == source:
            configs_found = True
            yield config
    if source is not None and not configs_found:
        logging.warning(f"No config file found with source={source}")


def is_schedule_enabled() -> bool:
    for config in iterate_configs(None):
        if config.is_schedule_enabled():
            logging.info('Schedule is enabled.')
            return True
    logging.info('Schedule is not enabled.')
    return False


def _example_config_fname() -> pathlib.Path:
    script_dir = pathlib.Path(os.path.realpath(__file__)).parent
    return script_dir / "example_config.conf"


def create_config(name: str, source: str | None):
    inadmissible_chars = "@/."
    if any(c in inadmissible_chars for c in name):
        os_utils.eprint(
            f"Error: Config name should be a file name, without following chars: {inadmissible_chars}"
        )
        return

    _config_fname = _CONFIG_PATH / f"{name}.conf"
    if _config_fname.exists():
        os_utils.eprint(f"Already exists: {_config_fname}")
        return

    lines: list[str] = []
    for line in open(_example_config_fname()):
        line = line.strip()
        if source and line.startswith("source ="):
            line = f"source = {source}"
        elif line.startswith("dest_prefix ="):
            line = f"dest_prefix = /.snapshots/@{name}-"
        lines.append(line)

    try:
        _config_fname.parent.mkdir(parents=True, exist_ok=True)
        with _config_fname.open("w") as out:
            out.write("\n".join(lines))
    except PermissionError:
        os_utils.eprint(f"Could not access or create {_config_fname}; run as root?")
        return

    os_utils.eprint()
    os_utils.eprint(f"Created: {_config_fname}")
    if not source:
        os_utils.eprint("Please edit the file to set 'source = ' field.")
