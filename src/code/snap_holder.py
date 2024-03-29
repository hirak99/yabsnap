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
"""Encapsulates a btrfs snapshot, and relevant metadata.

The existence of this object doesn't mean the snapshot exists;
it can also be an empty place holder.
"""

import dataclasses
import datetime
import json
import logging
import os

from . import global_flags
from . import os_utils

TIME_FORMAT = r"%Y%m%d%H%M%S"
TIME_FORMAT_LEN = 14


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.execute_sh(cmd)


@dataclasses.dataclass
class _Metadata:
    # Name of the subvolume from whcih this snap was taken.
    source: str = ""
    # Can be one of -
    # I - Package installation or system update
    # S - Scheduled
    # U - User
    trigger: str = ""
    # Optional comment if any.
    comment: str = ""

    def save_file(self, fname: str) -> None:
        # Ignore empty strings.
        data = {k: v for k, v in dataclasses.asdict(self).items() if v != ""}
        if global_flags.FLAGS.dryrun:
            os_utils.eprint(f"Would create {fname}: {data}")
            return
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_file(cls, fname: str) -> "_Metadata":
        if os.path.isfile(fname):
            with open(fname) as f:
                try:
                    return cls(**json.load(f))
                except json.JSONDecodeError:
                    logging.warning(f"Unable to parse metadata file: {fname}")
        return cls()


class Snapshot:
    def __init__(self, target: str) -> None:
        # The full pathname of the snapshot directory.
        # Also exposed as a public property .target.
        self._target = target
        timestr = self._target[-TIME_FORMAT_LEN:]
        self._snaptime = datetime.datetime.strptime(timestr, TIME_FORMAT)
        self._metadata_fname = target + "-meta.json"
        self.metadata = _Metadata.load_file(self._metadata_fname)
        self._dryrun = False

    @property
    def target(self) -> str:
        return self._target

    @property
    def snaptime(self) -> datetime.datetime:
        return self._snaptime

    def create_from(self, parent: str) -> None:
        if not os_utils.is_btrfs_volume(parent):
            logging.error("Unable to validate source as btrfs - aborting snapshot!")
            return
        self.metadata.source = parent
        self.metadata.save_file(self._metadata_fname)
        try:
            _execute_sh("btrfs subvolume snapshot -r " f"{parent} {self._target}")
        except os_utils.CommandError:
            logging.error("Unable to create; are you running as root?")
            raise

    def delete(self) -> None:
        try:
            _execute_sh(f"btrfs subvolume delete {self._target}")
        except os_utils.CommandError:
            logging.error("Unable to delete; are you running as root?")
            raise
        if not global_flags.FLAGS.dryrun:
            if os.path.exists(self._metadata_fname):
                os.remove(self._metadata_fname)
        else:
            os_utils.eprint(f"Would delete {self._metadata_fname}")
