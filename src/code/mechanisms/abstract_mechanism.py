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
import enum


# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    UNKNOWN = "UNKNOWN"
    BTRFS = "BTRFS"


class SnapMechanism(abc.ABC):
    """Interface with necessary methods to implement snapshotting system.

    Implementations may be based on btrfs, rsync, bcachefs, etc.
    """

    @abc.abstractmethod
    def verify_volume(self, mount_point: str) -> bool:
        """Confirms that the source path can be snapshotted."""

    @abc.abstractmethod
    def create(self, source: str, destination: str):
        """Creates a snapshot of source in a destination path."""

    @abc.abstractmethod
    def delete(self, destination: str):
        """Deletes an existing snapshot."""

    @abc.abstractmethod
    def rollback_gen(self, source_dests: list[tuple[str, str]]) -> list[str]:
        """Returns shell lines which when executed will result in a rollback of snapshots."""
        # It is okay to leave unimplemented, and raise NotImplementedError().
