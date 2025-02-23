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

from . import abstract_mechanism
from .. import global_flags
from .. import os_utils


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.execute_sh(cmd)


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
        try:
            _execute_sh(f"rsync -aAXHSv --delete {source}/ {destination}")
        except os_utils.CommandError:
            logging.error("Unable to create snapshot using rsync.")
            raise

    def delete(self, destination: str):
        try:
            _execute_sh(f"rm -rf {destination}")
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
