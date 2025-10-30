"""Encapsulates the JSON metadata for snapshots."""

import dataclasses
import datetime
import json
import logging
import os

from .. import global_flags
from ..mechanisms import snap_mechanisms
from ..utils import os_utils

from typing import Any


@dataclasses.dataclass
class SnapMetadata:
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
    def load_file(cls, fname: str) -> "SnapMetadata":
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
