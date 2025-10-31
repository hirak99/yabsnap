"""Encapsulates the JSON metadata for snapshots.

Note: Pydantic is an alternative to managing our own logic to load and save things like
enums. However, it is an additional dependency. We should consider switching only if the
complexity grows too high.
"""

import dataclasses
import datetime
import json
import logging
import os

from .. import global_flags
from ..mechanisms import snap_type_enum
from ..utils import dataclass_loader
from ..utils import os_utils

from typing import Any


@dataclasses.dataclass
class Btrfs:
    source_subvol: str


@dataclasses.dataclass
class SnapMetadata:
    # Snapshot type.
    # This will always be populated for new snapshots.
    # If empty, assumed btrfs for backwards compatibility with old snaps.
    snap_type: snap_type_enum.SnapType = snap_type_enum.SnapType.BTRFS
    # Name of the subvolume from whcih this snap was taken.
    source: str = ""
    # Filesystem UUID of source.
    source_uuid: str | None = None
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

    # Populated by mechanism.
    # aux: dict[str, str] = dataclasses.field(default_factory=dict)
    btrfs: Btrfs | None = None

    def is_expired(self, now: datetime.datetime) -> bool:
        if self.expiry is None:
            return False
        return self.expiry < now.timestamp()

    def _to_file_content(self) -> dict[str, Any]:
        # Ignore empty strings and None.
        result = {k: v for k, v in dataclasses.asdict(self).items() if v}
        if "snap_type" in result:
            result["snap_type"] = result["snap_type"].value
        return result

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
                try:
                    all_args = json.load(f)
                except json.JSONDecodeError:
                    logging.warning(f"Unable to parse metadata file: {fname}")
                    return cls()
            return dataclass_loader.load_dataclass(cls, all_args)
        return cls()
