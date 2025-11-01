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

import logging
import os
import re
import shlex

from . import abstract_mechanism
from .. import global_flags
from ..snapshot_logic import snap_holder
from ..utils import os_utils

from typing import override


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.runsh_or_error(cmd)


def _initialize_destination(destination: str) -> None:
    """If a previous snap is found, creates hardlinks from it and returns True."""
    # Confirm the destination matches the required format: PREFIX + YYYYMMDDhhmmss.
    dest_dir = os.path.basename(destination)
    match = re.match(r"^(.*)(\d{10})$", dest_dir)
    if not match:
        raise ValueError(
            "Destination directory name must match the pattern 'PREFIX + YYYYMMDDhhmmss'."
        )

    prefix = match.group(1)

    # Get the parent directory path of the destination.
    parent_dir = os.path.dirname(destination)

    # Check if there are any directories with the same format and prefix in the parent folder.
    existing_dirs = [
        d
        for d in os.listdir(parent_dir)
        if os.path.isdir(os.path.join(parent_dir, d))
        and re.match(rf"^{prefix}\d{{10}}$", d)
    ]

    if not existing_dirs:
        return

    # Find the lexicographically max directory (latest snapshot).
    latest_snapshot = max(existing_dirs)
    latest_snapshot_path = os.path.join(parent_dir, latest_snapshot)

    # Copy the latest snapshot recursively as hardlinks.
    logging.info(f"Found latest snapshot: {latest_snapshot}.")
    _execute_sh(
        f"cp -al {shlex.quote(latest_snapshot_path)}/ {shlex.quote(destination)}/"
    )


class RsyncSnapMechanism(abstract_mechanism.SnapMechanism):
    @override
    def verify_volume(self, source: str) -> bool:
        # This checks if the mount_point can be snapshotted by this mechanism.
        # We can verify if the source path exists and is readable.
        if not os.path.exists(source):
            logging.warning(f"Source path does not exist: {source}")
            return False
        if not os.access(source, os.R_OK):
            logging.warning(f"Source path is not readable: {source}")
            return False
        return True

    @override
    def create(self, source: str, destination: str):
        if not os_utils.command_exists("rsync"):
            raise RuntimeError(
                "rsync not found, please install to create rsync snapshots"
            )

        _initialize_destination(destination)
        try:
            _execute_sh(
                f"rsync -aAXHSv --delete {shlex.quote(source)}/ {shlex.quote(destination)}"
            )
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to create snapshot using rsync.") from exc

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"rm -rf {shlex.quote(destination)}")
        except os_utils.CommandError as exc:
            raise RuntimeError("Unable to delete snapshot.") from exc

    @override
    def rollback_gen(
        self,
        snapshots: list[snap_holder.Snapshot],
        subvol_map: dict[str, str] | None,
    ) -> list[str]:
        # Rollback for rsync snapshots is not directly supported in the same way as btrfs.
        # For now, we raise NotImplementedError. A possible implementation could involve
        # rsyncing back from the snapshot to the source, but this is complex and potentially dangerous.
        raise NotImplementedError("Rollback is not implemented for rsync snapshots.")

    @override
    def sync_paths(self, paths: set[str]):
        # As rsync is just copying files, we will let the os and fs handle syncing.
        pass
