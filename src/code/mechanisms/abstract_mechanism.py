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

import abc
import dataclasses
import enum
import logging
import os

from ..snapshot_logic import snap_metadata


# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    UNKNOWN = "UNKNOWN"
    BTRFS = "BTRFS"


@dataclasses.dataclass
class LightSnapshot:
    """Used to avoid circular reference in rollback generation."""

    target: str
    metadata: snap_metadata.SnapMetadata


def destdir_inside_source(source: str, dest_prefix: str) -> bool:
    """Whether the snapshot storage dir (dirname of dest_prefix) is inside source.

    Pure path check, no filesystem access. Used by mechanisms whose snapshots
    live as plain directories (rsync), and as a pre-filter by others.
    """
    destdir = os.path.dirname(dest_prefix.rstrip(os.sep))
    if not destdir:
        return False
    child = os.path.normpath(destdir)
    parent = os.path.normpath(source)
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


class SnapMechanism(abc.ABC):
    """Interface with necessary methods to implement snapshotting system.

    Implementations may be based on btrfs, rsync, bcachefs, etc.
    """

    @abc.abstractmethod
    def verify_volume(self, source: str) -> bool:
        """Confirms that the source path can be snapshotted."""

    def fill_metadata(self, metadata: snap_metadata.SnapMetadata) -> None:
        """Implementations can use it to fill in additional metadata."""
        return

    @abc.abstractmethod
    def create(self, source: str, destination: str):
        """Creates a snapshot of source in a destination path."""

    @abc.abstractmethod
    def delete(self, destination: str):
        """Deletes an existing snapshot."""

    @abc.abstractmethod
    def rollback_gen(
        self,
        snapshots: list[LightSnapshot],
        subvol_map: dict[str, str] | None,
    ) -> list[str]:
        """Returns shell script lines to roll back snapshots.

        If it is not possible to roll back this type of snap, or if it is
        unimplemented, raise an error such as NotImplementedError().

        source_dests: List of (live_path, snap_path) tuples. E.g. -
          [
            ('/', '/.snapshots/@root-20250921193009'),
            ('/home', '/.snapshots/@home-20250921193009'),
          ]

        subvol_map: A map from live_path (e.g., '/') to the subvolume name
          where it is currently mounted (e.g. '@'). This should not be required
          during normal operation. However, this parameter may be passed by the
          user when it cannot be auto detected, e.g. during offline recovery.
        """

    @abc.abstractmethod
    def _nested_dest_reason(self, source: str, dest_prefix: str) -> str | None:
        """Returns why snapshot storage (dirname of dest_prefix) inside source is bad.

        Returns None if the layout is fine. Must never raise for unresolvable
        layouts (debug-log and return None instead); each mechanism implements
        this with its own mount/subvolume awareness.
        """

    def warn_if_dest_inside_source(self, source: str, dest_prefix: str) -> None:
        """Warns if snapshot storage (dirname of dest_prefix) lives inside source.

        Called on snapshot write paths. Common framing is added here; the
        specific reason comes from _nested_dest_reason().
        """
        reason = self._nested_dest_reason(source, dest_prefix)
        if reason is not None:
            logging.warning(
                f"Nonstandard layout, rollback may not be supported. Reason: {reason}"
            )

    @abc.abstractmethod
    def sync_paths(self, paths: set[str]):
        """Syncs with a set of mount paths that may have been modified.

        Create a no-op implementation in case sync is not applicable.
        This will be called if the user passes the --sync flag.
        """
