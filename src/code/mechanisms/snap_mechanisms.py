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

import enum
import functools

from . import abstract_mechanism
from . import btrfs_mechanism
from . import rsync_mechanism


# The type of snapshot is maintained in two places -
# 1. Config
# 2. Snapshot
class SnapType(enum.Enum):
    UNKNOWN = "UNKNOWN"
    BTRFS = "BTRFS"
    RSYNC = "RSYNC"


@functools.cache
def get(snap_type: SnapType) -> abstract_mechanism.SnapMechanism:
    """Singleton factory implementation."""
    if snap_type == SnapType.BTRFS:
        return btrfs_mechanism.BtrfsSnapMechanism()
    if snap_type == SnapType.RSYNC:
        return rsync_mechanism.RsyncSnapMechanism()
    raise RuntimeError(f"Unknown snap_type {snap_type}")
