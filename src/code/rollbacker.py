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

from . import configs
from . import snap_operator
from .mechanisms import snap_mechanisms

from typing import Iterable


def rollback(configs_iter: Iterable[configs.Config], path_suffix: str):
    source_dests: list[tuple[str, str]] = []
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            if snap.metadata.snap_type == snap_mechanisms.SnapType.BTRFS:
                source_dests.append((snap.metadata.source, snap.target))
            else:
                raise RuntimeError(
                    f"Cannot rollback snap of type {snap.metadata.snap_type} yet"
                )
    print("\n".join(_rollback_btrfs_snapshots(source_dests)))


def _rollback_btrfs_snapshots(source_dests: list[tuple[str, str]]) -> list[str]:
    return snap_mechanisms.get(snap_mechanisms.SnapType.BTRFS).rollback_gen(
        source_dests
    )
