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
from . import human_interval
from . import os_utils
from .mechanisms import snap_mechanisms

from typing import Any


@dataclasses.dataclass
class _Metadata:
    # Snapshot type. If empty, assumed btrfs.
    snap_type: str = snap_mechanisms.SnapType.UNKNOWN.value
    # Name of the subvolume from whcih this snap was taken.
    source: str = ""
    # Can be one of -
    # I - Package installation or system update
    # S - Scheduled
    # U - User
    trigger: str = ""
    # Optional comment if any.
    comment: str = ""
    # Unix datetime in seconds.
    # Note: Expiry is absolute, ttl is relative to now. Expiry = Now + Ttl.
    expiry: float | None = None

    def is_expired(self, now: datetime.datetime) -> bool:
        if self.expiry is None:
            return False
        return self.expiry < now.timestamp()

    def _to_file_content(self) -> dict[str, Any]:
        # Ignore empty strings and None.
        return {k: v for k, v in dataclasses.asdict(self).items() if v}

    def save_file(self, fname: str) -> None:
        data = self._to_file_content()
        if global_flags.FLAGS.dryrun:
            os_utils.eprint(f"Would create {fname}: {data}")
            return
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_file(cls, fname: str) -> "_Metadata":
        if os.path.isfile(fname):
            with open(fname) as f:
                all_args = json.load(f)
                if "snap_type" not in all_args:
                    # For back compatibility. Older snaps will not have snap_type.
                    all_args["snap_type"] = "BTRFS"
                try:
                    return cls(**all_args)
                except json.JSONDecodeError:
                    logging.warning(f"Unable to parse metadata file: {fname}")
        return cls()


class Snapshot:
    def __init__(self, target: str) -> None:
        # The full pathname of the snapshot directory.
        # Also exposed as a public property .target.
        self._target = target
        timestr = self._target[-global_flags.TIME_FORMAT_LEN :]
        self._snaptime = datetime.datetime.strptime(timestr, global_flags.TIME_FORMAT)
        self._metadata_fname = target + "-meta.json"
        self.metadata = _Metadata.load_file(self._metadata_fname)
        self._dryrun = False

    @property
    def target(self) -> str:
        return self._target

    @property
    def snaptime(self) -> datetime.datetime:
        return self._snaptime

    @property
    def _snap_type(self) -> snap_mechanisms.SnapType:
        snap_type = snap_mechanisms.SnapType[self.metadata.snap_type]
        if snap_type == snap_mechanisms.SnapType.UNKNOWN:
            logging.warning(
                f"Cannot determine type for '{self.target}'.\n"
                f"This may occur if the metadata '{self._metadata_fname}' was manually deleted.\n"
                f"If so, also delete the snapshot '{self.target}' manually."
            )
        return snap_type

    def as_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        result["trigger"] = self.metadata.trigger
        result["comment"] = self.metadata.comment
        if self.metadata.expiry is not None:
            result["expiry"] = self.metadata.expiry
        return result

    def set_ttl(self, ttl_str: str, now: datetime.datetime) -> None:
        if ttl_str == "":
            self.metadata.expiry = None
        else:
            ttl_secs = human_interval.parse_to_secs(ttl_str)
            expiry = now + datetime.timedelta(seconds=ttl_secs)
            self.metadata.expiry = expiry.timestamp()
        self.metadata.save_file(self._metadata_fname)

    def create_from(self, snap_type: snap_mechanisms.SnapType, parent: str) -> None:
        if not snap_mechanisms.get(snap_type).verify_volume(parent):
            logging.error("Unable to validate source volume - aborting snapshot!")
            return
        # Create the metadata before the snapshot.
        # Thus we leave trace even if snapshotting fails.
        self.metadata.snap_type = snap_type.value
        self.metadata.source = parent
        self.metadata.save_file(self._metadata_fname)
        # Create the snap.
        snap_mechanisms.get(snap_type).create(parent, self._target)

    def delete(self) -> None:
        # First delete the snapshot.
        snap_mechanisms.get(self._snap_type).delete(self._target)
        # Then delete the metadata.
        if not global_flags.FLAGS.dryrun:
            if os.path.exists(self._metadata_fname):
                os.remove(self._metadata_fname)
        else:
            os_utils.eprint(f"Would delete {self._metadata_fname}")
