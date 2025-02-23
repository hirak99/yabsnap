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
from .. import os_utils


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.execute_sh(cmd)


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
    def verify_volume(self, mount_point: str) -> bool:
        # We can check if the source path exists and is readable.
        if not os.path.exists(mount_point):
            logging.warning(f"Source path does not exist: {mount_point}")
            return False
        if not os.access(mount_point, os.R_OK):
            logging.warning(f"Source path is not readable: {mount_point}")
            return False
        return True

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
        except os_utils.CommandError:
            logging.error("Unable to create snapshot using rsync.")
            raise

    def delete(self, destination: str):
        try:
            _execute_sh(f"rm -rf {shlex.quote(destination)}")
        except os_utils.CommandError:
            logging.error("Unable to delete snapshot.")
            raise

    def rollback_gen(self, source_dests: list[tuple[str, str]]) -> list[str]:
        # Rollback for rsync snapshots is not directly supported in the same way as btrfs.
        # For now, we raise NotImplementedError. A possible implementation could involve
        # rsyncing back from the snapshot to the source, but this is complex and potentially dangerous.
        raise NotImplementedError("Rollback is not implemented for rsync snapshots.")

    def sync_paths(self, paths: set[str]):
        # rsync itself is a synchronization tool, so we can consider sync_paths a no-op for rsync.
        # Alternatively, we could re-run rsync to ensure consistency, but for now, we'll do nothing.
        logging.info("sync_paths is a no-op for rsync mechanism.")
        pass
