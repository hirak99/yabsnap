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

import collections

from . import configs
from . import snap_operator
from .mechanisms import snap_mechanisms

from typing import Iterable


def rollback(configs_iter: Iterable[configs.Config], path_suffix: str):
    source_dests_by_snaptype: dict[snap_mechanisms.SnapType, list[tuple[str, str]]] = (
        collections.defaultdict(list)
    )
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            source_dests_by_snaptype[config.snap_type].append(
                (snap.metadata.source, snap.target)
            )
    for snap_type, source_dests in sorted(source_dests_by_snaptype.items()):
        print("\n".join(snap_mechanisms.get(snap_type).rollback_gen(source_dests)))
