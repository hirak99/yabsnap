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
import logging
import os
import subprocess
from typing import Iterable

from . import configs
from . import os_utils
from . import snap_operator
from .mechanisms import snap_mechanisms


def _find_and_categorize_snaps(
    configs_iter: Iterable[configs.Config], path_suffix: str
) -> dict[snap_mechanisms.SnapType, list[tuple[str, str]]]:
    """Find snapshots in the configuration file and categorize them based on their type."""
    source_dests_by_snaptype: dict[
        snap_mechanisms.SnapType, list[tuple[str, str]]
    ] = collections.defaultdict(list)

    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            source_dests_by_snaptype[config.snap_type].append(
                (snap.metadata.source, snap.target)
            )

    return source_dests_by_snaptype


_ROLLBACK_SCRIPT_FILEPATH = "/tmp/rollback.sh"


def rollback(
    configs_iter: Iterable[configs.Config],
    path_suffix: str,
    *,
    execute: bool = False,
    no_confirm: bool = False,
) -> None:
    source_dests_by_snaptype = _find_and_categorize_snaps(
        configs_iter, path_suffix
    )
    contents = _show_and_return_rollback_gen(source_dests_by_snaptype)
    _create_and_chmod_script(contents)

    if execute and no_confirm:
        subprocess.run([".", _ROLLBACK_SCRIPT_FILEPATH])
        return

    if execute is True:
        msg = "Review the code and enter 'y' to confirm execution. [y/N] "
        confirm = os_utils.interactive_confirm(msg)
        if confirm:
            subprocess.run(f".{_ROLLBACK_SCRIPT_FILEPATH}")


def _create_and_chmod_script(contents: list[str]) -> None:
    with open(_ROLLBACK_SCRIPT_FILEPATH, mode="w", encoding="utf_8") as fp:
        fp.writelines(contents)
    logging.info(
        f"The rollback script is saved in {_ROLLBACK_SCRIPT_FILEPATH} ."
    )

    os.chmod(_ROLLBACK_SCRIPT_FILEPATH, mode=0o700)
    if os.access(_ROLLBACK_SCRIPT_FILEPATH, mode=os.X_OK) is True:
        logging.info(
            f"Execution permissions have been granted for {_ROLLBACK_SCRIPT_FILEPATH} ."
        )
    else:
        logging.warning(
            f"Manual execution permissions need to be added for {_ROLLBACK_SCRIPT_FILEPATH} ."
        )


def _show_and_return_rollback_gen(
    source_dests_by_snaptype: dict[
        snap_mechanisms.SnapType, list[tuple[str, str]]
    ],
) -> list[str]:
    contents = [
        "\n".join(snap_mechanisms.get(snap_type).rollback_gen(source_dests))
        for snap_type, source_dests in sorted(source_dests_by_snaptype.items())
    ]

    print("=== THE FOLLOWING IS THE ROLLBACK CODE ===")
    for content in contents:
        print(content)
    print("=== THE ABOVE IS THE ROLLBACK CODE ===")

    return contents
