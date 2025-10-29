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

from . import abstract_mechanism
from . import rollback_btrfs
from .. import global_flags
from .. import os_utils

from typing import override


def _execute_sh(cmd: str):
    if global_flags.FLAGS.dryrun:
        os_utils.eprint("Would run " + cmd)
    else:
        os_utils.execute_sh(cmd)


class BtrfsSnapMechanism(abstract_mechanism.SnapMechanism):
    @override
    def verify_volume(self, source: str) -> bool:
        # Based on https://stackoverflow.com/a/32865333/196462
        fstype = os_utils.execute_sh("stat -f --format=%T " + source, error_ok=True)
        if not fstype:
            logging.warning(f"Not btrfs (cannot determine filesystem): {source}")
            return False
        if fstype.strip() != "btrfs":
            logging.warning(f"Not btrfs (filesystem not btrfs): {source}")
            return False
        inodenum = os_utils.execute_sh("stat --format=%i " + source, error_ok=True)
        if not inodenum:
            logging.warning(f"Not btrfs (cannot determine inode): {source}")
            return False
        if inodenum.strip() != "256":
            logging.warning(
                f"Not btrfs (inode not 256, possibly a subdirectory of a btrfs mount): {source}"
            )
            return False
        return True

    @override
    def create(self, source: str, destination: str):
        try:
            _execute_sh("btrfs subvolume snapshot -r " f"{source} {destination}")
        except os_utils.CommandError:
            logging.error("Unable to create; are you running as root?")
            raise

    @override
    def delete(self, destination: str):
        try:
            _execute_sh(f"btrfs subvolume delete {destination}")
        except os_utils.CommandError:
            logging.error("Unable to delete; are you running as root?")
            raise

    @override
    def rollback_gen(self, source_dests: list[tuple[str, str]]) -> list[str]:
        for source, _ in source_dests:
            if not self.verify_volume(source):
                raise RuntimeError(
                    f"Mount point may no longer be a btrfs volume: {source}"
                )
        return rollback_btrfs.rollback_gen(source_dests)

    def rollback_gen_offline(
        self,
        source_dests: list[tuple[str, str]],
        live_subvol_map: dict[str, str],
    ) -> list[str]:
        """Calls the offline rollback script generator."""
        # We do not perform the verify_volume check here because we assume the system is in an offline/recovery state.
        return rollback_btrfs.rollback_gen_offline(source_dests, live_subvol_map)

    @override
    def sync_paths(self, paths: set[str]):
        for mount_path in sorted(paths):
            if global_flags.FLAGS.dryrun:
                os_utils.eprint(f"Would sync {mount_path}")
                continue
            os_utils.eprint("Syncing ...", flush=True)
            os_utils.execute_sh(f"btrfs subvolume sync {mount_path}")
