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
import os
import pathlib
import shlex

from .mechanisms import snap_mechanisms
from .utils import human_interval
from .utils import os_utils

from typing import Iterable, Iterator, Optional

# Shortens the scheduled times by this amount. This ensures that sheduled backup
# happens, even if previous backup didn't expire by this much time.
#
# Since the scheduled job runs once per hour, this will not result in denser
# snapshots; just the deletion check will be lineant.
DURATION_BUFFER = datetime.timedelta(minutes=3)

# User specified config file to use.
# If set, _CONFIG_PATH will be ignored.
USER_CONFIG_FILE: Optional[str] = None

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
    # Enables TTL based scheduled snapshot management.
    enable_scheduled_ttl: bool = True
    # Will keep this many of snapshots; rest will be removed during housekeeping.
    keep_hourly: int = 0
    keep_daily: int = 5
    keep_weekly: int = 0
    keep_monthly: int = 0
    keep_yearly: int = 0

    post_transaction_scripts: list[str] = dataclasses.field(default_factory=list)

    # If empty, btrfs is assumed.
    snap_type: snap_mechanisms.SnapType = snap_mechanisms.SnapType.BTRFS

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
            if key == "post_transaction_scripts":
                result.post_transaction_scripts = shlex.split(value)
                continue
            if key == "snap_type":
                if not value:
                    value = "BTRFS"
                result.snap_type = snap_mechanisms.SnapType[value]
                continue
            if not hasattr(result, key):
                logging.warning(f"Invalid field {key=} found in {config_file=}")
            if key == "enable_scheduled_ttl":
                # Boolean.
                if value.lower() not in ("true", "false"):
                    raise ValueError(
                        f"Invalid boolean value for {key} in {config_file=}"
                    )
                setattr(result, key, value.lower().strip() == "true")
            elif key.endswith("_interval"):
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

    def call_post_hooks(self) -> None:
        for script in self.post_transaction_scripts:
            os_utils.run_user_script(script, [self.config_file])

    def is_compatible_volume(self) -> bool:
        return snap_mechanisms.get(self.snap_type).verify_volume(self.source)


def iterate_configs(source: Optional[str]) -> Iterator[Config]:
    config_iterator: Iterable[str]
    # Try to add the user-specified configuration file to the `config_iterator`
    # or try to add the configuration file from the `_CONFIG_PATH` to the `config_iterator`.
    if USER_CONFIG_FILE is not None:
        if not os.path.isfile(USER_CONFIG_FILE):
            logging.warning(f"Could not find specified config file: {USER_CONFIG_FILE}")
            return
        config_iterator = [USER_CONFIG_FILE]
        logging.info(f"Using user-supplied config {USER_CONFIG_FILE}")
    else:
        if not _CONFIG_PATH.is_dir():
            os_utils.eprint(
                "Config directory does not exist. Use 'create-config' command to create a config."
            )
            return

        if not os.access(_CONFIG_PATH, os.R_OK):
            logging.error(f"Cannot accesss '{_CONFIG_PATH}'; run as root?")
            return
        config_iterator = (
            str(path)
            for path in _CONFIG_PATH.iterdir()
            if path.is_file() and path.suffix == ".conf"
        )

    # Check whether the necessary fields in the configuration file are filled in
    # and append the configurations with filled necessary fields to `config_iterator`
    configs_found = False
    for fname in config_iterator:
        logging.info(f"Reading config {fname}")
        config = Config.from_configfile(fname)
        if not (config.source and config.dest_prefix):
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
    if USER_CONFIG_FILE is not None:
        # User-specified config indicates advanced usage, with possibly self
        # managed automation. Do not check for schedule if it is present.
        return True
    for config in iterate_configs(None):
        if config.is_schedule_enabled():
            logging.info("Schedule is enabled.")
            return True
    logging.info("Schedule is not enabled.")
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
    if USER_CONFIG_FILE is not None:
        _config_fname = pathlib.Path(USER_CONFIG_FILE)

    if _config_fname.exists():
        os_utils.eprint(f"Already exists: {_config_fname}")
        return

    lines: list[str] = []
    with open(_example_config_fname()) as f:
        for line in f:
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
        logging.error(f"Could not access or create {_config_fname}; run as root?")
        return

    os_utils.eprint()
    os_utils.eprint(f"Created: {_config_fname}")
    if not source:
        os_utils.eprint("Please edit the file to set 'source = ' field.")
