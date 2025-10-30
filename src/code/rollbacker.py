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
import tempfile

from . import configs
from . import global_flags
from . import snap_operator
from .mechanisms import snap_mechanisms
from .utils import os_utils

from typing import Iterable


def _get_rollback_script_text(
    configs_iter: Iterable[configs.Config],
    path_suffix: str,
    live_subvol_map: dict[str, str] | None,
) -> str | None:
    """Combines the rollback scripts from all snaps. Returns None if no matching snapshot exists."""
    source_dests_by_snaptype: dict[snap_mechanisms.SnapType, list[tuple[str, str]]] = (
        collections.defaultdict(list)
    )
    for config in configs_iter:
        snap = snap_operator.find_target(config, path_suffix)
        if snap:
            source_dests_by_snaptype[config.snap_type].append(
                (snap.metadata.source, snap.target)
            )
    if not source_dests_by_snaptype:
        return None

    content: list[str] = [
        "#!/bin/bash",
        "# Review and run this script to perform rollback.",
        "",
        "set -uexo pipefail",
        "",
    ]
    for snap_type, source_dests in sorted(source_dests_by_snaptype.items()):
        content.append(
            "\n".join(
                snap_mechanisms.get(snap_type).rollback_gen(
                    source_dests, live_subvol_map
                )
            )
        )
    return "\n".join(content)


def _save_and_execute_script(contents: str) -> None:
    if global_flags.FLAGS.dryrun:
        os_utils.eprint(f"Would execute the script if --dry-run is not passed.")
        return

    with tempfile.TemporaryDirectory(prefix="yabsnap_script") as dir:
        temp_file_name = os.path.join(dir, "yabsnap_script.sh")
        with open(temp_file_name, mode="w", encoding="utf_8") as fp:
            fp.write(contents)
        os.chmod(temp_file_name, mode=0o700)

        try:
            subprocess.run(temp_file_name, check=True)
            print()
            print("Rollback executed. Please reboot at earliest convenience.")
        except subprocess.CalledProcessError:
            logging.error("Execution of rollback was unsuccessful.")


def rollback(
    configs_iter: Iterable[configs.Config],
    path_suffix: str,
    live_subvol_map: dict[str, str] | None,
    *,
    execute: bool = False,
    no_confirm: bool = False,
) -> None:
    # Obtain and display the text of rollback.
    script_text = _get_rollback_script_text(configs_iter, path_suffix, live_subvol_map)
    if script_text is None:
        os_utils.eprint("No matching snapshots.")
        return
    print(script_text)

    # Check if we should execute the script.
    if not execute:
        return
    if not no_confirm:
        print()
        msg = "Please review the rollback script above, and confirm execution:"
        if not os_utils.interactive_confirm(msg):
            return

    # Save and execute the script.
    _save_and_execute_script(script_text)
